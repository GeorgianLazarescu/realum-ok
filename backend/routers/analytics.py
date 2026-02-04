from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
import uuid
from core.auth import get_current_user, require_admin
from core.database import db

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

class ReportCreate(BaseModel):
    name: str
    description: Optional[str] = None
    report_type: str
    metrics: List[str]
    filters: Optional[Dict[str, Any]] = None
    schedule: Optional[str] = None

class ExportRequest(BaseModel):
    format: str = "json"
    date_from: Optional[str] = None
    date_to: Optional[str] = None

@router.get("/dashboard")
async def get_dashboard_analytics(
    current_user: dict = Depends(get_current_user),
    time_range: str = Query("7d", regex="^(24h|7d|30d|90d|1y|all)$")
):
    """Get dashboard analytics overview"""
    try:
        now = datetime.now(timezone.utc)
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
            start_date = datetime(2020, 1, 1, tzinfo=timezone.utc)

        # User stats
        total_users = await db.users.count_documents({})
        new_users = await db.users.count_documents({"created_at": {"$gte": start_date.isoformat()}})

        # Course stats
        total_courses = await db.courses.count_documents({})
        
        # Project stats
        total_projects = await db.projects.count_documents({})

        # Transaction volume
        tx_pipeline = [
            {"$match": {"timestamp": {"$gte": start_date.isoformat()}}},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
        ]
        tx_result = await db.transactions.aggregate(tx_pipeline).to_list(1)
        total_volume = tx_result[0]["total"] if tx_result else 0

        # Active proposals
        active_proposals = await db.proposals.count_documents({"status": "active"})

        # Average course completion
        completion_pipeline = [
            {"$group": {"_id": None, "avg_progress": {"$avg": "$progress"}}}
        ]
        completion_result = await db.user_courses.aggregate(completion_pipeline).to_list(1)
        avg_completion = completion_result[0]["avg_progress"] if completion_result else 0

        return {
            "overview": {
                "total_users": total_users,
                "new_users": new_users,
                "total_courses": total_courses,
                "total_projects": total_projects,
                "token_volume": total_volume,
                "active_proposals": active_proposals,
                "avg_course_completion": round(avg_completion or 0, 2)
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
    """Get user growth data over time"""
    try:
        start_date = datetime.now(timezone.utc) - timedelta(days=days)

        users = await db.users.find(
            {"created_at": {"$gte": start_date.isoformat()}},
            {"_id": 0, "created_at": 1}
        ).to_list(None)

        growth_data = {}
        for user in users:
            date = user["created_at"][:10] if user.get("created_at") else None
            if date:
                growth_data[date] = growth_data.get(date, 0) + 1

        return {
            "growth_data": [{"date": k, "count": v} for k, v in sorted(growth_data.items())],
            "total_new_users": len(users)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/token-economy")
async def get_token_economy_analytics(current_user: dict = Depends(get_current_user)):
    """Get token economy analytics"""
    try:
        # Total transactions
        total_transactions = await db.transactions.count_documents({})

        # Total burned
        burn_pipeline = [
            {"$group": {"_id": None, "total": {"$sum": "$burned"}}}
        ]
        burn_result = await db.transactions.aggregate(burn_pipeline).to_list(1)
        total_burned = burn_result[0]["total"] if burn_result else 0

        # Get burn records
        burns_pipeline = [
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
        ]
        burns_result = await db.burns.aggregate(burns_pipeline).to_list(1)
        total_burned += burns_result[0]["total"] if burns_result else 0

        # Circulating supply
        supply_pipeline = [
            {"$group": {"_id": None, "total": {"$sum": "$realum_balance"}}}
        ]
        supply_result = await db.users.aggregate(supply_pipeline).to_list(1)
        circulating_supply = supply_result[0]["total"] if supply_result else 0

        # Total holders
        holders = await db.users.count_documents({"realum_balance": {"$gt": 0}})

        return {
            "token_economy": {
                "circulating_supply": circulating_supply,
                "total_burned": total_burned,
                "total_transactions": total_transactions,
                "holders": holders,
                "burn_rate": 0.02  # 2%
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/course-analytics")
async def get_course_analytics(current_user: dict = Depends(get_current_user)):
    """Get course analytics"""
    try:
        courses = await db.courses.find({}, {"_id": 0}).to_list(100)
        
        analytics = []
        for course in courses:
            course_id = course.get("id")
            
            # Get enrollment stats
            enrollments = await db.user_courses.count_documents({"course_id": course_id})
            completions = await db.user_courses.count_documents({"course_id": course_id, "completed": True})
            
            # Average progress
            progress_pipeline = [
                {"$match": {"course_id": course_id}},
                {"$group": {"_id": None, "avg_progress": {"$avg": "$progress"}}}
            ]
            progress_result = await db.user_courses.aggregate(progress_pipeline).to_list(1)
            avg_progress = progress_result[0]["avg_progress"] if progress_result else 0

            analytics.append({
                "course_id": course_id,
                "course_title": course.get("title"),
                "enrollments": enrollments,
                "completions": completions,
                "completion_rate": round(completions / enrollments * 100, 2) if enrollments > 0 else 0,
                "avg_progress": round(avg_progress or 0, 2)
            })

        return {"course_analytics": analytics}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/dao-activity")
async def get_dao_activity(current_user: dict = Depends(get_current_user)):
    """Get DAO activity analytics"""
    try:
        total_proposals = await db.proposals.count_documents({})
        total_votes = await db.votes.count_documents({})

        # Status breakdown
        status_pipeline = [
            {"$group": {"_id": "$status", "count": {"$sum": 1}}}
        ]
        status_result = await db.proposals.aggregate(status_pipeline).to_list(None)
        status_breakdown = {item["_id"]: item["count"] for item in status_result if item["_id"]}

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
    """Create a custom analytics report"""
    try:
        report_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        report_data = {
            "id": report_id,
            "user_id": current_user["id"],
            "name": report.name,
            "description": report.description,
            "report_type": report.report_type,
            "metrics": report.metrics,
            "filters": report.filters,
            "schedule": report.schedule,
            "created_at": now,
            "updated_at": now
        }

        await db.custom_reports.insert_one(report_data)

        return {"message": "Report created", "report_id": report_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/reports")
async def get_custom_reports(current_user: dict = Depends(get_current_user)):
    """Get user's custom reports"""
    try:
        reports = await db.custom_reports.find(
            {"user_id": current_user["id"]},
            {"_id": 0}
        ).to_list(50)

        return {"reports": reports}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/export")
async def export_analytics(
    export_req: ExportRequest,
    current_user: dict = Depends(get_current_user)
):
    """Export analytics data"""
    try:
        # Build query based on date filters
        query = {}
        if export_req.date_from:
            query["created_at"] = {"$gte": export_req.date_from}
        if export_req.date_to:
            if "created_at" in query:
                query["created_at"]["$lte"] = export_req.date_to
            else:
                query["created_at"] = {"$lte": export_req.date_to}

        users = await db.users.find(query, {"_id": 0, "password": 0}).to_list(1000)
        courses = await db.courses.find({}, {"_id": 0}).to_list(100)
        transactions = await db.transactions.find(query, {"_id": 0}).to_list(1000)

        data = {
            "users_count": len(users),
            "courses_count": len(courses),
            "transactions_count": len(transactions),
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "format": export_req.format
        }

        if export_req.format == "detailed":
            data["users"] = users
            data["courses"] = courses
            data["transactions"] = transactions

        return {
            "message": "Data exported successfully",
            "data": data
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/engagement-metrics")
async def get_engagement_metrics(current_user: dict = Depends(get_current_user)):
    """Get user engagement metrics"""
    try:
        total_daily_claims = await db.daily_rewards.count_documents({})
        total_referrals = await db.referrals.count_documents({})
        total_achievements = await db.user_achievements.count_documents({})

        # Max streak
        streak_pipeline = [
            {"$group": {"_id": None, "max_streak": {"$max": "$streak"}}}
        ]
        streak_result = await db.daily_rewards.aggregate(streak_pipeline).to_list(1)
        max_streak = streak_result[0]["max_streak"] if streak_result else 0

        return {
            "engagement": {
                "daily_claims": total_daily_claims,
                "referrals": total_referrals,
                "achievements_earned": total_achievements,
                "max_streak": max_streak or 0
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/platform-health")
async def get_platform_health(current_user: dict = Depends(require_admin)):
    """Get platform health metrics (admin only)"""
    try:
        # Active users (logged in within 7 days)
        week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        active_users = await db.users.count_documents({"last_login": {"$gte": week_ago}})
        
        # Error rate (from logs if available)
        total_users = await db.users.count_documents({})
        
        # Pending items
        pending_proposals = await db.proposals.count_documents({"status": "active"})
        pending_disputes = await db.disputes.count_documents({"status": "pending"})

        return {
            "platform_health": {
                "active_users_7d": active_users,
                "total_users": total_users,
                "pending_proposals": pending_proposals,
                "pending_disputes": pending_disputes,
                "status": "healthy"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
