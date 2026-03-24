"""
REALUM Tutorial & Onboarding System
Interactive tutorial for new users
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone
import uuid

router = APIRouter(prefix="/api/tutorial", tags=["Tutorial & Onboarding"])

from core.database import db
from core.auth import get_current_user


# ============== TUTORIAL STEPS ==============

TUTORIAL_STEPS = [
    {
        "id": "welcome",
        "order": 1,
        "title": "Bun venit în REALUM!",
        "description": "Descoperă lumea virtuală unde poți trăi o a doua viață.",
        "type": "intro",
        "npc": "Luna",
        "npc_message": "Salut! Eu sunt Luna, ghidul tău în REALUM. Hai să începem aventura!",
        "reward_rlm": 100,
        "reward_xp": 50,
        "action": None
    },
    {
        "id": "profile_setup",
        "order": 2,
        "title": "Configurează-ți Profilul",
        "description": "Personalizează-ți avatarul și completează profilul.",
        "type": "action",
        "npc": "Luna",
        "npc_message": "Un profil complet te ajută să faci conexiuni. Hai să-l configurăm!",
        "reward_rlm": 50,
        "reward_xp": 25,
        "action": {"type": "navigate", "target": "/profile/edit"}
    },
    {
        "id": "explore_dashboard",
        "order": 3,
        "title": "Explorează Dashboard-ul",
        "description": "Descoperă toate funcționalitățile disponibile.",
        "type": "tour",
        "npc": "Luna",
        "npc_message": "Dashboard-ul este centrul de comandă. De aici poți accesa totul!",
        "reward_rlm": 25,
        "reward_xp": 25,
        "action": {"type": "navigate", "target": "/dashboard"},
        "highlights": ["quick-actions", "stats-overview", "notifications"]
    },
    {
        "id": "claim_daily",
        "order": 4,
        "title": "Revendică Recompensa Zilnică",
        "description": "Învață să colectezi recompense zilnice pentru streak-uri.",
        "type": "action",
        "npc": "Vault",
        "npc_message": "Loghează-te zilnic pentru bonusuri din ce în ce mai mari!",
        "reward_rlm": 50,
        "reward_xp": 30,
        "action": {"type": "api_call", "endpoint": "/api/daily/claim"}
    },
    {
        "id": "visit_bank",
        "order": 5,
        "title": "Vizitează Banca",
        "description": "Deschide un cont de economii și câștigă dobândă.",
        "type": "action",
        "npc": "Vault",
        "npc_message": "Banca REALUM oferă conturi de economii cu dobândă competitivă!",
        "reward_rlm": 75,
        "reward_xp": 40,
        "action": {"type": "navigate", "target": "/bank"}
    },
    {
        "id": "explore_stocks",
        "order": 6,
        "title": "Descoperă Bursa",
        "description": "Învață bazele investițiilor pe bursa virtuală.",
        "type": "action",
        "npc": "Max",
        "npc_message": "Bursa REALUM are 8 companii în care poți investi. Hai să vedem!",
        "reward_rlm": 100,
        "reward_xp": 50,
        "action": {"type": "navigate", "target": "/stocks"}
    },
    {
        "id": "first_investment",
        "order": 7,
        "title": "Prima Ta Investiție",
        "description": "Cumpără prima ta acțiune pe bursă.",
        "type": "challenge",
        "npc": "Max",
        "npc_message": "E timpul să faci prima investiție! Ți-am dat 200 RLM bonus pentru asta.",
        "reward_rlm": 200,
        "reward_xp": 100,
        "action": {"type": "task", "task": "buy_stock", "target": 1},
        "bonus_rlm": 200
    },
    {
        "id": "join_chat",
        "order": 8,
        "title": "Conectează-te cu Comunitatea",
        "description": "Trimite primul tău mesaj în chat-ul global.",
        "type": "action",
        "npc": "Luna",
        "npc_message": "REALUM e despre comunitate. Salută-i pe ceilalți!",
        "reward_rlm": 50,
        "reward_xp": 30,
        "action": {"type": "navigate", "target": "/chat"}
    },
    {
        "id": "explore_politics",
        "order": 9,
        "title": "Sistemul Politic",
        "description": "Descoperă cum funcționează democrația în REALUM.",
        "type": "info",
        "npc": "Aria",
        "npc_message": "În REALUM, jucătorii decid legile și aleg liderii. Votul tău contează!",
        "reward_rlm": 50,
        "reward_xp": 40,
        "action": {"type": "navigate", "target": "/politics"}
    },
    {
        "id": "play_minigame",
        "order": 10,
        "title": "Joacă un Mini-Joc",
        "description": "Testează-ți norocul și câștigă RLM.",
        "type": "action",
        "npc": "Luna",
        "npc_message": "Mini-jocurile sunt o modalitate distractivă de a câștiga RLM!",
        "reward_rlm": 75,
        "reward_xp": 35,
        "action": {"type": "navigate", "target": "/games"}
    },
    {
        "id": "battle_pass",
        "order": 11,
        "title": "Descoperă Battle Pass",
        "description": "Progresează și deblochează recompense exclusive.",
        "type": "info",
        "npc": "Luna",
        "npc_message": "Battle Pass-ul îți oferă recompense pentru fiecare activitate!",
        "reward_rlm": 100,
        "reward_xp": 50,
        "action": {"type": "navigate", "target": "/battlepass"}
    },
    {
        "id": "tutorial_complete",
        "order": 12,
        "title": "Felicitări!",
        "description": "Ai completat tutorialul! Acum ești pregătit pentru aventură.",
        "type": "completion",
        "npc": "Luna",
        "npc_message": "Excelent! Ai învățat bazele REALUM. Acum lumea e a ta! 🎉",
        "reward_rlm": 500,
        "reward_xp": 250,
        "action": None,
        "badge": "tutorial_complete"
    }
]

TOTAL_TUTORIAL_RLM = sum(step.get("reward_rlm", 0) + step.get("bonus_rlm", 0) for step in TUTORIAL_STEPS)
TOTAL_TUTORIAL_XP = sum(step.get("reward_xp", 0) for step in TUTORIAL_STEPS)


# ============== ENDPOINTS ==============

@router.get("/steps")
async def get_tutorial_steps():
    """Get all tutorial steps"""
    return {
        "steps": TUTORIAL_STEPS,
        "total_steps": len(TUTORIAL_STEPS),
        "total_rewards": {
            "rlm": TOTAL_TUTORIAL_RLM,
            "xp": TOTAL_TUTORIAL_XP
        }
    }


@router.get("/progress")
async def get_tutorial_progress(current_user: dict = Depends(get_current_user)):
    """Get user's tutorial progress"""
    user_id = current_user["id"]
    
    progress = await db.tutorial_progress.find_one({"user_id": user_id})
    
    if not progress:
        progress = {
            "user_id": user_id,
            "completed_steps": [],
            "current_step": 1,
            "is_completed": False,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "total_rlm_earned": 0,
            "total_xp_earned": 0
        }
        await db.tutorial_progress.insert_one(progress)
    
    # Get current step details
    current_step_data = None
    for step in TUTORIAL_STEPS:
        if step["order"] == progress.get("current_step", 1):
            current_step_data = step
            break
    
    return {
        "current_step": progress.get("current_step", 1),
        "current_step_data": current_step_data,
        "completed_steps": progress.get("completed_steps", []),
        "is_completed": progress.get("is_completed", False),
        "total_steps": len(TUTORIAL_STEPS),
        "progress_percentage": round(len(progress.get("completed_steps", [])) / len(TUTORIAL_STEPS) * 100, 1),
        "total_rlm_earned": progress.get("total_rlm_earned", 0),
        "total_xp_earned": progress.get("total_xp_earned", 0)
    }


@router.post("/complete-step/{step_id}")
async def complete_tutorial_step(
    step_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Complete a tutorial step and claim rewards"""
    user_id = current_user["id"]
    
    # Find step
    step = None
    for s in TUTORIAL_STEPS:
        if s["id"] == step_id:
            step = s
            break
    
    if not step:
        raise HTTPException(status_code=404, detail="Tutorial step not found")
    
    # Get progress
    progress = await db.tutorial_progress.find_one({"user_id": user_id})
    
    if not progress:
        progress = {
            "user_id": user_id,
            "completed_steps": [],
            "current_step": 1,
            "is_completed": False,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "total_rlm_earned": 0,
            "total_xp_earned": 0
        }
    
    # Check if already completed
    if step_id in progress.get("completed_steps", []):
        raise HTTPException(status_code=400, detail="Step already completed")
    
    # Check if it's the current step (or allow skipping for testing)
    if step["order"] > progress.get("current_step", 1) + 1:
        raise HTTPException(status_code=400, detail="Complete previous steps first")
    
    # Calculate rewards
    rlm_reward = step.get("reward_rlm", 0) + step.get("bonus_rlm", 0)
    xp_reward = step.get("reward_xp", 0)
    
    # Update user balance and XP
    await db.users.update_one(
        {"id": user_id},
        {"$inc": {"realum_balance": rlm_reward, "xp": xp_reward}}
    )
    
    # Award badge if applicable
    badge_awarded = None
    if step.get("badge"):
        badge_awarded = step["badge"]
        await db.user_badges.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "badge_key": step["badge"],
            "awarded_at": datetime.now(timezone.utc).isoformat()
        })
    
    # Update progress
    completed_steps = progress.get("completed_steps", [])
    completed_steps.append(step_id)
    
    next_step = step["order"] + 1
    is_completed = next_step > len(TUTORIAL_STEPS)
    
    await db.tutorial_progress.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "completed_steps": completed_steps,
                "current_step": next_step if not is_completed else len(TUTORIAL_STEPS),
                "is_completed": is_completed,
                "completed_at": datetime.now(timezone.utc).isoformat() if is_completed else None
            },
            "$inc": {
                "total_rlm_earned": rlm_reward,
                "total_xp_earned": xp_reward
            }
        },
        upsert=True
    )
    
    # Get next step data
    next_step_data = None
    if not is_completed:
        for s in TUTORIAL_STEPS:
            if s["order"] == next_step:
                next_step_data = s
                break
    
    return {
        "message": f"Step '{step['title']}' completed!",
        "rewards": {
            "rlm": rlm_reward,
            "xp": xp_reward,
            "badge": badge_awarded
        },
        "next_step": next_step_data,
        "is_tutorial_complete": is_completed,
        "progress_percentage": round(len(completed_steps) / len(TUTORIAL_STEPS) * 100, 1)
    }


@router.post("/skip")
async def skip_tutorial(current_user: dict = Depends(get_current_user)):
    """Skip the tutorial entirely"""
    user_id = current_user["id"]
    
    await db.tutorial_progress.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "is_skipped": True,
                "skipped_at": datetime.now(timezone.utc).isoformat()
            }
        },
        upsert=True
    )
    
    return {"message": "Tutorial skipped", "note": "You can restart it anytime from settings"}


@router.post("/restart")
async def restart_tutorial(current_user: dict = Depends(get_current_user)):
    """Restart the tutorial (won't give rewards again)"""
    user_id = current_user["id"]
    
    await db.tutorial_progress.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "current_step": 1,
                "is_completed": False,
                "is_skipped": False,
                "restarted_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {"message": "Tutorial restarted", "note": "Rewards won't be given for already completed steps"}


@router.get("/npcs")
async def get_tutorial_npcs():
    """Get NPC information for tutorial"""
    return {
        "npcs": [
            {
                "id": "luna",
                "name": "Luna",
                "role": "Guide",
                "avatar": "👩‍🎤",
                "description": "Your friendly guide through REALUM"
            },
            {
                "id": "vault",
                "name": "Vault",
                "role": "Banker",
                "avatar": "🏦",
                "description": "Expert in finance and banking"
            },
            {
                "id": "max",
                "name": "Max",
                "role": "Trader",
                "avatar": "📈",
                "description": "Stock market specialist"
            },
            {
                "id": "aria",
                "name": "Aria",
                "role": "Mentor",
                "avatar": "👩‍🏫",
                "description": "Politics and governance expert"
            }
        ]
    }
