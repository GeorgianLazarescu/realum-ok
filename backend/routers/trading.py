"""
REALUM P2P Trading & Auction House
Direct trading between players and auction system
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import uuid

router = APIRouter(prefix="/api/trading", tags=["P2P Trading & Auctions"])

from core.database import db
from core.auth import get_current_user
from core.utils import serialize_doc


# ============== CONSTANTS ==============

# Trade offer expiration (hours)
TRADE_OFFER_EXPIRY_HOURS = 24

# Auction settings
AUCTION_MIN_DURATION_HOURS = 1
AUCTION_MAX_DURATION_HOURS = 168  # 7 days
AUCTION_FEE_PERCENT = 2.5  # 2.5% listing fee

# Item categories for trading
ITEM_CATEGORIES = [
    "collectibles",
    "equipment",
    "resources",
    "cosmetics",
    "property_deeds",
    "company_shares",
    "other"
]


# ============== MODELS ==============

class CreateTradeOfferRequest(BaseModel):
    target_username: str
    offer_rlm: float = 0
    offer_items: List[str] = []  # Item IDs
    request_rlm: float = 0
    request_items: List[str] = []
    message: Optional[str] = None

class CreateAuctionRequest(BaseModel):
    item_id: str
    item_name: str
    item_type: str
    starting_price: float = Field(..., gt=0)
    buyout_price: Optional[float] = None
    duration_hours: int = Field(..., ge=AUCTION_MIN_DURATION_HOURS, le=AUCTION_MAX_DURATION_HOURS)
    description: Optional[str] = None

class PlaceBidRequest(BaseModel):
    amount: float = Field(..., gt=0)


# ============== P2P TRADING ENDPOINTS ==============

@router.post("/offers/create")
async def create_trade_offer(
    data: CreateTradeOfferRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create a trade offer to another player"""
    # Find target user
    target = await db.users.find_one({"username": data.target_username})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    
    if target["id"] == current_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot trade with yourself")
    
    # Validate offer
    if data.offer_rlm <= 0 and not data.offer_items and data.request_rlm <= 0 and not data.request_items:
        raise HTTPException(status_code=400, detail="Trade must include something")
    
    # Check RLM balance
    if data.offer_rlm > 0 and current_user.get("realum_balance", 0) < data.offer_rlm:
        raise HTTPException(status_code=400, detail="Insufficient RLM balance")
    
    # Verify ownership of offered items
    for item_id in data.offer_items:
        item = await db.user_inventory.find_one({
            "id": item_id,
            "user_id": current_user["id"]
        })
        if not item:
            raise HTTPException(status_code=400, detail=f"You don't own item {item_id}")
    
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=TRADE_OFFER_EXPIRY_HOURS)
    
    # Lock offered RLM
    if data.offer_rlm > 0:
        await db.users.update_one(
            {"id": current_user["id"]},
            {"$inc": {"realum_balance": -data.offer_rlm, "locked_balance": data.offer_rlm}}
        )
    
    trade_offer = {
        "id": str(uuid.uuid4()),
        "sender_id": current_user["id"],
        "sender_username": current_user["username"],
        "recipient_id": target["id"],
        "recipient_username": target["username"],
        "offer_rlm": data.offer_rlm,
        "offer_items": data.offer_items,
        "request_rlm": data.request_rlm,
        "request_items": data.request_items,
        "message": data.message,
        "status": "pending",
        "created_at": now.isoformat(),
        "expires_at": expires_at.isoformat()
    }
    await db.trade_offers.insert_one(trade_offer)
    
    # Notify recipient
    await db.notifications.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": target["id"],
        "type": "trade_offer",
        "title": "Ofertă de Schimb",
        "message": f"{current_user['username']} ți-a trimis o ofertă de schimb",
        "data": {"offer_id": trade_offer["id"]},
        "read": False,
        "created_at": now.isoformat()
    })
    
    return {"offer": serialize_doc(trade_offer), "message": "Trade offer sent!"}


@router.get("/offers/incoming")
async def get_incoming_offers(current_user: dict = Depends(get_current_user)):
    """Get trade offers received"""
    offers = await db.trade_offers.find({
        "recipient_id": current_user["id"],
        "status": "pending",
        "expires_at": {"$gt": datetime.now(timezone.utc).isoformat()}
    }, {"_id": 0}).sort("created_at", -1).to_list(50)
    
    return {"offers": offers}


@router.get("/offers/outgoing")
async def get_outgoing_offers(current_user: dict = Depends(get_current_user)):
    """Get trade offers sent"""
    offers = await db.trade_offers.find({
        "sender_id": current_user["id"],
        "status": "pending"
    }, {"_id": 0}).sort("created_at", -1).to_list(50)
    
    return {"offers": offers}


@router.post("/offers/{offer_id}/accept")
async def accept_trade_offer(
    offer_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Accept a trade offer"""
    offer = await db.trade_offers.find_one({
        "id": offer_id,
        "recipient_id": current_user["id"],
        "status": "pending"
    })
    
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    
    # Check expiration
    if offer["expires_at"] < datetime.now(timezone.utc).isoformat():
        await db.trade_offers.update_one({"id": offer_id}, {"$set": {"status": "expired"}})
        raise HTTPException(status_code=400, detail="Offer has expired")
    
    # Verify recipient can fulfill their side
    if offer["request_rlm"] > 0 and current_user.get("realum_balance", 0) < offer["request_rlm"]:
        raise HTTPException(status_code=400, detail="Insufficient RLM to complete trade")
    
    for item_id in offer["request_items"]:
        item = await db.user_inventory.find_one({
            "id": item_id,
            "user_id": current_user["id"]
        })
        if not item:
            raise HTTPException(status_code=400, detail=f"You don't own requested item {item_id}")
    
    # Execute trade
    now = datetime.now(timezone.utc)
    
    # Transfer RLM
    if offer["offer_rlm"] > 0:
        # Unlock sender's RLM and transfer to recipient
        await db.users.update_one(
            {"id": offer["sender_id"]},
            {"$inc": {"locked_balance": -offer["offer_rlm"]}}
        )
        await db.users.update_one(
            {"id": current_user["id"]},
            {"$inc": {"realum_balance": offer["offer_rlm"]}}
        )
    
    if offer["request_rlm"] > 0:
        await db.users.update_one(
            {"id": current_user["id"]},
            {"$inc": {"realum_balance": -offer["request_rlm"]}}
        )
        await db.users.update_one(
            {"id": offer["sender_id"]},
            {"$inc": {"realum_balance": offer["request_rlm"]}}
        )
    
    # Transfer items
    for item_id in offer["offer_items"]:
        await db.user_inventory.update_one(
            {"id": item_id},
            {"$set": {"user_id": current_user["id"]}}
        )
    
    for item_id in offer["request_items"]:
        await db.user_inventory.update_one(
            {"id": item_id},
            {"$set": {"user_id": offer["sender_id"]}}
        )
    
    # Update offer status
    await db.trade_offers.update_one(
        {"id": offer_id},
        {"$set": {"status": "completed", "completed_at": now.isoformat()}}
    )
    
    # Notify sender
    await db.notifications.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": offer["sender_id"],
        "type": "trade_completed",
        "title": "Schimb Finalizat!",
        "message": f"{current_user['username']} a acceptat oferta ta de schimb",
        "read": False,
        "created_at": now.isoformat()
    })
    
    return {"message": "Trade completed successfully!"}


@router.post("/offers/{offer_id}/decline")
async def decline_trade_offer(
    offer_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Decline a trade offer"""
    offer = await db.trade_offers.find_one({
        "id": offer_id,
        "recipient_id": current_user["id"],
        "status": "pending"
    })
    
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    
    # Unlock sender's RLM
    if offer["offer_rlm"] > 0:
        await db.users.update_one(
            {"id": offer["sender_id"]},
            {"$inc": {"locked_balance": -offer["offer_rlm"], "realum_balance": offer["offer_rlm"]}}
        )
    
    await db.trade_offers.update_one(
        {"id": offer_id},
        {"$set": {"status": "declined", "declined_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"message": "Trade offer declined"}


@router.post("/offers/{offer_id}/cancel")
async def cancel_trade_offer(
    offer_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Cancel your own trade offer"""
    offer = await db.trade_offers.find_one({
        "id": offer_id,
        "sender_id": current_user["id"],
        "status": "pending"
    })
    
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    
    # Unlock RLM
    if offer["offer_rlm"] > 0:
        await db.users.update_one(
            {"id": current_user["id"]},
            {"$inc": {"locked_balance": -offer["offer_rlm"], "realum_balance": offer["offer_rlm"]}}
        )
    
    await db.trade_offers.update_one(
        {"id": offer_id},
        {"$set": {"status": "cancelled"}}
    )
    
    return {"message": "Trade offer cancelled"}


# ============== AUCTION HOUSE ENDPOINTS ==============

@router.get("/auctions")
async def list_auctions(
    category: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "ending_soon",  # ending_soon, price_low, price_high, newest
    limit: int = 50
):
    """List active auctions"""
    query = {
        "status": "active",
        "ends_at": {"$gt": datetime.now(timezone.utc).isoformat()}
    }
    
    if category:
        query["item_type"] = category
    
    if search:
        query["item_name"] = {"$regex": search, "$options": "i"}
    
    sort_options = {
        "ending_soon": [("ends_at", 1)],
        "price_low": [("current_price", 1)],
        "price_high": [("current_price", -1)],
        "newest": [("created_at", -1)]
    }
    
    auctions = await db.auctions.find(
        query,
        {"_id": 0}
    ).sort(sort_options.get(sort_by, [("ends_at", 1)])).limit(limit).to_list(limit)
    
    return {"auctions": auctions, "categories": ITEM_CATEGORIES}


@router.post("/auctions/create")
async def create_auction(
    data: CreateAuctionRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create a new auction"""
    # Verify item ownership
    item = await db.user_inventory.find_one({
        "id": data.item_id,
        "user_id": current_user["id"]
    })
    
    if not item:
        raise HTTPException(status_code=400, detail="You don't own this item")
    
    # Calculate listing fee
    listing_fee = data.starting_price * (AUCTION_FEE_PERCENT / 100)
    
    if current_user.get("realum_balance", 0) < listing_fee:
        raise HTTPException(status_code=400, detail=f"Need {listing_fee} RLM for listing fee")
    
    # Deduct listing fee
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$inc": {"realum_balance": -listing_fee}}
    )
    
    # Lock item
    await db.user_inventory.update_one(
        {"id": data.item_id},
        {"$set": {"locked": True, "locked_reason": "auction"}}
    )
    
    now = datetime.now(timezone.utc)
    ends_at = now + timedelta(hours=data.duration_hours)
    
    auction = {
        "id": str(uuid.uuid4()),
        "seller_id": current_user["id"],
        "seller_username": current_user["username"],
        "item_id": data.item_id,
        "item_name": data.item_name,
        "item_type": data.item_type,
        "description": data.description,
        "starting_price": data.starting_price,
        "current_price": data.starting_price,
        "buyout_price": data.buyout_price,
        "highest_bidder_id": None,
        "highest_bidder_username": None,
        "bid_count": 0,
        "status": "active",
        "listing_fee": listing_fee,
        "created_at": now.isoformat(),
        "ends_at": ends_at.isoformat()
    }
    await db.auctions.insert_one(auction)
    
    return {"auction": serialize_doc(auction), "message": "Auction created!"}


@router.get("/auctions/{auction_id}")
async def get_auction_details(auction_id: str):
    """Get auction details and bid history"""
    auction = await db.auctions.find_one({"id": auction_id}, {"_id": 0})
    if not auction:
        raise HTTPException(status_code=404, detail="Auction not found")
    
    bids = await db.auction_bids.find(
        {"auction_id": auction_id},
        {"_id": 0}
    ).sort("amount", -1).limit(20).to_list(20)
    
    return {"auction": auction, "bids": bids}


@router.post("/auctions/{auction_id}/bid")
async def place_bid(
    auction_id: str,
    data: PlaceBidRequest,
    current_user: dict = Depends(get_current_user)
):
    """Place a bid on an auction"""
    auction = await db.auctions.find_one({
        "id": auction_id,
        "status": "active"
    })
    
    if not auction:
        raise HTTPException(status_code=404, detail="Auction not found or ended")
    
    if auction["ends_at"] < datetime.now(timezone.utc).isoformat():
        raise HTTPException(status_code=400, detail="Auction has ended")
    
    if auction["seller_id"] == current_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot bid on your own auction")
    
    # Bid must be higher than current
    min_bid = auction["current_price"] * 1.05  # At least 5% higher
    if data.amount < min_bid:
        raise HTTPException(status_code=400, detail=f"Bid must be at least {min_bid:.2f} RLM")
    
    # Check balance
    if current_user.get("realum_balance", 0) < data.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    # Refund previous highest bidder
    if auction["highest_bidder_id"]:
        await db.users.update_one(
            {"id": auction["highest_bidder_id"]},
            {"$inc": {"locked_balance": -auction["current_price"], "realum_balance": auction["current_price"]}}
        )
    
    # Lock new bid amount
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$inc": {"realum_balance": -data.amount, "locked_balance": data.amount}}
    )
    
    now = datetime.now(timezone.utc)
    
    # Record bid
    bid = {
        "id": str(uuid.uuid4()),
        "auction_id": auction_id,
        "bidder_id": current_user["id"],
        "bidder_username": current_user["username"],
        "amount": data.amount,
        "created_at": now.isoformat()
    }
    await db.auction_bids.insert_one(bid)
    
    # Update auction
    update_data = {
        "current_price": data.amount,
        "highest_bidder_id": current_user["id"],
        "highest_bidder_username": current_user["username"],
        "bid_count": auction["bid_count"] + 1
    }
    
    # Extend auction if bid in last 5 minutes
    if auction["ends_at"] < (now + timedelta(minutes=5)).isoformat():
        update_data["ends_at"] = (now + timedelta(minutes=5)).isoformat()
    
    await db.auctions.update_one({"id": auction_id}, {"$set": update_data})
    
    return {"message": f"Bid of {data.amount} RLM placed!", "bid": serialize_doc(bid)}


@router.post("/auctions/{auction_id}/buyout")
async def buyout_auction(
    auction_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Buy item immediately at buyout price"""
    auction = await db.auctions.find_one({
        "id": auction_id,
        "status": "active"
    })
    
    if not auction:
        raise HTTPException(status_code=404, detail="Auction not found")
    
    if not auction.get("buyout_price"):
        raise HTTPException(status_code=400, detail="No buyout price set")
    
    if auction["seller_id"] == current_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot buyout your own auction")
    
    buyout = auction["buyout_price"]
    
    if current_user.get("realum_balance", 0) < buyout:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    # Refund previous highest bidder
    if auction["highest_bidder_id"]:
        await db.users.update_one(
            {"id": auction["highest_bidder_id"]},
            {"$inc": {"locked_balance": -auction["current_price"], "realum_balance": auction["current_price"]}}
        )
    
    now = datetime.now(timezone.utc)
    
    # Transfer payment
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$inc": {"realum_balance": -buyout}}
    )
    await db.users.update_one(
        {"id": auction["seller_id"]},
        {"$inc": {"realum_balance": buyout}}
    )
    
    # Transfer item
    await db.user_inventory.update_one(
        {"id": auction["item_id"]},
        {"$set": {"user_id": current_user["id"], "locked": False, "locked_reason": None}}
    )
    
    # Complete auction
    await db.auctions.update_one(
        {"id": auction_id},
        {"$set": {
            "status": "completed",
            "winner_id": current_user["id"],
            "winner_username": current_user["username"],
            "final_price": buyout,
            "completed_at": now.isoformat()
        }}
    )
    
    return {"message": f"Item purchased for {buyout} RLM!"}


@router.get("/my-auctions")
async def get_my_auctions(current_user: dict = Depends(get_current_user)):
    """Get user's auctions (selling and bidding)"""
    selling = await db.auctions.find(
        {"seller_id": current_user["id"]},
        {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    
    bidding = await db.auctions.find(
        {"highest_bidder_id": current_user["id"], "status": "active"},
        {"_id": 0}
    ).to_list(50)
    
    return {"selling": selling, "bidding": bidding}
