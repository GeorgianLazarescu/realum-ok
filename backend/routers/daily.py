from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone, timedelta
import uuid

from core.database import db
from core.auth import get_current_user
from services.token_service import create_transaction, add_xp, award_badge

router = APIRouter(prefix="/daily", tags=["Daily Rewards"])

# Daily reward configuration
BASE_RLM_REWARD = 10
BASE_XP_REWARD = 25
STREAK_BONUS_MULTIPLIER = 0.1  # 10% bonus per streak day
MAX_STREAK_BONUS = 2.0  # Max 200% bonus (at 20 day streak)

STREAK_MILESTONES = {
    7: {"badge": "week_warrior", "bonus_rlm": 50, "bonus_xp": 100},
    30: {"badge": "monthly_master", "bonus_rlm": 200, "bonus_xp": 500},
    100: {"badge": "century_champion", "bonus_rlm": 1000, "bonus_xp": 2500}
}

@router.get("/status")
async def get_daily_status(current_user: dict = Depends(get_current_user)):
    """Get daily reward status for current user"""
    user_id = current_user["id"]
    
    # Get daily reward record
    daily_record = await db.daily_rewards.find_one({"user_id": user_id}, {"_id": 0})
    
    now = datetime.now(timezone.utc)
    today = now.date().isoformat()
    
    if not daily_record:
        return {
            "can_claim": True,
            "streak": 0,
            "last_claim": None,
            "next_reward": {
                "rlm": BASE_RLM_REWARD,
                "xp": BASE_XP_REWARD
            },
            "streak_bonus": 0
        }
    
    last_claim_date = daily_record.get("last_claim_date", "")
    streak = daily_record.get("streak", 0)
    
    # Check if already claimed today
    can_claim = last_claim_date != today
    
    # Calculate streak bonus
    streak_bonus = min(streak * STREAK_BONUS_MULTIPLIER, MAX_STREAK_BONUS)
    
    # Calculate next reward
    next_rlm = int(BASE_RLM_REWARD * (1 + streak_bonus))
    next_xp = int(BASE_XP_REWARD * (1 + streak_bonus))
    
    # Check for upcoming milestone
    next_milestone = None
    for days, rewards in sorted(STREAK_MILESTONES.items()):
        if streak < days:
            next_milestone = {"days": days, "rewards": rewards}
            break
    
    return {
        "can_claim": can_claim,
        "streak": streak,
        "last_claim": daily_record.get("last_claim"),
        "next_reward": {
            "rlm": next_rlm,
            "xp": next_xp
        },
        "streak_bonus": int(streak_bonus * 100),
        "next_milestone": next_milestone,
        "total_claimed": daily_record.get("total_claimed", 0)
    }

@router.post("/claim")
async def claim_daily_reward(current_user: dict = Depends(get_current_user)):
    """Claim daily reward"""
    user_id = current_user["id"]
    
    now = datetime.now(timezone.utc)
    today = now.date().isoformat()
    yesterday = (now.date() - timedelta(days=1)).isoformat()
    
    # Get or create daily record
    daily_record = await db.daily_rewards.find_one({"user_id": user_id})
    
    if daily_record and daily_record.get("last_claim_date") == today:
        raise HTTPException(status_code=400, detail="Already claimed today")
    
    # Calculate streak
    old_streak = 0
    if daily_record:
        old_streak = daily_record.get("streak", 0)
        last_claim_date = daily_record.get("last_claim_date", "")
        
        # Continue streak if claimed yesterday, otherwise reset
        if last_claim_date == yesterday:
            new_streak = old_streak + 1
        else:
            new_streak = 1
    else:
        new_streak = 1
    
    # Calculate rewards
    streak_bonus = min(old_streak * STREAK_BONUS_MULTIPLIER, MAX_STREAK_BONUS)
    rlm_reward = int(BASE_RLM_REWARD * (1 + streak_bonus))
    xp_reward = int(BASE_XP_REWARD * (1 + streak_bonus))
    
    result = {
        "rlm_earned": rlm_reward,
        "xp_earned": xp_reward,
        "new_streak": new_streak,
        "streak_bonus": int(streak_bonus * 100),
        "milestones_reached": []
    }
    
    # Check for milestone rewards
    if new_streak in STREAK_MILESTONES:
        milestone = STREAK_MILESTONES[new_streak]
        rlm_reward += milestone["bonus_rlm"]
        xp_reward += milestone["bonus_xp"]
        
        # Award milestone badge
        await award_badge(user_id, milestone["badge"])
        
        result["milestones_reached"].append({
            "days": new_streak,
            "bonus_rlm": milestone["bonus_rlm"],
            "bonus_xp": milestone["bonus_xp"],
            "badge": milestone["badge"]
        })
    
    # Update user balance and XP
    await db.users.update_one(
        {"id": user_id},
        {"$inc": {"realum_balance": rlm_reward}}
    )
    await add_xp(user_id, xp_reward)
    
    # Create transaction
    await create_transaction(
        user_id, "credit", rlm_reward,
        f"Daily reward (Day {new_streak} streak)"
    )
    
    # Update daily record
    total_claimed = (daily_record.get("total_claimed", 0) if daily_record else 0) + 1
    
    await db.daily_rewards.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "user_id": user_id,
                "streak": new_streak,
                "last_claim": now.isoformat(),
                "last_claim_date": today,
                "total_claimed": total_claimed
            }
        },
        upsert=True
    )
    
    # Award first daily badge
    if total_claimed == 1:
        await award_badge(user_id, "daily_devotee")
        result["milestones_reached"].append({
            "badge": "daily_devotee",
            "message": "First daily reward claimed!"
        })
    
    result["new_balance"] = current_user["realum_balance"] + rlm_reward
    
    return result

@router.get("/leaderboard")
async def get_streak_leaderboard():
    """Get users with highest streaks"""
    records = await db.daily_rewards.find(
        {}, {"_id": 0}
    ).sort("streak", -1).limit(10).to_list(10)
    
    leaderboard = []
    for i, record in enumerate(records, 1):
        user = await db.users.find_one({"id": record["user_id"]}, {"_id": 0, "username": 1})
        if user:
            leaderboard.append({
                "rank": i,
                "username": user["username"],
                "streak": record["streak"],
                "total_claimed": record.get("total_claimed", 0)
            })
    
    return {"leaderboard": leaderboard}
