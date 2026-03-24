"""
REALUM Battle Pass System
Seasonal progression with free and premium tracks
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime, timezone, timedelta
import uuid

router = APIRouter(prefix="/api/battlepass", tags=["Battle Pass"])

from core.database import db
from core.auth import get_current_user
from core.utils import serialize_doc


# ============== CONSTANTS ==============

CURRENT_SEASON = 1
SEASON_NAME = "Geneza"
SEASON_END_DATE = "2026-06-01T00:00:00Z"

# XP needed per level
XP_PER_LEVEL = 1000
MAX_LEVEL = 50

# Battle Pass cost
BATTLE_PASS_COST = 500  # RLM

# Rewards per level (free and premium tracks)
BATTLE_PASS_REWARDS = {
    1: {"free": {"rlm": 50}, "premium": {"rlm": 100, "badge": "season1_starter"}},
    2: {"free": {"xp_boost": 1.1}, "premium": {"rlm": 75}},
    3: {"free": {"rlm": 30}, "premium": {"cosmetic": "avatar_glow_cyan"}},
    4: {"free": None, "premium": {"rlm": 100}},
    5: {"free": {"rlm": 75, "badge": "level5_free"}, "premium": {"rlm": 150, "cosmetic": "title_early_bird"}},
    6: {"free": {"xp_boost": 1.15}, "premium": {"rlm": 100}},
    7: {"free": {"rlm": 40}, "premium": {"cosmetic": "avatar_frame_gold"}},
    8: {"free": None, "premium": {"rlm": 125}},
    9: {"free": {"rlm": 50}, "premium": {"rlm": 100}},
    10: {"free": {"rlm": 100, "badge": "level10_milestone"}, "premium": {"rlm": 250, "cosmetic": "emote_victory", "badge": "premium_10"}},
    11: {"free": {"xp_boost": 1.2}, "premium": {"rlm": 100}},
    12: {"free": {"rlm": 50}, "premium": {"cosmetic": "chat_color_gold"}},
    13: {"free": None, "premium": {"rlm": 125}},
    14: {"free": {"rlm": 60}, "premium": {"rlm": 100}},
    15: {"free": {"rlm": 100}, "premium": {"rlm": 200, "cosmetic": "avatar_effect_sparkle"}},
    16: {"free": {"xp_boost": 1.25}, "premium": {"rlm": 100}},
    17: {"free": {"rlm": 50}, "premium": {"cosmetic": "profile_banner_1"}},
    18: {"free": None, "premium": {"rlm": 150}},
    19: {"free": {"rlm": 75}, "premium": {"rlm": 100}},
    20: {"free": {"rlm": 150, "badge": "level20_milestone"}, "premium": {"rlm": 300, "cosmetic": "title_veteran", "badge": "premium_20"}},
    21: {"free": {"xp_boost": 1.3}, "premium": {"rlm": 125}},
    22: {"free": {"rlm": 60}, "premium": {"cosmetic": "emote_dance"}},
    23: {"free": None, "premium": {"rlm": 150}},
    24: {"free": {"rlm": 80}, "premium": {"rlm": 125}},
    25: {"free": {"rlm": 125}, "premium": {"rlm": 250, "cosmetic": "avatar_glow_rainbow"}},
    26: {"free": {"xp_boost": 1.35}, "premium": {"rlm": 125}},
    27: {"free": {"rlm": 70}, "premium": {"cosmetic": "chat_effect_fire"}},
    28: {"free": None, "premium": {"rlm": 175}},
    29: {"free": {"rlm": 90}, "premium": {"rlm": 150}},
    30: {"free": {"rlm": 200, "badge": "level30_elite"}, "premium": {"rlm": 400, "cosmetic": "title_elite", "badge": "premium_30"}},
    31: {"free": {"xp_boost": 1.4}, "premium": {"rlm": 150}},
    32: {"free": {"rlm": 80}, "premium": {"cosmetic": "profile_banner_2"}},
    33: {"free": None, "premium": {"rlm": 175}},
    34: {"free": {"rlm": 100}, "premium": {"rlm": 150}},
    35: {"free": {"rlm": 150}, "premium": {"rlm": 300, "cosmetic": "emote_legendary"}},
    36: {"free": {"xp_boost": 1.45}, "premium": {"rlm": 175}},
    37: {"free": {"rlm": 90}, "premium": {"cosmetic": "avatar_effect_lightning"}},
    38: {"free": None, "premium": {"rlm": 200}},
    39: {"free": {"rlm": 110}, "premium": {"rlm": 175}},
    40: {"free": {"rlm": 250, "badge": "level40_master"}, "premium": {"rlm": 500, "cosmetic": "title_master", "badge": "premium_40"}},
    41: {"free": {"xp_boost": 1.5}, "premium": {"rlm": 200}},
    42: {"free": {"rlm": 100}, "premium": {"cosmetic": "chat_effect_ice"}},
    43: {"free": None, "premium": {"rlm": 225}},
    44: {"free": {"rlm": 125}, "premium": {"rlm": 200}},
    45: {"free": {"rlm": 200}, "premium": {"rlm": 400, "cosmetic": "avatar_frame_legendary"}},
    46: {"free": {"xp_boost": 1.6}, "premium": {"rlm": 225}},
    47: {"free": {"rlm": 125}, "premium": {"cosmetic": "profile_banner_legendary"}},
    48: {"free": None, "premium": {"rlm": 250}},
    49: {"free": {"rlm": 150}, "premium": {"rlm": 250}},
    50: {"free": {"rlm": 500, "badge": "season1_complete"}, "premium": {"rlm": 1000, "cosmetic": "title_legend", "badge": "premium_legend", "exclusive": "avatar_legendary_skin"}},
}

# Weekly challenges
WEEKLY_CHALLENGES = [
    {"id": "login_7", "name": "Zilnic Devotat", "description": "Loghează-te 7 zile", "xp": 500, "target": 7, "type": "login"},
    {"id": "trade_5", "name": "Comerciant", "description": "Efectuează 5 tranzacții pe bursă", "xp": 400, "target": 5, "type": "trade"},
    {"id": "chat_20", "name": "Social", "description": "Trimite 20 de mesaje în chat", "xp": 300, "target": 20, "type": "chat"},
    {"id": "guild_activity", "name": "Spirit de Echipă", "description": "Participă la 3 activități de guild", "xp": 450, "target": 3, "type": "guild"},
    {"id": "mini_games", "name": "Gamer", "description": "Joacă 10 mini-jocuri", "xp": 350, "target": 10, "type": "games"},
    {"id": "earn_1000", "name": "Profitabil", "description": "Câștigă 1000 RLM", "xp": 600, "target": 1000, "type": "earn"},
    {"id": "vote_3", "name": "Civic", "description": "Votează în 3 alegeri/propuneri", "xp": 400, "target": 3, "type": "vote"},
    {"id": "complete_quest", "name": "Aventurier", "description": "Completează un quest", "xp": 500, "target": 1, "type": "quest"},
]


# ============== MODELS ==============

class PurchaseBattlePass(BaseModel):
    use_rlm: bool = True  # Use RLM balance to purchase


# ============== HELPER FUNCTIONS ==============

def get_level_from_xp(xp: int) -> int:
    """Calculate level from XP"""
    return min(xp // XP_PER_LEVEL + 1, MAX_LEVEL)

def get_xp_for_next_level(current_xp: int) -> dict:
    """Get XP progress for current level"""
    level = get_level_from_xp(current_xp)
    if level >= MAX_LEVEL:
        return {"current": XP_PER_LEVEL, "needed": XP_PER_LEVEL, "percentage": 100}
    
    xp_in_level = current_xp % XP_PER_LEVEL
    return {
        "current": xp_in_level,
        "needed": XP_PER_LEVEL,
        "percentage": round(xp_in_level / XP_PER_LEVEL * 100, 1)
    }


# ============== ENDPOINTS ==============

@router.get("/info")
async def get_battle_pass_info():
    """Get current season battle pass info"""
    now = datetime.now(timezone.utc)
    end_date = datetime.fromisoformat(SEASON_END_DATE.replace('Z', '+00:00'))
    days_remaining = (end_date - now).days
    
    # Calculate total rewards
    total_free_rlm = sum(r["free"].get("rlm", 0) for r in BATTLE_PASS_REWARDS.values() if r["free"])
    total_premium_rlm = sum(r["premium"].get("rlm", 0) for r in BATTLE_PASS_REWARDS.values())
    
    return {
        "season": CURRENT_SEASON,
        "name": SEASON_NAME,
        "end_date": SEASON_END_DATE,
        "days_remaining": max(0, days_remaining),
        "max_level": MAX_LEVEL,
        "xp_per_level": XP_PER_LEVEL,
        "pass_cost": BATTLE_PASS_COST,
        "total_free_rlm": total_free_rlm,
        "total_premium_rlm": total_premium_rlm,
        "rewards_preview": {k: v for k, v in list(BATTLE_PASS_REWARDS.items())[:10]}
    }


@router.get("/my-progress")
async def get_my_battle_pass(current_user: dict = Depends(get_current_user)):
    """Get user's battle pass progress"""
    user_id = current_user["id"]
    
    # Get or create battle pass progress
    progress = await db.battle_pass_progress.find_one({"user_id": user_id, "season": CURRENT_SEASON})
    
    if not progress:
        progress = {
            "user_id": user_id,
            "season": CURRENT_SEASON,
            "xp": 0,
            "level": 1,
            "is_premium": False,
            "claimed_free": [],
            "claimed_premium": [],
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.battle_pass_progress.insert_one(progress)
    
    level = get_level_from_xp(progress.get("xp", 0))
    level_progress = get_xp_for_next_level(progress.get("xp", 0))
    
    # Get unclaimed rewards
    unclaimed_free = []
    unclaimed_premium = []
    claimed_free = progress.get("claimed_free", [])
    claimed_premium = progress.get("claimed_premium", [])
    
    for lvl in range(1, level + 1):
        rewards = BATTLE_PASS_REWARDS.get(lvl, {})
        if rewards.get("free") and lvl not in claimed_free:
            unclaimed_free.append({"level": lvl, "rewards": rewards["free"]})
        if rewards.get("premium") and lvl not in claimed_premium and progress.get("is_premium"):
            unclaimed_premium.append({"level": lvl, "rewards": rewards["premium"]})
    
    # Get weekly challenges progress
    weekly_progress = await db.battle_pass_weekly.find_one({
        "user_id": user_id,
        "season": CURRENT_SEASON,
        "week": get_current_week()
    })
    
    return {
        "season": CURRENT_SEASON,
        "season_name": SEASON_NAME,
        "level": level,
        "xp": progress.get("xp", 0),
        "level_progress": level_progress,
        "is_premium": progress.get("is_premium", False),
        "unclaimed_free": unclaimed_free,
        "unclaimed_premium": unclaimed_premium,
        "claimed_free_count": len(claimed_free),
        "claimed_premium_count": len(claimed_premium),
        "weekly_challenges": weekly_progress.get("challenges", []) if weekly_progress else [],
        "all_rewards": BATTLE_PASS_REWARDS
    }


def get_current_week():
    """Get current week number of the season"""
    now = datetime.now(timezone.utc)
    # Assume season started at beginning of year
    season_start = datetime(now.year, 1, 1, tzinfo=timezone.utc)
    return ((now - season_start).days // 7) + 1


@router.post("/purchase")
async def purchase_battle_pass(
    data: PurchaseBattlePass,
    current_user: dict = Depends(get_current_user)
):
    """Purchase premium battle pass"""
    user_id = current_user["id"]
    
    # Check if already purchased
    progress = await db.battle_pass_progress.find_one({
        "user_id": user_id,
        "season": CURRENT_SEASON
    })
    
    if progress and progress.get("is_premium"):
        raise HTTPException(status_code=400, detail="Battle Pass already purchased for this season")
    
    # Check balance
    if current_user.get("realum_balance", 0) < BATTLE_PASS_COST:
        raise HTTPException(status_code=400, detail=f"Insufficient balance. Need {BATTLE_PASS_COST} RLM")
    
    # Deduct cost
    await db.users.update_one(
        {"id": user_id},
        {"$inc": {"realum_balance": -BATTLE_PASS_COST}}
    )
    
    # Update battle pass
    now = datetime.now(timezone.utc)
    
    if progress:
        await db.battle_pass_progress.update_one(
            {"user_id": user_id, "season": CURRENT_SEASON},
            {"$set": {"is_premium": True, "purchased_at": now.isoformat()}}
        )
    else:
        await db.battle_pass_progress.insert_one({
            "user_id": user_id,
            "season": CURRENT_SEASON,
            "xp": 0,
            "level": 1,
            "is_premium": True,
            "claimed_free": [],
            "claimed_premium": [],
            "purchased_at": now.isoformat(),
            "created_at": now.isoformat()
        })
    
    # Award purchase badge
    await db.user_badges.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "badge_key": f"battlepass_s{CURRENT_SEASON}",
        "awarded_at": now.isoformat()
    })
    
    return {
        "message": "Battle Pass Premium purchased!",
        "season": CURRENT_SEASON,
        "cost": BATTLE_PASS_COST
    }


@router.post("/claim/{level}")
async def claim_reward(
    level: int,
    track: str = "free",  # "free" or "premium"
    current_user: dict = Depends(get_current_user)
):
    """Claim a battle pass reward"""
    user_id = current_user["id"]
    
    if level < 1 or level > MAX_LEVEL:
        raise HTTPException(status_code=400, detail="Invalid level")
    
    if track not in ["free", "premium"]:
        raise HTTPException(status_code=400, detail="Track must be 'free' or 'premium'")
    
    progress = await db.battle_pass_progress.find_one({
        "user_id": user_id,
        "season": CURRENT_SEASON
    })
    
    if not progress:
        raise HTTPException(status_code=400, detail="No battle pass progress found")
    
    current_level = get_level_from_xp(progress.get("xp", 0))
    
    if level > current_level:
        raise HTTPException(status_code=400, detail=f"Level not reached. Current: {current_level}")
    
    if track == "premium" and not progress.get("is_premium"):
        raise HTTPException(status_code=400, detail="Premium Battle Pass required")
    
    claimed_key = f"claimed_{track}"
    if level in progress.get(claimed_key, []):
        raise HTTPException(status_code=400, detail="Reward already claimed")
    
    # Get reward
    rewards = BATTLE_PASS_REWARDS.get(level, {}).get(track)
    if not rewards:
        raise HTTPException(status_code=400, detail="No reward at this level")
    
    # Apply rewards
    result = {"claimed": rewards}
    
    if "rlm" in rewards:
        await db.users.update_one(
            {"id": user_id},
            {"$inc": {"realum_balance": rewards["rlm"]}}
        )
        result["rlm_added"] = rewards["rlm"]
    
    if "xp_boost" in rewards:
        # Store XP boost for user
        await db.user_boosts.update_one(
            {"user_id": user_id},
            {"$set": {f"xp_multiplier_s{CURRENT_SEASON}": rewards["xp_boost"]}},
            upsert=True
        )
        result["xp_boost"] = rewards["xp_boost"]
    
    if "badge" in rewards:
        await db.user_badges.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "badge_key": rewards["badge"],
            "awarded_at": datetime.now(timezone.utc).isoformat()
        })
        result["badge_awarded"] = rewards["badge"]
    
    if "cosmetic" in rewards:
        await db.user_cosmetics.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "cosmetic_key": rewards["cosmetic"],
            "source": f"battlepass_s{CURRENT_SEASON}_level{level}",
            "awarded_at": datetime.now(timezone.utc).isoformat()
        })
        result["cosmetic_awarded"] = rewards["cosmetic"]
    
    # Mark as claimed
    await db.battle_pass_progress.update_one(
        {"user_id": user_id, "season": CURRENT_SEASON},
        {"$push": {claimed_key: level}}
    )
    
    return result


@router.post("/add-xp")
async def add_battle_pass_xp(
    xp_amount: int,
    current_user: dict = Depends(get_current_user)
):
    """Add XP to battle pass (internal use for activities)"""
    user_id = current_user["id"]
    
    progress = await db.battle_pass_progress.find_one({
        "user_id": user_id,
        "season": CURRENT_SEASON
    })
    
    old_level = 1
    old_xp = 0
    
    if progress:
        old_xp = progress.get("xp", 0)
        old_level = get_level_from_xp(old_xp)
    
    new_xp = old_xp + xp_amount
    new_level = get_level_from_xp(new_xp)
    
    if progress:
        await db.battle_pass_progress.update_one(
            {"user_id": user_id, "season": CURRENT_SEASON},
            {"$set": {"xp": new_xp, "level": new_level}}
        )
    else:
        await db.battle_pass_progress.insert_one({
            "user_id": user_id,
            "season": CURRENT_SEASON,
            "xp": new_xp,
            "level": new_level,
            "is_premium": False,
            "claimed_free": [],
            "claimed_premium": [],
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    
    leveled_up = new_level > old_level
    
    return {
        "xp_added": xp_amount,
        "new_xp": new_xp,
        "new_level": new_level,
        "leveled_up": leveled_up,
        "levels_gained": new_level - old_level if leveled_up else 0
    }


@router.get("/weekly-challenges")
async def get_weekly_challenges(current_user: dict = Depends(get_current_user)):
    """Get current week's challenges"""
    user_id = current_user["id"]
    current_week = get_current_week()
    
    # Get user's weekly progress
    weekly = await db.battle_pass_weekly.find_one({
        "user_id": user_id,
        "season": CURRENT_SEASON,
        "week": current_week
    })
    
    if not weekly:
        # Initialize weekly challenges
        challenges = []
        for i, ch in enumerate(WEEKLY_CHALLENGES[:5]):  # 5 challenges per week
            challenges.append({
                "id": ch["id"],
                "name": ch["name"],
                "description": ch["description"],
                "xp_reward": ch["xp"],
                "target": ch["target"],
                "progress": 0,
                "completed": False,
                "claimed": False
            })
        
        weekly = {
            "user_id": user_id,
            "season": CURRENT_SEASON,
            "week": current_week,
            "challenges": challenges,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.battle_pass_weekly.insert_one(weekly)
    
    return {
        "week": current_week,
        "challenges": weekly["challenges"],
        "total_xp_available": sum(c["xp_reward"] for c in weekly["challenges"] if not c["claimed"])
    }


@router.post("/weekly-challenges/{challenge_id}/claim")
async def claim_weekly_challenge(
    challenge_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Claim completed weekly challenge reward"""
    user_id = current_user["id"]
    current_week = get_current_week()
    
    weekly = await db.battle_pass_weekly.find_one({
        "user_id": user_id,
        "season": CURRENT_SEASON,
        "week": current_week
    })
    
    if not weekly:
        raise HTTPException(status_code=404, detail="Weekly challenges not found")
    
    challenge = None
    for ch in weekly["challenges"]:
        if ch["id"] == challenge_id:
            challenge = ch
            break
    
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")
    
    if not challenge["completed"]:
        raise HTTPException(status_code=400, detail="Challenge not completed")
    
    if challenge["claimed"]:
        raise HTTPException(status_code=400, detail="Already claimed")
    
    # Mark as claimed
    await db.battle_pass_weekly.update_one(
        {"user_id": user_id, "season": CURRENT_SEASON, "week": current_week, "challenges.id": challenge_id},
        {"$set": {"challenges.$.claimed": True}}
    )
    
    # Add XP to battle pass
    xp_reward = challenge["xp_reward"]
    
    # Update battle pass XP
    await db.battle_pass_progress.update_one(
        {"user_id": user_id, "season": CURRENT_SEASON},
        {"$inc": {"xp": xp_reward}},
        upsert=True
    )
    
    return {
        "message": f"Claimed {xp_reward} XP!",
        "xp_earned": xp_reward
    }


@router.get("/leaderboard")
async def get_battle_pass_leaderboard(limit: int = 20):
    """Get battle pass level leaderboard"""
    
    leaders = await db.battle_pass_progress.find(
        {"season": CURRENT_SEASON},
        {"_id": 0}
    ).sort("xp", -1).limit(limit).to_list(limit)
    
    leaderboard = []
    for i, progress in enumerate(leaders, 1):
        user = await db.users.find_one({"id": progress["user_id"]}, {"_id": 0, "username": 1})
        if user:
            leaderboard.append({
                "rank": i,
                "username": user["username"],
                "level": get_level_from_xp(progress.get("xp", 0)),
                "xp": progress.get("xp", 0),
                "is_premium": progress.get("is_premium", False)
            })
    
    return {"leaderboard": leaderboard, "season": CURRENT_SEASON}
