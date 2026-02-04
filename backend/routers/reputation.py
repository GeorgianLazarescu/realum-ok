from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, List
from datetime import datetime, timezone, timedelta
import uuid
from core.auth import get_current_user
from core.database import db

router = APIRouter(prefix="/api/reputation", tags=["Reputation"])

class ReputationUpdate(BaseModel):
    target_user_id: str
    category: str
    points: int
    reason: str

class ReputationEndorsement(BaseModel):
    skill: str
    comment: Optional[str] = None

def calculate_tier(score: int) -> str:
    """Calculate reputation tier based on score"""
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

@router.get("/score/{user_id}")
async def get_reputation_score(user_id: str):
    """Get reputation score for a user"""
    try:
        # Get direct reputation scores
        scores = await db.reputation_scores.find(
            {"user_id": user_id},
            {"_id": 0}
        ).to_list(None)

        if not scores:
            return {
                "user_id": user_id,
                "total_score": 0,
                "breakdown": {},
                "tier": "newcomer"
            }

        total_score = 0
        breakdown = {}

        for rep in scores:
            category = rep.get("category", "general")
            points = rep.get("points", 0)
            breakdown[category] = breakdown.get(category, 0) + points
            total_score += points

        return {
            "user_id": user_id,
            "total_score": total_score,
            "breakdown": breakdown,
            "tier": calculate_tier(total_score)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/my-reputation")
async def get_my_reputation(current_user: dict = Depends(get_current_user)):
    """Get comprehensive reputation for current user"""
    try:
        user_id = current_user["id"]

        # Direct reputation scores
        scores = await db.reputation_scores.find(
            {"user_id": user_id},
            {"_id": 0}
        ).to_list(None)

        # Activity-based scores
        courses_taught = await db.courses.count_documents({"creator_id": user_id})
        courses_completed = await db.user_courses.count_documents({"user_id": user_id, "completed": True})
        projects_created = await db.projects.count_documents({"creator_id": user_id})
        proposals_created = await db.proposals.count_documents({"proposer_id": user_id})
        votes_cast = await db.votes.count_documents({"user_id": user_id})
        bounties_completed = await db.bounties.count_documents({"claimed_by": user_id, "status": "completed"})
        disputes_resolved = await db.disputes.count_documents({"initiator_id": user_id, "status": "resolved"})

        # Calculate activity scores
        education_score = courses_taught * 50 + courses_completed * 10
        collaboration_score = projects_created * 30 + bounties_completed * 40
        governance_score = proposals_created * 40 + votes_cast * 5
        dispute_score = disputes_resolved * 20

        # Aggregate breakdown
        breakdown = {
            "education": education_score,
            "collaboration": collaboration_score,
            "governance": governance_score,
            "dispute_resolution": dispute_score
        }

        # Add direct scores
        for rep in scores:
            category = rep.get("category", "general")
            points = rep.get("points", 0)
            breakdown[category] = breakdown.get(category, 0) + points

        total_score = sum(breakdown.values())
        tier = calculate_tier(total_score)

        # Get endorsements
        endorsements = await db.skill_endorsements.find(
            {"user_id": user_id},
            {"_id": 0}
        ).to_list(50)

        # Group endorsements by skill
        endorsement_counts = {}
        for e in endorsements:
            skill = e.get("skill", "general")
            endorsement_counts[skill] = endorsement_counts.get(skill, 0) + 1

        return {
            "user_id": user_id,
            "total_score": total_score,
            "breakdown": breakdown,
            "tier": tier,
            "metrics": {
                "courses_taught": courses_taught,
                "courses_completed": courses_completed,
                "projects_created": projects_created,
                "proposals_created": proposals_created,
                "votes_cast": votes_cast,
                "bounties_completed": bounties_completed,
                "disputes_resolved": disputes_resolved
            },
            "endorsements": endorsement_counts
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/award")
async def award_reputation(
    update: ReputationUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Award reputation points to another user"""
    try:
        if update.target_user_id == current_user["id"]:
            raise HTTPException(status_code=400, detail="Cannot award reputation to yourself")

        # Verify target user exists
        target = await db.users.find_one({"id": update.target_user_id})
        if not target:
            raise HTTPException(status_code=404, detail="Target user not found")

        # Limit points per award
        max_points = 50
        if update.points > max_points:
            update.points = max_points
        if update.points < 1:
            update.points = 1

        now = datetime.now(timezone.utc).isoformat()

        await db.reputation_scores.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": update.target_user_id,
            "awarded_by": current_user["id"],
            "category": update.category,
            "points": update.points,
            "reason": update.reason,
            "created_at": now
        })

        return {
            "message": "Reputation awarded successfully",
            "points": update.points
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/endorse/{user_id}")
async def endorse_skill(
    user_id: str,
    endorsement: ReputationEndorsement,
    current_user: dict = Depends(get_current_user)
):
    """Endorse a user's skill"""
    try:
        if user_id == current_user["id"]:
            raise HTTPException(status_code=400, detail="Cannot endorse yourself")

        # Check if already endorsed
        existing = await db.skill_endorsements.find_one({
            "user_id": user_id,
            "endorsed_by": current_user["id"],
            "skill": endorsement.skill
        })

        if existing:
            raise HTTPException(status_code=400, detail="Already endorsed this skill")

        now = datetime.now(timezone.utc).isoformat()

        await db.skill_endorsements.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "endorsed_by": current_user["id"],
            "skill": endorsement.skill,
            "comment": endorsement.comment,
            "created_at": now
        })

        return {"message": "Skill endorsed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/leaderboard")
async def get_reputation_leaderboard(
    category: Optional[str] = None,
    limit: int = 100
):
    """Get reputation leaderboard"""
    try:
        # Aggregate scores by user
        match_stage = {}
        if category:
            match_stage = {"$match": {"category": category}}

        pipeline = [
            match_stage,
            {"$group": {
                "_id": "$user_id",
                "total_score": {"$sum": "$points"}
            }},
            {"$sort": {"total_score": -1}},
            {"$limit": limit}
        ] if category else [
            {"$group": {
                "_id": "$user_id",
                "total_score": {"$sum": "$points"}
            }},
            {"$sort": {"total_score": -1}},
            {"$limit": limit}
        ]

        results = await db.reputation_scores.aggregate(pipeline).to_list(limit)

        leaderboard = []
        for idx, item in enumerate(results):
            user_id = item["_id"]
            score = item["total_score"]
            
            user = await db.users.find_one(
                {"id": user_id},
                {"_id": 0, "username": 1, "avatar_url": 1}
            )
            
            if user:
                leaderboard.append({
                    "rank": idx + 1,
                    "user_id": user_id,
                    "username": user.get("username"),
                    "avatar_url": user.get("avatar_url"),
                    "reputation_score": score,
                    "tier": calculate_tier(score)
                })

        return {"leaderboard": leaderboard, "category": category}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/history/{user_id}")
async def get_reputation_history(
    user_id: str,
    days: int = 30,
    current_user: dict = Depends(get_current_user)
):
    """Get reputation history for a user"""
    try:
        start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        history = await db.reputation_scores.find(
            {
                "user_id": user_id,
                "created_at": {"$gte": start_date}
            },
            {"_id": 0}
        ).sort("created_at", -1).to_list(100)

        # Enrich with awarder info
        for item in history:
            awarder = await db.users.find_one(
                {"id": item.get("awarded_by")},
                {"_id": 0, "username": 1}
            )
            if awarder:
                item["awarded_by_username"] = awarder.get("username")

        return {"history": history, "days": days}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/badges-from-reputation")
async def get_reputation_badges(current_user: dict = Depends(get_current_user)):
    """Get badges earned from reputation"""
    try:
        rep_data = await get_my_reputation(current_user)
        total_score = rep_data["total_score"]
        breakdown = rep_data.get("breakdown", {})

        badges = []

        # Score-based badges
        if total_score >= 500:
            badges.append({"name": "Rising Star", "tier": "bronze", "requirement": "500 reputation"})
        if total_score >= 1000:
            badges.append({"name": "Trusted Member", "tier": "silver", "requirement": "1000 reputation"})
        if total_score >= 2500:
            badges.append({"name": "Community Leader", "tier": "gold", "requirement": "2500 reputation"})
        if total_score >= 5000:
            badges.append({"name": "Expert", "tier": "platinum", "requirement": "5000 reputation"})
        if total_score >= 10000:
            badges.append({"name": "Legend", "tier": "diamond", "requirement": "10000 reputation"})

        # Category-based badges
        if breakdown.get("education", 0) >= 500:
            badges.append({"name": "Educator", "tier": "special", "requirement": "500 education reputation"})
        if breakdown.get("collaboration", 0) >= 500:
            badges.append({"name": "Team Player", "tier": "special", "requirement": "500 collaboration reputation"})
        if breakdown.get("governance", 0) >= 500:
            badges.append({"name": "Governance Pro", "tier": "special", "requirement": "500 governance reputation"})

        return {
            "badges": badges,
            "total_score": total_score,
            "tier": calculate_tier(total_score)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/trending-users")
async def get_trending_users(days: int = 7):
    """Get users with most reputation gained recently"""
    try:
        start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        pipeline = [
            {"$match": {"created_at": {"$gte": start_date}}},
            {"$group": {
                "_id": "$user_id",
                "recent_score": {"$sum": "$points"}
            }},
            {"$sort": {"recent_score": -1}},
            {"$limit": 20}
        ]

        results = await db.reputation_scores.aggregate(pipeline).to_list(20)

        trending = []
        for item in results:
            user = await db.users.find_one(
                {"id": item["_id"]},
                {"_id": 0, "username": 1, "avatar_url": 1}
            )
            if user:
                trending.append({
                    "user_id": item["_id"],
                    "username": user.get("username"),
                    "avatar_url": user.get("avatar_url"),
                    "recent_reputation": item["recent_score"]
                })

        return {"trending_users": trending, "period_days": days}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/categories")
async def get_reputation_categories():
    """Get reputation category definitions"""
    return {
        "categories": {
            "education": {
                "name": "Education",
                "description": "Teaching and learning contributions",
                "max_per_action": 50,
                "examples": ["Creating courses", "Completing courses", "Mentoring"]
            },
            "collaboration": {
                "name": "Collaboration",
                "description": "Project participation and teamwork",
                "max_per_action": 40,
                "examples": ["Project contributions", "Bounty completion", "Team work"]
            },
            "governance": {
                "name": "Governance",
                "description": "DAO participation and voting",
                "max_per_action": 40,
                "examples": ["Creating proposals", "Voting", "Committee participation"]
            },
            "support": {
                "name": "Support",
                "description": "Helping other community members",
                "max_per_action": 25,
                "examples": ["Answering questions", "Bug reports", "Onboarding help"]
            },
            "innovation": {
                "name": "Innovation",
                "description": "New ideas and contributions",
                "max_per_action": 60,
                "examples": ["Feature suggestions", "Research", "Creative solutions"]
            },
            "quality": {
                "name": "Quality",
                "description": "High-quality content and work",
                "max_per_action": 45,
                "examples": ["Excellent submissions", "Thorough reviews", "Best practices"]
            }
        },
        "tiers": [
            {"name": "newcomer", "min_score": 0, "color": "#9CA3AF"},
            {"name": "beginner", "min_score": 500, "color": "#10B981"},
            {"name": "intermediate", "min_score": 1000, "color": "#3B82F6"},
            {"name": "advanced", "min_score": 2500, "color": "#8B5CF6"},
            {"name": "expert", "min_score": 5000, "color": "#F59E0B"},
            {"name": "legendary", "min_score": 10000, "color": "#EF4444"}
        ]
    }
