"""
REALUM Advanced Friends System
Friends, gifts, online status, and social features
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import uuid

router = APIRouter(prefix="/api/friends", tags=["Friends System"])

from core.database import db
from core.auth import get_current_user


# ============== MODELS ==============

class FriendRequest(BaseModel):
    target_username: str
    message: Optional[str] = None

class SendGift(BaseModel):
    friend_id: str
    gift_type: str  # rlm, item, badge
    amount: Optional[float] = None
    item_id: Optional[str] = None
    message: Optional[str] = None


# ============== CONSTANTS ==============

GIFT_TYPES = {
    "rlm": {"name": "RLM", "min": 10, "max": 10000, "fee_percent": 0},
    "xp_boost": {"name": "XP Boost", "cost": 50, "effect": "+25% XP for 1 hour"},
    "lucky_charm": {"name": "Lucky Charm", "cost": 100, "effect": "+10% luck in games"},
    "flowers": {"name": "Flowers", "cost": 25, "effect": "A nice gesture"},
    "cake": {"name": "Cake", "cost": 50, "effect": "Celebration!"},
    "trophy": {"name": "Trophy", "cost": 200, "effect": "Recognition of excellence"}
}


# ============== ENDPOINTS ==============

@router.get("/list")
async def get_friends_list(current_user: dict = Depends(get_current_user)):
    """Get user's friends list with online status"""
    user_id = current_user["id"]
    
    # Get all friendships
    friendships = await db.friendships.find({
        "$or": [
            {"user_id": user_id, "status": "accepted"},
            {"friend_id": user_id, "status": "accepted"}
        ]
    }).to_list(100)
    
    friends = []
    now = datetime.now(timezone.utc)
    
    for friendship in friendships:
        friend_id = friendship["friend_id"] if friendship["user_id"] == user_id else friendship["user_id"]
        
        friend = await db.users.find_one(
            {"id": friend_id},
            {"_id": 0, "id": 1, "username": 1, "avatar_url": 1, "level": 1, "last_active": 1}
        )
        
        if friend:
            # Check online status (active in last 5 minutes)
            last_active = friend.get("last_active")
            is_online = False
            if last_active:
                try:
                    last_active_dt = datetime.fromisoformat(last_active.replace('Z', '+00:00'))
                    is_online = (now - last_active_dt).total_seconds() < 300
                except:
                    pass
            
            friends.append({
                "id": friend["id"],
                "username": friend["username"],
                "avatar_url": friend.get("avatar_url"),
                "level": friend.get("level", 1),
                "is_online": is_online,
                "last_active": friend.get("last_active"),
                "friendship_since": friendship.get("accepted_at")
            })
    
    # Sort: online first, then by username
    friends.sort(key=lambda x: (not x["is_online"], x["username"].lower()))
    
    return {
        "friends": friends,
        "total": len(friends),
        "online_count": sum(1 for f in friends if f["is_online"])
    }


@router.post("/request")
async def send_friend_request(
    data: FriendRequest,
    current_user: dict = Depends(get_current_user)
):
    """Send a friend request"""
    user_id = current_user["id"]
    
    # Find target user
    target = await db.users.find_one({"username": data.target_username}, {"_id": 0, "id": 1, "username": 1})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    
    if target["id"] == user_id:
        raise HTTPException(status_code=400, detail="Cannot friend yourself")
    
    # Check if already friends or request pending
    existing = await db.friendships.find_one({
        "$or": [
            {"user_id": user_id, "friend_id": target["id"]},
            {"user_id": target["id"], "friend_id": user_id}
        ]
    })
    
    if existing:
        if existing["status"] == "accepted":
            raise HTTPException(status_code=400, detail="Already friends")
        elif existing["status"] == "pending":
            raise HTTPException(status_code=400, detail="Request already pending")
    
    # Create friend request
    friendship = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "friend_id": target["id"],
        "status": "pending",
        "message": data.message,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.friendships.insert_one(friendship)
    
    # Create notification
    await db.notifications.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": target["id"],
        "title": "Friend Request",
        "message": f"{current_user['username']} wants to be your friend!",
        "type": "friend_request",
        "data": {"friendship_id": friendship["id"], "from_user": current_user["username"]},
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": f"Friend request sent to {target['username']}"}


@router.get("/requests")
async def get_friend_requests(current_user: dict = Depends(get_current_user)):
    """Get pending friend requests"""
    user_id = current_user["id"]
    
    # Incoming requests
    incoming = await db.friendships.find({
        "friend_id": user_id,
        "status": "pending"
    }).to_list(50)
    
    incoming_requests = []
    for req in incoming:
        sender = await db.users.find_one(
            {"id": req["user_id"]},
            {"_id": 0, "id": 1, "username": 1, "avatar_url": 1, "level": 1}
        )
        if sender:
            incoming_requests.append({
                "request_id": req["id"],
                "from_user": sender,
                "message": req.get("message"),
                "sent_at": req["created_at"]
            })
    
    # Outgoing requests
    outgoing = await db.friendships.find({
        "user_id": user_id,
        "status": "pending"
    }).to_list(50)
    
    outgoing_requests = []
    for req in outgoing:
        target = await db.users.find_one(
            {"id": req["friend_id"]},
            {"_id": 0, "id": 1, "username": 1, "avatar_url": 1}
        )
        if target:
            outgoing_requests.append({
                "request_id": req["id"],
                "to_user": target,
                "sent_at": req["created_at"]
            })
    
    return {
        "incoming": incoming_requests,
        "outgoing": outgoing_requests
    }


@router.post("/requests/{request_id}/accept")
async def accept_friend_request(
    request_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Accept a friend request"""
    user_id = current_user["id"]
    
    friendship = await db.friendships.find_one({
        "id": request_id,
        "friend_id": user_id,
        "status": "pending"
    })
    
    if not friendship:
        raise HTTPException(status_code=404, detail="Friend request not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.friendships.update_one(
        {"id": request_id},
        {"$set": {"status": "accepted", "accepted_at": now}}
    )
    
    # Notify the sender
    await db.notifications.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": friendship["user_id"],
        "title": "Friend Request Accepted",
        "message": f"{current_user['username']} accepted your friend request!",
        "type": "friend_accepted",
        "read": False,
        "created_at": now
    })
    
    return {"message": "Friend request accepted!"}


@router.post("/requests/{request_id}/decline")
async def decline_friend_request(
    request_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Decline a friend request"""
    user_id = current_user["id"]
    
    result = await db.friendships.delete_one({
        "id": request_id,
        "friend_id": user_id,
        "status": "pending"
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Friend request not found")
    
    return {"message": "Friend request declined"}


@router.delete("/{friend_id}")
async def remove_friend(
    friend_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Remove a friend"""
    user_id = current_user["id"]
    
    result = await db.friendships.delete_one({
        "$or": [
            {"user_id": user_id, "friend_id": friend_id, "status": "accepted"},
            {"user_id": friend_id, "friend_id": user_id, "status": "accepted"}
        ]
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Friendship not found")
    
    return {"message": "Friend removed"}


@router.post("/gift")
async def send_gift(
    data: SendGift,
    current_user: dict = Depends(get_current_user)
):
    """Send a gift to a friend"""
    user_id = current_user["id"]
    
    # Verify friendship
    friendship = await db.friendships.find_one({
        "$or": [
            {"user_id": user_id, "friend_id": data.friend_id, "status": "accepted"},
            {"user_id": data.friend_id, "friend_id": user_id, "status": "accepted"}
        ]
    })
    
    if not friendship:
        raise HTTPException(status_code=400, detail="You can only send gifts to friends")
    
    # Get friend info
    friend = await db.users.find_one({"id": data.friend_id}, {"_id": 0, "username": 1})
    if not friend:
        raise HTTPException(status_code=404, detail="Friend not found")
    
    gift_value = 0
    gift_description = ""
    
    if data.gift_type == "rlm":
        if not data.amount or data.amount < 10:
            raise HTTPException(status_code=400, detail="Minimum gift is 10 RLM")
        if data.amount > current_user.get("realum_balance", 0):
            raise HTTPException(status_code=400, detail="Insufficient balance")
        
        gift_value = data.amount
        gift_description = f"{data.amount} RLM"
        
        # Transfer RLM
        await db.users.update_one({"id": user_id}, {"$inc": {"realum_balance": -data.amount}})
        await db.users.update_one({"id": data.friend_id}, {"$inc": {"realum_balance": data.amount}})
        
    elif data.gift_type in GIFT_TYPES:
        gift_info = GIFT_TYPES[data.gift_type]
        cost = gift_info.get("cost", 0)
        
        if cost > current_user.get("realum_balance", 0):
            raise HTTPException(status_code=400, detail="Insufficient balance")
        
        gift_value = cost
        gift_description = gift_info["name"]
        
        # Deduct cost
        if cost > 0:
            await db.users.update_one({"id": user_id}, {"$inc": {"realum_balance": -cost}})
    else:
        raise HTTPException(status_code=400, detail="Invalid gift type")
    
    # Record gift
    gift = {
        "id": str(uuid.uuid4()),
        "sender_id": user_id,
        "sender_name": current_user["username"],
        "recipient_id": data.friend_id,
        "recipient_name": friend["username"],
        "gift_type": data.gift_type,
        "value": gift_value,
        "message": data.message,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.gifts.insert_one(gift)
    
    # Notify friend
    await db.notifications.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": data.friend_id,
        "title": "Gift Received! 🎁",
        "message": f"{current_user['username']} sent you {gift_description}!" + (f" Message: {data.message}" if data.message else ""),
        "type": "gift",
        "data": {"gift_id": gift["id"]},
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "message": f"Gift sent to {friend['username']}!",
        "gift": gift_description,
        "cost": gift_value
    }


@router.get("/gifts/received")
async def get_received_gifts(current_user: dict = Depends(get_current_user)):
    """Get gifts received"""
    user_id = current_user["id"]
    
    gifts = await db.gifts.find(
        {"recipient_id": user_id},
        {"_id": 0}
    ).sort("created_at", -1).limit(50).to_list(50)
    
    return {"gifts": gifts}


@router.get("/gifts/sent")
async def get_sent_gifts(current_user: dict = Depends(get_current_user)):
    """Get gifts sent"""
    user_id = current_user["id"]
    
    gifts = await db.gifts.find(
        {"sender_id": user_id},
        {"_id": 0}
    ).sort("created_at", -1).limit(50).to_list(50)
    
    return {"gifts": gifts}


@router.get("/gift-types")
async def get_gift_types():
    """Get available gift types"""
    return {"gift_types": GIFT_TYPES}


@router.post("/update-status")
async def update_online_status(current_user: dict = Depends(get_current_user)):
    """Update user's online status (call periodically)"""
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$set": {"last_active": datetime.now(timezone.utc).isoformat()}}
    )
    return {"status": "online"}
