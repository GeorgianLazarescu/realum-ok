from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime, timezone, timedelta
import uuid

from core.database import db
from core.auth import get_current_user, require_admin
from services.token_service import TokenService
from services.notification_service import send_notification

router = APIRouter(prefix="/achievements", tags=["Achievements"])
token_service = TokenService()

class AchievementCreate(BaseModel):
    key: str
    name: str
    description: str
    category: str
    tier: str = "bronze"  # bronze, silver, gold, platinum, diamond
    xp_reward: int = 100
    token_reward: float = 0
    requirements: Dict = {}
    icon: Optional[str] = None
    is_hidden: bool = False

class QuestCreate(BaseModel):
    name: str
    description: str
    tasks: List[Dict]  # [{"type": "complete_course", "target": 1}, ...]
    xp_reward: int = 500
    token_reward: float = 50
    duration_days: int = 7
    is_repeatable: bool = False

# ===================== ACHIEVEMENT DEFINITIONS =====================

ACHIEVEMENTS = {
    # Learning achievements
    "first_course": {"name": "First Steps", "description": "Complete your first course", "tier": "bronze", "xp": 100, "category": "learning"},
    "course_master": {"name": "Course Master", "description": "Complete 10 courses", "tier": "gold", "xp": 500, "category": "learning"},
    "knowledge_seeker": {"name": "Knowledge Seeker", "description": "Complete 50 courses", "tier": "platinum", "xp": 2000, "category": "learning"},
    
    # Social achievements
    "socialite": {"name": "Socialite", "description": "Get 10 followers", "tier": "bronze", "xp": 100, "category": "social"},
    "influencer": {"name": "Influencer", "description": "Get 100 followers", "tier": "gold", "xp": 500, "category": "social"},
    "community_star": {"name": "Community Star", "description": "Get 1000 followers", "tier": "diamond", "xp": 5000, "category": "social"},
    
    # Governance achievements
    "first_vote": {"name": "Civic Duty", "description": "Cast your first vote", "tier": "bronze", "xp": 50, "category": "governance"},
    "proposal_creator": {"name": "Proposal Creator", "description": "Create your first proposal", "tier": "silver", "xp": 200, "category": "governance"},
    "governance_expert": {"name": "Governance Expert", "description": "Vote on 50 proposals", "tier": "gold", "xp": 500, "category": "governance"},
    
    # Economic achievements
    "token_holder": {"name": "Token Holder", "description": "Hold 1000 RLM", "tier": "bronze", "xp": 100, "category": "economic"},
    "whale": {"name": "Whale", "description": "Hold 100000 RLM", "tier": "platinum", "xp": 2000, "category": "economic"},
    "staking_beginner": {"name": "Staking Beginner", "description": "Stake tokens for first time", "tier": "bronze", "xp": 100, "category": "economic"},
    
    # Contribution achievements
    "bounty_hunter": {"name": "Bounty Hunter", "description": "Complete your first bounty", "tier": "bronze", "xp": 150, "category": "contribution"},
    "bounty_master": {"name": "Bounty Master", "description": "Complete 10 bounties", "tier": "gold", "xp": 750, "category": "contribution"},
    "project_creator": {"name": "Project Creator", "description": "Create a project", "tier": "silver", "xp": 200, "category": "contribution"},
    
    # Streak achievements
    "week_streak": {"name": "Week Warrior", "description": "7-day login streak", "tier": "bronze", "xp": 100, "category": "engagement"},
    "month_streak": {"name": "Month Master", "description": "30-day login streak", "tier": "silver", "xp": 500, "category": "engagement"},
    "century_streak": {"name": "Century Club", "description": "100-day login streak", "tier": "gold", "xp": 2000, "category": "engagement"},
    
    # Special achievements
    "early_adopter": {"name": "Early Adopter", "description": "Joined in the first month", "tier": "gold", "xp": 500, "category": "special", "hidden": True},
    "bug_hunter": {"name": "Bug Hunter", "description": "Report a verified bug", "tier": "silver", "xp": 300, "category": "special"},
}

# ===================== ACHIEVEMENTS =====================

@router.get("/")
async def get_all_achievements():
    """Get all achievement definitions"""
    try:
        # Get custom achievements from DB
        custom = await db.achievement_definitions.find(
            {"is_active": True},
            {"_id": 0}
        ).to_list(100)

        # Combine with predefined
        all_achievements = []
        for key, data in ACHIEVEMENTS.items():
            if not data.get("hidden", False):
                all_achievements.append({
                    "key": key,
                    "name": data["name"],
                    "description": data["description"],
                    "tier": data["tier"],
                    "xp_reward": data["xp"],
                    "category": data["category"]
                })

        all_achievements.extend(custom)

        # Group by category
        by_category = {}
        for ach in all_achievements:
            cat = ach.get("category", "general")
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(ach)

        return {
            "achievements": all_achievements,
            "by_category": by_category,
            "total": len(all_achievements)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/my")
async def get_my_achievements(current_user: dict = Depends(get_current_user)):
    """Get current user's achievements"""
    try:
        user_id = current_user["id"]

        # Get earned achievements
        earned = await db.user_achievements.find(
            {"user_id": user_id},
            {"_id": 0}
        ).to_list(100)

        earned_keys = [a["achievement_key"] for a in earned]

        # Get all achievements
        all_achievements = []
        for key, data in ACHIEVEMENTS.items():
            all_achievements.append({
                "key": key,
                "name": data["name"],
                "description": data["description"],
                "tier": data["tier"],
                "xp_reward": data["xp"],
                "category": data["category"],
                "earned": key in earned_keys,
                "earned_at": next((a["earned_at"] for a in earned if a["achievement_key"] == key), None)
            })

        # Stats
        total_earned = len(earned)
        total_xp = sum(ACHIEVEMENTS.get(a["achievement_key"], {}).get("xp", 0) for a in earned)

        return {
            "achievements": all_achievements,
            "earned_count": total_earned,
            "total_count": len(ACHIEVEMENTS),
            "total_xp_from_achievements": total_xp,
            "completion_percentage": round(total_earned / len(ACHIEVEMENTS) * 100, 1)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/check")
async def check_achievements(current_user: dict = Depends(get_current_user)):
    """Check and award any earned achievements"""
    try:
        user_id = current_user["id"]
        user = await db.users.find_one({"id": user_id})
        newly_earned = []

        # Get already earned
        earned = await db.user_achievements.find(
            {"user_id": user_id},
            {"achievement_key": 1}
        ).to_list(100)
        earned_keys = [a["achievement_key"] for a in earned]

        now = datetime.now(timezone.utc).isoformat()

        # Check each achievement
        checks = {
            # Course achievements
            "first_course": await db.user_courses.count_documents({"user_id": user_id, "completed": True}) >= 1,
            "course_master": await db.user_courses.count_documents({"user_id": user_id, "completed": True}) >= 10,
            "knowledge_seeker": await db.user_courses.count_documents({"user_id": user_id, "completed": True}) >= 50,
            
            # Social achievements
            "socialite": user.get("followers_count", 0) >= 10,
            "influencer": user.get("followers_count", 0) >= 100,
            "community_star": user.get("followers_count", 0) >= 1000,
            
            # Governance achievements
            "first_vote": await db.votes.count_documents({"user_id": user_id}) >= 1,
            "proposal_creator": await db.proposals.count_documents({"proposer_id": user_id}) >= 1,
            "governance_expert": await db.votes.count_documents({"user_id": user_id}) >= 50,
            
            # Economic achievements
            "token_holder": user.get("realum_balance", 0) >= 1000,
            "whale": user.get("realum_balance", 0) >= 100000,
            "staking_beginner": await db.stakes.count_documents({"user_id": user_id}) >= 1,
            
            # Contribution achievements
            "bounty_hunter": await db.bounties.count_documents({"claimed_by": user_id, "status": "completed"}) >= 1,
            "bounty_master": await db.bounties.count_documents({"claimed_by": user_id, "status": "completed"}) >= 10,
            "project_creator": await db.projects.count_documents({"creator_id": user_id}) >= 1,
        }

        # Check streak achievements
        daily_reward = await db.daily_rewards.find_one({"user_id": user_id})
        if daily_reward:
            streak = daily_reward.get("streak", 0)
            checks["week_streak"] = streak >= 7
            checks["month_streak"] = streak >= 30
            checks["century_streak"] = streak >= 100

        # Award new achievements
        for key, earned_check in checks.items():
            if earned_check and key not in earned_keys:
                ach_data = ACHIEVEMENTS.get(key, {})

                await db.user_achievements.insert_one({
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "achievement_key": key,
                    "earned_at": now
                })

                # Award XP
                xp_reward = ach_data.get("xp", 0)
                if xp_reward > 0:
                    await db.users.update_one(
                        {"id": user_id},
                        {"$inc": {"xp": xp_reward}}
                    )

                newly_earned.append({
                    "key": key,
                    "name": ach_data.get("name"),
                    "xp_reward": xp_reward
                })

                # Notify user
                await send_notification(
                    user_id=user_id,
                    title="Achievement Unlocked!",
                    message=f"You earned '{ach_data.get('name')}'! +{xp_reward} XP",
                    notification_type="achievement",
                    category="rewards"
                )

        return {
            "newly_earned": newly_earned,
            "count": len(newly_earned)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/progress")
async def get_achievement_progress(current_user: dict = Depends(get_current_user)):
    """Get progress towards unearned achievements"""
    try:
        user_id = current_user["id"]
        user = await db.users.find_one({"id": user_id})

        # Get already earned
        earned = await db.user_achievements.find(
            {"user_id": user_id},
            {"achievement_key": 1}
        ).to_list(100)
        earned_keys = [a["achievement_key"] for a in earned]

        # Calculate progress for each achievement
        progress = []

        # Course progress
        courses_completed = await db.user_courses.count_documents({"user_id": user_id, "completed": True})
        if "first_course" not in earned_keys:
            progress.append({"key": "first_course", "name": "First Steps", "current": courses_completed, "target": 1, "percentage": min(100, courses_completed * 100)})
        if "course_master" not in earned_keys:
            progress.append({"key": "course_master", "name": "Course Master", "current": courses_completed, "target": 10, "percentage": min(100, courses_completed * 10)})

        # Social progress
        followers = user.get("followers_count", 0)
        if "socialite" not in earned_keys:
            progress.append({"key": "socialite", "name": "Socialite", "current": followers, "target": 10, "percentage": min(100, followers * 10)})
        if "influencer" not in earned_keys:
            progress.append({"key": "influencer", "name": "Influencer", "current": followers, "target": 100, "percentage": min(100, followers)})

        # Governance progress
        votes = await db.votes.count_documents({"user_id": user_id})
        if "first_vote" not in earned_keys:
            progress.append({"key": "first_vote", "name": "Civic Duty", "current": votes, "target": 1, "percentage": min(100, votes * 100)})
        if "governance_expert" not in earned_keys:
            progress.append({"key": "governance_expert", "name": "Governance Expert", "current": votes, "target": 50, "percentage": min(100, votes * 2)})

        # Bounty progress
        bounties = await db.bounties.count_documents({"claimed_by": user_id, "status": "completed"})
        if "bounty_hunter" not in earned_keys:
            progress.append({"key": "bounty_hunter", "name": "Bounty Hunter", "current": bounties, "target": 1, "percentage": min(100, bounties * 100)})
        if "bounty_master" not in earned_keys:
            progress.append({"key": "bounty_master", "name": "Bounty Master", "current": bounties, "target": 10, "percentage": min(100, bounties * 10)})

        # Sort by percentage (closest to completion first)
        progress.sort(key=lambda x: x["percentage"], reverse=True)

        return {"progress": progress[:10]}  # Return top 10 closest
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ===================== QUESTS =====================

@router.get("/quests")
async def get_active_quests(current_user: dict = Depends(get_current_user)):
    """Get active quests"""
    try:
        now = datetime.now(timezone.utc).isoformat()

        # Get global quests
        quests = await db.quests.find(
            {"is_active": True, "ends_at": {"$gt": now}},
            {"_id": 0}
        ).to_list(20)

        # Get user's quest progress
        user_quests = await db.user_quests.find(
            {"user_id": current_user["id"]},
            {"_id": 0}
        ).to_list(20)

        quest_progress = {q["quest_id"]: q for q in user_quests}

        for quest in quests:
            progress = quest_progress.get(quest["id"], {})
            quest["user_progress"] = progress.get("progress", {})
            quest["completed"] = progress.get("completed", False)

        return {"quests": quests}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/quests/{quest_id}/claim")
async def claim_quest_reward(
    quest_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Claim completed quest reward"""
    try:
        user_id = current_user["id"]

        # Check quest completion
        user_quest = await db.user_quests.find_one({
            "user_id": user_id,
            "quest_id": quest_id,
            "completed": True,
            "claimed": False
        })

        if not user_quest:
            raise HTTPException(status_code=400, detail="Quest not completed or already claimed")

        quest = await db.quests.find_one({"id": quest_id})
        if not quest:
            raise HTTPException(status_code=404, detail="Quest not found")

        # Award rewards
        xp_reward = quest.get("xp_reward", 0)
        token_reward = quest.get("token_reward", 0)

        await db.users.update_one(
            {"id": user_id},
            {"$inc": {"xp": xp_reward, "realum_balance": token_reward}}
        )

        await db.user_quests.update_one(
            {"user_id": user_id, "quest_id": quest_id},
            {"$set": {"claimed": True, "claimed_at": datetime.now(timezone.utc).isoformat()}}
        )

        if token_reward > 0:
            await token_service.create_transaction(
                user_id=user_id,
                tx_type="credit",
                amount=token_reward,
                description=f"Quest reward: {quest['name']}"
            )

        return {
            "message": "Quest reward claimed",
            "xp_reward": xp_reward,
            "token_reward": token_reward
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ===================== LEADERBOARD =====================

@router.get("/leaderboard")
async def get_achievement_leaderboard(limit: int = 20):
    """Get achievement leaderboard"""
    try:
        pipeline = [
            {"$group": {
                "_id": "$user_id",
                "achievement_count": {"$sum": 1}
            }},
            {"$sort": {"achievement_count": -1}},
            {"$limit": limit}
        ]

        results = await db.user_achievements.aggregate(pipeline).to_list(limit)

        leaderboard = []
        for idx, item in enumerate(results):
            user = await db.users.find_one(
                {"id": item["_id"]},
                {"_id": 0, "username": 1, "avatar_url": 1, "level": 1}
            )
            if user:
                leaderboard.append({
                    "rank": idx + 1,
                    "user_id": item["_id"],
                    "username": user.get("username"),
                    "avatar_url": user.get("avatar_url"),
                    "level": user.get("level", 1),
                    "achievements": item["achievement_count"]
                })

        return {"leaderboard": leaderboard}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/tiers")
async def get_achievement_tiers():
    """Get achievement tier definitions"""
    return {
        "tiers": [
            {"key": "bronze", "name": "Bronze", "color": "#CD7F32", "min_xp": 50},
            {"key": "silver", "name": "Silver", "color": "#C0C0C0", "min_xp": 100},
            {"key": "gold", "name": "Gold", "color": "#FFD700", "min_xp": 250},
            {"key": "platinum", "name": "Platinum", "color": "#E5E4E2", "min_xp": 500},
            {"key": "diamond", "name": "Diamond", "color": "#B9F2FF", "min_xp": 1000}
        ],
        "categories": [
            "learning", "social", "governance", "economic", "contribution", "engagement", "special"
        ]
    }
