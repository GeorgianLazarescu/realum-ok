"""
REALUM Financial Derivatives System
Futures, Options, and Leveraged Trading
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Literal
from datetime import datetime, timezone, timedelta
import uuid
import random

router = APIRouter(prefix="/api/derivatives", tags=["Derivatives"])

from core.database import db
from core.auth import get_current_user


# ============== CONSTANTS ==============

LEVERAGE_LEVELS = [2, 5, 10, 20]  # 2x to 20x leverage
MARGIN_REQUIREMENT = 0.1  # 10% margin required
LIQUIDATION_THRESHOLD = 0.05  # 5% margin = liquidation

# Option types
OPTION_TYPES = ["call", "put"]
OPTION_EXPIRATIONS = [1, 7, 30, 90]  # Days until expiration


# ============== MODELS ==============

class OpenFutures(BaseModel):
    company_id: str
    position_type: Literal["long", "short"]
    leverage: int
    margin_amount: float  # RLM to put as margin
    
class BuyOption(BaseModel):
    company_id: str
    option_type: Literal["call", "put"]
    strike_price: float
    expiration_days: int
    quantity: int = 1

class ClosePosition(BaseModel):
    position_id: str


# ============== HELPER FUNCTIONS ==============

async def get_stock_price(company_id: str) -> float:
    """Get current stock price"""
    company = await db.stock_companies.find_one({"id": company_id}, {"_id": 0, "current_price": 1})
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company.get("current_price", 100)


def calculate_option_premium(
    current_price: float,
    strike_price: float,
    option_type: str,
    days_to_expiry: int,
    volatility: float = 0.3
) -> float:
    """Simple option pricing (simplified Black-Scholes)"""
    time_value = (days_to_expiry / 365) * volatility * current_price * 0.5
    
    if option_type == "call":
        intrinsic = max(0, current_price - strike_price)
    else:  # put
        intrinsic = max(0, strike_price - current_price)
    
    premium = intrinsic + time_value
    return round(max(premium, 1), 2)  # Minimum 1 RLM


# ============== FUTURES ENDPOINTS ==============

@router.get("/futures/positions")
async def get_futures_positions(current_user: dict = Depends(get_current_user)):
    """Get all open futures positions"""
    user_id = current_user["id"]
    
    positions = await db.futures_positions.find({
        "user_id": user_id,
        "status": "open"
    }, {"_id": 0}).to_list(50)
    
    # Update P&L for each position
    for pos in positions:
        current_price = await get_stock_price(pos["company_id"])
        entry_price = pos["entry_price"]
        size = pos["position_size"]
        leverage = pos["leverage"]
        
        if pos["position_type"] == "long":
            pnl = (current_price - entry_price) * size * leverage
        else:  # short
            pnl = (entry_price - current_price) * size * leverage
        
        pos["current_price"] = current_price
        pos["unrealized_pnl"] = round(pnl, 2)
        pos["pnl_percent"] = round((pnl / pos["margin_amount"]) * 100, 2)
        
        # Check liquidation
        margin_ratio = (pos["margin_amount"] + pnl) / (size * current_price * leverage)
        pos["margin_ratio"] = round(margin_ratio * 100, 2)
        pos["at_risk"] = margin_ratio < LIQUIDATION_THRESHOLD * 2
    
    return {"positions": positions}


@router.post("/futures/open")
async def open_futures_position(
    data: OpenFutures,
    current_user: dict = Depends(get_current_user)
):
    """Open a leveraged futures position"""
    user_id = current_user["id"]
    
    if data.leverage not in LEVERAGE_LEVELS:
        raise HTTPException(status_code=400, detail=f"Invalid leverage. Choose from: {LEVERAGE_LEVELS}")
    
    if data.margin_amount < 50:
        raise HTTPException(status_code=400, detail="Minimum margin is 50 RLM")
    
    if data.margin_amount > current_user.get("realum_balance", 0):
        raise HTTPException(status_code=400, detail="Insufficient balance for margin")
    
    # Get current price
    current_price = await get_stock_price(data.company_id)
    
    # Calculate position size
    position_value = data.margin_amount * data.leverage
    position_size = position_value / current_price
    
    # Deduct margin
    await db.users.update_one(
        {"id": user_id},
        {"$inc": {"realum_balance": -data.margin_amount}}
    )
    
    # Create position
    position = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "company_id": data.company_id,
        "position_type": data.position_type,
        "leverage": data.leverage,
        "margin_amount": data.margin_amount,
        "position_size": round(position_size, 4),
        "position_value": position_value,
        "entry_price": current_price,
        "status": "open",
        "opened_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.futures_positions.insert_one(position)
    
    return {
        "message": f"Opened {data.leverage}x {data.position_type} position",
        "position": position,
        "entry_price": current_price,
        "position_size": round(position_size, 4)
    }


@router.post("/futures/close")
async def close_futures_position(
    data: ClosePosition,
    current_user: dict = Depends(get_current_user)
):
    """Close a futures position"""
    user_id = current_user["id"]
    
    position = await db.futures_positions.find_one({
        "id": data.position_id,
        "user_id": user_id,
        "status": "open"
    })
    
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    
    # Get current price
    current_price = await get_stock_price(position["company_id"])
    entry_price = position["entry_price"]
    size = position["position_size"]
    leverage = position["leverage"]
    margin = position["margin_amount"]
    
    # Calculate P&L
    if position["position_type"] == "long":
        pnl = (current_price - entry_price) * size * leverage
    else:
        pnl = (entry_price - current_price) * size * leverage
    
    # Return margin + P&L (can be negative)
    final_amount = max(0, margin + pnl)  # Can't go below 0
    
    # Update user balance
    await db.users.update_one(
        {"id": user_id},
        {"$inc": {"realum_balance": final_amount}}
    )
    
    # Close position
    await db.futures_positions.update_one(
        {"id": data.position_id},
        {
            "$set": {
                "status": "closed",
                "exit_price": current_price,
                "realized_pnl": round(pnl, 2),
                "closed_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {
        "message": "Position closed",
        "exit_price": current_price,
        "realized_pnl": round(pnl, 2),
        "returned_amount": round(final_amount, 2)
    }


@router.get("/futures/history")
async def get_futures_history(current_user: dict = Depends(get_current_user)):
    """Get closed futures positions"""
    user_id = current_user["id"]
    
    positions = await db.futures_positions.find({
        "user_id": user_id,
        "status": "closed"
    }, {"_id": 0}).sort("closed_at", -1).limit(50).to_list(50)
    
    return {"history": positions}


# ============== OPTIONS ENDPOINTS ==============

@router.get("/options/chain/{company_id}")
async def get_options_chain(company_id: str):
    """Get available options for a stock"""
    current_price = await get_stock_price(company_id)
    
    # Generate strike prices around current price
    strikes = []
    for pct in [-20, -15, -10, -5, 0, 5, 10, 15, 20]:
        strikes.append(round(current_price * (1 + pct/100), 2))
    
    options_chain = []
    for exp_days in OPTION_EXPIRATIONS:
        for strike in strikes:
            for opt_type in OPTION_TYPES:
                premium = calculate_option_premium(current_price, strike, opt_type, exp_days)
                options_chain.append({
                    "strike_price": strike,
                    "option_type": opt_type,
                    "expiration_days": exp_days,
                    "premium": premium,
                    "in_the_money": (opt_type == "call" and current_price > strike) or 
                                   (opt_type == "put" and current_price < strike)
                })
    
    return {
        "company_id": company_id,
        "current_price": current_price,
        "options": options_chain
    }


@router.post("/options/buy")
async def buy_option(
    data: BuyOption,
    current_user: dict = Depends(get_current_user)
):
    """Buy an option contract"""
    user_id = current_user["id"]
    
    if data.option_type not in OPTION_TYPES:
        raise HTTPException(status_code=400, detail="Invalid option type")
    
    if data.expiration_days not in OPTION_EXPIRATIONS:
        raise HTTPException(status_code=400, detail=f"Invalid expiration. Choose from: {OPTION_EXPIRATIONS}")
    
    if data.quantity < 1 or data.quantity > 100:
        raise HTTPException(status_code=400, detail="Quantity must be 1-100")
    
    current_price = await get_stock_price(data.company_id)
    premium = calculate_option_premium(
        current_price, data.strike_price, data.option_type, data.expiration_days
    )
    
    total_cost = premium * data.quantity
    
    if total_cost > current_user.get("realum_balance", 0):
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    # Deduct cost
    await db.users.update_one(
        {"id": user_id},
        {"$inc": {"realum_balance": -total_cost}}
    )
    
    # Create option contract
    now = datetime.now(timezone.utc)
    expiration = now + timedelta(days=data.expiration_days)
    
    option = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "company_id": data.company_id,
        "option_type": data.option_type,
        "strike_price": data.strike_price,
        "quantity": data.quantity,
        "premium_paid": premium,
        "total_cost": total_cost,
        "entry_price": current_price,
        "status": "active",
        "purchased_at": now.isoformat(),
        "expires_at": expiration.isoformat()
    }
    
    await db.options_contracts.insert_one(option)
    
    return {
        "message": f"Bought {data.quantity} {data.option_type} option(s)",
        "option": option,
        "premium_per_contract": premium,
        "total_cost": total_cost
    }


@router.get("/options/my-contracts")
async def get_my_options(current_user: dict = Depends(get_current_user)):
    """Get user's option contracts"""
    user_id = current_user["id"]
    now = datetime.now(timezone.utc)
    
    contracts = await db.options_contracts.find({
        "user_id": user_id,
        "status": "active"
    }, {"_id": 0}).to_list(50)
    
    # Update current values
    for contract in contracts:
        current_price = await get_stock_price(contract["company_id"])
        strike = contract["strike_price"]
        
        # Calculate intrinsic value
        if contract["option_type"] == "call":
            intrinsic = max(0, current_price - strike) * contract["quantity"]
        else:
            intrinsic = max(0, strike - current_price) * contract["quantity"]
        
        contract["current_price"] = current_price
        contract["intrinsic_value"] = round(intrinsic, 2)
        contract["profit_if_exercised"] = round(intrinsic - contract["total_cost"], 2)
        
        # Time remaining
        expires = datetime.fromisoformat(contract["expires_at"].replace('Z', '+00:00'))
        contract["time_remaining"] = max(0, (expires - now).days)
    
    return {"contracts": contracts}


@router.post("/options/exercise/{contract_id}")
async def exercise_option(
    contract_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Exercise an option contract"""
    user_id = current_user["id"]
    
    contract = await db.options_contracts.find_one({
        "id": contract_id,
        "user_id": user_id,
        "status": "active"
    })
    
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    # Check expiration
    expires = datetime.fromisoformat(contract["expires_at"].replace('Z', '+00:00'))
    if datetime.now(timezone.utc) > expires:
        await db.options_contracts.update_one(
            {"id": contract_id},
            {"$set": {"status": "expired"}}
        )
        raise HTTPException(status_code=400, detail="Option has expired")
    
    current_price = await get_stock_price(contract["company_id"])
    strike = contract["strike_price"]
    quantity = contract["quantity"]
    
    # Calculate payout
    if contract["option_type"] == "call":
        if current_price <= strike:
            raise HTTPException(status_code=400, detail="Call option is out of the money")
        payout = (current_price - strike) * quantity
    else:  # put
        if current_price >= strike:
            raise HTTPException(status_code=400, detail="Put option is out of the money")
        payout = (strike - current_price) * quantity
    
    profit = payout - contract["total_cost"]
    
    # Pay out
    await db.users.update_one(
        {"id": user_id},
        {"$inc": {"realum_balance": payout}}
    )
    
    # Close contract
    await db.options_contracts.update_one(
        {"id": contract_id},
        {
            "$set": {
                "status": "exercised",
                "exit_price": current_price,
                "payout": payout,
                "profit": profit,
                "exercised_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {
        "message": "Option exercised!",
        "payout": round(payout, 2),
        "profit": round(profit, 2)
    }


@router.get("/options/history")
async def get_options_history(current_user: dict = Depends(get_current_user)):
    """Get options trading history"""
    user_id = current_user["id"]
    
    contracts = await db.options_contracts.find({
        "user_id": user_id,
        "status": {"$in": ["exercised", "expired"]}
    }, {"_id": 0}).sort("exercised_at", -1).limit(50).to_list(50)
    
    return {"history": contracts}


# ============== STATS ==============

@router.get("/stats")
async def get_derivatives_stats(current_user: dict = Depends(get_current_user)):
    """Get user's derivatives trading stats"""
    user_id = current_user["id"]
    
    # Futures stats
    futures_closed = await db.futures_positions.find({
        "user_id": user_id,
        "status": "closed"
    }, {"realized_pnl": 1}).to_list(1000)
    
    futures_pnl = sum(p.get("realized_pnl", 0) for p in futures_closed)
    futures_wins = sum(1 for p in futures_closed if p.get("realized_pnl", 0) > 0)
    
    # Options stats
    options_closed = await db.options_contracts.find({
        "user_id": user_id,
        "status": {"$in": ["exercised", "expired"]}
    }, {"profit": 1, "status": 1}).to_list(1000)
    
    options_pnl = sum(o.get("profit", 0) for o in options_closed if o.get("status") == "exercised")
    options_wins = sum(1 for o in options_closed if o.get("profit", 0) > 0)
    
    return {
        "futures": {
            "total_trades": len(futures_closed),
            "winning_trades": futures_wins,
            "total_pnl": round(futures_pnl, 2),
            "win_rate": round(futures_wins / len(futures_closed) * 100, 1) if futures_closed else 0
        },
        "options": {
            "total_contracts": len(options_closed),
            "exercised": sum(1 for o in options_closed if o.get("status") == "exercised"),
            "expired": sum(1 for o in options_closed if o.get("status") == "expired"),
            "total_pnl": round(options_pnl, 2)
        }
    }
