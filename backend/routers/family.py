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


# ============== FAMILY ACHIEVEMENTS ==============

FAMILY_ACHIEVEMENTS = [
    # Marriage Achievements
    {"id": "first_love", "name": "First Love", "description": "Get married for the first time", "type": "marriage", "requirement": 1, "reward_rlm": 100, "badge": "💍"},
    {"id": "silver_anniversary", "name": "Silver Anniversary", "description": "Stay married for 25 days", "type": "marriage_days", "requirement": 25, "reward_rlm": 250, "badge": "🥈"},
    {"id": "golden_anniversary", "name": "Golden Anniversary", "description": "Stay married for 50 days", "type": "marriage_days", "requirement": 50, "reward_rlm": 500, "badge": "🥇"},
    {"id": "diamond_anniversary", "name": "Diamond Anniversary", "description": "Stay married for 100 days", "type": "marriage_days", "requirement": 100, "reward_rlm": 1000, "badge": "💎"},
    
    # Children Achievements
    {"id": "first_child", "name": "New Parent", "description": "Have your first child", "type": "children", "requirement": 1, "reward_rlm": 150, "badge": "👶"},
    {"id": "growing_family", "name": "Growing Family", "description": "Have 3 children", "type": "children", "requirement": 3, "reward_rlm": 300, "badge": "👨‍👩‍👧‍👦"},
    {"id": "big_family", "name": "Big Happy Family", "description": "Have 5 children", "type": "children", "requirement": 5, "reward_rlm": 500, "badge": "🏠"},
    
    # Parenting Achievements
    {"id": "caring_parent", "name": "Caring Parent", "description": "Interact with your child 10 times", "type": "interactions", "requirement": 10, "reward_rlm": 50, "badge": "🤗"},
    {"id": "devoted_parent", "name": "Devoted Parent", "description": "Interact with your child 50 times", "type": "interactions", "requirement": 50, "reward_rlm": 200, "badge": "❤️"},
    {"id": "super_parent", "name": "Super Parent", "description": "Interact with your child 100 times", "type": "interactions", "requirement": 100, "reward_rlm": 500, "badge": "🦸"},
    
    # Education Achievements  
    {"id": "teacher", "name": "Home Teacher", "description": "Educate a child to level 5", "type": "education", "requirement": 5, "reward_rlm": 100, "badge": "📚"},
    {"id": "professor", "name": "Professor Parent", "description": "Educate a child to level 10", "type": "education", "requirement": 10, "reward_rlm": 250, "badge": "🎓"},
    {"id": "scholar", "name": "Raising a Scholar", "description": "Educate a child to level 20", "type": "education", "requirement": 20, "reward_rlm": 500, "badge": "🏆"},
]


@router.get("/achievements")
async def get_family_achievements(current_user: dict = Depends(get_current_user)):
    """Get user's family achievements progress"""
    user_id = current_user["id"]
    
    # Get user's family data
    marriage = await get_user_marriage_status(user_id)
    children = await db.children.find({
        "$or": [{"parent1_id": user_id}, {"parent2_id": user_id}]
    }).to_list(50)
    
    # Get claimed achievements
    claimed = await db.family_achievements.find({
        "user_id": user_id
    }).to_list(100)
    claimed_ids = {a["achievement_id"] for a in claimed}
    
    # Calculate progress for each achievement
    achievements = []
    
    # Calculate marriage days
    marriage_days = 0
    if marriage:
        married_at = datetime.fromisoformat(marriage["married_at"].replace("Z", "+00:00"))
        marriage_days = (datetime.now(timezone.utc) - married_at).days
    
    # Calculate total interactions and max education
    total_interactions = sum(c.get("total_interactions", 0) for c in children)
    max_education = max((c.get("education_level", 0) for c in children), default=0)
    
    for ach in FAMILY_ACHIEVEMENTS:
        progress = 0
        current = 0
        
        if ach["type"] == "marriage":
            current = 1 if marriage else 0
            progress = 100 if marriage else 0
        elif ach["type"] == "marriage_days":
            current = marriage_days
            progress = min(100, (marriage_days / ach["requirement"]) * 100)
        elif ach["type"] == "children":
            current = len(children)
            progress = min(100, (len(children) / ach["requirement"]) * 100)
        elif ach["type"] == "interactions":
            current = total_interactions
            progress = min(100, (total_interactions / ach["requirement"]) * 100)
        elif ach["type"] == "education":
            current = max_education
            progress = min(100, (max_education / ach["requirement"]) * 100)
        
        achievements.append({
            **ach,
            "progress": round(progress, 1),
            "current": current,
            "claimed": ach["id"] in claimed_ids,
            "can_claim": progress >= 100 and ach["id"] not in claimed_ids
        })
    
    return {
        "achievements": achievements,
        "total_claimed": len(claimed_ids),
        "total_achievements": len(FAMILY_ACHIEVEMENTS)
    }


@router.post("/achievements/{achievement_id}/claim")
async def claim_family_achievement(
    achievement_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Claim a completed family achievement"""
    user_id = current_user["id"]
    
    # Find achievement
    achievement = next((a for a in FAMILY_ACHIEVEMENTS if a["id"] == achievement_id), None)
    if not achievement:
        raise HTTPException(status_code=404, detail="Achievement not found")
    
    # Check if already claimed
    existing = await db.family_achievements.find_one({
        "user_id": user_id,
        "achievement_id": achievement_id
    })
    if existing:
        raise HTTPException(status_code=400, detail="Achievement already claimed")
    
    # Verify completion (simplified check)
    marriage = await get_user_marriage_status(user_id)
    children = await db.children.find({
        "$or": [{"parent1_id": user_id}, {"parent2_id": user_id}]
    }).to_list(50)
    
    can_claim = False
    
    if achievement["type"] == "marriage":
        can_claim = marriage is not None
    elif achievement["type"] == "marriage_days":
        if marriage:
            married_at = datetime.fromisoformat(marriage["married_at"].replace("Z", "+00:00"))
            days = (datetime.now(timezone.utc) - married_at).days
            can_claim = days >= achievement["requirement"]
    elif achievement["type"] == "children":
        can_claim = len(children) >= achievement["requirement"]
    elif achievement["type"] == "interactions":
        total = sum(c.get("total_interactions", 0) for c in children)
        can_claim = total >= achievement["requirement"]
    elif achievement["type"] == "education":
        max_edu = max((c.get("education_level", 0) for c in children), default=0)
        can_claim = max_edu >= achievement["requirement"]
    
    if not can_claim:
        raise HTTPException(status_code=400, detail="Achievement requirements not met")
    
    # Claim achievement
    await db.family_achievements.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "achievement_id": achievement_id,
        "claimed_at": datetime.now(timezone.utc).isoformat()
    })
    
    # Grant reward
    await db.users.update_one(
        {"id": user_id},
        {"$inc": {"realum_balance": achievement["reward_rlm"]}}
    )
    
    # Add badge to user
    await db.users.update_one(
        {"id": user_id},
        {"$addToSet": {"badges": achievement["badge"]}}
    )
    
    return {
        "achievement": achievement,
        "reward_rlm": achievement["reward_rlm"],
        "badge": achievement["badge"],
        "message": f"Congratulations! You earned '{achievement['name']}' and received {achievement['reward_rlm']} RLM!"
    }


# ============== FAMILY EVENTS ==============

@router.get("/events")
async def get_family_events(current_user: dict = Depends(get_current_user)):
    """Get upcoming and active family events (anniversaries, birthdays)"""
    user_id = current_user["id"]
    now = datetime.now(timezone.utc)
    
    events = []
    
    # Check wedding anniversary
    marriage = await get_user_marriage_status(user_id)
    if marriage:
        married_at = datetime.fromisoformat(marriage["married_at"].replace("Z", "+00:00"))
        
        # Calculate anniversary this year
        anniversary_this_year = married_at.replace(year=now.year)
        if anniversary_this_year < now:
            anniversary_this_year = anniversary_this_year.replace(year=now.year + 1)
        
        days_until = (anniversary_this_year - now).days
        years_married = now.year - married_at.year
        
        # Anniversary bonus calculation
        anniversary_bonus = min(500, 50 * years_married)  # 50 RLM per year, max 500
        
        # Check if today is anniversary
        is_anniversary = (now.month == married_at.month and now.day == married_at.day)
        
        events.append({
            "type": "anniversary",
            "name": f"Wedding Anniversary ({years_married} years)" if years_married > 0 else "First Wedding Anniversary",
            "date": anniversary_this_year.isoformat(),
            "days_until": days_until if not is_anniversary else 0,
            "is_today": is_anniversary,
            "bonus_rlm": anniversary_bonus,
            "partner": marriage.get("partner2_username") if marriage["partner1_id"] == user_id else marriage.get("partner1_username"),
            "icon": "💒"
        })
        
        # If today is anniversary, check if claimed
        if is_anniversary:
            claimed = await db.family_event_claims.find_one({
                "user_id": user_id,
                "event_type": "anniversary",
                "year": now.year
            })
            events[-1]["claimed"] = claimed is not None
            events[-1]["can_claim"] = claimed is None
    
    # Check children birthdays
    children = await db.children.find({
        "$or": [{"parent1_id": user_id}, {"parent2_id": user_id}]
    }).to_list(50)
    
    for child in children:
        birth_date_str = child.get("birth_date") or child.get("adopted_at")
        if not birth_date_str:
            continue
            
        birth_date = datetime.fromisoformat(birth_date_str.replace("Z", "+00:00"))
        
        # Calculate birthday this year
        birthday_this_year = birth_date.replace(year=now.year)
        if birthday_this_year < now:
            birthday_this_year = birthday_this_year.replace(year=now.year + 1)
        
        days_until = (birthday_this_year - now).days
        child_age = now.year - birth_date.year
        
        is_birthday = (now.month == birth_date.month and now.day == birth_date.day)
        birthday_bonus = 25 + (child_age * 5)  # Base 25 + 5 per year of age
        
        events.append({
            "type": "birthday",
            "name": f"{child['name']}'s Birthday",
            "child_id": child["id"],
            "child_name": child["name"],
            "date": birthday_this_year.isoformat(),
            "days_until": days_until if not is_birthday else 0,
            "is_today": is_birthday,
            "age": child_age + 1,  # They're turning this age
            "bonus_rlm": birthday_bonus,
            "icon": "🎂"
        })
        
        if is_birthday:
            claimed = await db.family_event_claims.find_one({
                "user_id": user_id,
                "event_type": "birthday",
                "child_id": child["id"],
                "year": now.year
            })
            events[-1]["claimed"] = claimed is not None
            events[-1]["can_claim"] = claimed is None
    
    # Sort by days until
    events.sort(key=lambda x: x["days_until"])
    
    # Separate active (today) and upcoming
    active_events = [e for e in events if e["is_today"]]
    upcoming_events = [e for e in events if not e["is_today"]][:5]
    
    return {
        "active_events": active_events,
        "upcoming_events": upcoming_events,
        "total_events": len(events)
    }


@router.post("/events/claim")
async def claim_family_event_bonus(
    event_type: str,
    child_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Claim bonus for a family event (anniversary or birthday)"""
    user_id = current_user["id"]
    now = datetime.now(timezone.utc)
    
    if event_type == "anniversary":
        # Verify it's anniversary day
        marriage = await get_user_marriage_status(user_id)
        if not marriage:
            raise HTTPException(status_code=400, detail="You are not married")
        
        married_at = datetime.fromisoformat(marriage["married_at"].replace("Z", "+00:00"))
        
        if not (now.month == married_at.month and now.day == married_at.day):
            raise HTTPException(status_code=400, detail="It's not your anniversary today")
        
        # Check if already claimed
        claimed = await db.family_event_claims.find_one({
            "user_id": user_id,
            "event_type": "anniversary",
            "year": now.year
        })
        if claimed:
            raise HTTPException(status_code=400, detail="Anniversary bonus already claimed this year")
        
        # Calculate bonus
        years_married = now.year - married_at.year
        bonus = min(500, 50 * max(1, years_married))
        
        # Claim
        await db.family_event_claims.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "event_type": "anniversary",
            "year": now.year,
            "bonus_rlm": bonus,
            "claimed_at": now.isoformat()
        })
        
        # Grant bonus to both partners
        partner_id = marriage["partner2_id"] if marriage["partner1_id"] == user_id else marriage["partner1_id"]
        
        await db.users.update_one({"id": user_id}, {"$inc": {"realum_balance": bonus}})
        await db.users.update_one({"id": partner_id}, {"$inc": {"realum_balance": bonus}})
        
        # Notify partner
        await db.notifications.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": partner_id,
            "type": "anniversary_bonus",
            "title": "Happy Anniversary! 💒",
            "message": f"You and {current_user['username']} received {bonus} RLM for your anniversary!",
            "read": False,
            "created_at": now.isoformat()
        })
        
        return {
            "event": "anniversary",
            "bonus_rlm": bonus,
            "years_married": years_married,
            "message": f"Happy Anniversary! You and your partner each received {bonus} RLM!"
        }
    
    elif event_type == "birthday":
        if not child_id:
            raise HTTPException(status_code=400, detail="Child ID required for birthday claim")
        
        # Verify child exists and belongs to user
        child = await db.children.find_one({
            "id": child_id,
            "$or": [{"parent1_id": user_id}, {"parent2_id": user_id}]
        })
        if not child:
            raise HTTPException(status_code=404, detail="Child not found")
        
        birth_date_str = child.get("birth_date") or child.get("adopted_at")
        if not birth_date_str:
            raise HTTPException(status_code=400, detail="Child birth date not set")
        
        birth_date = datetime.fromisoformat(birth_date_str.replace("Z", "+00:00"))
        
        if not (now.month == birth_date.month and now.day == birth_date.day):
            raise HTTPException(status_code=400, detail=f"It's not {child['name']}'s birthday today")
        
        # Check if already claimed
        claimed = await db.family_event_claims.find_one({
            "user_id": user_id,
            "event_type": "birthday",
            "child_id": child_id,
            "year": now.year
        })
        if claimed:
            raise HTTPException(status_code=400, detail="Birthday bonus already claimed this year")
        
        # Calculate bonus
        child_age = now.year - birth_date.year
        bonus = 25 + (child_age * 5)
        
        # Claim
        await db.family_event_claims.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "event_type": "birthday",
            "child_id": child_id,
            "year": now.year,
            "bonus_rlm": bonus,
            "claimed_at": now.isoformat()
        })
        
        # Grant bonus
        await db.users.update_one({"id": user_id}, {"$inc": {"realum_balance": bonus}})
        
        # Increase child's age
        await db.children.update_one({"id": child_id}, {"$inc": {"age": 1}})
        
        # Increase child's happiness
        await db.children.update_one({"id": child_id}, {"$set": {"happiness": 100}})
        
        return {
            "event": "birthday",
            "child_name": child["name"],
            "new_age": child_age + 1,
            "bonus_rlm": bonus,
            "message": f"Happy Birthday {child['name']}! You received {bonus} RLM!"
        }
    
    else:
        raise HTTPException(status_code=400, detail="Invalid event type")
