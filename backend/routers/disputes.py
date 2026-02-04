from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone
import uuid
from core.auth import get_current_user, require_admin
from core.database import db
from services.token_service import TokenService
from services.notification_service import send_notification

router = APIRouter(prefix="/api/disputes", tags=["Disputes"])
token_service = TokenService()

class DisputeCreate(BaseModel):
    dispute_type: str  # bounty, transaction, content, user_behavior
    subject_id: str
    subject_type: str  # bounty_id, tx_id, content_id, user_id
    description: str
    evidence_urls: Optional[List[str]] = []

class ArbitratorVote(BaseModel):
    decision: str  # favor_initiator, favor_respondent, split, dismiss
    reasoning: str

class EvidenceAdd(BaseModel):
    evidence_url: str
    description: str

@router.post("/create")
async def create_dispute(dispute: DisputeCreate, current_user: dict = Depends(get_current_user)):
    """Create a new dispute"""
    try:
        dispute_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        dispute_data = {
            "id": dispute_id,
            "initiator_id": current_user["id"],
            "dispute_type": dispute.dispute_type,
            "subject_id": dispute.subject_id,
            "subject_type": dispute.subject_type,
            "description": dispute.description,
            "evidence_urls": dispute.evidence_urls,
            "status": "pending",
            "severity": "medium",
            "votes_for_initiator": 0,
            "votes_for_respondent": 0,
            "created_at": now,
            "updated_at": now
        }

        await db.disputes.insert_one(dispute_data)

        return {
            "message": "Dispute created successfully",
            "dispute_id": dispute_id
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/list")
async def list_disputes(
    status: Optional[str] = None,
    dispute_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """List disputes"""
    try:
        query = {}
        if status:
            query["status"] = status
        if dispute_type:
            query["dispute_type"] = dispute_type

        disputes = await db.disputes.find(
            query, {"_id": 0}
        ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)

        # Enrich with initiator info
        for dispute in disputes:
            user = await db.users.find_one(
                {"id": dispute["initiator_id"]},
                {"_id": 0, "username": 1, "avatar_url": 1}
            )
            if user:
                dispute["initiator_username"] = user.get("username")
                dispute["initiator_avatar"] = user.get("avatar_url")

        total = await db.disputes.count_documents(query)

        return {"disputes": disputes, "total": total}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{dispute_id}")
async def get_dispute_details(dispute_id: str, current_user: dict = Depends(get_current_user)):
    """Get dispute details"""
    try:
        dispute = await db.disputes.find_one({"id": dispute_id}, {"_id": 0})

        if not dispute:
            raise HTTPException(status_code=404, detail="Dispute not found")

        # Get initiator info
        initiator = await db.users.find_one(
            {"id": dispute["initiator_id"]},
            {"_id": 0, "username": 1, "avatar_url": 1}
        )
        if initiator:
            dispute["initiator_username"] = initiator.get("username")
            dispute["initiator_avatar"] = initiator.get("avatar_url")

        # Get votes
        votes = await db.dispute_votes.find(
            {"dispute_id": dispute_id},
            {"_id": 0}
        ).to_list(50)

        # Enrich votes with arbitrator info
        for vote in votes:
            arb = await db.users.find_one(
                {"id": vote["arbitrator_id"]},
                {"_id": 0, "username": 1}
            )
            if arb:
                vote["arbitrator_username"] = arb.get("username")

        # Get arbitrators
        arbitrators = await db.dispute_arbitrators.find(
            {"dispute_id": dispute_id},
            {"_id": 0}
        ).to_list(10)

        return {
            "dispute": dispute,
            "votes": votes,
            "arbitrators": arbitrators
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{dispute_id}/add-evidence")
async def add_evidence(
    dispute_id: str,
    evidence: EvidenceAdd,
    current_user: dict = Depends(get_current_user)
):
    """Add evidence to a dispute"""
    try:
        dispute = await db.disputes.find_one({"id": dispute_id})
        
        if not dispute:
            raise HTTPException(status_code=404, detail="Dispute not found")

        if dispute["initiator_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Only initiator can add evidence")

        if dispute["status"] not in ["pending", "in_arbitration"]:
            raise HTTPException(status_code=400, detail="Cannot add evidence at this stage")

        evidence_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        await db.dispute_evidence.insert_one({
            "id": evidence_id,
            "dispute_id": dispute_id,
            "added_by": current_user["id"],
            "evidence_url": evidence.evidence_url,
            "description": evidence.description,
            "created_at": now
        })

        return {"message": "Evidence added successfully", "evidence_id": evidence_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/assign-arbitrators/{dispute_id}")
async def assign_arbitrators(
    dispute_id: str,
    arbitrator_ids: List[str],
    current_user: dict = Depends(require_admin)
):
    """Assign arbitrators to a dispute (admin only)"""
    try:
        dispute = await db.disputes.find_one({"id": dispute_id})

        if not dispute:
            raise HTTPException(status_code=404, detail="Dispute not found")

        if dispute["status"] != "pending":
            raise HTTPException(status_code=400, detail="Can only assign arbitrators to pending disputes")

        now = datetime.now(timezone.utc).isoformat()

        for arbitrator_id in arbitrator_ids:
            # Verify arbitrator exists
            arb = await db.users.find_one({"id": arbitrator_id})
            if not arb:
                continue

            await db.dispute_arbitrators.insert_one({
                "id": str(uuid.uuid4()),
                "dispute_id": dispute_id,
                "arbitrator_id": arbitrator_id,
                "status": "assigned",
                "assigned_at": now
            })

            # Notify arbitrator
            await send_notification(
                user_id=arbitrator_id,
                title="Assigned as Arbitrator",
                message=f"You have been assigned to arbitrate dispute #{dispute_id[:8]}",
                category="governance"
            )

        await db.disputes.update_one(
            {"id": dispute_id},
            {"$set": {"status": "in_arbitration", "updated_at": now}}
        )

        return {"message": f"Assigned {len(arbitrator_ids)} arbitrators"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/vote/{dispute_id}")
async def vote_on_dispute(
    dispute_id: str,
    vote: ArbitratorVote,
    current_user: dict = Depends(get_current_user)
):
    """Vote on a dispute as an arbitrator"""
    try:
        # Check if user is assigned arbitrator
        assignment = await db.dispute_arbitrators.find_one({
            "dispute_id": dispute_id,
            "arbitrator_id": current_user["id"]
        })

        if not assignment:
            raise HTTPException(status_code=403, detail="You are not assigned as an arbitrator")

        # Check for existing vote
        existing = await db.dispute_votes.find_one({
            "dispute_id": dispute_id,
            "arbitrator_id": current_user["id"]
        })

        if existing:
            raise HTTPException(status_code=400, detail="You have already voted")

        now = datetime.now(timezone.utc).isoformat()

        await db.dispute_votes.insert_one({
            "id": str(uuid.uuid4()),
            "dispute_id": dispute_id,
            "arbitrator_id": current_user["id"],
            "decision": vote.decision,
            "reasoning": vote.reasoning,
            "created_at": now
        })

        # Count votes
        all_votes = await db.dispute_votes.find(
            {"dispute_id": dispute_id},
            {"_id": 0, "decision": 1}
        ).to_list(None)

        arbitrators_count = await db.dispute_arbitrators.count_documents({"dispute_id": dispute_id})

        # Check if all arbitrators voted
        if len(all_votes) >= arbitrators_count:
            # Count decisions
            decision_counts = {}
            for v in all_votes:
                d = v["decision"]
                decision_counts[d] = decision_counts.get(d, 0) + 1

            final_decision = max(decision_counts, key=decision_counts.get)

            await db.disputes.update_one(
                {"id": dispute_id},
                {"$set": {
                    "status": "resolved",
                    "resolution": final_decision,
                    "resolved_at": now
                }}
            )

            # Notify initiator
            dispute = await db.disputes.find_one({"id": dispute_id})
            await send_notification(
                user_id=dispute["initiator_id"],
                title="Dispute Resolved",
                message=f"Your dispute has been resolved. Decision: {final_decision}",
                category="governance"
            )

            return {
                "message": "Dispute resolved",
                "final_decision": final_decision
            }
        else:
            return {
                "message": "Vote recorded",
                "votes_remaining": arbitrators_count - len(all_votes)
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/escalate/{dispute_id}")
async def escalate_dispute(dispute_id: str, current_user: dict = Depends(get_current_user)):
    """Escalate dispute to tribunal"""
    try:
        dispute = await db.disputes.find_one({
            "id": dispute_id,
            "initiator_id": current_user["id"]
        })

        if not dispute:
            raise HTTPException(status_code=404, detail="Dispute not found or not your dispute")

        if dispute["status"] != "in_arbitration":
            raise HTTPException(status_code=400, detail="Can only escalate disputes in arbitration")

        now = datetime.now(timezone.utc).isoformat()

        await db.disputes.update_one(
            {"id": dispute_id},
            {"$set": {
                "status": "escalated",
                "severity": "high",
                "escalated_at": now,
                "updated_at": now
            }}
        )

        return {"message": "Dispute escalated to tribunal"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/my-disputes")
async def get_my_disputes(current_user: dict = Depends(get_current_user)):
    """Get user's disputes"""
    try:
        user_id = current_user["id"]

        # Disputes I initiated
        initiated = await db.disputes.find(
            {"initiator_id": user_id},
            {"_id": 0}
        ).sort("created_at", -1).to_list(50)

        # Disputes I'm arbitrating
        arbitrating_assignments = await db.dispute_arbitrators.find(
            {"arbitrator_id": user_id},
            {"_id": 0, "dispute_id": 1}
        ).to_list(50)

        arbitrating_ids = [a["dispute_id"] for a in arbitrating_assignments]
        arbitrating = []
        
        if arbitrating_ids:
            arbitrating = await db.disputes.find(
                {"id": {"$in": arbitrating_ids}},
                {"_id": 0}
            ).to_list(50)

        return {
            "initiated_disputes": initiated,
            "arbitrating_disputes": arbitrating
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/apply-arbitrator")
async def apply_as_arbitrator(current_user: dict = Depends(get_current_user)):
    """Apply to become an arbitrator"""
    try:
        user_id = current_user["id"]
        
        # Check requirements
        user = await db.users.find_one({"id": user_id}, {"_id": 0, "xp": 1, "level": 1})
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user_xp = user.get("xp", 0)
        user_level = user.get("level", 1)

        if user_xp < 1000 or user_level < 5:
            raise HTTPException(
                status_code=400,
                detail="Requires minimum 1000 XP and Level 5 to become arbitrator"
            )

        # Check existing application
        existing = await db.arbitrator_applications.find_one({"user_id": user_id})
        if existing:
            raise HTTPException(status_code=400, detail="Already applied")

        now = datetime.now(timezone.utc).isoformat()

        await db.arbitrator_applications.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "status": "pending",
            "xp_at_application": user_xp,
            "level_at_application": user_level,
            "created_at": now
        })

        return {"message": "Arbitrator application submitted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/stats")
async def get_dispute_stats():
    """Get dispute statistics"""
    try:
        total = await db.disputes.count_documents({})

        # Status breakdown
        status_pipeline = [
            {"$group": {"_id": "$status", "count": {"$sum": 1}}}
        ]
        status_result = await db.disputes.aggregate(status_pipeline).to_list(None)
        status_breakdown = {item["_id"]: item["count"] for item in status_result if item["_id"]}

        # Type breakdown
        type_pipeline = [
            {"$group": {"_id": "$dispute_type", "count": {"$sum": 1}}}
        ]
        type_result = await db.disputes.aggregate(type_pipeline).to_list(None)
        type_breakdown = {item["_id"]: item["count"] for item in type_result if item["_id"]}

        # Resolution rate
        resolved = status_breakdown.get("resolved", 0)
        resolution_rate = round(resolved / total * 100, 2) if total > 0 else 0

        return {
            "stats": {
                "total_disputes": total,
                "status_breakdown": status_breakdown,
                "type_breakdown": type_breakdown,
                "resolution_rate": resolution_rate
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
