from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict
from pydantic import BaseModel
import uuid

from core.database import db
from core.auth import get_current_user, require_admin
from services.notification_service import (
    send_notification,
    send_notification_from_template,
    send_bulk_notification,
    mark_notification_read,
    mark_all_read,
    delete_notification,
    get_unread_count
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])

# ===================== MODELS =====================

class NotificationPreferencesUpdate(BaseModel):
    email_enabled: Optional[bool] = None
    push_enabled: Optional[bool] = None
    in_app_enabled: Optional[bool] = None
    daily_digest: Optional[bool] = None
    weekly_digest: Optional[bool] = None
    muted_categories: Optional[List[str]] = None
    quiet_hours_start: Optional[int] = None  # 0-23
    quiet_hours_end: Optional[int] = None  # 0-23

class NotificationCreate(BaseModel):
    title: str
    message: str
    notification_type: str = "info"
    channel: str = "in_app"
    category: str = "general"
    action_url: Optional[str] = None
    action_label: Optional[str] = None

class BulkNotificationCreate(BaseModel):
    title: str
    message: str
    notification_type: str = "info"
    channel: str = "in_app"
    category: str = "general"
    target_roles: List[str] = []  # Empty = all users

class PushSubscription(BaseModel):
    endpoint: str
    keys: Dict[str, str]  # p256dh, auth
    user_agent: Optional[str] = None

class NotificationTemplateCreate(BaseModel):
    template_key: str
    title_template: str
    message_template: str
    category: str = "general"
    default_channel: str = "in_app"

# ===================== NOTIFICATIONS =====================

@router.get("/")
async def get_notifications(
    skip: int = 0,
    limit: int = 20,
    unread_only: bool = False,
    category: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get notifications for current user"""
    try:
        user_id = current_user["id"]

        query = {"user_id": user_id}

        if unread_only:
            query["is_read"] = False

        if category:
            query["category"] = category

        # Filter out expired notifications
        now = datetime.now(timezone.utc).isoformat()
        query["$or"] = [
            {"expires_at": None},
            {"expires_at": {"$gt": now}}
        ]

        notifications = await db.notifications.find(
            query, {"_id": 0}
        ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)

        unread_count = await get_unread_count(user_id)
        total = await db.notifications.count_documents(query)

        return {
            "notifications": notifications,
            "unread_count": unread_count,
            "total": total
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/unread-count")
async def get_unread_notifications_count(current_user: dict = Depends(get_current_user)):
    """Get count of unread notifications"""
    count = await get_unread_count(current_user["id"])
    return {"unread_count": count}

@router.patch("/{notification_id}/read")
async def mark_notification_as_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Mark a notification as read"""
    success = await mark_notification_read(notification_id, current_user["id"])

    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")

    return {"message": "Notification marked as read"}

@router.post("/mark-all-read")
async def mark_all_notifications_read(current_user: dict = Depends(get_current_user)):
    """Mark all notifications as read"""
    count = await mark_all_read(current_user["id"])

    return {
        "message": f"{count} notifications marked as read",
        "count": count
    }

@router.delete("/{notification_id}")
async def delete_user_notification(
    notification_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a notification"""
    success = await delete_notification(notification_id, current_user["id"])

    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")

    return {"message": "Notification deleted"}

# ===================== PREFERENCES =====================

@router.get("/preferences")
async def get_notification_preferences(current_user: dict = Depends(get_current_user)):
    """Get notification preferences"""
    try:
        user_id = current_user["id"]

        prefs = await db.notification_preferences.find_one(
            {"user_id": user_id},
            {"_id": 0}
        )

        if not prefs:
            # Return defaults
            prefs = {
                "user_id": user_id,
                "email_enabled": True,
                "push_enabled": True,
                "in_app_enabled": True,
                "daily_digest": False,
                "weekly_digest": False,
                "muted_categories": [],
                "quiet_hours_start": None,
                "quiet_hours_end": None
            }

        # Get category options
        categories = await get_notification_categories()

        return {
            "preferences": prefs,
            "categories": categories["categories"]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/preferences")
async def update_notification_preferences(
    update: NotificationPreferencesUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update notification preferences"""
    try:
        user_id = current_user["id"]
        now = datetime.now(timezone.utc).isoformat()

        update_data = {k: v for k, v in update.dict().items() if v is not None}
        update_data["updated_at"] = now

        result = await db.notification_preferences.update_one(
            {"user_id": user_id},
            {"$set": update_data},
            upsert=True
        )

        return {"message": "Preferences updated"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/preferences/mute/{category}")
async def mute_category(
    category: str,
    current_user: dict = Depends(get_current_user)
):
    """Mute a notification category"""
    try:
        await db.notification_preferences.update_one(
            {"user_id": current_user["id"]},
            {"$addToSet": {"muted_categories": category}},
            upsert=True
        )

        return {"message": f"Category '{category}' muted"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/preferences/mute/{category}")
async def unmute_category(
    category: str,
    current_user: dict = Depends(get_current_user)
):
    """Unmute a notification category"""
    try:
        await db.notification_preferences.update_one(
            {"user_id": current_user["id"]},
            {"$pull": {"muted_categories": category}}
        )

        return {"message": f"Category '{category}' unmuted"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ===================== PUSH SUBSCRIPTIONS =====================

@router.post("/push/subscribe")
async def subscribe_to_push(
    subscription: PushSubscription,
    current_user: dict = Depends(get_current_user)
):
    """Subscribe to push notifications"""
    try:
        user_id = current_user["id"]
        now = datetime.now(timezone.utc).isoformat()

        # Check for existing subscription
        existing = await db.push_subscriptions.find_one({
            "user_id": user_id,
            "endpoint": subscription.endpoint
        })

        if existing:
            return {"message": "Already subscribed", "subscription_id": existing["id"]}

        subscription_id = str(uuid.uuid4())

        await db.push_subscriptions.insert_one({
            "id": subscription_id,
            "user_id": user_id,
            "endpoint": subscription.endpoint,
            "keys": subscription.keys,
            "user_agent": subscription.user_agent,
            "is_active": True,
            "created_at": now
        })

        return {
            "message": "Subscribed to push notifications",
            "subscription_id": subscription_id
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/push/unsubscribe")
async def unsubscribe_from_push(
    endpoint: str,
    current_user: dict = Depends(get_current_user)
):
    """Unsubscribe from push notifications"""
    try:
        result = await db.push_subscriptions.delete_one({
            "user_id": current_user["id"],
            "endpoint": endpoint
        })

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Subscription not found")

        return {"message": "Unsubscribed from push notifications"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/push/subscriptions")
async def get_push_subscriptions(current_user: dict = Depends(get_current_user)):
    """Get user's push subscriptions"""
    try:
        subscriptions = await db.push_subscriptions.find(
            {"user_id": current_user["id"], "is_active": True},
            {"_id": 0, "keys": 0}  # Don't expose keys
        ).to_list(10)

        return {"subscriptions": subscriptions}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ===================== ADMIN ENDPOINTS =====================

@router.post("/send")
async def send_notification_to_user(
    notification: NotificationCreate,
    user_id: str,
    current_user: dict = Depends(require_admin)
):
    """Send notification to a specific user (admin only)"""
    try:
        notification_id = await send_notification(
            user_id=user_id,
            title=notification.title,
            message=notification.message,
            notification_type=notification.notification_type,
            channel=notification.channel,
            category=notification.category,
            action_url=notification.action_url,
            action_label=notification.action_label
        )

        return {
            "message": "Notification sent",
            "notification_id": notification_id
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/broadcast")
async def broadcast_notification(
    notification: BulkNotificationCreate,
    current_user: dict = Depends(require_admin)
):
    """Broadcast notification to multiple users (admin only)"""
    try:
        # Get target users
        if notification.target_roles:
            users = await db.users.find(
                {"role": {"$in": notification.target_roles}},
                {"_id": 0, "id": 1}
            ).to_list(None)
        else:
            users = await db.users.find({}, {"_id": 0, "id": 1}).to_list(None)

        user_ids = [u["id"] for u in users]

        count = await send_bulk_notification(
            user_ids=user_ids,
            title=notification.title,
            message=notification.message,
            notification_type=notification.notification_type,
            channel=notification.channel,
            category=notification.category
        )

        return {
            "message": f"Notification broadcast to {count} users",
            "count": count
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ===================== TEMPLATES =====================

@router.post("/templates")
async def create_notification_template(
    template: NotificationTemplateCreate,
    current_user: dict = Depends(require_admin)
):
    """Create a notification template (admin only)"""
    try:
        # Check for existing template with same key
        existing = await db.notification_templates.find_one({
            "template_key": template.template_key
        })

        if existing:
            raise HTTPException(status_code=400, detail="Template key already exists")

        template_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        await db.notification_templates.insert_one({
            "id": template_id,
            "template_key": template.template_key,
            "title_template": template.title_template,
            "message_template": template.message_template,
            "category": template.category,
            "default_channel": template.default_channel,
            "is_active": True,
            "created_by": current_user["id"],
            "created_at": now
        })

        return {
            "message": "Template created",
            "template_id": template_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/templates")
async def get_notification_templates(current_user: dict = Depends(require_admin)):
    """Get all notification templates (admin only)"""
    try:
        templates = await db.notification_templates.find(
            {"is_active": True},
            {"_id": 0}
        ).to_list(100)

        return {"templates": templates}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/templates/{template_key}/send")
async def send_from_template(
    template_key: str,
    user_id: str,
    variables: Dict[str, str],
    current_user: dict = Depends(require_admin)
):
    """Send notification using a template (admin only)"""
    try:
        notification_id = await send_notification_from_template(
            user_id=user_id,
            template_key=template_key,
            variables=variables
        )

        if not notification_id:
            raise HTTPException(status_code=404, detail="Template not found")

        return {
            "message": "Notification sent from template",
            "notification_id": notification_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ===================== STATS & UTILS =====================

@router.get("/stats")
async def get_notification_stats(current_user: dict = Depends(require_admin)):
    """Get notification statistics (admin only)"""
    try:
        total = await db.notifications.count_documents({})
        unread = await db.notifications.count_documents({"is_read": False})

        # By category
        category_pipeline = [
            {"$group": {"_id": "$category", "count": {"$sum": 1}}}
        ]
        category_result = await db.notifications.aggregate(category_pipeline).to_list(None)
        by_category = {item["_id"]: item["count"] for item in category_result if item["_id"]}

        # By channel
        channel_pipeline = [
            {"$group": {"_id": "$channel", "count": {"$sum": 1}}}
        ]
        channel_result = await db.notifications.aggregate(channel_pipeline).to_list(None)
        by_channel = {item["_id"]: item["count"] for item in channel_result if item["_id"]}

        # Push subscriptions
        push_subs = await db.push_subscriptions.count_documents({"is_active": True})

        # Recent 24h
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        recent = await db.notifications.count_documents({
            "created_at": {"$gte": yesterday}
        })

        return {
            "stats": {
                "total_notifications": total,
                "unread_notifications": unread,
                "push_subscriptions": push_subs,
                "sent_last_24h": recent,
                "by_category": by_category,
                "by_channel": by_channel
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/categories")
async def get_notification_categories():
    """Get available notification categories"""
    return {
        "categories": [
            {"key": "general", "name": "General", "description": "General notifications"},
            {"key": "social", "name": "Social", "description": "Social interactions"},
            {"key": "governance", "name": "Governance", "description": "DAO and voting"},
            {"key": "rewards", "name": "Rewards", "description": "Tokens and achievements"},
            {"key": "jobs", "name": "Jobs & Bounties", "description": "Job and bounty updates"},
            {"key": "courses", "name": "Courses", "description": "Learning updates"},
            {"key": "announcement", "name": "Announcements", "description": "System announcements"},
            {"key": "security", "name": "Security", "description": "Security alerts"}
        ],
        "channels": [
            {"key": "in_app", "name": "In-App", "description": "In-application notifications"},
            {"key": "email", "name": "Email", "description": "Email notifications"},
            {"key": "push", "name": "Push", "description": "Browser push notifications"},
            {"key": "all", "name": "All Channels", "description": "All available channels"}
        ],
        "types": [
            {"key": "info", "color": "#3B82F6"},
            {"key": "success", "color": "#10B981"},
            {"key": "warning", "color": "#F59E0B"},
            {"key": "error", "color": "#EF4444"},
            {"key": "achievement", "color": "#8B5CF6"},
            {"key": "system", "color": "#6B7280"}
        ]
    }

@router.delete("/cleanup")
async def cleanup_old_notifications(
    days: int = 30,
    current_user: dict = Depends(require_admin)
):
    """Clean up old read notifications (admin only)"""
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        result = await db.notifications.delete_many({
            "is_read": True,
            "created_at": {"$lt": cutoff}
        })

        return {
            "message": f"Cleaned up {result.deleted_count} old notifications",
            "deleted_count": result.deleted_count
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
