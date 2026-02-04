from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import uuid
from core.auth import get_current_user
from core.database import db
from services.token_service import TokenService
from services.notification_service import send_notification

router = APIRouter(prefix="/api/bounties", tags=["Bounties"])
token_service = TokenService()

class BountyCreate(BaseModel):
    title: str
    description: str
    category: str
    required_skills: List[str] = []
    reward_amount: float
    deadline_days: int = 30
    difficulty: str = "medium"
    max_applicants: int = 10

class BountyClaim(BaseModel):
    proposal: str

class BountySubmission(BaseModel):
    submission_url: str
    notes: Optional[str] = None

class MilestoneCreate(BaseModel):
    title: str
    description: str
    reward_percentage: float  # Percentage of total bounty

@router.post("/create")
async def create_bounty(bounty: BountyCreate, current_user: dict = Depends(get_current_user)):
    """Create a new bounty with escrowed funds"""
    try:
        user_id = current_user["id"]
        
        # Check balance
        user = await db.users.find_one({"id": user_id}, {"_id": 0, "realum_balance": 1})
        current_balance = float(user.get("realum_balance", 0))

        if current_balance < bounty.reward_amount:
            raise HTTPException(status_code=400, detail="Insufficient RLM tokens to fund bounty")

        # Deduct from user balance (escrow)
        new_balance = current_balance - bounty.reward_amount
        await db.users.update_one(
            {"id": user_id},
            {"$set": {"realum_balance": new_balance}}
        )

        deadline = datetime.now(timezone.utc) + timedelta(days=bounty.deadline_days)
        bounty_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        bounty_data = {
            "id": bounty_id,
            "creator_id": user_id,
            "title": bounty.title,
            "description": bounty.description,
            "category": bounty.category,
            "required_skills": bounty.required_skills,
            "reward_amount": bounty.reward_amount,
            "deadline": deadline.isoformat(),
            "difficulty": bounty.difficulty,
            "max_applicants": bounty.max_applicants,
            "status": "open",
            "escrow_amount": bounty.reward_amount,
            "applicant_count": 0,
            "created_at": now,
            "updated_at": now
        }

        await db.bounties.insert_one(bounty_data)

        # Record escrow transaction
        await token_service.create_transaction(
            user_id=user_id,
            tx_type="debit",
            amount=bounty.reward_amount,
            description=f"Escrowed funds for bounty: {bounty.title}"
        )

        return {
            "message": "Bounty created successfully",
            "bounty_id": bounty_id,
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
    skip: int = 0,
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """List bounties with filters"""
    try:
        query = {}
        if status:
            query["status"] = status
        if category:
            query["category"] = category
        if difficulty:
            query["difficulty"] = difficulty

        bounties = await db.bounties.find(
            query, {"_id": 0}
        ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)

        # Enrich with creator info
        for bounty in bounties:
            creator = await db.users.find_one(
                {"id": bounty["creator_id"]},
                {"_id": 0, "username": 1, "avatar_url": 1}
            )
            if creator:
                bounty["creator_username"] = creator.get("username")
                bounty["creator_avatar"] = creator.get("avatar_url")

        total = await db.bounties.count_documents(query)

        return {"bounties": bounties, "total": total}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{bounty_id}")
async def get_bounty_details(bounty_id: str, current_user: dict = Depends(get_current_user)):
    """Get bounty details"""
    try:
        bounty = await db.bounties.find_one({"id": bounty_id}, {"_id": 0})
        
        if not bounty:
            raise HTTPException(status_code=404, detail="Bounty not found")

        # Get creator info
        creator = await db.users.find_one(
            {"id": bounty["creator_id"]},
            {"_id": 0, "username": 1, "avatar_url": 1}
        )
        if creator:
            bounty["creator_username"] = creator.get("username")
            bounty["creator_avatar"] = creator.get("avatar_url")

        # Get applications
        applications = await db.bounty_claims.find(
            {"bounty_id": bounty_id},
            {"_id": 0}
        ).to_list(50)

        # Get milestones
        milestones = await db.bounty_milestones.find(
            {"bounty_id": bounty_id},
            {"_id": 0}
        ).to_list(20)

        return {
            "bounty": bounty,
            "applications": applications,
            "milestones": milestones
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/claim/{bounty_id}")
async def claim_bounty(
    bounty_id: str,
    claim: BountyClaim,
    current_user: dict = Depends(get_current_user)
):
    """Apply to claim a bounty"""
    try:
        user_id = current_user["id"]
        
        bounty = await db.bounties.find_one({"id": bounty_id})

        if not bounty:
            raise HTTPException(status_code=404, detail="Bounty not found")

        if bounty["status"] != "open":
            raise HTTPException(status_code=400, detail="Bounty is not available")

        if bounty["creator_id"] == user_id:
            raise HTTPException(status_code=400, detail="Cannot claim your own bounty")

        if bounty.get("applicant_count", 0) >= bounty.get("max_applicants", 10):
            raise HTTPException(status_code=400, detail="Maximum applicants reached")

        # Check for existing claim
        existing = await db.bounty_claims.find_one({
            "bounty_id": bounty_id,
            "user_id": user_id
        })

        if existing:
            raise HTTPException(status_code=400, detail="You have already applied for this bounty")

        claim_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        claim_data = {
            "id": claim_id,
            "bounty_id": bounty_id,
            "user_id": user_id,
            "proposal": claim.proposal,
            "status": "pending",
            "created_at": now
        }

        await db.bounty_claims.insert_one(claim_data)

        # Update applicant count
        await db.bounties.update_one(
            {"id": bounty_id},
            {"$inc": {"applicant_count": 1}}
        )

        # Notify creator
        await send_notification(
            user_id=bounty["creator_id"],
            title="New Bounty Application",
            message=f"{current_user['username']} applied for your bounty: {bounty['title']}",
            category="jobs"
        )

        return {
            "message": "Application submitted successfully",
            "claim_id": claim_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/accept/{bounty_id}/{claim_id}")
async def accept_claim(
    bounty_id: str,
    claim_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Accept a bounty application"""
    try:
        # Verify bounty ownership
        bounty = await db.bounties.find_one({
            "id": bounty_id,
            "creator_id": current_user["id"]
        })

        if not bounty:
            raise HTTPException(status_code=404, detail="Bounty not found or not your bounty")

        if bounty["status"] != "open":
            raise HTTPException(status_code=400, detail="Bounty is not open")

        # Get claim
        claim = await db.bounty_claims.find_one({"id": claim_id})
        if not claim:
            raise HTTPException(status_code=404, detail="Application not found")

        now = datetime.now(timezone.utc).isoformat()

        # Accept the claim
        await db.bounty_claims.update_one(
            {"id": claim_id},
            {"$set": {"status": "accepted", "accepted_at": now}}
        )

        # Reject other claims
        await db.bounty_claims.update_many(
            {"bounty_id": bounty_id, "id": {"$ne": claim_id}},
            {"$set": {"status": "rejected"}}
        )

        # Update bounty status
        await db.bounties.update_one(
            {"id": bounty_id},
            {"$set": {
                "status": "in_progress",
                "claimed_by": claim["user_id"],
                "claimed_at": now
            }}
        )

        # Notify accepted user
        await send_notification(
            user_id=claim["user_id"],
            title="Bounty Application Accepted!",
            message=f"Your application for '{bounty['title']}' was accepted. Get started!",
            category="jobs"
        )

        return {"message": "Application accepted successfully"}
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
    """Submit work for review"""
    try:
        user_id = current_user["id"]
        
        bounty = await db.bounties.find_one({
            "id": bounty_id,
            "claimed_by": user_id
        })

        if not bounty:
            raise HTTPException(status_code=404, detail="Bounty not found or not claimed by you")

        if bounty["status"] != "in_progress":
            raise HTTPException(status_code=400, detail="Bounty is not in progress")

        submission_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        submission_data = {
            "id": submission_id,
            "bounty_id": bounty_id,
            "user_id": user_id,
            "submission_url": submission.submission_url,
            "notes": submission.notes,
            "status": "pending_review",
            "created_at": now
        }

        await db.bounty_submissions.insert_one(submission_data)

        await db.bounties.update_one(
            {"id": bounty_id},
            {"$set": {"status": "in_review", "updated_at": now}}
        )

        # Notify creator
        await send_notification(
            user_id=bounty["creator_id"],
            title="Bounty Work Submitted",
            message=f"Work submitted for review on '{bounty['title']}'",
            category="jobs"
        )

        return {
            "message": "Work submitted for review",
            "submission_id": submission_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/approve/{bounty_id}")
async def approve_bounty_submission(bounty_id: str, current_user: dict = Depends(get_current_user)):
    """Approve bounty submission and release funds"""
    try:
        bounty = await db.bounties.find_one({
            "id": bounty_id,
            "creator_id": current_user["id"]
        })

        if not bounty:
            raise HTTPException(status_code=404, detail="Bounty not found or not your bounty")

        if bounty["status"] != "in_review":
            raise HTTPException(status_code=400, detail="Bounty is not in review status")

        claimed_by = bounty.get("claimed_by")
        reward_amount = float(bounty.get("reward_amount", 0))

        if not claimed_by:
            raise HTTPException(status_code=400, detail="No claimer found")

        # Transfer reward to claimer
        await db.users.update_one(
            {"id": claimed_by},
            {"$inc": {"realum_balance": reward_amount}}
        )

        # Record transaction
        await token_service.create_transaction(
            user_id=claimed_by,
            tx_type="credit",
            amount=reward_amount,
            description=f"Bounty completed: {bounty['title']}"
        )

        now = datetime.now(timezone.utc).isoformat()

        # Update bounty
        await db.bounties.update_one(
            {"id": bounty_id},
            {"$set": {
                "status": "completed",
                "completed_at": now,
                "escrow_amount": 0
            }}
        )

        # Update submission
        await db.bounty_submissions.update_one(
            {"bounty_id": bounty_id, "user_id": claimed_by},
            {"$set": {"status": "approved", "approved_at": now}}
        )

        # Notify claimer
        await send_notification(
            user_id=claimed_by,
            title="Bounty Approved!",
            message=f"Your work on '{bounty['title']}' was approved! {reward_amount} RLM received.",
            category="rewards"
        )

        return {
            "message": "Bounty approved and reward released",
            "reward_amount": reward_amount
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/reject/{bounty_id}")
async def reject_bounty_submission(
    bounty_id: str,
    reason: str,
    current_user: dict = Depends(get_current_user)
):
    """Reject bounty submission and return to in_progress"""
    try:
        bounty = await db.bounties.find_one({
            "id": bounty_id,
            "creator_id": current_user["id"]
        })

        if not bounty:
            raise HTTPException(status_code=404, detail="Bounty not found or not your bounty")

        claimed_by = bounty.get("claimed_by")
        now = datetime.now(timezone.utc).isoformat()

        # Update bounty back to in_progress
        await db.bounties.update_one(
            {"id": bounty_id},
            {"$set": {
                "status": "in_progress",
                "rejection_reason": reason,
                "updated_at": now
            }}
        )

        # Update submission
        await db.bounty_submissions.update_one(
            {"bounty_id": bounty_id, "user_id": claimed_by},
            {"$set": {"status": "rejected", "rejection_reason": reason}}
        )

        # Notify claimer
        if claimed_by:
            await send_notification(
                user_id=claimed_by,
                title="Submission Needs Revision",
                message=f"Your submission for '{bounty['title']}' needs changes. Reason: {reason}",
                category="jobs"
            )

        return {"message": "Submission rejected. Claimer can resubmit."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/my-bounties")
async def get_my_bounties(current_user: dict = Depends(get_current_user)):
    """Get bounties created or claimed by user"""
    try:
        user_id = current_user["id"]
        
        created = await db.bounties.find(
            {"creator_id": user_id},
            {"_id": 0}
        ).sort("created_at", -1).to_list(50)
        
        claimed = await db.bounties.find(
            {"claimed_by": user_id},
            {"_id": 0}
        ).sort("created_at", -1).to_list(50)

        # Get applications
        applications = await db.bounty_claims.find(
            {"user_id": user_id},
            {"_id": 0}
        ).to_list(50)

        return {
            "created_bounties": created,
            "claimed_bounties": claimed,
            "applications": applications
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/stats")
async def get_bounty_stats():
    """Get bounty statistics"""
    try:
        total_bounties = await db.bounties.count_documents({})
        
        # Total value
        value_pipeline = [
            {"$group": {"_id": None, "total": {"$sum": "$reward_amount"}}}
        ]
        value_result = await db.bounties.aggregate(value_pipeline).to_list(1)
        total_value = value_result[0]["total"] if value_result else 0

        # Status breakdown
        status_pipeline = [
            {"$group": {"_id": "$status", "count": {"$sum": 1}}}
        ]
        status_result = await db.bounties.aggregate(status_pipeline).to_list(None)
        status_breakdown = {item["_id"]: item["count"] for item in status_result if item["_id"]}

        # Category breakdown
        category_pipeline = [
            {"$group": {"_id": "$category", "count": {"$sum": 1}}}
        ]
        category_result = await db.bounties.aggregate(category_pipeline).to_list(None)
        category_breakdown = {item["_id"]: item["count"] for item in category_result if item["_id"]}

        return {
            "stats": {
                "total_bounties": total_bounties,
                "total_value": total_value,
                "status_breakdown": status_breakdown,
                "category_breakdown": category_breakdown
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/categories")
async def get_bounty_categories():
    """Get available bounty categories"""
    return {
        "categories": [
            {"key": "development", "name": "Development", "description": "Software development tasks"},
            {"key": "design", "name": "Design", "description": "UI/UX and graphic design"},
            {"key": "content", "name": "Content", "description": "Writing and content creation"},
            {"key": "translation", "name": "Translation", "description": "Language translation tasks"},
            {"key": "marketing", "name": "Marketing", "description": "Marketing and promotion"},
            {"key": "research", "name": "Research", "description": "Research and analysis"},
            {"key": "community", "name": "Community", "description": "Community management"},
            {"key": "other", "name": "Other", "description": "Other tasks"}
        ]
    }
