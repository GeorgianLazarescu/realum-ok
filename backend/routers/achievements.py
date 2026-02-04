from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime
from core.auth import get_current_user
from core.database import supabase
from services.token_service import TokenService

router = APIRouter(prefix="/api/achievements", tags=["Achievements"])
token_service = TokenService()

class AchievementProgress(BaseModel):
    achievement_id: str
    progress: int

@router.get("/catalog")
async def get_achievement_catalog():
    try:
        achievements = {
            "education": [
                {"id": "first_course", "name": "First Course", "description": "Complete your first course", "requirement": 1, "reward": 50, "type": "course_completion"},
                {"id": "course_completionist", "name": "Course Completionist", "description": "Complete 5 courses", "requirement": 5, "reward": 250, "type": "course_completion"},
                {"id": "knowledge_seeker", "name": "Knowledge Seeker", "description": "Complete 10 courses", "requirement": 10, "reward": 500, "type": "course_completion"},
                {"id": "master_learner", "name": "Master Learner", "description": "Complete 25 courses", "requirement": 25, "reward": 1500, "type": "course_completion"},
            ],
            "creation": [
                {"id": "content_creator", "name": "Content Creator", "description": "Create your first course", "requirement": 1, "reward": 100, "type": "course_creation"},
                {"id": "educator", "name": "Educator", "description": "Create 5 courses", "requirement": 5, "reward": 500, "type": "course_creation"},
                {"id": "master_teacher", "name": "Master Teacher", "description": "Create 10 courses", "requirement": 10, "reward": 1000, "type": "course_creation"},
            ],
            "collaboration": [
                {"id": "team_player", "name": "Team Player", "description": "Join your first project", "requirement": 1, "reward": 75, "type": "project_join"},
                {"id": "collaborator", "name": "Collaborator", "description": "Join 5 projects", "requirement": 5, "reward": 375, "type": "project_join"},
                {"id": "project_leader", "name": "Project Leader", "description": "Create 3 projects", "requirement": 3, "reward": 300, "type": "project_creation"},
            ],
            "governance": [
                {"id": "voter", "name": "Voter", "description": "Cast your first vote", "requirement": 1, "reward": 25, "type": "voting"},
                {"id": "active_citizen", "name": "Active Citizen", "description": "Cast 10 votes", "requirement": 10, "reward": 200, "type": "voting"},
                {"id": "governance_expert", "name": "Governance Expert", "description": "Cast 50 votes", "requirement": 50, "reward": 1000, "type": "voting"},
                {"id": "proposer", "name": "Proposer", "description": "Create your first proposal", "requirement": 1, "reward": 100, "type": "proposal_creation"},
            ],
            "economy": [
                {"id": "token_holder", "name": "Token Holder", "description": "Hold 1,000 RLM", "requirement": 1000, "reward": 100, "type": "token_balance"},
                {"id": "investor", "name": "Investor", "description": "Hold 10,000 RLM", "requirement": 10000, "reward": 1000, "type": "token_balance"},
                {"id": "whale", "name": "Whale", "description": "Hold 100,000 RLM", "requirement": 100000, "reward": 10000, "type": "token_balance"},
            ],
            "social": [
                {"id": "networker", "name": "Networker", "description": "Have 10 followers", "requirement": 10, "reward": 50, "type": "followers"},
                {"id": "influencer", "name": "Influencer", "description": "Have 100 followers", "requirement": 100, "reward": 500, "type": "followers"},
                {"id": "community_leader", "name": "Community Leader", "description": "Have 1000 followers", "requirement": 1000, "reward": 5000, "type": "followers"},
            ],
            "milestones": [
                {"id": "daily_streak_7", "name": "Week Warrior", "description": "Login for 7 consecutive days", "requirement": 7, "reward": 100, "type": "daily_streak"},
                {"id": "daily_streak_30", "name": "Monthly Master", "description": "Login for 30 consecutive days", "requirement": 30, "reward": 500, "type": "daily_streak"},
                {"id": "daily_streak_100", "name": "Centennial Champion", "description": "Login for 100 consecutive days", "requirement": 100, "reward": 2000, "type": "daily_streak"},
            ]
        }

        return {"catalog": achievements}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/my-achievements")
async def get_my_achievements(current_user: dict = Depends(get_current_user)):
    try:
        result = supabase.table("user_achievements").select("*").eq("user_id", current_user["id"]).execute()

        return {"achievements": result.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/progress")
async def get_achievement_progress(current_user: dict = Depends(get_current_user)):
    try:
        user_result = supabase.table("users").select("*").eq("id", current_user["id"]).execute()
        user = user_result.data[0] if user_result.data else {}

        courses_completed = supabase.table("user_courses").select("id").eq("user_id", current_user["id"]).eq("completed", True).execute()
        courses_created = supabase.table("courses").select("id").eq("creator_id", current_user["id"]).execute()
        projects_joined = supabase.table("project_members").select("id").eq("user_id", current_user["id"]).execute()
        projects_created = supabase.table("projects").select("id").eq("creator_id", current_user["id"]).execute()
        votes_cast = supabase.table("votes").select("id").eq("user_id", current_user["id"]).execute()
        proposals_created = supabase.table("proposals").select("id").eq("proposer_id", current_user["id"]).execute()
        followers = supabase.table("follows").select("id").eq("following_id", current_user["id"]).execute()
        daily_rewards = supabase.table("daily_rewards").select("streak").eq("user_id", current_user["id"]).order("created_at", desc=True).limit(1).execute()

        token_balance = float(user.get("realum_balance", 0))
        max_streak = daily_rewards.data[0].get("streak", 0) if daily_rewards.data else 0

        progress = {
            "course_completion": len(courses_completed.data or []),
            "course_creation": len(courses_created.data or []),
            "project_join": len(projects_joined.data or []),
            "project_creation": len(projects_created.data or []),
            "voting": len(votes_cast.data or []),
            "proposal_creation": len(proposals_created.data or []),
            "token_balance": token_balance,
            "followers": len(followers.data or []),
            "daily_streak": max_streak
        }

        return {"progress": progress}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/check-and-award")
async def check_and_award_achievements(current_user: dict = Depends(get_current_user)):
    try:
        progress_data = await get_achievement_progress(current_user)
        progress = progress_data["progress"]

        catalog_data = await get_achievement_catalog()
        all_achievements = catalog_data["catalog"]

        existing_achievements = supabase.table("user_achievements").select("achievement_name").eq("user_id", current_user["id"]).execute()
        earned_names = [a["achievement_name"] for a in existing_achievements.data] if existing_achievements.data else []

        newly_earned = []

        for category, achievements in all_achievements.items():
            for achievement in achievements:
                if achievement["name"] in earned_names:
                    continue

                achievement_type = achievement["type"]
                requirement = achievement["requirement"]
                current_progress = progress.get(achievement_type, 0)

                if current_progress >= requirement:
                    achievement_data = {
                        "user_id": current_user["id"],
                        "achievement_type": category,
                        "achievement_name": achievement["name"],
                        "metadata": {
                            "description": achievement["description"],
                            "requirement": requirement,
                            "reward": achievement["reward"]
                        }
                    }

                    result = supabase.table("user_achievements").insert(achievement_data).execute()

                    user_result = supabase.table("users").select("realum_balance").eq("id", current_user["id"]).execute()
                    current_balance = float(user_result.data[0].get("realum_balance", 0))
                    new_balance = current_balance + achievement["reward"]

                    supabase.table("users").update({"realum_balance": new_balance}).eq("id", current_user["id"]).execute()

                    token_service.create_transaction(
                        user_id=current_user["id"],
                        amount=achievement["reward"],
                        transaction_type="achievement_reward",
                        description=f"Achievement unlocked: {achievement['name']}"
                    )

                    newly_earned.append({
                        "achievement": achievement,
                        "reward": achievement["reward"]
                    })

        return {
            "message": f"Awarded {len(newly_earned)} new achievements",
            "newly_earned": newly_earned
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/leaderboard/{category}")
async def get_achievement_leaderboard(category: str):
    try:
        achievements_result = supabase.table("user_achievements").select("user_id, achievement_type").eq("achievement_type", category).execute()

        user_counts = {}
        for achievement in achievements_result.data if achievements_result.data else []:
            user_id = achievement["user_id"]
            user_counts[user_id] = user_counts.get(user_id, 0) + 1

        leaderboard = []
        for user_id, count in sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:100]:
            user_result = supabase.table("users").select("username, avatar").eq("id", user_id).execute()
            if user_result.data:
                leaderboard.append({
                    "user_id": user_id,
                    "username": user_result.data[0].get("username"),
                    "avatar": user_result.data[0].get("avatar"),
                    "achievement_count": count
                })

        return {"leaderboard": leaderboard, "category": category}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/tree")
async def get_achievement_tree():
    try:
        tree = {
            "education_path": {
                "nodes": [
                    {"id": "first_course", "requires": [], "unlocks": ["course_completionist"]},
                    {"id": "course_completionist", "requires": ["first_course"], "unlocks": ["knowledge_seeker"]},
                    {"id": "knowledge_seeker", "requires": ["course_completionist"], "unlocks": ["master_learner"]},
                    {"id": "master_learner", "requires": ["knowledge_seeker"], "unlocks": []}
                ]
            },
            "creation_path": {
                "nodes": [
                    {"id": "content_creator", "requires": [], "unlocks": ["educator"]},
                    {"id": "educator", "requires": ["content_creator"], "unlocks": ["master_teacher"]},
                    {"id": "master_teacher", "requires": ["educator"], "unlocks": []}
                ]
            },
            "governance_path": {
                "nodes": [
                    {"id": "voter", "requires": [], "unlocks": ["active_citizen"]},
                    {"id": "active_citizen", "requires": ["voter"], "unlocks": ["governance_expert"]},
                    {"id": "governance_expert", "requires": ["active_citizen"], "unlocks": []}
                ]
            }
        }

        return {"achievement_tree": tree}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/stats")
async def get_achievement_stats():
    try:
        all_achievements = supabase.table("user_achievements").select("*").execute()

        total_achievements = len(all_achievements.data) if all_achievements.data else 0

        type_breakdown = {}
        for achievement in all_achievements.data if all_achievements.data else []:
            atype = achievement.get("achievement_type", "unknown")
            type_breakdown[atype] = type_breakdown.get(atype, 0) + 1

        most_earned = {}
        for achievement in all_achievements.data if all_achievements.data else []:
            name = achievement.get("achievement_name", "unknown")
            most_earned[name] = most_earned.get(name, 0) + 1

        top_achievements = sorted(most_earned.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "stats": {
                "total_achievements_earned": total_achievements,
                "type_breakdown": type_breakdown,
                "most_earned_achievements": [{"name": k, "count": v} for k, v in top_achievements]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/next-achievements")
async def get_next_achievements(current_user: dict = Depends(get_current_user)):
    try:
        progress_data = await get_achievement_progress(current_user)
        progress = progress_data["progress"]

        catalog_data = await get_achievement_catalog()
        all_achievements = catalog_data["catalog"]

        existing_achievements = supabase.table("user_achievements").select("achievement_name").eq("user_id", current_user["id"]).execute()
        earned_names = [a["achievement_name"] for a in existing_achievements.data] if existing_achievements.data else []

        next_achievements = []

        for category, achievements in all_achievements.items():
            for achievement in achievements:
                if achievement["name"] not in earned_names:
                    achievement_type = achievement["type"]
                    requirement = achievement["requirement"]
                    current_progress = progress.get(achievement_type, 0)

                    completion_percentage = min(100, int((current_progress / requirement) * 100))

                    next_achievements.append({
                        "achievement": achievement,
                        "progress": current_progress,
                        "requirement": requirement,
                        "completion_percentage": completion_percentage
                    })

        next_achievements.sort(key=lambda x: x["completion_percentage"], reverse=True)

        return {"next_achievements": next_achievements[:10]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
