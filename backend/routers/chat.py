from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel
import uuid

from core.database import db
from core.auth import get_current_user
from services.notification_service import send_notification

router = APIRouter(prefix="/chat", tags=["Chat"])

class ChannelCreate(BaseModel):
    name: str
    description: Optional[str] = None
    type: str = "group"
    is_private: bool = True
    member_ids: List[str] = []
    dao_id: Optional[str] = None

class MessageCreate(BaseModel):
    content: str
    message_type: str = "text"
    reply_to_id: Optional[str] = None
    attachments: List[dict] = []

class MessageUpdate(BaseModel):
    content: str

@router.post("/channels")
async def create_channel(
    channel: ChannelCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new chat channel"""
    channel_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    # Create channel
    await db.chat_channels.insert_one({
        "id": channel_id,
        "name": channel.name,
        "description": channel.description,
        "type": channel.type,
        "created_by": current_user["id"],
        "dao_id": channel.dao_id,
        "is_private": channel.is_private,
        "is_archived": False,
        "last_message_at": now,
        "created_at": now,
        "updated_at": now
    })

    # Add creator as owner
    await db.chat_members.insert_one({
        "id": str(uuid.uuid4()),
        "channel_id": channel_id,
        "user_id": current_user["id"],
        "role": "owner",
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
                "joined_at": now,
                "last_seen_at": now
            })

            # Send notification
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

@router.get("/channels")
async def get_user_channels(
    current_user: dict = Depends(get_current_user)
):
    """Get all channels user is a member of"""
    user_id = current_user["id"]

    # Get memberships
    memberships = await db.chat_members.find(
        {"user_id": user_id},
        {"_id": 0}
    ).to_list(100)

    channel_ids = [m["channel_id"] for m in memberships]

    # Get channels
    channels = await db.chat_channels.find(
        {"id": {"$in": channel_ids}, "is_archived": False},
        {"_id": 0}
    ).sort("last_message_at", -1).to_list(100)

    # Enrich with member info
    for channel in channels:
        # Get member count
        member_count = await db.chat_members.count_documents({"channel_id": channel["id"]})
        channel["member_count"] = member_count

        # Get unread count
        user_membership = next((m for m in memberships if m["channel_id"] == channel["id"]), None)
        if user_membership:
            last_read_id = user_membership.get("last_read_message_id")
            if last_read_id:
                unread_count = await db.chat_messages.count_documents({
                    "channel_id": channel["id"],
                    "id": {"$gt": last_read_id},
                    "sender_id": {"$ne": user_id}
                })
            else:
                unread_count = await db.chat_messages.count_documents({
                    "channel_id": channel["id"],
                    "sender_id": {"$ne": user_id}
                })
            channel["unread_count"] = unread_count

    return {"channels": channels}

@router.get("/channels/{channel_id}")
async def get_channel(
    channel_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get channel details"""
    # Check membership
    member = await db.chat_members.find_one({
        "channel_id": channel_id,
        "user_id": current_user["id"]
    })

    if not member:
        raise HTTPException(status_code=403, detail="Not a member of this channel")

    # Get channel
    channel = await db.chat_channels.find_one({"id": channel_id}, {"_id": 0})

    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    # Get members
    members = await db.chat_members.find(
        {"channel_id": channel_id},
        {"_id": 0}
    ).to_list(100)

    # Enrich members with user info
    for member_data in members:
        user = await db.users.find_one(
            {"id": member_data["user_id"]},
            {"_id": 0, "username": 1, "avatar_url": 1}
        )
        if user:
            member_data["username"] = user.get("username")
            member_data["avatar_url"] = user.get("avatar_url")

    channel["members"] = members

    return channel

@router.post("/channels/{channel_id}/messages")
async def send_message(
    channel_id: str,
    message: MessageCreate,
    current_user: dict = Depends(get_current_user)
):
    """Send a message to a channel"""
    user_id = current_user["id"]

    # Check membership
    member = await db.chat_members.find_one({
        "channel_id": channel_id,
        "user_id": user_id
    })

    if not member:
        raise HTTPException(status_code=403, detail="Not a member of this channel")

    message_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    # Create message
    await db.chat_messages.insert_one({
        "id": message_id,
        "channel_id": channel_id,
        "sender_id": user_id,
        "content": message.content,
        "message_type": message.message_type,
        "reply_to_id": message.reply_to_id,
        "attachments": message.attachments,
        "is_edited": False,
        "is_deleted": False,
        "created_at": now
    })

    # Update channel last message time
    await db.chat_channels.update_one(
        {"id": channel_id},
        {"$set": {"last_message_at": now}}
    )

    # Notify other members
    other_members = await db.chat_members.find(
        {"channel_id": channel_id, "user_id": {"$ne": user_id}},
        {"_id": 0, "user_id": 1}
    ).to_list(100)

    channel = await db.chat_channels.find_one({"id": channel_id}, {"_id": 0, "name": 1})

    for member_data in other_members:
        await send_notification(
            user_id=member_data["user_id"],
            title=f"New message in {channel.get('name', 'Chat')}",
            message=f"{current_user['username']}: {message.content[:50]}...",
            category="social",
            action_url=f"/chat/{channel_id}"
        )

    return {
        "message": "Message sent successfully",
        "message_id": message_id
    }

@router.get("/channels/{channel_id}/messages")
async def get_messages(
    channel_id: str,
    skip: int = 0,
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """Get messages from a channel"""
    # Check membership
    member = await db.chat_members.find_one({
        "channel_id": channel_id,
        "user_id": current_user["id"]
    })

    if not member:
        raise HTTPException(status_code=403, detail="Not a member of this channel")

    # Get messages
    messages = await db.chat_messages.find(
        {"channel_id": channel_id, "is_deleted": False},
        {"_id": 0}
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)

    # Reverse to chronological order
    messages.reverse()

    # Enrich with sender info and reactions
    for msg in messages:
        sender = await db.users.find_one(
            {"id": msg["sender_id"]},
            {"_id": 0, "username": 1, "avatar_url": 1}
        )
        if sender:
            msg["sender_username"] = sender.get("username")
            msg["sender_avatar"] = sender.get("avatar_url")

        # Get reactions
        reactions = await db.chat_reactions.find(
            {"message_id": msg["id"]},
            {"_id": 0}
        ).to_list(100)

        # Group reactions by emoji
        reaction_counts = {}
        for reaction in reactions:
            emoji = reaction["emoji"]
            if emoji not in reaction_counts:
                reaction_counts[emoji] = {"count": 0, "users": []}
            reaction_counts[emoji]["count"] += 1
            reaction_counts[emoji]["users"].append(reaction["user_id"])

        msg["reactions"] = reaction_counts

    # Update last read
    if messages:
        last_message_id = messages[-1]["id"]
        await db.chat_members.update_one(
            {"channel_id": channel_id, "user_id": current_user["id"]},
            {"$set": {"last_read_message_id": last_message_id}}
        )

    return {"messages": messages}

@router.patch("/messages/{message_id}")
async def edit_message(
    message_id: str,
    update: MessageUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Edit a message"""
    # Check ownership
    message = await db.chat_messages.find_one({"id": message_id})

    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    if message["sender_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your message")

    # Update message
    await db.chat_messages.update_one(
        {"id": message_id},
        {
            "$set": {
                "content": update.content,
                "is_edited": True,
                "edited_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )

    return {"message": "Message updated successfully"}

@router.delete("/messages/{message_id}")
async def delete_message(
    message_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a message"""
    # Check ownership
    message = await db.chat_messages.find_one({"id": message_id})

    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    if message["sender_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your message")

    # Soft delete
    await db.chat_messages.update_one(
        {"id": message_id},
        {
            "$set": {
                "is_deleted": True,
                "deleted_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )

    return {"message": "Message deleted successfully"}

@router.post("/messages/{message_id}/reactions")
async def add_reaction(
    message_id: str,
    emoji: str,
    current_user: dict = Depends(get_current_user)
):
    """Add a reaction to a message"""
    # Check if message exists and user has access
    message = await db.chat_messages.find_one({"id": message_id})

    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    # Check membership
    member = await db.chat_members.find_one({
        "channel_id": message["channel_id"],
        "user_id": current_user["id"]
    })

    if not member:
        raise HTTPException(status_code=403, detail="Not a member of this channel")

    # Add reaction (or ignore if exists)
    try:
        await db.chat_reactions.insert_one({
            "id": str(uuid.uuid4()),
            "message_id": message_id,
            "user_id": current_user["id"],
            "emoji": emoji,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    except:
        # Reaction already exists
        pass

    return {"message": "Reaction added"}

@router.delete("/messages/{message_id}/reactions/{emoji}")
async def remove_reaction(
    message_id: str,
    emoji: str,
    current_user: dict = Depends(get_current_user)
):
    """Remove a reaction from a message"""
    result = await db.chat_reactions.delete_one({
        "message_id": message_id,
        "user_id": current_user["id"],
        "emoji": emoji
    })

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Reaction not found")

    return {"message": "Reaction removed"}

@router.post("/channels/{channel_id}/members")
async def add_channel_member(
    channel_id: str,
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Add a member to a channel"""
    # Check if requester is admin/owner
    requester = await db.chat_members.find_one({
        "channel_id": channel_id,
        "user_id": current_user["id"]
    })

    if not requester or requester["role"] not in ["owner", "admin"]:
        raise HTTPException(status_code=403, detail="Only admins can add members")

    # Add member
    try:
        await db.chat_members.insert_one({
            "id": str(uuid.uuid4()),
            "channel_id": channel_id,
            "user_id": user_id,
            "role": "member",
            "joined_at": datetime.now(timezone.utc).isoformat(),
            "last_seen_at": datetime.now(timezone.utc).isoformat()
        })
    except:
        raise HTTPException(status_code=400, detail="User already a member")

    channel = await db.chat_channels.find_one({"id": channel_id}, {"_id": 0, "name": 1})

    # Notify new member
    await send_notification(
        user_id=user_id,
        title="Added to Chat",
        message=f"{current_user['username']} added you to {channel.get('name', 'a channel')}",
        category="social",
        action_url=f"/chat/{channel_id}"
    )

    return {"message": "Member added successfully"}

@router.patch("/channels/{channel_id}/typing")
async def update_typing_status(
    channel_id: str,
    is_typing: bool,
    current_user: dict = Depends(get_current_user)
):
    """Update typing indicator"""
    await db.chat_members.update_one(
        {"channel_id": channel_id, "user_id": current_user["id"]},
        {"$set": {"is_typing": is_typing}}
    )

    return {"message": "Status updated"}

@router.get("/channels/{channel_id}/typing")
async def get_typing_users(
    channel_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get users currently typing"""
    typing_users = await db.chat_members.find(
        {
            "channel_id": channel_id,
            "is_typing": True,
            "user_id": {"$ne": current_user["id"]}
        },
        {"_id": 0, "user_id": 1}
    ).to_list(10)

    # Get usernames
    user_ids = [u["user_id"] for u in typing_users]
    users = await db.users.find(
        {"id": {"$in": user_ids}},
        {"_id": 0, "id": 1, "username": 1}
    ).to_list(10)

    return {"typing_users": users}
