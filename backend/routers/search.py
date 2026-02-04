from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import uuid
import re

from core.database import db
from core.auth import get_current_user, require_admin

router = APIRouter(prefix="/search", tags=["Search & Discovery"])

class SearchQuery(BaseModel):
    query: str
    types: List[str] = []  # users, courses, projects, jobs, proposals
    filters: Optional[dict] = None

# ===================== UNIFIED SEARCH =====================

@router.get("/")
async def unified_search(
    q: str = Query(..., min_length=2, description="Search query"),
    types: Optional[str] = Query(None, description="Comma-separated types: users,courses,projects,jobs,proposals"),
    limit: int = Query(10, le=50),
    current_user: dict = Depends(get_current_user)
):
    """Search across all content types"""
    try:
        search_types = types.split(",") if types else ["users", "courses", "projects", "jobs", "proposals"]
        results = {}
        
        # Create case-insensitive regex pattern
        pattern = {"$regex": q, "$options": "i"}
        
        if "users" in search_types:
            users = await db.users.find(
                {"$or": [
                    {"username": pattern},
                    {"full_name": pattern},
                    {"bio": pattern}
                ]},
                {"_id": 0, "password": 0, "two_factor_secret": 0}
            ).limit(limit).to_list(limit)
            results["users"] = users
        
        if "courses" in search_types:
            courses = await db.courses.find(
                {"$or": [
                    {"title": pattern},
                    {"description": pattern},
                    {"category": pattern}
                ]},
                {"_id": 0}
            ).limit(limit).to_list(limit)
            results["courses"] = courses
        
        if "projects" in search_types:
            projects = await db.projects.find(
                {"$or": [
                    {"title": pattern},
                    {"description": pattern},
                    {"category": pattern}
                ]},
                {"_id": 0}
            ).limit(limit).to_list(limit)
            results["projects"] = projects
        
        if "jobs" in search_types:
            jobs = await db.jobs.find(
                {"$or": [
                    {"title": pattern},
                    {"description": pattern},
                    {"zone": pattern}
                ]},
                {"_id": 0}
            ).limit(limit).to_list(limit)
            results["jobs"] = jobs
        
        if "proposals" in search_types:
            proposals = await db.proposals.find(
                {"$or": [
                    {"title": pattern},
                    {"description": pattern}
                ]},
                {"_id": 0}
            ).limit(limit).to_list(limit)
            results["proposals"] = proposals
        
        # Count total results
        total = sum(len(v) for v in results.values())
        
        return {
            "query": q,
            "results": results,
            "total": total
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/users")
async def search_users(
    q: str = Query(..., min_length=2),
    role: Optional[str] = None,
    min_level: Optional[int] = None,
    skills: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """Search users with filters"""
    try:
        pattern = {"$regex": q, "$options": "i"}
        query = {
            "$or": [
                {"username": pattern},
                {"full_name": pattern},
                {"bio": pattern}
            ]
        }
        
        if role:
            query["role"] = role
        if min_level:
            query["level"] = {"$gte": min_level}
        if skills:
            skill_list = skills.split(",")
            query["skills"] = {"$in": skill_list}
        
        users = await db.users.find(
            query,
            {"_id": 0, "password": 0, "two_factor_secret": 0, "two_factor_backup_codes": 0}
        ).skip(skip).limit(limit).to_list(limit)
        
        total = await db.users.count_documents(query)
        
        return {"users": users, "total": total}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/courses")
async def search_courses(
    q: str = Query(..., min_length=2),
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
    min_xp: Optional[int] = None,
    skip: int = 0,
    limit: int = 20
):
    """Search courses with filters"""
    try:
        pattern = {"$regex": q, "$options": "i"}
        query = {
            "$or": [
                {"title": pattern},
                {"description": pattern}
            ]
        }
        
        if category:
            query["category"] = category
        if difficulty:
            query["difficulty"] = difficulty
        if min_xp:
            query["xp_reward"] = {"$gte": min_xp}
        
        courses = await db.courses.find(
            query,
            {"_id": 0}
        ).skip(skip).limit(limit).to_list(limit)
        
        total = await db.courses.count_documents(query)
        
        return {"courses": courses, "total": total}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/projects")
async def search_projects(
    q: str = Query(..., min_length=2),
    status: Optional[str] = None,
    category: Optional[str] = None,
    looking_for: Optional[str] = None,
    skip: int = 0,
    limit: int = 20
):
    """Search projects with filters"""
    try:
        pattern = {"$regex": q, "$options": "i"}
        query = {
            "$or": [
                {"title": pattern},
                {"description": pattern}
            ]
        }
        
        if status:
            query["status"] = status
        if category:
            query["category"] = category
        if looking_for:
            query["looking_for"] = {"$in": [looking_for]}
        
        projects = await db.projects.find(
            query,
            {"_id": 0}
        ).skip(skip).limit(limit).to_list(limit)
        
        total = await db.projects.count_documents(query)
        
        return {"projects": projects, "total": total}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/jobs")
async def search_jobs(
    q: str = Query(..., min_length=2),
    zone: Optional[str] = None,
    status: Optional[str] = "open",
    min_reward: Optional[float] = None,
    skip: int = 0,
    limit: int = 20
):
    """Search jobs with filters"""
    try:
        pattern = {"$regex": q, "$options": "i"}
        query = {
            "$or": [
                {"title": pattern},
                {"description": pattern}
            ]
        }
        
        if zone:
            query["zone"] = zone
        if status:
            query["status"] = status
        if min_reward:
            query["reward"] = {"$gte": min_reward}
        
        jobs = await db.jobs.find(
            query,
            {"_id": 0}
        ).skip(skip).limit(limit).to_list(limit)
        
        total = await db.jobs.count_documents(query)
        
        return {"jobs": jobs, "total": total}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ===================== SUGGESTIONS & AUTOCOMPLETE =====================

@router.get("/suggest")
async def get_search_suggestions(
    q: str = Query(..., min_length=1),
    limit: int = 5,
    current_user: dict = Depends(get_current_user)
):
    """Get search suggestions for autocomplete"""
    try:
        pattern = {"$regex": f"^{re.escape(q)}", "$options": "i"}
        suggestions = []
        
        # Get user suggestions
        users = await db.users.find(
            {"username": pattern},
            {"_id": 0, "username": 1}
        ).limit(limit).to_list(limit)
        suggestions.extend([{"type": "user", "text": u["username"]} for u in users])
        
        # Get course suggestions
        courses = await db.courses.find(
            {"title": pattern},
            {"_id": 0, "title": 1}
        ).limit(limit).to_list(limit)
        suggestions.extend([{"type": "course", "text": c["title"]} for c in courses])
        
        # Get project suggestions
        projects = await db.projects.find(
            {"title": pattern},
            {"_id": 0, "title": 1}
        ).limit(limit).to_list(limit)
        suggestions.extend([{"type": "project", "text": p["title"]} for p in projects])
        
        return {"suggestions": suggestions[:limit * 2]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ===================== TRENDING & POPULAR =====================

@router.get("/trending")
async def get_trending(
    period: str = Query("week", regex="^(day|week|month)$"),
    current_user: dict = Depends(get_current_user)
):
    """Get trending content"""
    try:
        if period == "day":
            cutoff = datetime.now(timezone.utc) - timedelta(days=1)
        elif period == "week":
            cutoff = datetime.now(timezone.utc) - timedelta(weeks=1)
        else:
            cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        
        cutoff_str = cutoff.isoformat()
        
        # Trending courses (most enrolled)
        courses = await db.courses.find(
            {},
            {"_id": 0, "id": 1, "title": 1, "category": 1}
        ).sort("enrolled_count", -1).limit(5).to_list(5)
        
        # Active proposals
        proposals = await db.proposals.find(
            {"status": "active"},
            {"_id": 0, "id": 1, "title": 1, "voter_count": 1}
        ).sort("voter_count", -1).limit(5).to_list(5)
        
        # New projects
        projects = await db.projects.find(
            {"created_at": {"$gte": cutoff_str}},
            {"_id": 0, "id": 1, "title": 1}
        ).sort("created_at", -1).limit(5).to_list(5)
        
        # Active bounties
        bounties = await db.bounties.find(
            {"status": "open"},
            {"_id": 0, "id": 1, "title": 1, "reward_amount": 1}
        ).sort("reward_amount", -1).limit(5).to_list(5)
        
        return {
            "trending": {
                "courses": courses,
                "proposals": proposals,
                "projects": projects,
                "bounties": bounties
            },
            "period": period
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/discover")
async def discover_content(current_user: dict = Depends(get_current_user)):
    """Personalized content discovery based on user profile"""
    try:
        user_id = current_user["id"]
        user_skills = current_user.get("skills", [])
        user_role = current_user.get("role", "citizen")
        
        recommendations = {}
        
        # Courses matching user skills/interests
        if user_skills:
            recommended_courses = await db.courses.find(
                {"tags": {"$in": user_skills}},
                {"_id": 0}
            ).limit(5).to_list(5)
        else:
            recommended_courses = await db.courses.find(
                {},
                {"_id": 0}
            ).sort("enrolled_count", -1).limit(5).to_list(5)
        recommendations["courses"] = recommended_courses
        
        # Jobs matching skills
        recommended_jobs = await db.jobs.find(
            {"status": "open"},
            {"_id": 0}
        ).limit(5).to_list(5)
        recommendations["jobs"] = recommended_jobs
        
        # Projects looking for user's role/skills
        recommended_projects = await db.projects.find(
            {"status": "active"},
            {"_id": 0}
        ).limit(5).to_list(5)
        recommendations["projects"] = recommended_projects
        
        # Users with similar interests
        if user_skills:
            similar_users = await db.users.find(
                {
                    "skills": {"$in": user_skills},
                    "id": {"$ne": user_id}
                },
                {"_id": 0, "username": 1, "avatar_url": 1, "skills": 1, "id": 1}
            ).limit(5).to_list(5)
        else:
            similar_users = []
        recommendations["users"] = similar_users
        
        return {"recommendations": recommendations}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ===================== SEARCH HISTORY =====================

@router.get("/history")
async def get_search_history(
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """Get user's search history"""
    try:
        history = await db.search_history.find(
            {"user_id": current_user["id"]},
            {"_id": 0}
        ).sort("searched_at", -1).limit(limit).to_list(limit)
        
        return {"history": history}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/history")
async def clear_search_history(current_user: dict = Depends(get_current_user)):
    """Clear user's search history"""
    try:
        result = await db.search_history.delete_many({"user_id": current_user["id"]})
        return {"message": f"Cleared {result.deleted_count} searches"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/filters")
async def get_search_filters():
    """Get available search filters"""
    return {
        "filters": {
            "users": {
                "roles": ["citizen", "expert", "educator", "entrepreneur", "admin"],
                "levels": list(range(1, 101)),
                "skills": ["programming", "design", "marketing", "finance", "legal", "community"]
            },
            "courses": {
                "categories": ["blockchain", "programming", "business", "design", "finance"],
                "difficulty": ["beginner", "intermediate", "advanced"]
            },
            "projects": {
                "status": ["active", "completed", "paused"],
                "categories": ["defi", "nft", "infrastructure", "community", "education"]
            },
            "jobs": {
                "zones": ["education", "tech", "business", "creative", "community", "governance"],
                "status": ["open", "in_progress", "completed"]
            }
        }
    }
