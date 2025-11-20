import socketio
import random
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')

fastapi_app = FastAPI()

# Разрешаем обычные HTTP запросы (CORS)
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Оборачиваем FastAPI в Socket.IO приложение
app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)

# Хранилище состояния игры (в памяти)
game_state = {
    "phase": "INTRO", # INTRO, SPINNING, RESULT
    "score": {"znatoki": 0, "tv": 0},
    "current_sector": 1, # Начальный сектор
    "target_sector": None,
    "spin_duration": 0,
    "used_questions": [], # Список сыгранных секторов
    "is_spinning": False
}

@fastapi_app.get("/")
async def root():
    return {"message": "CHGKA Game Server is running"}

@sio.event
async def connect(sid, environ):
    print(f"Client connected: {sid}")
    await sio.emit('state_update', game_state, to=sid)

@sio.event
async def disconnect(sid):
    print(f"Client disconnected: {sid}")

@sio.event
async def admin_spin(sid):
    if game_state["is_spinning"]:
        return

    available_sectors = [i for i in range(1, 14) if i not in game_state["used_questions"]]
    
    if not available_sectors:
        print("No more questions!")
        return

    target = random.choice(available_sectors)
    duration = random.uniform(5.0, 10.0) 

    print(f"Spinning to sector {target} in {duration:.2f}s")

    game_state["target_sector"] = target
    game_state["spin_duration"] = duration
    game_state["is_spinning"] = True
    
    await sio.emit('state_update', game_state)

    # Ждем окончания вращения
    await asyncio.sleep(duration)

    game_state["is_spinning"] = False
    game_state["current_sector"] = target
    game_state["used_questions"].append(target)
    
    await sio.emit('state_update', game_state)

@sio.event
async def admin_sound(sid, data):
    # data = {'sound': 'gong'}
    print(f"Playing sound: {data}")
    await sio.emit('play_sound', data) # Рассылаем всем команду "Играть звук"

@sio.event
async def admin_reset(sid):
    game_state["used_questions"] = []
    game_state["score"] = {"znatoki": 0, "tv": 0}
    await sio.emit('state_update', game_state)
