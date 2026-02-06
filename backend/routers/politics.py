"""
REALUM Political System
World and Local Government, Elections, Political Parties
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime, timezone, timedelta
from enum import Enum
import uuid
import random

router = APIRouter(prefix="/api/politics", tags=["Political System"])

from core.database import db
from core.auth import get_current_user


# ============== CONSTANTS ==============

# Political positions
WORLD_POSITIONS = {
    "world_president": {
        "title": "World President",
        "description": "Leader of the REALUM World Government",
        "term_days": 90,
        "salary_rlm": 1000,
        "min_level": 10,
        "min_reputation": 500
    },
    "world_minister": {
        "title": "World Minister",
        "description": "Member of the World Cabinet",
        "term_days": 90,
        "salary_rlm": 500,
        "min_level": 5,
        "min_reputation": 200
    },
    "world_senator": {
        "title": "World Senator",
        "description": "Member of the World Senate",
        "term_days": 60,
        "salary_rlm": 300,
        "min_level": 3,
        "min_reputation": 100
    }
}

LOCAL_POSITIONS = {
    "zone_governor": {
        "title": "Zone Governor",
        "description": "Leader of a REALUM Zone",
        "term_days": 60,
        "salary_rlm": 500,
        "min_level": 5,
        "min_reputation": 150
    },
    "zone_councilor": {
        "title": "Zone Councilor",
        "description": "Member of Zone Council",
        "term_days": 45,
        "salary_rlm": 200,
        "min_level": 2,
        "min_reputation": 50
    },
    "district_representative": {
        "title": "District Representative",
        "description": "Representative of a District",
        "term_days": 30,
        "salary_rlm": 100,
        "min_level": 1,
        "min_reputation": 20
    }
}

# REALUM Zones for local politics
REALUM_ZONES = [
    {"id": "learning_zone", "name": "Learning Zone", "city": "Oxford, UK"},
    {"id": "jobs_hub", "name": "Jobs Hub", "city": "San Francisco, USA"},
    {"id": "marketplace", "name": "Marketplace", "city": "Dubai, UAE"},
    {"id": "social_plaza", "name": "Social Plaza", "city": "Tokyo, Japan"},
    {"id": "treasury", "name": "Treasury", "city": "Singapore"},
    {"id": "dao_hall", "name": "DAO Hall", "city": "Zurich, Switzerland"}
]

# Campaign costs
CAMPAIGN_COST = {
    "world_president": 5000,
    "world_minister": 2000,
    "world_senator": 1000,
    "zone_governor": 1500,
    "zone_councilor": 500,
    "district_representative": 200
}

# Party creation cost
PARTY_CREATION_COST = 2000


# ============== MODELS ==============

class PoliticalParty(BaseModel):
    name: str = Field(..., min_length=3, max_length=50)
    abbreviation: str = Field(..., min_length=2, max_length=5)
    ideology: str  # progressive, conservative, libertarian, socialist, centrist
    description: str
    color: str = "#00FF00"

class CampaignRequest(BaseModel):
    position: str
    zone_id: Optional[str] = None  # Required for local positions
    platform: str  # Campaign promises
    slogan: str

class VoteRequest(BaseModel):
    election_id: str
    candidate_id: str

class ProposeLawRequest(BaseModel):
    title: str
    description: str
    law_type: str  # world, zone
    zone_id: Optional[str] = None
    effects: Dict = {}


# ============== HELPER FUNCTIONS ==============

def serialize_doc(doc):
    if doc and "_id" in doc:
        del doc["_id"]
    return doc

async def get_user_political_status(user_id: str):
    """Get user's current political positions and party membership"""
    # Current positions
    positions = await db.political_positions.find({
        "holder_id": user_id,
        "status": "active"
    }, {"_id": 0}).to_list(10)
    
    # Party membership
    party_membership = await db.party_members.find_one({
        "user_id": user_id,
        "status": "active"
    })
    
    party = None
    if party_membership:
        party = await db.political_parties.find_one({"id": party_membership["party_id"]})
    
    return {
        "positions": positions,
        "party": serialize_doc(party) if party else None,
        "party_role": party_membership.get("role") if party_membership else None
    }


# ============== POLITICAL PARTIES ==============

@router.get("/parties")
async def get_all_parties():
    """Get all political parties"""
    parties = await db.political_parties.find(
        {"status": "active"}, {"_id": 0}
    ).sort("member_count", -1).to_list(50)
    
    return {"parties": parties}


@router.post("/parties/create")
async def create_party(
    data: PoliticalParty,
    current_user: dict = Depends(get_current_user)
):
    """Create a new political party"""
    # Check if user already leads a party
    existing = await db.political_parties.find_one({
        "leader_id": current_user["id"],
        "status": "active"
    })
    if existing:
        raise HTTPException(status_code=400, detail="You already lead a party")
    
    # Check balance
    if current_user.get("realum_balance", 0) < PARTY_CREATION_COST:
        raise HTTPException(status_code=400, detail=f"Creating a party costs {PARTY_CREATION_COST} RLM")
    
    # Check name uniqueness
    name_exists = await db.political_parties.find_one({"name": data.name})
    if name_exists:
        raise HTTPException(status_code=400, detail="Party name already exists")
    
    # Deduct cost
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$inc": {"realum_balance": -PARTY_CREATION_COST}}
    )
    
    # Create party
    party = {
        "id": str(uuid.uuid4()),
        "name": data.name,
        "abbreviation": data.abbreviation.upper(),
        "ideology": data.ideology,
        "description": data.description,
        "color": data.color,
        "leader_id": current_user["id"],
        "leader_username": current_user["username"],
        "member_count": 1,
        "treasury": 0,
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.political_parties.insert_one(party)
    
    # Add creator as leader member
    await db.party_members.insert_one({
        "id": str(uuid.uuid4()),
        "party_id": party["id"],
        "user_id": current_user["id"],
        "username": current_user["username"],
        "role": "leader",
        "status": "active",
        "joined_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "party": serialize_doc(party),
        "message": f"Party '{data.name}' created successfully!"
    }


@router.post("/parties/{party_id}/join")
async def join_party(
    party_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Join a political party"""
    # Check party exists
    party = await db.political_parties.find_one({"id": party_id, "status": "active"})
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    
    # Check if already in a party
    existing = await db.party_members.find_one({
        "user_id": current_user["id"],
        "status": "active"
    })
    if existing:
        raise HTTPException(status_code=400, detail="You are already in a party. Leave first.")
    
    # Join party
    await db.party_members.insert_one({
        "id": str(uuid.uuid4()),
        "party_id": party_id,
        "user_id": current_user["id"],
        "username": current_user["username"],
        "role": "member",
        "status": "active",
        "joined_at": datetime.now(timezone.utc).isoformat()
    })
    
    # Update member count
    await db.political_parties.update_one(
        {"id": party_id},
        {"$inc": {"member_count": 1}}
    )
    
    return {"message": f"You joined {party['name']}!"}


@router.post("/parties/leave")
async def leave_party(current_user: dict = Depends(get_current_user)):
    """Leave current political party"""
    membership = await db.party_members.find_one({
        "user_id": current_user["id"],
        "status": "active"
    })
    
    if not membership:
        raise HTTPException(status_code=400, detail="You are not in any party")
    
    if membership["role"] == "leader":
        raise HTTPException(status_code=400, detail="Leaders cannot leave. Transfer leadership or dissolve the party.")
    
    # Leave party
    await db.party_members.update_one(
        {"id": membership["id"]},
        {"$set": {"status": "left", "left_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Update member count
    await db.political_parties.update_one(
        {"id": membership["party_id"]},
        {"$inc": {"member_count": -1}}
    )
    
    return {"message": "You left the party"}


# ============== ELECTIONS ==============

@router.get("/elections")
async def get_elections(
    status: Optional[str] = None,
    position_type: Optional[str] = None
):
    """Get all elections"""
    query = {}
    if status:
        query["status"] = status
    if position_type:
        query["position_type"] = position_type
    
    elections = await db.elections.find(query, {"_id": 0}).sort("created_at", -1).to_list(50)
    
    # Enrich with candidate count
    for election in elections:
        candidate_count = await db.election_candidates.count_documents({
            "election_id": election["id"]
        })
        election["candidate_count"] = candidate_count
    
    return {"elections": elections}


@router.get("/elections/{election_id}")
async def get_election_details(election_id: str):
    """Get detailed election information"""
    election = await db.elections.find_one({"id": election_id}, {"_id": 0})
    if not election:
        raise HTTPException(status_code=404, detail="Election not found")
    
    # Get candidates
    candidates = await db.election_candidates.find(
        {"election_id": election_id},
        {"_id": 0}
    ).to_list(50)
    
    # Get vote counts
    for candidate in candidates:
        vote_count = await db.election_votes.count_documents({
            "election_id": election_id,
            "candidate_id": candidate["id"]
        })
        candidate["votes"] = vote_count
    
    # Sort by votes
    candidates.sort(key=lambda x: x.get("votes", 0), reverse=True)
    
    return {
        "election": election,
        "candidates": candidates
    }


@router.post("/elections/campaign")
async def start_campaign(
    data: CampaignRequest,
    current_user: dict = Depends(get_current_user)
):
    """Start a campaign for a political position"""
    # Validate position
    all_positions = {**WORLD_POSITIONS, **LOCAL_POSITIONS}
    if data.position not in all_positions:
        raise HTTPException(status_code=400, detail="Invalid position")
    
    position_info = all_positions[data.position]
    
    # Check requirements
    user_level = current_user.get("level", 1)
    user_rep = current_user.get("reputation", 0)
    
    if user_level < position_info["min_level"]:
        raise HTTPException(status_code=400, detail=f"Minimum level {position_info['min_level']} required")
    
    if user_rep < position_info["min_reputation"]:
        raise HTTPException(status_code=400, detail=f"Minimum reputation {position_info['min_reputation']} required")
    
    # Check campaign cost
    cost = CAMPAIGN_COST.get(data.position, 1000)
    if current_user.get("realum_balance", 0) < cost:
        raise HTTPException(status_code=400, detail=f"Campaign costs {cost} RLM")
    
    # For local positions, validate zone
    if data.position in LOCAL_POSITIONS:
        if not data.zone_id:
            raise HTTPException(status_code=400, detail="Zone ID required for local positions")
        if not any(z["id"] == data.zone_id for z in REALUM_ZONES):
            raise HTTPException(status_code=400, detail="Invalid zone")
    
    # Find or create active election for this position
    election_query = {
        "position": data.position,
        "status": "active"
    }
    if data.zone_id:
        election_query["zone_id"] = data.zone_id
    
    election = await db.elections.find_one(election_query)
    
    if not election:
        # Create new election
        now = datetime.now(timezone.utc)
        election = {
            "id": str(uuid.uuid4()),
            "position": data.position,
            "position_title": position_info["title"],
            "zone_id": data.zone_id,
            "zone_name": next((z["name"] for z in REALUM_ZONES if z["id"] == data.zone_id), None) if data.zone_id else None,
            "status": "active",
            "voting_starts": (now + timedelta(days=3)).isoformat(),
            "voting_ends": (now + timedelta(days=10)).isoformat(),
            "term_days": position_info["term_days"],
            "created_at": now.isoformat()
        }
        await db.elections.insert_one(election)
    
    # Check if already a candidate
    existing_candidate = await db.election_candidates.find_one({
        "election_id": election["id"],
        "user_id": current_user["id"]
    })
    if existing_candidate:
        raise HTTPException(status_code=400, detail="You are already a candidate in this election")
    
    # Deduct campaign cost
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$inc": {"realum_balance": -cost}}
    )
    
    # Get party info
    party_membership = await db.party_members.find_one({
        "user_id": current_user["id"],
        "status": "active"
    })
    party = None
    if party_membership:
        party = await db.political_parties.find_one({"id": party_membership["party_id"]})
    
    # Register as candidate
    candidate = {
        "id": str(uuid.uuid4()),
        "election_id": election["id"],
        "user_id": current_user["id"],
        "username": current_user["username"],
        "party_id": party["id"] if party else None,
        "party_name": party["name"] if party else "Independent",
        "party_color": party["color"] if party else "#888888",
        "platform": data.platform,
        "slogan": data.slogan,
        "campaign_fund": cost,
        "registered_at": datetime.now(timezone.utc).isoformat()
    }
    await db.election_candidates.insert_one(candidate)
    
    return {
        "candidate": serialize_doc(candidate),
        "election": serialize_doc(election),
        "message": f"Campaign started for {position_info['title']}!",
        "voting_starts": election["voting_starts"]
    }


@router.post("/elections/vote")
async def cast_vote(
    data: VoteRequest,
    current_user: dict = Depends(get_current_user)
):
    """Cast a vote in an election"""
    # Verify election
    election = await db.elections.find_one({"id": data.election_id})
    if not election:
        raise HTTPException(status_code=404, detail="Election not found")
    
    # Check if voting is open
    now = datetime.now(timezone.utc)
    voting_starts = datetime.fromisoformat(election["voting_starts"].replace("Z", "+00:00"))
    voting_ends = datetime.fromisoformat(election["voting_ends"].replace("Z", "+00:00"))
    
    if now < voting_starts:
        raise HTTPException(status_code=400, detail="Voting has not started yet")
    if now > voting_ends:
        raise HTTPException(status_code=400, detail="Voting has ended")
    
    # Verify candidate
    candidate = await db.election_candidates.find_one({
        "id": data.candidate_id,
        "election_id": data.election_id
    })
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    # Check if already voted
    existing_vote = await db.election_votes.find_one({
        "election_id": data.election_id,
        "voter_id": current_user["id"]
    })
    if existing_vote:
        raise HTTPException(status_code=400, detail="You have already voted in this election")
    
    # Cast vote
    vote = {
        "id": str(uuid.uuid4()),
        "election_id": data.election_id,
        "candidate_id": data.candidate_id,
        "voter_id": current_user["id"],
        "voted_at": now.isoformat()
    }
    await db.election_votes.insert_one(vote)
    
    return {
        "message": f"Vote cast for {candidate['username']}!",
        "election": election["position_title"]
    }


# ============== GOVERNMENT & POSITIONS ==============

@router.get("/government/world")
async def get_world_government():
    """Get current world government officials"""
    positions = await db.political_positions.find({
        "level": "world",
        "status": "active"
    }, {"_id": 0}).to_list(50)
    
    return {
        "world_president": next((p for p in positions if p["position"] == "world_president"), None),
        "ministers": [p for p in positions if p["position"] == "world_minister"],
        "senators": [p for p in positions if p["position"] == "world_senator"]
    }


@router.get("/government/zone/{zone_id}")
async def get_zone_government(zone_id: str):
    """Get zone government officials"""
    if not any(z["id"] == zone_id for z in REALUM_ZONES):
        raise HTTPException(status_code=404, detail="Zone not found")
    
    positions = await db.political_positions.find({
        "zone_id": zone_id,
        "status": "active"
    }, {"_id": 0}).to_list(50)
    
    zone = next(z for z in REALUM_ZONES if z["id"] == zone_id)
    
    return {
        "zone": zone,
        "governor": next((p for p in positions if p["position"] == "zone_governor"), None),
        "councilors": [p for p in positions if p["position"] == "zone_councilor"],
        "representatives": [p for p in positions if p["position"] == "district_representative"]
    }


@router.get("/government/zones")
async def get_all_zone_governments():
    """Get all zone governments summary"""
    zones_data = []
    
    for zone in REALUM_ZONES:
        governor = await db.political_positions.find_one({
            "zone_id": zone["id"],
            "position": "zone_governor",
            "status": "active"
        }, {"_id": 0})
        
        councilor_count = await db.political_positions.count_documents({
            "zone_id": zone["id"],
            "position": "zone_councilor",
            "status": "active"
        })
        
        zones_data.append({
            "zone": zone,
            "governor": governor,
            "councilor_count": councilor_count
        })
    
    return {"zones": zones_data}


# ============== LAWS & POLICIES ==============

@router.get("/laws")
async def get_laws(
    law_type: Optional[str] = None,
    zone_id: Optional[str] = None,
    status: Optional[str] = "active"
):
    """Get all laws and policies"""
    query = {}
    if law_type:
        query["law_type"] = law_type
    if zone_id:
        query["zone_id"] = zone_id
    if status:
        query["status"] = status
    
    laws = await db.laws.find(query, {"_id": 0}).sort("enacted_at", -1).to_list(100)
    
    return {"laws": laws}


@router.post("/laws/propose")
async def propose_law(
    data: ProposeLawRequest,
    current_user: dict = Depends(get_current_user)
):
    """Propose a new law (requires political position)"""
    # Check if user holds a position
    user_position = await db.political_positions.find_one({
        "holder_id": current_user["id"],
        "status": "active"
    })
    
    if not user_position:
        raise HTTPException(status_code=403, detail="Only elected officials can propose laws")
    
    # Validate law type and zone
    if data.law_type == "zone" and not data.zone_id:
        raise HTTPException(status_code=400, detail="Zone ID required for zone laws")
    
    if data.law_type == "world" and user_position["level"] != "world":
        raise HTTPException(status_code=403, detail="Only world officials can propose world laws")
    
    if data.law_type == "zone" and user_position.get("zone_id") != data.zone_id:
        raise HTTPException(status_code=403, detail="Can only propose laws for your zone")
    
    now = datetime.now(timezone.utc)
    
    law = {
        "id": str(uuid.uuid4()),
        "title": data.title,
        "description": data.description,
        "law_type": data.law_type,
        "zone_id": data.zone_id,
        "effects": data.effects,
        "proposed_by": current_user["id"],
        "proposed_by_username": current_user["username"],
        "proposed_by_position": user_position["position_title"],
        "status": "voting",
        "votes_for": 0,
        "votes_against": 0,
        "voting_ends": (now + timedelta(days=3)).isoformat(),
        "proposed_at": now.isoformat()
    }
    await db.laws.insert_one(law)
    
    return {
        "law": serialize_doc(law),
        "message": "Law proposed! Voting will last 3 days."
    }


@router.post("/laws/{law_id}/vote")
async def vote_on_law(
    law_id: str,
    vote: str,  # "for" or "against"
    current_user: dict = Depends(get_current_user)
):
    """Vote on a proposed law (requires political position)"""
    if vote not in ["for", "against"]:
        raise HTTPException(status_code=400, detail="Vote must be 'for' or 'against'")
    
    # Check if user holds a position
    user_position = await db.political_positions.find_one({
        "holder_id": current_user["id"],
        "status": "active"
    })
    
    if not user_position:
        raise HTTPException(status_code=403, detail="Only elected officials can vote on laws")
    
    law = await db.laws.find_one({"id": law_id, "status": "voting"})
    if not law:
        raise HTTPException(status_code=404, detail="Law not found or voting has ended")
    
    # Check if already voted
    existing = await db.law_votes.find_one({
        "law_id": law_id,
        "voter_id": current_user["id"]
    })
    if existing:
        raise HTTPException(status_code=400, detail="You have already voted on this law")
    
    # Record vote
    await db.law_votes.insert_one({
        "id": str(uuid.uuid4()),
        "law_id": law_id,
        "voter_id": current_user["id"],
        "vote": vote,
        "voted_at": datetime.now(timezone.utc).isoformat()
    })
    
    # Update vote counts
    if vote == "for":
        await db.laws.update_one({"id": law_id}, {"$inc": {"votes_for": 1}})
    else:
        await db.laws.update_one({"id": law_id}, {"$inc": {"votes_against": 1}})
    
    return {"message": f"Vote recorded: {vote}"}


# ============== USER POLITICAL STATUS ==============

@router.get("/my-status")
async def get_my_political_status(current_user: dict = Depends(get_current_user)):
    """Get current user's political status"""
    status = await get_user_political_status(current_user["id"])
    
    # Get active candidacies
    candidacies = await db.election_candidates.find({
        "user_id": current_user["id"]
    }, {"_id": 0}).to_list(10)
    
    # Get voting history
    votes_cast = await db.election_votes.count_documents({"voter_id": current_user["id"]})
    
    return {
        **status,
        "candidacies": candidacies,
        "votes_cast": votes_cast,
        "can_create_party": current_user.get("realum_balance", 0) >= PARTY_CREATION_COST,
        "party_creation_cost": PARTY_CREATION_COST
    }


@router.get("/positions/available")
async def get_available_positions(current_user: dict = Depends(get_current_user)):
    """Get positions the user can run for"""
    user_level = current_user.get("level", 1)
    user_rep = current_user.get("reputation", 0)
    user_balance = current_user.get("realum_balance", 0)
    
    available = []
    
    # Check world positions
    for pos_id, pos_info in WORLD_POSITIONS.items():
        can_run = (
            user_level >= pos_info["min_level"] and
            user_rep >= pos_info["min_reputation"] and
            user_balance >= CAMPAIGN_COST.get(pos_id, 1000)
        )
        available.append({
            "position": pos_id,
            "level": "world",
            **pos_info,
            "campaign_cost": CAMPAIGN_COST.get(pos_id, 1000),
            "can_run": can_run,
            "reason": None if can_run else "Requirements not met"
        })
    
    # Check local positions
    for pos_id, pos_info in LOCAL_POSITIONS.items():
        can_run = (
            user_level >= pos_info["min_level"] and
            user_rep >= pos_info["min_reputation"] and
            user_balance >= CAMPAIGN_COST.get(pos_id, 500)
        )
        available.append({
            "position": pos_id,
            "level": "local",
            **pos_info,
            "campaign_cost": CAMPAIGN_COST.get(pos_id, 500),
            "can_run": can_run,
            "zones": REALUM_ZONES,
            "reason": None if can_run else "Requirements not met"
        })
    
    return {"positions": available}


# ============== POLITICAL STATISTICS ==============

@router.get("/statistics")
async def get_political_statistics():
    """Get overall political statistics"""
    total_parties = await db.political_parties.count_documents({"status": "active"})
    total_officials = await db.political_positions.count_documents({"status": "active"})
    active_elections = await db.elections.count_documents({"status": "active"})
    total_laws = await db.laws.count_documents({"status": "active"})
    total_votes_cast = await db.election_votes.count_documents({})
    
    # Top parties by members
    top_parties = await db.political_parties.find(
        {"status": "active"}, {"_id": 0, "name": 1, "abbreviation": 1, "member_count": 1, "color": 1}
    ).sort("member_count", -1).limit(5).to_list(5)
    
    return {
        "total_parties": total_parties,
        "total_officials": total_officials,
        "active_elections": active_elections,
        "total_laws": total_laws,
        "total_votes_cast": total_votes_cast,
        "top_parties": top_parties,
        "zones": REALUM_ZONES
    }
