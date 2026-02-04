from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from core.auth import get_current_user
from core.database import db
from services.token_service import TokenService

router = APIRouter(prefix="/api/disputes", tags=["Disputes"])
token_service = TokenService()

class DisputeCreate(BaseModel):
    dispute_type: str
    subject_id: str
    subject_type: str
    description: str
    evidence_urls: Optional[List[str]] = []

class ArbitratorVote(BaseModel):
    decision: str
    reasoning: str

@router.post("/create")
async def create_dispute(dispute: DisputeCreate, current_user: dict = Depends(get_current_user)):
    try:
        data = {
            "initiator_id": current_user["id"],
            "dispute_type": dispute.dispute_type,
            "subject_id": dispute.subject_id,
            "subject_type": dispute.subject_type,
            "description": dispute.description,
            "evidence_urls": dispute.evidence_urls,
            "status": "pending",
            "severity": "medium"
        }

        result = supabase.table("disputes").insert(data).execute()

        return {
            "message": "Dispute created successfully",
            "dispute": result.data[0]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/list")
async def list_disputes(
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    try:
        query = supabase.table("disputes").select("*, users(username, avatar)")

        if status:
            query = query.eq("status", status)

        result = query.order("created_at", desc=True).execute()

        return {"disputes": result.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{dispute_id}")
async def get_dispute_details(dispute_id: str, current_user: dict = Depends(get_current_user)):
    try:
        dispute_result = supabase.table("disputes").select("*, users(username, avatar)").eq("id", dispute_id).execute()

        if not dispute_result.data:
            raise HTTPException(status_code=404, detail="Dispute not found")

        votes_result = supabase.table("dispute_votes").select("*, users(username)").eq("dispute_id", dispute_id).execute()

        return {
            "dispute": dispute_result.data[0],
            "votes": votes_result.data
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/assign-arbitrators/{dispute_id}")
async def assign_arbitrators(
    dispute_id: str,
    arbitrator_ids: List[str],
    current_user: dict = Depends(get_current_user)
):
    try:
        dispute_result = supabase.table("disputes").select("*").eq("id", dispute_id).execute()

        if not dispute_result.data:
            raise HTTPException(status_code=404, detail="Dispute not found")

        for arbitrator_id in arbitrator_ids:
            assignment_data = {
                "dispute_id": dispute_id,
                "arbitrator_id": arbitrator_id,
                "status": "assigned"
            }

            supabase.table("dispute_arbitrators").insert(assignment_data).execute()

        supabase.table("disputes").update({"status": "in_arbitration"}).eq("id", dispute_id).execute()

        return {"message": "Arbitrators assigned successfully"}
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
    try:
        arbitrator_check = supabase.table("dispute_arbitrators").select("*").eq("dispute_id", dispute_id).eq("arbitrator_id", current_user["id"]).execute()

        if not arbitrator_check.data:
            raise HTTPException(status_code=403, detail="You are not assigned as an arbitrator for this dispute")

        existing_vote = supabase.table("dispute_votes").select("*").eq("dispute_id", dispute_id).eq("arbitrator_id", current_user["id"]).execute()

        if existing_vote.data:
            raise HTTPException(status_code=400, detail="You have already voted on this dispute")

        vote_data = {
            "dispute_id": dispute_id,
            "arbitrator_id": current_user["id"],
            "decision": vote.decision,
            "reasoning": vote.reasoning
        }

        supabase.table("dispute_votes").insert(vote_data).execute()

        all_votes = supabase.table("dispute_votes").select("decision").eq("dispute_id", dispute_id).execute()
        arbitrators_count = len(supabase.table("dispute_arbitrators").select("id").eq("dispute_id", dispute_id).execute().data or [])

        if len(all_votes.data or []) >= arbitrators_count:
            decision_counts = {}
            for v in all_votes.data or []:
                decision = v["decision"]
                decision_counts[decision] = decision_counts.get(decision, 0) + 1

            final_decision = max(decision_counts, key=decision_counts.get)

            supabase.table("disputes").update({
                "status": "resolved",
                "resolution": final_decision,
                "resolved_at": datetime.utcnow().isoformat()
            }).eq("id", dispute_id).execute()

            return {
                "message": "Dispute resolved",
                "final_decision": final_decision
            }
        else:
            return {
                "message": "Vote recorded",
                "votes_remaining": arbitrators_count - len(all_votes.data or [])
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/escalate/{dispute_id}")
async def escalate_dispute(dispute_id: str, current_user: dict = Depends(get_current_user)):
    try:
        dispute_result = supabase.table("disputes").select("*").eq("id", dispute_id).eq("initiator_id", current_user["id"]).execute()

        if not dispute_result.data:
            raise HTTPException(status_code=404, detail="Dispute not found or you're not the initiator")

        dispute = dispute_result.data[0]

        if dispute["status"] != "in_arbitration":
            raise HTTPException(status_code=400, detail="Dispute cannot be escalated at this stage")

        supabase.table("disputes").update({
            "status": "escalated",
            "severity": "high"
        }).eq("id", dispute_id).execute()

        return {"message": "Dispute escalated to tribunal"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/my-disputes")
async def get_my_disputes(current_user: dict = Depends(get_current_user)):
    try:
        initiated = supabase.table("disputes").select("*").eq("initiator_id", current_user["id"]).execute()

        arbitrating = supabase.table("dispute_arbitrators").select("dispute_id").eq("arbitrator_id", current_user["id"]).execute()

        arbitrating_ids = [a["dispute_id"] for a in arbitrating.data] if arbitrating.data else []
        arbitrating_disputes = []

        if arbitrating_ids:
            for dispute_id in arbitrating_ids:
                dispute_result = supabase.table("disputes").select("*").eq("id", dispute_id).execute()
                if dispute_result.data:
                    arbitrating_disputes.extend(dispute_result.data)

        return {
            "initiated_disputes": initiated.data,
            "arbitrating_disputes": arbitrating_disputes
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/stats")
async def get_dispute_stats():
    try:
        all_disputes = supabase.table("disputes").select("*").execute()

        total_disputes = len(all_disputes.data) if all_disputes.data else 0

        status_breakdown = {}
        for dispute in all_disputes.data if all_disputes.data else []:
            status = dispute.get("status", "unknown")
            status_breakdown[status] = status_breakdown.get(status, 0) + 1

        type_breakdown = {}
        for dispute in all_disputes.data if all_disputes.data else []:
            dtype = dispute.get("dispute_type", "unknown")
            type_breakdown[dtype] = type_breakdown.get(dtype, 0) + 1

        return {
            "stats": {
                "total_disputes": total_disputes,
                "status_breakdown": status_breakdown,
                "type_breakdown": type_breakdown
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/apply-arbitrator")
async def apply_as_arbitrator(current_user: dict = Depends(get_current_user)):
    try:
        user_result = supabase.table("users").select("xp, level").eq("id", current_user["id"]).execute()

        if not user_result.data:
            raise HTTPException(status_code=404, detail="User not found")

        user_xp = user_result.data[0].get("xp", 0)
        user_level = user_result.data[0].get("level", 1)

        if user_xp < 1000 or user_level < 5:
            raise HTTPException(status_code=400, detail="Insufficient XP or level to become an arbitrator (need 1000 XP and level 5)")

        existing_application = supabase.table("arbitrator_applications").select("*").eq("user_id", current_user["id"]).execute()

        if existing_application.data:
            raise HTTPException(status_code=400, detail="You have already applied to be an arbitrator")

        application_data = {
            "user_id": current_user["id"],
            "status": "pending",
            "xp_at_application": user_xp,
            "level_at_application": user_level
        }

        result = supabase.table("arbitrator_applications").insert(application_data).execute()

        return {
            "message": "Arbitrator application submitted",
            "application": result.data[0]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
