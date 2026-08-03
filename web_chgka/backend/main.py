import socketio
import random
import asyncio
import logging
import secrets
import os
import time
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from questions import parse_question_pack, QuestionParseError, QuestionPack
from state import (
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
    transition_complete_spin,
    transition_end_round,
    transition_reset,
    transition_score,
    transition_start_discussion,
    transition_start_game,
    transition_start_spin,
    transition_team_answer,
    transition_ten_seconds,
    validate_spin_start,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEBUG = True
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

sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Load question pack once when the app starts.
    _load_question_pack_on_startup()
    yield


fastapi_app = FastAPI(lifespan=lifespan)

fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)

# --- СИСТЕМА АВТОРИЗАЦИИ ---
# Хранилище активных админских токенов (в памяти)
# В продакшене можно использовать Redis для персистентности
admin_tokens = {}  # {token: True}

def generate_admin_token():
    """Генерирует безопасный токен для админа"""
    token = secrets.token_urlsafe(32)
    admin_tokens[token] = True
    logger.info(f"Generated admin token (total active: {len(admin_tokens)})")
    return token

def validate_admin_token(token):
    """Проверяет, валиден ли токен"""
    return token is not None and token in admin_tokens

async def get_client_role(sid):
    """Получает роль клиента из сессии Socket.IO"""
    try:
        session = await sio.get_session(sid)
        return session.get('role', 'player')
    except:
        return 'player'

async def require_admin(sid):
    """Проверяет, является ли клиент админом. Возвращает True/False"""
    role = await get_client_role(sid)
    if role != 'admin':
        logger.warning(f"Unauthorized admin action attempt from {sid} (role: {role})")
        return False
    return True

global_settings = {
    "volume": 1.0
}

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


def _cleanup_expired_media_tokens(now_ts: Optional[float] = None) -> None:
    now = now_ts if now_ts is not None else time.time()
    expired = [mid for mid, info in media_tokens.items() if info.get("expires_at", 0) <= now]
    for mid in expired:
        media_tokens.pop(mid, None)


def _clear_all_media_tokens() -> None:
    media_tokens.clear()


def _current_round_key() -> Optional[tuple[int, str, int]]:
    """
    Return a stable key for the current round context:
      (sector, kind, part_index)
    For normal questions part_index is always 0.
    """
    res = _get_round_ctx_and_sector()
    if not res:
        return None
    round_ctx, sector = res
    kind, part_index = _get_round_kind_and_part_index(round_ctx)
    return (sector, kind, part_index)


def _get_current_questions_for_media() -> list:
    """
    Return a list of Question objects whose media are allowed to be shown
    for the current round context.
    For blitz: includes both intro (top-level) and the current part.
    """
    res = _get_round_ctx_and_sector()
    if not res:
        return []
    round_ctx, sector = res
    try:
        q = loaded_pack.get_by_sector(sector)
    except Exception:
        return []
    kind, _part_index = _get_round_kind_and_part_index(round_ctx)
    if kind in ("blitz", "superblitz"):
        part_index = int(round_ctx.get("part_index", 0))
        part = q.parts[part_index] if 0 <= part_index < len(q.parts) else None
        out = [q]
        if part is not None:
            out.append(part)
        return out
    return [q]


def _resolve_media_path_to_abs(rel_path: str) -> Optional[Path]:
    """
    Given a relative media path from markdown (e.g. 'media/img.png'),
    resolve it to an absolute Path within the *current round* question folder.
    Returns None if not allowed / not found.
    """
    res = _get_round_ctx_and_sector()
    if not res:
        return None
    round_ctx, sector = res

    # Allowed absolute media paths from parsed pack for current question context
    allowed_abs: set[Path] = set()
    for qq in _get_current_questions_for_media():
        for m in getattr(qq, "media", []) or []:
            allowed_abs.add(Path(m.path))

    rel = Path(rel_path)
    if rel.is_absolute() or ".." in rel.parts:
        return None

    kind, part_index_norm = _get_round_kind_and_part_index(round_ctx)
    base_candidates: list[Path] = []
    base_candidates.append(Path(loaded_pack.path) / f"{sector:02d}")
    if kind in ("blitz", "superblitz"):
        base_candidates.append(Path(loaded_pack.path) / f"{sector:02d}" / f"{part_index_norm + 1:02d}")

    for base in base_candidates:
        try:
            cand = (base / rel).resolve()
        except Exception:
            continue
        if cand in allowed_abs and cand.exists() and cand.is_file():
            return cand
    return None

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
    loaded_pack = pack
    pack_admin_info = {
        "path": str(pack.path),
        "question_titles": [q.title for q in pack.questions],
        "question_types": types,
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

    for p in players_list:
        if p.get("role") == "admin" and p.get("online", False):
            await sio.emit("admin_question", payload, to=p["sid"])


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
    for sound in effects.sounds:
        await sio.emit("play_sound", {"sound": sound})
    await emit_state_update()
    if effects.refresh_admin_question:
        await _emit_current_question_to_admins()

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
            if p['role'] == 'admin' and p.get('online', False):
                await sio.emit('players_update', {'players': public_list}, to=p['sid'])

@fastapi_app.get("/")
async def root():
    return {"message": "CHGKA Game Server is running"}


@fastapi_app.get("/media/{media_id}")
async def get_media(media_id: str):
    _cleanup_expired_media_tokens()
    info = media_tokens.get(media_id)
    if not info:
        raise HTTPException(status_code=404, detail="Media not found")
    path = info.get("path")
    if not path:
        raise HTTPException(status_code=404, detail="Media not found")
    p = Path(path)
    if not p.exists() or not p.is_file():
        raise HTTPException(status_code=404, detail="Media not found")
    # Inline display
    return FileResponse(str(p))

@sio.event
async def connect(sid, environ):
    logger.info(f"Client connected: {sid}")
    
    await sio.save_session(sid, {'role': 'player'})
    
    await emit_state_update(to=sid)
    await sio.emit('role_update', {'role': 'player'}, to=sid)
    await sio.emit('settings_update', global_settings, to=sid)

@sio.event
async def restore_session(sid, data):
    """Клиент отправляет токен администратора или игрока при переподключении"""
    admin_token = data.get('token')
    player_token = data.get('player_token')
    
    session_data = {'role': 'player'}
    
    # 1. Проверка админа
    if admin_token and validate_admin_token(admin_token):
        session_data['role'] = 'admin'
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
        await sio.emit('auth_restored', {}, to=sid)
        await broadcast_players()
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
    password = data.get('password')
    correct_password = os.getenv('ADMIN_PASSWORD', 'admin123')
    
    if password == correct_password:
        token = generate_admin_token()
        await sio.save_session(sid, {'role': 'admin'})
        logger.info(f"Admin authenticated: {sid}")
        
        # Добавляем/обновляем админа
        admin_record = next((p for p in players_list if p['role'] == 'admin'), None)
        if not admin_record:
            players_list.append({'sid': sid, 'name': ADMIN_NAME, 'role': 'admin', 'token': token, 'online': True})
            add_log("Администратор присоединился")
        else:
             admin_record['sid'] = sid
             admin_record['token'] = token
             admin_record['online'] = True

        await broadcast_players()
        
        await sio.emit('auth_success', {'token': token}, to=sid)
        
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
        if p['role'] == 'admin' and p.get('online', False):
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
    """Админ запускает игру (переход из LOGIN в PRE_ROUND)"""
    if not await require_admin(sid):
        return
    
    try:
        effects = transition_start_game(app_state)
    except TransitionError as error:
        await _emit_transition_error(sid, error)
        return
    await _apply_transition_effects(effects)

@sio.event
async def leave_game(sid):
    """Явный выход игрока (кнопка Выход). Освобождает имя."""
    global players_list
    
    player = next((p for p in players_list if p['sid'] == sid), None)
    if player:
        player_name = player['name']
        player_role = player['role']
        
        # Удаляем из списка
        players_list = [p for p in players_list if p['sid'] != sid]
        
        if player_role == 'admin':
            add_log("Администратор вышел")
            # Инвалидируем токен админа (если хранили)
            token = player.get('token')
            if token and token in admin_tokens:
                del admin_tokens[token]
        else:
            add_log(f"{player_name} вышел из игры")
        
        logger.info(f"Player {player_name} left the game (explicit logout)")
        await broadcast_players()
        await emit_state_update()

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
async def admin_resolve_media(sid, data):
    """
    Resolve a markdown media path to a secure media_id for preview/share.
    Returns acknowledgement payload to the caller (admin).
    """
    if not await require_admin(sid):
        return {"ok": False, "error": "not_admin"}

    phase = app_state["game"]["phase"]
    if phase not in (PHASE_QUESTION_READING, PHASE_DISCUSSION, PHASE_TEAM_ANSWER, PHASE_POST_ROUND):
        return {"ok": False, "error": f"bad_phase:{phase}"}
    if app_state["wheel"]["is_spinning"]:
        return {"ok": False, "error": "spinning"}
    if not app_state["game"]["round"]:
        return {"ok": False, "error": "no_round"}

    media_type = (data.get("media_type") or "").strip().lower()
    media_path = (data.get("media_path") or "").strip()
    if media_type != "image":
        return {"ok": False, "error": "unsupported_media_type"}
    if not media_path:
        return {"ok": False, "error": "missing_media_path"}

    abs_path = _resolve_media_path_to_abs(media_path)
    if abs_path is None:
        return {"ok": False, "error": "media_not_allowed"}

    # Create token bound to the current round context.
    _cleanup_expired_media_tokens()
    media_id = secrets.token_urlsafe(16)
    media_tokens[media_id] = {
        "path": str(abs_path),
        "type": media_type,
        "round_key": _current_round_key(),
        "expires_at": time.time() + MEDIA_TOKEN_TTL_SECONDS,
    }
    return {"ok": True, "media_id": media_id, "type": media_type}


@sio.event
async def admin_share_media(sid, data):
    """Share resolved media_id to all clients (rendered instead of the table)."""
    if not await require_admin(sid):
        return
    phase = app_state["game"]["phase"]
    if phase not in (PHASE_QUESTION_READING, PHASE_DISCUSSION, PHASE_TEAM_ANSWER, PHASE_POST_ROUND):
        return
    if app_state["wheel"]["is_spinning"]:
        return
    if not app_state["game"]["round"]:
        return

    media_id = (data.get("media_id") or "").strip()
    if not media_id:
        return

    _cleanup_expired_media_tokens()
    info = media_tokens.get(media_id)
    if not info:
        await sio.emit(
            "admin_notification",
            {"type": "warning", "message": "Медиа устарело. Нажми превью ещё раз."},
            to=sid,
        )
        return

    if info.get("round_key") != _current_round_key():
        await sio.emit(
            "admin_notification",
            {"type": "warning", "message": "Это медиа относится к другому раунду."},
            to=sid,
        )
        return

    app_state["presentation"]["shared_media"] = {"type": info.get("type", "image"), "media_id": media_id}
    add_log("Медиа показано игрокам")
    await emit_state_update()


@sio.event
async def admin_hide_media(sid, data=None):
    """Hide shared media for all clients."""
    if not await require_admin(sid):
        return
    app_state["presentation"]["shared_media"] = None
    add_log("Медиа скрыто")
    await emit_state_update()


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
    
    add_log(f"Звук: {data.get('sound')}")
    await sio.emit('play_sound', data)

@sio.event
async def admin_volume(sid, data):
    if not await require_admin(sid):
        return
    
    try:
        vol = float(data.get('volume', 1.0))
        vol = max(0.0, min(1.0, vol))
        global_settings["volume"] = vol
        await sio.emit('settings_update', global_settings)
    except ValueError:
        pass

@sio.event
async def admin_stop_sounds(sid):
    if not await require_admin(sid):
        return
    
    add_log("Звук остановлен")
    await sio.emit('stop_sound')

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
    
    add_log(f"{player_name} был отключён администратором")
    logger.info(f"Player {player_name} kicked by admin")
    
    # Отправляем игроку событие что его кикнули
    # Не отключаем сокет программно — пусть клиент сам переподключится
    await sio.emit('kicked', {'message': 'Вы были отключены администратором'}, to=player_sid)
    
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
