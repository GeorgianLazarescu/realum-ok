from fastapi import APIRouter, HTTPException, Depends, Query
from datetime import datetime, timezone
import uuid
import random
import string

from core.database import db
from core.auth import get_current_user
from services.token_service import create_transaction, add_xp, award_badge

router = APIRouter(prefix="/referral", tags=["Referral System"])

# Referral rewards configuration
REFERRER_REWARD_RLM = 100  # Reward for the person who referred
REFERRER_REWARD_XP = 200
REFEREE_BONUS_RLM = 50  # Bonus for the new user who used a referral
REFEREE_BONUS_XP = 100
REQUIRED_LEVEL_FOR_REWARD = 2  # Referred user must reach this level

REFERRAL_MILESTONES = {
    5: {"badge": "friendly_inviter", "bonus_rlm": 250},
    10: {"badge": "social_butterfly", "bonus_rlm": 500},
    25: {"badge": "community_builder", "bonus_rlm": 1500},
    50: {"badge": "growth_champion", "bonus_rlm": 5000},
    100: {"badge": "viral_legend", "bonus_rlm": 15000}
}

def generate_referral_code():
    """Generate a unique 8-character referral code"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

@router.get("/code")
async def get_referral_code(current_user: dict = Depends(get_current_user)):
    """Get or create user's referral code"""
    user_id = current_user["id"]
    
    # Check if user already has a referral code
    referral_code = current_user.get("referral_code")
    
    if not referral_code:
        # Generate new code
        referral_code = generate_referral_code()
        # Ensure uniqueness
        while await db.users.find_one({"referral_code": referral_code}):
            referral_code = generate_referral_code()
        
        # Save to user
        await db.users.update_one(
            {"id": user_id},
            {"$set": {"referral_code": referral_code}}
        )
    
    return {
        "referral_code": referral_code,
        "referral_link": f"https://realum.io/register?ref={referral_code}"
    }

@router.get("/stats")
async def get_referral_stats(current_user: dict = Depends(get_current_user)):
    """Get referral statistics for current user"""
    user_id = current_user["id"]
    
    # Get all referrals
    referrals = await db.referrals.find(
        {"referrer_id": user_id}, {"_id": 0}
    ).to_list(100)
    
    total_invited = len(referrals)
    completed = sum(1 for r in referrals if r.get("completed"))
    pending = sum(1 for r in referrals if not r.get("completed"))
    total_earned = sum(r.get("reward_given", 0) for r in referrals)
    
    # Get next milestone
    next_milestone = None
    for count, rewards in sorted(REFERRAL_MILESTONES.items()):
        if completed < count:
            next_milestone = {
                "required": count,
                "current": completed,
                "bonus_rlm": rewards["bonus_rlm"],
                "badge": rewards["badge"]
            }
            break
    
    return {
        "referral_code": current_user.get("referral_code"),
        "total_invited": total_invited,
        "completed": completed,
        "pending": pending,
        "total_earned": total_earned,
        "next_milestone": next_milestone,
        "referrals": referrals[-10:]  # Last 10 referrals
    }

@router.post("/apply")
async def apply_referral_code(
    code: str = Query(..., description="Referral code to apply"),
    current_user: dict = Depends(get_current_user)
):
    """Apply a referral code (for new users only)"""
    user_id = current_user["id"]
    
    # Check if user already has a referrer
    if current_user.get("referred_by"):
        raise HTTPException(status_code=400, detail="Already have a referrer")
    
    # Check if user is too high level (should apply early)
    if current_user.get("level", 1) >= REQUIRED_LEVEL_FOR_REWARD:
        raise HTTPException(status_code=400, detail="Too late to apply referral code")
    
    # Find referrer by code
    referrer = await db.users.find_one({"referral_code": code.upper()}, {"_id": 0})
    if not referrer:
        raise HTTPException(status_code=404, detail="Invalid referral code")
    
    if referrer["id"] == user_id:
        raise HTTPException(status_code=400, detail="Cannot refer yourself")
    
    # Create referral record
    referral = {
        "id": str(uuid.uuid4()),
        "referrer_id": referrer["id"],
        "referrer_name": referrer["username"],
        "referee_id": user_id,
        "referee_name": current_user["username"],
        "completed": False,
        "reward_given": 0,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.referrals.insert_one(referral)
    
    # Update user with referrer
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"referred_by": referrer["id"]}}
    )
    
    # Give immediate bonus to new user
    await db.users.update_one(
        {"id": user_id},
        {"$inc": {"realum_balance": REFEREE_BONUS_RLM}}
    )
    await add_xp(user_id, REFEREE_BONUS_XP)
    await create_transaction(
        user_id, "credit", REFEREE_BONUS_RLM,
        f"Referral bonus from {referrer['username']}"
    )
    
    return {
        "status": "applied",
        "referrer": referrer["username"],
        "bonus_received": REFEREE_BONUS_RLM,
        "xp_received": REFEREE_BONUS_XP,
        "message": f"Reach level {REQUIRED_LEVEL_FOR_REWARD} to complete the referral and reward your friend!"
    }

@router.post("/check-completion")
async def check_referral_completion(current_user: dict = Depends(get_current_user)):
    """Check and process referral completion when user levels up"""
    user_id = current_user["id"]
    user_level = current_user.get("level", 1)
    
    # Check if user was referred
    referred_by = current_user.get("referred_by")
    if not referred_by:
        return {"status": "no_referrer"}
    
    # Check if already completed
    referral = await db.referrals.find_one({
        "referee_id": user_id,
        "referrer_id": referred_by
    })
    
    if not referral:
        return {"status": "referral_not_found"}
    
    if referral.get("completed"):
        return {"status": "already_completed"}
    
    # Check if user reached required level
    if user_level < REQUIRED_LEVEL_FOR_REWARD:
        return {
            "status": "pending",
            "current_level": user_level,
            "required_level": REQUIRED_LEVEL_FOR_REWARD
        }
    
    # Complete the referral!
    now = datetime.now(timezone.utc).isoformat()
    
    # Update referral record
    await db.referrals.update_one(
        {"id": referral["id"]},
        {
            "$set": {
                "completed": True,
                "completed_at": now,
                "reward_given": REFERRER_REWARD_RLM
            }
        }
    )
    
    # Reward the referrer
    await db.users.update_one(
        {"id": referred_by},
        {"$inc": {"realum_balance": REFERRER_REWARD_RLM}}
    )
    await add_xp(referred_by, REFERRER_REWARD_XP)
    await create_transaction(
        referred_by, "credit", REFERRER_REWARD_RLM,
        f"Referral completed: {current_user['username']} reached level {REQUIRED_LEVEL_FOR_REWARD}"
    )
    
    # Check for milestone rewards
    completed_count = await db.referrals.count_documents({
        "referrer_id": referred_by,
        "completed": True
    })
    
    milestone_reached = None
    if completed_count in REFERRAL_MILESTONES:
        milestone = REFERRAL_MILESTONES[completed_count]
        await db.users.update_one(
            {"id": referred_by},
            {"$inc": {"realum_balance": milestone["bonus_rlm"]}}
        )
        await award_badge(referred_by, milestone["badge"])
        await create_transaction(
            referred_by, "credit", milestone["bonus_rlm"],
            f"Referral milestone: {completed_count} successful referrals!"
        )
        milestone_reached = {
            "count": completed_count,
            "badge": milestone["badge"],
            "bonus": milestone["bonus_rlm"]
        }
    
    # Award first referral badge
    if completed_count == 1:
        await award_badge(referred_by, "first_referral")
    
    return {
        "status": "completed",
        "referrer_rewarded": REFERRER_REWARD_RLM,
        "milestone_reached": milestone_reached
    }

@router.get("/leaderboard")
async def get_referral_leaderboard():
    """Get top referrers"""
    pipeline = [
        {"$match": {"completed": True}},
        {"$group": {
            "_id": "$referrer_id",
            "referrer_name": {"$first": "$referrer_name"},
            "count": {"$sum": 1},
            "total_earned": {"$sum": "$reward_given"}
        }},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    
    results = await db.referrals.aggregate(pipeline).to_list(10)
    
    leaderboard = []
    for i, r in enumerate(results, 1):
        leaderboard.append({
            "rank": i,
            "username": r["referrer_name"],
            "referrals": r["count"],
            "total_earned": r["total_earned"]
        })
    
    return {"leaderboard": leaderboard}
