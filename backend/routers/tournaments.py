"""
REALUM Tournaments & Competitive Events
Competitions, tournaments, and seasonal events
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import uuid
import random

router = APIRouter(prefix="/api/tournaments", tags=["Tournaments"])

from core.database import db
from core.auth import get_current_user


# ============== TOURNAMENT TYPES ==============

TOURNAMENT_TYPES = {
    "stock_trading": {
        "name": "Trading Championship",
        "description": "Compete for the highest portfolio gains",
        "metric": "portfolio_gain_percent",
        "duration_hours": 168,  # 1 week
        "entry_fee": 100,
        "min_participants": 10,
        "max_participants": 100,
        "prizes": {
            1: {"rlm": 5000, "badge": "trading_champion"},
            2: {"rlm": 2500},
            3: {"rlm": 1000},
            "top10": {"rlm": 250}
        }
    },
    "daily_streak": {
        "name": "Streak Masters",
        "description": "Longest daily login streak wins",
        "metric": "streak_length",
        "duration_hours": 720,  # 30 days
        "entry_fee": 0,
        "min_participants": 5,
        "max_participants": 500,
        "prizes": {
            1: {"rlm": 3000, "badge": "streak_master"},
            2: {"rlm": 1500},
            3: {"rlm": 750},
            "top10": {"rlm": 100}
        }
    },
    "mini_games": {
        "name": "Games Tournament",
        "description": "Highest score across all mini-games",
        "metric": "total_game_score",
        "duration_hours": 72,  # 3 days
        "entry_fee": 50,
        "min_participants": 20,
        "max_participants": 200,
        "prizes": {
            1: {"rlm": 2000, "badge": "game_master"},
            2: {"rlm": 1000},
            3: {"rlm": 500},
            "top10": {"rlm": 100}
        }
    },
    "politics": {
        "name": "Political Influence",
        "description": "Gain the most political influence",
        "metric": "political_score",
        "duration_hours": 336,  # 2 weeks
        "entry_fee": 200,
        "min_participants": 10,
        "max_participants": 50,
        "prizes": {
            1: {"rlm": 10000, "badge": "political_mastermind"},
            2: {"rlm": 5000},
            3: {"rlm": 2000},
            "top10": {"rlm": 500}
        }
    },
    "guild_war": {
        "name": "Guild Wars",
        "description": "Guild vs Guild competition",
        "metric": "guild_total_score",
        "duration_hours": 168,  # 1 week
        "entry_fee": 500,  # Per guild
        "min_participants": 5,  # Min guilds
        "max_participants": 20,  # Max guilds
        "prizes": {
            1: {"rlm": 25000, "badge": "war_victors"},  # Split among guild
            2: {"rlm": 15000},
            3: {"rlm": 7500}
        },
        "is_guild_tournament": True
    },
    "referral_race": {
        "name": "Referral Race",
        "description": "Bring the most new players",
        "metric": "referral_count",
        "duration_hours": 336,  # 2 weeks
        "entry_fee": 0,
        "min_participants": 10,
        "max_participants": 1000,
        "prizes": {
            1: {"rlm": 5000, "badge": "top_recruiter"},
            2: {"rlm": 2500},
            3: {"rlm": 1000},
            "top10": {"rlm": 200}
        }
    }
}


# ============== MODELS ==============

class CreateTournament(BaseModel):
    tournament_type: str
    name: Optional[str] = None
    start_time: Optional[str] = None  # ISO format, default: now


# ============== ENDPOINTS ==============

@router.get("/types")
async def get_tournament_types():
    """Get all tournament types"""
    return {"tournament_types": TOURNAMENT_TYPES}


@router.get("/active")
async def get_active_tournaments():
    """Get currently active tournaments"""
    now = datetime.now(timezone.utc)
    
    tournaments = await db.tournaments.find({
        "status": {"$in": ["open", "active"]},
        "end_time": {"$gt": now.isoformat()}
    }, {"_id": 0}).sort("end_time", 1).to_list(20)
    
    # Add participant count
    for t in tournaments:
        t["participant_count"] = await db.tournament_participants.count_documents({
            "tournament_id": t["id"]
        })
    
    return {"tournaments": tournaments}


@router.get("/upcoming")
async def get_upcoming_tournaments():
    """Get upcoming tournaments"""
    now = datetime.now(timezone.utc)
    
    tournaments = await db.tournaments.find({
        "status": "scheduled",
        "start_time": {"$gt": now.isoformat()}
    }, {"_id": 0}).sort("start_time", 1).to_list(10)
    
    return {"tournaments": tournaments}


@router.get("/past")
async def get_past_tournaments(limit: int = 10):
    """Get completed tournaments"""
    tournaments = await db.tournaments.find({
        "status": "completed"
    }, {"_id": 0}).sort("end_time", -1).limit(limit).to_list(limit)
    
    return {"tournaments": tournaments}


@router.get("/{tournament_id}")
async def get_tournament_details(tournament_id: str):
    """Get tournament details and leaderboard"""
    tournament = await db.tournaments.find_one({"id": tournament_id}, {"_id": 0})
    
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    
    # Get leaderboard
    participants = await db.tournament_participants.find({
        "tournament_id": tournament_id
    }, {"_id": 0}).sort("score", -1).limit(50).to_list(50)
    
    leaderboard = []
    for i, p in enumerate(participants, 1):
        user = await db.users.find_one({"id": p["user_id"]}, {"_id": 0, "username": 1})
        leaderboard.append({
            "rank": i,
            "user_id": p["user_id"],
            "username": user["username"] if user else "Unknown",
            "score": p["score"],
            "joined_at": p["joined_at"]
        })
    
    return {
        "tournament": tournament,
        "leaderboard": leaderboard,
        "total_participants": len(participants)
    }


@router.post("/{tournament_id}/join")
async def join_tournament(
    tournament_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Join a tournament"""
    user_id = current_user["id"]
    
    tournament = await db.tournaments.find_one({"id": tournament_id})
    
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    
    if tournament["status"] not in ["open", "active"]:
        raise HTTPException(status_code=400, detail="Tournament not accepting participants")
    
    # Check if already joined
    existing = await db.tournament_participants.find_one({
        "tournament_id": tournament_id,
        "user_id": user_id
    })
    
    if existing:
        raise HTTPException(status_code=400, detail="Already joined this tournament")
    
    # Check participant limit
    participant_count = await db.tournament_participants.count_documents({
        "tournament_id": tournament_id
    })
    
    if participant_count >= tournament.get("max_participants", 100):
        raise HTTPException(status_code=400, detail="Tournament is full")
    
    # Check entry fee
    entry_fee = tournament.get("entry_fee", 0)
    if entry_fee > 0:
        if current_user.get("realum_balance", 0) < entry_fee:
            raise HTTPException(status_code=400, detail=f"Insufficient balance. Entry fee: {entry_fee} RLM")
        
        # Deduct entry fee
        await db.users.update_one(
            {"id": user_id},
            {"$inc": {"realum_balance": -entry_fee}}
        )
        
        # Add to prize pool
        await db.tournaments.update_one(
            {"id": tournament_id},
            {"$inc": {"prize_pool": entry_fee}}
        )
    
    # Join tournament
    participant = {
        "id": str(uuid.uuid4()),
        "tournament_id": tournament_id,
        "user_id": user_id,
        "score": 0,
        "starting_snapshot": {},  # Store initial values for comparison
        "joined_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Take snapshot based on tournament type
    t_type = tournament.get("tournament_type")
    if t_type == "stock_trading":
        portfolio = await db.stock_holdings.find({"user_id": user_id}, {"_id": 0}).to_list(100)
        participant["starting_snapshot"] = {
            "portfolio_value": sum(h.get("current_value", 0) for h in portfolio),
            "balance": current_user.get("realum_balance", 0)
        }
    elif t_type == "daily_streak":
        daily = await db.daily_rewards.find_one({"user_id": user_id})
        participant["starting_snapshot"] = {"streak": daily.get("streak", 0) if daily else 0}
    
    await db.tournament_participants.insert_one(participant)
    
    return {
        "message": f"Joined tournament: {tournament['name']}",
        "entry_fee_paid": entry_fee
    }


@router.post("/{tournament_id}/update-score")
async def update_tournament_score(
    tournament_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Update participant's score (call periodically)"""
    user_id = current_user["id"]
    
    tournament = await db.tournaments.find_one({"id": tournament_id})
    if not tournament or tournament["status"] != "active":
        raise HTTPException(status_code=400, detail="Tournament not active")
    
    participant = await db.tournament_participants.find_one({
        "tournament_id": tournament_id,
        "user_id": user_id
    })
    
    if not participant:
        raise HTTPException(status_code=400, detail="Not a participant")
    
    # Calculate score based on tournament type
    t_type = tournament.get("tournament_type")
    score = 0
    
    if t_type == "stock_trading":
        portfolio = await db.stock_holdings.find({"user_id": user_id}, {"_id": 0}).to_list(100)
        current_value = sum(h.get("current_value", 0) for h in portfolio) + current_user.get("realum_balance", 0)
        starting_value = participant["starting_snapshot"].get("portfolio_value", 0) + participant["starting_snapshot"].get("balance", 0)
        if starting_value > 0:
            score = ((current_value - starting_value) / starting_value) * 100  # Percent gain
    
    elif t_type == "daily_streak":
        daily = await db.daily_rewards.find_one({"user_id": user_id})
        current_streak = daily.get("streak", 0) if daily else 0
        starting_streak = participant["starting_snapshot"].get("streak", 0)
        score = current_streak - starting_streak
    
    elif t_type == "mini_games":
        # Sum of game scores during tournament period
        games = await db.game_results.find({
            "user_id": user_id,
            "played_at": {"$gte": participant["joined_at"]}
        }).to_list(1000)
        score = sum(g.get("score", 0) for g in games)
    
    elif t_type == "referral_race":
        referrals = await db.referrals.count_documents({
            "referrer_id": user_id,
            "created_at": {"$gte": participant["joined_at"]}
        })
        score = referrals
    
    # Update score
    await db.tournament_participants.update_one(
        {"tournament_id": tournament_id, "user_id": user_id},
        {"$set": {"score": round(score, 2), "last_updated": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Get current rank
    higher_count = await db.tournament_participants.count_documents({
        "tournament_id": tournament_id,
        "score": {"$gt": score}
    })
    
    return {
        "score": round(score, 2),
        "rank": higher_count + 1
    }


@router.get("/my-tournaments")
async def get_my_tournaments(current_user: dict = Depends(get_current_user)):
    """Get tournaments user is participating in"""
    user_id = current_user["id"]
    
    participations = await db.tournament_participants.find({
        "user_id": user_id
    }, {"_id": 0}).sort("joined_at", -1).to_list(50)
    
    my_tournaments = []
    for p in participations:
        tournament = await db.tournaments.find_one({"id": p["tournament_id"]}, {"_id": 0})
        if tournament:
            # Get rank
            higher_count = await db.tournament_participants.count_documents({
                "tournament_id": p["tournament_id"],
                "score": {"$gt": p["score"]}
            })
            
            my_tournaments.append({
                "tournament": tournament,
                "my_score": p["score"],
                "my_rank": higher_count + 1,
                "joined_at": p["joined_at"]
            })
    
    return {"my_tournaments": my_tournaments}


@router.post("/create")
async def create_tournament(
    data: CreateTournament,
    current_user: dict = Depends(get_current_user)
):
    """Create a new tournament (admin or auto-system)"""
    
    if data.tournament_type not in TOURNAMENT_TYPES:
        raise HTTPException(status_code=400, detail="Invalid tournament type")
    
    t_config = TOURNAMENT_TYPES[data.tournament_type]
    
    now = datetime.now(timezone.utc)
    start_time = now
    if data.start_time:
        start_time = datetime.fromisoformat(data.start_time.replace('Z', '+00:00'))
    
    end_time = start_time + timedelta(hours=t_config["duration_hours"])
    
    tournament = {
        "id": str(uuid.uuid4()),
        "tournament_type": data.tournament_type,
        "name": data.name or t_config["name"],
        "description": t_config["description"],
        "metric": t_config["metric"],
        "status": "open" if start_time <= now else "scheduled",
        "entry_fee": t_config["entry_fee"],
        "min_participants": t_config["min_participants"],
        "max_participants": t_config["max_participants"],
        "prizes": t_config["prizes"],
        "prize_pool": 0,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "created_by": current_user["id"],
        "created_at": now.isoformat()
    }
    
    await db.tournaments.insert_one(tournament)
    
    return {"message": "Tournament created", "tournament": tournament}


@router.get("/leaderboard/global")
async def get_global_leaderboard():
    """Get global tournament leaderboard (all-time wins)"""
    
    pipeline = [
        {"$match": {"rank": {"$lte": 3}}},
        {"$group": {
            "_id": "$user_id",
            "wins": {"$sum": {"$cond": [{"$eq": ["$rank", 1]}, 1, 0]}},
            "top3": {"$sum": 1},
            "total_earnings": {"$sum": "$prize_earned"}
        }},
        {"$sort": {"wins": -1, "top3": -1}},
        {"$limit": 20}
    ]
    
    results = await db.tournament_results.aggregate(pipeline).to_list(20)
    
    leaderboard = []
    for i, r in enumerate(results, 1):
        user = await db.users.find_one({"id": r["_id"]}, {"_id": 0, "username": 1})
        leaderboard.append({
            "rank": i,
            "username": user["username"] if user else "Unknown",
            "tournament_wins": r["wins"],
            "top3_finishes": r["top3"],
            "total_earnings": r["total_earnings"]
        })
    
    return {"leaderboard": leaderboard}
