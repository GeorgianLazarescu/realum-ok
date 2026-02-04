from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone
import uuid
from core.auth import get_current_user, require_admin
from core.database import db
from services.token_service import TokenService
from services.notification_service import send_notification

router = APIRouter(prefix="/api/feedback", tags=["Feedback"])
token_service = TokenService()

class FeedbackCreate(BaseModel):
    category: str
    title: str
    description: str
    priority: Optional[str] = "medium"

class IdeaCreate(BaseModel):
    title: str
    description: str
    category: str
    estimated_impact: Optional[str] = "medium"
    implementation_difficulty: Optional[str] = "medium"

class VoteRequest(BaseModel):
    vote_type: str  # upvote, downvote

class FeedbackResponse(BaseModel):
    content: str

FEEDBACK_REWARD = 10  # RLM tokens for submitting feedback
IDEA_REWARD = 20  # RLM tokens for submitting ideas
IMPLEMENTED_IDEA_BONUS = 100  # Bonus for ideas that get implemented

@router.post("/submit")
async def submit_feedback(feedback: FeedbackCreate, current_user: dict = Depends(get_current_user)):
    """Submit feedback and earn RLM tokens"""
    try:
        feedback_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        feedback_data = {
            "id": feedback_id,
            "user_id": current_user["id"],
            "category": feedback.category,
            "title": feedback.title,
            "description": feedback.description,
            "priority": feedback.priority,
            "status": "submitted",
            "votes_count": 0,
            "upvotes": 0,
            "downvotes": 0,
            "created_at": now,
            "updated_at": now
        }

        await db.feedback.insert_one(feedback_data)

        # Reward user
        await db.users.update_one(
            {"id": current_user["id"]},
            {"$inc": {"realum_balance": FEEDBACK_REWARD}}
        )

        await token_service.create_transaction(
            user_id=current_user["id"],
            tx_type="credit",
            amount=FEEDBACK_REWARD,
            description="Reward for submitting feedback"
        )

        return {
            "message": "Feedback submitted successfully",
            "feedback_id": feedback_id,
            "reward": FEEDBACK_REWARD
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/categories")
async def get_feedback_categories():
    """Get feedback categories"""
    return {
        "feedback_categories": [
            {"key": "bug", "name": "Bug Report", "description": "Report bugs and issues"},
            {"key": "feature", "name": "Feature Request", "description": "Suggest new features"},
            {"key": "improvement", "name": "Improvement", "description": "Suggest improvements"},
            {"key": "ui_ux", "name": "UI/UX", "description": "User interface feedback"},
            {"key": "performance", "name": "Performance", "description": "Performance issues"},
            {"key": "documentation", "name": "Documentation", "description": "Documentation feedback"},
            {"key": "other", "name": "Other", "description": "Other feedback"}
        ],
        "idea_categories": [
            {"key": "education", "name": "Education", "description": "Educational features"},
            {"key": "governance", "name": "Governance", "description": "DAO and governance"},
            {"key": "economy", "name": "Economy", "description": "Token economy"},
            {"key": "metaverse", "name": "Metaverse", "description": "Metaverse features"},
            {"key": "community", "name": "Community", "description": "Community features"},
            {"key": "integration", "name": "Integration", "description": "Third-party integrations"},
            {"key": "other", "name": "Other", "description": "Other ideas"}
        ]
    }

@router.get("/stats")
async def get_feedback_stats():
    """Get feedback and ideas statistics"""
    try:
        total_feedback = await db.feedback.count_documents({})
        total_ideas = await db.ideas.count_documents({})

        # Status breakdown for feedback
        fb_status_pipeline = [
            {"$group": {"_id": "$status", "count": {"$sum": 1}}}
        ]
        fb_status_result = await db.feedback.aggregate(fb_status_pipeline).to_list(None)
        fb_status = {item["_id"]: item["count"] for item in fb_status_result if item["_id"]}

        # Status breakdown for ideas
        idea_status_pipeline = [
            {"$group": {"_id": "$status", "count": {"$sum": 1}}}
        ]
        idea_status_result = await db.ideas.aggregate(idea_status_pipeline).to_list(None)
        idea_status = {item["_id"]: item["count"] for item in idea_status_result if item["_id"]}

        return {
            "stats": {
                "total_feedback": total_feedback,
                "total_ideas": total_ideas,
                "feedback_status": fb_status,
                "idea_status": idea_status
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/my-submissions")
async def get_my_submissions(current_user: dict = Depends(get_current_user)):
    """Get user's feedback and idea submissions"""
    try:
        user_id = current_user["id"]

        feedback = await db.feedback.find(
            {"user_id": user_id},
            {"_id": 0}
        ).sort("created_at", -1).to_list(50)

        ideas = await db.ideas.find(
            {"user_id": user_id},
            {"_id": 0}
        ).sort("created_at", -1).to_list(50)

        return {
            "feedback": feedback,
            "ideas": ideas
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/ideas/all")
async def get_all_ideas(
    category: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """Get all ideas"""
    try:
        query = {}
        if category:
            query["category"] = category
        if status:
            query["status"] = status

        ideas = await db.ideas.find(
            query, {"_id": 0}
        ).sort("votes_count", -1).skip(skip).limit(limit).to_list(limit)

        # Enrich with user info
        for idea in ideas:
            user = await db.users.find_one(
                {"id": idea["user_id"]},
                {"_id": 0, "username": 1, "avatar_url": 1}
            )
            if user:
                idea["username"] = user.get("username")
                idea["avatar_url"] = user.get("avatar_url")

        total = await db.ideas.count_documents(query)

        return {"ideas": ideas, "total": total}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/all")
async def get_all_feedback(
    category: Optional[str] = None,
    status: Optional[str] = None,
    sort_by: str = "votes",
    skip: int = 0,
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """Get all feedback with optional filters"""
    try:
        query = {}
        if category:
            query["category"] = category
        if status:
            query["status"] = status

        sort_field = "votes_count" if sort_by == "votes" else "created_at"

        feedback_list = await db.feedback.find(
            query, {"_id": 0}
        ).sort(sort_field, -1).skip(skip).limit(limit).to_list(limit)

        # Enrich with user info
        for fb in feedback_list:
            user = await db.users.find_one(
                {"id": fb["user_id"]},
                {"_id": 0, "username": 1, "avatar_url": 1}
            )
            if user:
                fb["username"] = user.get("username")
                fb["avatar_url"] = user.get("avatar_url")

            # Check if current user voted
            vote = await db.feedback_votes.find_one({
                "feedback_id": fb["id"],
                "user_id": current_user["id"]
            })
            fb["user_voted"] = vote.get("vote_type") if vote else None

        total = await db.feedback.count_documents(query)

        return {"feedback": feedback_list, "total": total}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{feedback_id}")
async def get_feedback_details(feedback_id: str, current_user: dict = Depends(get_current_user)):
    """Get feedback details"""
    try:
        feedback = await db.feedback.find_one({"id": feedback_id}, {"_id": 0})
        
        if not feedback:
            raise HTTPException(status_code=404, detail="Feedback not found")

        # Get user info
        user = await db.users.find_one(
            {"id": feedback["user_id"]},
            {"_id": 0, "username": 1, "avatar_url": 1}
        )
        if user:
            feedback["username"] = user.get("username")
            feedback["avatar_url"] = user.get("avatar_url")

        # Get responses
        responses = await db.feedback_responses.find(
            {"feedback_id": feedback_id},
            {"_id": 0}
        ).sort("created_at", 1).to_list(50)

        for resp in responses:
            resp_user = await db.users.find_one(
                {"id": resp["user_id"]},
                {"_id": 0, "username": 1, "role": 1}
            )
            if resp_user:
                resp["username"] = resp_user.get("username")
                resp["is_admin"] = resp_user.get("role") in ["admin", "Admin"]

        return {
            "feedback": feedback,
            "responses": responses
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/vote/{feedback_id}")
async def vote_on_feedback(
    feedback_id: str,
    vote: VoteRequest,
    current_user: dict = Depends(get_current_user)
):
    """Vote on feedback"""
    try:
        # Check if feedback exists
        feedback = await db.feedback.find_one({"id": feedback_id})
        if not feedback:
            raise HTTPException(status_code=404, detail="Feedback not found")

        # Check for existing vote
        existing = await db.feedback_votes.find_one({
            "feedback_id": feedback_id,
            "user_id": current_user["id"]
        })

        now = datetime.now(timezone.utc).isoformat()

        if existing:
            if existing["vote_type"] == vote.vote_type:
                # Remove vote
                await db.feedback_votes.delete_one({"id": existing["id"]})
                
                if vote.vote_type == "upvote":
                    await db.feedback.update_one(
                        {"id": feedback_id},
                        {"$inc": {"upvotes": -1, "votes_count": -1}}
                    )
                else:
                    await db.feedback.update_one(
                        {"id": feedback_id},
                        {"$inc": {"downvotes": -1, "votes_count": 1}}
                    )
                return {"message": "Vote removed"}
            else:
                # Change vote
                await db.feedback_votes.update_one(
                    {"id": existing["id"]},
                    {"$set": {"vote_type": vote.vote_type, "updated_at": now}}
                )
                
                if vote.vote_type == "upvote":
                    await db.feedback.update_one(
                        {"id": feedback_id},
                        {"$inc": {"upvotes": 1, "downvotes": -1, "votes_count": 2}}
                    )
                else:
                    await db.feedback.update_one(
                        {"id": feedback_id},
                        {"$inc": {"upvotes": -1, "downvotes": 1, "votes_count": -2}}
                    )
                return {"message": "Vote changed"}
        else:
            # New vote
            await db.feedback_votes.insert_one({
                "id": str(uuid.uuid4()),
                "feedback_id": feedback_id,
                "user_id": current_user["id"],
                "vote_type": vote.vote_type,
                "created_at": now
            })

            if vote.vote_type == "upvote":
                await db.feedback.update_one(
                    {"id": feedback_id},
                    {"$inc": {"upvotes": 1, "votes_count": 1}}
                )
            else:
                await db.feedback.update_one(
                    {"id": feedback_id},
                    {"$inc": {"downvotes": 1, "votes_count": -1}}
                )

            return {"message": "Vote recorded", "vote_type": vote.vote_type}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/respond/{feedback_id}")
async def respond_to_feedback(
    feedback_id: str,
    response: FeedbackResponse,
    current_user: dict = Depends(get_current_user)
):
    """Add official response to feedback"""
    try:
        feedback = await db.feedback.find_one({"id": feedback_id})
        if not feedback:
            raise HTTPException(status_code=404, detail="Feedback not found")

        response_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        await db.feedback_responses.insert_one({
            "id": response_id,
            "feedback_id": feedback_id,
            "user_id": current_user["id"],
            "content": response.content,
            "created_at": now
        })

        # Notify feedback author
        if feedback["user_id"] != current_user["id"]:
            await send_notification(
                user_id=feedback["user_id"],
                title="Response to Your Feedback",
                message=f"Someone responded to your feedback: {feedback['title']}",
                category="general"
            )

        return {"message": "Response added", "response_id": response_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/{feedback_id}/status")
async def update_feedback_status(
    feedback_id: str,
    status: str,
    current_user: dict = Depends(require_admin)
):
    """Update feedback status (admin only)"""
    try:
        valid_statuses = ["submitted", "under_review", "planned", "in_progress", "completed", "rejected"]
        if status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Invalid status. Valid: {valid_statuses}")

        feedback = await db.feedback.find_one({"id": feedback_id})
        if not feedback:
            raise HTTPException(status_code=404, detail="Feedback not found")

        now = datetime.now(timezone.utc).isoformat()

        await db.feedback.update_one(
            {"id": feedback_id},
            {"$set": {"status": status, "updated_at": now}}
        )

        # Notify author
        await send_notification(
            user_id=feedback["user_id"],
            title="Feedback Status Updated",
            message=f"Your feedback '{feedback['title']}' status changed to: {status}",
            category="general"
        )

        return {"message": "Status updated", "status": status}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ==================== IDEAS SECTION ====================

@router.post("/ideas/submit")
async def submit_idea(idea: IdeaCreate, current_user: dict = Depends(get_current_user)):
    """Submit a new idea"""
    try:
        idea_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        idea_data = {
            "id": idea_id,
            "user_id": current_user["id"],
            "title": idea.title,
            "description": idea.description,
            "category": idea.category,
            "estimated_impact": idea.estimated_impact,
            "implementation_difficulty": idea.implementation_difficulty,
            "status": "submitted",
            "votes_count": 0,
            "upvotes": 0,
            "downvotes": 0,
            "created_at": now,
            "updated_at": now
        }

        await db.ideas.insert_one(idea_data)

        # Reward user
        await db.users.update_one(
            {"id": current_user["id"]},
            {"$inc": {"realum_balance": IDEA_REWARD}}
        )

        await token_service.create_transaction(
            user_id=current_user["id"],
            tx_type="credit",
            amount=IDEA_REWARD,
            description="Reward for submitting idea"
        )

        return {
            "message": "Idea submitted successfully",
            "idea_id": idea_id,
            "reward": IDEA_REWARD
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/ideas/all")
async def get_all_ideas(
    category: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """Get all ideas"""
    try:
        query = {}
        if category:
            query["category"] = category
        if status:
            query["status"] = status

        ideas = await db.ideas.find(
            query, {"_id": 0}
        ).sort("votes_count", -1).skip(skip).limit(limit).to_list(limit)

        # Enrich with user info
        for idea in ideas:
            user = await db.users.find_one(
                {"id": idea["user_id"]},
                {"_id": 0, "username": 1, "avatar_url": 1}
            )
            if user:
                idea["username"] = user.get("username")
                idea["avatar_url"] = user.get("avatar_url")

        total = await db.ideas.count_documents(query)

        return {"ideas": ideas, "total": total}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/ideas/vote/{idea_id}")
async def vote_on_idea(
    idea_id: str,
    vote: VoteRequest,
    current_user: dict = Depends(get_current_user)
):
    """Vote on an idea"""
    try:
        idea = await db.ideas.find_one({"id": idea_id})
        if not idea:
            raise HTTPException(status_code=404, detail="Idea not found")

        existing = await db.idea_votes.find_one({
            "idea_id": idea_id,
            "user_id": current_user["id"]
        })

        now = datetime.now(timezone.utc).isoformat()

        if existing:
            raise HTTPException(status_code=400, detail="Already voted")

        await db.idea_votes.insert_one({
            "id": str(uuid.uuid4()),
            "idea_id": idea_id,
            "user_id": current_user["id"],
            "vote_type": vote.vote_type,
            "created_at": now
        })

        if vote.vote_type == "upvote":
            await db.ideas.update_one(
                {"id": idea_id},
                {"$inc": {"upvotes": 1, "votes_count": 1}}
            )
        else:
            await db.ideas.update_one(
                {"id": idea_id},
                {"$inc": {"downvotes": 1, "votes_count": -1}}
            )

        return {"message": "Vote recorded"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
