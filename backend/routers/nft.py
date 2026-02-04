from fastapi import APIRouter, HTTPException, Depends, Query
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from pydantic import BaseModel
import uuid

from core.database import db
from core.auth import get_current_user, require_admin

router = APIRouter(prefix="/api/nft", tags=["NFT Marketplace"])

# NFT Categories
NFT_CATEGORIES = ["achievement", "badge", "artwork", "collectible", "course_certificate", "membership"]

class NFTCreate(BaseModel):
    name: str
    description: Optional[str] = None
    image_url: str
    category: str = "collectible"
    attributes: List[dict] = []  # [{trait_type, value}]
    max_supply: Optional[int] = None  # None = unlimited
    royalty_percent: float = 5.0  # Creator royalty on resales

class NFTListingCreate(BaseModel):
    nft_id: str
    price: float
    duration_days: int = 7

class NFTBid(BaseModel):
    listing_id: str
    amount: float

class NFTTransfer(BaseModel):
    nft_id: str
    to_user_id: str

# ==================== NFT CREATION ====================

@router.post("/mint")
async def mint_nft(
    nft: NFTCreate,
    current_user: dict = Depends(get_current_user)
):
    """Mint a new NFT"""
    try:
        if nft.category not in NFT_CATEGORIES:
            raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of: {NFT_CATEGORIES}")
        
        # Check minting cost (100 RLM)
        minting_cost = 100
        user = await db.users.find_one({"id": current_user["id"]})
        if not user or user.get("realum_balance", 0) < minting_cost:
            raise HTTPException(status_code=400, detail=f"Insufficient balance. Minting costs {minting_cost} RLM")
        
        nft_id = str(uuid.uuid4())
        token_id = await db.nfts.count_documents({}) + 1
        now = datetime.now(timezone.utc).isoformat()
        
        nft_data = {
            "id": nft_id,
            "token_id": token_id,
            "name": nft.name,
            "description": nft.description,
            "image_url": nft.image_url,
            "category": nft.category,
            "attributes": nft.attributes,
            "max_supply": nft.max_supply,
            "current_supply": 1,
            "royalty_percent": nft.royalty_percent,
            "creator_id": current_user["id"],
            "creator_username": current_user.get("username"),
            "owner_id": current_user["id"],
            "owner_username": current_user.get("username"),
            "is_listed": False,
            "mint_price": minting_cost,
            "last_sale_price": None,
            "total_sales": 0,
            "views": 0,
            "likes": 0,
            "minted_at": now,
            "created_at": now
        }
        
        # Deduct minting cost
        await db.users.update_one(
            {"id": current_user["id"]},
            {"$inc": {"realum_balance": -minting_cost}}
        )
        
        # Record transaction
        await db.nft_transactions.insert_one({
            "id": str(uuid.uuid4()),
            "nft_id": nft_id,
            "type": "mint",
            "from_user_id": None,
            "to_user_id": current_user["id"],
            "price": minting_cost,
            "timestamp": now
        })
        
        await db.nfts.insert_one(nft_data)
        nft_data.pop("_id", None)
        
        return {"message": "NFT minted successfully", "nft": nft_data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/mint-achievement/{achievement_key}")
async def mint_achievement_nft(
    achievement_key: str,
    current_user: dict = Depends(get_current_user)
):
    """Mint an achievement as NFT"""
    try:
        # Check if user has the achievement
        user_achievement = await db.user_achievements.find_one({
            "user_id": current_user["id"],
            "achievement_key": achievement_key,
            "earned": True
        })
        
        if not user_achievement:
            raise HTTPException(status_code=400, detail="Achievement not earned")
        
        # Check if already minted
        existing = await db.nfts.find_one({
            "category": "achievement",
            "attributes": {"$elemMatch": {"trait_type": "achievement_key", "value": achievement_key}},
            "creator_id": current_user["id"]
        })
        
        if existing:
            raise HTTPException(status_code=400, detail="Achievement already minted as NFT")
        
        # Get achievement details
        achievement = await db.achievements.find_one({"key": achievement_key})
        if not achievement:
            raise HTTPException(status_code=404, detail="Achievement not found")
        
        nft_id = str(uuid.uuid4())
        token_id = await db.nfts.count_documents({}) + 1
        now = datetime.now(timezone.utc).isoformat()
        
        nft_data = {
            "id": nft_id,
            "token_id": token_id,
            "name": f"Achievement: {achievement.get('name', achievement_key)}",
            "description": achievement.get("description", "A REALUM achievement"),
            "image_url": achievement.get("icon_url", "/achievements/default.png"),
            "category": "achievement",
            "attributes": [
                {"trait_type": "achievement_key", "value": achievement_key},
                {"trait_type": "tier", "value": achievement.get("tier", "bronze")},
                {"trait_type": "xp_reward", "value": achievement.get("xp_reward", 0)},
                {"trait_type": "earned_date", "value": user_achievement.get("earned_at", now)}
            ],
            "max_supply": 1,
            "current_supply": 1,
            "royalty_percent": 0,
            "creator_id": current_user["id"],
            "creator_username": current_user.get("username"),
            "owner_id": current_user["id"],
            "owner_username": current_user.get("username"),
            "is_listed": False,
            "mint_price": 0,
            "last_sale_price": None,
            "total_sales": 0,
            "views": 0,
            "likes": 0,
            "minted_at": now,
            "created_at": now
        }
        
        await db.nfts.insert_one(nft_data)
        nft_data.pop("_id", None)
        
        return {"message": "Achievement minted as NFT", "nft": nft_data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ==================== MARKETPLACE ====================

@router.get("/marketplace")
async def get_marketplace_listings(
    category: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    sort_by: str = "recent",  # recent, price_low, price_high, popular
    limit: int = 20,
    offset: int = 0
):
    """Get active marketplace listings"""
    try:
        now = datetime.now(timezone.utc).isoformat()
        
        query = {"status": "active", "expires_at": {"$gt": now}}
        
        if category:
            query["category"] = category
        if min_price is not None:
            query["price"] = {"$gte": min_price}
        if max_price is not None:
            query["price"] = {**query.get("price", {}), "$lte": max_price}
        
        sort_field = "created_at"
        sort_order = -1
        if sort_by == "price_low":
            sort_field = "price"
            sort_order = 1
        elif sort_by == "price_high":
            sort_field = "price"
            sort_order = -1
        elif sort_by == "popular":
            sort_field = "views"
            sort_order = -1
        
        listings = await db.nft_listings.find(
            query,
            {"_id": 0}
        ).sort(sort_field, sort_order).skip(offset).limit(limit).to_list(limit)
        
        # Get NFT details for each listing
        for listing in listings:
            nft = await db.nfts.find_one(
                {"id": listing["nft_id"]},
                {"_id": 0}
            )
            listing["nft"] = nft
        
        total = await db.nft_listings.count_documents(query)
        
        return {
            "listings": listings,
            "total": total,
            "has_more": offset + limit < total
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/list")
async def create_listing(
    listing: NFTListingCreate,
    current_user: dict = Depends(get_current_user)
):
    """List an NFT for sale"""
    try:
        # Verify ownership
        nft = await db.nfts.find_one({"id": listing.nft_id})
        if not nft:
            raise HTTPException(status_code=404, detail="NFT not found")
        if nft["owner_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="You don't own this NFT")
        if nft.get("is_listed"):
            raise HTTPException(status_code=400, detail="NFT already listed")
        
        if listing.price < 1:
            raise HTTPException(status_code=400, detail="Minimum price is 1 RLM")
        
        listing_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=listing.duration_days)
        
        listing_data = {
            "id": listing_id,
            "nft_id": listing.nft_id,
            "seller_id": current_user["id"],
            "seller_username": current_user.get("username"),
            "price": listing.price,
            "category": nft["category"],
            "status": "active",
            "views": 0,
            "bids": [],
            "created_at": now.isoformat(),
            "expires_at": expires_at.isoformat()
        }
        
        await db.nft_listings.insert_one(listing_data)
        
        # Mark NFT as listed
        await db.nfts.update_one(
            {"id": listing.nft_id},
            {"$set": {"is_listed": True, "listing_id": listing_id}}
        )
        
        listing_data.pop("_id", None)
        return {"message": "NFT listed for sale", "listing": listing_data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/list/{listing_id}")
async def cancel_listing(
    listing_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Cancel a listing"""
    try:
        listing = await db.nft_listings.find_one({"id": listing_id})
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found")
        if listing["seller_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Not your listing")
        
        await db.nft_listings.update_one(
            {"id": listing_id},
            {"$set": {"status": "cancelled"}}
        )
        
        await db.nfts.update_one(
            {"id": listing["nft_id"]},
            {"$set": {"is_listed": False}, "$unset": {"listing_id": ""}}
        )
        
        return {"message": "Listing cancelled"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/buy/{listing_id}")
async def buy_nft(
    listing_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Buy an NFT from a listing"""
    try:
        listing = await db.nft_listings.find_one({"id": listing_id, "status": "active"})
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found or not active")
        
        if listing["seller_id"] == current_user["id"]:
            raise HTTPException(status_code=400, detail="Cannot buy your own NFT")
        
        # Check buyer balance
        buyer = await db.users.find_one({"id": current_user["id"]})
        if not buyer or buyer.get("realum_balance", 0) < listing["price"]:
            raise HTTPException(status_code=400, detail="Insufficient balance")
        
        nft = await db.nfts.find_one({"id": listing["nft_id"]})
        if not nft:
            raise HTTPException(status_code=404, detail="NFT not found")
        
        now = datetime.now(timezone.utc).isoformat()
        price = listing["price"]
        
        # Calculate royalty
        royalty = price * (nft.get("royalty_percent", 0) / 100)
        seller_amount = price - royalty
        
        # Transfer funds
        await db.users.update_one(
            {"id": current_user["id"]},
            {"$inc": {"realum_balance": -price}}
        )
        await db.users.update_one(
            {"id": listing["seller_id"]},
            {"$inc": {"realum_balance": seller_amount}}
        )
        
        # Pay royalty to creator if different from seller
        if royalty > 0 and nft["creator_id"] != listing["seller_id"]:
            await db.users.update_one(
                {"id": nft["creator_id"]},
                {"$inc": {"realum_balance": royalty}}
            )
        
        # Transfer NFT ownership
        await db.nfts.update_one(
            {"id": listing["nft_id"]},
            {"$set": {
                "owner_id": current_user["id"],
                "owner_username": current_user.get("username"),
                "is_listed": False,
                "last_sale_price": price
            },
            "$inc": {"total_sales": 1},
            "$unset": {"listing_id": ""}}
        )
        
        # Update listing
        await db.nft_listings.update_one(
            {"id": listing_id},
            {"$set": {
                "status": "sold",
                "buyer_id": current_user["id"],
                "sold_at": now
            }}
        )
        
        # Record transaction
        await db.nft_transactions.insert_one({
            "id": str(uuid.uuid4()),
            "nft_id": listing["nft_id"],
            "listing_id": listing_id,
            "type": "sale",
            "from_user_id": listing["seller_id"],
            "to_user_id": current_user["id"],
            "price": price,
            "royalty_paid": royalty,
            "timestamp": now
        })
        
        return {
            "message": "NFT purchased successfully",
            "nft_id": listing["nft_id"],
            "price_paid": price,
            "royalty_paid": royalty
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ==================== NFT QUERIES ====================

@router.get("/my-nfts")
async def get_my_nfts(
    current_user: dict = Depends(get_current_user)
):
    """Get NFTs owned by current user"""
    try:
        nfts = await db.nfts.find(
            {"owner_id": current_user["id"]},
            {"_id": 0}
        ).sort("created_at", -1).to_list(100)
        
        return {"nfts": nfts, "count": len(nfts)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/created")
async def get_created_nfts(
    current_user: dict = Depends(get_current_user)
):
    """Get NFTs created by current user"""
    try:
        nfts = await db.nfts.find(
            {"creator_id": current_user["id"]},
            {"_id": 0}
        ).sort("created_at", -1).to_list(100)
        
        return {"nfts": nfts, "count": len(nfts)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/nft/{nft_id}")
async def get_nft_details(nft_id: str):
    """Get NFT details"""
    try:
        nft = await db.nfts.find_one({"id": nft_id}, {"_id": 0})
        if not nft:
            raise HTTPException(status_code=404, detail="NFT not found")
        
        # Get transaction history
        transactions = await db.nft_transactions.find(
            {"nft_id": nft_id},
            {"_id": 0}
        ).sort("timestamp", -1).limit(20).to_list(20)
        
        # Get active listing if any
        listing = None
        if nft.get("is_listed"):
            listing = await db.nft_listings.find_one(
                {"nft_id": nft_id, "status": "active"},
                {"_id": 0}
            )
        
        # Increment views
        await db.nfts.update_one({"id": nft_id}, {"$inc": {"views": 1}})
        
        return {
            "nft": nft,
            "listing": listing,
            "transaction_history": transactions
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/categories")
async def get_nft_categories():
    """Get NFT categories with counts"""
    try:
        pipeline = [
            {"$group": {"_id": "$category", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        results = await db.nfts.aggregate(pipeline).to_list(20)
        
        categories = [
            {"key": r["_id"], "name": r["_id"].replace("_", " ").title(), "count": r["count"]}
            for r in results
        ]
        
        return {"categories": categories}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/stats")
async def get_nft_stats():
    """Get NFT marketplace statistics"""
    try:
        total_nfts = await db.nfts.count_documents({})
        total_listings = await db.nft_listings.count_documents({"status": "active"})
        total_sales = await db.nft_transactions.count_documents({"type": "sale"})
        
        # Total volume
        pipeline = [
            {"$match": {"type": "sale"}},
            {"$group": {"_id": None, "total": {"$sum": "$price"}}}
        ]
        volume_result = await db.nft_transactions.aggregate(pipeline).to_list(1)
        total_volume = volume_result[0]["total"] if volume_result else 0
        
        # Floor price (lowest listing)
        floor = await db.nft_listings.find(
            {"status": "active"}
        ).sort("price", 1).limit(1).to_list(1)
        floor_price = floor[0]["price"] if floor else 0
        
        return {
            "stats": {
                "total_nfts": total_nfts,
                "active_listings": total_listings,
                "total_sales": total_sales,
                "total_volume": total_volume,
                "floor_price": floor_price
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/nft/{nft_id}/like")
async def like_nft(
    nft_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Like an NFT"""
    try:
        existing = await db.nft_likes.find_one({
            "nft_id": nft_id,
            "user_id": current_user["id"]
        })
        
        if existing:
            # Unlike
            await db.nft_likes.delete_one({"id": existing["id"]})
            await db.nfts.update_one({"id": nft_id}, {"$inc": {"likes": -1}})
            return {"message": "NFT unliked", "liked": False}
        else:
            # Like
            await db.nft_likes.insert_one({
                "id": str(uuid.uuid4()),
                "nft_id": nft_id,
                "user_id": current_user["id"],
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            await db.nfts.update_one({"id": nft_id}, {"$inc": {"likes": 1}})
            return {"message": "NFT liked", "liked": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/transfer")
async def transfer_nft(
    transfer: NFTTransfer,
    current_user: dict = Depends(get_current_user)
):
    """Transfer NFT to another user"""
    try:
        nft = await db.nfts.find_one({"id": transfer.nft_id})
        if not nft:
            raise HTTPException(status_code=404, detail="NFT not found")
        if nft["owner_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="You don't own this NFT")
        if nft.get("is_listed"):
            raise HTTPException(status_code=400, detail="Cannot transfer listed NFT")
        
        # Verify recipient exists
        recipient = await db.users.find_one({"id": transfer.to_user_id})
        if not recipient:
            raise HTTPException(status_code=404, detail="Recipient not found")
        
        now = datetime.now(timezone.utc).isoformat()
        
        await db.nfts.update_one(
            {"id": transfer.nft_id},
            {"$set": {
                "owner_id": transfer.to_user_id,
                "owner_username": recipient.get("username")
            }}
        )
        
        await db.nft_transactions.insert_one({
            "id": str(uuid.uuid4()),
            "nft_id": transfer.nft_id,
            "type": "transfer",
            "from_user_id": current_user["id"],
            "to_user_id": transfer.to_user_id,
            "price": 0,
            "timestamp": now
        })
        
        return {"message": "NFT transferred successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
