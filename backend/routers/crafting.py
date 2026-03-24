"""
REALUM Crafting System
Create items from resources and recipes
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import uuid
import random

router = APIRouter(prefix="/api/crafting", tags=["Crafting System"])

from core.database import db
from core.auth import get_current_user
from core.utils import serialize_doc


# ============== CONSTANTS ==============

# Resource types
RESOURCES = {
    "metal": {"name": "Metal", "rarity": "common", "base_price": 5},
    "crystal": {"name": "Cristal", "rarity": "uncommon", "base_price": 15},
    "energy": {"name": "Energie", "rarity": "common", "base_price": 3},
    "data_chip": {"name": "Chip de Date", "rarity": "rare", "base_price": 50},
    "quantum_core": {"name": "Nucleu Cuantic", "rarity": "epic", "base_price": 200},
    "void_essence": {"name": "Esență de Vid", "rarity": "legendary", "base_price": 1000}
}

# Crafting recipes
RECIPES = {
    "basic_badge": {
        "name": "Insignă Simplă",
        "category": "cosmetic",
        "description": "O insignă simplă pentru profil",
        "materials": {"metal": 5, "crystal": 2},
        "craft_time_minutes": 5,
        "success_rate": 1.0,
        "result_rarity": "common"
    },
    "premium_badge": {
        "name": "Insignă Premium",
        "category": "cosmetic",
        "description": "O insignă strălucitoare",
        "materials": {"metal": 10, "crystal": 5, "energy": 10},
        "craft_time_minutes": 15,
        "success_rate": 0.9,
        "result_rarity": "uncommon"
    },
    "trading_boost": {
        "name": "Boost Tranzacții",
        "category": "consumable",
        "description": "+10% la câștiguri din tranzacții pentru 1 oră",
        "materials": {"energy": 20, "data_chip": 1},
        "craft_time_minutes": 10,
        "success_rate": 0.95,
        "result_rarity": "uncommon",
        "effect": {"type": "trading_boost", "value": 0.10, "duration_hours": 1}
    },
    "xp_boost": {
        "name": "Boost XP",
        "category": "consumable",
        "description": "+25% XP pentru 2 ore",
        "materials": {"crystal": 10, "energy": 15},
        "craft_time_minutes": 20,
        "success_rate": 0.85,
        "result_rarity": "rare",
        "effect": {"type": "xp_boost", "value": 0.25, "duration_hours": 2}
    },
    "lucky_charm": {
        "name": "Talisman Norocos",
        "category": "consumable",
        "description": "+15% șansă la jocuri pentru 30 minute",
        "materials": {"crystal": 5, "quantum_core": 1},
        "craft_time_minutes": 30,
        "success_rate": 0.75,
        "result_rarity": "epic",
        "effect": {"type": "luck_boost", "value": 0.15, "duration_hours": 0.5}
    },
    "elite_frame": {
        "name": "Ramă de Elită",
        "category": "cosmetic",
        "description": "Ramă legendară pentru avatar",
        "materials": {"quantum_core": 2, "void_essence": 1, "crystal": 20},
        "craft_time_minutes": 60,
        "success_rate": 0.5,
        "result_rarity": "legendary"
    },
    "resource_doubler": {
        "name": "Dublor de Resurse",
        "category": "consumable",
        "description": "Dublează următoarea colectare de resurse",
        "materials": {"data_chip": 3, "energy": 30},
        "craft_time_minutes": 25,
        "success_rate": 0.8,
        "result_rarity": "rare",
        "effect": {"type": "resource_doubler", "uses": 1}
    }
}

# Resource gathering locations
GATHERING_LOCATIONS = {
    "mines": {"resource": "metal", "base_amount": [1, 5], "cooldown_minutes": 30},
    "caves": {"resource": "crystal", "base_amount": [1, 3], "cooldown_minutes": 45},
    "power_plant": {"resource": "energy", "base_amount": [2, 8], "cooldown_minutes": 20},
    "data_center": {"resource": "data_chip", "base_amount": [0, 1], "cooldown_minutes": 120, "chance": 0.3},
    "quantum_lab": {"resource": "quantum_core", "base_amount": [0, 1], "cooldown_minutes": 360, "chance": 0.15},
    "void_rift": {"resource": "void_essence", "base_amount": [0, 1], "cooldown_minutes": 720, "chance": 0.05}
}


# ============== MODELS ==============

class CraftItemRequest(BaseModel):
    recipe_id: str

class GatherResourceRequest(BaseModel):
    location: str


# ============== HELPER FUNCTIONS ==============

async def get_user_resources(user_id: str) -> dict:
    """Get user's resources"""
    resources = await db.user_resources.find_one({"user_id": user_id})
    if not resources:
        resources = {
            "user_id": user_id,
            "metal": 0,
            "crystal": 0,
            "energy": 0,
            "data_chip": 0,
            "quantum_core": 0,
            "void_essence": 0
        }
        await db.user_resources.insert_one(resources)
    return resources

async def add_resource(user_id: str, resource: str, amount: int):
    """Add resource to user"""
    await db.user_resources.update_one(
        {"user_id": user_id},
        {"$inc": {resource: amount}},
        upsert=True
    )

async def remove_resource(user_id: str, resource: str, amount: int):
    """Remove resource from user"""
    await db.user_resources.update_one(
        {"user_id": user_id},
        {"$inc": {resource: -amount}}
    )


# ============== ENDPOINTS ==============

@router.get("/resources")
async def get_resources(current_user: dict = Depends(get_current_user)):
    """Get user's resources"""
    resources = await get_user_resources(current_user["id"])
    
    # Get gathering cooldowns
    cooldowns = {}
    for location in GATHERING_LOCATIONS.keys():
        last_gather = await db.resource_gathering.find_one({
            "user_id": current_user["id"],
            "location": location
        }, sort=[("gathered_at", -1)])
        
        if last_gather:
            cooldown_mins = GATHERING_LOCATIONS[location]["cooldown_minutes"]
            cooldown_end = datetime.fromisoformat(last_gather["gathered_at"].replace("Z", "+00:00")) + timedelta(minutes=cooldown_mins)
            if cooldown_end > datetime.now(timezone.utc):
                cooldowns[location] = cooldown_end.isoformat()
    
    return {
        "resources": {k: v for k, v in resources.items() if k != "_id" and k != "user_id"},
        "resource_info": RESOURCES,
        "cooldowns": cooldowns
    }


@router.get("/recipes")
async def get_recipes():
    """Get all crafting recipes"""
    return {
        "recipes": RECIPES,
        "resource_info": RESOURCES
    }


@router.get("/locations")
async def get_gathering_locations():
    """Get resource gathering locations"""
    return {
        "locations": GATHERING_LOCATIONS,
        "resource_info": RESOURCES
    }


@router.post("/gather")
async def gather_resource(
    data: GatherResourceRequest,
    current_user: dict = Depends(get_current_user)
):
    """Gather resources from a location"""
    if data.location not in GATHERING_LOCATIONS:
        raise HTTPException(status_code=404, detail="Location not found")
    
    location = GATHERING_LOCATIONS[data.location]
    
    # Check cooldown
    last_gather = await db.resource_gathering.find_one({
        "user_id": current_user["id"],
        "location": data.location
    }, sort=[("gathered_at", -1)])
    
    if last_gather:
        cooldown_end = datetime.fromisoformat(last_gather["gathered_at"].replace("Z", "+00:00")) + timedelta(minutes=location["cooldown_minutes"])
        if cooldown_end > datetime.now(timezone.utc):
            remaining = (cooldown_end - datetime.now(timezone.utc)).total_seconds() / 60
            raise HTTPException(status_code=400, detail=f"Location on cooldown. Wait {int(remaining)} minutes.")
    
    # Calculate gathered amount
    chance = location.get("chance", 1.0)
    if random.random() > chance:
        amount = 0
    else:
        amount = random.randint(location["base_amount"][0], location["base_amount"][1])
    
    resource = location["resource"]
    
    if amount > 0:
        await add_resource(current_user["id"], resource, amount)
    
    # Record gathering
    await db.resource_gathering.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "location": data.location,
        "resource": resource,
        "amount": amount,
        "gathered_at": datetime.now(timezone.utc).isoformat()
    })
    
    if amount > 0:
        return {
            "success": True,
            "resource": resource,
            "amount": amount,
            "message": f"Ai colectat {amount}x {RESOURCES[resource]['name']}!"
        }
    else:
        return {
            "success": False,
            "resource": resource,
            "amount": 0,
            "message": "Nu ai găsit nimic de data aceasta."
        }


@router.post("/craft")
async def craft_item(
    data: CraftItemRequest,
    current_user: dict = Depends(get_current_user)
):
    """Craft an item from recipe"""
    if data.recipe_id not in RECIPES:
        raise HTTPException(status_code=404, detail="Recipe not found")
    
    recipe = RECIPES[data.recipe_id]
    
    # Check if already crafting
    active_craft = await db.crafting_queue.find_one({
        "user_id": current_user["id"],
        "status": "crafting"
    })
    if active_craft:
        raise HTTPException(status_code=400, detail="Already crafting something")
    
    # Check resources
    user_resources = await get_user_resources(current_user["id"])
    
    for resource, needed in recipe["materials"].items():
        if user_resources.get(resource, 0) < needed:
            raise HTTPException(status_code=400, detail=f"Not enough {RESOURCES[resource]['name']}")
    
    # Deduct resources
    for resource, needed in recipe["materials"].items():
        await remove_resource(current_user["id"], resource, needed)
    
    now = datetime.now(timezone.utc)
    completes_at = now + timedelta(minutes=recipe["craft_time_minutes"])
    
    craft = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "recipe_id": data.recipe_id,
        "recipe_name": recipe["name"],
        "status": "crafting",
        "started_at": now.isoformat(),
        "completes_at": completes_at.isoformat()
    }
    await db.crafting_queue.insert_one(craft)
    
    return {
        "craft": serialize_doc(craft),
        "message": f"Crafting {recipe['name']}... Ready in {recipe['craft_time_minutes']} minutes."
    }


@router.get("/queue")
async def get_crafting_queue(current_user: dict = Depends(get_current_user)):
    """Get user's crafting queue"""
    queue = await db.crafting_queue.find(
        {"user_id": current_user["id"]},
        {"_id": 0}
    ).sort("started_at", -1).limit(10).to_list(10)
    
    return {"queue": queue}


@router.post("/collect/{craft_id}")
async def collect_crafted_item(
    craft_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Collect a finished crafted item"""
    craft = await db.crafting_queue.find_one({
        "id": craft_id,
        "user_id": current_user["id"],
        "status": "crafting"
    })
    
    if not craft:
        raise HTTPException(status_code=404, detail="Craft not found")
    
    # Check if complete
    if craft["completes_at"] > datetime.now(timezone.utc).isoformat():
        raise HTTPException(status_code=400, detail="Crafting not complete yet")
    
    recipe = RECIPES.get(craft["recipe_id"])
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    
    # Check success
    success = random.random() < recipe["success_rate"]
    
    now = datetime.now(timezone.utc)
    
    if success:
        # Create item in inventory
        item = {
            "id": str(uuid.uuid4()),
            "user_id": current_user["id"],
            "name": recipe["name"],
            "type": recipe["category"],
            "rarity": recipe["result_rarity"],
            "description": recipe["description"],
            "effect": recipe.get("effect"),
            "crafted": True,
            "recipe_id": craft["recipe_id"],
            "created_at": now.isoformat()
        }
        await db.user_inventory.insert_one(item)
        
        await db.crafting_queue.update_one(
            {"id": craft_id},
            {"$set": {"status": "completed", "completed_at": now.isoformat()}}
        )
        
        return {
            "success": True,
            "item": serialize_doc(item),
            "message": f"Ai creat cu succes {recipe['name']}!"
        }
    else:
        await db.crafting_queue.update_one(
            {"id": craft_id},
            {"$set": {"status": "failed", "completed_at": now.isoformat()}}
        )
        
        return {
            "success": False,
            "message": "Crafting-ul a eșuat! Materialele au fost pierdute."
        }


@router.get("/inventory")
async def get_crafted_inventory(current_user: dict = Depends(get_current_user)):
    """Get user's crafted items inventory"""
    items = await db.user_inventory.find(
        {"user_id": current_user["id"]},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    return {"items": items}


@router.post("/use/{item_id}")
async def use_consumable(
    item_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Use a consumable item"""
    item = await db.user_inventory.find_one({
        "id": item_id,
        "user_id": current_user["id"],
        "type": "consumable"
    })
    
    if not item:
        raise HTTPException(status_code=404, detail="Consumable not found")
    
    effect = item.get("effect")
    if not effect:
        raise HTTPException(status_code=400, detail="Item has no effect")
    
    now = datetime.now(timezone.utc)
    
    # Apply effect
    duration_hours = effect.get("duration_hours", 1)
    expires_at = now + timedelta(hours=duration_hours)
    
    active_effect = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "effect_type": effect["type"],
        "value": effect.get("value", 0),
        "item_name": item["name"],
        "started_at": now.isoformat(),
        "expires_at": expires_at.isoformat()
    }
    await db.active_effects.insert_one(active_effect)
    
    # Remove item from inventory
    await db.user_inventory.delete_one({"id": item_id})
    
    return {
        "message": f"{item['name']} activated! Effect lasts {duration_hours} hours.",
        "effect": active_effect
    }


@router.get("/effects")
async def get_active_effects(current_user: dict = Depends(get_current_user)):
    """Get user's active effects"""
    effects = await db.active_effects.find({
        "user_id": current_user["id"],
        "expires_at": {"$gt": datetime.now(timezone.utc).isoformat()}
    }, {"_id": 0}).to_list(20)
    
    return {"effects": effects}


@router.get("/leaderboard")
async def get_crafting_leaderboard(limit: int = 20):
    """Get top crafters"""
    pipeline = [
        {"$match": {"status": "completed"}},
        {"$group": {
            "_id": "$user_id",
            "total_crafts": {"$sum": 1}
        }},
        {"$sort": {"total_crafts": -1}},
        {"$limit": limit}
    ]
    
    results = await db.crafting_queue.aggregate(pipeline).to_list(limit)
    
    leaderboard = []
    for i, r in enumerate(results):
        user = await db.users.find_one({"id": r["_id"]})
        leaderboard.append({
            "rank": i + 1,
            "username": user.get("username", "Unknown") if user else "Unknown",
            "total_crafts": r["total_crafts"]
        })
    
    return {"leaderboard": leaderboard}
