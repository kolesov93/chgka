import socketio
import random
import asyncio
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

DEBUG = True

MIN_SPIN_DURATION = 5.0 if DEBUG else 10.0
MAX_SPIN_DURATION = 10.0 if DEBUG else 20.0

app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)

# Хранилище состояния игры
game_state = {
    "phase": "INTRO",
    "score": {"znatoki": 0, "tv": 0},
    "current_sector": 1, 
    "target_sector": None,
    "spin_duration": 0,
    "used_questions": [], 
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
    
    # Если игра закончилась (кто-то набрал 6)
    if game_state["score"]["znatoki"] >= 6 or game_state["score"]["tv"] >= 6:
        return

    available_sectors = [i for i in range(1, 14) if i not in game_state["used_questions"]]
    
    if not available_sectors:
        print("No more questions!")
        return

    target = random.choice(available_sectors)
    duration = random.uniform(MIN_SPIN_DURATION, MAX_SPIN_DURATION)

    game_state["target_sector"] = target
    game_state["spin_duration"] = duration
    game_state["is_spinning"] = True
    
    await sio.emit('state_update', game_state)

    await asyncio.sleep(duration)

    game_state["is_spinning"] = False
    game_state["current_sector"] = target
    game_state["spin_duration"] = 0
    game_state["used_questions"].append(target)
    
    await sio.emit('state_update', game_state)

@sio.event
async def admin_score(sid, data):
    # data = {'winner': 'znatoki' | 'tv'}
    winner = data.get('winner')
    
    if winner == 'znatoki':
        game_state["score"]["znatoki"] += 1
        await sio.emit('play_sound', {'category': 'win'})
        
    elif winner == 'tv':
        game_state["score"]["tv"] += 1
        await sio.emit('play_sound', {'category': 'lose'})
    
    else:
        logger.error(f"Invalid winner: {winner}")

    await sio.emit('state_update', game_state)

@sio.event
async def admin_sound(sid, data):
    await sio.emit('play_sound', data)

@sio.event
async def admin_reset(sid):
    game_state["used_questions"] = []
    game_state["score"] = {"znatoki": 0, "tv": 0}
    game_state["spin_duration"] = 0
    game_state["is_spinning"] = False
    game_state["current_sector"] = 1
    game_state["target_sector"] = None
    game_state["phase"] = "INTRO"
    await sio.emit('state_update', game_state)
