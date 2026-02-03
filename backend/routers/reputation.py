from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime, timedelta
from backend.core.auth import get_current_user
from backend.core.database import supabase

router = APIRouter(prefix="/api/reputation", tags=["Reputation"])

class ReputationUpdate(BaseModel):
    target_user_id: str
    category: str
    points: int
    reason: str

@router.get("/score/{user_id}")
async def get_reputation_score(user_id: str):
    try:
        reputation_result = supabase.table("reputation_scores").select("*").eq("user_id", user_id).execute()

        if not reputation_result.data:
            return {
                "user_id": user_id,
                "total_score": 0,
                "breakdown": {}
            }

        total_score = 0
        breakdown = {}

        for rep in reputation_result.data:
            category = rep.get("category", "general")
            points = rep.get("points", 0)
            breakdown[category] = breakdown.get(category, 0) + points
            total_score += points

        return {
            "user_id": user_id,
            "total_score": total_score,
            "breakdown": breakdown
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/my-reputation")
async def get_my_reputation(current_user: dict = Depends(get_current_user)):
    try:
        reputation_result = supabase.table("reputation_scores").select("*").eq("user_id", current_user["id"]).execute()

        courses_taught = supabase.table("courses").select("id").eq("creator_id", current_user["id"]).execute()
        courses_completed = supabase.table("user_courses").select("id").eq("user_id", current_user["id"]).eq("completed", True).execute()
        projects_created = supabase.table("projects").select("id").eq("creator_id", current_user["id"]).execute()
        proposals_created = supabase.table("proposals").select("id").eq("proposer_id", current_user["id"]).execute()
        votes_cast = supabase.table("votes").select("id").eq("user_id", current_user["id"]).execute()

        education_score = len(courses_taught.data or []) * 50 + len(courses_completed.data or []) * 10
        collaboration_score = len(projects_created.data or []) * 30
        governance_score = len(proposals_created.data or []) * 40 + len(votes_cast.data or []) * 5

        total_score = 0
        breakdown = {}

        for rep in reputation_result.data if reputation_result.data else []:
            category = rep.get("category", "general")
            points = rep.get("points", 0)
            breakdown[category] = breakdown.get(category, 0) + points
            total_score += points

        breakdown["education"] = breakdown.get("education", 0) + education_score
        breakdown["collaboration"] = breakdown.get("collaboration", 0) + collaboration_score
        breakdown["governance"] = breakdown.get("governance", 0) + governance_score
        total_score += education_score + collaboration_score + governance_score

        tier = self._calculate_tier(total_score)

        return {
            "user_id": current_user["id"],
            "total_score": total_score,
            "breakdown": breakdown,
            "tier": tier,
            "metrics": {
                "courses_taught": len(courses_taught.data or []),
                "courses_completed": len(courses_completed.data or []),
                "projects_created": len(projects_created.data or []),
                "proposals_created": len(proposals_created.data or []),
                "votes_cast": len(votes_cast.data or [])
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

def _calculate_tier(score: int) -> str:
    if score >= 10000:
        return "legendary"
    elif score >= 5000:
        return "expert"
    elif score >= 2500:
        return "advanced"
    elif score >= 1000:
        return "intermediate"
    elif score >= 500:
        return "beginner"
    else:
        return "newcomer"

@router.post("/award")
async def award_reputation(
    update: ReputationUpdate,
    current_user: dict = Depends(get_current_user)
):
    try:
        if update.target_user_id == current_user["id"]:
            raise HTTPException(status_code=400, detail="Cannot award reputation to yourself")

        data = {
            "user_id": update.target_user_id,
            "awarded_by": current_user["id"],
            "category": update.category,
            "points": update.points,
            "reason": update.reason
        }

        result = supabase.table("reputation_scores").insert(data).execute()

        return {
            "message": "Reputation awarded successfully",
            "reputation": result.data[0]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/leaderboard")
async def get_reputation_leaderboard(category: Optional[str] = None):
    try:
        if category:
            reputation_result = supabase.table("reputation_scores").select("user_id, points").eq("category", category).execute()
        else:
            reputation_result = supabase.table("reputation_scores").select("user_id, points").execute()

        user_scores = {}
        for rep in reputation_result.data if reputation_result.data else []:
            user_id = rep["user_id"]
            points = rep.get("points", 0)
            user_scores[user_id] = user_scores.get(user_id, 0) + points

        leaderboard = []
        for user_id, score in sorted(user_scores.items(), key=lambda x: x[1], reverse=True)[:100]:
            user_result = supabase.table("users").select("username, avatar").eq("id", user_id).execute()
            if user_result.data:
                leaderboard.append({
                    "user_id": user_id,
                    "username": user_result.data[0].get("username"),
                    "avatar": user_result.data[0].get("avatar"),
                    "reputation_score": score,
                    "tier": _calculate_tier(score)
                })

        return {"leaderboard": leaderboard}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/history/{user_id}")
async def get_reputation_history(user_id: str, current_user: dict = Depends(get_current_user)):
    try:
        history_result = supabase.table("reputation_scores").select("*, users!awarded_by(username)").eq("user_id", user_id).order("created_at", desc=True).execute()

        return {"history": history_result.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/badges-from-reputation")
async def get_reputation_badges(current_user: dict = Depends(get_current_user)):
    try:
        rep_data = await get_my_reputation(current_user)
        total_score = rep_data["total_score"]

        badges = []

        if total_score >= 500:
            badges.append({"name": "Rising Star", "tier": "bronze"})
        if total_score >= 1000:
            badges.append({"name": "Trusted Member", "tier": "silver"})
        if total_score >= 2500:
            badges.append({"name": "Community Leader", "tier": "gold"})
        if total_score >= 5000:
            badges.append({"name": "Expert", "tier": "platinum"})
        if total_score >= 10000:
            badges.append({"name": "Legend", "tier": "diamond"})

        breakdown = rep_data.get("breakdown", {})

        if breakdown.get("education", 0) >= 500:
            badges.append({"name": "Educator", "tier": "special"})
        if breakdown.get("collaboration", 0) >= 500:
            badges.append({"name": "Team Player", "tier": "special"})
        if breakdown.get("governance", 0) >= 500:
            badges.append({"name": "Governance Pro", "tier": "special"})

        return {"badges": badges, "total_score": total_score}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/trending-users")
async def get_trending_users(days: int = 7):
    try:
        start_date = datetime.utcnow() - timedelta(days=days)

        reputation_result = supabase.table("reputation_scores").select("user_id, points").gte("created_at", start_date.isoformat()).execute()

        user_scores = {}
        for rep in reputation_result.data if reputation_result.data else []:
            user_id = rep["user_id"]
            points = rep.get("points", 0)
            user_scores[user_id] = user_scores.get(user_id, 0) + points

        trending = []
        for user_id, score in sorted(user_scores.items(), key=lambda x: x[1], reverse=True)[:20]:
            user_result = supabase.table("users").select("username, avatar").eq("id", user_id).execute()
            if user_result.data:
                trending.append({
                    "user_id": user_id,
                    "username": user_result.data[0].get("username"),
                    "avatar": user_result.data[0].get("avatar"),
                    "recent_reputation": score
                })

        return {"trending_users": trending, "period_days": days}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/categories")
async def get_reputation_categories():
    try:
        categories = {
            "education": {
                "name": "Education",
                "description": "Teaching and learning contributions",
                "max_per_action": 50
            },
            "collaboration": {
                "name": "Collaboration",
                "description": "Project participation and teamwork",
                "max_per_action": 30
            },
            "governance": {
                "name": "Governance",
                "description": "DAO participation and voting",
                "max_per_action": 40
            },
            "support": {
                "name": "Support",
                "description": "Helping other community members",
                "max_per_action": 25
            },
            "innovation": {
                "name": "Innovation",
                "description": "New ideas and contributions",
                "max_per_action": 60
            },
            "quality": {
                "name": "Quality",
                "description": "High-quality content and work",
                "max_per_action": 45
            }
        }

        return {"categories": categories}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
