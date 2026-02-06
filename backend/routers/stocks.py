"""
REALUM Stock Market
Virtual stock exchange for in-game companies
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import uuid
import random
import math

router = APIRouter(prefix="/api/stocks", tags=["Stock Market"])

from core.database import db
from core.auth import get_current_user


# ============== CONSTANTS ==============

# Default companies in the REALUM economy
DEFAULT_COMPANIES = [
    {
        "id": "realum-tech",
        "symbol": "RLMT",
        "name": "REALUM Technologies",
        "sector": "technology",
        "description": "Core platform infrastructure and metaverse technology",
        "base_price": 100.0,
        "volatility": 0.05,
        "dividend_rate": 0.02
    },
    {
        "id": "cyber-bank",
        "symbol": "CYBK",
        "name": "Cyber Bank Corp",
        "sector": "finance",
        "description": "Leading financial services in the REALUM economy",
        "base_price": 75.0,
        "volatility": 0.03,
        "dividend_rate": 0.04
    },
    {
        "id": "neo-energy",
        "symbol": "NRGY",
        "name": "Neo Energy Systems",
        "sector": "energy",
        "description": "Renewable energy and power grid solutions",
        "base_price": 50.0,
        "volatility": 0.06,
        "dividend_rate": 0.03
    },
    {
        "id": "meta-real",
        "symbol": "MTRE",
        "name": "Meta Real Estate",
        "sector": "real_estate",
        "description": "Virtual land and property development",
        "base_price": 120.0,
        "volatility": 0.04,
        "dividend_rate": 0.05
    },
    {
        "id": "edu-verse",
        "symbol": "EDVS",
        "name": "EduVerse Academy",
        "sector": "education",
        "description": "Online courses and educational content",
        "base_price": 35.0,
        "volatility": 0.04,
        "dividend_rate": 0.01
    },
    {
        "id": "quantum-labs",
        "symbol": "QLAB",
        "name": "Quantum Labs Inc",
        "sector": "research",
        "description": "Cutting-edge research and development",
        "base_price": 200.0,
        "volatility": 0.08,
        "dividend_rate": 0.0
    },
    {
        "id": "social-net",
        "symbol": "SNET",
        "name": "SocialNet Media",
        "sector": "media",
        "description": "Social media and entertainment platforms",
        "base_price": 45.0,
        "volatility": 0.07,
        "dividend_rate": 0.015
    },
    {
        "id": "trade-hub",
        "symbol": "TRHB",
        "name": "TradeHub Markets",
        "sector": "commerce",
        "description": "Marketplace and e-commerce solutions",
        "base_price": 60.0,
        "volatility": 0.05,
        "dividend_rate": 0.025
    }
]

# Trading fees
TRADING_FEE_PERCENT = 0.1  # 0.1% per trade
MIN_TRADE_AMOUNT = 1
MAX_SHARES_PER_TRADE = 10000

# Market hours (always open in REALUM)
MARKET_OPEN = True


# ============== MODELS ==============

class BuyOrderRequest(BaseModel):
    company_id: str
    shares: int = Field(..., gt=0, le=MAX_SHARES_PER_TRADE)

class SellOrderRequest(BaseModel):
    company_id: str
    shares: int = Field(..., gt=0, le=MAX_SHARES_PER_TRADE)

class LimitOrderRequest(BaseModel):
    company_id: str
    shares: int = Field(..., gt=0, le=MAX_SHARES_PER_TRADE)
    order_type: str  # "buy" or "sell"
    limit_price: float = Field(..., gt=0)


# ============== HELPER FUNCTIONS ==============

def serialize_doc(doc):
    """Remove MongoDB _id"""
    if doc and "_id" in doc:
        del doc["_id"]
    return doc

async def initialize_companies():
    """Initialize default companies if they don't exist"""
    for company in DEFAULT_COMPANIES:
        existing = await db.stock_companies.find_one({"id": company["id"]})
        if not existing:
            now = datetime.now(timezone.utc)
            company_data = {
                **company,
                "current_price": company["base_price"],
                "previous_close": company["base_price"],
                "day_high": company["base_price"],
                "day_low": company["base_price"],
                "volume_today": 0,
                "market_cap": company["base_price"] * 1000000,  # 1M shares
                "total_shares": 1000000,
                "available_shares": 900000,  # 90% available for trading
                "price_history": [],
                "created_at": now.isoformat(),
                "last_update": now.isoformat()
            }
            await db.stock_companies.insert_one(company_data)

async def update_stock_price(company_id: str, trade_volume: int, is_buy: bool):
    """Update stock price based on supply/demand"""
    company = await db.stock_companies.find_one({"id": company_id})
    if not company:
        return
    
    # Price impact based on volume and volatility
    volatility = company.get("volatility", 0.05)
    volume_impact = min(trade_volume / 10000, 0.1)  # Cap at 10% impact
    
    # Random market fluctuation
    random_factor = random.uniform(-volatility/2, volatility/2)
    
    # Direction based on buy/sell pressure
    direction = 1 if is_buy else -1
    price_change = company["current_price"] * (volume_impact * direction * 0.1 + random_factor)
    
    new_price = max(1.0, company["current_price"] + price_change)  # Min price of 1 RLM
    new_price = round(new_price, 2)
    
    # Update day high/low
    day_high = max(company.get("day_high", new_price), new_price)
    day_low = min(company.get("day_low", new_price), new_price)
    
    # Add to price history (keep last 100 entries)
    price_history = company.get("price_history", [])[-99:]
    price_history.append({
        "price": new_price,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    await db.stock_companies.update_one(
        {"id": company_id},
        {
            "$set": {
                "current_price": new_price,
                "day_high": day_high,
                "day_low": day_low,
                "price_history": price_history,
                "last_update": datetime.now(timezone.utc).isoformat()
            },
            "$inc": {"volume_today": trade_volume}
        }
    )
    
    return new_price


# ============== MARKET ENDPOINTS ==============

@router.get("/market")
async def get_market_overview():
    """Get market overview and all stocks"""
    await initialize_companies()
    
    companies = await db.stock_companies.find({}, {"_id": 0, "price_history": 0}).to_list(50)
    
    # Calculate market stats
    total_volume = sum(c.get("volume_today", 0) for c in companies)
    total_market_cap = sum(c.get("market_cap", 0) for c in companies)
    
    # Calculate gainers and losers
    for c in companies:
        prev = c.get("previous_close", c["current_price"])
        change = c["current_price"] - prev
        c["change"] = round(change, 2)
        c["change_percent"] = round((change / prev) * 100, 2) if prev > 0 else 0
    
    gainers = sorted([c for c in companies if c["change_percent"] > 0], key=lambda x: x["change_percent"], reverse=True)[:3]
    losers = sorted([c for c in companies if c["change_percent"] < 0], key=lambda x: x["change_percent"])[:3]
    
    return {
        "market_open": MARKET_OPEN,
        "total_volume": total_volume,
        "total_market_cap": total_market_cap,
        "companies": companies,
        "gainers": gainers,
        "losers": losers,
        "trading_fee_percent": TRADING_FEE_PERCENT
    }


@router.get("/company/{company_id}")
async def get_company_details(company_id: str):
    """Get detailed company information"""
    company = await db.stock_companies.find_one({"id": company_id})
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Calculate change
    prev = company.get("previous_close", company["current_price"])
    change = company["current_price"] - prev
    
    # Get recent trades
    recent_trades = await db.stock_trades.find(
        {"company_id": company_id},
        {"_id": 0}
    ).sort("executed_at", -1).limit(20).to_list(20)
    
    return {
        "company": serialize_doc(company),
        "change": round(change, 2),
        "change_percent": round((change / prev) * 100, 2) if prev > 0 else 0,
        "recent_trades": recent_trades
    }


@router.get("/portfolio")
async def get_portfolio(current_user: dict = Depends(get_current_user)):
    """Get user's stock portfolio"""
    holdings = await db.stock_holdings.find(
        {"user_id": current_user["id"], "shares": {"$gt": 0}},
        {"_id": 0}
    ).to_list(50)
    
    total_value = 0
    total_cost = 0
    
    # Enrich with current prices
    for holding in holdings:
        company = await db.stock_companies.find_one({"id": holding["company_id"]})
        if company:
            holding["current_price"] = company["current_price"]
            holding["company_name"] = company["name"]
            holding["symbol"] = company["symbol"]
            holding["market_value"] = round(holding["shares"] * company["current_price"], 2)
            total_value += holding["market_value"]
            total_cost += holding.get("total_cost", 0)
    
    total_gain = total_value - total_cost
    gain_percent = round((total_gain / total_cost) * 100, 2) if total_cost > 0 else 0
    
    return {
        "holdings": holdings,
        "total_value": round(total_value, 2),
        "total_cost": round(total_cost, 2),
        "total_gain": round(total_gain, 2),
        "gain_percent": gain_percent
    }


@router.get("/transactions")
async def get_transactions(
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """Get user's trading history"""
    trades = await db.stock_trades.find(
        {"user_id": current_user["id"]},
        {"_id": 0}
    ).sort("executed_at", -1).limit(limit).to_list(limit)
    
    return {"transactions": trades}


# ============== TRADING ENDPOINTS ==============

@router.post("/buy")
async def buy_stock(
    data: BuyOrderRequest,
    current_user: dict = Depends(get_current_user)
):
    """Buy shares of a company"""
    await initialize_companies()
    
    company = await db.stock_companies.find_one({"id": data.company_id})
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Calculate total cost with fees
    share_price = company["current_price"]
    subtotal = share_price * data.shares
    fee = subtotal * (TRADING_FEE_PERCENT / 100)
    total_cost = subtotal + fee
    
    # Check wallet balance
    if current_user.get("realum_balance", 0) < total_cost:
        raise HTTPException(status_code=400, detail=f"Insufficient funds. Need {total_cost:.2f} RLM")
    
    # Check available shares
    if data.shares > company.get("available_shares", 0):
        raise HTTPException(status_code=400, detail="Not enough shares available")
    
    # Deduct from wallet
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$inc": {"realum_balance": -total_cost}}
    )
    
    # Update company shares
    await db.stock_companies.update_one(
        {"id": data.company_id},
        {"$inc": {"available_shares": -data.shares}}
    )
    
    # Update stock price
    new_price = await update_stock_price(data.company_id, data.shares, is_buy=True)
    
    # Update or create holding
    existing_holding = await db.stock_holdings.find_one({
        "user_id": current_user["id"],
        "company_id": data.company_id
    })
    
    now = datetime.now(timezone.utc)
    
    if existing_holding:
        new_shares = existing_holding["shares"] + data.shares
        new_cost = existing_holding.get("total_cost", 0) + subtotal
        avg_price = new_cost / new_shares
        
        await db.stock_holdings.update_one(
            {"id": existing_holding["id"]},
            {
                "$set": {
                    "shares": new_shares,
                    "total_cost": new_cost,
                    "average_price": round(avg_price, 2),
                    "updated_at": now.isoformat()
                }
            }
        )
    else:
        await db.stock_holdings.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": current_user["id"],
            "company_id": data.company_id,
            "shares": data.shares,
            "total_cost": subtotal,
            "average_price": share_price,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        })
    
    # Record trade
    trade = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "company_id": data.company_id,
        "company_symbol": company["symbol"],
        "company_name": company["name"],
        "type": "buy",
        "shares": data.shares,
        "price_per_share": share_price,
        "subtotal": subtotal,
        "fee": round(fee, 2),
        "total": round(total_cost, 2),
        "executed_at": now.isoformat()
    }
    await db.stock_trades.insert_one(trade)
    
    return {
        "status": "success",
        "trade": serialize_doc(trade),
        "new_price": new_price,
        "message": f"Bought {data.shares} shares of {company['symbol']} at {share_price:.2f} RLM"
    }


@router.post("/sell")
async def sell_stock(
    data: SellOrderRequest,
    current_user: dict = Depends(get_current_user)
):
    """Sell shares of a company"""
    company = await db.stock_companies.find_one({"id": data.company_id})
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Check holdings
    holding = await db.stock_holdings.find_one({
        "user_id": current_user["id"],
        "company_id": data.company_id
    })
    
    if not holding or holding["shares"] < data.shares:
        raise HTTPException(status_code=400, detail="Insufficient shares to sell")
    
    # Calculate proceeds
    share_price = company["current_price"]
    subtotal = share_price * data.shares
    fee = subtotal * (TRADING_FEE_PERCENT / 100)
    proceeds = subtotal - fee
    
    # Add to wallet
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$inc": {"realum_balance": proceeds}}
    )
    
    # Return shares to market
    await db.stock_companies.update_one(
        {"id": data.company_id},
        {"$inc": {"available_shares": data.shares}}
    )
    
    # Update stock price
    new_price = await update_stock_price(data.company_id, data.shares, is_buy=False)
    
    # Update holding
    new_shares = holding["shares"] - data.shares
    if new_shares > 0:
        # Calculate new average (proportional cost basis)
        cost_per_share = holding.get("total_cost", 0) / holding["shares"] if holding["shares"] > 0 else 0
        new_cost = cost_per_share * new_shares
        
        await db.stock_holdings.update_one(
            {"id": holding["id"]},
            {
                "$set": {
                    "shares": new_shares,
                    "total_cost": new_cost,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )
    else:
        await db.stock_holdings.delete_one({"id": holding["id"]})
    
    # Calculate profit/loss
    cost_basis = (holding.get("total_cost", 0) / holding["shares"]) * data.shares if holding["shares"] > 0 else 0
    profit = proceeds - cost_basis
    
    now = datetime.now(timezone.utc)
    
    # Record trade
    trade = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "company_id": data.company_id,
        "company_symbol": company["symbol"],
        "company_name": company["name"],
        "type": "sell",
        "shares": data.shares,
        "price_per_share": share_price,
        "subtotal": subtotal,
        "fee": round(fee, 2),
        "total": round(proceeds, 2),
        "profit": round(profit, 2),
        "executed_at": now.isoformat()
    }
    await db.stock_trades.insert_one(trade)
    
    return {
        "status": "success",
        "trade": serialize_doc(trade),
        "new_price": new_price,
        "profit": round(profit, 2),
        "message": f"Sold {data.shares} shares of {company['symbol']} at {share_price:.2f} RLM"
    }


# ============== MARKET STATS ==============

@router.get("/leaderboard")
async def get_investor_leaderboard(limit: int = 10):
    """Get top investors by portfolio value"""
    # Aggregate portfolio values
    pipeline = [
        {"$match": {"shares": {"$gt": 0}}},
        {"$group": {
            "_id": "$user_id",
            "total_shares": {"$sum": "$shares"},
            "companies_count": {"$sum": 1}
        }},
        {"$sort": {"total_shares": -1}},
        {"$limit": limit}
    ]
    
    results = await db.stock_holdings.aggregate(pipeline).to_list(limit)
    
    leaderboard = []
    for i, r in enumerate(results):
        user = await db.users.find_one({"id": r["_id"]})
        if user:
            leaderboard.append({
                "rank": i + 1,
                "username": user.get("username", "Unknown"),
                "total_shares": r["total_shares"],
                "companies": r["companies_count"]
            })
    
    return {"leaderboard": leaderboard}


@router.get("/sectors")
async def get_sector_performance():
    """Get performance by sector"""
    companies = await db.stock_companies.find({}, {"_id": 0}).to_list(50)
    
    sectors = {}
    for c in companies:
        sector = c.get("sector", "other")
        if sector not in sectors:
            sectors[sector] = {"companies": [], "total_volume": 0, "avg_change": 0}
        
        prev = c.get("previous_close", c["current_price"])
        change_pct = ((c["current_price"] - prev) / prev * 100) if prev > 0 else 0
        
        sectors[sector]["companies"].append(c["symbol"])
        sectors[sector]["total_volume"] += c.get("volume_today", 0)
        sectors[sector]["avg_change"] += change_pct
    
    # Calculate averages
    for sector in sectors:
        count = len(sectors[sector]["companies"])
        if count > 0:
            sectors[sector]["avg_change"] = round(sectors[sector]["avg_change"] / count, 2)
    
    return {"sectors": sectors}
