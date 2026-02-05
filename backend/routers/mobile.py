from fastapi import APIRouter, HTTPException, Depends, Request
from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel
import uuid

from core.database import db
from core.auth import get_current_user

router = APIRouter(prefix="/api/mobile", tags=["Mobile APIs"])

class DeviceRegistration(BaseModel):
    device_id: str
    device_type: str  # ios, android, web
    push_token: Optional[str] = None
    app_version: str
    os_version: str

class PushSubscription(BaseModel):
    endpoint: str
    keys: dict

@router.post("/register-device")
async def register_device(
    device: DeviceRegistration,
    current_user: dict = Depends(get_current_user)
):
    """Register mobile device for push notifications"""
    try:
        now = datetime.now(timezone.utc).isoformat()
        
        await db.user_devices.update_one(
            {"user_id": current_user["id"], "device_id": device.device_id},
            {"$set": {
                "user_id": current_user["id"],
                "device_id": device.device_id,
                "device_type": device.device_type,
                "push_token": device.push_token,
                "app_version": device.app_version,
                "os_version": device.os_version,
                "last_active": now,
                "updated_at": now
            },
            "$setOnInsert": {"created_at": now}},
            upsert=True
        )
        
        return {"message": "Device registered"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/push-subscription")
async def save_push_subscription(
    subscription: PushSubscription,
    current_user: dict = Depends(get_current_user)
):
    """Save web push subscription"""
    try:
        now = datetime.now(timezone.utc).isoformat()
        
        await db.push_subscriptions.update_one(
            {"user_id": current_user["id"], "endpoint": subscription.endpoint},
            {"$set": {
                "user_id": current_user["id"],
                "endpoint": subscription.endpoint,
                "keys": subscription.keys,
                "updated_at": now
            },
            "$setOnInsert": {"created_at": now}},
            upsert=True
        )
        
        return {"message": "Subscription saved"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/dashboard")
async def get_mobile_dashboard(current_user: dict = Depends(get_current_user)):
    """Optimized dashboard data for mobile"""
    try:
        user_id = current_user["id"]
        
        # Get compact user stats
        user = await db.users.find_one(
            {"id": user_id},
            {"_id": 0, "realum_balance": 1, "xp": 1, "level": 1, "streak_days": 1}
        )
        
        # Unread notifications count
        unread = await db.notifications.count_documents({
            "user_id": user_id, "is_read": False
        })
        
        # Active stakes summary
        stakes = await db.stakes.find(
            {"user_id": user_id, "status": "active"},
            {"_id": 0, "amount": 1}
        ).to_list(100)
        total_staked = sum(s["amount"] for s in stakes)
        
        # Recent activity (last 5)
        activity = await db.user_activity.find(
            {"user_id": user_id},
            {"_id": 0}
        ).sort("timestamp", -1).limit(5).to_list(5)
        
        return {
            "user": user,
            "unread_notifications": unread,
            "total_staked": total_staked,
            "recent_activity": activity
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/feed")
async def get_mobile_feed(
    limit: int = 10,
    offset: int = 0,
    current_user: dict = Depends(get_current_user)
):
    """Optimized feed for mobile with smaller payloads"""
    try:
        user_id = current_user["id"]
        
        # Get following
        following = await db.follows.find(
            {"follower_id": user_id},
            {"_id": 0, "following_id": 1}
        ).to_list(None)
        following_ids = [f["following_id"] for f in following]
        
        # Get feed items
        feed = await db.activity_feed.find(
            {"user_id": {"$in": following_ids + [user_id]}},
            {"_id": 0, "id": 1, "type": 1, "title": 1, "preview": 1, "timestamp": 1, "user_id": 1}
        ).sort("timestamp", -1).skip(offset).limit(limit).to_list(limit)
        
        return {"feed": feed, "has_more": len(feed) == limit}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/quick-actions")
async def get_quick_actions(current_user: dict = Depends(get_current_user)):
    """Get personalized quick actions for mobile home screen"""
    try:
        actions = []
        user_id = current_user["id"]
        
        # Check daily reward
        today = datetime.now(timezone.utc).date().isoformat()
        claimed = await db.daily_claims.find_one({
            "user_id": user_id,
            "date": today
        })
        if not claimed:
            actions.append({
                "id": "daily_reward",
                "title": "Claim Daily Reward",
                "icon": "gift",
                "action": "/api/daily/claim",
                "priority": 1
            })
        
        # Check uncompleted courses
        in_progress = await db.enrollments.find_one({
            "user_id": user_id,
            "completed": False
        })
        if in_progress:
            actions.append({
                "id": "continue_course",
                "title": "Continue Learning",
                "icon": "book",
                "action": f"/courses/{in_progress['course_id']}",
                "priority": 2
            })
        
        # Active proposals to vote
        voted = await db.votes.find(
            {"user_id": user_id},
            {"_id": 0, "proposal_id": 1}
        ).to_list(100)
        voted_ids = [v["proposal_id"] for v in voted]
        
        pending_vote = await db.proposals.find_one({
            "id": {"$nin": voted_ids},
            "status": "active"
        })
        if pending_vote:
            actions.append({
                "id": "vote",
                "title": "Vote on Proposal",
                "icon": "vote",
                "action": "/voting",
                "priority": 3
            })
        
        # Staking opportunity
        user = await db.users.find_one({"id": user_id})
        if user and user.get("realum_balance", 0) >= 100:
            has_stake = await db.stakes.find_one({"user_id": user_id, "status": "active"})
            if not has_stake:
                actions.append({
                    "id": "stake",
                    "title": "Start Earning with Staking",
                    "icon": "trending-up",
                    "action": "/wallet",
                    "priority": 4
                })
        
        actions.sort(key=lambda x: x["priority"])
        return {"actions": actions[:4]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/offline-data")
async def get_offline_data(current_user: dict = Depends(get_current_user)):
    """Get essential data for offline mode"""
    try:
        user_id = current_user["id"]
        
        # User profile
        user = await db.users.find_one(
            {"id": user_id},
            {"_id": 0, "password_hash": 0}
        )
        
        # Enrolled courses (for offline viewing)
        enrollments = await db.enrollments.find(
            {"user_id": user_id},
            {"_id": 0, "course_id": 1}
        ).to_list(20)
        
        course_ids = [e["course_id"] for e in enrollments]
        courses = await db.courses.find(
            {"id": {"$in": course_ids}},
            {"_id": 0, "id": 1, "title": 1, "description": 1, "thumbnail_url": 1}
        ).to_list(20)
        
        # Achievements
        achievements = await db.user_achievements.find(
            {"user_id": user_id, "earned": True},
            {"_id": 0}
        ).to_list(50)
        
        return {
            "user": user,
            "courses": courses,
            "achievements": achievements,
            "synced_at": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/sync")
async def sync_offline_actions(
    actions: List[dict],
    current_user: dict = Depends(get_current_user)
):
    """Sync actions performed while offline"""
    try:
        results = []
        for action in actions:
            try:
                action_type = action.get("type")
                if action_type == "video_progress":
                    await db.video_progress.update_one(
                        {"video_id": action["video_id"], "user_id": current_user["id"]},
                        {"$set": {
                            "position_seconds": action["position"],
                            "updated_at": action.get("timestamp")
                        }},
                        upsert=True
                    )
                    results.append({"action_id": action.get("id"), "status": "synced"})
                elif action_type == "note":
                    await db.video_notes.insert_one({
                        "id": str(uuid.uuid4()),
                        "video_id": action["video_id"],
                        "user_id": current_user["id"],
                        "timestamp_seconds": action["timestamp_seconds"],
                        "content": action["content"],
                        "created_at": action.get("created_at")
                    })
                    results.append({"action_id": action.get("id"), "status": "synced"})
            except Exception as e:
                results.append({"action_id": action.get("id"), "status": "failed", "error": str(e)})
        
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/app-config")
async def get_app_config():
    """Get mobile app configuration"""
    return {
        "config": {
            "min_app_version": "1.0.0",
            "latest_version": "1.0.0",
            "force_update": False,
            "maintenance_mode": False,
            "features": {
                "nft_enabled": True,
                "staking_enabled": True,
                "chat_enabled": True,
                "3d_metaverse_enabled": True
            },
            "api_version": "v1",
            "cache_ttl_seconds": 300
        }
    }
