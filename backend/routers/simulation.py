from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime, timezone, timedelta
import uuid
import random

from core.database import db
from core.auth import get_current_user
from services.token_service import TokenService
from services.notification_service import send_notification

router = APIRouter(prefix="/simulation", tags=["Tokenomics Simulation"])
token_service = TokenService()

class SimulationParams(BaseModel):
    initial_supply: float = 100000000
    burn_rate: float = 0.02
    daily_emissions: float = 10000
    staking_apy: float = 0.12
    user_growth_rate: float = 0.05
    days_to_simulate: int = 365
    transaction_volume_daily: float = 50000

class StakingAction(BaseModel):
    amount: float
    duration_days: int = 30  # 30, 90, 180, 365

class TokenSwap(BaseModel):
    from_token: str
    to_token: str
    amount: float

# ===================== TOKENOMICS SIMULATION =====================

@router.post("/run")
async def run_simulation(
    params: SimulationParams,
    current_user: dict = Depends(get_current_user)
):
    """Run tokenomics simulation"""
    try:
        results = []
        current_supply = params.initial_supply
        total_burned = 0
        users = 1000  # Starting users
        staked = 0
        
        for day in range(1, params.days_to_simulate + 1):
            # Daily emissions
            current_supply += params.daily_emissions
            
            # Transaction burns
            daily_burn = params.transaction_volume_daily * params.burn_rate
            current_supply -= daily_burn
            total_burned += daily_burn
            
            # User growth
            new_users = int(users * params.user_growth_rate / 365)
            users += new_users
            
            # Staking simulation (20% of users stake 10% of their holdings)
            avg_holdings = current_supply / users
            staking_change = users * 0.2 * avg_holdings * 0.1 * (random.random() - 0.3)
            staked = max(0, staked + staking_change)
            
            # Record daily snapshot
            if day % 30 == 0 or day == params.days_to_simulate:
                results.append({
                    "day": day,
                    "circulating_supply": round(current_supply, 2),
                    "total_burned": round(total_burned, 2),
                    "total_users": users,
                    "total_staked": round(staked, 2),
                    "staking_ratio": round(staked / current_supply * 100, 2) if current_supply > 0 else 0,
                    "price_estimate": round(1000000 / current_supply, 6)  # Simple supply-based estimate
                })
        
        # Calculate summary
        summary = {
            "initial_supply": params.initial_supply,
            "final_supply": round(current_supply, 2),
            "total_burned": round(total_burned, 2),
            "burn_percentage": round(total_burned / params.initial_supply * 100, 2),
            "final_users": users,
            "user_growth": round((users - 1000) / 1000 * 100, 2),
            "final_staking_ratio": round(staked / current_supply * 100, 2) if current_supply > 0 else 0
        }
        
        return {
            "summary": summary,
            "timeline": results,
            "params_used": params.dict()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/presets")
async def get_simulation_presets():
    """Get simulation preset configurations"""
    return {
        "presets": [
            {
                "name": "Conservative",
                "description": "Low emission, high burn",
                "params": {
                    "burn_rate": 0.03,
                    "daily_emissions": 5000,
                    "staking_apy": 0.08,
                    "user_growth_rate": 0.03
                }
            },
            {
                "name": "Balanced",
                "description": "Standard parameters",
                "params": {
                    "burn_rate": 0.02,
                    "daily_emissions": 10000,
                    "staking_apy": 0.12,
                    "user_growth_rate": 0.05
                }
            },
            {
                "name": "Aggressive Growth",
                "description": "High emissions for rapid adoption",
                "params": {
                    "burn_rate": 0.015,
                    "daily_emissions": 20000,
                    "staking_apy": 0.18,
                    "user_growth_rate": 0.10
                }
            },
            {
                "name": "Deflationary",
                "description": "Focus on reducing supply",
                "params": {
                    "burn_rate": 0.05,
                    "daily_emissions": 3000,
                    "staking_apy": 0.10,
                    "user_growth_rate": 0.04
                }
            }
        ]
    }

# ===================== STAKING =====================

@router.post("/stake")
async def stake_tokens(
    stake: StakingAction,
    current_user: dict = Depends(get_current_user)
):
    """Stake RLM tokens"""
    try:
        user_id = current_user["id"]
        
        # Validate duration
        valid_durations = [30, 90, 180, 365]
        if stake.duration_days not in valid_durations:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid duration. Choose from: {valid_durations} days"
            )
        
        # Check balance
        user = await db.users.find_one({"id": user_id}, {"realum_balance": 1})
        balance = user.get("realum_balance", 0)
        
        if balance < stake.amount:
            raise HTTPException(status_code=400, detail="Insufficient balance")
        
        if stake.amount < 100:
            raise HTTPException(status_code=400, detail="Minimum stake is 100 RLM")
        
        # Calculate APY based on duration
        apy_multipliers = {30: 1.0, 90: 1.25, 180: 1.5, 365: 2.0}
        base_apy = 0.12
        final_apy = base_apy * apy_multipliers[stake.duration_days]
        
        # Calculate expected reward
        expected_reward = stake.amount * final_apy * (stake.duration_days / 365)
        
        now = datetime.now(timezone.utc)
        unlock_date = now + timedelta(days=stake.duration_days)
        stake_id = str(uuid.uuid4())
        
        # Deduct from balance
        await db.users.update_one(
            {"id": user_id},
            {"$inc": {"realum_balance": -stake.amount}}
        )
        
        # Create stake record
        await db.stakes.insert_one({
            "id": stake_id,
            "user_id": user_id,
            "amount": stake.amount,
            "duration_days": stake.duration_days,
            "apy": final_apy,
            "expected_reward": round(expected_reward, 2),
            "status": "active",
            "staked_at": now.isoformat(),
            "unlocks_at": unlock_date.isoformat()
        })
        
        # Record transaction
        await token_service.create_transaction(
            user_id=user_id,
            tx_type="debit",
            amount=stake.amount,
            description=f"Staked for {stake.duration_days} days at {final_apy*100:.1f}% APY"
        )
        
        return {
            "message": "Tokens staked successfully",
            "stake_id": stake_id,
            "amount": stake.amount,
            "duration_days": stake.duration_days,
            "apy": f"{final_apy*100:.1f}%",
            "expected_reward": round(expected_reward, 2),
            "unlocks_at": unlock_date.isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/unstake/{stake_id}")
async def unstake_tokens(
    stake_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Unstake tokens (with penalty if early)"""
    try:
        user_id = current_user["id"]
        
        stake = await db.stakes.find_one({
            "id": stake_id,
            "user_id": user_id,
            "status": "active"
        })
        
        if not stake:
            raise HTTPException(status_code=404, detail="Stake not found")
        
        now = datetime.now(timezone.utc)
        unlocks_at = datetime.fromisoformat(stake["unlocks_at"].replace('Z', '+00:00'))
        staked_at = datetime.fromisoformat(stake["staked_at"].replace('Z', '+00:00'))
        
        amount = stake["amount"]
        expected_reward = stake["expected_reward"]
        
        if now >= unlocks_at:
            # Full reward
            total_return = amount + expected_reward
            penalty = 0
        else:
            # Early withdrawal penalty (50% of potential rewards + 5% of principal)
            days_staked = (now - staked_at).days
            days_total = stake["duration_days"]
            earned_reward = expected_reward * (days_staked / days_total)
            penalty = expected_reward * 0.5 + amount * 0.05
            total_return = amount + earned_reward - penalty
        
        # Return tokens
        await db.users.update_one(
            {"id": user_id},
            {"$inc": {"realum_balance": total_return}}
        )
        
        # Update stake
        await db.stakes.update_one(
            {"id": stake_id},
            {"$set": {
                "status": "completed",
                "completed_at": now.isoformat(),
                "actual_reward": total_return - amount,
                "penalty": penalty
            }}
        )
        
        # Record transaction
        await token_service.create_transaction(
            user_id=user_id,
            tx_type="credit",
            amount=total_return,
            description=f"Unstaked: {amount} RLM + {total_return - amount:.2f} reward" + 
                       (f" (penalty: {penalty:.2f})" if penalty > 0 else "")
        )
        
        return {
            "message": "Tokens unstaked",
            "principal": amount,
            "reward": round(total_return - amount, 2),
            "penalty": round(penalty, 2),
            "total_returned": round(total_return, 2),
            "early_withdrawal": now < unlocks_at
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/stakes")
async def get_user_stakes(current_user: dict = Depends(get_current_user)):
    """Get user's staking positions"""
    try:
        user_id = current_user["id"]
        
        stakes = await db.stakes.find(
            {"user_id": user_id},
            {"_id": 0}
        ).sort("staked_at", -1).to_list(50)
        
        # Calculate totals
        total_staked = sum(s["amount"] for s in stakes if s["status"] == "active")
        total_expected = sum(s["expected_reward"] for s in stakes if s["status"] == "active")
        
        return {
            "stakes": stakes,
            "summary": {
                "total_staked": total_staked,
                "total_expected_rewards": round(total_expected, 2),
                "active_stakes": len([s for s in stakes if s["status"] == "active"])
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ===================== TOKEN ECONOMY STATS =====================

@router.get("/economy")
async def get_token_economy():
    """Get current token economy statistics"""
    try:
        # Total supply (from all user balances + staked)
        supply_pipeline = [
            {"$group": {"_id": None, "total": {"$sum": "$realum_balance"}}}
        ]
        supply_result = await db.users.aggregate(supply_pipeline).to_list(1)
        circulating = supply_result[0]["total"] if supply_result else 0
        
        # Total staked
        staked_pipeline = [
            {"$match": {"status": "active"}},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
        ]
        staked_result = await db.stakes.aggregate(staked_pipeline).to_list(1)
        total_staked = staked_result[0]["total"] if staked_result else 0
        
        # Total burned
        burn_pipeline = [
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
        ]
        burn_result = await db.burns.aggregate(burn_pipeline).to_list(1)
        total_burned = burn_result[0]["total"] if burn_result else 0
        
        # Transaction volume (last 24h)
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        volume_pipeline = [
            {"$match": {"timestamp": {"$gte": yesterday}}},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
        ]
        volume_result = await db.transactions.aggregate(volume_pipeline).to_list(1)
        daily_volume = volume_result[0]["total"] if volume_result else 0
        
        # Holders count
        holders = await db.users.count_documents({"realum_balance": {"$gt": 0}})
        
        total_supply = circulating + total_staked
        
        return {
            "economy": {
                "total_supply": round(total_supply, 2),
                "circulating_supply": round(circulating, 2),
                "total_staked": round(total_staked, 2),
                "staking_ratio": round(total_staked / total_supply * 100, 2) if total_supply > 0 else 0,
                "total_burned": round(total_burned, 2),
                "burn_rate": 0.02,
                "daily_volume_24h": round(daily_volume, 2),
                "holders": holders
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/leaderboard/stakers")
async def get_top_stakers(limit: int = Query(20, le=100)):
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
        for idx, item in enumerate(results):
            user = await db.users.find_one(
                {"id": item["_id"]},
                {"_id": 0, "username": 1, "avatar_url": 1}
            )
            if user:
                leaderboard.append({
                    "rank": idx + 1,
                    "user_id": item["_id"],
                    "username": user.get("username"),
                    "avatar_url": user.get("avatar_url"),
                    "total_staked": item["total_staked"],
                    "stake_count": item["stake_count"]
                })
        
        return {"leaderboard": leaderboard}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/apy-tiers")
async def get_apy_tiers():
    """Get staking APY tiers"""
    return {
        "tiers": [
            {"duration_days": 30, "base_apy": 12, "multiplier": 1.0, "final_apy": 12},
            {"duration_days": 90, "base_apy": 12, "multiplier": 1.25, "final_apy": 15},
            {"duration_days": 180, "base_apy": 12, "multiplier": 1.5, "final_apy": 18},
            {"duration_days": 365, "base_apy": 12, "multiplier": 2.0, "final_apy": 24}
        ],
        "min_stake": 100,
        "early_withdrawal_penalty": "50% of rewards + 5% of principal"
    }
