from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import uuid

from core.database import db
from core.auth import get_current_user
from services.notification_service import send_notification

router = APIRouter(prefix="/social", tags=["Social Features"])

class CommentCreate(BaseModel):
    content: str
    parent_id: Optional[str] = None  # For nested comments

class ReactionCreate(BaseModel):
    reaction_type: str = "like"  # like, love, celebrate, insightful, curious

# ===================== FOLLOWS =====================

@router.post("/follow/{user_id}")
async def follow_user(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Follow a user"""
    try:
        if user_id == current_user["id"]:
            raise HTTPException(status_code=400, detail="Cannot follow yourself")

        # Check if user exists
        target = await db.users.find_one({"id": user_id})
        if not target:
            raise HTTPException(status_code=404, detail="User not found")

        # Check if already following
        existing = await db.follows.find_one({
            "follower_id": current_user["id"],
            "following_id": user_id
        })

        if existing:
            raise HTTPException(status_code=400, detail="Already following this user")

        now = datetime.now(timezone.utc).isoformat()

        await db.follows.insert_one({
            "id": str(uuid.uuid4()),
            "follower_id": current_user["id"],
            "following_id": user_id,
            "created_at": now
        })

        # Update follower/following counts
        await db.users.update_one(
            {"id": current_user["id"]},
            {"$inc": {"following_count": 1}}
        )
        await db.users.update_one(
            {"id": user_id},
            {"$inc": {"followers_count": 1}}
        )

        # Notify the followed user
        await send_notification(
            user_id=user_id,
            title="New Follower",
            message=f"{current_user['username']} started following you",
            category="social"
        )

        return {"message": "Now following user"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/follow/{user_id}")
async def unfollow_user(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Unfollow a user"""
    try:
        result = await db.follows.delete_one({
            "follower_id": current_user["id"],
            "following_id": user_id
        })

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Not following this user")

        # Update counts
        await db.users.update_one(
            {"id": current_user["id"]},
            {"$inc": {"following_count": -1}}
        )
        await db.users.update_one(
            {"id": user_id},
            {"$inc": {"followers_count": -1}}
        )

        return {"message": "Unfollowed user"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/followers/{user_id}")
async def get_followers(
    user_id: str,
    skip: int = 0,
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """Get user's followers"""
    try:
        follows = await db.follows.find(
            {"following_id": user_id},
            {"_id": 0}
        ).skip(skip).limit(limit).to_list(limit)

        # Get follower details
        followers = []
        for follow in follows:
            user = await db.users.find_one(
                {"id": follow["follower_id"]},
                {"_id": 0, "id": 1, "username": 1, "avatar_url": 1, "bio": 1}
            )
            if user:
                # Check if current user follows them back
                is_following = await db.follows.find_one({
                    "follower_id": current_user["id"],
                    "following_id": user["id"]
                })
                user["is_following"] = is_following is not None
                followers.append(user)

        total = await db.follows.count_documents({"following_id": user_id})

        return {"followers": followers, "total": total}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/following/{user_id}")
async def get_following(
    user_id: str,
    skip: int = 0,
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """Get users that a user is following"""
    try:
        follows = await db.follows.find(
            {"follower_id": user_id},
            {"_id": 0}
        ).skip(skip).limit(limit).to_list(limit)

        following = []
        for follow in follows:
            user = await db.users.find_one(
                {"id": follow["following_id"]},
                {"_id": 0, "id": 1, "username": 1, "avatar_url": 1, "bio": 1}
            )
            if user:
                is_following = await db.follows.find_one({
                    "follower_id": current_user["id"],
                    "following_id": user["id"]
                })
                user["is_following"] = is_following is not None
                following.append(user)

        total = await db.follows.count_documents({"follower_id": user_id})

        return {"following": following, "total": total}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ===================== COMMENTS =====================

@router.post("/comments/{content_type}/{content_id}")
async def add_comment(
    content_type: str,
    content_id: str,
    comment: CommentCreate,
    current_user: dict = Depends(get_current_user)
):
    """Add a comment to content"""
    try:
        valid_types = ["course", "project", "proposal", "job", "bounty", "post"]
        if content_type not in valid_types:
            raise HTTPException(status_code=400, detail=f"Invalid content type. Use: {valid_types}")

        comment_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        comment_data = {
            "id": comment_id,
            "content_type": content_type,
            "content_id": content_id,
            "author_id": current_user["id"],
            "content": comment.content,
            "parent_id": comment.parent_id,
            "likes_count": 0,
            "replies_count": 0,
            "is_edited": False,
            "is_deleted": False,
            "created_at": now,
            "updated_at": now
        }

        await db.comments.insert_one(comment_data)

        # Update parent reply count if nested comment
        if comment.parent_id:
            await db.comments.update_one(
                {"id": comment.parent_id},
                {"$inc": {"replies_count": 1}}
            )

        # Add author info to response
        comment_data["author_username"] = current_user.get("username")
        comment_data["author_avatar"] = current_user.get("avatar_url")

        return comment_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/comments/{content_type}/{content_id}")
async def get_comments(
    content_type: str,
    content_id: str,
    skip: int = 0,
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """Get comments for content"""
    try:
        # Get top-level comments
        comments = await db.comments.find(
            {
                "content_type": content_type,
                "content_id": content_id,
                "parent_id": None,
                "is_deleted": False
            },
            {"_id": 0}
        ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)

        # Enrich with author info and replies
        for comment in comments:
            author = await db.users.find_one(
                {"id": comment["author_id"]},
                {"_id": 0, "username": 1, "avatar_url": 1}
            )
            if author:
                comment["author_username"] = author.get("username")
                comment["author_avatar"] = author.get("avatar_url")

            # Check if current user liked
            liked = await db.comment_likes.find_one({
                "comment_id": comment["id"],
                "user_id": current_user["id"]
            })
            comment["liked_by_me"] = liked is not None

            # Get first few replies
            replies = await db.comments.find(
                {"parent_id": comment["id"], "is_deleted": False},
                {"_id": 0}
            ).sort("created_at", 1).limit(3).to_list(3)

            for reply in replies:
                reply_author = await db.users.find_one(
                    {"id": reply["author_id"]},
                    {"_id": 0, "username": 1, "avatar_url": 1}
                )
                if reply_author:
                    reply["author_username"] = reply_author.get("username")
                    reply["author_avatar"] = reply_author.get("avatar_url")

            comment["replies"] = replies

        total = await db.comments.count_documents({
            "content_type": content_type,
            "content_id": content_id,
            "parent_id": None,
            "is_deleted": False
        })

        return {"comments": comments, "total": total}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/comments/{comment_id}/like")
async def like_comment(
    comment_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Like/unlike a comment"""
    try:
        existing = await db.comment_likes.find_one({
            "comment_id": comment_id,
            "user_id": current_user["id"]
        })

        if existing:
            # Unlike
            await db.comment_likes.delete_one({"id": existing["id"]})
            await db.comments.update_one(
                {"id": comment_id},
                {"$inc": {"likes_count": -1}}
            )
            return {"message": "Unliked", "liked": False}
        else:
            # Like
            await db.comment_likes.insert_one({
                "id": str(uuid.uuid4()),
                "comment_id": comment_id,
                "user_id": current_user["id"],
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            await db.comments.update_one(
                {"id": comment_id},
                {"$inc": {"likes_count": 1}}
            )
            return {"message": "Liked", "liked": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/comments/{comment_id}")
async def delete_comment(
    comment_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a comment (soft delete)"""
    try:
        comment = await db.comments.find_one({"id": comment_id})
        
        if not comment:
            raise HTTPException(status_code=404, detail="Comment not found")

        if comment["author_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Not your comment")

        await db.comments.update_one(
            {"id": comment_id},
            {"$set": {
                "is_deleted": True,
                "content": "[deleted]",
                "deleted_at": datetime.now(timezone.utc).isoformat()
            }}
        )

        return {"message": "Comment deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ===================== REACTIONS =====================

@router.post("/reactions/{content_type}/{content_id}")
async def add_reaction(
    content_type: str,
    content_id: str,
    reaction: ReactionCreate,
    current_user: dict = Depends(get_current_user)
):
    """Add a reaction to content"""
    try:
        valid_reactions = ["like", "love", "celebrate", "insightful", "curious"]
        if reaction.reaction_type not in valid_reactions:
            raise HTTPException(status_code=400, detail=f"Invalid reaction. Use: {valid_reactions}")

        # Check for existing reaction
        existing = await db.reactions.find_one({
            "content_type": content_type,
            "content_id": content_id,
            "user_id": current_user["id"]
        })

        now = datetime.now(timezone.utc).isoformat()

        if existing:
            if existing["reaction_type"] == reaction.reaction_type:
                # Remove reaction
                await db.reactions.delete_one({"id": existing["id"]})
                return {"message": "Reaction removed", "action": "removed"}
            else:
                # Change reaction
                await db.reactions.update_one(
                    {"id": existing["id"]},
                    {"$set": {"reaction_type": reaction.reaction_type, "updated_at": now}}
                )
                return {"message": "Reaction changed", "action": "changed", "type": reaction.reaction_type}
        else:
            # Add new reaction
            await db.reactions.insert_one({
                "id": str(uuid.uuid4()),
                "content_type": content_type,
                "content_id": content_id,
                "user_id": current_user["id"],
                "reaction_type": reaction.reaction_type,
                "created_at": now
            })
            return {"message": "Reaction added", "action": "added", "type": reaction.reaction_type}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/reactions/{content_type}/{content_id}")
async def get_reactions(
    content_type: str,
    content_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get reactions for content"""
    try:
        # Aggregate reactions by type
        pipeline = [
            {"$match": {"content_type": content_type, "content_id": content_id}},
            {"$group": {"_id": "$reaction_type", "count": {"$sum": 1}}}
        ]
        result = await db.reactions.aggregate(pipeline).to_list(10)
        
        reactions = {item["_id"]: item["count"] for item in result}
        total = sum(reactions.values())

        # Check user's reaction
        user_reaction = await db.reactions.find_one({
            "content_type": content_type,
            "content_id": content_id,
            "user_id": current_user["id"]
        })

        return {
            "reactions": reactions,
            "total": total,
            "my_reaction": user_reaction["reaction_type"] if user_reaction else None
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ===================== ACTIVITY FEED =====================

@router.get("/feed")
async def get_activity_feed(
    skip: int = 0,
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """Get personalized activity feed"""
    try:
        user_id = current_user["id"]

        # Get users being followed
        follows = await db.follows.find(
            {"follower_id": user_id},
            {"following_id": 1}
        ).to_list(100)
        following_ids = [f["following_id"] for f in follows]
        following_ids.append(user_id)  # Include own activity

        # Get recent activities from followed users
        activities = await db.activities.find(
            {"user_id": {"$in": following_ids}},
            {"_id": 0}
        ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)

        # Enrich with user info
        for activity in activities:
            user = await db.users.find_one(
                {"id": activity["user_id"]},
                {"_id": 0, "username": 1, "avatar_url": 1}
            )
            if user:
                activity["username"] = user.get("username")
                activity["avatar_url"] = user.get("avatar_url")

        return {"feed": activities}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/feed/global")
async def get_global_feed(
    skip: int = 0,
    limit: int = 20
):
    """Get global activity feed (public)"""
    try:
        activities = await db.activities.find(
            {"is_public": True},
            {"_id": 0}
        ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)

        for activity in activities:
            user = await db.users.find_one(
                {"id": activity["user_id"]},
                {"_id": 0, "username": 1, "avatar_url": 1}
            )
            if user:
                activity["username"] = user.get("username")
                activity["avatar_url"] = user.get("avatar_url")

        return {"feed": activities}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ===================== STATS =====================

@router.get("/stats/{user_id}")
async def get_social_stats(user_id: str):
    """Get social statistics for a user"""
    try:
        user = await db.users.find_one(
            {"id": user_id},
            {"_id": 0, "followers_count": 1, "following_count": 1}
        )

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        comments_count = await db.comments.count_documents({"author_id": user_id})
        reactions_received = await db.reactions.count_documents({"content_id": user_id})

        return {
            "stats": {
                "followers": user.get("followers_count", 0),
                "following": user.get("following_count", 0),
                "comments": comments_count,
                "reactions_received": reactions_received
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/reaction-types")
async def get_reaction_types():
    """Get available reaction types"""
    return {
        "reactions": [
            {"type": "like", "emoji": "👍", "name": "Like"},
            {"type": "love", "emoji": "❤️", "name": "Love"},
            {"type": "celebrate", "emoji": "🎉", "name": "Celebrate"},
            {"type": "insightful", "emoji": "💡", "name": "Insightful"},
            {"type": "curious", "emoji": "🤔", "name": "Curious"}
        ]
    }
