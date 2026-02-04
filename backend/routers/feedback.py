from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from core.auth import get_current_user
from core.database import db
from services.token_service import TokenService

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

class VoteRequest(BaseModel):
    vote_type: str

@router.post("/submit")
async def submit_feedback(feedback: FeedbackCreate, current_user: dict = Depends(get_current_user)):
    try:
        data = {
            "user_id": current_user["id"],
            "category": feedback.category,
            "title": feedback.title,
            "description": feedback.description,
            "priority": feedback.priority,
            "status": "submitted",
            "votes_count": 0
        }

        result = supabase.table("feedback").insert(data).execute()

        reward_amount = 10
        user_result = supabase.table("users").select("realum_balance").eq("id", current_user["id"]).execute()
        current_balance = float(user_result.data[0].get("realum_balance", 0))
        new_balance = current_balance + reward_amount

        supabase.table("users").update({"realum_balance": new_balance}).eq("id", current_user["id"]).execute()

        token_service.create_transaction(
            user_id=current_user["id"],
            amount=reward_amount,
            transaction_type="feedback_reward",
            description="Reward for submitting feedback"
        )

        return {
            "message": "Feedback submitted successfully",
            "feedback": result.data[0],
            "reward": reward_amount
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/all")
async def get_all_feedback(
    category: Optional[str] = None,
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    try:
        query = supabase.table("feedback").select("*, users(username, avatar)")

        if category:
            query = query.eq("category", category)
        if status:
            query = query.eq("status", status)

        result = query.order("votes_count", desc=True).execute()

        return {"feedback": result.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/vote/{feedback_id}")
async def vote_on_feedback(
    feedback_id: str,
    vote: VoteRequest,
    current_user: dict = Depends(get_current_user)
):
    try:
        existing_vote = supabase.table("feedback_votes").select("*").eq("feedback_id", feedback_id).eq("user_id", current_user["id"]).execute()

        if existing_vote.data:
            raise HTTPException(status_code=400, detail="You have already voted on this feedback")

        vote_data = {
            "feedback_id": feedback_id,
            "user_id": current_user["id"],
            "vote_type": vote.vote_type
        }

        supabase.table("feedback_votes").insert(vote_data).execute()

        vote_increment = 1 if vote.vote_type == "upvote" else -1

        feedback_result = supabase.table("feedback").select("votes_count, user_id").eq("id", feedback_id).execute()

        if feedback_result.data:
            current_votes = feedback_result.data[0].get("votes_count", 0)
            new_votes = current_votes + vote_increment

            supabase.table("feedback").update({"votes_count": new_votes}).eq("id", feedback_id).execute()

            if vote.vote_type == "upvote":
                feedback_owner_id = feedback_result.data[0]["user_id"]
                owner_result = supabase.table("users").select("realum_balance").eq("id", feedback_owner_id).execute()

                if owner_result.data:
                    current_balance = float(owner_result.data[0].get("realum_balance", 0))
                    reward = 5
                    new_balance = current_balance + reward

                    supabase.table("users").update({"realum_balance": new_balance}).eq("id", feedback_owner_id).execute()

                    token_service.create_transaction(
                        user_id=feedback_owner_id,
                        amount=reward,
                        transaction_type="upvote_reward",
                        description="Reward for receiving upvote on feedback"
                    )

        return {"message": "Vote recorded", "new_vote_count": new_votes if feedback_result.data else 0}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/ideas")
async def submit_idea(idea: IdeaCreate, current_user: dict = Depends(get_current_user)):
    try:
        data = {
            "user_id": current_user["id"],
            "title": idea.title,
            "description": idea.description,
            "category": idea.category,
            "estimated_impact": idea.estimated_impact,
            "status": "submitted",
            "votes_count": 0,
            "implementation_status": "proposed"
        }

        result = supabase.table("ideas").insert(data).execute()

        reward_amount = 25
        user_result = supabase.table("users").select("realum_balance").eq("id", current_user["id"]).execute()
        current_balance = float(user_result.data[0].get("realum_balance", 0))
        new_balance = current_balance + reward_amount

        supabase.table("users").update({"realum_balance": new_balance}).eq("id", current_user["id"]).execute()

        token_service.create_transaction(
            user_id=current_user["id"],
            amount=reward_amount,
            transaction_type="idea_reward",
            description="Reward for submitting idea"
        )

        return {
            "message": "Idea submitted successfully",
            "idea": result.data[0],
            "reward": reward_amount
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/ideas")
async def get_all_ideas(
    category: Optional[str] = None,
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    try:
        query = supabase.table("ideas").select("*, users(username, avatar)")

        if category:
            query = query.eq("category", category)
        if status:
            query = query.eq("implementation_status", status)

        result = query.order("votes_count", desc=True).execute()

        return {"ideas": result.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/ideas/vote/{idea_id}")
async def vote_on_idea(
    idea_id: str,
    vote: VoteRequest,
    current_user: dict = Depends(get_current_user)
):
    try:
        existing_vote = supabase.table("idea_votes").select("*").eq("idea_id", idea_id).eq("user_id", current_user["id"]).execute()

        if existing_vote.data:
            raise HTTPException(status_code=400, detail="You have already voted on this idea")

        vote_data = {
            "idea_id": idea_id,
            "user_id": current_user["id"],
            "vote_type": vote.vote_type
        }

        supabase.table("idea_votes").insert(vote_data).execute()

        vote_increment = 1 if vote.vote_type == "upvote" else -1

        idea_result = supabase.table("ideas").select("votes_count, user_id").eq("id", idea_id).execute()

        if idea_result.data:
            current_votes = idea_result.data[0].get("votes_count", 0)
            new_votes = current_votes + vote_increment

            supabase.table("ideas").update({"votes_count": new_votes}).eq("id", idea_id).execute()

            if new_votes >= 50 and vote.vote_type == "upvote":
                idea_owner_id = idea_result.data[0]["user_id"]
                owner_result = supabase.table("users").select("realum_balance").eq("id", idea_owner_id).execute()

                if owner_result.data:
                    current_balance = float(owner_result.data[0].get("realum_balance", 0))
                    bonus_reward = 100
                    new_balance = current_balance + bonus_reward

                    supabase.table("users").update({"realum_balance": new_balance}).eq("id", idea_owner_id).execute()

                    token_service.create_transaction(
                        user_id=idea_owner_id,
                        amount=bonus_reward,
                        transaction_type="popular_idea_bonus",
                        description="Bonus for popular idea (50+ votes)"
                    )

        return {"message": "Vote recorded", "new_vote_count": new_votes if idea_result.data else 0}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/my-contributions")
async def get_my_contributions(current_user: dict = Depends(get_current_user)):
    try:
        feedback_result = supabase.table("feedback").select("*").eq("user_id", current_user["id"]).execute()
        ideas_result = supabase.table("ideas").select("*").eq("user_id", current_user["id"]).execute()

        total_rewards = 0
        for fb in feedback_result.data if feedback_result.data else []:
            total_rewards += (fb.get("votes_count", 0) * 5) + 10

        for idea in ideas_result.data if ideas_result.data else []:
            total_rewards += (idea.get("votes_count", 0) * 5) + 25
            if idea.get("votes_count", 0) >= 50:
                total_rewards += 100

        return {
            "feedback": feedback_result.data,
            "ideas": ideas_result.data,
            "total_contributions": len(feedback_result.data or []) + len(ideas_result.data or []),
            "total_rewards_earned": total_rewards
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/top-contributors")
async def get_top_contributors():
    try:
        feedback_result = supabase.table("feedback").select("user_id").execute()
        ideas_result = supabase.table("ideas").select("user_id").execute()

        user_contributions = {}
        for fb in feedback_result.data if feedback_result.data else []:
            user_id = fb["user_id"]
            user_contributions[user_id] = user_contributions.get(user_id, 0) + 1

        for idea in ideas_result.data if ideas_result.data else []:
            user_id = idea["user_id"]
            user_contributions[user_id] = user_contributions.get(user_id, 0) + 1

        top_contributors = []
        for user_id, count in sorted(user_contributions.items(), key=lambda x: x[1], reverse=True)[:10]:
            user_result = supabase.table("users").select("username, avatar").eq("id", user_id).execute()
            if user_result.data:
                top_contributors.append({
                    "user_id": user_id,
                    "username": user_result.data[0].get("username"),
                    "avatar": user_result.data[0].get("avatar"),
                    "contributions": count
                })

        return {"top_contributors": top_contributors}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
