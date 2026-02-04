from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from core.auth import get_current_user
from core.database import supabase

router = APIRouter(prefix="/api/social", tags=["Social"])

class CommentCreate(BaseModel):
    content_type: str
    content_id: str
    content: str
    parent_comment_id: Optional[str] = None

class PostCreate(BaseModel):
    content: str
    media_urls: Optional[list] = []

@router.post("/follow/{user_id}")
async def follow_user(user_id: str, current_user: dict = Depends(get_current_user)):
    try:
        if user_id == current_user["id"]:
            raise HTTPException(status_code=400, detail="Cannot follow yourself")

        existing_follow = supabase.table("follows").select("*").eq("follower_id", current_user["id"]).eq("following_id", user_id).execute()

        if existing_follow.data:
            raise HTTPException(status_code=400, detail="Already following this user")

        data = {
            "follower_id": current_user["id"],
            "following_id": user_id
        }

        result = supabase.table("follows").insert(data).execute()

        return {
            "message": "User followed successfully",
            "follow": result.data[0]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/unfollow/{user_id}")
async def unfollow_user(user_id: str, current_user: dict = Depends(get_current_user)):
    try:
        supabase.table("follows").delete().eq("follower_id", current_user["id"]).eq("following_id", user_id).execute()

        return {"message": "User unfollowed successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/followers/{user_id}")
async def get_followers(user_id: str):
    try:
        result = supabase.table("follows").select("follower_id, users(username, avatar)").eq("following_id", user_id).execute()

        followers = []
        for follow in result.data if result.data else []:
            if follow.get("users"):
                followers.append({
                    "user_id": follow["follower_id"],
                    "username": follow["users"]["username"],
                    "avatar": follow["users"]["avatar"]
                })

        return {"followers": followers, "count": len(followers)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/following/{user_id}")
async def get_following(user_id: str):
    try:
        result = supabase.table("follows").select("following_id, users(username, avatar)").eq("follower_id", user_id).execute()

        following = []
        for follow in result.data if result.data else []:
            if follow.get("users"):
                following.append({
                    "user_id": follow["following_id"],
                    "username": follow["users"]["username"],
                    "avatar": follow["users"]["avatar"]
                })

        return {"following": following, "count": len(following)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/like")
async def like_content(
    content_type: str,
    content_id: str,
    current_user: dict = Depends(get_current_user)
):
    try:
        existing_like = supabase.table("likes").select("*").eq("user_id", current_user["id"]).eq("content_type", content_type).eq("content_id", content_id).execute()

        if existing_like.data:
            supabase.table("likes").delete().eq("user_id", current_user["id"]).eq("content_type", content_type).eq("content_id", content_id).execute()

            if content_type == "course":
                course_result = supabase.table("courses").select("likes").eq("id", content_id).execute()
                if course_result.data:
                    current_likes = course_result.data[0].get("likes", 0)
                    supabase.table("courses").update({"likes": max(0, current_likes - 1)}).eq("id", content_id).execute()

            elif content_type == "project":
                project_result = supabase.table("projects").select("likes").eq("id", content_id).execute()
                if project_result.data:
                    current_likes = project_result.data[0].get("likes", 0)
                    supabase.table("projects").update({"likes": max(0, current_likes - 1)}).eq("id", content_id).execute()

            return {"message": "Like removed", "liked": False}

        else:
            like_data = {
                "user_id": current_user["id"],
                "content_type": content_type,
                "content_id": content_id
            }

            supabase.table("likes").insert(like_data).execute()

            if content_type == "course":
                course_result = supabase.table("courses").select("likes").eq("id", content_id).execute()
                if course_result.data:
                    current_likes = course_result.data[0].get("likes", 0)
                    supabase.table("courses").update({"likes": current_likes + 1}).eq("id", content_id).execute()

            elif content_type == "project":
                project_result = supabase.table("projects").select("likes").eq("id", content_id).execute()
                if project_result.data:
                    current_likes = project_result.data[0].get("likes", 0)
                    supabase.table("projects").update({"likes": current_likes + 1}).eq("id", content_id).execute()

            return {"message": "Content liked", "liked": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/comments")
async def create_comment(comment: CommentCreate, current_user: dict = Depends(get_current_user)):
    try:
        data = {
            "user_id": current_user["id"],
            "content_type": comment.content_type,
            "content_id": comment.content_id,
            "content": comment.content,
            "parent_comment_id": comment.parent_comment_id,
            "likes": 0
        }

        result = supabase.table("comments").insert(data).execute()

        return {
            "message": "Comment created",
            "comment": result.data[0]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/comments/{content_type}/{content_id}")
async def get_comments(content_type: str, content_id: str):
    try:
        result = supabase.table("comments").select("*, users(username, avatar)").eq("content_type", content_type).eq("content_id", content_id).eq("is_removed", False).order("created_at", desc=True).execute()

        comments = []
        for comment in result.data if result.data else []:
            comment_data = {**comment}
            if comment.get("parent_comment_id"):
                replies_result = supabase.table("comments").select("*, users(username, avatar)").eq("parent_comment_id", comment["id"]).eq("is_removed", False).execute()
                comment_data["replies"] = replies_result.data or []

            comments.append(comment_data)

        return {"comments": comments}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/comments/{comment_id}")
async def delete_comment(comment_id: str, current_user: dict = Depends(get_current_user)):
    try:
        comment_result = supabase.table("comments").select("*").eq("id", comment_id).eq("user_id", current_user["id"]).execute()

        if not comment_result.data:
            raise HTTPException(status_code=404, detail="Comment not found or you don't have permission")

        supabase.table("comments").update({"is_removed": True}).eq("id", comment_id).execute()

        return {"message": "Comment deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/feed")
async def get_activity_feed(
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    try:
        following_result = supabase.table("follows").select("following_id").eq("follower_id", current_user["id"]).execute()

        following_ids = [f["following_id"] for f in following_result.data] if following_result.data else []
        following_ids.append(current_user["id"])

        activities = []

        courses_result = supabase.table("courses").select("*, users(username, avatar)").in_("creator_id", following_ids).order("created_at", desc=True).limit(limit).execute()
        for course in courses_result.data if courses_result.data else []:
            activities.append({
                "type": "course_created",
                "data": course,
                "created_at": course["created_at"]
            })

        projects_result = supabase.table("projects").select("*, users(username, avatar)").in_("creator_id", following_ids).order("created_at", desc=True).limit(limit).execute()
        for project in projects_result.data if projects_result.data else []:
            activities.append({
                "type": "project_created",
                "data": project,
                "created_at": project["created_at"]
            })

        activities.sort(key=lambda x: x["created_at"], reverse=True)

        return {"feed": activities[:limit]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/posts")
async def create_post(post: PostCreate, current_user: dict = Depends(get_current_user)):
    try:
        data = {
            "user_id": current_user["id"],
            "content": post.content,
            "media_urls": post.media_urls,
            "likes": 0,
            "comments_count": 0
        }

        result = supabase.table("posts").insert(data).execute()

        return {
            "message": "Post created",
            "post": result.data[0]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/posts")
async def get_posts(
    user_id: Optional[str] = None,
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    try:
        query = supabase.table("posts").select("*, users(username, avatar)")

        if user_id:
            query = query.eq("user_id", user_id)

        result = query.order("created_at", desc=True).limit(limit).execute()

        return {"posts": result.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/notifications")
async def get_notifications(current_user: dict = Depends(get_current_user)):
    try:
        notifications = []

        new_followers = supabase.table("follows").select("follower_id, created_at, users(username, avatar)").eq("following_id", current_user["id"]).order("created_at", desc=True).limit(10).execute()

        for follow in new_followers.data if new_followers.data else []:
            if follow.get("users"):
                notifications.append({
                    "type": "new_follower",
                    "user": follow["users"],
                    "created_at": follow["created_at"]
                })

        new_comments = supabase.table("comments").select("id, content, created_at, users(username, avatar)").or_(f"content_type.eq.course,content_type.eq.project").order("created_at", desc=True).limit(10).execute()

        for comment in new_comments.data if new_comments.data else []:
            if comment.get("users"):
                notifications.append({
                    "type": "new_comment",
                    "comment": comment["content"],
                    "user": comment["users"],
                    "created_at": comment["created_at"]
                })

        notifications.sort(key=lambda x: x["created_at"], reverse=True)

        return {"notifications": notifications[:20]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/trending-posts")
async def get_trending_posts():
    try:
        result = supabase.table("posts").select("*, users(username, avatar)").order("likes", desc=True).limit(10).execute()

        return {"trending_posts": result.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
