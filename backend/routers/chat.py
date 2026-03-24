"""
REALUM Chat System
Global chat, guild chat, and private messaging
"""

from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime, timezone, timedelta
import uuid
import json
import asyncio

router = APIRouter(prefix="/api/chat", tags=["Chat System"])

from core.database import db
from core.auth import get_current_user
from core.utils import serialize_doc


# ============== CONSTANTS ==============

# Chat channels
CHAT_CHANNELS = {
    "global": {"name": "Global", "description": "Chat public pentru toți"},
    "trade": {"name": "Trade", "description": "Discuții despre tranzacții"},
    "politics": {"name": "Politică", "description": "Dezbateri politice"},
    "help": {"name": "Ajutor", "description": "Întrebări și răspunsuri"}
}

# Rate limiting
MAX_MESSAGES_PER_MINUTE = 10
MESSAGE_MAX_LENGTH = 500


# ============== CONNECTION MANAGER ==============

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.user_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, channel: str, user_id: str):
        await websocket.accept()
        if channel not in self.active_connections:
            self.active_connections[channel] = []
        self.active_connections[channel].append(websocket)
        self.user_connections[user_id] = websocket
    
    def disconnect(self, websocket: WebSocket, channel: str, user_id: str):
        if channel in self.active_connections:
            if websocket in self.active_connections[channel]:
                self.active_connections[channel].remove(websocket)
        if user_id in self.user_connections:
            del self.user_connections[user_id]
    
    async def broadcast(self, channel: str, message: dict):
        if channel in self.active_connections:
            for connection in self.active_connections[channel]:
                try:
                    await connection.send_json(message)
                except:
                    pass
    
    async def send_personal(self, user_id: str, message: dict):
        if user_id in self.user_connections:
            try:
                await self.user_connections[user_id].send_json(message)
            except:
                pass

manager = ConnectionManager()


# ============== MODELS ==============

class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=MESSAGE_MAX_LENGTH)
    channel: str = "global"

class PrivateMessageRequest(BaseModel):
    recipient_username: str
    content: str = Field(..., min_length=1, max_length=MESSAGE_MAX_LENGTH)


# ============== HELPER FUNCTIONS ==============

async def check_rate_limit(user_id: str) -> bool:
    """Check if user can send message (rate limiting)"""
    one_minute_ago = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    
    count = await db.chat_messages.count_documents({
        "sender_id": user_id,
        "created_at": {"$gte": one_minute_ago}
    })
    
    return count < MAX_MESSAGES_PER_MINUTE


# ============== ENDPOINTS ==============

@router.get("/channels")
async def get_channels():
    """Get available chat channels"""
    return {"channels": CHAT_CHANNELS}


@router.get("/messages/{channel}")
async def get_channel_messages(
    channel: str,
    limit: int = 50,
    before: Optional[str] = None
):
    """Get messages from a channel"""
    if channel not in CHAT_CHANNELS and not channel.startswith("guild_"):
        raise HTTPException(status_code=404, detail="Channel not found")
    
    query = {"channel": channel}
    if before:
        query["created_at"] = {"$lt": before}
    
    messages = await db.chat_messages.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return {"messages": list(reversed(messages))}


@router.post("/send")
async def send_message(
    data: SendMessageRequest,
    current_user: dict = Depends(get_current_user)
):
    """Send a message to a channel"""
    if data.channel not in CHAT_CHANNELS and not data.channel.startswith("guild_"):
        raise HTTPException(status_code=404, detail="Channel not found")
    
    # Rate limit check
    if not await check_rate_limit(current_user["id"]):
        raise HTTPException(status_code=429, detail="Too many messages. Wait a moment.")
    
    now = datetime.now(timezone.utc)
    
    message = {
        "id": str(uuid.uuid4()),
        "channel": data.channel,
        "sender_id": current_user["id"],
        "sender_username": current_user["username"],
        "content": data.content,
        "created_at": now.isoformat()
    }
    await db.chat_messages.insert_one(message)
    
    # Broadcast to WebSocket clients
    await manager.broadcast(data.channel, {
        "type": "message",
        "data": serialize_doc(message)
    })
    
    return {"message": serialize_doc(message)}


@router.get("/private")
async def get_private_conversations(current_user: dict = Depends(get_current_user)):
    """Get list of private conversations"""
    # Get unique conversation partners
    pipeline = [
        {"$match": {
            "$or": [
                {"sender_id": current_user["id"]},
                {"recipient_id": current_user["id"]}
            ]
        }},
        {"$group": {
            "_id": {
                "$cond": [
                    {"$eq": ["$sender_id", current_user["id"]]},
                    "$recipient_id",
                    "$sender_id"
                ]
            },
            "last_message": {"$last": "$content"},
            "last_time": {"$last": "$created_at"},
            "unread": {
                "$sum": {
                    "$cond": [
                        {"$and": [
                            {"$eq": ["$recipient_id", current_user["id"]]},
                            {"$eq": ["$read", False]}
                        ]},
                        1,
                        0
                    ]
                }
            }
        }},
        {"$sort": {"last_time": -1}},
        {"$limit": 50}
    ]
    
    results = await db.private_messages.aggregate(pipeline).to_list(50)
    
    conversations = []
    for r in results:
        user = await db.users.find_one({"id": r["_id"]})
        if user:
            conversations.append({
                "user_id": r["_id"],
                "username": user.get("username", "Unknown"),
                "last_message": r["last_message"],
                "last_time": r["last_time"],
                "unread_count": r["unread"]
            })
    
    return {"conversations": conversations}


@router.get("/private/{user_id}")
async def get_private_messages(
    user_id: str,
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """Get private messages with a user"""
    messages = await db.private_messages.find({
        "$or": [
            {"sender_id": current_user["id"], "recipient_id": user_id},
            {"sender_id": user_id, "recipient_id": current_user["id"]}
        ]
    }, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    
    # Mark as read
    await db.private_messages.update_many(
        {"sender_id": user_id, "recipient_id": current_user["id"], "read": False},
        {"$set": {"read": True}}
    )
    
    return {"messages": list(reversed(messages))}


@router.post("/private/send")
async def send_private_message(
    data: PrivateMessageRequest,
    current_user: dict = Depends(get_current_user)
):
    """Send a private message"""
    recipient = await db.users.find_one({"username": data.recipient_username})
    if not recipient:
        raise HTTPException(status_code=404, detail="User not found")
    
    if recipient["id"] == current_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot message yourself")
    
    # Rate limit
    if not await check_rate_limit(current_user["id"]):
        raise HTTPException(status_code=429, detail="Too many messages")
    
    now = datetime.now(timezone.utc)
    
    message = {
        "id": str(uuid.uuid4()),
        "sender_id": current_user["id"],
        "sender_username": current_user["username"],
        "recipient_id": recipient["id"],
        "recipient_username": recipient["username"],
        "content": data.content,
        "read": False,
        "created_at": now.isoformat()
    }
    await db.private_messages.insert_one(message)
    
    # Send to recipient via WebSocket
    await manager.send_personal(recipient["id"], {
        "type": "private_message",
        "data": serialize_doc(message)
    })
    
    # Create notification
    await db.notifications.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": recipient["id"],
        "type": "private_message",
        "title": "Mesaj Nou",
        "message": f"{current_user['username']} ți-a trimis un mesaj",
        "read": False,
        "created_at": now.isoformat()
    })
    
    return {"message": serialize_doc(message)}


# ============== WEBSOCKET ==============

@router.websocket("/ws/{channel}")
async def websocket_endpoint(websocket: WebSocket, channel: str):
    """WebSocket for real-time chat"""
    # Simple auth via query param (in production, use proper auth)
    token = websocket.query_params.get("token", "")
    user_id = websocket.query_params.get("user_id", str(uuid.uuid4()))
    
    await manager.connect(websocket, channel, user_id)
    
    try:
        while True:
            data = await websocket.receive_text()
            # Echo back or process message
            await manager.broadcast(channel, {
                "type": "message",
                "data": json.loads(data)
            })
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel, user_id)


@router.get("/online-count/{channel}")
async def get_online_count(channel: str):
    """Get count of online users in channel"""
    count = len(manager.active_connections.get(channel, []))
    return {"channel": channel, "online_count": count}
