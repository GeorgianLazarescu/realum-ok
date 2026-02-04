from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from core.auth import get_current_user, require_role
from core.database import supabase

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

class ReportCreate(BaseModel):
    name: str
    description: Optional[str] = None
    report_type: str
    metrics: List[str]
    filters: Optional[Dict[str, Any]] = None
    schedule: Optional[str] = None

class ExportRequest(BaseModel):
    format: str
    date_from: Optional[str] = None
    date_to: Optional[str] = None

@router.get("/dashboard")
async def get_dashboard_analytics(
    current_user: dict = Depends(get_current_user),
    time_range: str = Query("7d", regex="^(24h|7d|30d|90d|1y|all)$")
):
    try:
        now = datetime.utcnow()
        if time_range == "24h":
            start_date = now - timedelta(days=1)
        elif time_range == "7d":
            start_date = now - timedelta(days=7)
        elif time_range == "30d":
            start_date = now - timedelta(days=30)
        elif time_range == "90d":
            start_date = now - timedelta(days=90)
        elif time_range == "1y":
            start_date = now - timedelta(days=365)
        else:
            start_date = datetime(2020, 1, 1)

        users_result = supabase.table("users").select("id, created_at").gte("created_at", start_date.isoformat()).execute()
        total_users = len(users_result.data) if users_result.data else 0

        courses_result = supabase.table("courses").select("id").execute()
        total_courses = len(courses_result.data) if courses_result.data else 0

        projects_result = supabase.table("projects").select("id").execute()
        total_projects = len(projects_result.data) if projects_result.data else 0

        transactions_result = supabase.table("transactions").select("amount").gte("created_at", start_date.isoformat()).execute()
        total_volume = sum(float(t["amount"]) for t in transactions_result.data) if transactions_result.data else 0

        proposals_result = supabase.table("proposals").select("id, status").execute()
        active_proposals = len([p for p in proposals_result.data if p["status"] == "active"]) if proposals_result.data else 0

        enrollments_result = supabase.table("user_courses").select("id, progress").execute()
        avg_completion = sum(float(e.get("progress", 0)) for e in enrollments_result.data) / len(enrollments_result.data) if enrollments_result.data else 0

        return {
            "overview": {
                "total_users": total_users,
                "total_courses": total_courses,
                "total_projects": total_projects,
                "token_volume": total_volume,
                "active_proposals": active_proposals,
                "avg_course_completion": round(avg_completion, 2)
            },
            "time_range": time_range
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/user-growth")
async def get_user_growth(
    current_user: dict = Depends(get_current_user),
    days: int = Query(30, ge=1, le=365)
):
    try:
        start_date = datetime.utcnow() - timedelta(days=days)

        users_result = supabase.table("users").select("created_at").gte("created_at", start_date.isoformat()).execute()

        growth_data = {}
        for user in users_result.data if users_result.data else []:
            date = user["created_at"][:10]
            growth_data[date] = growth_data.get(date, 0) + 1

        return {
            "growth_data": [{"date": k, "count": v} for k, v in sorted(growth_data.items())],
            "total_new_users": len(users_result.data) if users_result.data else 0
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/token-economy")
async def get_token_economy_analytics(current_user: dict = Depends(get_current_user)):
    try:
        transactions_result = supabase.table("transactions").select("*").execute()

        total_supply = 0
        total_burned = 0
        total_transactions = len(transactions_result.data) if transactions_result.data else 0

        for tx in transactions_result.data if transactions_result.data else []:
            if tx.get("type") == "burn":
                total_burned += float(tx.get("amount", 0))
            total_supply += float(tx.get("amount", 0))

        users_result = supabase.table("users").select("realum_balance").execute()
        circulating_supply = sum(float(u.get("realum_balance", 0)) for u in users_result.data) if users_result.data else 0

        return {
            "token_economy": {
                "total_supply": total_supply,
                "circulating_supply": circulating_supply,
                "total_burned": total_burned,
                "total_transactions": total_transactions,
                "holders": len(users_result.data) if users_result.data else 0
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/course-analytics")
async def get_course_analytics(current_user: dict = Depends(get_current_user)):
    try:
        courses_result = supabase.table("courses").select("id, title, creator_id, status").execute()
        enrollments_result = supabase.table("user_courses").select("course_id, progress, completed").execute()

        course_stats = {}
        for enrollment in enrollments_result.data if enrollments_result.data else []:
            course_id = enrollment["course_id"]
            if course_id not in course_stats:
                course_stats[course_id] = {
                    "enrollments": 0,
                    "completions": 0,
                    "total_progress": 0
                }
            course_stats[course_id]["enrollments"] += 1
            course_stats[course_id]["total_progress"] += float(enrollment.get("progress", 0))
            if enrollment.get("completed"):
                course_stats[course_id]["completions"] += 1

        analytics = []
        for course in courses_result.data if courses_result.data else []:
            stats = course_stats.get(course["id"], {"enrollments": 0, "completions": 0, "total_progress": 0})
            avg_progress = stats["total_progress"] / stats["enrollments"] if stats["enrollments"] > 0 else 0

            analytics.append({
                "course_id": course["id"],
                "course_title": course["title"],
                "enrollments": stats["enrollments"],
                "completions": stats["completions"],
                "completion_rate": round(stats["completions"] / stats["enrollments"] * 100, 2) if stats["enrollments"] > 0 else 0,
                "avg_progress": round(avg_progress, 2)
            })

        return {"course_analytics": analytics}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/dao-activity")
async def get_dao_activity(current_user: dict = Depends(get_current_user)):
    try:
        proposals_result = supabase.table("proposals").select("*").execute()
        votes_result = supabase.table("votes").select("*").execute()

        total_proposals = len(proposals_result.data) if proposals_result.data else 0
        total_votes = len(votes_result.data) if votes_result.data else 0

        status_breakdown = {}
        for proposal in proposals_result.data if proposals_result.data else []:
            status = proposal.get("status", "unknown")
            status_breakdown[status] = status_breakdown.get(status, 0) + 1

        return {
            "dao_activity": {
                "total_proposals": total_proposals,
                "total_votes": total_votes,
                "status_breakdown": status_breakdown,
                "avg_votes_per_proposal": round(total_votes / total_proposals, 2) if total_proposals > 0 else 0
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/reports")
async def create_custom_report(
    report: ReportCreate,
    current_user: dict = Depends(get_current_user)
):
    try:
        data = {
            "user_id": current_user["id"],
            "name": report.name,
            "description": report.description,
            "report_type": report.report_type,
            "metrics": report.metrics,
            "filters": report.filters,
            "schedule": report.schedule
        }

        result = supabase.table("custom_reports").insert(data).execute()

        return {"message": "Report created", "report": result.data[0]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/reports")
async def get_custom_reports(current_user: dict = Depends(get_current_user)):
    try:
        result = supabase.table("custom_reports").select("*").eq("user_id", current_user["id"]).execute()
        return {"reports": result.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/export")
async def export_analytics(
    export_req: ExportRequest,
    current_user: dict = Depends(get_current_user)
):
    try:
        users_result = supabase.table("users").select("*").execute()
        courses_result = supabase.table("courses").select("*").execute()
        transactions_result = supabase.table("transactions").select("*").execute()

        data = {
            "users": users_result.data,
            "courses": courses_result.data,
            "transactions": transactions_result.data,
            "exported_at": datetime.utcnow().isoformat(),
            "format": export_req.format
        }

        return {
            "message": "Data exported successfully",
            "format": export_req.format,
            "data": data
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/engagement-metrics")
async def get_engagement_metrics(current_user: dict = Depends(get_current_user)):
    try:
        daily_rewards_result = supabase.table("daily_rewards").select("*").execute()
        referrals_result = supabase.table("referrals").select("*").execute()
        achievements_result = supabase.table("user_achievements").select("*").execute()

        total_daily_claims = len(daily_rewards_result.data) if daily_rewards_result.data else 0
        total_referrals = len(referrals_result.data) if referrals_result.data else 0
        total_achievements = len(achievements_result.data) if achievements_result.data else 0

        max_streak = max((r.get("streak", 0) for r in daily_rewards_result.data), default=0) if daily_rewards_result.data else 0

        return {
            "engagement": {
                "daily_claims": total_daily_claims,
                "referrals": total_referrals,
                "achievements_earned": total_achievements,
                "max_streak": max_streak
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
