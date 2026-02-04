from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone
import uuid
from core.auth import get_current_user, require_admin
from core.database import db
from services.token_service import TokenService
from services.notification_service import send_notification

router = APIRouter(prefix="/api/subdaos", tags=["SubDAOs"])
token_service = TokenService()

class SubDAOCreate(BaseModel):
    name: str
    description: str
    category: str
    parent_dao_id: Optional[str] = None
    budget_request: float = 0
    governance_model: str = "simple_majority"
    mission: Optional[str] = None
    goals: List[str] = []

class BudgetAllocation(BaseModel):
    amount: float
    purpose: str

class MemberInvite(BaseModel):
    user_id: str
    role: str = "member"

class SubDAOProposalCreate(BaseModel):
    title: str
    description: str
    proposal_type: str  # budget, membership, governance, project
    budget_amount: Optional[float] = None
    voting_duration_days: int = 7

@router.post("/create")
async def create_subdao(subdao: SubDAOCreate, current_user: dict = Depends(get_current_user)):
    """Create a new Sub-DAO"""
    try:
        subdao_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        subdao_data = {
            "id": subdao_id,
            "name": subdao.name,
            "description": subdao.description,
            "category": subdao.category,
            "parent_dao_id": subdao.parent_dao_id,
            "creator_id": current_user["id"],
            "budget_allocated": 0,
            "budget_requested": subdao.budget_request,
            "governance_model": subdao.governance_model,
            "mission": subdao.mission,
            "goals": subdao.goals,
            "status": "pending_approval",
            "member_count": 1,
            "proposal_count": 0,
            "created_at": now,
            "updated_at": now
        }

        await db.subdaos.insert_one(subdao_data)

        # Add creator as founder
        await db.subdao_members.insert_one({
            "id": str(uuid.uuid4()),
            "subdao_id": subdao_id,
            "user_id": current_user["id"],
            "role": "founder",
            "voting_power": 100,
            "joined_at": now
        })

        return {
            "message": "Sub-DAO created successfully",
            "subdao_id": subdao_id
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/list")
async def list_subdaos(
    status: Optional[str] = None,
    category: Optional[str] = None,
    parent_dao_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """List Sub-DAOs"""
    try:
        query = {}
        if status:
            query["status"] = status
        if category:
            query["category"] = category
        if parent_dao_id:
            query["parent_dao_id"] = parent_dao_id

        subdaos = await db.subdaos.find(
            query, {"_id": 0}
        ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)

        # Enrich with creator info
        for subdao in subdaos:
            creator = await db.users.find_one(
                {"id": subdao["creator_id"]},
                {"_id": 0, "username": 1, "avatar_url": 1}
            )
            if creator:
                subdao["creator_username"] = creator.get("username")
                subdao["creator_avatar"] = creator.get("avatar_url")

        total = await db.subdaos.count_documents(query)

        return {"subdaos": subdaos, "total": total}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{subdao_id}")
async def get_subdao_details(subdao_id: str, current_user: dict = Depends(get_current_user)):
    """Get Sub-DAO details"""
    try:
        subdao = await db.subdaos.find_one({"id": subdao_id}, {"_id": 0})

        if not subdao:
            raise HTTPException(status_code=404, detail="Sub-DAO not found")

        # Get creator info
        creator = await db.users.find_one(
            {"id": subdao["creator_id"]},
            {"_id": 0, "username": 1, "avatar_url": 1}
        )
        if creator:
            subdao["creator_username"] = creator.get("username")
            subdao["creator_avatar"] = creator.get("avatar_url")

        # Get members
        members = await db.subdao_members.find(
            {"subdao_id": subdao_id},
            {"_id": 0}
        ).to_list(100)

        # Enrich members
        for member in members:
            user = await db.users.find_one(
                {"id": member["user_id"]},
                {"_id": 0, "username": 1, "avatar_url": 1}
            )
            if user:
                member["username"] = user.get("username")
                member["avatar_url"] = user.get("avatar_url")

        # Get proposals
        proposals = await db.subdao_proposals.find(
            {"subdao_id": subdao_id},
            {"_id": 0}
        ).sort("created_at", -1).to_list(50)

        # Get budget allocations
        allocations = await db.subdao_budget_allocations.find(
            {"subdao_id": subdao_id},
            {"_id": 0}
        ).sort("created_at", -1).to_list(20)

        # Check if current user is member
        user_membership = next(
            (m for m in members if m["user_id"] == current_user["id"]),
            None
        )

        return {
            "subdao": subdao,
            "members": members,
            "proposals": proposals,
            "budget_allocations": allocations,
            "user_membership": user_membership
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{subdao_id}/join")
async def join_subdao(subdao_id: str, current_user: dict = Depends(get_current_user)):
    """Request to join a Sub-DAO"""
    try:
        subdao = await db.subdaos.find_one({"id": subdao_id})
        
        if not subdao:
            raise HTTPException(status_code=404, detail="Sub-DAO not found")

        if subdao["status"] != "active":
            raise HTTPException(status_code=400, detail="Sub-DAO is not active")

        # Check if already member
        existing = await db.subdao_members.find_one({
            "subdao_id": subdao_id,
            "user_id": current_user["id"]
        })

        if existing:
            raise HTTPException(status_code=400, detail="Already a member")

        now = datetime.now(timezone.utc).isoformat()

        await db.subdao_members.insert_one({
            "id": str(uuid.uuid4()),
            "subdao_id": subdao_id,
            "user_id": current_user["id"],
            "role": "member",
            "voting_power": 10,
            "joined_at": now
        })

        # Update member count
        await db.subdaos.update_one(
            {"id": subdao_id},
            {"$inc": {"member_count": 1}}
        )

        return {"message": "Successfully joined Sub-DAO"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{subdao_id}/invite")
async def invite_member(
    subdao_id: str,
    invite: MemberInvite,
    current_user: dict = Depends(get_current_user)
):
    """Invite a member to Sub-DAO"""
    try:
        # Check if requester is admin/founder
        requester = await db.subdao_members.find_one({
            "subdao_id": subdao_id,
            "user_id": current_user["id"]
        })

        if not requester or requester["role"] not in ["founder", "admin"]:
            raise HTTPException(status_code=403, detail="Only founders and admins can invite")

        # Check if user exists
        user = await db.users.find_one({"id": invite.user_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Check if already member
        existing = await db.subdao_members.find_one({
            "subdao_id": subdao_id,
            "user_id": invite.user_id
        })

        if existing:
            raise HTTPException(status_code=400, detail="User is already a member")

        now = datetime.now(timezone.utc).isoformat()

        await db.subdao_members.insert_one({
            "id": str(uuid.uuid4()),
            "subdao_id": subdao_id,
            "user_id": invite.user_id,
            "role": invite.role,
            "voting_power": 10,
            "invited_by": current_user["id"],
            "joined_at": now
        })

        await db.subdaos.update_one(
            {"id": subdao_id},
            {"$inc": {"member_count": 1}}
        )

        # Notify invited user
        subdao = await db.subdaos.find_one({"id": subdao_id}, {"_id": 0, "name": 1})
        await send_notification(
            user_id=invite.user_id,
            title="Sub-DAO Invitation",
            message=f"You've been invited to join {subdao['name']}",
            category="governance"
        )

        return {"message": "Member invited successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{subdao_id}/proposals")
async def create_subdao_proposal(
    subdao_id: str,
    proposal: SubDAOProposalCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a proposal within a Sub-DAO"""
    try:
        # Check membership
        member = await db.subdao_members.find_one({
            "subdao_id": subdao_id,
            "user_id": current_user["id"]
        })

        if not member:
            raise HTTPException(status_code=403, detail="Not a member of this Sub-DAO")

        proposal_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        end_date = now + timedelta(days=proposal.voting_duration_days)

        proposal_data = {
            "id": proposal_id,
            "subdao_id": subdao_id,
            "creator_id": current_user["id"],
            "title": proposal.title,
            "description": proposal.description,
            "proposal_type": proposal.proposal_type,
            "budget_amount": proposal.budget_amount,
            "status": "active",
            "votes_for": 0,
            "votes_against": 0,
            "voting_ends_at": end_date.isoformat(),
            "created_at": now.isoformat()
        }

        await db.subdao_proposals.insert_one(proposal_data)

        await db.subdaos.update_one(
            {"id": subdao_id},
            {"$inc": {"proposal_count": 1}}
        )

        return {
            "message": "Proposal created successfully",
            "proposal_id": proposal_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{subdao_id}/proposals/{proposal_id}/vote")
async def vote_on_subdao_proposal(
    subdao_id: str,
    proposal_id: str,
    vote: bool,  # True = for, False = against
    current_user: dict = Depends(get_current_user)
):
    """Vote on a Sub-DAO proposal"""
    try:
        # Check membership
        member = await db.subdao_members.find_one({
            "subdao_id": subdao_id,
            "user_id": current_user["id"]
        })

        if not member:
            raise HTTPException(status_code=403, detail="Not a member")

        # Check proposal
        proposal = await db.subdao_proposals.find_one({"id": proposal_id})
        if not proposal:
            raise HTTPException(status_code=404, detail="Proposal not found")

        if proposal["status"] != "active":
            raise HTTPException(status_code=400, detail="Voting has ended")

        # Check existing vote
        existing = await db.subdao_votes.find_one({
            "proposal_id": proposal_id,
            "user_id": current_user["id"]
        })

        if existing:
            raise HTTPException(status_code=400, detail="Already voted")

        voting_power = member.get("voting_power", 10)
        now = datetime.now(timezone.utc).isoformat()

        await db.subdao_votes.insert_one({
            "id": str(uuid.uuid4()),
            "proposal_id": proposal_id,
            "subdao_id": subdao_id,
            "user_id": current_user["id"],
            "vote": vote,
            "voting_power": voting_power,
            "created_at": now
        })

        # Update vote counts
        if vote:
            await db.subdao_proposals.update_one(
                {"id": proposal_id},
                {"$inc": {"votes_for": voting_power}}
            )
        else:
            await db.subdao_proposals.update_one(
                {"id": proposal_id},
                {"$inc": {"votes_against": voting_power}}
            )

        return {"message": "Vote recorded", "voting_power": voting_power}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{subdao_id}/allocate-budget")
async def allocate_budget(
    subdao_id: str,
    allocation: BudgetAllocation,
    current_user: dict = Depends(require_admin)
):
    """Allocate budget to a Sub-DAO (admin only)"""
    try:
        subdao = await db.subdaos.find_one({"id": subdao_id})

        if not subdao:
            raise HTTPException(status_code=404, detail="Sub-DAO not found")

        if subdao["status"] != "active":
            raise HTTPException(status_code=400, detail="Sub-DAO must be active")

        now = datetime.now(timezone.utc).isoformat()

        # Update budget
        await db.subdaos.update_one(
            {"id": subdao_id},
            {"$inc": {"budget_allocated": allocation.amount}}
        )

        # Record allocation
        await db.subdao_budget_allocations.insert_one({
            "id": str(uuid.uuid4()),
            "subdao_id": subdao_id,
            "amount": allocation.amount,
            "purpose": allocation.purpose,
            "allocated_by": current_user["id"],
            "created_at": now
        })

        new_budget = subdao.get("budget_allocated", 0) + allocation.amount

        return {
            "message": "Budget allocated successfully",
            "new_budget": new_budget
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{subdao_id}/approve")
async def approve_subdao(subdao_id: str, current_user: dict = Depends(require_admin)):
    """Approve a pending Sub-DAO (admin only)"""
    try:
        subdao = await db.subdaos.find_one({"id": subdao_id})

        if not subdao:
            raise HTTPException(status_code=404, detail="Sub-DAO not found")

        if subdao["status"] != "pending_approval":
            raise HTTPException(status_code=400, detail="Sub-DAO is not pending approval")

        now = datetime.now(timezone.utc).isoformat()

        await db.subdaos.update_one(
            {"id": subdao_id},
            {"$set": {
                "status": "active",
                "approved_by": current_user["id"],
                "approved_at": now,
                "updated_at": now
            }}
        )

        # Notify creator
        await send_notification(
            user_id=subdao["creator_id"],
            title="Sub-DAO Approved!",
            message=f"Your Sub-DAO '{subdao['name']}' has been approved.",
            category="governance"
        )

        return {"message": "Sub-DAO approved successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/my-subdaos")
async def get_my_subdaos(current_user: dict = Depends(get_current_user)):
    """Get Sub-DAOs user is involved in"""
    try:
        user_id = current_user["id"]

        # Created by user
        created = await db.subdaos.find(
            {"creator_id": user_id},
            {"_id": 0}
        ).to_list(50)

        # Member of
        memberships = await db.subdao_members.find(
            {"user_id": user_id},
            {"_id": 0, "subdao_id": 1, "role": 1}
        ).to_list(50)

        member_ids = [m["subdao_id"] for m in memberships]
        member_subdaos = []
        
        if member_ids:
            member_subdaos = await db.subdaos.find(
                {"id": {"$in": member_ids}},
                {"_id": 0}
            ).to_list(50)

        return {
            "created_subdaos": created,
            "member_subdaos": member_subdaos,
            "memberships": memberships
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/hierarchy")
async def get_dao_hierarchy():
    """Get hierarchical view of all Sub-DAOs"""
    try:
        all_subdaos = await db.subdaos.find(
            {"status": "active"},
            {"_id": 0}
        ).to_list(100)

        # Build tree structure
        root_daos = []
        child_daos = {}

        for subdao in all_subdaos:
            parent_id = subdao.get("parent_dao_id")
            if not parent_id:
                root_daos.append(subdao)
            else:
                if parent_id not in child_daos:
                    child_daos[parent_id] = []
                child_daos[parent_id].append(subdao)

        def build_tree(dao):
            dao_id = dao["id"]
            dao["children"] = child_daos.get(dao_id, [])
            for child in dao["children"]:
                build_tree(child)
            return dao

        hierarchy = [build_tree(dao) for dao in root_daos]

        return {"hierarchy": hierarchy}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/stats")
async def get_subdao_stats():
    """Get Sub-DAO statistics"""
    try:
        total = await db.subdaos.count_documents({})

        # Total budget
        budget_pipeline = [
            {"$group": {"_id": None, "total": {"$sum": "$budget_allocated"}}}
        ]
        budget_result = await db.subdaos.aggregate(budget_pipeline).to_list(1)
        total_budget = budget_result[0]["total"] if budget_result else 0

        # Status breakdown
        status_pipeline = [
            {"$group": {"_id": "$status", "count": {"$sum": 1}}}
        ]
        status_result = await db.subdaos.aggregate(status_pipeline).to_list(None)
        status_breakdown = {item["_id"]: item["count"] for item in status_result if item["_id"]}

        # Category breakdown
        category_pipeline = [
            {"$group": {"_id": "$category", "count": {"$sum": 1}}}
        ]
        category_result = await db.subdaos.aggregate(category_pipeline).to_list(None)
        category_breakdown = {item["_id"]: item["count"] for item in category_result if item["_id"]}

        # Total members
        total_members = await db.subdao_members.count_documents({})

        return {
            "stats": {
                "total_subdaos": total,
                "total_budget_allocated": total_budget,
                "total_members": total_members,
                "status_breakdown": status_breakdown,
                "category_breakdown": category_breakdown
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/categories")
async def get_subdao_categories():
    """Get available Sub-DAO categories"""
    return {
        "categories": [
            {"key": "education", "name": "Education", "description": "Educational initiatives"},
            {"key": "development", "name": "Development", "description": "Technical development"},
            {"key": "community", "name": "Community", "description": "Community building"},
            {"key": "marketing", "name": "Marketing", "description": "Marketing and outreach"},
            {"key": "research", "name": "Research", "description": "Research and analysis"},
            {"key": "governance", "name": "Governance", "description": "Governance improvements"},
            {"key": "events", "name": "Events", "description": "Events and meetups"},
            {"key": "other", "name": "Other", "description": "Other initiatives"}
        ],
        "governance_models": [
            {"key": "simple_majority", "name": "Simple Majority", "description": "50% + 1 votes needed"},
            {"key": "super_majority", "name": "Super Majority", "description": "66% votes needed"},
            {"key": "quadratic", "name": "Quadratic Voting", "description": "Square root voting power"},
            {"key": "conviction", "name": "Conviction Voting", "description": "Time-weighted voting"}
        ]
    }

from datetime import timedelta
