from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel
import uuid

from core.database import db
from core.auth import get_current_user, require_admin
from services.token_service import create_transaction

router = APIRouter(prefix="/advanced", tags=["Advanced Features"])

# M181-185: DAO Advanced Features
class VoteDelegation(BaseModel):
    delegate_id: str
    dao_id: Optional[str] = None

@router.post("/dao/delegate")
async def delegate_vote(delegation: VoteDelegation, current_user: dict = Depends(get_current_user)):
    """Delegate voting power to another user"""
    await db.dao_vote_delegations.insert_one({
        "id": str(uuid.uuid4()),
        "delegator_id": current_user["id"],
        "delegate_id": delegation.delegate_id,
        "dao_id": delegation.dao_id,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    return {"message": "Vote delegated successfully"}

@router.get("/dao/delegations")
async def get_delegations(current_user: dict = Depends(get_current_user)):
    """Get user's vote delegations"""
    delegations = await db.dao_vote_delegations.find(
        {"delegator_id": current_user["id"], "is_active": True},
        {"_id": 0}
    ).to_list(100)
    return {"delegations": delegations}

# M186-190: Treasury Management
@router.get("/dao/{dao_id}/treasury")
async def get_dao_treasury(dao_id: str):
    """Get DAO treasury status"""
    treasury = await db.dao_treasury.find_one({"dao_id": dao_id}, {"_id": 0})
    if not treasury:
        treasury = {"dao_id": dao_id, "balance_rlm": 0, "total_income": 0, "total_expenses": 0}
    return treasury

@router.get("/dao/{dao_id}/budget")
async def get_dao_budget(dao_id: str):
    """Get DAO budget allocations"""
    allocations = await db.dao_budget_allocations.find(
        {"dao_id": dao_id, "status": "active"},
        {"_id": 0}
    ).to_list(100)
    return {"budget_allocations": allocations}

# M191: Partner Integration
class PartnerAPIKeyCreate(BaseModel):
    permissions: List[str] = []

@router.post("/partner/api-key")
async def create_partner_api_key(data: PartnerAPIKeyCreate, current_user: dict = Depends(get_current_user)):
    """Create partner API key"""
    api_key = f"pk_{uuid.uuid4().hex}"
    api_secret = f"sk_{uuid.uuid4().hex}"

    await db.partner_api_keys.insert_one({
        "id": str(uuid.uuid4()),
        "partner_id": current_user["id"],
        "api_key": api_key,
        "api_secret": api_secret,
        "is_active": True,
        "rate_limit": 1000,
        "permissions": data.permissions,
        "created_at": datetime.now(timezone.utc).isoformat()
    })

    return {"api_key": api_key, "api_secret": api_secret, "message": "Store securely"}

@router.get("/partner/api-keys")
async def list_partner_api_keys(current_user: dict = Depends(get_current_user)):
    """List partner API keys"""
    keys = await db.partner_api_keys.find(
        {"partner_id": current_user["id"]},
        {"_id": 0, "api_secret": 0}
    ).to_list(100)
    return {"api_keys": keys}

# M192: Advanced Analytics
class ReportCreate(BaseModel):
    report_name: str
    report_type: str
    query_config: dict
    schedule: str = "manual"

@router.post("/analytics/reports")
async def create_custom_report(report: ReportCreate, current_user: dict = Depends(get_current_user)):
    """Create custom analytics report"""
    report_id = str(uuid.uuid4())

    await db.custom_reports.insert_one({
        "id": report_id,
        "user_id": current_user["id"],
        "report_name": report.report_name,
        "report_type": report.report_type,
        "query_config": report.query_config,
        "schedule": report.schedule,
        "is_public": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    })

    return {"message": "Report created", "report_id": report_id}

@router.get("/analytics/reports")
async def list_reports(current_user: dict = Depends(get_current_user)):
    """List user's custom reports"""
    reports = await db.custom_reports.find(
        {"user_id": current_user["id"]},
        {"_id": 0}
    ).to_list(100)
    return {"reports": reports}

# M193: Badge Evolution
@router.get("/badges/evolution/{badge_id}")
async def get_badge_evolution(badge_id: str):
    """Get badge evolution path"""
    evolution = await db.badge_evolution.find(
        {"badge_id": badge_id},
        {"_id": 0}
    ).sort("level", 1).to_list(10)
    return {"evolution_path": evolution}

@router.get("/badges/progress")
async def get_badge_progress(current_user: dict = Depends(get_current_user)):
    """Get user's badge progress"""
    progress = await db.user_badge_progress.find(
        {"user_id": current_user["id"]},
        {"_id": 0}
    ).to_list(100)
    return {"badge_progress": progress}

# M194-195: Feedback System
class FeedbackCreate(BaseModel):
    feedback_type: str
    title: str
    description: str
    category: str = "general"

@router.post("/feedback")
async def submit_feedback(feedback: FeedbackCreate, current_user: dict = Depends(get_current_user)):
    """Submit user feedback"""
    feedback_id = str(uuid.uuid4())

    await db.user_feedback.insert_one({
        "id": feedback_id,
        "user_id": current_user["id"],
        "feedback_type": feedback.feedback_type,
        "title": feedback.title,
        "description": feedback.description,
        "category": feedback.category,
        "status": "submitted",
        "upvotes": 0,
        "implemented": False,
        "reward_amount": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    })

    return {"message": "Feedback submitted", "feedback_id": feedback_id}

@router.post("/feedback/{feedback_id}/vote")
async def vote_feedback(feedback_id: str, current_user: dict = Depends(get_current_user)):
    """Upvote feedback"""
    try:
        await db.feedback_votes.insert_one({
            "id": str(uuid.uuid4()),
            "feedback_id": feedback_id,
            "user_id": current_user["id"],
            "created_at": datetime.now(timezone.utc).isoformat()
        })

        await db.user_feedback.update_one(
            {"id": feedback_id},
            {"$inc": {"upvotes": 1}}
        )
    except:
        raise HTTPException(status_code=400, detail="Already voted")

    return {"message": "Vote recorded"}

@router.get("/feedback")
async def list_feedback(skip: int = 0, limit: int = 20):
    """List all feedback"""
    feedback = await db.user_feedback.find(
        {},
        {"_id": 0}
    ).sort("upvotes", -1).skip(skip).limit(limit).to_list(limit)
    return {"feedback": feedback}

# M196: Task Bounties
class BountyCreate(BaseModel):
    title: str
    description: str
    category: str
    bounty_amount: int
    difficulty: str = "medium"
    required_skills: List[str] = []
    dao_id: Optional[str] = None

@router.post("/bounties")
async def create_bounty(bounty: BountyCreate, current_user: dict = Depends(get_current_user)):
    """Create task bounty"""
    bounty_id = str(uuid.uuid4())

    await db.task_bounties.insert_one({
        "id": bounty_id,
        "dao_id": bounty.dao_id,
        "title": bounty.title,
        "description": bounty.description,
        "category": bounty.category,
        "bounty_amount": bounty.bounty_amount,
        "difficulty": bounty.difficulty,
        "required_skills": bounty.required_skills,
        "creator_id": current_user["id"],
        "status": "open",
        "created_at": datetime.now(timezone.utc).isoformat()
    })

    return {"message": "Bounty created", "bounty_id": bounty_id}

@router.get("/bounties")
async def list_bounties(status: str = "open", skip: int = 0, limit: int = 20):
    """List task bounties"""
    bounties = await db.task_bounties.find(
        {"status": status},
        {"_id": 0}
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    return {"bounties": bounties}

@router.post("/bounties/{bounty_id}/apply")
async def apply_for_bounty(bounty_id: str, proposal: str, current_user: dict = Depends(get_current_user)):
    """Apply for a bounty"""
    try:
        await db.bounty_applications.insert_one({
            "id": str(uuid.uuid4()),
            "bounty_id": bounty_id,
            "applicant_id": current_user["id"],
            "proposal": proposal,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    except:
        raise HTTPException(status_code=400, detail="Already applied")

    return {"message": "Application submitted"}

# M197: Dispute Resolution
class DisputeCreate(BaseModel):
    dispute_type: str
    respondent_id: str
    title: str
    description: str
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None

@router.post("/disputes")
async def file_dispute(dispute: DisputeCreate, current_user: dict = Depends(get_current_user)):
    """File a dispute"""
    dispute_id = str(uuid.uuid4())

    await db.disputes.insert_one({
        "id": dispute_id,
        "dispute_type": dispute.dispute_type,
        "complainant_id": current_user["id"],
        "respondent_id": dispute.respondent_id,
        "related_entity_type": dispute.related_entity_type,
        "related_entity_id": dispute.related_entity_id,
        "title": dispute.title,
        "description": dispute.description,
        "evidence": [],
        "status": "open",
        "created_at": datetime.now(timezone.utc).isoformat()
    })

    return {"message": "Dispute filed", "dispute_id": dispute_id}

@router.get("/disputes")
async def list_disputes(current_user: dict = Depends(get_current_user)):
    """List user's disputes"""
    disputes = await db.disputes.find(
        {"$or": [
            {"complainant_id": current_user["id"]},
            {"respondent_id": current_user["id"]},
            {"arbitrator_id": current_user["id"]}
        ]},
        {"_id": 0}
    ).to_list(100)
    return {"disputes": disputes}

# M198: Reputation Engine
@router.get("/reputation/{user_id}")
async def get_user_reputation(user_id: str):
    """Get user reputation scores"""
    reputation = await db.user_reputation.find(
        {"user_id": user_id},
        {"_id": 0}
    ).to_list(10)
    return {"reputation": reputation}

class EndorsementCreate(BaseModel):
    endorsed_id: str
    reputation_type: str
    comment: Optional[str] = None
    strength: int = 1

@router.post("/reputation/endorse")
async def endorse_user(endorsement: EndorsementCreate, current_user: dict = Depends(get_current_user)):
    """Endorse another user"""
    try:
        await db.reputation_endorsements.insert_one({
            "id": str(uuid.uuid4()),
            "endorser_id": current_user["id"],
            "endorsed_id": endorsement.endorsed_id,
            "reputation_type": endorsement.reputation_type,
            "comment": endorsement.comment,
            "strength": endorsement.strength,
            "created_at": datetime.now(timezone.utc).isoformat()
        })

        # Update reputation score
        await db.user_reputation.update_one(
            {"user_id": endorsement.endorsed_id, "reputation_type": endorsement.reputation_type},
            {
                "$inc": {"score": endorsement.strength * 10, "endorsements": 1},
                "$set": {"last_calculated_at": datetime.now(timezone.utc).isoformat()}
            },
            upsert=True
        )
    except:
        raise HTTPException(status_code=400, detail="Already endorsed")

    return {"message": "Endorsement recorded"}

# M199: Sub-DAO System
class SubDAOCreate(BaseModel):
    parent_dao_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    purpose: str
    budget_allocation: int = 0

@router.post("/sub-daos")
async def create_sub_dao(sub_dao: SubDAOCreate, current_user: dict = Depends(get_current_user)):
    """Create a sub-DAO"""
    sub_dao_id = str(uuid.uuid4())

    await db.sub_daos.insert_one({
        "id": sub_dao_id,
        "parent_dao_id": sub_dao.parent_dao_id,
        "name": sub_dao.name,
        "description": sub_dao.description,
        "purpose": sub_dao.purpose,
        "budget_allocation": sub_dao.budget_allocation,
        "member_count": 1,
        "is_autonomous": False,
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc).isoformat()
    })

    # Add creator as lead
    await db.sub_dao_members.insert_one({
        "id": str(uuid.uuid4()),
        "sub_dao_id": sub_dao_id,
        "user_id": current_user["id"],
        "role": "lead",
        "joined_at": datetime.now(timezone.utc).isoformat()
    })

    return {"message": "Sub-DAO created", "sub_dao_id": sub_dao_id}

@router.get("/sub-daos")
async def list_sub_daos(parent_dao_id: Optional[str] = None):
    """List sub-DAOs"""
    query = {}
    if parent_dao_id:
        query["parent_dao_id"] = parent_dao_id

    sub_daos = await db.sub_daos.find(query, {"_id": 0}).to_list(100)
    return {"sub_daos": sub_daos}

@router.post("/sub-daos/{sub_dao_id}/join")
async def join_sub_dao(sub_dao_id: str, current_user: dict = Depends(get_current_user)):
    """Join a sub-DAO"""
    try:
        await db.sub_dao_members.insert_one({
            "id": str(uuid.uuid4()),
            "sub_dao_id": sub_dao_id,
            "user_id": current_user["id"],
            "role": "member",
            "joined_at": datetime.now(timezone.utc).isoformat()
        })

        await db.sub_daos.update_one(
            {"id": sub_dao_id},
            {"$inc": {"member_count": 1}}
        )
    except:
        raise HTTPException(status_code=400, detail="Already a member")

    return {"message": "Joined sub-DAO successfully"}
