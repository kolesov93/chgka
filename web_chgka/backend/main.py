import socketio
import random
import asyncio
import logging
import secrets
import os
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEBUG = True
MIN_SPIN_DURATION = 5.0 if DEBUG else 10.0
MAX_SPIN_DURATION = 10.0 if DEBUG else 20.0
SECTORS_COUNT = 13
ANGLE_STEP = 360 / SECTORS_COUNT
ADMIN_NAME = 'Господин Ведущий'

sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
fastapi_app = FastAPI()

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

# Хранилище состояния игры
game_state = {
    "phase": "LOGIN",  # LOGIN, PRE_ROUND, ROUND, RESULT
    "players": [],  # Список игроков: [{"sid": "...", "name": "...", "role": "player|admin"}]
    "score": {"znatoki": 0, "tv": 0},
    "current_sector": 1, 
    "target_angle": None, # Точный угол остановки (0-360)
    "playing_sector": None, # Какой сектор реально играет (с учетом скачки)
    "spin_duration": 0,
    "used_questions": [], 
    "is_spinning": False,
    "logs": [] # Лог событий ["12:00:01 - Игра началась", ...]
}

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
    
    for i in range(1, 14):
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


@fastapi_app.get("/")
async def root():
    return {"message": "CHGKA Game Server is running"}

@sio.event
async def connect(sid, environ):
    logger.info(f"Client connected: {sid}")
    
    await sio.save_session(sid, {'role': 'player', 'admin_token': None, 'player_name': None})
    
    await sio.emit('state_update', game_state, to=sid)
    await sio.emit('role_update', {'role': 'player'}, to=sid)

@sio.event
async def restore_session(sid, data):
    """Клиент отправляет токен/имя при переподключении"""
    token = data.get('token')
    player_name = data.get('player_name')
    
    session_data = {'role': 'player', 'admin_token': None, 'player_name': None}
    
    if token and validate_admin_token(token):
        session_data['role'] = 'admin'
        session_data['admin_token'] = token
        await sio.save_session(sid, session_data)
        logger.info(f"Session restored for {sid}: admin")
        
        admin_exists = any(p['sid'] == sid for p in game_state['players'])
        if not admin_exists:
            game_state['players'].append({'sid': sid, 'name': ADMIN_NAME, 'role': 'admin'})
        
        await sio.emit('role_update', {'role': 'admin'}, to=sid)
        await sio.emit('state_update', game_state, to=sid)
        await sio.emit('auth_restored', {}, to=sid)
        return
    
    if player_name:
        session_data['player_name'] = player_name
        await sio.save_session(sid, session_data)
        
        player_exists = any(p['sid'] == sid for p in game_state['players'])
        if not player_exists:
            game_state['players'].append({'sid': sid, 'name': player_name, 'role': 'player'})
            add_log(f"{player_name} переподключился")
            await sio.emit('state_update', game_state)
    
    await sio.emit('role_update', {'role': 'player'}, to=sid)
    await sio.emit('state_update', game_state, to=sid)

@sio.event
async def authenticate_admin(sid, data):
    """Проверка пароля и выдача токена"""
    password = data.get('password')
    correct_password = os.getenv('ADMIN_PASSWORD', 'admin123')
    
    if password == correct_password:
        token = generate_admin_token()
        await sio.save_session(sid, {'role': 'admin', 'admin_token': token, 'player_name': None})
        logger.info(f"Admin authenticated: {sid}")
        
        # Добавляем админа в список игроков (если его там нет)
        admin_exists = any(p['sid'] == sid for p in game_state['players'])
        if not admin_exists:
            game_state['players'].append({'sid': sid, 'name': ADMIN_NAME, 'role': 'admin'})
            add_log("Администратор присоединился")
            await sio.emit('state_update', game_state)  # Рассылаем всем обновленный список
        
        await sio.emit('auth_success', {'token': token}, to=sid)
        
        await sio.emit('role_update', {'role': 'admin'}, to=sid)
        await sio.emit('state_update', game_state, to=sid)
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
    
    # Проверяем, не занято ли имя другим игроком (кроме текущего)
    name_taken = any(p['name'] == player_name and p['sid'] != sid for p in game_state['players'])
    if name_taken:
        await sio.emit('join_failed', {'message': 'Это имя уже занято'}, to=sid)
        return
    
    # Сохраняем имя в сессии
    session = await sio.get_session(sid)
    session['player_name'] = player_name
    await sio.save_session(sid, session)
    
    # Добавляем/обновляем игрока в списке
    player_exists = any(p['sid'] == sid for p in game_state['players'])
    if player_exists:
        # Обновляем имя существующего игрока
        for p in game_state['players']:
            if p['sid'] == sid:
                p['name'] = player_name
                break
    else:
        # Добавляем нового игрока
        game_state['players'].append({'sid': sid, 'name': player_name, 'role': 'player'})
        add_log(f"{player_name} присоединился к игре")
    
    # Рассылаем обновленный список всем
    await sio.emit('state_update', game_state)
    
    # Отправляем успех клиенту
    await sio.emit('join_success', {}, to=sid)

@sio.event
async def start_game(sid):
    """Админ запускает игру (переход из LOGIN в PRE_ROUND)"""
    if not await require_admin(sid):
        return
    
    if game_state['phase'] != 'LOGIN':
        logger.warning(f"Attempt to start game in wrong phase: {game_state['phase']}")
        return
    
    game_state['phase'] = 'PRE_ROUND'
    add_log("Игра началась!")
    await sio.emit('state_update', game_state)

@sio.event
async def disconnect(sid):
    logger.info(f"Client disconnected: {sid}")
    
    # Удаляем игрока из списка
    player_removed = False
    for i, player in enumerate(game_state['players']):
        if player['sid'] == sid:
            player_name = player['name']
            game_state['players'].pop(i)
            player_removed = True
            if game_state['phase'] == 'LOGIN':
                add_log(f"{player_name} покинул игру")
            break
    
    # Рассылаем обновленный список всем (если игрок был удален)
    if player_removed:
        await sio.emit('state_update', game_state)

@sio.event
async def admin_spin(sid, data=None):
    if not await require_admin(sid):
        return
    
    force_sector = data.get('force_sector') if data else None

    if game_state["is_spinning"]:
        return
    
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
    
    if playing_sector == 13:
        await sio.emit('play_sound', {'sound': 'sector13'})

    await sio.emit('state_update', game_state)

@sio.event
async def admin_score(sid, data):
    if not await require_admin(sid):
        return
    
    winner = data.get('winner')
    if winner == 'znatoki':
        game_state["score"]["znatoki"] += 1
        add_log("Очко Знатокам!")
        await sio.emit('play_sound', {'category': 'win'})
    elif winner == 'tv':
        game_state["score"]["tv"] += 1
        add_log("Очко Телезрителям!")
        await sio.emit('play_sound', {'category': 'lose'})
    
    await sio.emit('state_update', game_state)

@sio.event
async def admin_sound(sid, data):
    if not await require_admin(sid):
        return
    
    add_log(f"Звук: {data.get('sound')}")
    await sio.emit('play_sound', data)

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
    game_state["phase"] = "INTRO"
    game_state["logs"] = []
    add_log("Игра сброшена")
    await sio.emit('state_update', game_state)
