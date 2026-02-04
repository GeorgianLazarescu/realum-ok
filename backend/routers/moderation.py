from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime, timezone, timedelta
import uuid
import re

from core.database import db
from core.auth import get_current_user, require_admin
from services.notification_service import send_notification

router = APIRouter(prefix="/moderation", tags=["Content Moderation"])

# Banned words list (can be configured in DB)
BANNED_WORDS = [
    "spam", "scam", "phishing", "hack", "exploit",
    # Add more as needed
]

# Spam patterns
SPAM_PATTERNS = [
    r"(https?://\S+){3,}",  # Multiple URLs
    r"([A-Z]{5,}\s*){3,}",  # ALL CAPS spam
    r"(.{1,3})\1{5,}",  # Repeated characters
]

class ModerationReport(BaseModel):
    content_type: str  # message, comment, profile, course, project
    content_id: str
    reason: str
    description: Optional[str] = None

class ModerationAction(BaseModel):
    action: str  # approve, reject, warn, ban, delete
    reason: Optional[str] = None
    ban_duration_days: Optional[int] = None

class ContentAnalysis(BaseModel):
    text: str

class AutoModRule(BaseModel):
    rule_type: str  # word_filter, spam_pattern, rate_limit
    pattern: str
    action: str  # flag, block, warn
    severity: str = "medium"

# ===================== CONTENT ANALYSIS =====================

def analyze_content(text: str) -> Dict:
    """Analyze content for potential violations"""
    issues = []
    severity = "clean"
    
    text_lower = text.lower()
    
    # Check banned words
    for word in BANNED_WORDS:
        if word in text_lower:
            issues.append({"type": "banned_word", "word": word})
            severity = "high"
    
    # Check spam patterns
    for pattern in SPAM_PATTERNS:
        if re.search(pattern, text):
            issues.append({"type": "spam_pattern", "pattern": pattern})
            if severity != "high":
                severity = "medium"
    
    # Check excessive caps
    caps_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)
    if caps_ratio > 0.7 and len(text) > 20:
        issues.append({"type": "excessive_caps", "ratio": caps_ratio})
        if severity == "clean":
            severity = "low"
    
    # Check for suspicious links
    url_count = len(re.findall(r'https?://\S+', text))
    if url_count > 3:
        issues.append({"type": "many_urls", "count": url_count})
        if severity == "clean":
            severity = "medium"
    
    return {
        "is_clean": len(issues) == 0,
        "severity": severity,
        "issues": issues,
        "score": 100 - (len(issues) * 20)  # Simple scoring
    }

@router.post("/analyze")
async def analyze_text(
    analysis: ContentAnalysis,
    current_user: dict = Depends(get_current_user)
):
    """Analyze text content for potential issues"""
    try:
        result = analyze_content(analysis.text)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ===================== REPORTING =====================

@router.post("/report")
async def report_content(
    report: ModerationReport,
    current_user: dict = Depends(get_current_user)
):
    """Report content for moderation"""
    try:
        report_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        report_data = {
            "id": report_id,
            "reporter_id": current_user["id"],
            "content_type": report.content_type,
            "content_id": report.content_id,
            "reason": report.reason,
            "description": report.description,
            "status": "pending",
            "created_at": now
        }

        await db.moderation_reports.insert_one(report_data)

        # Check if content has multiple reports
        report_count = await db.moderation_reports.count_documents({
            "content_id": report.content_id,
            "status": "pending"
        })

        # Auto-flag if multiple reports
        if report_count >= 3:
            await db.moderation_queue.update_one(
                {"content_id": report.content_id},
                {
                    "$set": {
                        "content_type": report.content_type,
                        "content_id": report.content_id,
                        "status": "flagged",
                        "report_count": report_count,
                        "priority": "high",
                        "updated_at": now
                    },
                    "$setOnInsert": {"id": str(uuid.uuid4()), "created_at": now}
                },
                upsert=True
            )

        return {
            "message": "Report submitted",
            "report_id": report_id
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/queue")
async def get_moderation_queue(
    status: Optional[str] = "pending",
    priority: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    current_user: dict = Depends(require_admin)
):
    """Get moderation queue (admin only)"""
    try:
        query = {}
        if status:
            query["status"] = status
        if priority:
            query["priority"] = priority

        items = await db.moderation_queue.find(
            query, {"_id": 0}
        ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)

        # Enrich with reports
        for item in items:
            reports = await db.moderation_reports.find(
                {"content_id": item["content_id"]},
                {"_id": 0}
            ).to_list(10)
            item["reports"] = reports

        total = await db.moderation_queue.count_documents(query)

        return {"queue": items, "total": total}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/action/{content_id}")
async def take_moderation_action(
    content_id: str,
    action: ModerationAction,
    current_user: dict = Depends(require_admin)
):
    """Take action on reported content (admin only)"""
    try:
        now = datetime.now(timezone.utc).isoformat()

        # Get queue item
        queue_item = await db.moderation_queue.find_one({"content_id": content_id})

        if not queue_item:
            raise HTTPException(status_code=404, detail="Content not in moderation queue")

        # Record action
        await db.moderation_actions.insert_one({
            "id": str(uuid.uuid4()),
            "content_id": content_id,
            "content_type": queue_item.get("content_type"),
            "action": action.action,
            "reason": action.reason,
            "moderator_id": current_user["id"],
            "created_at": now
        })

        # Update queue status
        await db.moderation_queue.update_one(
            {"content_id": content_id},
            {"$set": {
                "status": "resolved",
                "resolution": action.action,
                "resolved_by": current_user["id"],
                "resolved_at": now
            }}
        )

        # Update reports
        await db.moderation_reports.update_many(
            {"content_id": content_id, "status": "pending"},
            {"$set": {"status": "resolved", "resolution": action.action}}
        )

        # Execute action based on type
        if action.action == "delete":
            # Soft delete the content
            content_type = queue_item.get("content_type")
            collection_map = {
                "message": "chat_messages",
                "comment": "comments",
                "course": "courses",
                "project": "projects",
                "feedback": "feedback"
            }
            if content_type in collection_map:
                await db[collection_map[content_type]].update_one(
                    {"id": content_id},
                    {"$set": {"is_deleted": True, "deleted_by_moderation": True}}
                )

        elif action.action == "ban":
            # Get content creator and ban them
            # This would need to lookup the content to find the user
            pass

        elif action.action == "warn":
            # Send warning notification
            # Would need to lookup content creator
            pass

        return {
            "message": f"Action '{action.action}' taken on content",
            "content_id": content_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ===================== USER MODERATION =====================

@router.post("/users/{user_id}/warn")
async def warn_user(
    user_id: str,
    reason: str,
    current_user: dict = Depends(require_admin)
):
    """Issue a warning to a user"""
    try:
        now = datetime.now(timezone.utc).isoformat()

        # Record warning
        await db.user_warnings.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "reason": reason,
            "issued_by": current_user["id"],
            "created_at": now
        })

        # Get warning count
        warning_count = await db.user_warnings.count_documents({"user_id": user_id})

        # Notify user
        await send_notification(
            user_id=user_id,
            title="Warning Issued",
            message=f"You have received a warning: {reason}",
            notification_type="warning",
            category="security"
        )

        # Auto-ban after 3 warnings
        if warning_count >= 3:
            await db.users.update_one(
                {"id": user_id},
                {"$set": {
                    "is_banned": True,
                    "banned_at": now,
                    "ban_reason": "Automatic ban after 3 warnings"
                }}
            )

        return {
            "message": "Warning issued",
            "warning_count": warning_count,
            "auto_banned": warning_count >= 3
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/users/{user_id}/ban")
async def ban_user(
    user_id: str,
    reason: str,
    duration_days: Optional[int] = None,
    current_user: dict = Depends(require_admin)
):
    """Ban a user"""
    try:
        now = datetime.now(timezone.utc)
        expires_at = None
        
        if duration_days:
            expires_at = (now + timedelta(days=duration_days)).isoformat()

        await db.users.update_one(
            {"id": user_id},
            {"$set": {
                "is_banned": True,
                "banned_at": now.isoformat(),
                "ban_reason": reason,
                "ban_expires_at": expires_at,
                "banned_by": current_user["id"]
            }}
        )

        # Record ban
        await db.user_bans.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "reason": reason,
            "duration_days": duration_days,
            "expires_at": expires_at,
            "issued_by": current_user["id"],
            "created_at": now.isoformat()
        })

        return {
            "message": "User banned",
            "expires_at": expires_at,
            "permanent": duration_days is None
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/users/{user_id}/unban")
async def unban_user(
    user_id: str,
    current_user: dict = Depends(require_admin)
):
    """Unban a user"""
    try:
        await db.users.update_one(
            {"id": user_id},
            {"$set": {
                "is_banned": False,
                "unbanned_at": datetime.now(timezone.utc).isoformat(),
                "unbanned_by": current_user["id"]
            }}
        )

        return {"message": "User unbanned"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ===================== AUTO-MODERATION RULES =====================

@router.post("/rules")
async def create_automod_rule(
    rule: AutoModRule,
    current_user: dict = Depends(require_admin)
):
    """Create an auto-moderation rule"""
    try:
        rule_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        await db.automod_rules.insert_one({
            "id": rule_id,
            "rule_type": rule.rule_type,
            "pattern": rule.pattern,
            "action": rule.action,
            "severity": rule.severity,
            "is_active": True,
            "created_by": current_user["id"],
            "created_at": now
        })

        return {"message": "Rule created", "rule_id": rule_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/rules")
async def get_automod_rules(current_user: dict = Depends(require_admin)):
    """Get all auto-moderation rules"""
    try:
        rules = await db.automod_rules.find(
            {"is_active": True},
            {"_id": 0}
        ).to_list(100)

        return {"rules": rules}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/rules/{rule_id}")
async def delete_automod_rule(
    rule_id: str,
    current_user: dict = Depends(require_admin)
):
    """Delete an auto-moderation rule"""
    try:
        result = await db.automod_rules.update_one(
            {"id": rule_id},
            {"$set": {"is_active": False}}
        )

        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Rule not found")

        return {"message": "Rule deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ===================== STATS =====================

@router.get("/stats")
async def get_moderation_stats(current_user: dict = Depends(require_admin)):
    """Get moderation statistics"""
    try:
        total_reports = await db.moderation_reports.count_documents({})
        pending_reports = await db.moderation_reports.count_documents({"status": "pending"})
        resolved_reports = await db.moderation_reports.count_documents({"status": "resolved"})

        total_bans = await db.user_bans.count_documents({})
        active_bans = await db.users.count_documents({"is_banned": True})
        total_warnings = await db.user_warnings.count_documents({})

        # By reason
        reason_pipeline = [
            {"$group": {"_id": "$reason", "count": {"$sum": 1}}}
        ]
        reason_result = await db.moderation_reports.aggregate(reason_pipeline).to_list(None)
        by_reason = {item["_id"]: item["count"] for item in reason_result if item["_id"]}

        return {
            "stats": {
                "total_reports": total_reports,
                "pending_reports": pending_reports,
                "resolved_reports": resolved_reports,
                "total_bans": total_bans,
                "active_bans": active_bans,
                "total_warnings": total_warnings,
                "by_reason": by_reason
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/reasons")
async def get_report_reasons():
    """Get available report reasons"""
    return {
        "reasons": [
            {"key": "spam", "name": "Spam", "description": "Unsolicited promotional content"},
            {"key": "harassment", "name": "Harassment", "description": "Bullying or targeted harassment"},
            {"key": "inappropriate", "name": "Inappropriate Content", "description": "Adult or offensive content"},
            {"key": "misinformation", "name": "Misinformation", "description": "False or misleading information"},
            {"key": "scam", "name": "Scam/Fraud", "description": "Fraudulent activity or scams"},
            {"key": "impersonation", "name": "Impersonation", "description": "Pretending to be someone else"},
            {"key": "copyright", "name": "Copyright Violation", "description": "Unauthorized use of content"},
            {"key": "other", "name": "Other", "description": "Other violations"}
        ]
    }
