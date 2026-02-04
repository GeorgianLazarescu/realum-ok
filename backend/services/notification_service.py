from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
import uuid
import re

from core.database import db

async def send_notification(
    user_id: str,
    title: str,
    message: str,
    notification_type: str = "info",
    channel: str = "in_app",
    category: str = "general",
    action_url: Optional[str] = None,
    action_label: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    expires_in_days: Optional[int] = None
) -> str:
    """
    Send a notification to a user

    Args:
        user_id: Target user ID
        title: Notification title
        message: Notification message
        notification_type: Type of notification (info, success, warning, error, achievement, system)
        channel: Delivery channel (in_app, email, push, all)
        category: Notification category for filtering
        action_url: Optional URL for action button
        action_label: Optional label for action button
        metadata: Additional metadata as dict
        expires_in_days: Optional expiration in days

    Returns:
        notification_id: ID of created notification
    """
    notification_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    # Check user preferences
    prefs = await db.notification_preferences.find_one({"user_id": user_id}, {"_id": 0})

    if not prefs:
        # Create default preferences
        await db.notification_preferences.insert_one({
            "user_id": user_id,
            "email_enabled": True,
            "push_enabled": True,
            "in_app_enabled": True,
            "daily_digest": False,
            "weekly_digest": False,
            "muted_categories": [],
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        })
        prefs = {
            "email_enabled": True,
            "push_enabled": True,
            "in_app_enabled": True,
            "muted_categories": []
        }

    # Check if category is muted
    muted_categories = prefs.get("muted_categories", [])
    if category in muted_categories:
        return None

    # Check channel preferences
    if channel == "email" and not prefs.get("email_enabled", True):
        return None
    if channel == "push" and not prefs.get("push_enabled", True):
        return None
    if channel == "in_app" and not prefs.get("in_app_enabled", True):
        return None

    # Calculate expiration
    expires_at = None
    if expires_in_days:
        expires_at = (now + timedelta(days=expires_in_days)).isoformat()

    # Create notification
    await db.notifications.insert_one({
        "id": notification_id,
        "user_id": user_id,
        "type": notification_type,
        "title": title,
        "message": message,
        "channel": channel,
        "category": category,
        "action_url": action_url,
        "action_label": action_label,
        "is_read": False,
        "metadata": metadata or {},
        "created_at": now.isoformat(),
        "expires_at": expires_at
    })

    # Queue for processing if email or push
    if channel in ["email", "push", "all"]:
        await queue_notification(user_id, notification_id, priority=1)

    return notification_id

async def send_notification_from_template(
    user_id: str,
    template_key: str,
    variables: Dict[str, Any],
    channel: str = "in_app",
    action_url: Optional[str] = None,
    action_label: Optional[str] = None
) -> Optional[str]:
    """
    Send a notification using a predefined template

    Args:
        user_id: Target user ID
        template_key: Template key to use
        variables: Dictionary of variables to replace in template
        channel: Delivery channel
        action_url: Optional action URL
        action_label: Optional action label

    Returns:
        notification_id or None if template not found
    """
    template = await db.notification_templates.find_one({
        "template_key": template_key,
        "is_active": True
    })

    if not template:
        return None

    # Replace variables in title and message
    title = template["title_template"]
    message = template["message_template"]

    for key, value in variables.items():
        title = title.replace(f"{{{{{key}}}}}", str(value))
        message = message.replace(f"{{{{{key}}}}}", str(value))

    return await send_notification(
        user_id=user_id,
        title=title,
        message=message,
        notification_type="info",
        channel=channel or template.get("default_channel", "in_app"),
        category=template.get("category", "general"),
        action_url=action_url,
        action_label=action_label
    )

async def send_bulk_notification(
    user_ids: List[str],
    title: str,
    message: str,
    notification_type: str = "info",
    channel: str = "in_app",
    category: str = "general"
) -> int:
    """
    Send notifications to multiple users

    Returns:
        Number of notifications sent
    """
    count = 0
    for user_id in user_ids:
        notification_id = await send_notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            channel=channel,
            category=category
        )
        if notification_id:
            count += 1

    return count

async def queue_notification(
    user_id: str,
    notification_id: str,
    scheduled_for: Optional[datetime] = None,
    priority: int = 1
) -> str:
    """
    Queue a notification for processing

    Args:
        user_id: Target user ID
        notification_id: Notification to queue
        scheduled_for: When to send (default: now)
        priority: Priority level 1-5 (5 = highest)

    Returns:
        queue_id
    """
    queue_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    if not scheduled_for:
        scheduled_for = now

    await db.notification_queue.insert_one({
        "id": queue_id,
        "user_id": user_id,
        "notification_id": notification_id,
        "scheduled_for": scheduled_for.isoformat() if isinstance(scheduled_for, datetime) else scheduled_for,
        "priority": priority,
        "retry_count": 0,
        "max_retries": 3,
        "status": "pending",
        "created_at": now.isoformat()
    })

    return queue_id

async def mark_notification_read(notification_id: str, user_id: str) -> bool:
    """Mark a notification as read"""
    result = await db.notifications.update_one(
        {"id": notification_id, "user_id": user_id},
        {
            "$set": {
                "is_read": True,
                "read_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )

    return result.modified_count > 0

async def mark_all_read(user_id: str) -> int:
    """Mark all user notifications as read"""
    now = datetime.now(timezone.utc).isoformat()
    result = await db.notifications.update_many(
        {"user_id": user_id, "is_read": False},
        {
            "$set": {
                "is_read": True,
                "read_at": now
            }
        }
    )

    return result.modified_count

async def delete_notification(notification_id: str, user_id: str) -> bool:
    """Delete a notification"""
    result = await db.notifications.delete_one({
        "id": notification_id,
        "user_id": user_id
    })

    return result.deleted_count > 0

async def get_unread_count(user_id: str) -> int:
    """Get count of unread notifications"""
    count = await db.notifications.count_documents({
        "user_id": user_id,
        "is_read": False
    })

    return count

async def cleanup_old_notifications(days: int = 30) -> int:
    """Delete old read notifications"""
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.notifications.delete_many({
        "is_read": True,
        "created_at": {"$lt": cutoff_date.isoformat()}
    })

    return result.deleted_count
