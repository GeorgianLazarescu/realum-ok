from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime, timezone
import uuid

from core.database import db
from core.config import TOKEN_BURN_RATE
from core.auth import get_current_user
from models.marketplace import Job, MarketplaceItem, MarketplaceCreate
from services.token_service import burn_tokens, create_transaction, add_xp, award_badge

router = APIRouter(tags=["Jobs & Marketplace"])

# ==================== JOBS ====================

@router.get("/jobs", response_model=List[Job])
async def get_jobs(zone: Optional[str] = None, role: Optional[str] = None):
    query = {}
    if zone:
        query["zone"] = zone
    if role:
        query["required_role"] = role
    jobs = await db.jobs.find(query, {"_id": 0}).to_list(100)
    return jobs

@router.post("/jobs/{job_id}/apply")
async def apply_for_job(job_id: str, current_user: dict = Depends(get_current_user)):
    job = await db.jobs.find_one({"id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.get("required_level", 1) > current_user.get("level", 1):
        raise HTTPException(status_code=400, detail=f"Requires level {job['required_level']}")
    
    if job.get("required_role") and job["required_role"] != current_user["role"]:
        raise HTTPException(status_code=400, detail=f"Requires role: {job['required_role']}")
    
    # Check if already applied
    existing = await db.active_jobs.find_one({
        "user_id": current_user["id"],
        "job_id": job_id
    })
    if existing:
        raise HTTPException(status_code=400, detail="Already applied to this job")
    
    active_job = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "job_id": job_id,
        "job": job,
        "started_at": datetime.now(timezone.utc).isoformat()
    }
    await db.active_jobs.insert_one(active_job)
    
    return {"status": "applied", "job": job}

@router.get("/jobs/active")
async def get_active_jobs(current_user: dict = Depends(get_current_user)):
    active_jobs = await db.active_jobs.find(
        {"user_id": current_user["id"]}, {"_id": 0}
    ).to_list(100)
    return {"active_jobs": active_jobs}

@router.post("/jobs/{job_id}/complete")
async def complete_job(job_id: str, current_user: dict = Depends(get_current_user)):
    active_job = await db.active_jobs.find_one({
        "user_id": current_user["id"],
        "job_id": job_id
    })
    if not active_job:
        raise HTTPException(status_code=400, detail="Job not active")
    
    job = active_job.get("job")
    if not job:
        raise HTTPException(status_code=404, detail="Job data not found")
    
    reward = job.get("reward", 0)
    xp_reward = job.get("xp_reward", 0)
    
    # Add reward to user
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$inc": {"realum_balance": reward}}
    )
    
    # Add XP
    await add_xp(current_user["id"], xp_reward)
    
    # Create transaction
    await create_transaction(
        current_user["id"], "credit", reward,
        f"Job completed: {job['title']}"
    )
    
    # Remove from active jobs
    await db.active_jobs.delete_one({"_id": active_job["_id"]})
    
    # Award first job badge
    jobs_completed = await db.transactions.count_documents({
        "user_id": current_user["id"],
        "description": {"$regex": "^Job completed"}
    })
    if jobs_completed == 1:
        await award_badge(current_user["id"], "first_job")
    
    return {
        "status": "completed",
        "reward": reward,
        "xp_gained": xp_reward,
        "new_balance": current_user["realum_balance"] + reward
    }

# ==================== MARKETPLACE ====================

@router.get("/marketplace")
async def get_marketplace_items(category: Optional[str] = None):
    query = {}
    if category:
        query["category"] = category
    items = await db.marketplace.find(query, {"_id": 0}).to_list(100)
    return {"items": items}

@router.post("/marketplace")
async def create_marketplace_item(
    data: MarketplaceCreate,
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] not in ["creator", "partner"]:
        raise HTTPException(status_code=403, detail="Only creators and partners can list items")
    
    item = {
        "id": str(uuid.uuid4()),
        "title": data.title,
        "description": data.description,
        "category": data.category,
        "price_rlm": data.price_rlm,
        "seller_id": current_user["id"],
        "seller_name": current_user["username"],
        "downloads": 0,
        "rating": 0.0,
        "reviews": [],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.marketplace.insert_one(item)
    return {"status": "created", "item_id": item["id"]}

@router.post("/marketplace/{item_id}/purchase")
async def purchase_item(item_id: str, current_user: dict = Depends(get_current_user)):
    item = await db.marketplace.find_one({"id": item_id}, {"_id": 0})
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    if item["seller_id"] == current_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot purchase your own item")
    
    if current_user["realum_balance"] < item["price_rlm"]:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    burn_amount = item["price_rlm"] * TOKEN_BURN_RATE
    seller_amount = item["price_rlm"] - burn_amount
    
    # Deduct from buyer
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$inc": {"realum_balance": -item["price_rlm"]}}
    )
    
    # Add to seller
    await db.users.update_one(
        {"id": item["seller_id"]},
        {"$inc": {"realum_balance": seller_amount}}
    )
    
    # Record burn
    await burn_tokens(burn_amount, f"Marketplace purchase: {item['title']}")
    
    # Record transactions
    await create_transaction(
        current_user["id"], "debit", item["price_rlm"],
        f"Purchased: {item['title']}", burn_amount
    )
    await create_transaction(
        item["seller_id"], "credit", seller_amount,
        f"Sold: {item['title']}"
    )
    
    # Update downloads
    await db.marketplace.update_one(
        {"id": item_id},
        {"$inc": {"downloads": 1}}
    )
    
    return {
        "status": "purchased",
        "item": item["title"],
        "amount_paid": item["price_rlm"],
        "amount_burned": burn_amount
    }
