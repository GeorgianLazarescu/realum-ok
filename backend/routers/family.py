"""
REALUM Family System
Marriage, Divorce, and Children mechanics
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from enum import Enum
import uuid
import random

router = APIRouter(prefix="/api/family", tags=["Family System"])

from core.database import db
from core.auth import get_current_user


# ============== CONSTANTS ==============

MARRIAGE_COST = 50  # RLM cost to propose
WEDDING_COST = 200  # RLM cost for wedding ceremony
DIVORCE_COST = 100  # RLM cost for divorce
ADOPTION_COST = 150  # RLM cost to adopt
CHILD_CREATION_COST = 300  # RLM cost to have a child (married couples only)
DIVORCE_COOLDOWN_DAYS = 7  # Days before can remarry

# Couple bonuses
COUPLE_XP_BONUS = 1.10  # 10% XP bonus when working together
COUPLE_RLM_BONUS = 1.05  # 5% RLM bonus on jobs


# ============== MODELS ==============

class MarriageStatus(str, Enum):
    SINGLE = "single"
    ENGAGED = "engaged"
    MARRIED = "married"
    DIVORCED = "divorced"

class ProposalRequest(BaseModel):
    partner_id: str
    message: Optional[str] = "Will you marry me in REALUM?"

class ProposalResponse(BaseModel):
    proposal_id: str
    accept: bool

class ChildType(str, Enum):
    ADOPTED = "adopted"
    BIOLOGICAL = "biological"

class AdoptChildRequest(BaseModel):
    child_name: str
    child_gender: str  # "boy", "girl", "other"

class CreateChildRequest(BaseModel):
    child_name: str
    child_gender: str


# ============== HELPER FUNCTIONS ==============

def serialize_doc(doc):
    """Remove MongoDB _id and convert to serializable format"""
    if doc and "_id" in doc:
        del doc["_id"]
    return doc

async def get_user_marriage_status(user_id: str):
    """Get user's current marriage status"""
    marriage = await db.marriages.find_one({
        "$or": [
            {"partner1_id": user_id},
            {"partner2_id": user_id}
        ],
        "status": "active"
    })
    return marriage

async def check_can_marry(user_id: str):
    """Check if user can get married"""
    # Check if already married
    existing = await get_user_marriage_status(user_id)
    if existing:
        return False, "You are already married"
    
    # Check divorce cooldown
    last_divorce = await db.divorces.find_one(
        {"$or": [{"user1_id": user_id}, {"user2_id": user_id}]},
        sort=[("divorced_at", -1)]
    )
    
    if last_divorce:
        divorce_date = datetime.fromisoformat(last_divorce["divorced_at"].replace("Z", "+00:00"))
        cooldown_end = divorce_date + timedelta(days=DIVORCE_COOLDOWN_DAYS)
        if datetime.now(timezone.utc) < cooldown_end:
            days_left = (cooldown_end - datetime.now(timezone.utc)).days
            return False, f"Divorce cooldown: {days_left} days remaining"
    
    return True, "OK"


# ============== MARRIAGE ENDPOINTS ==============

@router.get("/status")
async def get_family_status(current_user: dict = Depends(get_current_user)):
    """Get user's family status including marriage and children"""
    user_id = current_user["id"]
    
    # Get marriage status
    marriage = await get_user_marriage_status(user_id)
    marriage_info = None
    partner_info = None
    
    if marriage:
        partner_id = marriage["partner2_id"] if marriage["partner1_id"] == user_id else marriage["partner1_id"]
        partner = await db.users.find_one({"id": partner_id}, {"_id": 0, "password_hash": 0})
        partner_info = {
            "id": partner["id"],
            "username": partner["username"],
            "avatar_url": partner.get("avatar_url")
        } if partner else None
        
        marriage_info = {
            "status": "married",
            "married_at": marriage["married_at"],
            "anniversary": marriage.get("anniversary"),
            "partner": partner_info
        }
    
    # Check for pending proposals
    pending_proposals = await db.proposals.find({
        "to_user_id": user_id,
        "status": "pending"
    }, {"_id": 0}).to_list(10)
    
    # Enrich proposals with sender info
    for proposal in pending_proposals:
        sender = await db.users.find_one({"id": proposal["from_user_id"]}, {"_id": 0, "password_hash": 0})
        proposal["from_user"] = {
            "username": sender["username"],
            "avatar_url": sender.get("avatar_url")
        } if sender else None
    
    # Get children
    children = await db.children.find({
        "$or": [
            {"parent1_id": user_id},
            {"parent2_id": user_id}
        ]
    }, {"_id": 0}).to_list(20)
    
    # Can marry check
    can_marry, reason = await check_can_marry(user_id)
    
    return {
        "marriage": marriage_info,
        "status": "married" if marriage else "single",
        "pending_proposals": pending_proposals,
        "children": children,
        "children_count": len(children),
        "can_marry": can_marry,
        "marry_reason": reason if not can_marry else None,
        "costs": {
            "proposal": MARRIAGE_COST,
            "wedding": WEDDING_COST,
            "divorce": DIVORCE_COST,
            "adoption": ADOPTION_COST,
            "child_creation": CHILD_CREATION_COST
        }
    }


@router.post("/propose")
async def propose_marriage(
    data: ProposalRequest,
    current_user: dict = Depends(get_current_user)
):
    """Send a marriage proposal to another user"""
    user_id = current_user["id"]
    
    if user_id == data.partner_id:
        raise HTTPException(status_code=400, detail="You cannot propose to yourself")
    
    # Check if can marry
    can_marry, reason = await check_can_marry(user_id)
    if not can_marry:
        raise HTTPException(status_code=400, detail=reason)
    
    # Check partner exists and can marry
    partner = await db.users.find_one({"id": data.partner_id})
    if not partner:
        raise HTTPException(status_code=404, detail="User not found")
    
    partner_can_marry, partner_reason = await check_can_marry(data.partner_id)
    if not partner_can_marry:
        raise HTTPException(status_code=400, detail=f"Partner cannot marry: {partner_reason}")
    
    # Check existing proposals
    existing = await db.proposals.find_one({
        "from_user_id": user_id,
        "to_user_id": data.partner_id,
        "status": "pending"
    })
    if existing:
        raise HTTPException(status_code=400, detail="You already have a pending proposal to this user")
    
    # Check balance
    if current_user.get("realum_balance", 0) < MARRIAGE_COST:
        raise HTTPException(status_code=400, detail=f"Insufficient RLM. Proposal costs {MARRIAGE_COST} RLM")
    
    # Deduct cost
    await db.users.update_one(
        {"id": user_id},
        {"$inc": {"realum_balance": -MARRIAGE_COST}}
    )
    
    # Create proposal
    proposal = {
        "id": str(uuid.uuid4()),
        "from_user_id": user_id,
        "from_username": current_user["username"],
        "to_user_id": data.partner_id,
        "to_username": partner["username"],
        "message": data.message,
        "status": "pending",
        "cost_paid": MARRIAGE_COST,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.proposals.insert_one(proposal)
    
    # Create notification
    await db.notifications.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": data.partner_id,
        "type": "marriage_proposal",
        "title": "Marriage Proposal! 💍",
        "message": f"{current_user['username']} has proposed to you: '{data.message}'",
        "data": {"proposal_id": proposal["id"]},
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "proposal_id": proposal["id"],
        "status": "pending",
        "message": f"Proposal sent to {partner['username']}!",
        "cost_deducted": MARRIAGE_COST
    }


@router.post("/proposal/respond")
async def respond_to_proposal(
    data: ProposalResponse,
    current_user: dict = Depends(get_current_user)
):
    """Accept or reject a marriage proposal"""
    user_id = current_user["id"]
    
    # Find proposal
    proposal = await db.proposals.find_one({
        "id": data.proposal_id,
        "to_user_id": user_id,
        "status": "pending"
    })
    
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    if data.accept:
        # Check if both can still marry
        can_marry, reason = await check_can_marry(user_id)
        if not can_marry:
            raise HTTPException(status_code=400, detail=reason)
        
        partner_can_marry, partner_reason = await check_can_marry(proposal["from_user_id"])
        if not partner_can_marry:
            raise HTTPException(status_code=400, detail=f"Partner cannot marry: {partner_reason}")
        
        # Check balance for wedding
        if current_user.get("realum_balance", 0) < WEDDING_COST:
            raise HTTPException(status_code=400, detail=f"Insufficient RLM. Wedding costs {WEDDING_COST} RLM")
        
        # Deduct wedding cost from accepter
        await db.users.update_one(
            {"id": user_id},
            {"$inc": {"realum_balance": -WEDDING_COST}}
        )
        
        # Create marriage
        marriage = {
            "id": str(uuid.uuid4()),
            "partner1_id": proposal["from_user_id"],
            "partner1_username": proposal["from_username"],
            "partner2_id": user_id,
            "partner2_username": current_user["username"],
            "status": "active",
            "married_at": datetime.now(timezone.utc).isoformat(),
            "anniversary": datetime.now(timezone.utc).strftime("%m-%d"),
            "proposal_id": proposal["id"]
        }
        await db.marriages.insert_one(marriage)
        
        # Update proposal status
        await db.proposals.update_one(
            {"id": data.proposal_id},
            {"$set": {"status": "accepted", "responded_at": datetime.now(timezone.utc).isoformat()}}
        )
        
        # Update both users' marriage status
        await db.users.update_one({"id": user_id}, {"$set": {"marriage_status": "married", "spouse_id": proposal["from_user_id"]}})
        await db.users.update_one({"id": proposal["from_user_id"]}, {"$set": {"marriage_status": "married", "spouse_id": user_id}})
        
        # Notify proposer
        await db.notifications.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": proposal["from_user_id"],
            "type": "marriage_accepted",
            "title": "Congratulations! 💒",
            "message": f"{current_user['username']} accepted your proposal! You are now married!",
            "read": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        return {
            "status": "married",
            "marriage_id": marriage["id"],
            "partner": proposal["from_username"],
            "message": f"Congratulations! You are now married to {proposal['from_username']}!",
            "bonuses": {
                "xp_multiplier": COUPLE_XP_BONUS,
                "rlm_multiplier": COUPLE_RLM_BONUS
            }
        }
    else:
        # Reject proposal
        await db.proposals.update_one(
            {"id": data.proposal_id},
            {"$set": {"status": "rejected", "responded_at": datetime.now(timezone.utc).isoformat()}}
        )
        
        # Refund half the proposal cost to proposer
        refund = MARRIAGE_COST // 2
        await db.users.update_one(
            {"id": proposal["from_user_id"]},
            {"$inc": {"realum_balance": refund}}
        )
        
        # Notify proposer
        await db.notifications.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": proposal["from_user_id"],
            "type": "proposal_rejected",
            "title": "Proposal Declined",
            "message": f"{current_user['username']} has declined your proposal. {refund} RLM refunded.",
            "read": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        return {
            "status": "rejected",
            "message": "Proposal declined"
        }


@router.post("/divorce")
async def file_divorce(current_user: dict = Depends(get_current_user)):
    """File for divorce"""
    user_id = current_user["id"]
    
    # Check if married
    marriage = await get_user_marriage_status(user_id)
    if not marriage:
        raise HTTPException(status_code=400, detail="You are not married")
    
    # Check balance
    if current_user.get("realum_balance", 0) < DIVORCE_COST:
        raise HTTPException(status_code=400, detail=f"Insufficient RLM. Divorce costs {DIVORCE_COST} RLM")
    
    # Get partner info
    partner_id = marriage["partner2_id"] if marriage["partner1_id"] == user_id else marriage["partner1_id"]
    
    # Deduct cost
    await db.users.update_one(
        {"id": user_id},
        {"$inc": {"realum_balance": -DIVORCE_COST}}
    )
    
    # End marriage
    await db.marriages.update_one(
        {"id": marriage["id"]},
        {"$set": {"status": "ended", "divorced_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Record divorce
    divorce = {
        "id": str(uuid.uuid4()),
        "marriage_id": marriage["id"],
        "user1_id": marriage["partner1_id"],
        "user2_id": marriage["partner2_id"],
        "filed_by": user_id,
        "divorced_at": datetime.now(timezone.utc).isoformat(),
        "cost_paid": DIVORCE_COST
    }
    await db.divorces.insert_one(divorce)
    
    # Update both users
    await db.users.update_one({"id": user_id}, {"$set": {"marriage_status": "divorced", "spouse_id": None}})
    await db.users.update_one({"id": partner_id}, {"$set": {"marriage_status": "divorced", "spouse_id": None}})
    
    # Notify ex-partner
    await db.notifications.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": partner_id,
        "type": "divorce",
        "title": "Divorce Filed 💔",
        "message": f"{current_user['username']} has filed for divorce.",
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "status": "divorced",
        "message": "Divorce finalized",
        "cooldown_days": DIVORCE_COOLDOWN_DAYS,
        "can_remarry_after": (datetime.now(timezone.utc) + timedelta(days=DIVORCE_COOLDOWN_DAYS)).isoformat()
    }


# ============== CHILDREN ENDPOINTS ==============

# Available children for adoption
ADOPTABLE_CHILDREN = [
    {"name": "Little Star", "personality": "curious", "interests": ["science", "nature"]},
    {"name": "Sunshine", "personality": "cheerful", "interests": ["art", "music"]},
    {"name": "Brave Heart", "personality": "adventurous", "interests": ["sports", "exploration"]},
    {"name": "Dreamer", "personality": "creative", "interests": ["stories", "imagination"]},
    {"name": "Buddy", "personality": "friendly", "interests": ["games", "friends"]},
]


@router.get("/adoption/available")
async def get_available_children(current_user: dict = Depends(get_current_user)):
    """Get list of children available for adoption"""
    return {
        "children": ADOPTABLE_CHILDREN,
        "adoption_cost": ADOPTION_COST
    }


@router.post("/adopt")
async def adopt_child(
    data: AdoptChildRequest,
    current_user: dict = Depends(get_current_user)
):
    """Adopt a virtual child"""
    user_id = current_user["id"]
    
    # Check balance
    if current_user.get("realum_balance", 0) < ADOPTION_COST:
        raise HTTPException(status_code=400, detail=f"Insufficient RLM. Adoption costs {ADOPTION_COST} RLM")
    
    # Deduct cost
    await db.users.update_one(
        {"id": user_id},
        {"$inc": {"realum_balance": -ADOPTION_COST}}
    )
    
    # Check if married - if so, add spouse as parent2
    marriage = await get_user_marriage_status(user_id)
    parent2_id = None
    if marriage:
        parent2_id = marriage["partner2_id"] if marriage["partner1_id"] == user_id else marriage["partner1_id"]
    
    # Create child
    child = {
        "id": str(uuid.uuid4()),
        "name": data.child_name,
        "gender": data.child_gender,
        "type": "adopted",
        "parent1_id": user_id,
        "parent2_id": parent2_id,
        "personality": random.choice(["curious", "cheerful", "adventurous", "creative", "friendly"]),
        "interests": random.sample(["science", "art", "sports", "music", "games", "nature", "stories"], 2),
        "age": random.randint(1, 10),
        "happiness": 100,
        "health": 100,
        "education_level": 0,
        "adopted_at": datetime.now(timezone.utc).isoformat(),
        "last_interaction": datetime.now(timezone.utc).isoformat()
    }
    await db.children.insert_one(child)
    
    return {
        "child": serialize_doc(child),
        "message": f"Congratulations! You have adopted {data.child_name}!",
        "cost_deducted": ADOPTION_COST
    }


@router.post("/create-child")
async def create_child(
    data: CreateChildRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create a child (married couples only)"""
    user_id = current_user["id"]
    
    # Check if married
    marriage = await get_user_marriage_status(user_id)
    if not marriage:
        raise HTTPException(status_code=400, detail="You must be married to have a child together")
    
    # Check balance
    if current_user.get("realum_balance", 0) < CHILD_CREATION_COST:
        raise HTTPException(status_code=400, detail=f"Insufficient RLM. Having a child costs {CHILD_CREATION_COST} RLM")
    
    # Deduct cost
    await db.users.update_one(
        {"id": user_id},
        {"$inc": {"realum_balance": -CHILD_CREATION_COST}}
    )
    
    # Get partner
    partner_id = marriage["partner2_id"] if marriage["partner1_id"] == user_id else marriage["partner1_id"]
    partner = await db.users.find_one({"id": partner_id})
    
    # Create child with traits from both parents
    child = {
        "id": str(uuid.uuid4()),
        "name": data.child_name,
        "gender": data.child_gender,
        "type": "biological",
        "parent1_id": user_id,
        "parent1_username": current_user["username"],
        "parent2_id": partner_id,
        "parent2_username": partner["username"] if partner else "Unknown",
        "personality": random.choice(["curious", "cheerful", "adventurous", "creative", "friendly", "thoughtful"]),
        "interests": random.sample(["science", "art", "sports", "music", "games", "nature", "stories", "tech"], 3),
        "age": 0,
        "happiness": 100,
        "health": 100,
        "education_level": 0,
        "birth_date": datetime.now(timezone.utc).isoformat(),
        "last_interaction": datetime.now(timezone.utc).isoformat()
    }
    await db.children.insert_one(child)
    
    # Notify partner
    await db.notifications.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": partner_id,
        "type": "new_child",
        "title": "New Family Member! 👶",
        "message": f"You and {current_user['username']} now have a child named {data.child_name}!",
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "child": serialize_doc(child),
        "message": f"Congratulations! {data.child_name} has been born!",
        "cost_deducted": CHILD_CREATION_COST
    }


@router.get("/children")
async def get_my_children(current_user: dict = Depends(get_current_user)):
    """Get all user's children"""
    user_id = current_user["id"]
    
    children = await db.children.find({
        "$or": [
            {"parent1_id": user_id},
            {"parent2_id": user_id}
        ]
    }, {"_id": 0}).to_list(50)
    
    return {"children": children}


@router.post("/children/{child_id}/interact")
async def interact_with_child(
    child_id: str,
    interaction_type: str = "play",  # play, feed, educate
    current_user: dict = Depends(get_current_user)
):
    """Interact with a child"""
    user_id = current_user["id"]
    
    child = await db.children.find_one({
        "id": child_id,
        "$or": [{"parent1_id": user_id}, {"parent2_id": user_id}]
    })
    
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    
    # Update child stats based on interaction
    updates = {"last_interaction": datetime.now(timezone.utc).isoformat()}
    reward_xp = 0
    
    if interaction_type == "play":
        updates["happiness"] = min(100, child.get("happiness", 50) + 10)
        reward_xp = 5
    elif interaction_type == "feed":
        updates["health"] = min(100, child.get("health", 50) + 10)
        reward_xp = 3
    elif interaction_type == "educate":
        updates["education_level"] = child.get("education_level", 0) + 1
        reward_xp = 10
    
    await db.children.update_one({"id": child_id}, {"$set": updates})
    
    # Grant XP to parent
    await db.users.update_one(
        {"id": user_id},
        {"$inc": {"xp": reward_xp}}
    )
    
    return {
        "message": f"You {interaction_type}ed with {child['name']}!",
        "xp_earned": reward_xp,
        "child_updates": updates
    }


@router.get("/bonuses")
async def get_family_bonuses(current_user: dict = Depends(get_current_user)):
    """Get family-related bonuses for the user"""
    user_id = current_user["id"]
    
    bonuses = {
        "xp_multiplier": 1.0,
        "rlm_multiplier": 1.0,
        "active_bonuses": []
    }
    
    # Marriage bonus
    marriage = await get_user_marriage_status(user_id)
    if marriage:
        bonuses["xp_multiplier"] *= COUPLE_XP_BONUS
        bonuses["rlm_multiplier"] *= COUPLE_RLM_BONUS
        bonuses["active_bonuses"].append({
            "name": "Married Couple Bonus",
            "xp": "+10%",
            "rlm": "+5%"
        })
    
    # Children bonus (per child)
    children_count = await db.children.count_documents({
        "$or": [{"parent1_id": user_id}, {"parent2_id": user_id}]
    })
    
    if children_count > 0:
        child_bonus = 1 + (children_count * 0.02)  # 2% per child
        bonuses["xp_multiplier"] *= child_bonus
        bonuses["active_bonuses"].append({
            "name": f"Parent Bonus ({children_count} children)",
            "xp": f"+{children_count * 2}%"
        })
    
    return bonuses
