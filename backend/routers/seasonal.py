"""
REALUM Seasonal Events Calendar
Special events, holidays, and time-limited activities
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from enum import Enum
import uuid

router = APIRouter(prefix="/api/seasonal", tags=["Seasonal Events"])

from core.database import db
from core.auth import get_current_user

# ============== SEASONAL EVENTS DATA ==============

SEASONAL_EVENTS = [
    {
        "id": "winter_festival",
        "name": "Winter Festival",
        "emoji": "❄️",
        "description": "Celebrate the winter season with snow, gifts, and community warmth!",
        "start_month": 12,
        "start_day": 15,
        "end_month": 1,
        "end_day": 5,
        "rewards": {
            "daily_bonus": 2.0,
            "special_items": ["Snowflake Badge", "Winter Avatar Frame"],
            "bonus_rlm": 100
        },
        "activities": [
            {"name": "Gift Exchange", "description": "Send gifts to friends for bonus XP", "reward_rlm": 50},
            {"name": "Snowball Fight", "description": "Mini-game in Social Plaza", "reward_rlm": 25},
            {"name": "Ice Sculpture Contest", "description": "Create and vote on designs", "reward_rlm": 100}
        ],
        "theme_colors": {"primary": "#87CEEB", "secondary": "#FFFFFF", "accent": "#4169E1"}
    },
    {
        "id": "spring_bloom",
        "name": "Spring Bloom Festival",
        "emoji": "🌸",
        "description": "New beginnings! Plant seeds of knowledge and watch your skills grow.",
        "start_month": 3,
        "start_day": 20,
        "end_month": 4,
        "end_day": 10,
        "rewards": {
            "daily_bonus": 1.5,
            "special_items": ["Cherry Blossom Badge", "Growth Avatar Frame"],
            "bonus_rlm": 75
        },
        "activities": [
            {"name": "Skill Seeds", "description": "Plant and grow new skills", "reward_rlm": 40},
            {"name": "Garden Building", "description": "Design virtual gardens", "reward_rlm": 60},
            {"name": "Mentor Match", "description": "Connect with experienced users", "reward_rlm": 30}
        ],
        "theme_colors": {"primary": "#FFB7C5", "secondary": "#90EE90", "accent": "#FF69B4"}
    },
    {
        "id": "summer_games",
        "name": "Summer Games",
        "emoji": "☀️",
        "description": "Compete, collaborate, and conquer in the ultimate metaverse Olympics!",
        "start_month": 6,
        "start_day": 21,
        "end_month": 7,
        "end_day": 21,
        "rewards": {
            "daily_bonus": 2.5,
            "special_items": ["Champion Badge", "Golden Avatar Frame"],
            "bonus_rlm": 200
        },
        "activities": [
            {"name": "Coding Olympics", "description": "Programming competitions", "reward_rlm": 150},
            {"name": "Trading Tournament", "description": "Best traders win big", "reward_rlm": 200},
            {"name": "Creative Showcase", "description": "Art and design contest", "reward_rlm": 100},
            {"name": "Community Challenge", "description": "Team-based objectives", "reward_rlm": 75}
        ],
        "theme_colors": {"primary": "#FFD700", "secondary": "#FF8C00", "accent": "#FF4500"}
    },
    {
        "id": "harvest_moon",
        "name": "Harvest Moon Festival",
        "emoji": "🎃",
        "description": "Reap what you've sown! Celebrate achievements and prepare for winter.",
        "start_month": 10,
        "start_day": 15,
        "end_month": 11,
        "end_day": 5,
        "rewards": {
            "daily_bonus": 1.75,
            "special_items": ["Harvest Badge", "Autumn Avatar Frame"],
            "bonus_rlm": 100
        },
        "activities": [
            {"name": "Achievement Harvest", "description": "Bonus for completing achievements", "reward_rlm": 80},
            {"name": "Mystery Hunt", "description": "Find hidden items across zones", "reward_rlm": 60},
            {"name": "Costume Contest", "description": "Best avatar costume wins", "reward_rlm": 50}
        ],
        "theme_colors": {"primary": "#FF8C00", "secondary": "#8B4513", "accent": "#FFD700"}
    },
    {
        "id": "founders_day",
        "name": "Founders Day",
        "emoji": "🎂",
        "description": "Celebrating the birth of REALUM! Special rewards for all citizens.",
        "start_month": 2,
        "start_day": 5,
        "end_month": 2,
        "end_day": 12,
        "rewards": {
            "daily_bonus": 3.0,
            "special_items": ["Founders Badge", "Legacy Avatar Frame", "Exclusive NFT"],
            "bonus_rlm": 250
        },
        "activities": [
            {"name": "History Tour", "description": "Learn about REALUM's origins", "reward_rlm": 50},
            {"name": "Founders Raffle", "description": "Win rare items", "reward_rlm": 0},
            {"name": "Community AMA", "description": "Ask anything session", "reward_rlm": 25}
        ],
        "theme_colors": {"primary": "#9D4EDD", "secondary": "#00F0FF", "accent": "#FF003C"}
    },
    {
        "id": "dao_week",
        "name": "DAO Governance Week",
        "emoji": "🗳️",
        "description": "Your voice matters! Special voting events and governance discussions.",
        "start_month": 5,
        "start_day": 1,
        "end_month": 5,
        "end_day": 7,
        "rewards": {
            "daily_bonus": 1.5,
            "special_items": ["Voter Badge", "Democracy Frame"],
            "bonus_rlm": 75
        },
        "activities": [
            {"name": "Vote-a-thon", "description": "Extra rewards for voting", "reward_rlm": 40},
            {"name": "Proposal Contest", "description": "Best proposals win", "reward_rlm": 100},
            {"name": "Town Halls", "description": "Live community discussions", "reward_rlm": 30}
        ],
        "theme_colors": {"primary": "#40C4FF", "secondary": "#1E88E5", "accent": "#0D47A1"}
    },
    {
        "id": "new_year",
        "name": "New Year Celebration",
        "emoji": "🎆",
        "description": "Ring in the new year with fireworks, resolutions, and fresh starts!",
        "start_month": 12,
        "start_day": 31,
        "end_month": 1,
        "end_day": 3,
        "rewards": {
            "daily_bonus": 5.0,
            "special_items": ["New Year Badge", "2026 Avatar Frame"],
            "bonus_rlm": 300
        },
        "activities": [
            {"name": "Countdown Party", "description": "Live countdown event", "reward_rlm": 100},
            {"name": "Resolution Setting", "description": "Set goals for the year", "reward_rlm": 50},
            {"name": "Year in Review", "description": "Celebrate your achievements", "reward_rlm": 75}
        ],
        "theme_colors": {"primary": "#FFD700", "secondary": "#C0C0C0", "accent": "#FF1493"}
    },
    {
        "id": "love_week",
        "name": "Love & Friendship Week",
        "emoji": "💝",
        "description": "Celebrate connections! Send love to friends and make new bonds.",
        "start_month": 2,
        "start_day": 10,
        "end_month": 2,
        "end_day": 17,
        "rewards": {
            "daily_bonus": 2.0,
            "special_items": ["Heart Badge", "Love Avatar Frame"],
            "bonus_rlm": 100
        },
        "activities": [
            {"name": "Friend Finder", "description": "Match with compatible users", "reward_rlm": 30},
            {"name": "Gift Giving", "description": "Send virtual gifts", "reward_rlm": 25},
            {"name": "Partnership Bonuses", "description": "Extra rewards for pairs", "reward_rlm": 50}
        ],
        "theme_colors": {"primary": "#FF69B4", "secondary": "#FF1493", "accent": "#DC143C"}
    }
]

# ============== MODELS ==============

class EventParticipation(BaseModel):
    event_id: str
    activity_name: str

# ============== HELPER FUNCTIONS ==============

def serialize_doc(doc):
    if doc is None:
        return None
    if '_id' in doc:
        del doc['_id']
    return doc

def is_event_active(event: dict) -> bool:
    """Check if an event is currently active"""
    now = datetime.now(timezone.utc)
    current_month = now.month
    current_day = now.day
    
    start_month = event["start_month"]
    start_day = event["start_day"]
    end_month = event["end_month"]
    end_day = event["end_day"]
    
    # Handle year-crossing events (e.g., Dec 31 - Jan 3)
    if start_month > end_month:
        # Event crosses year boundary
        if current_month >= start_month:
            return current_day >= start_day if current_month == start_month else True
        elif current_month <= end_month:
            return current_day <= end_day if current_month == end_month else True
        return False
    else:
        # Normal event within same year
        if current_month < start_month or current_month > end_month:
            return False
        if current_month == start_month and current_day < start_day:
            return False
        if current_month == end_month and current_day > end_day:
            return False
        return True

def get_days_until_event(event: dict) -> int:
    """Calculate days until event starts"""
    now = datetime.now(timezone.utc)
    current_year = now.year
    
    # Create event start date
    event_start = datetime(current_year, event["start_month"], event["start_day"], tzinfo=timezone.utc)
    
    # If event already passed this year, calculate for next year
    if event_start < now:
        event_start = datetime(current_year + 1, event["start_month"], event["start_day"], tzinfo=timezone.utc)
    
    delta = event_start - now
    return delta.days

# ============== ENDPOINTS ==============

@router.get("/events")
async def get_all_events():
    """Get all seasonal events with status"""
    events = []
    for event in SEASONAL_EVENTS:
        active = is_event_active(event)
        days_until = get_days_until_event(event) if not active else 0
        
        events.append({
            **event,
            "is_active": active,
            "days_until": days_until,
            "status": "active" if active else ("upcoming" if days_until < 30 else "future")
        })
    
    # Sort: active first, then by days until
    events.sort(key=lambda x: (not x["is_active"], x["days_until"]))
    
    return {"events": events}

@router.get("/active")
async def get_active_events():
    """Get currently active events"""
    active_events = []
    for event in SEASONAL_EVENTS:
        if is_event_active(event):
            active_events.append({
                **event,
                "is_active": True
            })
    
    return {
        "active_events": active_events,
        "count": len(active_events),
        "has_active": len(active_events) > 0
    }

@router.get("/upcoming")
async def get_upcoming_events(days: int = 30):
    """Get upcoming events within specified days"""
    upcoming = []
    for event in SEASONAL_EVENTS:
        if not is_event_active(event):
            days_until = get_days_until_event(event)
            if days_until <= days:
                upcoming.append({
                    **event,
                    "days_until": days_until,
                    "is_active": False
                })
    
    upcoming.sort(key=lambda x: x["days_until"])
    return {"upcoming_events": upcoming}

@router.get("/event/{event_id}")
async def get_event_details(event_id: str):
    """Get detailed info for a specific event"""
    for event in SEASONAL_EVENTS:
        if event["id"] == event_id:
            return {
                "event": {
                    **event,
                    "is_active": is_event_active(event),
                    "days_until": get_days_until_event(event) if not is_event_active(event) else 0
                }
            }
    
    raise HTTPException(status_code=404, detail="Event not found")

@router.post("/participate")
async def participate_in_activity(
    participation: EventParticipation,
    current_user: dict = Depends(get_current_user)
):
    """Participate in an event activity"""
    # Find the event
    event = None
    for e in SEASONAL_EVENTS:
        if e["id"] == participation.event_id:
            event = e
            break
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    if not is_event_active(event):
        raise HTTPException(status_code=400, detail="Event is not currently active")
    
    # Find the activity
    activity = None
    for a in event["activities"]:
        if a["name"] == participation.activity_name:
            activity = a
            break
    
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    # Check if already participated today
    today = datetime.now(timezone.utc).date().isoformat()
    existing = await db.event_participations.find_one({
        "user_id": current_user["id"],
        "event_id": participation.event_id,
        "activity_name": participation.activity_name,
        "date": today
    })
    
    if existing:
        return {"message": "Already participated today", "can_participate": False}
    
    # Record participation
    record = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "event_id": participation.event_id,
        "activity_name": participation.activity_name,
        "reward_rlm": activity["reward_rlm"],
        "date": today,
        "participated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.event_participations.insert_one(record)
    
    return {
        "message": f"Successfully participated in {activity['name']}!",
        "reward_rlm": activity["reward_rlm"],
        "activity": activity,
        "can_participate": False  # Already participated today
    }

@router.get("/my-participation")
async def get_my_participation(
    event_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get user's event participation history"""
    query = {"user_id": current_user["id"]}
    if event_id:
        query["event_id"] = event_id
    
    participations = await db.event_participations.find(query).sort("participated_at", -1).limit(50).to_list(50)
    
    total_rewards = sum(p.get("reward_rlm", 0) for p in participations)
    
    return {
        "participations": [serialize_doc(p) for p in participations],
        "total_count": len(participations),
        "total_rewards_earned": total_rewards
    }

@router.get("/calendar")
async def get_event_calendar():
    """Get full year calendar of events"""
    calendar = {}
    
    for month in range(1, 13):
        calendar[month] = {
            "month_name": datetime(2026, month, 1).strftime("%B"),
            "events": []
        }
    
    for event in SEASONAL_EVENTS:
        start_month = event["start_month"]
        calendar[start_month]["events"].append({
            "id": event["id"],
            "name": event["name"],
            "emoji": event["emoji"],
            "start_day": event["start_day"],
            "end_day": event["end_day"] if event["end_month"] == start_month else f"→{event['end_month']}/{event['end_day']}",
            "theme_colors": event["theme_colors"]
        })
    
    return {"calendar": calendar}

@router.get("/bonus")
async def get_current_bonus(current_user: dict = Depends(get_current_user)):
    """Get current bonus multiplier from active events"""
    total_bonus = 1.0  # Base multiplier
    active_bonuses = []
    
    for event in SEASONAL_EVENTS:
        if is_event_active(event):
            bonus = event["rewards"]["daily_bonus"]
            total_bonus *= bonus
            active_bonuses.append({
                "event": event["name"],
                "emoji": event["emoji"],
                "bonus": bonus
            })
    
    return {
        "total_multiplier": round(total_bonus, 2),
        "active_bonuses": active_bonuses,
        "has_bonus": total_bonus > 1.0
    }
