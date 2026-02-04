from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime
from core.auth import get_current_user
from core.database import supabase
from services.token_service import TokenService

router = APIRouter(prefix="/api/badges", tags=["Badges"])
token_service = TokenService()

class BadgeUpgradeRequest(BaseModel):
    achievement_id: str

@router.get("/catalog")
async def get_badge_catalog():
    try:
        badges = {
            "common": [
                {"id": "first_login", "name": "First Steps", "description": "Complete your first login", "level": 1, "rarity": "common", "evolution_path": ["regular_user", "active_member"]},
                {"id": "profile_complete", "name": "Profile Pro", "description": "Complete your profile", "level": 1, "rarity": "common", "evolution_path": ["verified_member"]},
            ],
            "rare": [
                {"id": "course_master", "name": "Course Master", "description": "Complete 5 courses", "level": 2, "rarity": "rare", "evolution_path": ["education_guru", "mentor"]},
                {"id": "project_creator", "name": "Project Creator", "description": "Launch 3 projects", "level": 2, "rarity": "rare", "evolution_path": ["innovation_leader"]},
            ],
            "epic": [
                {"id": "dao_voter", "name": "DAO Participant", "description": "Vote on 10 proposals", "level": 3, "rarity": "epic", "evolution_path": ["governance_expert"]},
                {"id": "token_holder", "name": "Token Whale", "description": "Hold 10,000 RLM", "level": 3, "rarity": "epic", "evolution_path": ["investor"]},
            ],
            "legendary": [
                {"id": "platform_founder", "name": "Platform Founder", "description": "Early adopter", "level": 4, "rarity": "legendary", "evolution_path": []},
                {"id": "community_leader", "name": "Community Leader", "description": "Help 100 users", "level": 4, "rarity": "legendary", "evolution_path": []},
            ]
        }

        return {"catalog": badges}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/my-badges")
async def get_my_badges(current_user: dict = Depends(get_current_user)):
    try:
        result = supabase.table("user_achievements").select("*").eq("user_id", current_user["id"]).execute()

        badges_with_evolution = []
        for achievement in result.data if result.data else []:
            metadata = achievement.get("metadata", {})
            badges_with_evolution.append({
                "id": achievement["id"],
                "achievement_type": achievement["achievement_type"],
                "achievement_name": achievement["achievement_name"],
                "earned_at": achievement["earned_at"],
                "level": metadata.get("level", 1),
                "rarity": metadata.get("rarity", "common"),
                "can_evolve": metadata.get("can_evolve", False),
                "evolution_progress": metadata.get("evolution_progress", 0),
                "next_evolution": metadata.get("next_evolution")
            })

        return {"badges": badges_with_evolution}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/evolve/{achievement_id}")
async def evolve_badge(achievement_id: str, current_user: dict = Depends(get_current_user)):
    try:
        achievement_result = supabase.table("user_achievements").select("*").eq("id", achievement_id).eq("user_id", current_user["id"]).execute()

        if not achievement_result.data:
            raise HTTPException(status_code=404, detail="Achievement not found")

        achievement = achievement_result.data[0]
        metadata = achievement.get("metadata", {})

        if not metadata.get("can_evolve", False):
            raise HTTPException(status_code=400, detail="Badge cannot evolve yet")

        current_level = metadata.get("level", 1)
        next_evolution = metadata.get("next_evolution")

        evolution_cost = current_level * 500

        user_result = supabase.table("users").select("realum_balance").eq("id", current_user["id"]).execute()
        current_balance = float(user_result.data[0].get("realum_balance", 0))

        if current_balance < evolution_cost:
            raise HTTPException(status_code=400, detail=f"Insufficient RLM tokens. Need {evolution_cost} RLM")

        new_balance = current_balance - evolution_cost
        supabase.table("users").update({"realum_balance": new_balance}).eq("id", current_user["id"]).execute()

        token_service.create_transaction(
            user_id=current_user["id"],
            amount=-evolution_cost,
            transaction_type="badge_evolution",
            description=f"Evolved badge to level {current_level + 1}"
        )

        new_metadata = {
            **metadata,
            "level": current_level + 1,
            "rarity": self._get_rarity_for_level(current_level + 1),
            "evolved_at": datetime.utcnow().isoformat(),
            "can_evolve": False,
            "evolution_progress": 0
        }

        supabase.table("user_achievements").update({"metadata": new_metadata}).eq("id", achievement_id).execute()

        return {
            "message": "Badge evolved successfully",
            "new_level": current_level + 1,
            "cost": evolution_cost,
            "new_balance": new_balance
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

def _get_rarity_for_level(level: int) -> str:
    if level >= 4:
        return "legendary"
    elif level >= 3:
        return "epic"
    elif level >= 2:
        return "rare"
    else:
        return "common"

@router.get("/evolution-paths")
async def get_evolution_paths():
    try:
        paths = {
            "first_login": {
                "level_1": "First Steps",
                "level_2": "Regular User",
                "level_3": "Active Member",
                "level_4": "Core Community"
            },
            "course_master": {
                "level_1": "Student",
                "level_2": "Course Master",
                "level_3": "Education Guru",
                "level_4": "Mentor Legend"
            },
            "project_creator": {
                "level_1": "Contributor",
                "level_2": "Project Creator",
                "level_3": "Innovation Leader",
                "level_4": "Visionary"
            },
            "dao_voter": {
                "level_1": "Observer",
                "level_2": "DAO Participant",
                "level_3": "Governance Expert",
                "level_4": "Council Member"
            }
        }

        return {"evolution_paths": paths}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/track-progress/{achievement_type}")
async def track_badge_progress(achievement_type: str, current_user: dict = Depends(get_current_user)):
    try:
        achievement_result = supabase.table("user_achievements").select("*").eq("user_id", current_user["id"]).eq("achievement_type", achievement_type).execute()

        if not achievement_result.data:
            return {"message": "Achievement not earned yet"}

        achievement = achievement_result.data[0]
        metadata = achievement.get("metadata", {})

        progress = metadata.get("evolution_progress", 0) + 1
        can_evolve = progress >= 100

        new_metadata = {
            **metadata,
            "evolution_progress": min(progress, 100),
            "can_evolve": can_evolve
        }

        supabase.table("user_achievements").update({"metadata": new_metadata}).eq("id", achievement["id"]).execute()

        return {
            "message": "Progress updated",
            "progress": min(progress, 100),
            "can_evolve": can_evolve
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/leaderboard")
async def get_badge_leaderboard():
    try:
        achievements_result = supabase.table("user_achievements").select("user_id, metadata").execute()

        user_scores = {}
        for achievement in achievements_result.data if achievements_result.data else []:
            user_id = achievement["user_id"]
            metadata = achievement.get("metadata", {})
            level = metadata.get("level", 1)
            rarity_multiplier = {"common": 1, "rare": 2, "epic": 5, "legendary": 10}.get(metadata.get("rarity", "common"), 1)

            score = level * rarity_multiplier
            user_scores[user_id] = user_scores.get(user_id, 0) + score

        leaderboard = []
        for user_id, score in sorted(user_scores.items(), key=lambda x: x[1], reverse=True)[:100]:
            user_result = supabase.table("users").select("username, avatar").eq("id", user_id).execute()
            if user_result.data:
                leaderboard.append({
                    "user_id": user_id,
                    "username": user_result.data[0].get("username"),
                    "avatar": user_result.data[0].get("avatar"),
                    "badge_score": score
                })

        return {"leaderboard": leaderboard}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
