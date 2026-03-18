"""
REALUM Premium Membership System
Subscription benefits and exclusive features
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone, timedelta
import uuid

router = APIRouter(prefix="/api/premium", tags=["Premium Membership"])

from core.database import db
from core.auth import get_current_user
from core.utils import serialize_doc


# ============== CONSTANTS ==============

# Premium tiers and benefits
PREMIUM_TIERS = {
    "silver": {
        "name": "Silver",
        "price_monthly": 500,
        "price_yearly": 5000,  # ~17% discount
        "color": "#C0C0C0",
        "benefits": {
            "interest_bonus": 0.25,        # +25% bank interest
            "fee_reduction": 0.25,         # -25% trading fees
            "tax_reduction": 0.10,         # -10% taxes
            "daily_bonus": 10,             # +10 RLM daily
            "xp_multiplier": 1.25,         # +25% XP
            "exclusive_badge": "silver_member",
            "priority_support": False,
            "custom_profile": False
        }
    },
    "gold": {
        "name": "Gold",
        "price_monthly": 1000,
        "price_yearly": 9000,  # ~25% discount
        "color": "#FFD700",
        "benefits": {
            "interest_bonus": 0.50,        # +50% bank interest
            "fee_reduction": 0.50,         # -50% trading fees
            "tax_reduction": 0.20,         # -20% taxes
            "daily_bonus": 25,             # +25 RLM daily
            "xp_multiplier": 1.50,         # +50% XP
            "exclusive_badge": "gold_member",
            "priority_support": True,
            "custom_profile": True
        }
    },
    "platinum": {
        "name": "Platinum",
        "price_monthly": 2000,
        "price_yearly": 15000,  # ~37% discount
        "color": "#E5E4E2",
        "benefits": {
            "interest_bonus": 1.00,        # +100% bank interest
            "fee_reduction": 0.75,         # -75% trading fees
            "tax_reduction": 0.30,         # -30% taxes
            "daily_bonus": 50,             # +50 RLM daily
            "xp_multiplier": 2.00,         # +100% XP
            "exclusive_badge": "platinum_member",
            "priority_support": True,
            "custom_profile": True,
            "early_access": True,
            "vip_events": True
        }
    }
}

# Exclusive items for premium members
PREMIUM_EXCLUSIVE_ITEMS = [
    {"id": "golden_avatar_frame", "name": "Golden Avatar Frame", "tier": "gold", "type": "cosmetic"},
    {"id": "platinum_badge", "name": "Platinum Crown Badge", "tier": "platinum", "type": "cosmetic"},
    {"id": "vip_title", "name": "VIP Title", "tier": "silver", "type": "title"},
    {"id": "exclusive_emotes", "name": "Exclusive Emotes Pack", "tier": "gold", "type": "emotes"},
]


# ============== MODELS ==============

class SubscribeRequest(BaseModel):
    tier: str
    duration: str = "monthly"  # monthly or yearly


# ============== HELPER FUNCTIONS ==============

async def get_user_premium_status(user_id: str):
    """Get user's premium subscription status"""
    subscription = await db.premium_subscriptions.find_one({
        "user_id": user_id,
        "status": "active",
        "expires_at": {"$gt": datetime.now(timezone.utc).isoformat()}
    })
    return subscription

async def apply_premium_bonus(user_id: str, bonus_type: str, base_value: float) -> float:
    """Apply premium bonus to a value"""
    subscription = await get_user_premium_status(user_id)
    if not subscription:
        return base_value
    
    tier = subscription.get("tier")
    tier_info = PREMIUM_TIERS.get(tier)
    if not tier_info:
        return base_value
    
    benefits = tier_info.get("benefits", {})
    
    if bonus_type == "interest":
        return base_value * (1 + benefits.get("interest_bonus", 0))
    elif bonus_type == "fee":
        return base_value * (1 - benefits.get("fee_reduction", 0))
    elif bonus_type == "tax":
        return base_value * (1 - benefits.get("tax_reduction", 0))
    elif bonus_type == "xp":
        return base_value * benefits.get("xp_multiplier", 1)
    
    return base_value

async def give_daily_premium_bonus(user_id: str):
    """Give daily bonus to premium members"""
    subscription = await get_user_premium_status(user_id)
    if not subscription:
        return 0
    
    tier = subscription.get("tier")
    tier_info = PREMIUM_TIERS.get(tier)
    if not tier_info:
        return 0
    
    daily_bonus = tier_info["benefits"].get("daily_bonus", 0)
    
    # Check if already claimed today
    today = datetime.now(timezone.utc).date().isoformat()
    last_claim = subscription.get("last_daily_claim", "")
    
    if last_claim == today:
        return 0  # Already claimed
    
    # Give bonus
    await db.users.update_one(
        {"id": user_id},
        {"$inc": {"realum_balance": daily_bonus}}
    )
    
    # Update last claim date
    await db.premium_subscriptions.update_one(
        {"id": subscription["id"]},
        {"$set": {"last_daily_claim": today}}
    )
    
    return daily_bonus


# ============== ENDPOINTS ==============

@router.get("/tiers")
async def get_premium_tiers():
    """Get all premium tier information"""
    return {
        "tiers": PREMIUM_TIERS,
        "exclusive_items": PREMIUM_EXCLUSIVE_ITEMS
    }


@router.get("/status")
async def get_premium_status(current_user: dict = Depends(get_current_user)):
    """Get user's premium subscription status"""
    subscription = await get_user_premium_status(current_user["id"])
    
    if not subscription:
        return {
            "is_premium": False,
            "tier": None,
            "benefits": None,
            "message": "Upgrade to Premium for exclusive benefits!"
        }
    
    tier_info = PREMIUM_TIERS.get(subscription["tier"])
    days_remaining = 0
    
    if subscription.get("expires_at"):
        expires = datetime.fromisoformat(subscription["expires_at"].replace("Z", "+00:00"))
        days_remaining = max(0, (expires - datetime.now(timezone.utc)).days)
    
    return {
        "is_premium": True,
        "tier": subscription["tier"],
        "tier_name": tier_info["name"] if tier_info else "Unknown",
        "tier_color": tier_info["color"] if tier_info else "#888",
        "benefits": tier_info["benefits"] if tier_info else {},
        "expires_at": subscription.get("expires_at"),
        "days_remaining": days_remaining,
        "subscribed_at": subscription.get("subscribed_at"),
        "auto_renew": subscription.get("auto_renew", False)
    }


@router.post("/subscribe")
async def subscribe_premium(
    data: SubscribeRequest,
    current_user: dict = Depends(get_current_user)
):
    """Subscribe to premium tier"""
    if data.tier not in PREMIUM_TIERS:
        raise HTTPException(status_code=400, detail="Invalid tier")
    
    tier_info = PREMIUM_TIERS[data.tier]
    
    # Calculate price
    if data.duration == "yearly":
        price = tier_info["price_yearly"]
        duration_days = 365
    else:
        price = tier_info["price_monthly"]
        duration_days = 30
    
    # Check balance
    if current_user.get("realum_balance", 0) < price:
        raise HTTPException(status_code=400, detail=f"Insufficient funds. Need {price} RLM")
    
    # Check existing subscription
    existing = await get_user_premium_status(current_user["id"])
    
    now = datetime.now(timezone.utc)
    
    if existing:
        # Extend existing subscription
        current_expiry = datetime.fromisoformat(existing["expires_at"].replace("Z", "+00:00"))
        new_expiry = max(current_expiry, now) + timedelta(days=duration_days)
        
        # If upgrading tier
        if list(PREMIUM_TIERS.keys()).index(data.tier) > list(PREMIUM_TIERS.keys()).index(existing["tier"]):
            # Deduct full price for upgrade
            await db.users.update_one(
                {"id": current_user["id"]},
                {"$inc": {"realum_balance": -price}}
            )
            
            await db.premium_subscriptions.update_one(
                {"id": existing["id"]},
                {"$set": {
                    "tier": data.tier,
                    "expires_at": new_expiry.isoformat(),
                    "upgraded_at": now.isoformat()
                }}
            )
            
            message = f"Upgraded to {tier_info['name']} Premium!"
        else:
            # Same tier - extend
            await db.users.update_one(
                {"id": current_user["id"]},
                {"$inc": {"realum_balance": -price}}
            )
            
            await db.premium_subscriptions.update_one(
                {"id": existing["id"]},
                {"$set": {"expires_at": new_expiry.isoformat()}}
            )
            
            message = f"Extended {tier_info['name']} Premium by {duration_days} days!"
    else:
        # New subscription
        await db.users.update_one(
            {"id": current_user["id"]},
            {"$inc": {"realum_balance": -price}}
        )
        
        expires_at = now + timedelta(days=duration_days)
        
        subscription = {
            "id": str(uuid.uuid4()),
            "user_id": current_user["id"],
            "username": current_user["username"],
            "tier": data.tier,
            "duration": data.duration,
            "price_paid": price,
            "status": "active",
            "subscribed_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "auto_renew": False
        }
        await db.premium_subscriptions.insert_one(subscription)
        
        message = f"Welcome to {tier_info['name']} Premium!"
    
    # Add premium badge
    badge_name = tier_info["benefits"].get("exclusive_badge")
    if badge_name:
        await db.users.update_one(
            {"id": current_user["id"]},
            {"$addToSet": {"badges": badge_name}}
        )
    
    return {
        "message": message,
        "tier": data.tier,
        "tier_name": tier_info["name"],
        "benefits": tier_info["benefits"],
        "duration_days": duration_days
    }


@router.post("/claim-daily")
async def claim_daily_bonus(current_user: dict = Depends(get_current_user)):
    """Claim daily premium bonus"""
    bonus = await give_daily_premium_bonus(current_user["id"])
    
    if bonus == 0:
        subscription = await get_user_premium_status(current_user["id"])
        if not subscription:
            raise HTTPException(status_code=403, detail="Premium membership required")
        raise HTTPException(status_code=400, detail="Daily bonus already claimed today")
    
    return {
        "message": f"Claimed {bonus} RLM daily bonus!",
        "bonus_amount": bonus
    }


@router.post("/toggle-auto-renew")
async def toggle_auto_renew(current_user: dict = Depends(get_current_user)):
    """Toggle auto-renewal for subscription"""
    subscription = await get_user_premium_status(current_user["id"])
    
    if not subscription:
        raise HTTPException(status_code=404, detail="No active subscription")
    
    new_status = not subscription.get("auto_renew", False)
    
    await db.premium_subscriptions.update_one(
        {"id": subscription["id"]},
        {"$set": {"auto_renew": new_status}}
    )
    
    return {
        "auto_renew": new_status,
        "message": f"Auto-renewal {'enabled' if new_status else 'disabled'}"
    }


@router.post("/cancel")
async def cancel_subscription(current_user: dict = Depends(get_current_user)):
    """Cancel premium subscription (keeps benefits until expiry)"""
    subscription = await get_user_premium_status(current_user["id"])
    
    if not subscription:
        raise HTTPException(status_code=404, detail="No active subscription")
    
    await db.premium_subscriptions.update_one(
        {"id": subscription["id"]},
        {"$set": {
            "auto_renew": False,
            "cancelled_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {
        "message": "Subscription cancelled. Benefits will remain active until expiry.",
        "expires_at": subscription["expires_at"]
    }


# ============== EXCLUSIVE CONTENT ==============

@router.get("/exclusive-items")
async def get_exclusive_items(current_user: dict = Depends(get_current_user)):
    """Get premium exclusive items user can access"""
    subscription = await get_user_premium_status(current_user["id"])
    
    if not subscription:
        return {
            "available_items": [],
            "locked_items": PREMIUM_EXCLUSIVE_ITEMS,
            "message": "Subscribe to unlock exclusive items!"
        }
    
    user_tier = subscription["tier"]
    tier_order = list(PREMIUM_TIERS.keys())
    user_tier_index = tier_order.index(user_tier)
    
    available = []
    locked = []
    
    for item in PREMIUM_EXCLUSIVE_ITEMS:
        item_tier_index = tier_order.index(item["tier"])
        if item_tier_index <= user_tier_index:
            available.append(item)
        else:
            locked.append(item)
    
    return {
        "available_items": available,
        "locked_items": locked,
        "user_tier": user_tier
    }


# ============== STATISTICS ==============

@router.get("/statistics")
async def get_premium_statistics():
    """Get premium subscription statistics (public)"""
    total_active = await db.premium_subscriptions.count_documents({"status": "active"})
    
    tier_counts = {}
    for tier in PREMIUM_TIERS.keys():
        count = await db.premium_subscriptions.count_documents({
            "tier": tier,
            "status": "active"
        })
        tier_counts[tier] = count
    
    return {
        "total_premium_members": total_active,
        "members_by_tier": tier_counts
    }
