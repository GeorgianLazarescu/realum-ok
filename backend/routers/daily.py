from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone, timedelta, date
from typing import Optional
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
    """Claim daily reward with advanced streak and seasonal bonuses"""
    user_id = current_user["id"]

    now = datetime.now(timezone.utc)
    today = now.date().isoformat()
    yesterday = (now.date() - timedelta(days=1)).isoformat()

    # Get or create daily record
    daily_record = await db.daily_rewards.find_one({"user_id": user_id})

    if daily_record and daily_record.get("last_claim_date") == today:
        raise HTTPException(status_code=400, detail="Already claimed today")

    # Get or create streak record
    streak_record = await db.daily_reward_streaks.find_one({"user_id": user_id})

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

    # Calculate streak multiplier based on streak length
    if new_streak >= 90:
        streak_multiplier = 3.0
    elif new_streak >= 30:
        streak_multiplier = 2.0
    elif new_streak >= 7:
        streak_multiplier = 1.5
    else:
        streak_multiplier = 1.0

    # Check for active seasonal events
    seasonal_event = await db.seasonal_rewards.find_one({
        "is_active": True,
        "start_date": {"$lte": now},
        "end_date": {"$gte": now}
    }, {"_id": 0})

    seasonal_multiplier = 1.0
    seasonal_bonus_tokens = 0
    seasonal_event_id = None

    if seasonal_event:
        seasonal_multiplier = seasonal_event.get("base_reward_multiplier", 1.0)
        seasonal_bonus_tokens = seasonal_event.get("bonus_tokens", 0)
        seasonal_event_id = seasonal_event.get("id")

    # Calculate rewards with all bonuses
    base_rlm = BASE_RLM_REWARD
    base_xp = BASE_XP_REWARD

    rlm_reward = int(base_rlm * streak_multiplier * seasonal_multiplier) + seasonal_bonus_tokens
    xp_reward = int(base_xp * streak_multiplier * seasonal_multiplier)

    result = {
        "rlm_earned": rlm_reward,
        "xp_earned": xp_reward,
        "new_streak": new_streak,
        "streak_multiplier": streak_multiplier,
        "seasonal_event": seasonal_event.get("event_name") if seasonal_event else None,
        "seasonal_bonus": seasonal_bonus_tokens,
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
        f"Daily reward (Day {new_streak} streak, {streak_multiplier}x multiplier)"
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
                "total_claimed": total_claimed,
                "streak_multiplier": streak_multiplier,
                "seasonal_event_id": seasonal_event_id
            }
        },
        upsert=True
    )

    # Update streak record
    longest_streak = max(new_streak, streak_record.get("longest_streak", 0) if streak_record else 0)

    await db.daily_reward_streaks.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "user_id": user_id,
                "current_streak": new_streak,
                "longest_streak": longest_streak,
                "last_claim_date": today,
                "streak_multiplier": streak_multiplier,
                "updated_at": now.isoformat()
            },
            "$inc": {"total_claims": 1}
        },
        upsert=True
    )

    # Add to reward calendar
    await db.reward_calendar.update_one(
        {"user_id": user_id, "claim_date": today},
        {
            "$set": {
                "user_id": user_id,
                "claim_date": today,
                "tokens_earned": rlm_reward,
                "streak_day": new_streak,
                "was_seasonal_bonus": seasonal_event is not None,
                "seasonal_event_id": seasonal_event_id,
                "notes": f"{streak_multiplier}x streak bonus" + (f", {seasonal_event.get('event_name')}" if seasonal_event else ""),
                "created_at": now.isoformat()
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

@router.get("/seasonal")
async def get_seasonal_rewards():
    """Get active seasonal reward events"""
    now = datetime.now(timezone.utc)

    events = await db.seasonal_rewards.find({
        "is_active": True,
        "start_date": {"$lte": now},
        "end_date": {"$gte": now}
    }, {"_id": 0}).to_list(10)

    return {"active_events": events}

@router.get("/calendar")
async def get_reward_calendar(
    month: Optional[int] = None,
    year: Optional[int] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get reward calendar for a specific month"""
    user_id = current_user["id"]
    now = datetime.now(timezone.utc)

    target_month = month or now.month
    target_year = year or now.year

    # Get all claims for the target month
    start_date = date(target_year, target_month, 1)
    if target_month == 12:
        end_date = date(target_year + 1, 1, 1)
    else:
        end_date = date(target_year, target_month + 1, 1)

    calendar_entries = await db.reward_calendar.find({
        "user_id": user_id,
        "claim_date": {
            "$gte": start_date.isoformat(),
            "$lt": end_date.isoformat()
        }
    }, {"_id": 0}).sort("claim_date", 1).to_list(31)

    # Get streak information
    streak_info = await db.daily_reward_streaks.find_one({"user_id": user_id}, {"_id": 0})

    return {
        "month": target_month,
        "year": target_year,
        "calendar": calendar_entries,
        "streak_info": streak_info or {
            "current_streak": 0,
            "longest_streak": 0,
            "total_claims": 0
        }
    }

@router.get("/stats")
async def get_reward_statistics(current_user: dict = Depends(get_current_user)):
    """Get detailed reward statistics for current user"""
    user_id = current_user["id"]

    # Get streak information
    streak_info = await db.daily_reward_streaks.find_one({"user_id": user_id}, {"_id": 0})

    # Get total tokens earned from daily rewards
    calendar_entries = await db.reward_calendar.find(
        {"user_id": user_id},
        {"_id": 0}
    ).to_list(1000)

    total_tokens = sum(entry.get("tokens_earned", 0) for entry in calendar_entries)
    total_seasonal_bonuses = sum(
        entry.get("tokens_earned", 0)
        for entry in calendar_entries
        if entry.get("was_seasonal_bonus", False)
    )

    # Calculate monthly activity
    monthly_activity = {}
    for entry in calendar_entries:
        claim_date = entry.get("claim_date", "")
        if claim_date:
            month_key = claim_date[:7]  # YYYY-MM format
            monthly_activity[month_key] = monthly_activity.get(month_key, 0) + 1

    return {
        "streak_info": streak_info or {
            "current_streak": 0,
            "longest_streak": 0,
            "total_claims": 0,
            "streak_multiplier": 1.0
        },
        "total_tokens_earned": total_tokens,
        "total_seasonal_bonuses": total_seasonal_bonuses,
        "monthly_activity": monthly_activity,
        "total_days_claimed": len(calendar_entries)
    }
