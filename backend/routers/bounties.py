from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
from core.auth import get_current_user
from core.database import supabase
from services.token_service import TokenService

router = APIRouter(prefix="/api/bounties", tags=["Bounties"])
token_service = TokenService()

class BountyCreate(BaseModel):
    title: str
    description: str
    category: str
    required_skills: List[str]
    reward_amount: float
    deadline_days: int
    difficulty: str

class BountyClaim(BaseModel):
    proposal: str

class BountySubmission(BaseModel):
    submission_url: str
    notes: Optional[str] = None

@router.post("/create")
async def create_bounty(bounty: BountyCreate, current_user: dict = Depends(get_current_user)):
    try:
        user_result = supabase.table("users").select("realum_balance").eq("id", current_user["id"]).execute()
        current_balance = float(user_result.data[0].get("realum_balance", 0))

        if current_balance < bounty.reward_amount:
            raise HTTPException(status_code=400, detail="Insufficient RLM tokens to fund bounty")

        new_balance = current_balance - bounty.reward_amount
        supabase.table("users").update({"realum_balance": new_balance}).eq("id", current_user["id"]).execute()

        deadline = datetime.utcnow() + timedelta(days=bounty.deadline_days)

        data = {
            "creator_id": current_user["id"],
            "title": bounty.title,
            "description": bounty.description,
            "category": bounty.category,
            "required_skills": bounty.required_skills,
            "reward_amount": bounty.reward_amount,
            "deadline": deadline.isoformat(),
            "difficulty": bounty.difficulty,
            "status": "open",
            "escrow_amount": bounty.reward_amount
        }

        result = supabase.table("bounties").insert(data).execute()

        token_service.create_transaction(
            user_id=current_user["id"],
            amount=-bounty.reward_amount,
            transaction_type="bounty_escrow",
            description=f"Escrowed funds for bounty: {bounty.title}"
        )

        return {
            "message": "Bounty created successfully",
            "bounty": result.data[0],
            "new_balance": new_balance
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/list")
async def list_bounties(
    status: Optional[str] = "open",
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    try:
        query = supabase.table("bounties").select("*, users(username, avatar)")

        if status:
            query = query.eq("status", status)
        if category:
            query = query.eq("category", category)
        if difficulty:
            query = query.eq("difficulty", difficulty)

        result = query.order("created_at", desc=True).execute()

        return {"bounties": result.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/claim/{bounty_id}")
async def claim_bounty(
    bounty_id: str,
    claim: BountyClaim,
    current_user: dict = Depends(get_current_user)
):
    try:
        bounty_result = supabase.table("bounties").select("*").eq("id", bounty_id).execute()

        if not bounty_result.data:
            raise HTTPException(status_code=404, detail="Bounty not found")

        bounty = bounty_result.data[0]

        if bounty["status"] != "open":
            raise HTTPException(status_code=400, detail="Bounty is not available")

        if bounty["creator_id"] == current_user["id"]:
            raise HTTPException(status_code=400, detail="Cannot claim your own bounty")

        existing_claim = supabase.table("bounty_claims").select("*").eq("bounty_id", bounty_id).eq("user_id", current_user["id"]).execute()

        if existing_claim.data:
            raise HTTPException(status_code=400, detail="You have already claimed this bounty")

        claim_data = {
            "bounty_id": bounty_id,
            "user_id": current_user["id"],
            "proposal": claim.proposal,
            "status": "claimed"
        }

        result = supabase.table("bounty_claims").insert(claim_data).execute()

        supabase.table("bounties").update({"status": "claimed", "claimed_by": current_user["id"]}).eq("id", bounty_id).execute()

        return {
            "message": "Bounty claimed successfully",
            "claim": result.data[0]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/submit/{bounty_id}")
async def submit_bounty_work(
    bounty_id: str,
    submission: BountySubmission,
    current_user: dict = Depends(get_current_user)
):
    try:
        bounty_result = supabase.table("bounties").select("*").eq("id", bounty_id).eq("claimed_by", current_user["id"]).execute()

        if not bounty_result.data:
            raise HTTPException(status_code=404, detail="Bounty not found or not claimed by you")

        claim_result = supabase.table("bounty_claims").select("*").eq("bounty_id", bounty_id).eq("user_id", current_user["id"]).execute()

        if not claim_result.data:
            raise HTTPException(status_code=404, detail="Claim not found")

        claim_id = claim_result.data[0]["id"]

        submission_data = {
            "claim_id": claim_id,
            "bounty_id": bounty_id,
            "user_id": current_user["id"],
            "submission_url": submission.submission_url,
            "notes": submission.notes,
            "status": "pending_review"
        }

        result = supabase.table("bounty_submissions").insert(submission_data).execute()

        supabase.table("bounties").update({"status": "in_review"}).eq("id", bounty_id).execute()
        supabase.table("bounty_claims").update({"status": "submitted"}).eq("id", claim_id).execute()

        return {
            "message": "Work submitted for review",
            "submission": result.data[0]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/approve/{bounty_id}")
async def approve_bounty_submission(bounty_id: str, current_user: dict = Depends(get_current_user)):
    try:
        bounty_result = supabase.table("bounties").select("*").eq("id", bounty_id).eq("creator_id", current_user["id"]).execute()

        if not bounty_result.data:
            raise HTTPException(status_code=404, detail="Bounty not found or you're not the creator")

        bounty = bounty_result.data[0]

        if bounty["status"] != "in_review":
            raise HTTPException(status_code=400, detail="Bounty is not in review status")

        claimed_by = bounty.get("claimed_by")
        reward_amount = float(bounty.get("reward_amount", 0))

        if not claimed_by:
            raise HTTPException(status_code=400, detail="No claimer found")

        claimer_result = supabase.table("users").select("realum_balance").eq("id", claimed_by).execute()

        if claimer_result.data:
            current_balance = float(claimer_result.data[0].get("realum_balance", 0))
            new_balance = current_balance + reward_amount

            supabase.table("users").update({"realum_balance": new_balance}).eq("id", claimed_by).execute()

            token_service.create_transaction(
                user_id=claimed_by,
                amount=reward_amount,
                transaction_type="bounty_reward",
                description=f"Bounty completed: {bounty['title']}"
            )

        supabase.table("bounties").update({"status": "completed"}).eq("id", bounty_id).execute()

        claim_result = supabase.table("bounty_claims").select("id").eq("bounty_id", bounty_id).eq("user_id", claimed_by).execute()
        if claim_result.data:
            supabase.table("bounty_claims").update({"status": "approved"}).eq("id", claim_result.data[0]["id"]).execute()

        submission_result = supabase.table("bounty_submissions").select("id").eq("bounty_id", bounty_id).eq("user_id", claimed_by).execute()
        if submission_result.data:
            supabase.table("bounty_submissions").update({"status": "approved"}).eq("id", submission_result.data[0]["id"]).execute()

        return {
            "message": "Bounty approved and reward released",
            "reward_amount": reward_amount
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/reject/{bounty_id}")
async def reject_bounty_submission(bounty_id: str, reason: str, current_user: dict = Depends(get_current_user)):
    try:
        bounty_result = supabase.table("bounties").select("*").eq("id", bounty_id).eq("creator_id", current_user["id"]).execute()

        if not bounty_result.data:
            raise HTTPException(status_code=404, detail="Bounty not found or you're not the creator")

        bounty = bounty_result.data[0]
        claimed_by = bounty.get("claimed_by")
        reward_amount = float(bounty.get("reward_amount", 0))

        creator_result = supabase.table("users").select("realum_balance").eq("id", current_user["id"]).execute()
        current_balance = float(creator_result.data[0].get("realum_balance", 0))
        new_balance = current_balance + reward_amount

        supabase.table("users").update({"realum_balance": new_balance}).eq("id", current_user["id"]).execute()

        token_service.create_transaction(
            user_id=current_user["id"],
            amount=reward_amount,
            transaction_type="bounty_refund",
            description=f"Bounty rejected, escrow returned: {bounty['title']}"
        )

        supabase.table("bounties").update({"status": "rejected", "rejection_reason": reason}).eq("id", bounty_id).execute()

        if claimed_by:
            claim_result = supabase.table("bounty_claims").select("id").eq("bounty_id", bounty_id).eq("user_id", claimed_by).execute()
            if claim_result.data:
                supabase.table("bounty_claims").update({"status": "rejected"}).eq("id", claim_result.data[0]["id"]).execute()

            submission_result = supabase.table("bounty_submissions").select("id").eq("bounty_id", bounty_id).eq("user_id", claimed_by).execute()
            if submission_result.data:
                supabase.table("bounty_submissions").update({"status": "rejected", "rejection_reason": reason}).eq("id", submission_result.data[0]["id"]).execute()

        return {"message": "Bounty rejected and funds returned"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/my-bounties")
async def get_my_bounties(current_user: dict = Depends(get_current_user)):
    try:
        created = supabase.table("bounties").select("*").eq("creator_id", current_user["id"]).execute()
        claimed = supabase.table("bounties").select("*").eq("claimed_by", current_user["id"]).execute()

        return {
            "created_bounties": created.data,
            "claimed_bounties": claimed.data
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/stats")
async def get_bounty_stats():
    try:
        all_bounties = supabase.table("bounties").select("*").execute()

        total_bounties = len(all_bounties.data) if all_bounties.data else 0
        total_value = sum(float(b.get("reward_amount", 0)) for b in all_bounties.data) if all_bounties.data else 0

        status_breakdown = {}
        for bounty in all_bounties.data if all_bounties.data else []:
            status = bounty.get("status", "unknown")
            status_breakdown[status] = status_breakdown.get(status, 0) + 1

        return {
            "stats": {
                "total_bounties": total_bounties,
                "total_value": total_value,
                "status_breakdown": status_breakdown
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
