"""
REALUM Real Estate System
Virtual land, properties, and rental income
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import uuid
import random

router = APIRouter(prefix="/api/realestate", tags=["Real Estate"])

from core.database import db
from core.auth import get_current_user
from core.utils import serialize_doc


# ============== CONSTANTS ==============

# Property types and base prices
PROPERTY_TYPES = {
    "apartment": {
        "name": "Apartament",
        "base_price": 500,
        "rent_rate": 0.05,  # 5% monthly rent
        "maintenance": 0.01,  # 1% monthly maintenance
        "max_per_zone": 100
    },
    "house": {
        "name": "Casă",
        "base_price": 1500,
        "rent_rate": 0.04,
        "maintenance": 0.015,
        "max_per_zone": 50
    },
    "villa": {
        "name": "Vilă",
        "base_price": 5000,
        "rent_rate": 0.035,
        "maintenance": 0.02,
        "max_per_zone": 20
    },
    "office": {
        "name": "Birou",
        "base_price": 2000,
        "rent_rate": 0.06,
        "maintenance": 0.012,
        "max_per_zone": 40
    },
    "shop": {
        "name": "Magazin",
        "base_price": 1000,
        "rent_rate": 0.07,
        "maintenance": 0.015,
        "max_per_zone": 60
    },
    "warehouse": {
        "name": "Depozit",
        "base_price": 800,
        "rent_rate": 0.04,
        "maintenance": 0.008,
        "max_per_zone": 30
    },
    "land": {
        "name": "Teren",
        "base_price": 300,
        "rent_rate": 0.02,
        "maintenance": 0.005,
        "max_per_zone": 200
    }
}

# Zones from politics module
REALUM_ZONES = [
    {"id": "learning_zone", "name": "Learning Zone", "city": "Oxford, UK", "price_multiplier": 1.2},
    {"id": "jobs_hub", "name": "Jobs Hub", "city": "San Francisco, USA", "price_multiplier": 1.5},
    {"id": "marketplace", "name": "Marketplace", "city": "Dubai, UAE", "price_multiplier": 1.8},
    {"id": "social_plaza", "name": "Social Plaza", "city": "Tokyo, Japan", "price_multiplier": 1.4},
    {"id": "treasury", "name": "Treasury", "city": "Singapore", "price_multiplier": 2.0},
    {"id": "dao_hall", "name": "DAO Hall", "city": "Zurich, Switzerland", "price_multiplier": 1.6}
]

# Property tax rate (monthly)
PROPERTY_TAX_RATE = 0.02  # 2% monthly


# ============== MODELS ==============

class BuyPropertyRequest(BaseModel):
    property_type: str
    zone_id: str
    custom_name: Optional[str] = None

class SetRentRequest(BaseModel):
    rent_amount: float = Field(..., gt=0)

class RentPropertyRequest(BaseModel):
    duration_months: int = Field(..., ge=1, le=12)


# ============== HELPER FUNCTIONS ==============

def calculate_property_price(property_type: str, zone_id: str) -> float:
    """Calculate property price based on type and zone"""
    type_info = PROPERTY_TYPES.get(property_type)
    zone_info = next((z for z in REALUM_ZONES if z["id"] == zone_id), None)
    
    if not type_info or not zone_info:
        return 0
    
    return type_info["base_price"] * zone_info["price_multiplier"]

async def process_rent_payments():
    """Process monthly rent payments (called by scheduler)"""
    now = datetime.now(timezone.utc)
    
    # Find all active rentals
    rentals = await db.property_rentals.find({
        "status": "active",
        "next_payment_due": {"$lte": now.isoformat()}
    }).to_list(1000)
    
    for rental in rentals:
        # Check if tenant has funds
        tenant = await db.users.find_one({"id": rental["tenant_id"]})
        if not tenant or tenant.get("realum_balance", 0) < rental["monthly_rent"]:
            # Evict tenant
            await db.property_rentals.update_one(
                {"id": rental["id"]},
                {"$set": {"status": "evicted", "ended_at": now.isoformat()}}
            )
            await db.properties.update_one(
                {"id": rental["property_id"]},
                {"$set": {"is_rented": False, "current_tenant": None}}
            )
            continue
        
        # Process payment
        await db.users.update_one(
            {"id": rental["tenant_id"]},
            {"$inc": {"realum_balance": -rental["monthly_rent"]}}
        )
        
        # Pay landlord (minus property tax)
        tax = rental["monthly_rent"] * PROPERTY_TAX_RATE
        landlord_payment = rental["monthly_rent"] - tax
        
        await db.users.update_one(
            {"id": rental["landlord_id"]},
            {"$inc": {"realum_balance": landlord_payment}}
        )
        
        # Update next payment date
        next_due = datetime.fromisoformat(rental["next_payment_due"].replace("Z", "+00:00")) + timedelta(days=30)
        
        # Check if rental period ended
        if next_due > datetime.fromisoformat(rental["end_date"].replace("Z", "+00:00")):
            await db.property_rentals.update_one(
                {"id": rental["id"]},
                {"$set": {"status": "completed", "ended_at": now.isoformat()}}
            )
            await db.properties.update_one(
                {"id": rental["property_id"]},
                {"$set": {"is_rented": False, "current_tenant": None}}
            )
        else:
            await db.property_rentals.update_one(
                {"id": rental["id"]},
                {"$set": {"next_payment_due": next_due.isoformat()}}
            )


# ============== PROPERTY ENDPOINTS ==============

@router.get("/market")
async def get_property_market():
    """Get property market overview"""
    # Get properties for sale
    for_sale = await db.properties.find(
        {"for_sale": True},
        {"_id": 0}
    ).sort("price", 1).limit(50).to_list(50)
    
    # Get available to buy (new)
    available = []
    for zone in REALUM_ZONES:
        for ptype, pinfo in PROPERTY_TYPES.items():
            # Count existing properties
            count = await db.properties.count_documents({
                "zone_id": zone["id"],
                "property_type": ptype
            })
            
            if count < pinfo["max_per_zone"]:
                price = calculate_property_price(ptype, zone["id"])
                available.append({
                    "property_type": ptype,
                    "type_name": pinfo["name"],
                    "zone_id": zone["id"],
                    "zone_name": zone["name"],
                    "price": price,
                    "rent_rate": pinfo["rent_rate"],
                    "available": pinfo["max_per_zone"] - count
                })
    
    return {
        "for_sale": for_sale,
        "available_new": available,
        "property_types": PROPERTY_TYPES,
        "zones": REALUM_ZONES
    }


@router.get("/my-properties")
async def get_my_properties(current_user: dict = Depends(get_current_user)):
    """Get user's properties"""
    properties = await db.properties.find(
        {"owner_id": current_user["id"]},
        {"_id": 0}
    ).to_list(100)
    
    total_value = sum(p.get("current_value", p.get("purchase_price", 0)) for p in properties)
    monthly_rent_income = sum(
        p.get("rent_amount", 0) for p in properties if p.get("is_rented")
    )
    
    return {
        "properties": properties,
        "total_count": len(properties),
        "total_value": round(total_value, 2),
        "monthly_rent_income": round(monthly_rent_income, 2)
    }


@router.post("/buy")
async def buy_property(
    data: BuyPropertyRequest,
    current_user: dict = Depends(get_current_user)
):
    """Buy a new property"""
    if data.property_type not in PROPERTY_TYPES:
        raise HTTPException(status_code=400, detail="Invalid property type")
    
    zone = next((z for z in REALUM_ZONES if z["id"] == data.zone_id), None)
    if not zone:
        raise HTTPException(status_code=400, detail="Invalid zone")
    
    type_info = PROPERTY_TYPES[data.property_type]
    
    # Check availability
    count = await db.properties.count_documents({
        "zone_id": data.zone_id,
        "property_type": data.property_type
    })
    if count >= type_info["max_per_zone"]:
        raise HTTPException(status_code=400, detail="No more properties of this type available in this zone")
    
    price = calculate_property_price(data.property_type, data.zone_id)
    
    if current_user.get("realum_balance", 0) < price:
        raise HTTPException(status_code=400, detail=f"Insufficient funds. Need {price} RLM")
    
    # Deduct payment
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$inc": {"realum_balance": -price}}
    )
    
    now = datetime.now(timezone.utc)
    
    property_doc = {
        "id": str(uuid.uuid4()),
        "property_type": data.property_type,
        "type_name": type_info["name"],
        "zone_id": data.zone_id,
        "zone_name": zone["name"],
        "name": data.custom_name or f"{type_info['name']} în {zone['name']}",
        "owner_id": current_user["id"],
        "owner_username": current_user["username"],
        "purchase_price": price,
        "current_value": price,
        "rent_rate": type_info["rent_rate"],
        "maintenance_rate": type_info["maintenance"],
        "rent_amount": 0,
        "is_rented": False,
        "for_sale": False,
        "current_tenant": None,
        "purchased_at": now.isoformat(),
        "last_rent_collected": None
    }
    await db.properties.insert_one(property_doc)
    
    return {
        "property": serialize_doc(property_doc),
        "message": f"Purchased {type_info['name']} in {zone['name']} for {price} RLM!"
    }


@router.post("/{property_id}/sell")
async def list_for_sale(
    property_id: str,
    price: float,
    current_user: dict = Depends(get_current_user)
):
    """List property for sale"""
    property_doc = await db.properties.find_one({
        "id": property_id,
        "owner_id": current_user["id"]
    })
    
    if not property_doc:
        raise HTTPException(status_code=404, detail="Property not found")
    
    if property_doc.get("is_rented"):
        raise HTTPException(status_code=400, detail="Cannot sell rented property")
    
    await db.properties.update_one(
        {"id": property_id},
        {"$set": {"for_sale": True, "sale_price": price}}
    )
    
    return {"message": f"Property listed for sale at {price} RLM"}


@router.post("/{property_id}/buy-from-owner")
async def buy_from_owner(
    property_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Buy property from another player"""
    property_doc = await db.properties.find_one({
        "id": property_id,
        "for_sale": True
    })
    
    if not property_doc:
        raise HTTPException(status_code=404, detail="Property not for sale")
    
    if property_doc["owner_id"] == current_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot buy your own property")
    
    price = property_doc.get("sale_price", property_doc["current_value"])
    
    if current_user.get("realum_balance", 0) < price:
        raise HTTPException(status_code=400, detail="Insufficient funds")
    
    # Transfer payment
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$inc": {"realum_balance": -price}}
    )
    
    # Pay seller (minus 5% transaction fee)
    seller_payment = price * 0.95
    await db.users.update_one(
        {"id": property_doc["owner_id"]},
        {"$inc": {"realum_balance": seller_payment}}
    )
    
    # Transfer ownership
    await db.properties.update_one(
        {"id": property_id},
        {"$set": {
            "owner_id": current_user["id"],
            "owner_username": current_user["username"],
            "for_sale": False,
            "sale_price": None,
            "current_value": price,
            "purchased_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": f"Property purchased for {price} RLM!"}


# ============== RENTAL ENDPOINTS ==============

@router.post("/{property_id}/set-rent")
async def set_rent_price(
    property_id: str,
    data: SetRentRequest,
    current_user: dict = Depends(get_current_user)
):
    """Set rent price for property"""
    property_doc = await db.properties.find_one({
        "id": property_id,
        "owner_id": current_user["id"]
    })
    
    if not property_doc:
        raise HTTPException(status_code=404, detail="Property not found")
    
    # Max rent is 10% of property value per month
    max_rent = property_doc["current_value"] * 0.1
    if data.rent_amount > max_rent:
        raise HTTPException(status_code=400, detail=f"Maximum rent is {max_rent} RLM/month")
    
    await db.properties.update_one(
        {"id": property_id},
        {"$set": {"rent_amount": data.rent_amount, "available_for_rent": True}}
    )
    
    return {"message": f"Rent set to {data.rent_amount} RLM/month"}


@router.get("/rentals")
async def get_available_rentals(zone_id: Optional[str] = None):
    """Get properties available for rent"""
    query = {"available_for_rent": True, "is_rented": False, "rent_amount": {"$gt": 0}}
    if zone_id:
        query["zone_id"] = zone_id
    
    rentals = await db.properties.find(query, {"_id": 0}).to_list(100)
    
    return {"available_rentals": rentals}


@router.post("/{property_id}/rent")
async def rent_property(
    property_id: str,
    data: RentPropertyRequest,
    current_user: dict = Depends(get_current_user)
):
    """Rent a property"""
    property_doc = await db.properties.find_one({
        "id": property_id,
        "available_for_rent": True,
        "is_rented": False
    })
    
    if not property_doc:
        raise HTTPException(status_code=404, detail="Property not available for rent")
    
    if property_doc["owner_id"] == current_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot rent your own property")
    
    # First month payment + deposit
    first_payment = property_doc["rent_amount"] * 2  # First month + deposit
    
    if current_user.get("realum_balance", 0) < first_payment:
        raise HTTPException(status_code=400, detail=f"Need {first_payment} RLM (first month + deposit)")
    
    # Deduct payment
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$inc": {"realum_balance": -first_payment}}
    )
    
    # Pay landlord first month
    tax = property_doc["rent_amount"] * PROPERTY_TAX_RATE
    landlord_payment = property_doc["rent_amount"] - tax
    await db.users.update_one(
        {"id": property_doc["owner_id"]},
        {"$inc": {"realum_balance": landlord_payment}}
    )
    
    now = datetime.now(timezone.utc)
    end_date = now + timedelta(days=30 * data.duration_months)
    next_payment = now + timedelta(days=30)
    
    rental = {
        "id": str(uuid.uuid4()),
        "property_id": property_id,
        "property_name": property_doc["name"],
        "tenant_id": current_user["id"],
        "tenant_username": current_user["username"],
        "landlord_id": property_doc["owner_id"],
        "monthly_rent": property_doc["rent_amount"],
        "deposit": property_doc["rent_amount"],
        "duration_months": data.duration_months,
        "start_date": now.isoformat(),
        "end_date": end_date.isoformat(),
        "next_payment_due": next_payment.isoformat(),
        "status": "active"
    }
    await db.property_rentals.insert_one(rental)
    
    # Update property
    await db.properties.update_one(
        {"id": property_id},
        {"$set": {
            "is_rented": True,
            "current_tenant": current_user["id"],
            "current_tenant_username": current_user["username"]
        }}
    )
    
    return {
        "rental": serialize_doc(rental),
        "message": f"Rented {property_doc['name']} for {data.duration_months} months!"
    }


@router.get("/my-rentals")
async def get_my_rentals(current_user: dict = Depends(get_current_user)):
    """Get properties user is renting"""
    rentals = await db.property_rentals.find(
        {"tenant_id": current_user["id"], "status": "active"},
        {"_id": 0}
    ).to_list(50)
    
    return {"rentals": rentals}


# ============== STATISTICS ==============

@router.get("/statistics")
async def get_real_estate_statistics():
    """Get real estate market statistics"""
    # Total properties by zone
    zone_stats = []
    for zone in REALUM_ZONES:
        count = await db.properties.count_documents({"zone_id": zone["id"]})
        total_value = 0
        properties = await db.properties.find({"zone_id": zone["id"]}).to_list(1000)
        total_value = sum(p.get("current_value", 0) for p in properties)
        
        zone_stats.append({
            "zone": zone,
            "property_count": count,
            "total_value": total_value
        })
    
    # Top property owners
    pipeline = [
        {"$group": {
            "_id": "$owner_id",
            "count": {"$sum": 1},
            "total_value": {"$sum": "$current_value"}
        }},
        {"$sort": {"total_value": -1}},
        {"$limit": 10}
    ]
    top_owners = await db.properties.aggregate(pipeline).to_list(10)
    
    for owner in top_owners:
        user = await db.users.find_one({"id": owner["_id"]})
        owner["username"] = user.get("username", "Unknown") if user else "Unknown"
    
    return {
        "zone_statistics": zone_stats,
        "top_owners": top_owners,
        "total_properties": await db.properties.count_documents({}),
        "properties_for_rent": await db.properties.count_documents({"available_for_rent": True, "is_rented": False}),
        "properties_for_sale": await db.properties.count_documents({"for_sale": True})
    }
