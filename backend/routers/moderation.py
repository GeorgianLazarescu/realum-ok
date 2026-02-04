from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
from core.auth import get_current_user
from core.database import supabase

router = APIRouter(prefix="/api/moderation", tags=["Moderation"])

class ReportCreate(BaseModel):
    content_type: str
    content_id: str
    reason: str
    description: Optional[str] = None
    evidence_urls: Optional[List[str]] = []

class ModerationAction(BaseModel):
    action: str
    reason: str
    duration_days: Optional[int] = None

@router.post("/report")
async def report_content(report: ReportCreate, current_user: dict = Depends(get_current_user)):
    try:
        data = {
            "reporter_id": current_user["id"],
            "content_type": report.content_type,
            "content_id": report.content_id,
            "reason": report.reason,
            "description": report.description,
            "evidence_urls": report.evidence_urls,
            "status": "pending",
            "severity": "medium"
        }

        result = supabase.table("content_reports").insert(data).execute()

        supabase.table("moderation_queue").insert({
            "report_id": result.data[0]["id"],
            "content_type": report.content_type,
            "content_id": report.content_id,
            "priority": "normal"
        }).execute()

        return {
            "message": "Content reported successfully",
            "report": result.data[0]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/queue")
async def get_moderation_queue(
    status: Optional[str] = "pending",
    priority: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    try:
        user_result = supabase.table("users").select("role").eq("id", current_user["id"]).execute()

        if not user_result.data or user_result.data[0].get("role") not in ["evaluator", "partner"]:
            raise HTTPException(status_code=403, detail="Only evaluators and partners can access moderation queue")

        query = supabase.table("moderation_queue").select("*, content_reports(*)")

        if status:
            query = query.eq("status", status)
        if priority:
            query = query.eq("priority", priority)

        result = query.order("created_at", desc=False).execute()

        return {"queue": result.data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/review/{report_id}")
async def review_report(
    report_id: str,
    action: ModerationAction,
    current_user: dict = Depends(get_current_user)
):
    try:
        user_result = supabase.table("users").select("role").eq("id", current_user["id"]).execute()

        if not user_result.data or user_result.data[0].get("role") not in ["evaluator", "partner"]:
            raise HTTPException(status_code=403, detail="Only evaluators and partners can review reports")

        report_result = supabase.table("content_reports").select("*").eq("id", report_id).execute()

        if not report_result.data:
            raise HTTPException(status_code=404, detail="Report not found")

        report = report_result.data[0]

        action_data = {
            "report_id": report_id,
            "moderator_id": current_user["id"],
            "action_taken": action.action,
            "reason": action.reason,
            "duration_days": action.duration_days
        }

        supabase.table("moderation_actions").insert(action_data).execute()

        if action.action == "remove":
            content_type = report["content_type"]
            content_id = report["content_id"]

            if content_type == "course":
                supabase.table("courses").update({"status": "removed"}).eq("id", content_id).execute()
            elif content_type == "project":
                supabase.table("projects").update({"status": "suspended"}).eq("id", content_id).execute()
            elif content_type == "comment":
                supabase.table("comments").update({"is_removed": True}).eq("id", content_id).execute()

        elif action.action == "warn":
            content_owner_result = None
            if report["content_type"] == "course":
                content_owner_result = supabase.table("courses").select("creator_id").eq("id", report["content_id"]).execute()
            elif report["content_type"] == "project":
                content_owner_result = supabase.table("projects").select("creator_id").eq("id", report["content_id"]).execute()

            if content_owner_result and content_owner_result.data:
                owner_id = content_owner_result.data[0].get("creator_id")
                supabase.table("user_warnings").insert({
                    "user_id": owner_id,
                    "reason": action.reason,
                    "issued_by": current_user["id"]
                }).execute()

        elif action.action == "ban":
            content_owner_result = None
            if report["content_type"] == "course":
                content_owner_result = supabase.table("courses").select("creator_id").eq("id", report["content_id"]).execute()
            elif report["content_type"] == "project":
                content_owner_result = supabase.table("projects").select("creator_id").eq("id", report["content_id"]).execute()

            if content_owner_result and content_owner_result.data:
                owner_id = content_owner_result.data[0].get("creator_id")
                ban_until = None
                if action.duration_days:
                    ban_until = (datetime.utcnow() + timedelta(days=action.duration_days)).isoformat()

                supabase.table("user_bans").insert({
                    "user_id": owner_id,
                    "reason": action.reason,
                    "banned_by": current_user["id"],
                    "ban_until": ban_until
                }).execute()

        supabase.table("content_reports").update({"status": "resolved"}).eq("id", report_id).execute()
        supabase.table("moderation_queue").update({"status": "completed"}).eq("report_id", report_id).execute()

        return {
            "message": "Moderation action completed",
            "action": action.action
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/my-reports")
async def get_my_reports(current_user: dict = Depends(get_current_user)):
    try:
        result = supabase.table("content_reports").select("*").eq("reporter_id", current_user["id"]).execute()
        return {"reports": result.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/stats")
async def get_moderation_stats(current_user: dict = Depends(get_current_user)):
    try:
        user_result = supabase.table("users").select("role").eq("id", current_user["id"]).execute()

        if not user_result.data or user_result.data[0].get("role") not in ["evaluator", "partner"]:
            raise HTTPException(status_code=403, detail="Only evaluators and partners can view moderation stats")

        all_reports = supabase.table("content_reports").select("*").execute()
        all_actions = supabase.table("moderation_actions").select("*").execute()

        total_reports = len(all_reports.data) if all_reports.data else 0

        status_breakdown = {}
        for report in all_reports.data if all_reports.data else []:
            status = report.get("status", "unknown")
            status_breakdown[status] = status_breakdown.get(status, 0) + 1

        action_breakdown = {}
        for action in all_actions.data if all_actions.data else []:
            action_taken = action.get("action_taken", "unknown")
            action_breakdown[action_taken] = action_breakdown.get(action_taken, 0) + 1

        return {
            "stats": {
                "total_reports": total_reports,
                "status_breakdown": status_breakdown,
                "action_breakdown": action_breakdown,
                "total_actions": len(all_actions.data) if all_actions.data else 0
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/auto-moderate")
async def auto_moderate_content(
    content_type: str,
    content_id: str,
    current_user: dict = Depends(get_current_user)
):
    try:
        content_text = ""

        if content_type == "course":
            course_result = supabase.table("courses").select("title, description").eq("id", content_id).execute()
            if course_result.data:
                content_text = f"{course_result.data[0].get('title', '')} {course_result.data[0].get('description', '')}"

        elif content_type == "comment":
            comment_result = supabase.table("comments").select("content").eq("id", content_id).execute()
            if comment_result.data:
                content_text = comment_result.data[0].get("content", "")

        banned_words = ["spam", "scam", "hack", "illegal"]
        violations = []

        for word in banned_words:
            if word.lower() in content_text.lower():
                violations.append(word)

        if violations:
            auto_report_data = {
                "reporter_id": "system",
                "content_type": content_type,
                "content_id": content_id,
                "reason": "auto_moderation",
                "description": f"Detected banned words: {', '.join(violations)}",
                "status": "pending",
                "severity": "high"
            }

            supabase.table("content_reports").insert(auto_report_data).execute()

            return {
                "flagged": True,
                "violations": violations,
                "message": "Content flagged for review"
            }

        return {
            "flagged": False,
            "message": "Content passed auto-moderation"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/banned-users")
async def get_banned_users(current_user: dict = Depends(get_current_user)):
    try:
        user_result = supabase.table("users").select("role").eq("id", current_user["id"]).execute()

        if not user_result.data or user_result.data[0].get("role") not in ["evaluator", "partner"]:
            raise HTTPException(status_code=403, detail="Only evaluators and partners can view banned users")

        result = supabase.table("user_bans").select("*, users(username, avatar)").execute()

        active_bans = []
        for ban in result.data if result.data else []:
            ban_until = ban.get("ban_until")
            if not ban_until or datetime.fromisoformat(ban_until) > datetime.utcnow():
                active_bans.append(ban)

        return {"banned_users": active_bans}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/unban/{user_id}")
async def unban_user(user_id: str, current_user: dict = Depends(get_current_user)):
    try:
        user_result = supabase.table("users").select("role").eq("id", current_user["id"]).execute()

        if not user_result.data or user_result.data[0].get("role") not in ["evaluator", "partner"]:
            raise HTTPException(status_code=403, detail="Only evaluators and partners can unban users")

        supabase.table("user_bans").delete().eq("user_id", user_id).execute()

        return {"message": "User unbanned successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
