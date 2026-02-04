from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel
import uuid

from core.database import db
from core.auth import get_current_user

router = APIRouter(prefix="/api/recommendations", tags=["AI Recommendations"])

class RecommendationFeedback(BaseModel):
    item_id: str
    item_type: str
    feedback: str  # liked, disliked, saved, dismissed

@router.get("/courses")
async def get_course_recommendations(
    limit: int = 5,
    current_user: dict = Depends(get_current_user)
):
    """Get AI-powered course recommendations based on user profile"""
    try:
        user_id = current_user["id"]
        user_skills = current_user.get("skills", [])
        completed = current_user.get("courses_completed", [])
        
        # Get courses not completed by user
        query = {"id": {"$nin": completed}, "is_published": True}
        
        # If user has skills, prioritize related courses
        if user_skills:
            courses = await db.courses.find(
                {**query, "skills": {"$in": user_skills}},
                {"_id": 0}
            ).limit(limit).to_list(limit)
        else:
            courses = []
        
        # Fill remaining with popular courses
        if len(courses) < limit:
            remaining = limit - len(courses)
            popular = await db.courses.find(
                {**query, "id": {"$nin": [c["id"] for c in courses]}},
                {"_id": 0}
            ).sort("enrollment_count", -1).limit(remaining).to_list(remaining)
            courses.extend(popular)
        
        # Add recommendation reasons
        for course in courses:
            reasons = []
            if any(s in course.get("skills", []) for s in user_skills):
                reasons.append("Matches your skills")
            if course.get("enrollment_count", 0) > 100:
                reasons.append("Popular course")
            if course.get("rating", 0) >= 4.5:
                reasons.append("Highly rated")
            course["recommendation_reasons"] = reasons or ["Recommended for you"]
        
        return {"recommendations": courses, "type": "courses"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/jobs")
async def get_job_recommendations(
    limit: int = 5,
    current_user: dict = Depends(get_current_user)
):
    """Get job recommendations based on user skills and experience"""
    try:
        user_skills = current_user.get("skills", [])
        user_role = current_user.get("role", "citizen")
        
        query = {"status": "open"}
        
        # Match by skills
        if user_skills:
            jobs = await db.jobs.find(
                {**query, "required_skills": {"$in": user_skills}},
                {"_id": 0}
            ).limit(limit).to_list(limit)
        else:
            jobs = await db.jobs.find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
        
        for job in jobs:
            match_score = 0
            reasons = []
            
            # Calculate skill match
            req_skills = set(job.get("required_skills", []))
            user_skill_set = set(user_skills)
            if req_skills:
                match_score = len(req_skills & user_skill_set) / len(req_skills) * 100
                if match_score >= 80:
                    reasons.append(f"{int(match_score)}% skill match")
                elif match_score >= 50:
                    reasons.append("Partial skill match")
            
            if job.get("budget", 0) > 500:
                reasons.append("High reward")
            
            job["match_score"] = round(match_score, 1)
            job["recommendation_reasons"] = reasons or ["New opportunity"]
        
        # Sort by match score
        jobs.sort(key=lambda x: x.get("match_score", 0), reverse=True)
        
        return {"recommendations": jobs, "type": "jobs"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/users")
async def get_user_recommendations(
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """Get recommended users to follow based on interests"""
    try:
        user_id = current_user["id"]
        user_skills = current_user.get("skills", [])
        
        # Get users not already following
        following = await db.follows.find(
            {"follower_id": user_id},
            {"_id": 0, "following_id": 1}
        ).to_list(None)
        following_ids = [f["following_id"] for f in following] + [user_id]
        
        query = {"id": {"$nin": following_ids}}
        
        # Find users with similar skills
        if user_skills:
            users = await db.users.find(
                {**query, "skills": {"$in": user_skills}},
                {"_id": 0, "id": 1, "username": 1, "avatar_url": 1, "skills": 1, "level": 1}
            ).limit(limit).to_list(limit)
        else:
            users = await db.users.find(
                query,
                {"_id": 0, "id": 1, "username": 1, "avatar_url": 1, "skills": 1, "level": 1}
            ).sort("xp", -1).limit(limit).to_list(limit)
        
        for user in users:
            shared = set(user.get("skills", [])) & set(user_skills)
            user["shared_skills"] = list(shared)
            user["recommendation_reason"] = f"{len(shared)} shared skills" if shared else "Active contributor"
        
        return {"recommendations": users, "type": "users"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/content")
async def get_content_recommendations(
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """Get personalized content feed"""
    try:
        user_id = current_user["id"]
        
        # Get user interests from activity
        viewed = await db.content_views.find(
            {"user_id": user_id},
            {"_id": 0, "content_id": 1, "category": 1}
        ).sort("viewed_at", -1).limit(50).to_list(50)
        
        viewed_ids = [v["content_id"] for v in viewed]
        categories = list(set(v.get("category") for v in viewed if v.get("category")))
        
        query = {"status": "published", "id": {"$nin": viewed_ids}}
        
        if categories:
            content = await db.content.find(
                {**query, "category": {"$in": categories}},
                {"_id": 0}
            ).sort("created_at", -1).limit(limit).to_list(limit)
        else:
            content = await db.content.find(query, {"_id": 0}).sort("views", -1).limit(limit).to_list(limit)
        
        return {"recommendations": content, "type": "content"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/feedback")
async def submit_recommendation_feedback(
    feedback: RecommendationFeedback,
    current_user: dict = Depends(get_current_user)
):
    """Submit feedback on recommendations to improve AI"""
    try:
        now = datetime.now(timezone.utc).isoformat()
        
        await db.recommendation_feedback.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": current_user["id"],
            "item_id": feedback.item_id,
            "item_type": feedback.item_type,
            "feedback": feedback.feedback,
            "created_at": now
        })
        
        return {"message": "Feedback recorded"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/for-you")
async def get_personalized_feed(
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """Get unified personalized feed combining all recommendations"""
    try:
        feed = []
        
        # Get a mix of recommendations
        courses = (await get_course_recommendations(3, current_user))["recommendations"]
        jobs = (await get_job_recommendations(3, current_user))["recommendations"]
        users = (await get_user_recommendations(4, current_user))["recommendations"]
        
        for c in courses:
            feed.append({"type": "course", "data": c, "priority": 1})
        for j in jobs:
            feed.append({"type": "job", "data": j, "priority": 2})
        for u in users:
            feed.append({"type": "user", "data": u, "priority": 3})
        
        # Mix the feed
        import random
        random.shuffle(feed)
        feed.sort(key=lambda x: x["priority"])
        
        return {"feed": feed[:limit], "generated_at": datetime.now(timezone.utc).isoformat()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
