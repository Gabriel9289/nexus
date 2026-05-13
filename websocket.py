from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from dotenv import load_dotenv
import os
import json

from database import get_db, SessionLocal
from models import User

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM  = os.getenv("ALGORITHM", "HS256")

router = APIRouter(tags=["WebSocket"])


# --- Connection Manager ||||||||||||||--
# Keeps a dict of user_id → WebSocket connection
# So we can push a message to a specific user by their ID

class ConnectionManager:
    def __init__(self):
        # { user_id: websocket }
        self.active: dict[int, WebSocket] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active[user_id] = websocket

    def disconnect(self, user_id: int):
        self.active.pop(user_id, None)

    async def send_to_user(self, user_id: int, message: dict):
        ws = self.active.get(user_id)
        if ws:
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                self.disconnect(user_id)

    async def broadcast(self, message: dict):
        disconnected = []
        for user_id, ws in self.active.items():
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                disconnected.append(user_id)
        for uid in disconnected:
            self.disconnect(uid)


# Global manager — one instance shared across the whole app
manager = ConnectionManager()


# --- Token validator for WebSocket --------------
# HTTP routes use Depends() for auth — WebSockets can't do that the same way
# So we decode the token manually from the query parameter

def get_user_from_token(token: str, db: Session) -> User | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            return None
        return db.query(User).filter(User.id == int(user_id)).first()
    except JWTError:
        return None


# --- WebSocket endpoint ||||||||||||||--

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str):
    db   = SessionLocal()
    user = get_user_from_token(token, db)

    if not user:
        await websocket.close(code=4001)
        db.close()
        return

    await manager.connect(user.id, websocket)

    try:
        # Confirm connection
        await manager.send_to_user(user.id, {
            "type":    "connected",
            "message": f"Welcome to Nexus, {user.display_name or user.username}!"
        })

        # Keep connection alive — listen for pings from client
        while True:
            data = await websocket.receive_text()

            # Client can send { "type": "ping" } to keep connection alive
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await manager.send_to_user(user.id, {"type": "pong"})
            except Exception:
                pass

    except WebSocketDisconnect:
        manager.disconnect(user.id)
        db.close()