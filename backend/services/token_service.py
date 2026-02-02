from ..core.database import db
from ..core.config import TOKEN_BURN_RATE
from datetime import datetime, timezone
import uuid

async def burn_tokens(amount: float, reason: str):
    """Record token burn in the database"""
    burn_record = {
        "id": str(uuid.uuid4()),
        "amount": amount,
        "reason": reason,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    await db.burns.insert_one(burn_record)
    return burn_record

async def award_badge(user_id: str, badge_id: str):
    """Award a badge to a user"""
    await db.users.update_one(
        {"id": user_id},
        {"$addToSet": {"badges": badge_id}}
    )

async def add_xp(user_id: str, xp_amount: int):
    """Add XP to a user and check for level up"""
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        return
    
    new_xp = user.get("xp", 0) + xp_amount
    new_level = 1 + (new_xp // 500)
    
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"xp": new_xp, "level": new_level}}
    )
    
    return {"xp": new_xp, "level": new_level}

async def create_transaction(user_id: str, tx_type: str, amount: float, description: str, burned: float = 0):
    """Create a wallet transaction record"""
    tx = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "type": tx_type,
        "amount": amount,
        "burned": burned,
        "description": description,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    await db.transactions.insert_one(tx)
    return tx

async def get_token_stats():
    """Get overall token economy statistics"""
    total_users = await db.users.count_documents({})
    pipeline = [{"$group": {"_id": None, "total": {"$sum": "$realum_balance"}}}]
    result = await db.users.aggregate(pipeline).to_list(1)
    total_supply = result[0]["total"] if result else 0
    
    burn_pipeline = [{"$group": {"_id": None, "total": {"$sum": "$amount"}}}]
    burn_result = await db.burns.aggregate(burn_pipeline).to_list(1)
    total_burned = burn_result[0]["total"] if burn_result else 0
    
    return {
        "total_supply": total_supply,
        "total_burned": total_burned,
        "burn_rate": TOKEN_BURN_RATE * 100,
        "active_users": total_users
    }
