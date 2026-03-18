"""
REALUM Tax & Budget System
Government taxation, public budgets, and fiscal policies
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime, timezone, timedelta
import uuid

router = APIRouter(prefix="/api/treasury", tags=["Treasury & Taxes"])

from core.database import db
from core.auth import get_current_user
from core.utils import serialize_doc


# ============== TAX CONSTANTS ==============

# Tax rates (configurable by government)
DEFAULT_TAX_RATES = {
    "transaction_tax": 0.02,      # 2% on marketplace transactions
    "trading_tax": 0.01,          # 1% on stock trades
    "income_tax": 0.05,           # 5% on job earnings
    "wealth_tax": 0.001,          # 0.1% monthly on savings > 5000 RLM
    "property_tax": 0.02,         # 2% monthly on properties (future)
    "corporate_tax": 0.10,        # 10% on company profits
}

# Wealth tax threshold
WEALTH_TAX_THRESHOLD = 5000

# Budget allocation categories
BUDGET_CATEGORIES = [
    {"id": "education", "name": "Educație", "description": "Finanțare cursuri și academii", "icon": "GraduationCap"},
    {"id": "infrastructure", "name": "Infrastructură", "description": "Dezvoltare zone și facilități", "icon": "Building"},
    {"id": "social", "name": "Social", "description": "Ajutoare și bonusuri cetățeni", "icon": "Heart"},
    {"id": "security", "name": "Securitate", "description": "Moderare și protecție", "icon": "Shield"},
    {"id": "innovation", "name": "Inovație", "description": "Cercetare și dezvoltare", "icon": "Lightbulb"},
    {"id": "events", "name": "Evenimente", "description": "Organizare evenimente speciale", "icon": "Calendar"},
]


# ============== MODELS ==============

class TaxRateUpdate(BaseModel):
    tax_type: str
    new_rate: float = Field(..., ge=0, le=0.5)  # Max 50%

class BudgetAllocation(BaseModel):
    category: str
    amount: float = Field(..., gt=0)
    description: str

class BudgetProposal(BaseModel):
    title: str
    allocations: List[Dict]  # [{category, percentage}]
    description: str

class GrantApplication(BaseModel):
    category: str
    amount: float = Field(..., gt=0, le=10000)
    purpose: str
    details: str


# ============== HELPER FUNCTIONS ==============

async def get_treasury_balance():
    """Get current world treasury balance"""
    treasury = await db.world_treasury.find_one({"id": "main"})
    if not treasury:
        treasury = {
            "id": "main",
            "balance": 0.0,
            "total_collected": 0.0,
            "total_spent": 0.0,
            "tax_rates": DEFAULT_TAX_RATES.copy(),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.world_treasury.insert_one(treasury)
    return treasury

async def get_zone_treasury(zone_id: str):
    """Get zone treasury balance"""
    treasury = await db.zone_treasuries.find_one({"zone_id": zone_id})
    if not treasury:
        treasury = {
            "id": str(uuid.uuid4()),
            "zone_id": zone_id,
            "balance": 0.0,
            "total_collected": 0.0,
            "total_spent": 0.0,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.zone_treasuries.insert_one(treasury)
    return treasury

async def collect_tax(user_id: str, amount: float, tax_type: str, description: str, zone_id: str = None):
    """Collect tax from a transaction"""
    treasury = await get_treasury_balance()
    tax_rate = treasury.get("tax_rates", DEFAULT_TAX_RATES).get(tax_type, 0)
    
    if tax_rate <= 0:
        return 0
    
    tax_amount = amount * tax_rate
    
    # World gets 70%, zone gets 30% (if applicable)
    world_share = tax_amount * 0.7
    zone_share = tax_amount * 0.3 if zone_id else tax_amount * 0.3
    
    # Update world treasury
    await db.world_treasury.update_one(
        {"id": "main"},
        {"$inc": {"balance": world_share, "total_collected": world_share}}
    )
    
    # Update zone treasury if applicable
    if zone_id:
        await db.zone_treasuries.update_one(
            {"zone_id": zone_id},
            {"$inc": {"balance": zone_share, "total_collected": zone_share}},
            upsert=True
        )
    
    # Record tax collection
    await db.tax_records.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "tax_type": tax_type,
        "amount": tax_amount,
        "base_amount": amount,
        "rate": tax_rate,
        "world_share": world_share,
        "zone_share": zone_share,
        "zone_id": zone_id,
        "description": description,
        "collected_at": datetime.now(timezone.utc).isoformat()
    })
    
    return tax_amount


# ============== PUBLIC ENDPOINTS ==============

@router.get("/info")
async def get_treasury_info():
    """Get public treasury information"""
    treasury = await get_treasury_balance()
    
    # Get recent spending
    recent_spending = await db.budget_spending.find(
        {}, {"_id": 0}
    ).sort("spent_at", -1).limit(10).to_list(10)
    
    return {
        "world_treasury": {
            "balance": treasury.get("balance", 0),
            "total_collected": treasury.get("total_collected", 0),
            "total_spent": treasury.get("total_spent", 0)
        },
        "tax_rates": treasury.get("tax_rates", DEFAULT_TAX_RATES),
        "budget_categories": BUDGET_CATEGORIES,
        "recent_spending": recent_spending
    }


@router.get("/tax-rates")
async def get_tax_rates():
    """Get current tax rates"""
    treasury = await get_treasury_balance()
    return {
        "rates": treasury.get("tax_rates", DEFAULT_TAX_RATES),
        "descriptions": {
            "transaction_tax": "Taxă pe tranzacții marketplace",
            "trading_tax": "Taxă pe tranzacții bursă",
            "income_tax": "Impozit pe venit (joburi)",
            "wealth_tax": f"Impozit pe avere > {WEALTH_TAX_THRESHOLD} RLM",
            "property_tax": "Impozit pe proprietăți",
            "corporate_tax": "Impozit pe profit companii"
        }
    }


@router.get("/budget")
async def get_budget_overview():
    """Get current budget allocation and spending"""
    treasury = await get_treasury_balance()
    
    # Get current budget allocation
    current_budget = await db.budgets.find_one({"status": "active"}, {"_id": 0})
    
    # Get spending by category
    pipeline = [
        {"$group": {
            "_id": "$category",
            "total_spent": {"$sum": "$amount"},
            "count": {"$sum": 1}
        }}
    ]
    spending_by_category = await db.budget_spending.aggregate(pipeline).to_list(20)
    
    return {
        "treasury_balance": treasury.get("balance", 0),
        "current_budget": current_budget,
        "spending_by_category": {s["_id"]: s["total_spent"] for s in spending_by_category},
        "categories": BUDGET_CATEGORIES
    }


@router.get("/my-taxes")
async def get_my_tax_history(
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """Get user's tax payment history"""
    taxes = await db.tax_records.find(
        {"user_id": current_user["id"]},
        {"_id": 0}
    ).sort("collected_at", -1).limit(limit).to_list(limit)
    
    # Calculate totals
    total_paid = sum(t.get("amount", 0) for t in taxes)
    
    return {
        "taxes": taxes,
        "total_paid": round(total_paid, 2),
        "tax_count": len(taxes)
    }


# ============== GOVERNMENT ENDPOINTS (Requires Position) ==============

async def check_government_position(user_id: str, required_level: str = "any"):
    """Check if user holds a government position"""
    position = await db.political_positions.find_one({
        "holder_id": user_id,
        "status": "active"
    })
    
    if not position:
        raise HTTPException(status_code=403, detail="Only government officials can perform this action")
    
    if required_level == "world" and position.get("level") != "world":
        raise HTTPException(status_code=403, detail="Only world government officials can perform this action")
    
    return position


@router.post("/tax-rates/update")
async def update_tax_rate(
    data: TaxRateUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update a tax rate (World government only)"""
    await check_government_position(current_user["id"], "world")
    
    if data.tax_type not in DEFAULT_TAX_RATES:
        raise HTTPException(status_code=400, detail="Invalid tax type")
    
    # Update rate
    await db.world_treasury.update_one(
        {"id": "main"},
        {"$set": {f"tax_rates.{data.tax_type}": data.new_rate}}
    )
    
    # Log the change
    await db.tax_changes.insert_one({
        "id": str(uuid.uuid4()),
        "tax_type": data.tax_type,
        "old_rate": DEFAULT_TAX_RATES[data.tax_type],
        "new_rate": data.new_rate,
        "changed_by": current_user["id"],
        "changed_by_username": current_user["username"],
        "changed_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "message": f"Tax rate for {data.tax_type} updated to {data.new_rate * 100}%",
        "new_rate": data.new_rate
    }


@router.post("/budget/allocate")
async def allocate_budget(
    data: BudgetAllocation,
    current_user: dict = Depends(get_current_user)
):
    """Allocate budget to a category (Government only)"""
    position = await check_government_position(current_user["id"])
    
    if data.category not in [c["id"] for c in BUDGET_CATEGORIES]:
        raise HTTPException(status_code=400, detail="Invalid budget category")
    
    treasury = await get_treasury_balance()
    
    if treasury.get("balance", 0) < data.amount:
        raise HTTPException(status_code=400, detail="Insufficient treasury balance")
    
    # Deduct from treasury
    await db.world_treasury.update_one(
        {"id": "main"},
        {"$inc": {"balance": -data.amount, "total_spent": data.amount}}
    )
    
    # Record spending
    spending = {
        "id": str(uuid.uuid4()),
        "category": data.category,
        "amount": data.amount,
        "description": data.description,
        "approved_by": current_user["id"],
        "approved_by_username": current_user["username"],
        "position": position.get("position_title"),
        "spent_at": datetime.now(timezone.utc).isoformat()
    }
    await db.budget_spending.insert_one(spending)
    
    return {
        "spending": serialize_doc(spending),
        "message": f"Allocated {data.amount} RLM to {data.category}",
        "remaining_balance": treasury["balance"] - data.amount
    }


# ============== CITIZEN GRANTS ==============

@router.post("/grants/apply")
async def apply_for_grant(
    data: GrantApplication,
    current_user: dict = Depends(get_current_user)
):
    """Apply for a government grant"""
    if data.category not in [c["id"] for c in BUDGET_CATEGORIES]:
        raise HTTPException(status_code=400, detail="Invalid grant category")
    
    # Check if user already has pending application
    pending = await db.grant_applications.find_one({
        "user_id": current_user["id"],
        "status": "pending"
    })
    if pending:
        raise HTTPException(status_code=400, detail="You already have a pending grant application")
    
    application = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "username": current_user["username"],
        "category": data.category,
        "amount": data.amount,
        "purpose": data.purpose,
        "details": data.details,
        "status": "pending",
        "applied_at": datetime.now(timezone.utc).isoformat()
    }
    await db.grant_applications.insert_one(application)
    
    return {
        "application": serialize_doc(application),
        "message": "Grant application submitted! Awaiting government review."
    }


@router.get("/grants/pending")
async def get_pending_grants(current_user: dict = Depends(get_current_user)):
    """Get pending grant applications (Government only)"""
    await check_government_position(current_user["id"])
    
    applications = await db.grant_applications.find(
        {"status": "pending"},
        {"_id": 0}
    ).sort("applied_at", 1).to_list(50)
    
    return {"applications": applications}


@router.post("/grants/{application_id}/approve")
async def approve_grant(
    application_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Approve a grant application (Government only)"""
    await check_government_position(current_user["id"])
    
    application = await db.grant_applications.find_one({"id": application_id, "status": "pending"})
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    treasury = await get_treasury_balance()
    if treasury.get("balance", 0) < application["amount"]:
        raise HTTPException(status_code=400, detail="Insufficient treasury balance")
    
    # Deduct from treasury
    await db.world_treasury.update_one(
        {"id": "main"},
        {"$inc": {"balance": -application["amount"], "total_spent": application["amount"]}}
    )
    
    # Add to user balance
    await db.users.update_one(
        {"id": application["user_id"]},
        {"$inc": {"realum_balance": application["amount"]}}
    )
    
    # Update application
    await db.grant_applications.update_one(
        {"id": application_id},
        {"$set": {
            "status": "approved",
            "approved_by": current_user["id"],
            "approved_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Record spending
    await db.budget_spending.insert_one({
        "id": str(uuid.uuid4()),
        "category": application["category"],
        "amount": application["amount"],
        "description": f"Grant to {application['username']}: {application['purpose']}",
        "grant_id": application_id,
        "approved_by": current_user["id"],
        "spent_at": datetime.now(timezone.utc).isoformat()
    })
    
    # Notify user
    await db.notifications.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": application["user_id"],
        "type": "grant_approved",
        "title": "Grant Approved! 🎉",
        "message": f"Your grant of {application['amount']} RLM has been approved!",
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": f"Grant of {application['amount']} RLM approved for {application['username']}"}


@router.post("/grants/{application_id}/reject")
async def reject_grant(
    application_id: str,
    reason: str = "Application did not meet requirements",
    current_user: dict = Depends(get_current_user)
):
    """Reject a grant application (Government only)"""
    await check_government_position(current_user["id"])
    
    application = await db.grant_applications.find_one({"id": application_id, "status": "pending"})
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    await db.grant_applications.update_one(
        {"id": application_id},
        {"$set": {
            "status": "rejected",
            "rejected_by": current_user["id"],
            "rejection_reason": reason,
            "rejected_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Notify user
    await db.notifications.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": application["user_id"],
        "type": "grant_rejected",
        "title": "Grant Application Update",
        "message": f"Your grant application was not approved. Reason: {reason}",
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "Grant application rejected"}


# ============== STATISTICS ==============

@router.get("/statistics")
async def get_treasury_statistics():
    """Get treasury statistics"""
    treasury = await get_treasury_balance()
    
    # Tax collection by type
    pipeline = [
        {"$group": {
            "_id": "$tax_type",
            "total": {"$sum": "$amount"},
            "count": {"$sum": 1}
        }}
    ]
    tax_by_type = await db.tax_records.aggregate(pipeline).to_list(20)
    
    # Recent tax collections
    recent_taxes = await db.tax_records.find(
        {}, {"_id": 0}
    ).sort("collected_at", -1).limit(20).to_list(20)
    
    # Top taxpayers
    top_taxpayers_pipeline = [
        {"$group": {
            "_id": "$user_id",
            "total_paid": {"$sum": "$amount"}
        }},
        {"$sort": {"total_paid": -1}},
        {"$limit": 10}
    ]
    top_taxpayers = await db.tax_records.aggregate(top_taxpayers_pipeline).to_list(10)
    
    # Enrich with usernames
    for tp in top_taxpayers:
        user = await db.users.find_one({"id": tp["_id"]})
        tp["username"] = user.get("username", "Unknown") if user else "Unknown"
    
    return {
        "treasury_balance": treasury.get("balance", 0),
        "total_collected": treasury.get("total_collected", 0),
        "total_spent": treasury.get("total_spent", 0),
        "tax_by_type": {t["_id"]: t["total"] for t in tax_by_type},
        "recent_taxes": recent_taxes,
        "top_taxpayers": top_taxpayers
    }
