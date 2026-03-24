"""
REALUM Games & Daily Missions System
Mini-games, quizzes, daily/weekly missions with rewards
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import uuid
import random

router = APIRouter(prefix="/api/games", tags=["Games & Missions"])

from core.database import db
from core.auth import get_current_user
from core.utils import serialize_doc


# ============== CONSTANTS ==============

# Mini-games available
MINI_GAMES = {
    "daily_quiz": {
        "name": "Quiz Zilnic",
        "description": "Răspunde la întrebări și câștigă RLM",
        "reward_range": (5, 25),
        "cooldown_hours": 24,
        "xp_reward": 50
    },
    "lucky_spin": {
        "name": "Roata Norocului",
        "description": "Învârte roata pentru premii!",
        "cost": 10,
        "prizes": [
            {"type": "rlm", "value": 5, "weight": 30},
            {"type": "rlm", "value": 20, "weight": 25},
            {"type": "rlm", "value": 50, "weight": 15},
            {"type": "rlm", "value": 100, "weight": 8},
            {"type": "rlm", "value": 500, "weight": 2},
            {"type": "xp", "value": 100, "weight": 10},
            {"type": "nothing", "value": 0, "weight": 10}
        ]
    },
    "number_guess": {
        "name": "Ghicește Numărul",
        "description": "Ghicește un număr între 1-10",
        "cost": 5,
        "reward": 25,
        "xp_reward": 20
    },
    "coin_flip": {
        "name": "Cap sau Pajură",
        "description": "50/50 să-ți dublezi miza",
        "min_bet": 10,
        "max_bet": 1000
    }
}

# Quiz questions (can be expanded)
QUIZ_QUESTIONS = [
    {"question": "Care este moneda oficială REALUM?", "options": ["RLM", "BTC", "ETH", "USD"], "correct": 0},
    {"question": "Câte zone are REALUM?", "options": ["4", "5", "6", "7"], "correct": 2},
    {"question": "Ce poți face în banca REALUM?", "options": ["Doar depozite", "Doar împrumuturi", "Ambele", "Nimic"], "correct": 2},
    {"question": "Cum se numește sistemul politic din REALUM?", "options": ["Monarhie", "Democrație", "Dictatură", "Anarhie"], "correct": 1},
    {"question": "Ce tip de economie are REALUM?", "options": ["Socialistă", "Capitalistă", "Mixtă", "Virtuală"], "correct": 3},
    {"question": "Care este zona cu cel mai mare multiplicator de preț?", "options": ["Learning Zone", "Jobs Hub", "Treasury", "DAO Hall"], "correct": 2},
    {"question": "Ce poți cumpăra în Marketplace?", "options": ["Doar haine", "Doar mâncare", "Items virtuale", "Mașini reale"], "correct": 2},
    {"question": "Cum poți deveni politician în REALUM?", "options": ["Plătești bani", "Candidezi la alegeri", "Te naști așa", "Nu poți"], "correct": 1},
]

# Mission types
MISSION_TYPES = {
    "daily": {
        "login": {"name": "Conectare Zilnică", "reward": 10, "xp": 25},
        "transaction": {"name": "Fă o Tranzacție", "reward": 15, "xp": 30},
        "vote": {"name": "Votează într-o Alegere", "reward": 20, "xp": 50},
        "chat": {"name": "Vorbește cu un NPC", "reward": 10, "xp": 20},
        "play_game": {"name": "Joacă un Mini-joc", "reward": 15, "xp": 35}
    },
    "weekly": {
        "buy_stock": {"name": "Cumpără Acțiuni", "reward": 100, "xp": 200},
        "rent_property": {"name": "Închiriază o Proprietate", "reward": 150, "xp": 300},
        "win_election": {"name": "Câștigă o Alegere", "reward": 500, "xp": 1000},
        "earn_1000": {"name": "Câștigă 1000 RLM", "reward": 200, "xp": 400},
        "make_10_trades": {"name": "Fă 10 Tranzacții pe Bursă", "reward": 250, "xp": 500}
    }
}


# ============== MODELS ==============

class QuizAnswer(BaseModel):
    question_index: int
    answer_index: int

class NumberGuess(BaseModel):
    guess: int = Field(..., ge=1, le=10)

class CoinFlipBet(BaseModel):
    choice: str  # "heads" or "tails"
    amount: float = Field(..., ge=10, le=1000)


# ============== HELPER FUNCTIONS ==============

async def check_game_cooldown(user_id: str, game_id: str, hours: int) -> bool:
    """Check if user can play a game (cooldown passed)"""
    last_play = await db.game_plays.find_one({
        "user_id": user_id,
        "game_id": game_id
    }, sort=[("played_at", -1)])
    
    if not last_play:
        return True
    
    last_time = datetime.fromisoformat(last_play["played_at"].replace("Z", "+00:00"))
    cooldown_end = last_time + timedelta(hours=hours)
    
    return datetime.now(timezone.utc) > cooldown_end

async def record_game_play(user_id: str, game_id: str, result: dict):
    """Record a game play"""
    await db.game_plays.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "game_id": game_id,
        "result": result,
        "played_at": datetime.now(timezone.utc).isoformat()
    })

async def give_reward(user_id: str, rlm: float = 0, xp: int = 0):
    """Give rewards to user"""
    updates = {}
    if rlm > 0:
        updates["realum_balance"] = rlm
    if xp > 0:
        updates["xp"] = xp
    
    if updates:
        await db.users.update_one(
            {"id": user_id},
            {"$inc": updates}
        )


# ============== GAME ENDPOINTS ==============

@router.get("/list")
async def get_games_list():
    """Get available mini-games"""
    return {"games": MINI_GAMES}


@router.get("/status")
async def get_games_status(current_user: dict = Depends(get_current_user)):
    """Get user's game status and cooldowns"""
    status = {}
    
    for game_id, game_info in MINI_GAMES.items():
        cooldown = game_info.get("cooldown_hours", 0)
        can_play = await check_game_cooldown(current_user["id"], game_id, cooldown)
        
        last_play = await db.game_plays.find_one({
            "user_id": current_user["id"],
            "game_id": game_id
        }, sort=[("played_at", -1)])
        
        status[game_id] = {
            "can_play": can_play,
            "last_played": last_play["played_at"] if last_play else None,
            "cooldown_hours": cooldown
        }
    
    return {"status": status}


@router.post("/quiz/start")
async def start_daily_quiz(current_user: dict = Depends(get_current_user)):
    """Start daily quiz"""
    game = MINI_GAMES["daily_quiz"]
    
    if not await check_game_cooldown(current_user["id"], "daily_quiz", game["cooldown_hours"]):
        raise HTTPException(status_code=400, detail="Quiz already completed today. Come back tomorrow!")
    
    # Select 5 random questions
    questions = random.sample(QUIZ_QUESTIONS, min(5, len(QUIZ_QUESTIONS)))
    
    # Store quiz session
    session = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "questions": questions,
        "current_index": 0,
        "correct_count": 0,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "status": "active"
    }
    await db.quiz_sessions.insert_one(session)
    
    return {
        "session_id": session["id"],
        "total_questions": len(questions),
        "current_question": {
            "index": 0,
            "question": questions[0]["question"],
            "options": questions[0]["options"]
        }
    }


@router.post("/quiz/{session_id}/answer")
async def answer_quiz_question(
    session_id: str,
    data: QuizAnswer,
    current_user: dict = Depends(get_current_user)
):
    """Answer a quiz question"""
    session = await db.quiz_sessions.find_one({
        "id": session_id,
        "user_id": current_user["id"],
        "status": "active"
    })
    
    if not session:
        raise HTTPException(status_code=404, detail="Quiz session not found")
    
    questions = session["questions"]
    current_idx = session["current_index"]
    
    if data.question_index != current_idx:
        raise HTTPException(status_code=400, detail="Invalid question index")
    
    # Check answer
    is_correct = questions[current_idx]["correct"] == data.answer_index
    correct_count = session["correct_count"] + (1 if is_correct else 0)
    
    next_idx = current_idx + 1
    is_finished = next_idx >= len(questions)
    
    # Update session
    if is_finished:
        # Calculate rewards
        game = MINI_GAMES["daily_quiz"]
        base_reward = game["reward_range"][0]
        bonus_per_correct = (game["reward_range"][1] - game["reward_range"][0]) / len(questions)
        total_reward = base_reward + int(correct_count * bonus_per_correct)
        xp_reward = game["xp_reward"]
        
        # Give rewards
        await give_reward(current_user["id"], total_reward, xp_reward)
        
        # Record play
        await record_game_play(current_user["id"], "daily_quiz", {
            "correct": correct_count,
            "total": len(questions),
            "reward": total_reward
        })
        
        await db.quiz_sessions.update_one(
            {"id": session_id},
            {"$set": {"status": "completed", "correct_count": correct_count, "reward": total_reward}}
        )
        
        return {
            "is_correct": is_correct,
            "correct_answer": questions[current_idx]["correct"],
            "finished": True,
            "final_score": f"{correct_count}/{len(questions)}",
            "reward": total_reward,
            "xp_earned": xp_reward
        }
    else:
        await db.quiz_sessions.update_one(
            {"id": session_id},
            {"$set": {"current_index": next_idx, "correct_count": correct_count}}
        )
        
        return {
            "is_correct": is_correct,
            "correct_answer": questions[current_idx]["correct"],
            "finished": False,
            "next_question": {
                "index": next_idx,
                "question": questions[next_idx]["question"],
                "options": questions[next_idx]["options"]
            }
        }


@router.post("/lucky-spin")
async def play_lucky_spin(current_user: dict = Depends(get_current_user)):
    """Play lucky spin game"""
    game = MINI_GAMES["lucky_spin"]
    cost = game["cost"]
    
    if current_user.get("realum_balance", 0) < cost:
        raise HTTPException(status_code=400, detail=f"Need {cost} RLM to spin")
    
    # Deduct cost
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$inc": {"realum_balance": -cost}}
    )
    
    # Weighted random selection
    prizes = game["prizes"]
    total_weight = sum(p["weight"] for p in prizes)
    rand = random.uniform(0, total_weight)
    
    cumulative = 0
    won_prize = prizes[-1]
    for prize in prizes:
        cumulative += prize["weight"]
        if rand <= cumulative:
            won_prize = prize
            break
    
    # Give reward
    if won_prize["type"] == "rlm":
        await give_reward(current_user["id"], rlm=won_prize["value"])
    elif won_prize["type"] == "xp":
        await give_reward(current_user["id"], xp=won_prize["value"])
    
    # Record play
    await record_game_play(current_user["id"], "lucky_spin", {
        "prize": won_prize,
        "cost": cost
    })
    
    return {
        "result": won_prize,
        "message": f"Ai câștigat {won_prize['value']} {won_prize['type'].upper()}!" if won_prize["type"] != "nothing" else "Mai mult noroc data viitoare!"
    }


@router.post("/number-guess")
async def play_number_guess(
    data: NumberGuess,
    current_user: dict = Depends(get_current_user)
):
    """Play number guessing game"""
    game = MINI_GAMES["number_guess"]
    cost = game["cost"]
    
    if current_user.get("realum_balance", 0) < cost:
        raise HTTPException(status_code=400, detail=f"Need {cost} RLM to play")
    
    # Deduct cost
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$inc": {"realum_balance": -cost}}
    )
    
    # Generate random number
    secret_number = random.randint(1, 10)
    won = data.guess == secret_number
    
    result = {
        "guess": data.guess,
        "secret_number": secret_number,
        "won": won
    }
    
    if won:
        await give_reward(current_user["id"], rlm=game["reward"], xp=game["xp_reward"])
        result["reward"] = game["reward"]
        result["message"] = f"Corect! Ai câștigat {game['reward']} RLM!"
    else:
        result["message"] = f"Greșit! Numărul era {secret_number}."
    
    await record_game_play(current_user["id"], "number_guess", result)
    
    return result


@router.post("/coin-flip")
async def play_coin_flip(
    data: CoinFlipBet,
    current_user: dict = Depends(get_current_user)
):
    """Play coin flip game"""
    if data.choice not in ["heads", "tails"]:
        raise HTTPException(status_code=400, detail="Choose 'heads' or 'tails'")
    
    if current_user.get("realum_balance", 0) < data.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    # Deduct bet
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$inc": {"realum_balance": -data.amount}}
    )
    
    # Flip coin
    result = random.choice(["heads", "tails"])
    won = data.choice == result
    
    winnings = data.amount * 2 if won else 0
    
    if won:
        await give_reward(current_user["id"], rlm=winnings)
    
    await record_game_play(current_user["id"], "coin_flip", {
        "choice": data.choice,
        "result": result,
        "bet": data.amount,
        "won": won,
        "winnings": winnings
    })
    
    return {
        "choice": data.choice,
        "result": result,
        "won": won,
        "winnings": winnings,
        "message": f"{'Cap' if result == 'heads' else 'Pajură'}! {'Ai câștigat ' + str(winnings) + ' RLM!' if won else 'Ai pierdut.'}"
    }


# ============== MISSIONS ENDPOINTS ==============

@router.get("/missions")
async def get_missions(current_user: dict = Depends(get_current_user)):
    """Get available daily and weekly missions"""
    today = datetime.now(timezone.utc).date().isoformat()
    week_start = (datetime.now(timezone.utc) - timedelta(days=datetime.now(timezone.utc).weekday())).date().isoformat()
    
    # Get user's completed missions
    daily_completed = await db.mission_completions.find({
        "user_id": current_user["id"],
        "mission_type": "daily",
        "completed_date": today
    }, {"_id": 0, "mission_id": 1}).to_list(20)
    daily_completed_ids = [m["mission_id"] for m in daily_completed]
    
    weekly_completed = await db.mission_completions.find({
        "user_id": current_user["id"],
        "mission_type": "weekly",
        "week_start": week_start
    }, {"_id": 0, "mission_id": 1}).to_list(20)
    weekly_completed_ids = [m["mission_id"] for m in weekly_completed]
    
    # Format missions
    daily_missions = []
    for mission_id, info in MISSION_TYPES["daily"].items():
        daily_missions.append({
            "id": mission_id,
            **info,
            "completed": mission_id in daily_completed_ids
        })
    
    weekly_missions = []
    for mission_id, info in MISSION_TYPES["weekly"].items():
        weekly_missions.append({
            "id": mission_id,
            **info,
            "completed": mission_id in weekly_completed_ids
        })
    
    return {
        "daily": daily_missions,
        "weekly": weekly_missions,
        "today": today,
        "week_start": week_start
    }


@router.post("/missions/{mission_id}/complete")
async def complete_mission(
    mission_id: str,
    mission_type: str = "daily",
    current_user: dict = Depends(get_current_user)
):
    """Complete a mission (called internally when conditions are met)"""
    if mission_type not in MISSION_TYPES:
        raise HTTPException(status_code=400, detail="Invalid mission type")
    
    if mission_id not in MISSION_TYPES[mission_type]:
        raise HTTPException(status_code=404, detail="Mission not found")
    
    today = datetime.now(timezone.utc).date().isoformat()
    week_start = (datetime.now(timezone.utc) - timedelta(days=datetime.now(timezone.utc).weekday())).date().isoformat()
    
    # Check if already completed
    query = {
        "user_id": current_user["id"],
        "mission_id": mission_id,
        "mission_type": mission_type
    }
    if mission_type == "daily":
        query["completed_date"] = today
    else:
        query["week_start"] = week_start
    
    existing = await db.mission_completions.find_one(query)
    if existing:
        raise HTTPException(status_code=400, detail="Mission already completed")
    
    mission = MISSION_TYPES[mission_type][mission_id]
    
    # Give rewards
    await give_reward(current_user["id"], rlm=mission["reward"], xp=mission["xp"])
    
    # Record completion
    completion = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "mission_id": mission_id,
        "mission_type": mission_type,
        "reward": mission["reward"],
        "xp": mission["xp"],
        "completed_at": datetime.now(timezone.utc).isoformat()
    }
    if mission_type == "daily":
        completion["completed_date"] = today
    else:
        completion["week_start"] = week_start
    
    await db.mission_completions.insert_one(completion)
    
    return {
        "message": f"Misiune completată! +{mission['reward']} RLM, +{mission['xp']} XP",
        "reward": mission["reward"],
        "xp": mission["xp"]
    }


# ============== LEADERBOARD ==============

@router.get("/leaderboard")
async def get_games_leaderboard(limit: int = 20):
    """Get games leaderboard by total winnings"""
    pipeline = [
        {"$match": {"result.reward": {"$exists": True}}},
        {"$group": {
            "_id": "$user_id",
            "total_plays": {"$sum": 1},
            "total_won": {"$sum": "$result.reward"}
        }},
        {"$sort": {"total_won": -1}},
        {"$limit": limit}
    ]
    
    results = await db.game_plays.aggregate(pipeline).to_list(limit)
    
    leaderboard = []
    for i, r in enumerate(results):
        user = await db.users.find_one({"id": r["_id"]})
        leaderboard.append({
            "rank": i + 1,
            "username": user.get("username", "Unknown") if user else "Unknown",
            "total_plays": r["total_plays"],
            "total_won": r["total_won"]
        })
    
    return {"leaderboard": leaderboard}
