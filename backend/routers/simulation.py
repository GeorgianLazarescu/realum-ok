from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
import uuid
import bcrypt

from ..core.database import db
from ..core.config import INITIAL_BALANCE, TOKEN_BURN_RATE
from ..services.token_service import burn_tokens, create_transaction

router = APIRouter(prefix="/simulation", tags=["Simulation"])

SIMULATION_USERS = {
    "andreea": {"email": "andreea@realum.io", "role": "creator", "username": "Andreea"},
    "vlad": {"email": "vlad@realum.io", "role": "contributor", "username": "Vlad"},
    "sorin": {"email": "sorin@realum.io", "role": "evaluator", "username": "Sorin"}
}

@router.get("/status")
async def get_simulation_status():
    users = {}
    for name, data in SIMULATION_USERS.items():
        user = await db.users.find_one({"email": data["email"]}, {"_id": 0, "password": 0})
        if user:
            users[name] = {
                "id": user["id"],
                "balance": user["realum_balance"],
                "xp": user.get("xp", 0),
                "role": user["role"]
            }
    
    if not users:
        return {"status": "not_initialized", "users": {}}
    
    # Check for marketplace item
    item = await db.marketplace.find_one({"title": "UI Design Kit"}, {"_id": 0})
    
    return {
        "status": "ready",
        "users": users,
        "marketplace_item": item
    }

@router.post("/setup")
async def setup_simulation():
    """Create simulation users and marketplace item"""
    now = datetime.now(timezone.utc).isoformat()
    
    created_users = {}
    for name, data in SIMULATION_USERS.items():
        # Delete existing user
        await db.users.delete_one({"email": data["email"]})
        
        password = f"{data['username']}123!"
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        
        user = {
            "id": str(uuid.uuid4()),
            "email": data["email"],
            "username": data["username"],
            "password": hashed,
            "role": data["role"],
            "realum_balance": INITIAL_BALANCE,
            "wallet_address": None,
            "xp": 0,
            "level": 1,
            "badges": [],
            "skills": [],
            "courses_completed": [],
            "projects_joined": [],
            "created_at": now
        }
        
        await db.users.insert_one(user)
        created_users[name] = {"id": user["id"], "balance": INITIAL_BALANCE}
    
    # Create marketplace item for Andreea
    await db.marketplace.delete_one({"title": "UI Design Kit"})
    item = {
        "id": str(uuid.uuid4()),
        "title": "UI Design Kit",
        "description": "Professional UI components for metaverse applications",
        "category": "design",
        "price_rlm": 100,
        "seller_id": created_users["andreea"]["id"],
        "seller_name": "Andreea",
        "downloads": 0,
        "rating": 0.0,
        "created_at": now
    }
    await db.marketplace.insert_one(item)
    
    return {
        "status": "setup_complete",
        "users": created_users,
        "item_id": item["id"]
    }

@router.post("/step/{step_num}")
async def run_simulation_step(step_num: int):
    """Run a simulation step"""
    if step_num not in [1, 2, 3]:
        raise HTTPException(status_code=400, detail="Invalid step number (1-3)")
    
    # Get users
    andreea = await db.users.find_one({"email": "andreea@realum.io"})
    vlad = await db.users.find_one({"email": "vlad@realum.io"})
    sorin = await db.users.find_one({"email": "sorin@realum.io"})
    
    if not all([andreea, vlad, sorin]):
        raise HTTPException(status_code=400, detail="Simulation not initialized")
    
    result = {"step": step_num}
    
    if step_num == 1:
        # Vlad purchases Andreea's UI Design Kit
        item = await db.marketplace.find_one({"title": "UI Design Kit"})
        if not item:
            raise HTTPException(status_code=404, detail="Marketplace item not found")
        
        price = item["price_rlm"]
        burn = price * TOKEN_BURN_RATE
        net = price - burn
        
        await db.users.update_one({"id": vlad["id"]}, {"$inc": {"realum_balance": -price}})
        await db.users.update_one({"id": andreea["id"]}, {"$inc": {"realum_balance": net}})
        
        await burn_tokens(burn, "Simulation: Vlad purchased Andreea's design")
        await create_transaction(vlad["id"], "debit", price, "Purchased UI Design Kit", burn)
        await create_transaction(andreea["id"], "credit", net, "Sold UI Design Kit")
        
        result.update({
            "action": "Vlad purchased Andreea's UI Design Kit",
            "amount": price,
            "burned": burn,
            "vlad_balance": vlad["realum_balance"] - price,
            "andreea_balance": andreea["realum_balance"] + net
        })
    
    elif step_num == 2:
        # Vlad completes a design task
        task_reward = 50
        xp_reward = 100
        
        await db.users.update_one(
            {"id": vlad["id"]},
            {"$inc": {"realum_balance": task_reward, "xp": xp_reward}}
        )
        await create_transaction(vlad["id"], "credit", task_reward, "Task completed: UI Implementation")
        
        result.update({
            "action": "Vlad completed a design task",
            "reward": task_reward,
            "xp": xp_reward,
            "vlad_balance": vlad["realum_balance"] + task_reward
        })
    
    elif step_num == 3:
        # Sorin validates Vlad's work
        validation_reward = 25
        xp_reward = 50
        
        await db.users.update_one(
            {"id": sorin["id"]},
            {"$inc": {"realum_balance": validation_reward, "xp": xp_reward}}
        )
        await create_transaction(sorin["id"], "credit", validation_reward, "Validated Vlad's contribution")
        
        result.update({
            "action": "Sorin validated Vlad's work",
            "reward": validation_reward,
            "xp": xp_reward,
            "sorin_balance": sorin["realum_balance"] + validation_reward
        })
    
    return result
