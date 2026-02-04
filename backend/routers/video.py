from fastapi import APIRouter, HTTPException, Depends, Query
from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel
import uuid

from core.database import db
from core.auth import get_current_user, require_admin

router = APIRouter(prefix="/api/video", tags=["Video Streaming"])

class VideoCreate(BaseModel):
    course_id: str
    title: str
    description: Optional[str] = None
    video_url: str
    thumbnail_url: Optional[str] = None
    duration_seconds: int
    order: int = 0
    chapters: List[dict] = []  # [{title, start_time, end_time}]
    is_preview: bool = False

class VideoProgress(BaseModel):
    video_id: str
    position_seconds: int
    completed: bool = False

class VideoNote(BaseModel):
    video_id: str
    timestamp_seconds: int
    content: str

@router.post("/videos")
async def create_video(
    video: VideoCreate,
    current_user: dict = Depends(require_admin)
):
    """Create a new video for a course (admin only)"""
    try:
        video_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        video_data = {
            "id": video_id,
            **video.dict(),
            "views": 0,
            "likes": 0,
            "avg_watch_time": 0,
            "created_by": current_user["id"],
            "created_at": now
        }
        
        await db.videos.insert_one(video_data)
        video_data.pop("_id", None)
        
        # Update course video count
        await db.courses.update_one(
            {"id": video.course_id},
            {"$inc": {"video_count": 1}}
        )
        
        return {"message": "Video created", "video": video_data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/courses/{course_id}/videos")
async def get_course_videos(
    course_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all videos for a course"""
    try:
        videos = await db.videos.find(
            {"course_id": course_id},
            {"_id": 0}
        ).sort("order", 1).to_list(100)
        
        # Get user progress for each video
        user_id = current_user["id"]
        for video in videos:
            progress = await db.video_progress.find_one(
                {"video_id": video["id"], "user_id": user_id},
                {"_id": 0}
            )
            video["user_progress"] = progress
        
        return {"videos": videos, "count": len(videos)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/videos/{video_id}")
async def get_video(
    video_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get video details with streaming URL"""
    try:
        video = await db.videos.find_one({"id": video_id}, {"_id": 0})
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Check course enrollment (unless preview)
        if not video.get("is_preview"):
            enrollment = await db.enrollments.find_one({
                "course_id": video["course_id"],
                "user_id": current_user["id"]
            })
            if not enrollment:
                raise HTTPException(status_code=403, detail="Not enrolled in course")
        
        # Get user progress
        progress = await db.video_progress.find_one(
            {"video_id": video_id, "user_id": current_user["id"]},
            {"_id": 0}
        )
        video["user_progress"] = progress
        
        # Get user notes
        notes = await db.video_notes.find(
            {"video_id": video_id, "user_id": current_user["id"]},
            {"_id": 0}
        ).sort("timestamp_seconds", 1).to_list(100)
        video["user_notes"] = notes
        
        # Increment view count
        await db.videos.update_one(
            {"id": video_id},
            {"$inc": {"views": 1}}
        )
        
        return {"video": video}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/progress")
async def update_progress(
    progress: VideoProgress,
    current_user: dict = Depends(get_current_user)
):
    """Update video watch progress"""
    try:
        now = datetime.now(timezone.utc).isoformat()
        user_id = current_user["id"]
        
        existing = await db.video_progress.find_one({
            "video_id": progress.video_id,
            "user_id": user_id
        })
        
        if existing:
            # Update existing progress
            update_data = {
                "position_seconds": progress.position_seconds,
                "updated_at": now
            }
            if progress.completed and not existing.get("completed"):
                update_data["completed"] = True
                update_data["completed_at"] = now
            
            await db.video_progress.update_one(
                {"video_id": progress.video_id, "user_id": user_id},
                {"$set": update_data}
            )
        else:
            # Create new progress
            await db.video_progress.insert_one({
                "id": str(uuid.uuid4()),
                "video_id": progress.video_id,
                "user_id": user_id,
                "position_seconds": progress.position_seconds,
                "completed": progress.completed,
                "completed_at": now if progress.completed else None,
                "created_at": now,
                "updated_at": now
            })
        
        # Check if all videos in course completed
        if progress.completed:
            video = await db.videos.find_one({"id": progress.video_id})
            if video:
                course_videos = await db.videos.count_documents({"course_id": video["course_id"]})
                completed_videos = await db.video_progress.count_documents({
                    "user_id": user_id,
                    "completed": True,
                    "video_id": {"$in": [v["id"] for v in await db.videos.find({"course_id": video["course_id"]}).to_list(100)]}
                })
                
                if completed_videos >= course_videos:
                    # Mark course as completed
                    await db.enrollments.update_one(
                        {"course_id": video["course_id"], "user_id": user_id},
                        {"$set": {"completed": True, "completed_at": now}}
                    )
        
        return {"message": "Progress updated"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/progress/{video_id}")
async def get_progress(
    video_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get video progress for current user"""
    try:
        progress = await db.video_progress.find_one(
            {"video_id": video_id, "user_id": current_user["id"]},
            {"_id": 0}
        )
        return {"progress": progress}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/notes")
async def add_note(
    note: VideoNote,
    current_user: dict = Depends(get_current_user)
):
    """Add a note to a video at specific timestamp"""
    try:
        note_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        note_data = {
            "id": note_id,
            "video_id": note.video_id,
            "user_id": current_user["id"],
            "timestamp_seconds": note.timestamp_seconds,
            "content": note.content,
            "created_at": now
        }
        
        await db.video_notes.insert_one(note_data)
        note_data.pop("_id", None)
        
        return {"message": "Note added", "note": note_data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/notes/{video_id}")
async def get_notes(
    video_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all notes for a video"""
    try:
        notes = await db.video_notes.find(
            {"video_id": video_id, "user_id": current_user["id"]},
            {"_id": 0}
        ).sort("timestamp_seconds", 1).to_list(100)
        
        return {"notes": notes}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/notes/{note_id}")
async def delete_note(
    note_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a note"""
    try:
        result = await db.video_notes.delete_one({
            "id": note_id,
            "user_id": current_user["id"]
        })
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Note not found")
        
        return {"message": "Note deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/videos/{video_id}/like")
async def like_video(
    video_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Like a video"""
    try:
        existing = await db.video_likes.find_one({
            "video_id": video_id,
            "user_id": current_user["id"]
        })
        
        if existing:
            return {"message": "Already liked"}
        
        await db.video_likes.insert_one({
            "id": str(uuid.uuid4()),
            "video_id": video_id,
            "user_id": current_user["id"],
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        await db.videos.update_one(
            {"id": video_id},
            {"$inc": {"likes": 1}}
        )
        
        return {"message": "Video liked"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/history")
async def get_watch_history(
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """Get user's video watch history"""
    try:
        progress_list = await db.video_progress.find(
            {"user_id": current_user["id"]},
            {"_id": 0}
        ).sort("updated_at", -1).limit(limit).to_list(limit)
        
        history = []
        for p in progress_list:
            video = await db.videos.find_one(
                {"id": p["video_id"]},
                {"_id": 0, "id": 1, "title": 1, "thumbnail_url": 1, "duration_seconds": 1, "course_id": 1}
            )
            if video:
                history.append({
                    **video,
                    "progress": p
                })
        
        return {"history": history}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
