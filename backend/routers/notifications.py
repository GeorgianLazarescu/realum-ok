from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel
import uuid

from core.database import db
from core.auth import get_current_user, admin_required
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

class NotificationPreferencesUpdate(BaseModel):
    email_enabled: Optional[bool] = None
    push_enabled: Optional[bool] = None
    in_app_enabled: Optional[bool] = None
    daily_digest: Optional[bool] = None
    weekly_digest: Optional[bool] = None
    muted_categories: Optional[List[str]] = None

class NotificationCreate(BaseModel):
    title: str
    message: str
    notification_type: str = "info"
    channel: str = "in_app"
    category: str = "general"
    action_url: Optional[str] = None
    action_label: Optional[str] = None

@router.get("/")
async def get_notifications(
    skip: int = 0,
    limit: int = 20,
    unread_only: bool = False,
    category: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get notifications for current user"""
    user_id = current_user["id"]

    query = {"user_id": user_id}

    if unread_only:
        query["is_read"] = False

    if category:
        query["category"] = category

    # Get notifications
    notifications = await db.notifications.find(
        query, {"_id": 0}
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)

    # Get unread count
    unread_count = await get_unread_count(user_id)

    return {
        "notifications": notifications,
        "unread_count": unread_count,
        "total": len(notifications)
    }

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
async def delete_notification_endpoint(
    notification_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a notification"""
    success = await delete_notification(notification_id, current_user["id"])

    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")

    return {"message": "Notification deleted"}

@router.get("/preferences")
async def get_notification_preferences(current_user: dict = Depends(get_current_user)):
    """Get notification preferences for current user"""
    user_id = current_user["id"]

    prefs = await db.notification_preferences.find_one(
        {"user_id": user_id},
        {"_id": 0}
    )

    if not prefs:
        # Return defaults
        return {
            "email_enabled": True,
            "push_enabled": True,
            "in_app_enabled": True,
            "daily_digest": False,
            "weekly_digest": False,
            "muted_categories": []
        }

    return prefs

@router.patch("/preferences")
async def update_notification_preferences(
    preferences: NotificationPreferencesUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update notification preferences"""
    user_id = current_user["id"]

    update_data = preferences.dict(exclude_unset=True)

    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided")

    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

    await db.notification_preferences.update_one(
        {"user_id": user_id},
        {"$set": update_data},
        upsert=True
    )

    return {"message": "Preferences updated successfully"}

@router.get("/categories")
async def get_notification_categories():
    """Get all notification categories"""
    categories = [
        {"key": "general", "name": "General", "description": "General platform notifications"},
        {"key": "rewards", "name": "Rewards", "description": "Daily rewards and bonuses"},
        {"key": "education", "name": "Education", "description": "Course and learning updates"},
        {"key": "jobs", "name": "Jobs", "description": "Job applications and assignments"},
        {"key": "governance", "name": "Governance", "description": "DAO proposals and voting"},
        {"key": "transactions", "name": "Transactions", "description": "Token transfers and payments"},
        {"key": "achievements", "name": "Achievements", "description": "Badges, levels, and milestones"},
        {"key": "projects", "name": "Projects", "description": "Project updates and collaboration"},
        {"key": "social", "name": "Social", "description": "Comments, likes, and follows"},
        {"key": "system", "name": "System", "description": "System announcements"}
    ]

    return {"categories": categories}

@router.post("/test")
async def send_test_notification(current_user: dict = Depends(get_current_user)):
    """Send a test notification to current user"""
    notification_id = await send_notification(
        user_id=current_user["id"],
        title="Test Notification",
        message="This is a test notification from REALUM",
        notification_type="info",
        channel="in_app",
        category="system"
    )

    return {
        "message": "Test notification sent",
        "notification_id": notification_id
    }

@router.post("/broadcast")
async def broadcast_notification(
    notification: NotificationCreate,
    current_user: dict = Depends(admin_required)
):
    """Broadcast notification to all users (admin only)"""
    # Get all user IDs
    users = await db.users.find({}, {"_id": 0, "id": 1}).to_list(1000)
    user_ids = [user["id"] for user in users]

    count = await send_bulk_notification(
        user_ids=user_ids,
        title=notification.title,
        message=notification.message,
        notification_type=notification.notification_type,
        channel=notification.channel,
        category=notification.category
    )

    return {
        "message": f"Notification broadcasted to {count} users",
        "count": count
    }

@router.get("/templates")
async def get_notification_templates():
    """Get all notification templates"""
    templates = await db.notification_templates.find(
        {"is_active": True},
        {"_id": 0}
    ).to_list(50)

    return {"templates": templates}
