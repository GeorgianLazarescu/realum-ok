from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
import uuid
import math

from core.database import db
from core.auth import get_current_user, require_admin
from services.token_service import TokenService
from services.notification_service import send_notification

router = APIRouter(prefix="/api/dao", tags=["DAO & Governance"])
token_service = TokenService()

# ===================== MODELS =====================

class ProposalCreate(BaseModel):
    title: str
    description: str
    proposal_type: str = "general"  # general, budget, parameter, emergency
    budget_request: Optional[float] = None
    voting_duration_days: int = 7
    quorum_percentage: float = 10.0  # Minimum participation %
    execution_delay_hours: int = 24

class VoteRequest(BaseModel):
    vote: bool  # True = for, False = against
    voting_power: Optional[float] = None  # For quadratic voting

class DelegationCreate(BaseModel):
    delegate_to: str  # User ID to delegate to
    categories: List[str] = []  # Empty = all categories
    expires_at: Optional[str] = None

class TreasuryAllocation(BaseModel):
    category: str
    amount: float
    description: str
    recipient_type: str  # subdao, project, bounty, external
    recipient_id: Optional[str] = None

class QuadraticVoteRequest(BaseModel):
    votes: int  # Number of votes to cast (cost = votes^2 tokens)
    direction: bool  # True = for, False = against

# ===================== PROPOSALS =====================

@router.get("/proposals")
async def get_proposals(
    status: Optional[str] = None,
    proposal_type: Optional[str] = None,
    creator_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 20
):
    """Get proposals with filters"""
    try:
        query = {}
        if status:
            query["status"] = status
        if proposal_type:
            query["proposal_type"] = proposal_type
        if creator_id:
            query["proposer_id"] = creator_id

        proposals = await db.proposals.find(
            query, {"_id": 0}
        ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)

        # Enrich with proposer info
        for proposal in proposals:
            user = await db.users.find_one(
                {"id": proposal.get("proposer_id")},
                {"_id": 0, "username": 1, "avatar_url": 1}
            )
            if user:
                proposal["proposer_username"] = user.get("username")
                proposal["proposer_avatar"] = user.get("avatar_url")

        total = await db.proposals.count_documents(query)

        return {"proposals": proposals, "total": total}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/proposals")
async def create_proposal(
    data: ProposalCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new proposal"""
    try:
        # Check level requirement
        if current_user.get("level", 1) < 2:
            raise HTTPException(status_code=403, detail="Requires level 2 to create proposals")

        proposal_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        voting_ends = now + timedelta(days=data.voting_duration_days)

        proposal = {
            "id": proposal_id,
            "title": data.title,
            "description": data.description,
            "proposal_type": data.proposal_type,
            "budget_request": data.budget_request,
            "proposer_id": current_user["id"],
            "proposer_name": current_user["username"],
            "status": "active",
            "votes_for": 0,
            "votes_against": 0,
            "total_voting_power_for": 0,
            "total_voting_power_against": 0,
            "voter_count": 0,
            "voters": [],
            "quorum_percentage": data.quorum_percentage,
            "execution_delay_hours": data.execution_delay_hours,
            "voting_ends_at": voting_ends.isoformat(),
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }

        await db.proposals.insert_one(proposal)

        return {
            "message": "Proposal created",
            "proposal_id": proposal_id,
            "voting_ends_at": voting_ends.isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/proposals/{proposal_id}")
async def get_proposal_details(proposal_id: str):
    """Get detailed proposal information"""
    try:
        proposal = await db.proposals.find_one({"id": proposal_id}, {"_id": 0})

        if not proposal:
            raise HTTPException(status_code=404, detail="Proposal not found")

        # Get proposer info
        user = await db.users.find_one(
            {"id": proposal.get("proposer_id")},
            {"_id": 0, "username": 1, "avatar_url": 1}
        )
        if user:
            proposal["proposer_username"] = user.get("username")
            proposal["proposer_avatar"] = user.get("avatar_url")

        # Get votes
        votes = await db.votes.find(
            {"proposal_id": proposal_id},
            {"_id": 0}
        ).to_list(100)

        # Enrich votes with user info
        for vote in votes:
            voter = await db.users.find_one(
                {"id": vote.get("user_id")},
                {"_id": 0, "username": 1}
            )
            if voter:
                vote["username"] = voter.get("username")

        # Calculate participation
        total_users = await db.users.count_documents({})
        participation = (proposal.get("voter_count", 0) / total_users * 100) if total_users > 0 else 0
        quorum_reached = participation >= proposal.get("quorum_percentage", 10)

        return {
            "proposal": proposal,
            "votes": votes,
            "participation_percentage": round(participation, 2),
            "quorum_reached": quorum_reached
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/proposals/{proposal_id}/vote")
async def vote_on_proposal(
    proposal_id: str,
    vote: VoteRequest,
    current_user: dict = Depends(get_current_user)
):
    """Vote on a proposal with delegation support"""
    try:
        proposal = await db.proposals.find_one({"id": proposal_id})
        if not proposal:
            raise HTTPException(status_code=404, detail="Proposal not found")

        if proposal["status"] != "active":
            raise HTTPException(status_code=400, detail="Voting is closed")

        # Check if voting period ended
        voting_ends = datetime.fromisoformat(proposal["voting_ends_at"].replace('Z', '+00:00'))
        if datetime.now(timezone.utc) > voting_ends:
            raise HTTPException(status_code=400, detail="Voting period has ended")

        user_id = current_user["id"]

        if user_id in proposal.get("voters", []):
            raise HTTPException(status_code=400, detail="Already voted")

        # Calculate voting power (base + level bonus + delegated)
        base_power = 1
        level_bonus = current_user.get("level", 1) * 0.1
        
        # Get delegated power
        delegations = await db.vote_delegations.find({
            "delegate_to": user_id,
            "is_active": True,
            "$or": [
                {"categories": []},
                {"categories": proposal.get("proposal_type", "general")}
            ]
        }).to_list(100)

        delegated_power = len(delegations) * 0.5
        total_voting_power = base_power + level_bonus + delegated_power

        now = datetime.now(timezone.utc).isoformat()

        # Record vote
        await db.votes.insert_one({
            "id": str(uuid.uuid4()),
            "proposal_id": proposal_id,
            "user_id": user_id,
            "vote": vote.vote,
            "voting_power": total_voting_power,
            "delegated_from": [d["user_id"] for d in delegations],
            "created_at": now
        })

        # Update proposal
        update_field = "votes_for" if vote.vote else "votes_against"
        power_field = "total_voting_power_for" if vote.vote else "total_voting_power_against"

        await db.proposals.update_one(
            {"id": proposal_id},
            {
                "$inc": {
                    update_field: 1,
                    power_field: total_voting_power,
                    "voter_count": 1
                },
                "$push": {"voters": user_id}
            }
        )

        return {
            "message": "Vote recorded",
            "vote": "for" if vote.vote else "against",
            "voting_power": total_voting_power,
            "delegations_used": len(delegations)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/proposals/{proposal_id}/vote/quadratic")
async def quadratic_vote(
    proposal_id: str,
    vote: QuadraticVoteRequest,
    current_user: dict = Depends(get_current_user)
):
    """Vote using quadratic voting (cost = votes^2 tokens)"""
    try:
        proposal = await db.proposals.find_one({"id": proposal_id})
        if not proposal:
            raise HTTPException(status_code=404, detail="Proposal not found")

        if proposal["status"] != "active":
            raise HTTPException(status_code=400, detail="Voting is closed")

        user_id = current_user["id"]

        # Check existing quadratic votes
        existing = await db.quadratic_votes.find_one({
            "proposal_id": proposal_id,
            "user_id": user_id
        })

        if existing:
            raise HTTPException(status_code=400, detail="Already cast quadratic votes")

        # Calculate cost (quadratic)
        cost = vote.votes ** 2

        # Check balance
        user = await db.users.find_one({"id": user_id}, {"realum_balance": 1})
        if user.get("realum_balance", 0) < cost:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient balance. {vote.votes} votes cost {cost} RLM"
            )

        # Deduct tokens
        await db.users.update_one(
            {"id": user_id},
            {"$inc": {"realum_balance": -cost}}
        )

        now = datetime.now(timezone.utc).isoformat()

        # Record quadratic vote
        await db.quadratic_votes.insert_one({
            "id": str(uuid.uuid4()),
            "proposal_id": proposal_id,
            "user_id": user_id,
            "votes": vote.votes,
            "direction": vote.direction,
            "cost": cost,
            "created_at": now
        })

        # Update proposal
        if vote.direction:
            await db.proposals.update_one(
                {"id": proposal_id},
                {"$inc": {"total_voting_power_for": vote.votes}}
            )
        else:
            await db.proposals.update_one(
                {"id": proposal_id},
                {"$inc": {"total_voting_power_against": vote.votes}}
            )

        # Record transaction
        await token_service.create_transaction(
            user_id=user_id,
            tx_type="debit",
            amount=cost,
            description=f"Quadratic voting: {vote.votes} votes on proposal {proposal_id[:8]}"
        )

        return {
            "message": "Quadratic votes cast",
            "votes": vote.votes,
            "direction": "for" if vote.direction else "against",
            "cost": cost,
            "effective_power": vote.votes
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/proposals/{proposal_id}/execute")
async def execute_proposal(
    proposal_id: str,
    current_user: dict = Depends(require_admin)
):
    """Execute a passed proposal after delay period"""
    try:
        proposal = await db.proposals.find_one({"id": proposal_id})
        if not proposal:
            raise HTTPException(status_code=404, detail="Proposal not found")

        if proposal["status"] != "passed":
            raise HTTPException(status_code=400, detail="Proposal must be passed first")

        # Check execution delay
        passed_at = datetime.fromisoformat(proposal.get("passed_at", proposal["created_at"]).replace('Z', '+00:00'))
        delay_hours = proposal.get("execution_delay_hours", 24)
        can_execute_at = passed_at + timedelta(hours=delay_hours)

        if datetime.now(timezone.utc) < can_execute_at:
            raise HTTPException(
                status_code=400,
                detail=f"Execution delay not met. Can execute at {can_execute_at.isoformat()}"
            )

        now = datetime.now(timezone.utc).isoformat()

        await db.proposals.update_one(
            {"id": proposal_id},
            {"$set": {
                "status": "executed",
                "executed_at": now,
                "executed_by": current_user["id"]
            }}
        )

        # If budget proposal, allocate from treasury
        if proposal.get("proposal_type") == "budget" and proposal.get("budget_request"):
            await db.treasury_allocations.insert_one({
                "id": str(uuid.uuid4()),
                "proposal_id": proposal_id,
                "amount": proposal["budget_request"],
                "category": "proposal_execution",
                "description": f"Budget allocation for proposal: {proposal['title']}",
                "allocated_at": now
            })

        # Notify proposer
        await send_notification(
            user_id=proposal["proposer_id"],
            title="Proposal Executed",
            message=f"Your proposal '{proposal['title']}' has been executed.",
            category="governance"
        )

        return {"message": "Proposal executed", "executed_at": now}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ===================== DELEGATION =====================

@router.post("/delegate")
async def delegate_voting_power(
    delegation: DelegationCreate,
    current_user: dict = Depends(get_current_user)
):
    """Delegate voting power to another user"""
    try:
        if delegation.delegate_to == current_user["id"]:
            raise HTTPException(status_code=400, detail="Cannot delegate to yourself")

        # Verify delegate exists
        delegate = await db.users.find_one({"id": delegation.delegate_to})
        if not delegate:
            raise HTTPException(status_code=404, detail="Delegate user not found")

        # Check for existing active delegation
        existing = await db.vote_delegations.find_one({
            "user_id": current_user["id"],
            "is_active": True
        })

        if existing:
            raise HTTPException(
                status_code=400,
                detail="Already have an active delegation. Revoke it first."
            )

        delegation_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        await db.vote_delegations.insert_one({
            "id": delegation_id,
            "user_id": current_user["id"],
            "delegate_to": delegation.delegate_to,
            "categories": delegation.categories,
            "expires_at": delegation.expires_at,
            "is_active": True,
            "created_at": now
        })

        # Notify delegate
        await send_notification(
            user_id=delegation.delegate_to,
            title="Voting Power Delegated",
            message=f"{current_user['username']} has delegated their voting power to you.",
            category="governance"
        )

        return {
            "message": "Voting power delegated",
            "delegation_id": delegation_id,
            "delegate_to": delegate.get("username")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/delegate")
async def revoke_delegation(current_user: dict = Depends(get_current_user)):
    """Revoke active delegation"""
    try:
        result = await db.vote_delegations.update_one(
            {"user_id": current_user["id"], "is_active": True},
            {"$set": {
                "is_active": False,
                "revoked_at": datetime.now(timezone.utc).isoformat()
            }}
        )

        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="No active delegation found")

        return {"message": "Delegation revoked"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/delegation/status")
async def get_delegation_status(current_user: dict = Depends(get_current_user)):
    """Get current delegation status"""
    try:
        user_id = current_user["id"]

        # My active delegation
        my_delegation = await db.vote_delegations.find_one(
            {"user_id": user_id, "is_active": True},
            {"_id": 0}
        )

        if my_delegation:
            delegate = await db.users.find_one(
                {"id": my_delegation["delegate_to"]},
                {"_id": 0, "username": 1}
            )
            if delegate:
                my_delegation["delegate_username"] = delegate.get("username")

        # Delegations to me
        delegations_to_me = await db.vote_delegations.find(
            {"delegate_to": user_id, "is_active": True},
            {"_id": 0}
        ).to_list(50)

        # Enrich with user info
        for d in delegations_to_me:
            user = await db.users.find_one(
                {"id": d["user_id"]},
                {"_id": 0, "username": 1}
            )
            if user:
                d["from_username"] = user.get("username")

        return {
            "my_delegation": my_delegation,
            "delegations_to_me": delegations_to_me,
            "total_delegated_power": len(delegations_to_me) * 0.5
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ===================== TREASURY =====================

@router.get("/treasury/balance")
async def get_treasury_balance():
    """Get DAO treasury balance and allocations"""
    try:
        # Get treasury record
        treasury = await db.dao_treasury.find_one({"id": "main_treasury"})

        if not treasury:
            # Initialize treasury if not exists
            treasury = {
                "id": "main_treasury",
                "total_balance": 1000000,  # Initial treasury
                "allocated": 0,
                "available": 1000000,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            await db.dao_treasury.insert_one(treasury)

        # Get recent allocations
        allocations = await db.treasury_allocations.find(
            {},
            {"_id": 0}
        ).sort("allocated_at", -1).limit(20).to_list(20)

        # Get allocation by category
        category_pipeline = [
            {"$group": {"_id": "$category", "total": {"$sum": "$amount"}}}
        ]
        category_result = await db.treasury_allocations.aggregate(category_pipeline).to_list(None)
        by_category = {item["_id"]: item["total"] for item in category_result if item["_id"]}

        return {
            "treasury": {
                "total_balance": treasury.get("total_balance", 0),
                "allocated": treasury.get("allocated", 0),
                "available": treasury.get("available", treasury.get("total_balance", 0))
            },
            "recent_allocations": allocations,
            "by_category": by_category
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/treasury/allocate")
async def allocate_treasury_funds(
    allocation: TreasuryAllocation,
    current_user: dict = Depends(require_admin)
):
    """Allocate treasury funds (admin only, requires proposal)"""
    try:
        treasury = await db.dao_treasury.find_one({"id": "main_treasury"})
        if not treasury:
            raise HTTPException(status_code=400, detail="Treasury not initialized")

        available = treasury.get("available", 0)
        if allocation.amount > available:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient treasury funds. Available: {available}"
            )

        allocation_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        await db.treasury_allocations.insert_one({
            "id": allocation_id,
            "category": allocation.category,
            "amount": allocation.amount,
            "description": allocation.description,
            "recipient_type": allocation.recipient_type,
            "recipient_id": allocation.recipient_id,
            "allocated_by": current_user["id"],
            "allocated_at": now
        })

        # Update treasury
        await db.dao_treasury.update_one(
            {"id": "main_treasury"},
            {
                "$inc": {
                    "allocated": allocation.amount,
                    "available": -allocation.amount
                },
                "$set": {"last_updated": now}
            }
        )

        return {
            "message": "Funds allocated",
            "allocation_id": allocation_id,
            "amount": allocation.amount
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/treasury/budget-proposals")
async def get_budget_proposals():
    """Get pending budget proposals"""
    try:
        proposals = await db.proposals.find(
            {"proposal_type": "budget", "status": {"$in": ["active", "passed"]}},
            {"_id": 0}
        ).sort("created_at", -1).to_list(50)

        total_requested = sum(p.get("budget_request", 0) for p in proposals if p.get("status") == "active")

        return {
            "proposals": proposals,
            "total_active_requests": total_requested
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ===================== CITY ZONES =====================

@router.get("/city/zones")
async def get_city_zones():
    """Get all city zones in the metaverse"""
    try:
        zones = await db.zones.find({}, {"_id": 0}).to_list(100)

        # Add job counts and active users
        for zone in zones:
            job_count = await db.jobs.count_documents({"zone": zone["id"]})
            zone["jobs_count"] = job_count

        return {"zones": zones}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ===================== STATS =====================

@router.get("/stats")
async def get_dao_stats():
    """Get comprehensive DAO statistics"""
    try:
        total_proposals = await db.proposals.count_documents({})
        active_proposals = await db.proposals.count_documents({"status": "active"})
        passed_proposals = await db.proposals.count_documents({"status": "passed"})
        executed_proposals = await db.proposals.count_documents({"status": "executed"})

        total_votes = await db.votes.count_documents({})
        total_delegations = await db.vote_delegations.count_documents({"is_active": True})

        # Treasury info
        treasury = await db.dao_treasury.find_one({"id": "main_treasury"})
        treasury_balance = treasury.get("available", 0) if treasury else 0

        # Participation rate
        total_users = await db.users.count_documents({})
        users_who_voted = len(set([v["user_id"] async for v in db.votes.find({}, {"user_id": 1})]))
        participation_rate = (users_who_voted / total_users * 100) if total_users > 0 else 0

        return {
            "stats": {
                "total_proposals": total_proposals,
                "active_proposals": active_proposals,
                "passed_proposals": passed_proposals,
                "executed_proposals": executed_proposals,
                "total_votes": total_votes,
                "active_delegations": total_delegations,
                "treasury_available": treasury_balance,
                "participation_rate": round(participation_rate, 2)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/governance-parameters")
async def get_governance_parameters():
    """Get current governance parameters"""
    return {
        "parameters": {
            "min_proposal_level": 2,
            "default_voting_days": 7,
            "default_quorum_percentage": 10,
            "execution_delay_hours": 24,
            "quadratic_voting_enabled": True,
            "delegation_enabled": True,
            "max_budget_per_proposal": 100000,
            "emergency_proposal_quorum": 25
        },
        "voting_options": [
            {"key": "simple", "name": "Simple Voting", "description": "1 user = 1 vote"},
            {"key": "weighted", "name": "Weighted Voting", "description": "Based on level and delegation"},
            {"key": "quadratic", "name": "Quadratic Voting", "description": "Cost = votes^2 tokens"}
        ],
        "proposal_types": [
            {"key": "general", "name": "General", "description": "General governance proposals"},
            {"key": "budget", "name": "Budget", "description": "Treasury fund allocation"},
            {"key": "parameter", "name": "Parameter", "description": "Change governance parameters"},
            {"key": "emergency", "name": "Emergency", "description": "Urgent matters requiring quick action"}
        ]
    }
