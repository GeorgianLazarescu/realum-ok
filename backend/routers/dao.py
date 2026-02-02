from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime, timezone
import uuid

from core.database import db
from core.auth import get_current_user
from models.dao import Proposal, ProposalCreate, VoteRequest, CityZone
from services.token_service import add_xp, award_badge

router = APIRouter(tags=["DAO & Governance"])

# ==================== PROPOSALS ====================

@router.get("/proposals", response_model=List[Proposal])
async def get_proposals(status: Optional[str] = None):
    query = {}
    if status:
        query["status"] = status
    proposals = await db.proposals.find(query, {"_id": 0}).to_list(100)
    return proposals

@router.post("/proposals")
async def create_proposal(
    data: ProposalCreate,
    current_user: dict = Depends(get_current_user)
):
    if current_user.get("level", 1) < 2:
        raise HTTPException(status_code=403, detail="Requires level 2 to create proposals")
    
    proposal = {
        "id": str(uuid.uuid4()),
        "title": data.title,
        "description": data.description,
        "proposer_id": current_user["id"],
        "proposer_name": current_user["username"],
        "status": "active",
        "votes_for": 0,
        "votes_against": 0,
        "voters": [],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.proposals.insert_one(proposal)
    return {"status": "created", "proposal_id": proposal["id"]}

@router.post("/proposals/{proposal_id}/vote")
async def vote_on_proposal(
    proposal_id: str,
    vote: VoteRequest,
    current_user: dict = Depends(get_current_user)
):
    proposal = await db.proposals.find_one({"id": proposal_id})
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    if proposal["status"] != "active":
        raise HTTPException(status_code=400, detail="Voting is closed")
    
    if current_user["id"] in proposal.get("voters", []):
        raise HTTPException(status_code=400, detail="Already voted")
    
    update_field = "votes_for" if vote.vote_type == "for" else "votes_against"
    
    await db.proposals.update_one(
        {"id": proposal_id},
        {
            "$inc": {update_field: 1},
            "$push": {"voters": current_user["id"]}
        }
    )
    
    # Award first vote badge
    total_votes = await db.proposals.count_documents({
        "voters": current_user["id"]
    })
    if total_votes == 1:
        await award_badge(current_user["id"], "first_vote")
    
    # Add XP for voting
    await add_xp(current_user["id"], 10)
    
    return {"status": "voted", "vote_type": vote.vote_type}

# ==================== CITY ZONES ====================

@router.get("/city/zones", response_model=List[CityZone])
async def get_city_zones():
    zones = await db.zones.find({}, {"_id": 0}).to_list(100)
    
    # Add job counts
    for zone in zones:
        job_count = await db.jobs.count_documents({"zone": zone["id"]})
        zone["jobs_count"] = job_count
    
    return zones
