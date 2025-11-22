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
    "phase": "INTRO",
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
    
    await sio.save_session(sid, {'role': 'player', 'admin_token': None})
    
    client_state = game_state.copy()
    client_state['my_role'] = 'player'  # По умолчанию
    await sio.emit('state_update', client_state, to=sid)

@sio.event
async def restore_session(sid, data):
    """Клиент отправляет токен при переподключении"""
    token = data.get('token')
    
    if validate_admin_token(token):
        # Восстанавливаем роль админа
        await sio.save_session(sid, {'role': 'admin', 'admin_token': token})
        logger.info(f"Session restored for {sid}: admin")
        
        # Отправляем обновленный стейт с ролью
        client_state = game_state.copy()
        client_state['my_role'] = 'admin'
        await sio.emit('state_update', client_state, to=sid)
        await sio.emit('auth_restored', {}, to=sid)
    else:
        # Токен невалидный или отсутствует - остаемся игроком
        client_state = game_state.copy()
        client_state['my_role'] = 'player'
        await sio.emit('state_update', client_state, to=sid)

@sio.event
async def authenticate_admin(sid, data):
    """Проверка пароля и выдача токена"""
    password = data.get('password')
    correct_password = os.getenv('ADMIN_PASSWORD', 'admin123')  # По умолчанию для разработки
    
    if password == correct_password:
        # Генерируем токен и сохраняем в сессии
        token = generate_admin_token()
        await sio.save_session(sid, {'role': 'admin', 'admin_token': token})
        logger.info(f"Admin authenticated: {sid}")
        
        # Отправляем токен клиенту
        await sio.emit('auth_success', {'token': token}, to=sid)
        
        # Обновляем стейт с ролью
        client_state = game_state.copy()
        client_state['my_role'] = 'admin'
        await sio.emit('state_update', client_state, to=sid)
    else:
        logger.warning(f"Failed admin auth attempt from {sid}")
        await sio.emit('auth_failed', {'message': 'Неверный пароль'}, to=sid)

@sio.event
async def disconnect(sid):
    print(f"Client disconnected: {sid}")

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
