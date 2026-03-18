"""
REALUM Player Companies & IPO System
Users can create companies and list them on the stock market
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import uuid
import random

router = APIRouter(prefix="/api/companies", tags=["Player Companies"])

from core.database import db
from core.auth import get_current_user
from core.utils import serialize_doc


# ============== CONSTANTS ==============

# Company creation costs
COMPANY_CREATION_COST = 5000  # 5000 RLM to register a company
IPO_COST = 10000  # 10000 RLM to go public (IPO)
IPO_MIN_SHARES = 100000  # Minimum shares for IPO
IPO_MAX_SHARES = 10000000  # Maximum shares for IPO

# Company sectors
COMPANY_SECTORS = [
    {"id": "technology", "name": "Tehnologie", "volatility": 0.06},
    {"id": "finance", "name": "Finanțe", "volatility": 0.04},
    {"id": "energy", "name": "Energie", "volatility": 0.05},
    {"id": "real_estate", "name": "Imobiliare", "volatility": 0.03},
    {"id": "education", "name": "Educație", "volatility": 0.03},
    {"id": "entertainment", "name": "Divertisment", "volatility": 0.07},
    {"id": "commerce", "name": "Comerț", "volatility": 0.05},
    {"id": "manufacturing", "name": "Producție", "volatility": 0.04},
]

# Dividend settings
MIN_DIVIDEND_RATE = 0.0
MAX_DIVIDEND_RATE = 0.10  # Max 10% annual dividend
DIVIDEND_PAYOUT_INTERVAL_DAYS = 30


# ============== MODELS ==============

class CreateCompanyRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=50)
    symbol: str = Field(..., min_length=2, max_length=5)
    sector: str
    description: str = Field(..., min_length=10, max_length=500)
    logo_color: str = "#00F0FF"

class IPORequest(BaseModel):
    total_shares: int = Field(..., ge=IPO_MIN_SHARES, le=IPO_MAX_SHARES)
    initial_price: float = Field(..., ge=1.0, le=1000.0)
    public_percentage: float = Field(..., ge=10, le=90)  # % of shares to sell
    dividend_rate: float = Field(default=0.02, ge=MIN_DIVIDEND_RATE, le=MAX_DIVIDEND_RATE)

class UpdateCompanyRequest(BaseModel):
    description: Optional[str] = None
    dividend_rate: Optional[float] = None
    logo_color: Optional[str] = None

class InvestInCompanyRequest(BaseModel):
    amount: float = Field(..., gt=0)


# ============== HELPER FUNCTIONS ==============

async def get_user_company(user_id: str):
    """Get company owned by user"""
    return await db.player_companies.find_one({"owner_id": user_id, "status": {"$ne": "dissolved"}})

async def calculate_company_value(company_id: str) -> float:
    """Calculate total company value"""
    company = await db.player_companies.find_one({"id": company_id})
    if not company:
        return 0
    
    if company.get("is_public"):
        # For public companies, use market cap
        return company.get("current_price", 0) * company.get("total_shares", 0)
    else:
        # For private companies, use assets + investments
        return company.get("treasury", 0) + company.get("total_investment", 0)


# ============== COMPANY ENDPOINTS ==============

@router.get("/sectors")
async def get_company_sectors():
    """Get available company sectors"""
    return {
        "sectors": COMPANY_SECTORS,
        "creation_cost": COMPANY_CREATION_COST,
        "ipo_cost": IPO_COST
    }


@router.get("/my-company")
async def get_my_company(current_user: dict = Depends(get_current_user)):
    """Get user's company details"""
    company = await get_user_company(current_user["id"])
    
    if not company:
        return {
            "has_company": False,
            "can_create": current_user.get("realum_balance", 0) >= COMPANY_CREATION_COST,
            "creation_cost": COMPANY_CREATION_COST
        }
    
    # Get investors if private
    investors = []
    if not company.get("is_public"):
        investors = await db.company_investments.find(
            {"company_id": company["id"]},
            {"_id": 0}
        ).to_list(50)
    
    # Get shareholders if public
    shareholders = []
    if company.get("is_public"):
        pipeline = [
            {"$match": {"company_id": company["id"], "shares": {"$gt": 0}}},
            {"$group": {
                "_id": "$user_id",
                "shares": {"$sum": "$shares"}
            }},
            {"$sort": {"shares": -1}},
            {"$limit": 20}
        ]
        shareholder_data = await db.stock_holdings.aggregate(pipeline).to_list(20)
        for sh in shareholder_data:
            user = await db.users.find_one({"id": sh["_id"]})
            shareholders.append({
                "user_id": sh["_id"],
                "username": user.get("username", "Unknown") if user else "Unknown",
                "shares": sh["shares"],
                "percentage": round((sh["shares"] / company["total_shares"]) * 100, 2)
            })
    
    return {
        "has_company": True,
        "company": serialize_doc(company),
        "investors": investors,
        "shareholders": shareholders,
        "company_value": await calculate_company_value(company["id"])
    }


@router.post("/create")
async def create_company(
    data: CreateCompanyRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create a new private company"""
    # Check if user already has a company
    existing = await get_user_company(current_user["id"])
    if existing:
        raise HTTPException(status_code=400, detail="You already own a company")
    
    # Check balance
    if current_user.get("realum_balance", 0) < COMPANY_CREATION_COST:
        raise HTTPException(status_code=400, detail=f"Need {COMPANY_CREATION_COST} RLM to create a company")
    
    # Validate sector
    if data.sector not in [s["id"] for s in COMPANY_SECTORS]:
        raise HTTPException(status_code=400, detail="Invalid sector")
    
    # Check symbol uniqueness
    symbol_exists = await db.player_companies.find_one({"symbol": data.symbol.upper()})
    if symbol_exists:
        raise HTTPException(status_code=400, detail="Symbol already in use")
    
    stock_symbol_exists = await db.stock_companies.find_one({"symbol": data.symbol.upper()})
    if stock_symbol_exists:
        raise HTTPException(status_code=400, detail="Symbol already in use by market company")
    
    # Deduct cost
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$inc": {"realum_balance": -COMPANY_CREATION_COST}}
    )
    
    now = datetime.now(timezone.utc)
    sector_info = next(s for s in COMPANY_SECTORS if s["id"] == data.sector)
    
    company = {
        "id": str(uuid.uuid4()),
        "name": data.name,
        "symbol": data.symbol.upper(),
        "sector": data.sector,
        "sector_name": sector_info["name"],
        "description": data.description,
        "logo_color": data.logo_color,
        "owner_id": current_user["id"],
        "owner_username": current_user["username"],
        "status": "private",
        "is_public": False,
        "treasury": COMPANY_CREATION_COST * 0.5,  # 50% goes to company treasury
        "total_investment": 0,
        "revenue": 0,
        "expenses": 0,
        "profit": 0,
        "employee_count": 1,  # Owner
        "founded_at": now.isoformat(),
        "created_at": now.isoformat()
    }
    await db.player_companies.insert_one(company)
    
    return {
        "company": serialize_doc(company),
        "message": f"Company '{data.name}' created successfully!"
    }


@router.post("/invest/{company_id}")
async def invest_in_company(
    company_id: str,
    data: InvestInCompanyRequest,
    current_user: dict = Depends(get_current_user)
):
    """Invest in a private company"""
    company = await db.player_companies.find_one({"id": company_id, "status": "private"})
    if not company:
        raise HTTPException(status_code=404, detail="Private company not found")
    
    if company["owner_id"] == current_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot invest in your own company")
    
    if current_user.get("realum_balance", 0) < data.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    # Deduct from investor
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$inc": {"realum_balance": -data.amount}}
    )
    
    # Add to company treasury
    await db.player_companies.update_one(
        {"id": company_id},
        {"$inc": {"treasury": data.amount, "total_investment": data.amount}}
    )
    
    # Record investment
    investment = {
        "id": str(uuid.uuid4()),
        "company_id": company_id,
        "company_name": company["name"],
        "investor_id": current_user["id"],
        "investor_username": current_user["username"],
        "amount": data.amount,
        "invested_at": datetime.now(timezone.utc).isoformat()
    }
    await db.company_investments.insert_one(investment)
    
    # Notify owner
    await db.notifications.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": company["owner_id"],
        "type": "investment_received",
        "title": "New Investment! 💰",
        "message": f"{current_user['username']} invested {data.amount} RLM in {company['name']}",
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "investment": serialize_doc(investment),
        "message": f"Invested {data.amount} RLM in {company['name']}"
    }


# ============== IPO ENDPOINTS ==============

@router.post("/ipo")
async def launch_ipo(
    data: IPORequest,
    current_user: dict = Depends(get_current_user)
):
    """Launch an IPO to make company public"""
    company = await get_user_company(current_user["id"])
    if not company:
        raise HTTPException(status_code=404, detail="You don't own a company")
    
    if company.get("is_public"):
        raise HTTPException(status_code=400, detail="Company is already public")
    
    # Check IPO cost
    total_cost = IPO_COST
    if current_user.get("realum_balance", 0) < total_cost:
        raise HTTPException(status_code=400, detail=f"Need {total_cost} RLM for IPO")
    
    # Calculate shares distribution
    public_shares = int(data.total_shares * (data.public_percentage / 100))
    owner_shares = data.total_shares - public_shares
    
    # Deduct IPO cost
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$inc": {"realum_balance": -total_cost}}
    )
    
    now = datetime.now(timezone.utc)
    sector_info = next((s for s in COMPANY_SECTORS if s["id"] == company["sector"]), {"volatility": 0.05})
    
    # Update company to public
    await db.player_companies.update_one(
        {"id": company["id"]},
        {"$set": {
            "status": "public",
            "is_public": True,
            "total_shares": data.total_shares,
            "public_shares": public_shares,
            "owner_shares": owner_shares,
            "current_price": data.initial_price,
            "ipo_price": data.initial_price,
            "dividend_rate": data.dividend_rate,
            "market_cap": data.initial_price * data.total_shares,
            "ipo_date": now.isoformat()
        }}
    )
    
    # Add to stock market
    stock_listing = {
        "id": company["id"],
        "symbol": company["symbol"],
        "name": company["name"],
        "sector": company["sector"],
        "description": company["description"],
        "base_price": data.initial_price,
        "volatility": sector_info["volatility"],
        "dividend_rate": data.dividend_rate,
        "current_price": data.initial_price,
        "previous_close": data.initial_price,
        "day_high": data.initial_price,
        "day_low": data.initial_price,
        "volume_today": 0,
        "market_cap": data.initial_price * data.total_shares,
        "total_shares": data.total_shares,
        "available_shares": public_shares,
        "is_player_company": True,
        "owner_id": current_user["id"],
        "price_history": [],
        "created_at": now.isoformat(),
        "last_update": now.isoformat()
    }
    await db.stock_companies.insert_one(stock_listing)
    
    # Give owner their shares
    await db.stock_holdings.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "company_id": company["id"],
        "shares": owner_shares,
        "total_cost": 0,  # Owner gets shares for free
        "average_price": 0,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    })
    
    return {
        "message": f"🎉 {company['name']} is now public! IPO successful!",
        "symbol": company["symbol"],
        "initial_price": data.initial_price,
        "total_shares": data.total_shares,
        "public_shares": public_shares,
        "owner_shares": owner_shares,
        "market_cap": data.initial_price * data.total_shares
    }


@router.get("/public")
async def get_public_player_companies():
    """Get all public player-owned companies"""
    companies = await db.stock_companies.find(
        {"is_player_company": True},
        {"_id": 0, "price_history": 0}
    ).sort("market_cap", -1).to_list(50)
    
    return {"companies": companies}


# ============== COMPANY MANAGEMENT ==============

@router.post("/{company_id}/dividend")
async def pay_dividend(
    company_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Pay dividends to shareholders"""
    company = await db.player_companies.find_one({"id": company_id, "owner_id": current_user["id"]})
    if not company:
        raise HTTPException(status_code=404, detail="Company not found or you're not the owner")
    
    if not company.get("is_public"):
        raise HTTPException(status_code=400, detail="Only public companies can pay dividends")
    
    # Check last dividend date
    last_dividend = company.get("last_dividend_date")
    if last_dividend:
        last_date = datetime.fromisoformat(last_dividend.replace("Z", "+00:00"))
        if (datetime.now(timezone.utc) - last_date).days < DIVIDEND_PAYOUT_INTERVAL_DAYS:
            raise HTTPException(status_code=400, detail=f"Can only pay dividends every {DIVIDEND_PAYOUT_INTERVAL_DAYS} days")
    
    dividend_rate = company.get("dividend_rate", 0.02)
    dividend_per_share = company["current_price"] * dividend_rate / 12  # Monthly dividend
    
    # Get all shareholders
    holdings = await db.stock_holdings.find(
        {"company_id": company_id, "shares": {"$gt": 0}}
    ).to_list(1000)
    
    total_dividend_paid = 0
    
    for holding in holdings:
        dividend_amount = holding["shares"] * dividend_per_share
        total_dividend_paid += dividend_amount
        
        # Pay dividend
        await db.users.update_one(
            {"id": holding["user_id"]},
            {"$inc": {"realum_balance": dividend_amount}}
        )
        
        # Record dividend payment
        await db.dividend_payments.insert_one({
            "id": str(uuid.uuid4()),
            "company_id": company_id,
            "user_id": holding["user_id"],
            "shares": holding["shares"],
            "dividend_per_share": dividend_per_share,
            "total_amount": dividend_amount,
            "paid_at": datetime.now(timezone.utc).isoformat()
        })
    
    # Update last dividend date
    await db.player_companies.update_one(
        {"id": company_id},
        {"$set": {"last_dividend_date": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {
        "message": f"Dividends paid! Total: {total_dividend_paid:.2f} RLM",
        "dividend_per_share": round(dividend_per_share, 4),
        "shareholders_paid": len(holdings),
        "total_paid": round(total_dividend_paid, 2)
    }


@router.get("/leaderboard")
async def get_company_leaderboard():
    """Get top companies by market cap"""
    companies = await db.stock_companies.find(
        {"is_player_company": True},
        {"_id": 0, "name": 1, "symbol": 1, "market_cap": 1, "current_price": 1, "owner_id": 1}
    ).sort("market_cap", -1).limit(20).to_list(20)
    
    # Enrich with owner names
    for company in companies:
        owner = await db.users.find_one({"id": company.get("owner_id")})
        company["owner_username"] = owner.get("username", "Unknown") if owner else "Unknown"
    
    return {"leaderboard": companies}
