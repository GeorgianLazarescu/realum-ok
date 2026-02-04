from fastapi import APIRouter, HTTPException, Depends, Query
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict
from pydantic import BaseModel
import uuid

from core.database import db
from core.auth import get_current_user, require_admin
from services.notification_service import send_notification

router = APIRouter(prefix="/api/chat", tags=["Chat"])

# ===================== MODELS =====================

class ChannelCreate(BaseModel):
    name: str
    description: Optional[str] = None
    channel_type: str = "group"  # direct, group, dao, project
    is_private: bool = True
    member_ids: List[str] = []
    dao_id: Optional[str] = None
    project_id: Optional[str] = None

class MessageCreate(BaseModel):
    content: str
    message_type: str = "text"  # text, image, file, code, poll
    reply_to_id: Optional[str] = None
    attachments: List[Dict] = []
    mentions: List[str] = []

class MessageUpdate(BaseModel):
    content: str

class ReactionAdd(BaseModel):
    emoji: str

class PollCreate(BaseModel):
    question: str
    options: List[str]
    expires_in_hours: int = 24
    allow_multiple: bool = False

# ===================== CHANNELS =====================

@router.post("/channels")
async def create_channel(
    channel: ChannelCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new chat channel"""
    try:
        channel_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        # For direct messages, check if channel exists
        if channel.channel_type == "direct" and len(channel.member_ids) == 1:
            other_user_id = channel.member_ids[0]
            existing = await db.chat_channels.find_one({
                "channel_type": "direct",
                "$or": [
                    {"participants": [current_user["id"], other_user_id]},
                    {"participants": [other_user_id, current_user["id"]]}
                ]
            })
            if existing:
                return {"channel_id": existing["id"], "existing": True}

        channel_data = {
            "id": channel_id,
            "name": channel.name,
            "description": channel.description,
            "channel_type": channel.channel_type,
            "created_by": current_user["id"],
            "dao_id": channel.dao_id,
            "project_id": channel.project_id,
            "is_private": channel.is_private,
            "is_archived": False,
            "participants": [current_user["id"]] + channel.member_ids,
            "message_count": 0,
            "last_message_at": now,
            "last_message_preview": None,
            "settings": {
                "allow_reactions": True,
                "allow_threads": True,
                "allow_files": True,
                "slow_mode_seconds": 0
            },
            "created_at": now,
            "updated_at": now
        }

        await db.chat_channels.insert_one(channel_data)

        # Add creator as owner
        await db.chat_members.insert_one({
            "id": str(uuid.uuid4()),
            "channel_id": channel_id,
            "user_id": current_user["id"],
            "role": "owner",
            "notifications_enabled": True,
            "joined_at": now,
            "last_seen_at": now
        })

        # Add other members
        for member_id in channel.member_ids:
            if member_id != current_user["id"]:
                await db.chat_members.insert_one({
                    "id": str(uuid.uuid4()),
                    "channel_id": channel_id,
                    "user_id": member_id,
                    "role": "member",
                    "notifications_enabled": True,
                    "joined_at": now,
                    "last_seen_at": now
                })

                await send_notification(
                    user_id=member_id,
                    title="New Chat Invitation",
                    message=f"{current_user['username']} added you to {channel.name}",
                    category="social",
                    action_url=f"/chat/{channel_id}"
                )

        return {
            "message": "Channel created successfully",
            "channel_id": channel_id
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/channels")
async def get_user_channels(
    channel_type: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get all channels user is a member of"""
    try:
        user_id = current_user["id"]

        # Get memberships
        memberships = await db.chat_members.find(
            {"user_id": user_id},
            {"_id": 0}
        ).to_list(100)

        channel_ids = [m["channel_id"] for m in memberships]

        # Get channels
        query = {"id": {"$in": channel_ids}, "is_archived": False}
        if channel_type:
            query["channel_type"] = channel_type

        channels = await db.chat_channels.find(
            query,
            {"_id": 0}
        ).sort("last_message_at", -1).to_list(100)

        # Enrich with unread counts and member info
        for channel in channels:
            membership = next((m for m in memberships if m["channel_id"] == channel["id"]), None)
            
            if membership:
                last_seen = membership.get("last_seen_at", channel["created_at"])
                unread = await db.chat_messages.count_documents({
                    "channel_id": channel["id"],
                    "created_at": {"$gt": last_seen}
                })
                channel["unread_count"] = unread

            # For direct messages, get other user info
            if channel["channel_type"] == "direct":
                participants = channel.get("participants", [])
                other_id = next((p for p in participants if p != user_id), None)
                if other_id:
                    other_user = await db.users.find_one(
                        {"id": other_id},
                        {"_id": 0, "username": 1, "avatar_url": 1}
                    )
                    if other_user:
                        channel["other_user"] = other_user

        return {"channels": channels}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/channels/{channel_id}")
async def get_channel_details(
    channel_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get channel details with members"""
    try:
        # Verify membership
        membership = await db.chat_members.find_one({
            "channel_id": channel_id,
            "user_id": current_user["id"]
        })

        if not membership:
            raise HTTPException(status_code=403, detail="Not a member of this channel")

        channel = await db.chat_channels.find_one({"id": channel_id}, {"_id": 0})
        if not channel:
            raise HTTPException(status_code=404, detail="Channel not found")

        # Get members
        members = await db.chat_members.find(
            {"channel_id": channel_id},
            {"_id": 0}
        ).to_list(100)

        # Enrich with user info
        for member in members:
            user = await db.users.find_one(
                {"id": member["user_id"]},
                {"_id": 0, "username": 1, "avatar_url": 1}
            )
            if user:
                member["username"] = user.get("username")
                member["avatar_url"] = user.get("avatar_url")

        # Get pinned messages
        pinned = await db.chat_messages.find(
            {"channel_id": channel_id, "is_pinned": True},
            {"_id": 0}
        ).to_list(10)

        return {
            "channel": channel,
            "members": members,
            "pinned_messages": pinned,
            "your_role": membership.get("role")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/channels/{channel_id}/leave")
async def leave_channel(
    channel_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Leave a channel"""
    try:
        result = await db.chat_members.delete_one({
            "channel_id": channel_id,
            "user_id": current_user["id"]
        })

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Not a member of this channel")

        # Update participant list
        await db.chat_channels.update_one(
            {"id": channel_id},
            {"$pull": {"participants": current_user["id"]}}
        )

        return {"message": "Left channel successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ===================== MESSAGES =====================

@router.post("/channels/{channel_id}/messages")
async def send_message(
    channel_id: str,
    message: MessageCreate,
    current_user: dict = Depends(get_current_user)
):
    """Send a message to a channel"""
    try:
        # Verify membership
        membership = await db.chat_members.find_one({
            "channel_id": channel_id,
            "user_id": current_user["id"]
        })

        if not membership:
            raise HTTPException(status_code=403, detail="Not a member of this channel")

        # Check slow mode
        channel = await db.chat_channels.find_one({"id": channel_id})
        slow_mode = channel.get("settings", {}).get("slow_mode_seconds", 0)
        
        if slow_mode > 0:
            last_message = await db.chat_messages.find_one(
                {"channel_id": channel_id, "sender_id": current_user["id"]},
                sort=[("created_at", -1)]
            )
            if last_message:
                last_time = datetime.fromisoformat(last_message["created_at"].replace('Z', '+00:00'))
                if (datetime.now(timezone.utc) - last_time).seconds < slow_mode:
                    raise HTTPException(
                        status_code=429,
                        detail=f"Slow mode active. Wait {slow_mode} seconds between messages."
                    )

        message_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        message_data = {
            "id": message_id,
            "channel_id": channel_id,
            "sender_id": current_user["id"],
            "content": message.content,
            "message_type": message.message_type,
            "reply_to_id": message.reply_to_id,
            "attachments": message.attachments,
            "mentions": message.mentions,
            "reactions": {},
            "is_edited": False,
            "is_pinned": False,
            "is_deleted": False,
            "thread_count": 0,
            "created_at": now,
            "updated_at": now
        }

        await db.chat_messages.insert_one(message_data)

        # Update channel
        preview = message.content[:50] + "..." if len(message.content) > 50 else message.content
        await db.chat_channels.update_one(
            {"id": channel_id},
            {
                "$set": {
                    "last_message_at": now,
                    "last_message_preview": preview
                },
                "$inc": {"message_count": 1}
            }
        )

        # Notify mentioned users
        for mentioned_id in message.mentions:
            if mentioned_id != current_user["id"]:
                await send_notification(
                    user_id=mentioned_id,
                    title="You were mentioned",
                    message=f"{current_user['username']} mentioned you in {channel.get('name', 'a chat')}",
                    category="social",
                    action_url=f"/chat/{channel_id}#message-{message_id}"
                )

        # Return message with sender info
        message_data["sender_username"] = current_user.get("username")
        message_data["sender_avatar"] = current_user.get("avatar_url")

        return message_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/channels/{channel_id}/messages")
async def get_messages(
    channel_id: str,
    before: Optional[str] = None,
    limit: int = Query(50, le=100),
    current_user: dict = Depends(get_current_user)
):
    """Get messages from a channel"""
    try:
        # Verify membership
        membership = await db.chat_members.find_one({
            "channel_id": channel_id,
            "user_id": current_user["id"]
        })

        if not membership:
            raise HTTPException(status_code=403, detail="Not a member of this channel")

        query = {"channel_id": channel_id, "is_deleted": False}
        if before:
            query["created_at"] = {"$lt": before}

        messages = await db.chat_messages.find(
            query,
            {"_id": 0}
        ).sort("created_at", -1).limit(limit).to_list(limit)

        # Reverse to get chronological order
        messages.reverse()

        # Enrich with sender info
        for msg in messages:
            sender = await db.users.find_one(
                {"id": msg["sender_id"]},
                {"_id": 0, "username": 1, "avatar_url": 1}
            )
            if sender:
                msg["sender_username"] = sender.get("username")
                msg["sender_avatar"] = sender.get("avatar_url")

            # Get reply info if exists
            if msg.get("reply_to_id"):
                reply_msg = await db.chat_messages.find_one(
                    {"id": msg["reply_to_id"]},
                    {"_id": 0, "content": 1, "sender_id": 1}
                )
                if reply_msg:
                    reply_sender = await db.users.find_one(
                        {"id": reply_msg["sender_id"]},
                        {"_id": 0, "username": 1}
                    )
                    msg["reply_preview"] = {
                        "content": reply_msg["content"][:100],
                        "username": reply_sender.get("username") if reply_sender else "Unknown"
                    }

        # Update last seen
        await db.chat_members.update_one(
            {"channel_id": channel_id, "user_id": current_user["id"]},
            {"$set": {"last_seen_at": datetime.now(timezone.utc).isoformat()}}
        )

        return {"messages": messages, "has_more": len(messages) == limit}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/channels/{channel_id}/messages/{message_id}")
async def edit_message(
    channel_id: str,
    message_id: str,
    update: MessageUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Edit a message"""
    try:
        message = await db.chat_messages.find_one({
            "id": message_id,
            "channel_id": channel_id,
            "sender_id": current_user["id"]
        })

        if not message:
            raise HTTPException(status_code=404, detail="Message not found or not yours")

        now = datetime.now(timezone.utc).isoformat()

        await db.chat_messages.update_one(
            {"id": message_id},
            {"$set": {
                "content": update.content,
                "is_edited": True,
                "edited_at": now,
                "updated_at": now
            }}
        )

        return {"message": "Message edited"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/channels/{channel_id}/messages/{message_id}")
async def delete_message(
    channel_id: str,
    message_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a message (soft delete)"""
    try:
        message = await db.chat_messages.find_one({
            "id": message_id,
            "channel_id": channel_id
        })

        if not message:
            raise HTTPException(status_code=404, detail="Message not found")

        # Check permission (sender or channel admin)
        is_sender = message["sender_id"] == current_user["id"]
        membership = await db.chat_members.find_one({
            "channel_id": channel_id,
            "user_id": current_user["id"]
        })
        is_admin = membership and membership.get("role") in ["owner", "admin"]

        if not (is_sender or is_admin):
            raise HTTPException(status_code=403, detail="Cannot delete this message")

        await db.chat_messages.update_one(
            {"id": message_id},
            {"$set": {
                "is_deleted": True,
                "deleted_at": datetime.now(timezone.utc).isoformat(),
                "deleted_by": current_user["id"]
            }}
        )

        return {"message": "Message deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ===================== REACTIONS =====================

@router.post("/channels/{channel_id}/messages/{message_id}/reactions")
async def add_reaction(
    channel_id: str,
    message_id: str,
    reaction: ReactionAdd,
    current_user: dict = Depends(get_current_user)
):
    """Add a reaction to a message"""
    try:
        message = await db.chat_messages.find_one({"id": message_id})
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")

        user_id = current_user["id"]
        emoji = reaction.emoji

        # Get current reactions
        reactions = message.get("reactions", {})
        
        if emoji not in reactions:
            reactions[emoji] = []
        
        if user_id in reactions[emoji]:
            # Remove reaction
            reactions[emoji].remove(user_id)
            if not reactions[emoji]:
                del reactions[emoji]
            action = "removed"
        else:
            # Add reaction
            reactions[emoji].append(user_id)
            action = "added"

        await db.chat_messages.update_one(
            {"id": message_id},
            {"$set": {"reactions": reactions}}
        )

        return {"message": f"Reaction {action}", "action": action}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ===================== THREADS =====================

@router.post("/channels/{channel_id}/messages/{message_id}/thread")
async def reply_in_thread(
    channel_id: str,
    message_id: str,
    message: MessageCreate,
    current_user: dict = Depends(get_current_user)
):
    """Reply to a message in a thread"""
    try:
        parent = await db.chat_messages.find_one({"id": message_id})
        if not parent:
            raise HTTPException(status_code=404, detail="Parent message not found")

        thread_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        await db.chat_threads.insert_one({
            "id": thread_id,
            "channel_id": channel_id,
            "parent_message_id": message_id,
            "sender_id": current_user["id"],
            "content": message.content,
            "message_type": message.message_type,
            "attachments": message.attachments,
            "is_deleted": False,
            "created_at": now
        })

        # Update parent thread count
        await db.chat_messages.update_one(
            {"id": message_id},
            {"$inc": {"thread_count": 1}}
        )

        return {"message": "Thread reply added", "thread_id": thread_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/channels/{channel_id}/messages/{message_id}/thread")
async def get_thread(
    channel_id: str,
    message_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get thread replies for a message"""
    try:
        threads = await db.chat_threads.find(
            {"parent_message_id": message_id, "is_deleted": False},
            {"_id": 0}
        ).sort("created_at", 1).to_list(100)

        # Enrich with sender info
        for thread in threads:
            sender = await db.users.find_one(
                {"id": thread["sender_id"]},
                {"_id": 0, "username": 1, "avatar_url": 1}
            )
            if sender:
                thread["sender_username"] = sender.get("username")
                thread["sender_avatar"] = sender.get("avatar_url")

        return {"threads": threads}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ===================== POLLS =====================

@router.post("/channels/{channel_id}/polls")
async def create_poll(
    channel_id: str,
    poll: PollCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a poll in a channel"""
    try:
        poll_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=poll.expires_in_hours)

        # Create poll
        await db.chat_polls.insert_one({
            "id": poll_id,
            "channel_id": channel_id,
            "creator_id": current_user["id"],
            "question": poll.question,
            "options": [{"text": opt, "votes": []} for opt in poll.options],
            "allow_multiple": poll.allow_multiple,
            "is_closed": False,
            "expires_at": expires_at.isoformat(),
            "created_at": now.isoformat()
        })

        # Create message for poll
        message_id = str(uuid.uuid4())
        await db.chat_messages.insert_one({
            "id": message_id,
            "channel_id": channel_id,
            "sender_id": current_user["id"],
            "content": f"📊 Poll: {poll.question}",
            "message_type": "poll",
            "poll_id": poll_id,
            "reactions": {},
            "is_edited": False,
            "is_pinned": False,
            "is_deleted": False,
            "created_at": now.isoformat()
        })

        return {"message": "Poll created", "poll_id": poll_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/polls/{poll_id}/vote")
async def vote_on_poll(
    poll_id: str,
    option_index: int,
    current_user: dict = Depends(get_current_user)
):
    """Vote on a poll"""
    try:
        poll = await db.chat_polls.find_one({"id": poll_id})
        if not poll:
            raise HTTPException(status_code=404, detail="Poll not found")

        if poll.get("is_closed"):
            raise HTTPException(status_code=400, detail="Poll is closed")

        expires_at = datetime.fromisoformat(poll["expires_at"].replace('Z', '+00:00'))
        if datetime.now(timezone.utc) > expires_at:
            raise HTTPException(status_code=400, detail="Poll has expired")

        options = poll.get("options", [])
        if option_index >= len(options):
            raise HTTPException(status_code=400, detail="Invalid option")

        user_id = current_user["id"]

        # Check if already voted
        if not poll.get("allow_multiple"):
            for opt in options:
                if user_id in opt.get("votes", []):
                    raise HTTPException(status_code=400, detail="Already voted")

        # Add vote
        options[option_index]["votes"].append(user_id)

        await db.chat_polls.update_one(
            {"id": poll_id},
            {"$set": {"options": options}}
        )

        return {"message": "Vote recorded"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/polls/{poll_id}")
async def get_poll_results(
    poll_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get poll results"""
    try:
        poll = await db.chat_polls.find_one({"id": poll_id}, {"_id": 0})
        if not poll:
            raise HTTPException(status_code=404, detail="Poll not found")

        # Calculate results
        total_votes = sum(len(opt.get("votes", [])) for opt in poll.get("options", []))
        
        results = []
        for opt in poll.get("options", []):
            votes = len(opt.get("votes", []))
            percentage = (votes / total_votes * 100) if total_votes > 0 else 0
            results.append({
                "text": opt["text"],
                "votes": votes,
                "percentage": round(percentage, 1),
                "voted_by_me": current_user["id"] in opt.get("votes", [])
            })

        return {
            "poll": {
                "id": poll["id"],
                "question": poll["question"],
                "is_closed": poll.get("is_closed", False),
                "expires_at": poll.get("expires_at"),
                "total_votes": total_votes
            },
            "results": results
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ===================== DIRECT MESSAGES =====================

@router.post("/direct/{user_id}")
async def start_direct_message(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Start or get direct message channel with a user"""
    try:
        if user_id == current_user["id"]:
            raise HTTPException(status_code=400, detail="Cannot DM yourself")

        # Check if user exists
        other_user = await db.users.find_one({"id": user_id})
        if not other_user:
            raise HTTPException(status_code=404, detail="User not found")

        # Check for existing DM channel
        existing = await db.chat_channels.find_one({
            "channel_type": "direct",
            "participants": {"$all": [current_user["id"], user_id]}
        })

        if existing:
            return {"channel_id": existing["id"], "existing": True}

        # Create new DM channel
        channel_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        await db.chat_channels.insert_one({
            "id": channel_id,
            "name": f"DM: {current_user['username']} & {other_user['username']}",
            "channel_type": "direct",
            "participants": [current_user["id"], user_id],
            "is_private": True,
            "message_count": 0,
            "created_at": now,
            "last_message_at": now
        })

        # Add both users as members
        for uid in [current_user["id"], user_id]:
            await db.chat_members.insert_one({
                "id": str(uuid.uuid4()),
                "channel_id": channel_id,
                "user_id": uid,
                "role": "member",
                "notifications_enabled": True,
                "joined_at": now,
                "last_seen_at": now
            })

        return {"channel_id": channel_id, "existing": False}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ===================== SEARCH =====================

@router.get("/search")
async def search_messages(
    query: str = Query(..., min_length=2),
    channel_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Search messages across channels"""
    try:
        user_id = current_user["id"]

        # Get user's channels
        memberships = await db.chat_members.find(
            {"user_id": user_id},
            {"channel_id": 1}
        ).to_list(100)
        
        user_channel_ids = [m["channel_id"] for m in memberships]

        # Build search query
        search_query = {
            "channel_id": {"$in": user_channel_ids} if not channel_id else channel_id,
            "is_deleted": False,
            "content": {"$regex": query, "$options": "i"}
        }

        if channel_id and channel_id not in user_channel_ids:
            raise HTTPException(status_code=403, detail="Not a member of this channel")

        messages = await db.chat_messages.find(
            search_query,
            {"_id": 0}
        ).sort("created_at", -1).limit(50).to_list(50)

        # Enrich with sender and channel info
        for msg in messages:
            sender = await db.users.find_one(
                {"id": msg["sender_id"]},
                {"_id": 0, "username": 1}
            )
            if sender:
                msg["sender_username"] = sender.get("username")

            channel = await db.chat_channels.find_one(
                {"id": msg["channel_id"]},
                {"_id": 0, "name": 1}
            )
            if channel:
                msg["channel_name"] = channel.get("name")

        return {"results": messages, "count": len(messages)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
