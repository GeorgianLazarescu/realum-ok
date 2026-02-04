from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from pydantic import BaseModel
import uuid

from core.database import db
from core.auth import get_current_user

router = APIRouter(prefix="/api/defi", tags=["DeFi & Staking"])

class StakeCreate(BaseModel):
    amount: float
    duration_days: int = 30  # 30, 90, 180, 365

class UnstakeRequest(BaseModel):
    stake_id: str

# Staking APY rates based on duration
STAKING_RATES = {
    30: 5.0,    # 5% APY for 30 days
    90: 8.0,    # 8% APY for 90 days
    180: 12.0,  # 12% APY for 180 days
    365: 18.0   # 18% APY for 365 days
}

@router.get("/staking/rates")
async def get_staking_rates():
    """Get current staking rates"""
    return {
        "rates": [
            {"duration_days": d, "apy": r, "label": f"{d} days"}
            for d, r in STAKING_RATES.items()
        ],
        "min_stake": 100,
        "max_stake": 1000000
    }

@router.post("/staking/stake")
async def stake_tokens(
    stake: StakeCreate,
    current_user: dict = Depends(get_current_user)
):
    """Stake RLM tokens"""
    try:
        if stake.duration_days not in STAKING_RATES:
            raise HTTPException(status_code=400, detail="Invalid staking duration")
        
        if stake.amount < 100:
            raise HTTPException(status_code=400, detail="Minimum stake is 100 RLM")
        
        # Check user balance
        user = await db.users.find_one({"id": current_user["id"]})
        if not user or user.get("realum_balance", 0) < stake.amount:
            raise HTTPException(status_code=400, detail="Insufficient balance")
        
        now = datetime.now(timezone.utc)
        end_date = now + timedelta(days=stake.duration_days)
        apy = STAKING_RATES[stake.duration_days]
        
        # Calculate expected rewards
        expected_reward = stake.amount * (apy / 100) * (stake.duration_days / 365)
        
        stake_id = str(uuid.uuid4())
        
        stake_data = {
            "id": stake_id,
            "user_id": current_user["id"],
            "amount": stake.amount,
            "duration_days": stake.duration_days,
            "apy": apy,
            "expected_reward": round(expected_reward, 2),
            "start_date": now.isoformat(),
            "end_date": end_date.isoformat(),
            "status": "active",
            "rewards_claimed": 0,
            "created_at": now.isoformat()
        }
        
        # Deduct from balance
        await db.users.update_one(
            {"id": current_user["id"]},
            {"$inc": {"realum_balance": -stake.amount}}
        )
        
        await db.stakes.insert_one(stake_data)
        stake_data.pop("_id", None)
        
        return {"message": "Tokens staked", "stake": stake_data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/staking/my-stakes")
async def get_my_stakes(current_user: dict = Depends(get_current_user)):
    """Get user's staking positions"""
    try:
        stakes = await db.stakes.find(
            {"user_id": current_user["id"]},
            {"_id": 0}
        ).sort("created_at", -1).to_list(50)
        
        now = datetime.now(timezone.utc)
        total_staked = 0
        total_rewards = 0
        
        for stake in stakes:
            if stake["status"] == "active":
                total_staked += stake["amount"]
                
                # Calculate accrued rewards
                start = datetime.fromisoformat(stake["start_date"].replace("Z", "+00:00"))
                days_elapsed = (now - start).days
                accrued = stake["amount"] * (stake["apy"] / 100) * (days_elapsed / 365)
                stake["accrued_rewards"] = round(accrued, 2)
                total_rewards += accrued
                
                # Check if matured
                end = datetime.fromisoformat(stake["end_date"].replace("Z", "+00:00"))
                stake["is_matured"] = now >= end
                stake["days_remaining"] = max(0, (end - now).days)
        
        return {
            "stakes": stakes,
            "summary": {
                "total_staked": total_staked,
                "total_accrued_rewards": round(total_rewards, 2),
                "active_stakes": sum(1 for s in stakes if s["status"] == "active")
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/staking/unstake")
async def unstake_tokens(
    request: UnstakeRequest,
    current_user: dict = Depends(get_current_user)
):
    """Unstake tokens (with penalty if early)"""
    try:
        stake = await db.stakes.find_one({
            "id": request.stake_id,
            "user_id": current_user["id"],
            "status": "active"
        })
        
        if not stake:
            raise HTTPException(status_code=404, detail="Stake not found")
        
        now = datetime.now(timezone.utc)
        end = datetime.fromisoformat(stake["end_date"].replace("Z", "+00:00"))
        start = datetime.fromisoformat(stake["start_date"].replace("Z", "+00:00"))
        
        is_early = now < end
        days_elapsed = (now - start).days
        
        # Calculate rewards
        accrued = stake["amount"] * (stake["apy"] / 100) * (days_elapsed / 365)
        
        # Early withdrawal penalty: 50% of accrued rewards
        if is_early:
            penalty = accrued * 0.5
            final_reward = accrued - penalty
        else:
            penalty = 0
            final_reward = accrued
        
        return_amount = stake["amount"] + final_reward
        
        # Update user balance
        await db.users.update_one(
            {"id": current_user["id"]},
            {"$inc": {"realum_balance": return_amount}}
        )
        
        # Update stake status
        await db.stakes.update_one(
            {"id": request.stake_id},
            {"$set": {
                "status": "completed",
                "rewards_claimed": round(final_reward, 2),
                "penalty_applied": round(penalty, 2) if is_early else 0,
                "completed_at": now.isoformat()
            }}
        )
        
        return {
            "message": "Tokens unstaked",
            "principal": stake["amount"],
            "rewards": round(final_reward, 2),
            "penalty": round(penalty, 2) if is_early else 0,
            "total_returned": round(return_amount, 2),
            "early_withdrawal": is_early
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/staking/leaderboard")
async def get_staking_leaderboard(limit: int = 20):
    """Get top stakers leaderboard"""
    try:
        pipeline = [
            {"$match": {"status": "active"}},
            {"$group": {
                "_id": "$user_id",
                "total_staked": {"$sum": "$amount"},
                "stake_count": {"$sum": 1}
            }},
            {"$sort": {"total_staked": -1}},
            {"$limit": limit}
        ]
        
        results = await db.stakes.aggregate(pipeline).to_list(limit)
        
        leaderboard = []
        for i, r in enumerate(results):
            user = await db.users.find_one(
                {"id": r["_id"]},
                {"_id": 0, "username": 1, "avatar_url": 1}
            )
            if user:
                leaderboard.append({
                    "rank": i + 1,
                    "user_id": r["_id"],
                    "username": user.get("username"),
                    "avatar_url": user.get("avatar_url"),
                    "total_staked": r["total_staked"],
                    "stake_count": r["stake_count"]
                })
        
        return {"leaderboard": leaderboard}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/staking/stats")
async def get_staking_stats():
    """Get global staking statistics"""
    try:
        # Total staked
        pipeline = [
            {"$match": {"status": "active"}},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}, "count": {"$sum": 1}}}
        ]
        result = await db.stakes.aggregate(pipeline).to_list(1)
        
        total_staked = result[0]["total"] if result else 0
        active_stakes = result[0]["count"] if result else 0
        
        # Unique stakers
        unique_stakers = len(await db.stakes.distinct("user_id", {"status": "active"}))
        
        # Total rewards distributed
        rewards_pipeline = [
            {"$match": {"status": "completed"}},
            {"$group": {"_id": None, "total": {"$sum": "$rewards_claimed"}}}
        ]
        rewards_result = await db.stakes.aggregate(rewards_pipeline).to_list(1)
        total_rewards = rewards_result[0]["total"] if rewards_result else 0
        
        return {
            "stats": {
                "total_staked": total_staked,
                "active_stakes": active_stakes,
                "unique_stakers": unique_stakers,
                "total_rewards_distributed": round(total_rewards, 2),
                "average_stake": round(total_staked / active_stakes, 2) if active_stakes > 0 else 0
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
