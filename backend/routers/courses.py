from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime, timezone
import uuid

from core.database import db
from core.auth import get_current_user
from services.token_service import add_xp, award_badge, create_transaction

router = APIRouter(prefix="/courses", tags=["Learning"])

@router.get("")
async def get_courses(category: Optional[str] = None, difficulty: Optional[str] = None):
    query = {}
    if category:
        query["category"] = category
    if difficulty:
        query["difficulty"] = difficulty
    courses = await db.courses.find(query, {"_id": 0}).to_list(100)
    return {"courses": courses}

@router.get("/{course_id}")
async def get_course(course_id: str, current_user: dict = Depends(get_current_user)):
    course = await db.courses.find_one({"id": course_id}, {"_id": 0})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Get user progress
    enrollment = await db.enrollments.find_one({
        "user_id": current_user["id"],
        "course_id": course_id
    }, {"_id": 0})
    
    return {
        "course": course,
        "enrollment": enrollment
    }

@router.post("/{course_id}/enroll")
async def enroll_in_course(course_id: str, current_user: dict = Depends(get_current_user)):
    course = await db.courses.find_one({"id": course_id}, {"_id": 0})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    existing = await db.enrollments.find_one({
        "user_id": current_user["id"],
        "course_id": course_id
    })
    if existing:
        raise HTTPException(status_code=400, detail="Already enrolled")
    
    enrollment = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "course_id": course_id,
        "progress": 0,
        "lessons_completed": [],
        "enrolled_at": datetime.now(timezone.utc).isoformat(),
        "completed": False
    }
    
    await db.enrollments.insert_one(enrollment)
    
    # Award learner badge on first enrollment
    enrollments_count = await db.enrollments.count_documents({"user_id": current_user["id"]})
    if enrollments_count == 1:
        await award_badge(current_user["id"], "lifelong_learner")
    
    return {"status": "enrolled", "course": course["title"]}

@router.post("/{course_id}/lesson/{lesson_id}/complete")
async def complete_lesson(
    course_id: str,
    lesson_id: str,
    current_user: dict = Depends(get_current_user)
):
    course = await db.courses.find_one({"id": course_id}, {"_id": 0})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    enrollment = await db.enrollments.find_one({
        "user_id": current_user["id"],
        "course_id": course_id
    })
    if not enrollment:
        raise HTTPException(status_code=400, detail="Not enrolled in this course")
    
    if lesson_id in enrollment.get("lessons_completed", []):
        raise HTTPException(status_code=400, detail="Lesson already completed")
    
    # Update enrollment
    lessons_completed = enrollment.get("lessons_completed", []) + [lesson_id]
    total_lessons = len(course.get("lessons", []))
    progress = (len(lessons_completed) / total_lessons * 100) if total_lessons > 0 else 100
    
    updates = {
        "lessons_completed": lessons_completed,
        "progress": progress
    }
    
    result = {"status": "lesson_completed", "progress": progress}
    
    # Check if course completed
    if progress >= 100:
        updates["completed"] = True
        updates["completed_at"] = datetime.now(timezone.utc).isoformat()
        
        # Award rewards
        xp_reward = course.get("xp_reward", 0)
        rlm_reward = course.get("rlm_reward", 0)
        
        await add_xp(current_user["id"], xp_reward)
        
        if rlm_reward > 0:
            await db.users.update_one(
                {"id": current_user["id"]},
                {"$inc": {"realum_balance": rlm_reward}}
            )
            await create_transaction(
                current_user["id"], "credit", rlm_reward,
                f"Course completed: {course['title']}"
            )
        
        # Add to completed courses
        await db.users.update_one(
            {"id": current_user["id"]},
            {"$addToSet": {"courses_completed": course_id}}
        )
        
        # Award course badge if any
        if course.get("badge_awarded"):
            await award_badge(current_user["id"], course["badge_awarded"])
        
        result["course_completed"] = True
        result["xp_earned"] = xp_reward
        result["rlm_earned"] = rlm_reward
    
    await db.enrollments.update_one(
        {"_id": enrollment["_id"]},
        {"$set": updates}
    )
    
    return result
