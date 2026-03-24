"""
REALUM Guild/Alliance System
Player groups with shared benefits and activities
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import uuid

router = APIRouter(prefix="/api/guilds", tags=["Guilds & Alliances"])

from core.database import db
from core.auth import get_current_user
from core.utils import serialize_doc


# ============== CONSTANTS ==============

# Guild creation cost
GUILD_CREATION_COST = 3000

# Guild ranks
GUILD_RANKS = {
    "leader": {"name": "Lider", "permissions": ["all"]},
    "officer": {"name": "Ofițer", "permissions": ["invite", "kick", "announce", "bank_withdraw"]},
    "veteran": {"name": "Veteran", "permissions": ["invite", "bank_deposit"]},
    "member": {"name": "Membru", "permissions": ["bank_deposit"]},
    "recruit": {"name": "Recrut", "permissions": []}
}

# Guild perks (unlocked at different levels)
GUILD_PERKS = {
    1: {"name": "Guild Chat", "description": "Chat privat pentru membrii"},
    3: {"name": "Guild Bank", "description": "Trezorerie comună"},
    5: {"name": "+5% XP Bonus", "description": "Bonus XP pentru toți membrii", "xp_bonus": 0.05},
    10: {"name": "+10% Trading Discount", "description": "Reducere la comisioane", "fee_reduction": 0.10},
    15: {"name": "Guild Wars", "description": "Participă la războaie între gilde"},
    20: {"name": "+15% XP Bonus", "description": "Bonus XP crescut", "xp_bonus": 0.15},
    25: {"name": "Alliance Creation", "description": "Creează alianțe cu alte gilde"}
}

# Max members per guild level
def get_max_members(level):
    return 10 + (level * 5)  # 15 at level 1, 60 at level 10, etc.


# ============== MODELS ==============

class CreateGuildRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=30)
    tag: str = Field(..., min_length=2, max_length=5)
    description: str = Field(..., min_length=10, max_length=500)
    color: str = "#00F0FF"
    is_public: bool = True

class GuildInviteRequest(BaseModel):
    username: str

class GuildAnnouncementRequest(BaseModel):
    title: str = Field(..., max_length=100)
    content: str = Field(..., max_length=1000)

class GuildBankTransaction(BaseModel):
    amount: float = Field(..., gt=0)
    note: Optional[str] = None

class CreateAllianceRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=30)
    guild_ids: List[str]


# ============== HELPER FUNCTIONS ==============

async def get_user_guild(user_id: str):
    """Get user's current guild membership"""
    membership = await db.guild_members.find_one({
        "user_id": user_id,
        "status": "active"
    })
    if membership:
        guild = await db.guilds.find_one({"id": membership["guild_id"]})
        return guild, membership
    return None, None

async def calculate_guild_level(guild_id: str) -> int:
    """Calculate guild level based on total XP"""
    guild = await db.guilds.find_one({"id": guild_id})
    if not guild:
        return 1
    xp = guild.get("total_xp", 0)
    # Level formula: level = floor(sqrt(xp / 1000)) + 1
    import math
    return max(1, int(math.sqrt(xp / 1000)) + 1)

async def add_guild_xp(guild_id: str, amount: int):
    """Add XP to guild"""
    await db.guilds.update_one(
        {"id": guild_id},
        {"$inc": {"total_xp": amount}}
    )
    # Update level
    new_level = await calculate_guild_level(guild_id)
    await db.guilds.update_one(
        {"id": guild_id},
        {"$set": {"level": new_level}}
    )


# ============== GUILD ENDPOINTS ==============

@router.get("/list")
async def list_guilds(
    search: Optional[str] = None,
    limit: int = 20
):
    """List public guilds"""
    query = {"is_public": True}
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"tag": {"$regex": search, "$options": "i"}}
        ]
    
    guilds = await db.guilds.find(query, {"_id": 0}).sort("level", -1).limit(limit).to_list(limit)
    
    # Enrich with member count
    for guild in guilds:
        guild["member_count"] = await db.guild_members.count_documents({
            "guild_id": guild["id"],
            "status": "active"
        })
    
    return {"guilds": guilds}


@router.get("/my-guild")
async def get_my_guild(current_user: dict = Depends(get_current_user)):
    """Get user's guild info"""
    guild, membership = await get_user_guild(current_user["id"])
    
    if not guild:
        return {
            "has_guild": False,
            "can_create": current_user.get("realum_balance", 0) >= GUILD_CREATION_COST,
            "creation_cost": GUILD_CREATION_COST
        }
    
    # Get members
    members = await db.guild_members.find(
        {"guild_id": guild["id"], "status": "active"},
        {"_id": 0}
    ).to_list(100)
    
    # Get announcements
    announcements = await db.guild_announcements.find(
        {"guild_id": guild["id"]},
        {"_id": 0}
    ).sort("created_at", -1).limit(10).to_list(10)
    
    # Get available perks
    level = guild.get("level", 1)
    available_perks = [perk for lvl, perk in GUILD_PERKS.items() if lvl <= level]
    
    return {
        "has_guild": True,
        "guild": serialize_doc(guild),
        "membership": serialize_doc(membership),
        "members": members,
        "announcements": announcements,
        "perks": available_perks,
        "max_members": get_max_members(level),
        "ranks": GUILD_RANKS
    }


@router.post("/create")
async def create_guild(
    data: CreateGuildRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create a new guild"""
    # Check if user already in a guild
    existing_guild, _ = await get_user_guild(current_user["id"])
    if existing_guild:
        raise HTTPException(status_code=400, detail="You're already in a guild")
    
    # Check balance
    if current_user.get("realum_balance", 0) < GUILD_CREATION_COST:
        raise HTTPException(status_code=400, detail=f"Need {GUILD_CREATION_COST} RLM to create a guild")
    
    # Check unique name/tag
    existing = await db.guilds.find_one({
        "$or": [{"name": data.name}, {"tag": data.tag.upper()}]
    })
    if existing:
        raise HTTPException(status_code=400, detail="Guild name or tag already exists")
    
    # Deduct cost
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$inc": {"realum_balance": -GUILD_CREATION_COST}}
    )
    
    now = datetime.now(timezone.utc)
    
    guild = {
        "id": str(uuid.uuid4()),
        "name": data.name,
        "tag": data.tag.upper(),
        "description": data.description,
        "color": data.color,
        "leader_id": current_user["id"],
        "leader_username": current_user["username"],
        "is_public": data.is_public,
        "level": 1,
        "total_xp": 0,
        "bank_balance": GUILD_CREATION_COST * 0.5,  # 50% goes to guild bank
        "alliance_id": None,
        "created_at": now.isoformat()
    }
    await db.guilds.insert_one(guild)
    
    # Add creator as leader
    membership = {
        "id": str(uuid.uuid4()),
        "guild_id": guild["id"],
        "user_id": current_user["id"],
        "username": current_user["username"],
        "rank": "leader",
        "status": "active",
        "joined_at": now.isoformat()
    }
    await db.guild_members.insert_one(membership)
    
    return {
        "guild": serialize_doc(guild),
        "message": f"Guild '{data.name}' created successfully!"
    }


@router.post("/{guild_id}/join")
async def join_guild(
    guild_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Join a public guild"""
    existing_guild, _ = await get_user_guild(current_user["id"])
    if existing_guild:
        raise HTTPException(status_code=400, detail="You're already in a guild")
    
    guild = await db.guilds.find_one({"id": guild_id})
    if not guild:
        raise HTTPException(status_code=404, detail="Guild not found")
    
    if not guild.get("is_public"):
        raise HTTPException(status_code=400, detail="This guild is invite-only")
    
    # Check member limit
    member_count = await db.guild_members.count_documents({
        "guild_id": guild_id,
        "status": "active"
    })
    max_members = get_max_members(guild.get("level", 1))
    if member_count >= max_members:
        raise HTTPException(status_code=400, detail="Guild is full")
    
    now = datetime.now(timezone.utc)
    
    membership = {
        "id": str(uuid.uuid4()),
        "guild_id": guild_id,
        "user_id": current_user["id"],
        "username": current_user["username"],
        "rank": "recruit",
        "status": "active",
        "joined_at": now.isoformat()
    }
    await db.guild_members.insert_one(membership)
    
    # Add XP to guild
    await add_guild_xp(guild_id, 100)
    
    return {"message": f"Joined guild '{guild['name']}'!"}


@router.post("/leave")
async def leave_guild(current_user: dict = Depends(get_current_user)):
    """Leave current guild"""
    guild, membership = await get_user_guild(current_user["id"])
    
    if not guild:
        raise HTTPException(status_code=400, detail="You're not in a guild")
    
    if membership["rank"] == "leader":
        # Transfer leadership or disband
        other_members = await db.guild_members.find({
            "guild_id": guild["id"],
            "status": "active",
            "user_id": {"$ne": current_user["id"]}
        }).to_list(1)
        
        if other_members:
            # Transfer to first officer, or first member
            new_leader = other_members[0]
            await db.guild_members.update_one(
                {"id": new_leader["id"]},
                {"$set": {"rank": "leader"}}
            )
            await db.guilds.update_one(
                {"id": guild["id"]},
                {"$set": {
                    "leader_id": new_leader["user_id"],
                    "leader_username": new_leader["username"]
                }}
            )
        else:
            # Disband guild
            await db.guilds.delete_one({"id": guild["id"]})
    
    await db.guild_members.update_one(
        {"id": membership["id"]},
        {"$set": {"status": "left", "left_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"message": "Left the guild"}


@router.post("/{guild_id}/invite")
async def invite_to_guild(
    guild_id: str,
    data: GuildInviteRequest,
    current_user: dict = Depends(get_current_user)
):
    """Invite a user to guild"""
    guild, membership = await get_user_guild(current_user["id"])
    
    if not guild or guild["id"] != guild_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if "invite" not in GUILD_RANKS[membership["rank"]]["permissions"] and membership["rank"] != "leader":
        raise HTTPException(status_code=403, detail="No permission to invite")
    
    # Find target user
    target = await db.users.find_one({"username": data.username})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if already in a guild
    existing, _ = await get_user_guild(target["id"])
    if existing:
        raise HTTPException(status_code=400, detail="User is already in a guild")
    
    # Create invite
    invite = {
        "id": str(uuid.uuid4()),
        "guild_id": guild_id,
        "guild_name": guild["name"],
        "inviter_id": current_user["id"],
        "inviter_username": current_user["username"],
        "target_id": target["id"],
        "target_username": target["username"],
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.guild_invites.insert_one(invite)
    
    # Notify target
    await db.notifications.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": target["id"],
        "type": "guild_invite",
        "title": "Invitație la Guild!",
        "message": f"{current_user['username']} te-a invitat în guild-ul {guild['name']}",
        "data": {"invite_id": invite["id"]},
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": f"Invited {data.username} to the guild"}


@router.post("/invites/{invite_id}/accept")
async def accept_invite(
    invite_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Accept guild invite"""
    invite = await db.guild_invites.find_one({
        "id": invite_id,
        "target_id": current_user["id"],
        "status": "pending"
    })
    
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")
    
    # Check if already in guild
    existing, _ = await get_user_guild(current_user["id"])
    if existing:
        raise HTTPException(status_code=400, detail="You're already in a guild")
    
    guild = await db.guilds.find_one({"id": invite["guild_id"]})
    if not guild:
        raise HTTPException(status_code=404, detail="Guild no longer exists")
    
    now = datetime.now(timezone.utc)
    
    # Create membership
    membership = {
        "id": str(uuid.uuid4()),
        "guild_id": guild["id"],
        "user_id": current_user["id"],
        "username": current_user["username"],
        "rank": "recruit",
        "status": "active",
        "joined_at": now.isoformat()
    }
    await db.guild_members.insert_one(membership)
    
    # Update invite
    await db.guild_invites.update_one(
        {"id": invite_id},
        {"$set": {"status": "accepted"}}
    )
    
    await add_guild_xp(guild["id"], 100)
    
    return {"message": f"Joined guild '{guild['name']}'!"}


@router.post("/{guild_id}/announce")
async def create_announcement(
    guild_id: str,
    data: GuildAnnouncementRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create guild announcement"""
    guild, membership = await get_user_guild(current_user["id"])
    
    if not guild or guild["id"] != guild_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if "announce" not in GUILD_RANKS[membership["rank"]]["permissions"] and membership["rank"] != "leader":
        raise HTTPException(status_code=403, detail="No permission to announce")
    
    announcement = {
        "id": str(uuid.uuid4()),
        "guild_id": guild_id,
        "author_id": current_user["id"],
        "author_username": current_user["username"],
        "title": data.title,
        "content": data.content,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.guild_announcements.insert_one(announcement)
    
    return {"announcement": serialize_doc(announcement)}


@router.post("/{guild_id}/bank/deposit")
async def deposit_to_guild_bank(
    guild_id: str,
    data: GuildBankTransaction,
    current_user: dict = Depends(get_current_user)
):
    """Deposit to guild bank"""
    guild, membership = await get_user_guild(current_user["id"])
    
    if not guild or guild["id"] != guild_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if guild.get("level", 1) < 3:
        raise HTTPException(status_code=400, detail="Guild bank unlocks at level 3")
    
    if current_user.get("realum_balance", 0) < data.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    # Transfer
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$inc": {"realum_balance": -data.amount}}
    )
    
    await db.guilds.update_one(
        {"id": guild_id},
        {"$inc": {"bank_balance": data.amount}}
    )
    
    # Log transaction
    await db.guild_bank_transactions.insert_one({
        "id": str(uuid.uuid4()),
        "guild_id": guild_id,
        "user_id": current_user["id"],
        "username": current_user["username"],
        "type": "deposit",
        "amount": data.amount,
        "note": data.note,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    # Add XP
    await add_guild_xp(guild_id, int(data.amount / 10))
    
    return {"message": f"Deposited {data.amount} RLM to guild bank"}


@router.get("/leaderboard")
async def get_guild_leaderboard(limit: int = 20):
    """Get top guilds"""
    guilds = await db.guilds.find(
        {},
        {"_id": 0}
    ).sort("level", -1).limit(limit).to_list(limit)
    
    for i, guild in enumerate(guilds):
        guild["rank"] = i + 1
        guild["member_count"] = await db.guild_members.count_documents({
            "guild_id": guild["id"],
            "status": "active"
        })
    
    return {"leaderboard": guilds}


# ============== ALLIANCE ENDPOINTS ==============

@router.get("/alliances")
async def list_alliances():
    """List all alliances"""
    alliances = await db.alliances.find({}, {"_id": 0}).to_list(50)
    
    for alliance in alliances:
        alliance["guild_count"] = await db.guilds.count_documents({
            "alliance_id": alliance["id"]
        })
    
    return {"alliances": alliances}


@router.post("/alliances/create")
async def create_alliance(
    data: CreateAllianceRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create alliance (guild level 25+ required)"""
    guild, membership = await get_user_guild(current_user["id"])
    
    if not guild or membership["rank"] != "leader":
        raise HTTPException(status_code=403, detail="Only guild leaders can create alliances")
    
    if guild.get("level", 1) < 25:
        raise HTTPException(status_code=400, detail="Guild must be level 25+ to create alliance")
    
    if guild.get("alliance_id"):
        raise HTTPException(status_code=400, detail="Guild is already in an alliance")
    
    now = datetime.now(timezone.utc)
    
    alliance = {
        "id": str(uuid.uuid4()),
        "name": data.name,
        "founder_guild_id": guild["id"],
        "founder_guild_name": guild["name"],
        "created_at": now.isoformat()
    }
    await db.alliances.insert_one(alliance)
    
    # Add founding guild to alliance
    await db.guilds.update_one(
        {"id": guild["id"]},
        {"$set": {"alliance_id": alliance["id"]}}
    )
    
    return {"alliance": serialize_doc(alliance), "message": f"Alliance '{data.name}' created!"}
