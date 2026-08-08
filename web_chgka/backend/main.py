import socketio
import random
import asyncio
import hmac
import logging
import secrets
import os
import time
from pathlib import Path
from typing import Callable, Optional
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from auth import AdminTokenStore
from config import load_app_config
from live_ops import (
    live_ops_cancel_spin,
    live_ops_force_phase,
    live_ops_open_round,
    live_ops_reset_to_intro,
    live_ops_set_score,
    live_ops_set_sector_used,
    live_ops_set_timer,
)
from media import (
    MediaPlaybackError,
    complete_shared_media,
    create_media_token_info,
    create_shared_media,
    current_media_catalog as build_current_media_catalog,
    media_token_is_current,
    next_media_in_section,
    pause_shared_media,
    play_shared_media,
    stop_shared_media,
)
from questions import parse_question_pack, QuestionParseError, QuestionPack
from sound_control import (
    FADE_DURATION_MS,
    begin_fade,
    complete_fade,
    create_sound_control_state,
    public_sound_control,
    supersede_fade,
)
from state import (
    PHASE_INTRO,
    PHASE_LOGIN,
    PHASE_QUESTION_READING,
    PHASE_DISCUSSION,
    PHASE_TEAM_ANSWER,
    PHASE_POST_ROUND,
    create_initial_app_state,
    public_game_state,
)
from transitions import (
    TransitionEffects,
    TransitionError,
    clear_blackbox_presentation,
    transition_complete_spin,
    transition_advance_intro,
    transition_end_round,
    transition_reset,
    transition_end_blackbox,
    transition_score,
    transition_start_discussion,
    transition_start_blackbox,
    transition_start_game,
    transition_start_intro_music,
    transition_start_spin,
    transition_team_answer,
    transition_ten_seconds,
    validate_spin_start,
)
from ui_text import media_display_name, sound_label

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

APP_CONFIG = load_app_config()
DEBUG = APP_CONFIG.is_development
MIN_SPIN_DURATION = 5.0 if DEBUG else 10.0
MAX_SPIN_DURATION = 10.0 if DEBUG else 20.0
SECTORS_COUNT = 13
ANGLE_STEP = 360 / SECTORS_COUNT
ADMIN_NAME = 'Господин Ведущий'
NORMAL_DISCUSSION_SECONDS = 60
BLITZ_DISCUSSION_SECONDS = 20
TEN_SECONDS = 10

# Media access
MEDIA_TOKEN_TTL_SECONDS = 10 * 60  # 10 minutes

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=list(APP_CONFIG.allowed_origins),
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Load question pack once when the app starts.
    _load_question_pack_on_startup()
    yield


fastapi_app = FastAPI(lifespan=lifespan)

fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=list(APP_CONFIG.allowed_origins),
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["Content-Type"],
)

app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)

# --- СИСТЕМА АВТОРИЗАЦИИ ---
# Хранилище единственного активного admin token (в памяти).
admin_tokens = AdminTokenStore(APP_CONFIG.admin_token_ttl_seconds)

def generate_admin_token():
    """Генерирует безопасный токен для админа"""
    token = admin_tokens.issue()
    logger.info(f"Generated admin token (total active: {len(admin_tokens)})")
    return token

def validate_admin_token(token):
    """Проверяет, валиден ли токен"""
    return admin_tokens.validate(token)


def revoke_admin_token(token) -> None:
    admin_tokens.revoke(token)


def _admin_password_matches(password: object) -> bool:
    if not isinstance(password, str):
        return False
    return hmac.compare_digest(
        password.encode("utf-8"),
        APP_CONFIG.admin_password.encode("utf-8"),
    )


def _admin_record_is_authorized(player: dict) -> bool:
    return (
        player.get("role") == "admin"
        and player.get("online", False)
        and validate_admin_token(player.get("token"))
    )

async def get_client_role(sid):
    """Получает роль клиента из сессии Socket.IO"""
    try:
        session = await sio.get_session(sid)
    except Exception:
        return 'player'
    role = session.get("role", "player")
    if role == "admin" and not validate_admin_token(session.get("admin_token")):
        return "player"
    return role


async def _expire_admin_session(sid: str, token: object) -> None:
    """Downgrade an expired/revoked admin socket and clear its public record."""
    global players_list

    revoke_admin_token(token)
    players_list = [
        player
        for player in players_list
        if not (player.get("role") == "admin" and player.get("sid") == sid)
    ]
    try:
        await sio.save_session(sid, {"role": "player"})
    except Exception:
        pass
    await sio.emit("role_update", {"role": "player"}, to=sid)
    await sio.emit(
        "auth_expired",
        {"message": "Сессия ведущего истекла. Введите пароль ещё раз."},
        to=sid,
    )
    await broadcast_players()

async def require_admin(sid):
    """Validate role plus the non-expired token for every privileged action."""
    try:
        session = await sio.get_session(sid)
    except Exception:
        session = {"role": "player"}
    role = session.get("role", "player")
    token = session.get("admin_token")
    if role == "admin" and validate_admin_token(token):
        return True
    if role == "admin":
        await _expire_admin_session(sid, token)
    logger.warning(f"Unauthorized admin action attempt from {sid} (role: {role})")
    return False

global_settings = {
    "volume": 1.0,
    "sound_control": create_sound_control_state(),
}


def _now_ms() -> int:
    return int(time.time() * 1000)


def _public_settings(*, now_ms: Optional[int] = None) -> dict:
    timestamp_ms = _now_ms() if now_ms is None else now_ms
    return {
        "volume": global_settings["volume"],
        "sound_control": public_sound_control(
            global_settings["sound_control"],
            now_ms=timestamp_ms,
        ),
    }


async def emit_settings_update(to: Optional[str] = None) -> None:
    payload = _public_settings()
    if to is None:
        await sio.emit("settings_update", payload)
    else:
        await sio.emit("settings_update", payload, to=to)


def _supersede_sound_fade(*, mode: str) -> int:
    """Synchronously invalidate pending fade completion before network awaits."""
    return supersede_fade(global_settings["sound_control"], mode=mode)

# Хранилище игроков (теперь отдельно)
# [{"sid": "...", "name": "...", "role": "player|admin", "token": "..."}]
players_list = []

# Хранилище состояния игры
app_state = create_initial_app_state()

# Loaded question pack (kept on server; admin UI may request more details later)
loaded_pack: Optional[QuestionPack] = None

# Admin-only pack info (safe subset to send over socket)
pack_admin_info: dict = {}

# Temporary media tokens (media_id -> info)
# Stored only in-memory; safe enough for development.
media_tokens: dict = {}

def _get_round_ctx_and_sector() -> Optional[tuple[dict, int]]:
    """
    Common validation helper: ensure we have a loaded pack, an active round context,
    and a valid sector (1..SECTORS_COUNT). Returns (round_ctx, sector) or None.
    """
    if loaded_pack is None:
        return None
    round_ctx = app_state["game"]["round"]
    if not round_ctx:
        return None
    sector = round_ctx.get("sector")
    if not isinstance(sector, int) or not (1 <= sector <= SECTORS_COUNT):
        return None
    return round_ctx, sector

def _get_round_kind_and_part_index(round_ctx: dict) -> tuple[str, int]:
    kind = round_ctx.get("kind", "normal")
    part_index = int(round_ctx.get("part_index", 0)) if kind in ("blitz", "superblitz") else 0
    return kind, part_index


def _effective_blackbox(question, round_ctx: dict) -> bool:
    """Return the pack-backed black-box flag for the active question/part."""
    kind, part_index = _get_round_kind_and_part_index(round_ctx)
    if kind in ("blitz", "superblitz"):
        part = (
            question.parts[part_index]
            if 0 <= part_index < len(question.parts)
            else None
        )
        return bool(question.blackbox or (part is not None and part.blackbox))
    return bool(question.blackbox)


def _cleanup_expired_media_tokens(now_ts: Optional[float] = None) -> None:
    now = now_ts if now_ts is not None else time.time()
    shared_media = app_state["presentation"].get("shared_media")
    active_shared_id = shared_media.get("media_id") if shared_media else None
    expired = [
        mid
        for mid, info in media_tokens.items()
        if mid != active_shared_id and info.get("expires_at", 0) <= now
    ]
    for mid in expired:
        media_tokens.pop(mid, None)


def _clear_all_media_tokens() -> None:
    media_tokens.clear()


def _get_current_media_catalog() -> dict:
    return build_current_media_catalog(loaded_pack, app_state)


def _media_token_is_current(
    info: dict,
    now_ts: Optional[float] = None,
    *,
    allow_expired: bool = False,
) -> bool:
    return media_token_is_current(
        info,
        loaded_pack,
        app_state,
        now_ts=now_ts if now_ts is not None else time.time(),
        allow_expired=allow_expired,
    )

def _load_question_pack_on_startup() -> None:
    """
    Load questions pack once at startup and expose per-sector question types via app_state.
    """
    env_path = os.getenv("QUESTIONS_PACK_PATH")
    if not env_path:
        raise RuntimeError("QUESTIONS_PACK_PATH is required (path to pack folder with 01..13).")

    pack_path = Path(env_path).resolve()
    if not pack_path.exists():
        raise RuntimeError(f"QUESTIONS_PACK_PATH does not exist: {pack_path}")
    global loaded_pack
    global pack_admin_info
    try:
        pack = parse_question_pack(pack_path)
    except QuestionParseError as e:
        logger.error(f"Failed to load question pack from {pack_path}: {e}")
        raise

    types = [q.type.value for q in pack.questions]
    if len(types) != SECTORS_COUNT:
        raise RuntimeError(f"Question pack must contain {SECTORS_COUNT} questions, got {len(types)}")

    app_state["pack"]["question_types"] = types
    app_state["pack"]["intro_authors"] = [
        [
            {
                "sector": sector,
                "slot": slot,
                "name": author_question.author,
                "city": author_question.city,
                "has_photo": author_question.author_photo is not None,
            }
            for slot, author_question in enumerate(
                question.parts or [question],
                start=1,
            )
        ]
        for sector, question in enumerate(pack.questions[:12], start=1)
    ]
    loaded_pack = pack
    pack_admin_info = {
        "path": str(pack.path),
        "question_titles": [q.title for q in pack.questions],
        "question_types": types,
        "question_blackbox": [
            {
                "question": question.blackbox,
                "parts": [part.blackbox for part in question.parts],
            }
            for question in pack.questions
        ],
        "intro_html": pack.intro_html,
    }
    logger.info(f"Loaded question pack: {pack.path} ({len(types)} questions)")

async def _emit_pack_info_to_admin(sid: str) -> None:
    """Send question titles (and types) to admin only."""
    role = await get_client_role(sid)
    if role != "admin":
        return
    await sio.emit(
        "pack_info",
        {"pack": pack_admin_info},
        to=sid,
    )


async def _emit_current_question_to_admins() -> None:
    """Send current question content to all online admins (admin-only)."""
    res = _get_round_ctx_and_sector()
    if not res:
        return
    round_ctx, sector = res

    try:
        q = loaded_pack.get_by_sector(sector)
    except Exception:
        return

    kind, _part_index_norm = _get_round_kind_and_part_index(round_ctx)
    payload = {
        "sector": sector,
        "kind": kind,
        "phase": app_state["game"]["phase"],
        "blackbox": _effective_blackbox(q, round_ctx),
    }

    if kind in ("blitz", "superblitz"):
        part_index = int(round_ctx.get("part_index", 0))
        part = q.parts[part_index] if 0 <= part_index < len(q.parts) else None
        payload.update(
            {
                "round_title": q.title,
                "part_index": part_index,
                "intro_html": q.question_html,
            }
        )
        if part is not None:
            payload.update(
                {
                    "title": part.title,
                    "author": part.author,
                    "question_html": part.question_html,
                    "answer_html": part.answer_html,
                    "comment_html": part.comment_html,
                    "sources_html": part.sources_html,
                }
            )
    else:
        payload.update(
            {
                "title": q.title,
                "author": q.author,
                "question_html": q.question_html,
                "answer_html": q.answer_html,
                "comment_html": q.comment_html,
                "sources_html": q.sources_html,
            }
        )

    payload["media"] = [
        media.public_descriptor()
        for media in _get_current_media_catalog().values()
    ]

    for p in players_list:
        if _admin_record_is_authorized(p):
            await sio.emit("admin_question", payload, to=p["sid"])


async def _clear_admin_question_for_admins() -> None:
    """Remove stale admin-only question content after recovery clears a round."""
    for player in players_list:
        if _admin_record_is_authorized(player):
            await sio.emit("admin_question", None, to=player["sid"])


def add_log(message):
    time_str = datetime.now().strftime("%H:%M:%S")
    log_entry = f"[{time_str}] {message}"
    app_state["logs"].insert(0, log_entry) # Новые сверху
    # Ограничим размер лога
    if len(app_state["logs"]) > 50:
        app_state["logs"] = app_state["logs"][:50]
    return log_entry


async def emit_state_update(to: Optional[str] = None) -> None:
    payload = public_game_state(app_state)
    if to is None:
        await sio.emit("state_update", payload)
    else:
        await sio.emit("state_update", payload, to=to)


async def _emit_transition_error(sid: str, error: TransitionError) -> None:
    logger.warning("Rejected transition %s for %s: %s", error.code, sid, error.message)
    await sio.emit(
        "admin_notification",
        {"type": "warning", "message": error.message},
        to=sid,
    )


async def _apply_transition_effects(effects: TransitionEffects) -> None:
    """Deliver side effects after a transition has atomically mutated state."""
    if effects.clear_media_tokens:
        _clear_all_media_tokens()
    for message in effects.logs:
        add_log(message)
    if effects.stop_sounds:
        _supersede_sound_fade(mode="stopped")
        await emit_settings_update()
        await sio.emit("stop_sound")
    if effects.start_sound_output or effects.sounds:
        _supersede_sound_fade(mode="normal")
        await emit_settings_update()
    for sound in effects.sounds:
        await sio.emit("play_sound", {"sound": sound})
    await emit_state_update()
    if effects.clear_admin_question:
        await _clear_admin_question_for_admins()
    elif effects.refresh_admin_question:
        await _emit_current_question_to_admins()


async def _apply_live_ops_action(
    sid: str,
    action: Callable[[], TransitionEffects],
) -> dict:
    if not await require_admin(sid):
        return {"ok": False, "error": "not_admin"}
    try:
        effects = action()
    except TransitionError as error:
        await _emit_transition_error(sid, error)
        return {"ok": False, "error": error.code, "message": error.message}
    await _apply_transition_effects(effects)
    return {"ok": True}


def get_sector_from_angle(angle):
    # В GameTable: angleDeg = 90 + (i * angleStep)
    best_sector = 1
    min_diff = 360
    
    for i in range(1, SECTORS_COUNT + 1):
        sector_angle = (90 + i * ANGLE_STEP) % 360
        diff = abs(angle - sector_angle)
        if diff > 180: diff = 360 - diff 
        
        if diff < min_diff:
            min_diff = diff
            best_sector = i
            
    return best_sector

# --- ЛОГИКА ВЫБОРА УГЛА ---
def calculate_spin_result(force_sector=None, used_questions=None):
    used_questions = used_questions or []
    if force_sector:
        good_sectors = [force_sector]
        current_sector = SECTORS_COUNT if force_sector == 1 else force_sector - 1
        while current_sector in used_questions and current_sector != force_sector:
            good_sectors.append(current_sector)
            current_sector = SECTORS_COUNT if current_sector == 1 else current_sector - 1
        
        logging.info(f"Good sectors: {good_sectors}")
        chosen_sector = random.choice(good_sectors)
        center_angle = (90 + chosen_sector * ANGLE_STEP) % 360
        raw_angle = random.uniform(center_angle - ANGLE_STEP / 2, center_angle + ANGLE_STEP / 2)
    else:
        raw_angle = random.uniform(0, 360)

    return raw_angle, get_sector_from_angle(raw_angle)


async def broadcast_players(target_sid=None):
    """Рассылает список игроков. Админам полный, остальным - ничего (или кол-во)"""
    
    public_list = [
        {
            'name': p['name'], 
            'role': p['role'], 
            'online': p.get('online', False),
            'pending': p.get('pending', False)
        } 
        for p in players_list
    ]
    
    # Если нужно послать конкретному клиенту
    if target_sid:
        role = await get_client_role(target_sid)
        if role == 'admin':
            await sio.emit('players_update', {'players': public_list}, to=target_sid)
    else:
        # Рассылаем всем админам
        for p in players_list:
            if _admin_record_is_authorized(p):
                await sio.emit('players_update', {'players': public_list}, to=p['sid'])

@fastapi_app.get("/")
async def root():
    return {"message": "Сервер игры «Что? Где? Когда?» работает"}


@fastapi_app.get("/media/{media_id}")
async def get_media(media_id: str):
    _cleanup_expired_media_tokens()
    info = media_tokens.get(media_id)
    shared_media = app_state["presentation"].get("shared_media")
    is_active_shared = bool(
        shared_media and shared_media.get("media_id") == media_id
    )
    if not info or not _media_token_is_current(
        info,
        allow_expired=is_active_shared,
    ):
        media_tokens.pop(media_id, None)
        raise HTTPException(status_code=404, detail="Медиа не найдено")
    path = info.get("path")
    if not path:
        raise HTTPException(status_code=404, detail="Медиа не найдено")
    p = Path(path)
    if not p.exists() or not p.is_file():
        raise HTTPException(status_code=404, detail="Медиа не найдено")
    # Inline display
    return FileResponse(str(p))


@fastapi_app.get("/intro/author-photo/{sector}/{slot}")
async def get_intro_author_photo(sector: int, slot: int):
    if loaded_pack is None or not 1 <= sector <= 12:
        raise HTTPException(status_code=404, detail="Фото автора не найдено")
    intro = app_state["presentation"]["intro"]
    if app_state["game"]["phase"] != PHASE_INTRO or intro is None:
        raise HTTPException(status_code=404, detail="Фото автора не найдено")
    if intro["slide_index"] != sector:
        raise HTTPException(status_code=404, detail="Фото автора не найдено")

    question = loaded_pack.get_by_sector(sector)
    author_questions = question.parts or [question]
    if not 1 <= slot <= len(author_questions):
        raise HTTPException(status_code=404, detail="Фото автора не найдено")

    photo_path = author_questions[slot - 1].author_photo
    if photo_path is None or not photo_path.is_file():
        raise HTTPException(status_code=404, detail="Фото автора не найдено")
    return FileResponse(
        str(photo_path),
        headers={"Cache-Control": "no-store"},
    )

@sio.event
async def connect(sid, environ):
    logger.info(f"Client connected: {sid}")
    
    await sio.save_session(sid, {'role': 'player'})
    
    # Settings go first so a reconnecting client knows whether sound is fading
    # or stopped before a spinning wheel/shared audio is rendered from state.
    await emit_settings_update(to=sid)
    await emit_state_update(to=sid)
    await sio.emit('role_update', {'role': 'player'}, to=sid)

@sio.event
async def restore_session(sid, data):
    """Клиент отправляет токен администратора или игрока при переподключении"""
    payload = data if isinstance(data, dict) else {}
    admin_token = payload.get('token')
    player_token = payload.get('player_token')
    
    session_data = {'role': 'player'}
    
    # 1. Проверка админа
    if admin_token and validate_admin_token(admin_token):
        session_data['role'] = 'admin'
        session_data['admin_token'] = admin_token
        await sio.save_session(sid, session_data)
        logger.info(f"Session restored for {sid}: admin")
        
        # Ищем админа в списке игроков
        admin_record = next((p for p in players_list if p['role'] == 'admin'), None)
        
        if not admin_record:
            # Если админа не было в списке, добавляем
            players_list.append({'sid': sid, 'name': ADMIN_NAME, 'role': 'admin', 'token': admin_token, 'online': True})
        else:
            # Если был - обновляем SID (перехват сессии)
            if admin_record['sid'] != sid:
                logger.info(f"Admin reconnected from new SID: {sid} (old: {admin_record['sid']})")
                admin_record['sid'] = sid
            admin_record['online'] = True

        await sio.emit('role_update', {'role': 'admin'}, to=sid)
        await emit_state_update(to=sid)
        await _emit_pack_info_to_admin(sid)
        await _emit_current_question_to_admins()
        expires_at = admin_tokens.expires_at(admin_token)
        await sio.emit(
            'auth_restored',
            {
                'expires_at_ms': int(expires_at * 1000) if expires_at is not None else None,
            },
            to=sid,
        )
        await broadcast_players()
        return
    if admin_token:
        await sio.save_session(sid, session_data)
        await sio.emit('role_update', {'role': 'player'}, to=sid)
        await sio.emit(
            'auth_expired',
            {'message': 'Сессия ведущего недействительна. Введите пароль ещё раз.'},
            to=sid,
        )
        return
    
    # 2. Проверка игрока по токену
    if player_token:
        # Ищем игрока с таким токеном
        player_record = next((p for p in players_list if p.get('token') == player_token), None)
        
        if player_record:
            # Игрок найден - восстанавливаем сессию
            session_data['player_name'] = player_record['name']
            await sio.save_session(sid, session_data)
            
            # Обновляем SID (перехват)
            if player_record['sid'] != sid:
                 logger.info(f"Player {player_record['name']} reconnected from new SID: {sid} (old: {player_record['sid']})")
                 player_record['sid'] = sid
            player_record['online'] = True

            await sio.emit('role_update', {'role': 'player'}, to=sid)
            await emit_state_update(to=sid)
            if player_record.get('pending', False):
                await sio.emit('join_pending', {'name': player_record['name']}, to=sid)
            else:
                await sio.emit('join_success', {'name': player_record['name']}, to=sid)
            # Уведомляем админов об изменении статуса
            await broadcast_players()
            return
    
    # Если ничего не подошло - остаемся гостем
    await sio.emit('role_update', {'role': 'player'}, to=sid)
    await emit_state_update(to=sid)

@sio.event
async def authenticate_admin(sid, data):
    """Проверка пароля и выдача токена"""
    payload = data if isinstance(data, dict) else {}
    password = payload.get('password')

    if _admin_password_matches(password):
        previous_admins = [
            player.copy()
            for player in players_list
            if player.get('role') == 'admin'
        ]
        token = generate_admin_token()
        await sio.save_session(
            sid,
            {'role': 'admin', 'admin_token': token},
        )
        logger.info(f"Admin authenticated: {sid}")

        for previous in previous_admins:
            previous_sid = previous.get('sid')
            if previous_sid and previous_sid != sid and previous.get('online', False):
                try:
                    await sio.save_session(previous_sid, {'role': 'player'})
                except Exception:
                    pass
                await sio.emit('role_update', {'role': 'player'}, to=previous_sid)
                await sio.emit(
                    'auth_expired',
                    {'message': 'Выполнен новый вход ведущего. Войдите повторно при необходимости.'},
                    to=previous_sid,
                )
        
        # Добавляем/обновляем админа
        admin_record = next((p for p in players_list if p['role'] == 'admin'), None)
        if not admin_record:
            players_list.append({'sid': sid, 'name': ADMIN_NAME, 'role': 'admin', 'token': token, 'online': True})
            add_log("Ведущий присоединился")
        else:
             admin_record['sid'] = sid
             admin_record['token'] = token
             admin_record['online'] = True

        await broadcast_players()
        
        expires_at = admin_tokens.expires_at(token)
        await sio.emit(
            'auth_success',
            {
                'token': token,
                'expires_at_ms': int(expires_at * 1000) if expires_at is not None else None,
            },
            to=sid,
        )
        
        await sio.emit('role_update', {'role': 'admin'}, to=sid)
        await emit_state_update(to=sid)
        await _emit_pack_info_to_admin(sid)
        await _emit_current_question_to_admins()
    else:
        logger.warning(f"Failed admin auth attempt from {sid}")
        await sio.emit('auth_failed', {'message': 'Неверный пароль'}, to=sid)

@sio.event
async def join_game(sid, data):
    """Игрок вводит имя и присоединяется к игре"""
    player_name = data.get('name', '').strip()
    
    if not player_name or len(player_name) < 1:
        await sio.emit('join_failed', {'message': 'Имя не может быть пустым'}, to=sid)
        return
    
    if len(player_name) > 50:
        await sio.emit('join_failed', {'message': 'Имя слишком длинное'}, to=sid)
        return
    
    # Проверяем, не занято ли имя другим игроком
    name_taken = any(p['name'] == player_name for p in players_list)
    if name_taken:
        await sio.emit('join_failed', {'message': 'Это имя уже занято'}, to=sid)
        return
    
    # Генерируем токен для игрока
    player_token = secrets.token_urlsafe(16)

    # Сохраняем в сессии
    session = await sio.get_session(sid)
    session['player_name'] = player_name
    await sio.save_session(sid, session)
    
    # Если игра уже началась (не LOGIN), требуется одобрение админа
    needs_approval = app_state["game"]["phase"] != PHASE_LOGIN
    
    # Добавляем нового игрока
    players_list.append({
        'sid': sid, 
        'name': player_name, 
        'role': 'player', 
        'token': player_token, 
        'online': True,
        'pending': needs_approval  # Ожидает одобрения
    })
    
    if needs_approval:
        add_log(f"{player_name} ожидает одобрения")
        await broadcast_players()
        # Уведомляем админа о новом игроке
        await notify_admin('player_waiting', {'name': player_name})
        # Игроку сообщаем, что он ждёт одобрения
        await sio.emit('join_pending', {'token': player_token, 'name': player_name}, to=sid)
    else:
        add_log(f"{player_name} присоединился к игре")
        await broadcast_players()
        # Отправляем успех клиенту вместе с токеном
        await sio.emit('join_success', {'token': player_token, 'name': player_name}, to=sid)

async def notify_admin(event_type, data):
    """Отправляет уведомление всем онлайн админам"""
    for p in players_list:
        if _admin_record_is_authorized(p):
            await sio.emit('admin_notification', {'type': event_type, **data}, to=p['sid'])

@sio.event
async def admin_approve(sid, data):
    """Админ одобряет игрока"""
    if not await require_admin(sid):
        return
    
    player_name = data.get('name')
    if not player_name:
        return
    
    # Ищем pending игрока
    player = next((p for p in players_list if p['name'] == player_name and p.get('pending')), None)
    if not player:
        return
    
    # Одобряем
    player['pending'] = False
    add_log(f"{player_name} допущен к игре")
    
    await broadcast_players()
    
    # Уведомляем игрока
    await sio.emit('join_success', {'name': player_name}, to=player['sid'])

@sio.event
async def start_game(sid):
    """Админ запускает intro перед первым раундом."""
    if not await require_admin(sid):
        return
    
    try:
        effects = transition_start_game(app_state)
    except TransitionError as error:
        await _emit_transition_error(sid, error)
        return
    await _apply_transition_effects(effects)


@sio.event
async def admin_start_intro_music(sid):
    """Один раз запустить общий intro-трек по команде ведущего."""
    if not await require_admin(sid):
        return

    try:
        effects = transition_start_intro_music(app_state, now_ms=_now_ms())
    except TransitionError as error:
        await _emit_transition_error(sid, error)
        return
    await _apply_transition_effects(effects)


@sio.event
async def admin_advance_intro(sid, data):
    """Переключить ровно один intro-слайд или перейти к первому раунду."""
    if not await require_admin(sid):
        return

    payload = data if isinstance(data, dict) else {}
    try:
        effects = transition_advance_intro(
            app_state,
            expected_slide=payload.get("expected_slide"),
        )
    except TransitionError as error:
        await _emit_transition_error(sid, error)
        return
    await _apply_transition_effects(effects)

@sio.event
async def leave_game(sid):
    """Явный выход игрока (кнопка Выход). Освобождает имя."""
    global players_list

    try:
        session = await sio.get_session(sid)
    except Exception:
        session = {}
    session_admin_token = session.get("admin_token")

    player = next((p for p in players_list if p['sid'] == sid), None)
    if player:
        player_name = player['name']
        player_role = player['role']
        
        # Удаляем из списка
        players_list = [p for p in players_list if p['sid'] != sid]
        
        if player_role == 'admin':
            add_log("Ведущий вышел")
            revoke_admin_token(player.get('token'))
        else:
            add_log(f"{player_name} вышел из игры")
        
        logger.info(f"Player {player_name} left the game (explicit logout)")
        await broadcast_players()
        await emit_state_update()
    revoke_admin_token(session_admin_token)
    try:
        await sio.save_session(sid, {"role": "player"})
    except Exception:
        pass

@sio.event
async def disconnect(sid):
    logger.info(f"Client disconnected: {sid}")
    
    # Ставим offline, но НЕ удаляем (чтобы можно было переподключиться)
    player = next((p for p in players_list if p['sid'] == sid), None)
    if player:
        player['online'] = False
        await broadcast_players()

@sio.event
async def admin_spin(sid, data=None):
    if not await require_admin(sid):
        return

    force_sector = data.get('force_sector') if data else None
    try:
        validate_spin_start(app_state)
        if force_sector is not None:
            if (
                not isinstance(force_sector, int)
                or isinstance(force_sector, bool)
                or not 1 <= force_sector <= SECTORS_COUNT
            ):
                raise TransitionError("invalid_sector", f"Некорректный сектор: {force_sector}")
            if force_sector in app_state["game"]["used_questions"]:
                raise TransitionError("sector_used", f"Сектор {force_sector} уже сыгран")

        raw_angle, raw_sector = calculate_spin_result(
            force_sector,
            app_state["game"]["used_questions"],
        )
        duration = random.uniform(MIN_SPIN_DURATION, MAX_SPIN_DURATION)
        effects = transition_start_spin(
            app_state,
            raw_angle=raw_angle,
            raw_sector=raw_sector,
            duration=duration,
            forced=force_sector is not None,
        )
    except TransitionError as error:
        await _emit_transition_error(sid, error)
        return

    spin_id = effects.spin_id
    await _apply_transition_effects(effects)
    await asyncio.sleep(duration)

    try:
        effects = transition_complete_spin(app_state, spin_id=spin_id)
    except TransitionError as error:
        if error.code != "stale_spin":
            await _emit_transition_error(sid, error)
        return
    await _apply_transition_effects(effects)

@sio.event
async def admin_score(sid, data):
    if not await require_admin(sid):
        return
    winner = data.get('winner')
    try:
        effects = transition_score(
            app_state,
            winner=winner,
            correct_sound=random.choice(["yes1", "yes2"]),
            incorrect_sound=random.choice(["no1", "no2"]),
        )
    except TransitionError as error:
        await _emit_transition_error(sid, error)
        return
    await _apply_transition_effects(effects)


@sio.event
async def admin_set_score(sid, data):
    data = data if isinstance(data, dict) else {}
    return await _apply_live_ops_action(
        sid,
        lambda: live_ops_set_score(
            app_state,
            znatoki=data.get("znatoki"),
            tv=data.get("tv"),
        ),
    )


@sio.event
async def admin_set_sector_used(sid, data):
    data = data if isinstance(data, dict) else {}
    return await _apply_live_ops_action(
        sid,
        lambda: live_ops_set_sector_used(
            app_state,
            sector=data.get("sector"),
            used=data.get("used"),
        ),
    )


@sio.event
async def admin_open_round(sid, data):
    data = data if isinstance(data, dict) else {}
    return await _apply_live_ops_action(
        sid,
        lambda: live_ops_open_round(
            app_state,
            sector=data.get("sector"),
            part_index=data.get("part_index"),
        ),
    )


@sio.event
async def admin_force_phase(sid, data):
    data = data if isinstance(data, dict) else {}
    now_ms = int(time.time() * 1000)
    return await _apply_live_ops_action(
        sid,
        lambda: live_ops_force_phase(
            app_state,
            phase=data.get("phase"),
            now_ms=now_ms,
            normal_discussion_seconds=NORMAL_DISCUSSION_SECONDS,
            blitz_discussion_seconds=BLITZ_DISCUSSION_SECONDS,
        ),
    )


@sio.event
async def admin_reset_to_intro(sid, data=None):
    return await _apply_live_ops_action(
        sid,
        lambda: live_ops_reset_to_intro(app_state),
    )


@sio.event
async def admin_cancel_spin(sid, data=None):
    return await _apply_live_ops_action(
        sid,
        lambda: live_ops_cancel_spin(app_state),
    )


@sio.event
async def admin_set_timer(sid, data):
    data = data if isinstance(data, dict) else {}
    now_ms = int(time.time() * 1000)
    return await _apply_live_ops_action(
        sid,
        lambda: live_ops_set_timer(
            app_state,
            seconds=data.get("seconds"),
            now_ms=now_ms,
        ),
    )


@sio.event
async def admin_end_round(sid, data=None):
    """
    POST_ROUND handler.
    - Normal flow: POST_ROUND -> PRE_ROUND (end round), clears round context and shared media, plays gong.
    - Blitz flow: if round has advance_next_part, then POST_ROUND -> QUESTION_READING and advances to next part
      WITHOUT gong.
    """
    if not await require_admin(sid):
        return
    try:
        effects = transition_end_round(
            app_state,
            gong_sound=random.choice(["gong1", "gong2", "gong3"]),
        )
    except TransitionError as error:
        await _emit_transition_error(sid, error)
        return
    await _apply_transition_effects(effects)


@sio.event
async def admin_start_blackbox(sid, data=None):
    """Start the static black-box presentation for the active pack question."""
    if not await require_admin(sid):
        return {"ok": False, "error": "not_admin"}

    current = _get_round_ctx_and_sector()
    if current is None:
        return {"ok": False, "error": "no_round"}
    round_ctx, sector = current
    try:
        question = loaded_pack.get_by_sector(sector)
        effects = transition_start_blackbox(
            app_state,
            enabled=_effective_blackbox(question, round_ctx),
            now_ms=_now_ms(),
        )
    except TransitionError as error:
        await _emit_transition_error(sid, error)
        return {"ok": False, "error": error.code, "message": error.message}

    await _apply_transition_effects(effects)
    return {"ok": True}


@sio.event
async def admin_stop_blackbox(sid, data=None):
    """Stop only the active black-box presentation."""
    if not await require_admin(sid):
        return {"ok": False, "error": "not_admin"}
    payload = data if isinstance(data, dict) else {}
    try:
        effects = transition_end_blackbox(
            app_state,
            expected_generation=payload.get("playback_generation"),
        )
    except TransitionError as error:
        await _emit_transition_error(sid, error)
        return {"ok": False, "error": error.code, "message": error.message}

    await _apply_transition_effects(effects)
    return {"ok": True}


@sio.event
async def admin_blackbox_ended(sid, data=None):
    """Accept natural music completion only from the current host generation."""
    if not await require_admin(sid):
        return {"ok": False, "error": "not_admin"}
    payload = data if isinstance(data, dict) else {}
    try:
        effects = transition_end_blackbox(
            app_state,
            expected_generation=payload.get("playback_generation"),
            natural=True,
        )
    except TransitionError as error:
        return {"ok": False, "error": error.code}

    await _apply_transition_effects(effects)
    return {"ok": True}


def _store_current_media_token(media) -> tuple[str, dict]:
    media_id = secrets.token_urlsafe(16)
    info = create_media_token_info(
        media,
        app_state,
        expires_at=time.time() + MEDIA_TOKEN_TTL_SECONDS,
    )
    media_tokens[media_id] = info
    return media_id, info


def _create_current_shared_media(media_id: str, info: dict) -> dict:
    catalog = _get_current_media_catalog()
    has_next = next_media_in_section(catalog, info["media_ref"]) is not None
    return create_shared_media(media_id, info, has_next=has_next)


@sio.event
async def admin_resolve_media(sid, data):
    """
    Resolve an admin-only opaque media_ref to a secure media_id.
    Returns acknowledgement payload to the caller (admin).
    """
    if not await require_admin(sid):
        return {"ok": False, "error": "not_admin"}
    data = data if isinstance(data, dict) else {}

    phase = app_state["game"]["phase"]
    if phase not in (PHASE_QUESTION_READING, PHASE_DISCUSSION, PHASE_TEAM_ANSWER, PHASE_POST_ROUND):
        return {"ok": False, "error": f"bad_phase:{phase}"}
    if app_state["wheel"]["is_spinning"]:
        return {"ok": False, "error": "spinning"}
    if not app_state["game"]["round"]:
        return {"ok": False, "error": "no_round"}

    media_ref = (data.get("media_ref") or "").strip()
    if not media_ref:
        return {"ok": False, "error": "missing_media_ref"}

    media = _get_current_media_catalog().get(media_ref)
    if media is None:
        return {"ok": False, "error": "media_not_allowed"}
    if media.type not in ("image", "audio", "video"):
        return {"ok": False, "error": "unsupported_media_type"}

    # Create token bound to the current round context.
    _cleanup_expired_media_tokens()
    media_id, _info = _store_current_media_token(media)
    return {
        "ok": True,
        "media_id": media_id,
        **media.public_descriptor(),
    }


@sio.event
async def admin_share_media(sid, data):
    """Share resolved media_id to all clients (rendered instead of the table)."""
    if not await require_admin(sid):
        return {"ok": False, "error": "not_admin"}
    data = data if isinstance(data, dict) else {}
    phase = app_state["game"]["phase"]
    if phase not in (PHASE_QUESTION_READING, PHASE_DISCUSSION, PHASE_TEAM_ANSWER, PHASE_POST_ROUND):
        return {"ok": False, "error": f"bad_phase:{phase}"}
    if app_state["wheel"]["is_spinning"]:
        return {"ok": False, "error": "spinning"}
    if app_state["presentation"].get("blackbox") is not None:
        return {"ok": False, "error": "blackbox_active"}
    if not app_state["game"]["round"]:
        return {"ok": False, "error": "no_round"}

    media_id = (data.get("media_id") or "").strip()
    if not media_id:
        return {"ok": False, "error": "missing_media_id"}

    _cleanup_expired_media_tokens()
    info = media_tokens.get(media_id)
    if not info:
        await sio.emit(
            "admin_notification",
            {"type": "warning", "message": "Медиа устарело. Нажми превью ещё раз."},
            to=sid,
        )
        return {"ok": False, "error": "media_expired"}

    if not _media_token_is_current(info):
        media_tokens.pop(media_id, None)
        await sio.emit(
            "admin_notification",
            {"type": "warning", "message": "Медиа больше не относится к текущему вопросу."},
            to=sid,
        )
        return {"ok": False, "error": "media_not_current"}

    previous = app_state["presentation"].get("shared_media")
    previous_id = previous.get("media_id") if previous else None
    app_state["presentation"]["shared_media"] = _create_current_shared_media(media_id, info)
    if previous_id and previous_id != media_id:
        media_tokens.pop(previous_id, None)
    add_log(f"Медиа показано игрокам: {media_display_name(info)}")
    await emit_state_update()
    return {"ok": True}


@sio.event
async def admin_share_next_media(sid, data=None):
    """Replace shared media with the next item in the same source section."""
    if not await require_admin(sid):
        return {"ok": False, "error": "not_admin"}
    data = data if isinstance(data, dict) else {}

    phase = app_state["game"]["phase"]
    if phase not in (PHASE_QUESTION_READING, PHASE_DISCUSSION, PHASE_TEAM_ANSWER, PHASE_POST_ROUND):
        return {"ok": False, "error": f"bad_phase:{phase}"}
    if app_state["wheel"]["is_spinning"]:
        return {"ok": False, "error": "spinning"}
    if app_state["presentation"].get("blackbox") is not None:
        return {"ok": False, "error": "blackbox_active"}

    shared_media = app_state["presentation"].get("shared_media")
    expected_media_id = data.get("expected_media_id")
    if not isinstance(expected_media_id, str) or not expected_media_id:
        return {"ok": False, "error": "missing_expected_media_id"}
    if shared_media is None or shared_media.get("media_id") != expected_media_id:
        return {"ok": False, "error": "stale_current_media"}
    info = _get_current_shared_media_token_info()
    if info is None:
        return {"ok": False, "error": "no_current_media"}

    catalog = _get_current_media_catalog()
    next_media = next_media_in_section(catalog, info["media_ref"])
    if next_media is None:
        shared_media["has_next"] = False
        return {"ok": False, "error": "no_next_media"}

    next_id, next_info = _store_current_media_token(next_media)
    previous_id = shared_media["media_id"]
    app_state["presentation"]["shared_media"] = _create_current_shared_media(
        next_id,
        next_info,
    )
    media_tokens.pop(previous_id, None)
    add_log(f"Следующее медиа показано игрокам: {next_info['name']}")
    await emit_state_update()
    return {
        "ok": True,
        "media_id": next_id,
        **next_media.public_descriptor(),
    }


def _get_current_shared_media_token_info() -> Optional[dict]:
    shared_media = app_state["presentation"].get("shared_media")
    if not shared_media:
        return None
    media_id = shared_media.get("media_id")
    info = media_tokens.get(media_id)
    if not info or not _media_token_is_current(info, allow_expired=True):
        return None
    if info.get("media_ref") != shared_media.get("media_ref"):
        return None
    return info


async def _admin_media_playback_action(sid: str, action: str) -> None:
    if not await require_admin(sid):
        return

    shared_media = app_state["presentation"].get("shared_media")
    info = _get_current_shared_media_token_info()
    if shared_media is None or info is None:
        app_state["presentation"]["shared_media"] = None
        await sio.emit(
            "admin_notification",
            {"type": "warning", "message": "Сначала покажи актуальное медиа игрокам."},
            to=sid,
        )
        await emit_state_update()
        return

    try:
        if action == "play":
            changed = play_shared_media(
                shared_media,
                now_ms=int(time.time() * 1000),
            )
        elif action == "pause":
            changed = pause_shared_media(
                shared_media,
                now_ms=int(time.time() * 1000),
            )
        elif action == "stop":
            changed = stop_shared_media(shared_media)
        else:
            raise ValueError(f"Unknown media playback action: {action}")
    except MediaPlaybackError:
        await sio.emit(
            "admin_notification",
            {"type": "warning", "message": "Это медиа нельзя воспроизводить."},
            to=sid,
        )
        return

    # Any valid explicit playback command supersedes an older global fade, even
    # when the requested media state was already active. A Play restores sound;
    # Pause/Stop cancel pending all-sound completion without globally muting
    # unrelated game sounds.
    _supersede_sound_fade(mode="normal")
    await emit_settings_update()
    if changed:
        labels = {"play": "запущено", "pause": "на паузе", "stop": "остановлено"}
        add_log(f"Медиа {labels[action]}: {media_display_name(info)}")
        await emit_state_update()


@sio.event
async def admin_play_media(sid, data=None):
    await _admin_media_playback_action(sid, "play")


@sio.event
async def admin_pause_media(sid, data=None):
    await _admin_media_playback_action(sid, "pause")


@sio.event
async def admin_stop_media(sid, data=None):
    await _admin_media_playback_action(sid, "stop")


@sio.event
async def admin_media_ended(sid, data):
    """Accept natural completion from the host for the current play generation."""
    if not await require_admin(sid):
        return {"ok": False, "error": "not_admin"}
    data = data if isinstance(data, dict) else {}

    media_id = data.get("media_id")
    generation = data.get("playback_generation")
    if not isinstance(media_id, str) or not media_id:
        return {"ok": False, "error": "missing_media_id"}
    if not isinstance(generation, int) or isinstance(generation, bool) or generation < 0:
        return {"ok": False, "error": "invalid_generation"}

    shared_media = app_state["presentation"].get("shared_media")
    if shared_media is None or shared_media.get("media_id") != media_id:
        return {"ok": False, "error": "stale_media"}
    info = _get_current_shared_media_token_info()
    if info is None:
        return {"ok": False, "error": "media_not_current"}

    try:
        changed = complete_shared_media(
            shared_media,
            expected_generation=generation,
        )
    except MediaPlaybackError:
        return {"ok": False, "error": "unsupported_media_type"}
    if not changed:
        return {"ok": False, "error": "stale_playback"}

    add_log(f"Медиа завершено: {media_display_name(info)}")
    await emit_state_update()
    return {"ok": True}


@sio.event
async def admin_hide_media(sid, data=None):
    """Hide shared media for all clients."""
    if not await require_admin(sid):
        return {"ok": False, "error": "not_admin"}
    shared_media = app_state["presentation"].get("shared_media")
    app_state["presentation"]["shared_media"] = None
    if shared_media:
        media_tokens.pop(shared_media.get("media_id"), None)
    add_log("Медиа скрыто")
    await emit_state_update()
    return {"ok": True}


@sio.event
async def admin_start_discussion(sid, data=None):
    """Переход QUESTION_READING -> DISCUSSION."""
    if not await require_admin(sid):
        return
    round_ctx = app_state["game"]["round"] or {}
    kind = round_ctx.get("kind", "normal")
    seconds = BLITZ_DISCUSSION_SECONDS if kind in ("blitz", "superblitz") else NORMAL_DISCUSSION_SECONDS
    deadline_ms = int(time.time() * 1000) + seconds * 1000
    try:
        effects = transition_start_discussion(app_state, deadline_ms=deadline_ms)
    except TransitionError as error:
        await _emit_transition_error(sid, error)
        return
    await _apply_transition_effects(effects)


@sio.event
async def admin_team_answer(sid, data=None):
    """Переход DISCUSSION -> TEAM_ANSWER."""
    if not await require_admin(sid):
        return
    try:
        effects = transition_team_answer(app_state)
    except TransitionError as error:
        await _emit_transition_error(sid, error)
        return
    await _apply_transition_effects(effects)


@sio.event
async def admin_ten_seconds(sid, data=None):
    """
    Force 10 seconds left: play warning signal to everyone and reset timer to 10 seconds.
    Allowed only in DISCUSSION.
    """
    if not await require_admin(sid):
        return
    deadline_ms = int(time.time() * 1000) + TEN_SECONDS * 1000
    try:
        effects = transition_ten_seconds(app_state, deadline_ms=deadline_ms)
    except TransitionError as error:
        await _emit_transition_error(sid, error)
        return
    await _apply_transition_effects(effects)

@sio.event
async def admin_sound(sid, data):
    if not await require_admin(sid):
        return
    
    _supersede_sound_fade(mode="normal")
    add_log(f"Звук: {sound_label(data.get('sound'))}")
    await emit_settings_update()
    await sio.emit('play_sound', data)

@sio.event
async def admin_volume(sid, data):
    if not await require_admin(sid):
        return
    
    try:
        vol = float(data.get('volume', 1.0))
        vol = max(0.0, min(1.0, vol))
        global_settings["volume"] = vol
        await emit_settings_update()
    except ValueError:
        pass

@sio.event
async def admin_stop_sounds(sid):
    if not await require_admin(sid):
        return

    media_stopped = False
    try:
        media_stopped = stop_shared_media(
            app_state["presentation"].get("shared_media")
        )
    except MediaPlaybackError:
        pass
    blackbox_stopped = clear_blackbox_presentation(app_state)

    _supersede_sound_fade(mode="stopped")
    add_log("Звук остановлен")
    await emit_settings_update()
    await sio.emit('stop_sound')
    if media_stopped or blackbox_stopped:
        await emit_state_update()


@sio.event
async def admin_fade_sounds(sid, data=None):
    if not await require_admin(sid):
        return {"ok": False, "error": "not_admin"}

    generation = begin_fade(
        global_settings["sound_control"],
        now_ms=_now_ms(),
        duration_ms=FADE_DURATION_MS,
    )
    add_log("Затухание звука: 3 сек.")
    await emit_settings_update()
    await emit_state_update()
    await asyncio.sleep(FADE_DURATION_MS / 1000)

    # A later Play, Stop, Silence, spin, effect, or Fade advances generation.
    # The obsolete coroutine must not stop any sound from that later command.
    if not complete_fade(
        global_settings["sound_control"],
        generation=generation,
    ):
        return {"ok": True, "completed": False}

    media_stopped = False
    try:
        media_stopped = stop_shared_media(
            app_state["presentation"].get("shared_media")
        )
    except MediaPlaybackError:
        pass
    blackbox_stopped = clear_blackbox_presentation(app_state)

    await sio.emit("stop_sound")
    await emit_settings_update()
    if media_stopped or blackbox_stopped:
        await emit_state_update()
    return {"ok": True, "completed": True}

@sio.event
async def admin_kick(sid, data):
    """Админ отключает игрока"""
    global players_list
    
    if not await require_admin(sid):
        return
    
    player_name = data.get('name')
    if not player_name:
        return
    
    # Ищем игрока по имени (не админа)
    player = next((p for p in players_list if p['name'] == player_name and p['role'] != 'admin'), None)
    if not player:
        return
    
    player_sid = player['sid']
    
    # Удаляем из списка
    players_list = [p for p in players_list if p['name'] != player_name or p['role'] == 'admin']
    
    add_log(f"{player_name} был отключён ведущим")
    logger.info(f"Player {player_name} kicked by admin")
    
    # Отправляем игроку событие что его кикнули
    # Не отключаем сокет программно — пусть клиент сам переподключится
    await sio.emit('kicked', {'message': 'Вы были отключены ведущим'}, to=player_sid)
    
    await broadcast_players()

@sio.event
async def admin_log(sid, data):
    if not await require_admin(sid):
        return
    
    msg = data.get('message')
    if msg:
        add_log(msg)
        await emit_state_update()

@sio.event
async def admin_reset(sid):
    if not await require_admin(sid):
        return

    effects = transition_reset(app_state)
    await _apply_transition_effects(effects)
