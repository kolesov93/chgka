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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEBUG = True
MIN_SPIN_DURATION = 5.0 if DEBUG else 10.0
MAX_SPIN_DURATION = 10.0 if DEBUG else 20.0
SECTORS_COUNT = 13
ANGLE_STEP = 360 / SECTORS_COUNT
ADMIN_NAME = 'Господин Ведущий'
BLITZ_PARTS = 3
NORMAL_DISCUSSION_SECONDS = 60
BLITZ_DISCUSSION_SECONDS = 20
TEN_SECONDS = 10

# Game phases
PHASE_LOGIN = "LOGIN"
PHASE_PRE_ROUND = "PRE_ROUND"
PHASE_QUESTION_READING = "QUESTION_READING" 
PHASE_DISCUSSION = "DISCUSSION"
PHASE_TEAM_ANSWER = "TEAM_ANSWER"
PHASE_POST_ROUND = "POST_ROUND"

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
game_state = {
    "phase": PHASE_LOGIN,
    "score": {"znatoki": 0, "tv": 0},
    "current_sector": 1, 
    "target_angle": None, # Точный угол остановки (0-360)
    "playing_sector": None, # Какой сектор реально играет (с учетом скачки)
    "spin_duration": 0,
    "used_questions": [], 
    "is_spinning": False,
    "logs": [], # Лог событий ["12:00:01 - Игра началась", ...]
    # Loaded from question pack at startup (len=13), values: "normal" | "blitz" | "superblitz"
    "question_types": None,
    # Discussion timer deadline (unix ms). Can go negative on the client; that's OK.
    "discussion_deadline_ms": None,
    # Current round context (safe to send to all clients; no question text here)
    # Example:
    #   {"kind":"normal","sector":5}
    #   {"kind":"blitz","sector":4,"part_index":0}
    "round": None,
    # Shared media shown to all clients (rendered instead of the table on frontend)
    # Example: {"type":"image","media_id":"..."}
    "shared_media": None,
}

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
    round_ctx = game_state.get("round")
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
    Load questions pack once at startup and expose per-sector question types via game_state.
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

    game_state["question_types"] = types
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
        "phase": game_state.get("phase"),
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
    game_state["logs"].insert(0, log_entry) # Новые сверху
    # Ограничим размер лога
    if len(game_state["logs"]) > 50:
        game_state["logs"] = game_state["logs"][:50]
    return log_entry

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
def calculate_spin_result(force_sector=None, used_questions = []):
    if force_sector:
        good_sectors = [force_sector] 
        current_sector = (force_sector + SECTORS_COUNT - 1) % SECTORS_COUNT
        while current_sector in used_questions and current_sector != force_sector:
            good_sectors.append(current_sector)
            current_sector = (current_sector - 1 + SECTORS_COUNT) % SECTORS_COUNT
        
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
    
    await sio.emit('state_update', game_state, to=sid)
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
        await sio.emit('state_update', game_state, to=sid)
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
            await sio.emit('state_update', game_state, to=sid)
            # Отправляем join_success, чтобы фронт понял, что он в игре
            await sio.emit('join_success', {'name': player_record['name']}, to=sid)
            # Уведомляем админов об изменении статуса
            await broadcast_players()
            return
    
    # Если ничего не подошло - остаемся гостем
    await sio.emit('role_update', {'role': 'player'}, to=sid)
    await sio.emit('state_update', game_state, to=sid)

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
        await sio.emit('state_update', game_state, to=sid)
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
    needs_approval = game_state['phase'] != PHASE_LOGIN
    
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
    
    if game_state['phase'] != PHASE_LOGIN:
        logger.warning(f"Attempt to start game in wrong phase: {game_state['phase']}")
        return
    
    game_state['phase'] = PHASE_PRE_ROUND
    add_log("Игра началась!")
    await sio.emit('state_update', game_state)

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
        await sio.emit('state_update', game_state)

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

    if game_state["is_spinning"]:
        return

    if game_state.get("phase") != PHASE_PRE_ROUND:
        await sio.emit(
            "admin_notification",
            {
                "type": "warning",
                "message": f"Нельзя крутить волчок в фазе {game_state.get('phase')}",
            },
            to=sid,
        )
        return

    # Ensure any previously shared media is hidden when we start a new spin.
    game_state["shared_media"] = None
    _clear_all_media_tokens()
    
    if game_state["score"]["znatoki"] >= 6 or game_state["score"]["tv"] >= 6:
        return

    # 1. Генерируем результат
    raw_angle, raw_sector = calculate_spin_result(force_sector, game_state["used_questions"])
    
    # 2. Определяем играющий сектор (Скачка)
    playing_sector = raw_sector
    
    # Защита от бесконечного цикла (если все сыграны)
    loop_check = 0
    while playing_sector in game_state["used_questions"] and loop_check < SECTORS_COUNT + 1:
        playing_sector += 1
        if playing_sector > 13:
            playing_sector = 1
        loop_check += 1
            
    duration = random.uniform(MIN_SPIN_DURATION, MAX_SPIN_DURATION)

    log_msg = f"Вращение! Угол: {raw_angle:.1f}° (Сектор {raw_sector})"
    if force_sector:
        log_msg += " [FORCED]"
    log_msg += f" -> Играет: {playing_sector}"
    add_log(log_msg)

    game_state["target_angle"] = raw_angle
    game_state["playing_sector"] = playing_sector
    game_state["spin_duration"] = duration
    game_state["is_spinning"] = True
    
    if playing_sector == SECTORS_COUNT:
        add_log("Внимание! 13-й сектор!")
    
    await sio.emit('state_update', game_state)

    await asyncio.sleep(duration)

    game_state["is_spinning"] = False
    game_state["current_sector"] = playing_sector
    game_state["spin_duration"] = 0
    game_state["used_questions"].append(playing_sector)

    game_state["phase"] = PHASE_QUESTION_READING
    add_log("Фаза: зачитывание вопроса")

    # Initialize round context based on question type
    qtypes = game_state.get("question_types") or []
    qtype = qtypes[playing_sector - 1] if len(qtypes) >= playing_sector else "normal"
    if qtype in ("blitz", "superblitz"):
        game_state["round"] = {"kind": qtype, "sector": playing_sector, "part_index": 0}
    else:
        game_state["round"] = {"kind": "normal", "sector": playing_sector}
    game_state["discussion_deadline_ms"] = None
    
    if playing_sector == 13:
        await sio.emit('play_sound', {'sound': 'sector13'})

    await sio.emit('state_update', game_state)
    await _emit_current_question_to_admins()

@sio.event
async def admin_score(sid, data):
    if not await require_admin(sid):
        return
    
    # Начисление очков / подтверждение ответа разрешаем только в фазе ответа команды
    if game_state.get("phase") != PHASE_TEAM_ANSWER:
        await sio.emit(
            "admin_notification",
            {"type": "warning", "message": f"Нельзя нажимать верно/очки в фазе {game_state.get('phase')}"},
            to=sid,
        )
        return

    round_ctx = game_state.get("round") or {"kind": "normal"}
    kind = round_ctx.get("kind", "normal")
    winner = data.get('winner')

    # Blitz / superblitz:
    # - any wrong answer ends the round immediately (TV +1)
    # - correct answers in part 1/2 advance to next part WITHOUT sounds/scores
    # - correct answer in part 3 gives Znatoki +1 (normal scoring)
    if kind in ("blitz", "superblitz"):
        part_index = int(round_ctx.get("part_index", 0))

        if winner == "tv":
            game_state["score"]["tv"] += 1
            add_log("Неверно. Очко Телезрителям!")
            await sio.emit("play_sound", {"sound": random.choice(["no1", "no2"])})
            game_state["discussion_deadline_ms"] = None
            game_state["phase"] = PHASE_POST_ROUND
            add_log("Фаза: послераунд (обсуждение ответа)")
            await sio.emit('state_update', game_state)
            await _emit_current_question_to_admins()
            return

        if winner != "znatoki":
            return

        # Parts 1/2: go to POST_ROUND, then advance to the next part on explicit admin action.
        if part_index < BLITZ_PARTS - 1:
            # We need an explicit flag here; we cannot infer it later from part_index alone
            # (wrong answers in parts 1/2 must NOT advance).
            round_ctx["advance_next_part"] = True
            game_state["round"] = round_ctx
            game_state["discussion_deadline_ms"] = None
            game_state["phase"] = PHASE_POST_ROUND
            add_log(f"Верно (часть {part_index + 1}/{BLITZ_PARTS}). Фаза: послераунд")
            await sio.emit('state_update', game_state)
            await _emit_current_question_to_admins()
            return

        # Last part correct -> Znatoki +1
        game_state["score"]["znatoki"] += 1
        add_log("Все ответы верны. Очко Знатокам!")
        await sio.emit("play_sound", {"sound": random.choice(["yes1", "yes2"])})
        game_state["discussion_deadline_ms"] = None
        game_state["phase"] = PHASE_POST_ROUND
        add_log("Фаза: послераунд (обсуждение ответа)")
        await sio.emit('state_update', game_state)
        await _emit_current_question_to_admins()
        return

    # Normal scoring
    if winner == 'znatoki':
        game_state["score"]["znatoki"] += 1
        add_log("Очко Знатокам!")
        await sio.emit("play_sound", {"sound": random.choice(["yes1", "yes2"])})
    elif winner == 'tv':
        game_state["score"]["tv"] += 1
        add_log("Очко Телезрителям!")
        await sio.emit("play_sound", {"sound": random.choice(["no1", "no2"])})
    else:
        return

    game_state["discussion_deadline_ms"] = None
    game_state["phase"] = PHASE_POST_ROUND
    add_log("Фаза: послераунд (обсуждение ответа)")
    await sio.emit('state_update', game_state)
    await _emit_current_question_to_admins()


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
    if game_state.get("phase") != PHASE_POST_ROUND:
        await sio.emit(
            "admin_notification",
            {"type": "warning", "message": f"Нельзя завершить раунд в фазе {game_state.get('phase')}"},
            to=sid,
        )
        return

    # Blitz intermediate part: advance to next part instead of ending the round.
    round_ctx = game_state.get("round") or {}
    kind = round_ctx.get("kind", "normal")
    if kind in ("blitz", "superblitz") and round_ctx.get("advance_next_part") is True:
        part_index = int(round_ctx.get("part_index", 0))
        next_part_index = part_index + 1
        # Hide shared media and drop media tokens (bound to current part).
        game_state["shared_media"] = None
        _clear_all_media_tokens()
        game_state["discussion_deadline_ms"] = None

        round_ctx["part_index"] = next_part_index
        round_ctx.pop("advance_next_part", None)
        game_state["round"] = round_ctx
        game_state["phase"] = PHASE_QUESTION_READING
        add_log(f"Переходим к части {next_part_index + 1}/{BLITZ_PARTS}. Фаза: зачитывание вопроса")
        await sio.emit("state_update", game_state)
        await _emit_current_question_to_admins()
        return

    # Hide shared media and drop media tokens (they are tied to the round context).
    game_state["shared_media"] = None
    _clear_all_media_tokens()

    # Clear timers and round context.
    game_state["discussion_deadline_ms"] = None
    game_state["round"] = None

    # Phase transition.
    game_state["phase"] = PHASE_PRE_ROUND
    add_log("Раунд завершён. Фаза: ожидание следующего вращения")

    # Gong at the end of post-round (same for all clients).
    await sio.emit("play_sound", {"sound": random.choice(["gong1", "gong2", "gong3"])})

    await sio.emit("state_update", game_state)


@sio.event
async def admin_resolve_media(sid, data):
    """
    Resolve a markdown media path to a secure media_id for preview/share.
    Returns acknowledgement payload to the caller (admin).
    """
    if not await require_admin(sid):
        return {"ok": False, "error": "not_admin"}

    phase = game_state.get("phase")
    if phase not in (PHASE_QUESTION_READING, PHASE_DISCUSSION, PHASE_TEAM_ANSWER, PHASE_POST_ROUND):
        return {"ok": False, "error": f"bad_phase:{phase}"}
    if game_state.get("is_spinning"):
        return {"ok": False, "error": "spinning"}
    if not game_state.get("round"):
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
    phase = game_state.get("phase")
    if phase not in (PHASE_QUESTION_READING, PHASE_DISCUSSION, PHASE_TEAM_ANSWER, PHASE_POST_ROUND):
        return
    if game_state.get("is_spinning"):
        return
    if not game_state.get("round"):
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

    game_state["shared_media"] = {"type": info.get("type", "image"), "media_id": media_id}
    add_log("Медиа показано игрокам")
    await sio.emit("state_update", game_state)


@sio.event
async def admin_hide_media(sid, data=None):
    """Hide shared media for all clients."""
    if not await require_admin(sid):
        return
    game_state["shared_media"] = None
    add_log("Медиа скрыто")
    await sio.emit("state_update", game_state)


@sio.event
async def admin_start_discussion(sid, data=None):
    """Переход QUESTION_READING -> DISCUSSION."""
    if not await require_admin(sid):
        return
    if game_state.get("phase") != PHASE_QUESTION_READING:
        return
    game_state["phase"] = PHASE_DISCUSSION
    round_ctx = game_state.get("round") or {}
    kind = round_ctx.get("kind", "normal")
    seconds = BLITZ_DISCUSSION_SECONDS if kind in ("blitz", "superblitz") else NORMAL_DISCUSSION_SECONDS
    game_state["discussion_deadline_ms"] = int(time.time() * 1000) + seconds * 1000
    add_log("Фаза: обсуждение")
    await sio.emit('state_update', game_state)


@sio.event
async def admin_team_answer(sid, data=None):
    """Переход DISCUSSION -> TEAM_ANSWER."""
    if not await require_admin(sid):
        return
    if game_state.get("phase") != PHASE_DISCUSSION:
        return
    # Stop discussion timer and play signal for everyone
    game_state["discussion_deadline_ms"] = None
    await sio.emit("play_sound", {"sound": "sig1"})
    game_state["phase"] = PHASE_TEAM_ANSWER
    add_log("Фаза: ответ команды")
    await sio.emit('state_update', game_state)


@sio.event
async def admin_ten_seconds(sid, data=None):
    """
    Force 10 seconds left: play warning signal to everyone and reset timer to 10 seconds.
    Allowed only in DISCUSSION.
    """
    if not await require_admin(sid):
        return
    if game_state.get("phase") != PHASE_DISCUSSION:
        await sio.emit(
            "admin_notification",
            {"type": "warning", "message": f"Эта команда доступна только в фазе {PHASE_DISCUSSION}"},
            to=sid,
        )
        return
    game_state["discussion_deadline_ms"] = int(time.time() * 1000) + TEN_SECONDS * 1000
    await sio.emit("play_sound", {"sound": "sig2"})
    add_log("Сигнал: 10 секунд (таймер сброшен на 10)")
    await sio.emit('state_update', game_state)

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
        await sio.emit('state_update', game_state)

@sio.event
async def admin_reset(sid):
    if not await require_admin(sid):
        return
    
    game_state["used_questions"] = []
    game_state["score"] = {"znatoki": 0, "tv": 0}
    game_state["spin_duration"] = 0
    game_state["is_spinning"] = False
    game_state["current_sector"] = 1
    game_state["target_angle"] = None
    game_state["playing_sector"] = None
    game_state["discussion_deadline_ms"] = None
    game_state["round"] = None
    game_state["phase"] = "INTRO"
    game_state["logs"] = []
    add_log("Игра сброшена")
    await sio.emit('state_update', game_state)
