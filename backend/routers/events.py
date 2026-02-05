"""
REALUM Random Events & Mini-Tasks System
Generates random life events, opportunities, expenses, and mini-tasks
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from enum import Enum
import uuid
import random

router = APIRouter(prefix="/api/events", tags=["Random Events"])

from core.database import db
from core.auth import get_current_user

# ============== ENUMS ==============

class EventType(str, Enum):
    ILLNESS = "illness"
    OPPORTUNITY = "opportunity"
    EXPENSE = "expense"
    SOCIAL = "social"
    CAREER = "career"
    DISCOVERY = "discovery"
    CHALLENGE = "challenge"

class EventSeverity(str, Enum):
    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    CRITICAL = "critical"

class TaskType(str, Enum):
    JOB = "job"
    DECISION = "decision"
    ACTION = "action"
    SOCIAL = "social"
    LEARNING = "learning"

class TaskStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"

# ============== EVENT TEMPLATES ==============

ILLNESS_EVENTS = [
    {"name": "Common Cold", "severity": "minor", "energy_cost": 10, "duration_hours": 24, "description": "You caught a cold. Rest recommended."},
    {"name": "Fatigue", "severity": "minor", "energy_cost": 20, "duration_hours": 12, "description": "You're feeling exhausted from overwork."},
    {"name": "Stress Burnout", "severity": "moderate", "energy_cost": 40, "duration_hours": 48, "description": "Work stress is affecting your health."},
    {"name": "Digital Eye Strain", "severity": "minor", "energy_cost": 15, "duration_hours": 6, "description": "Too much screen time is affecting you."},
    {"name": "Anxiety Episode", "severity": "moderate", "energy_cost": 30, "duration_hours": 24, "description": "You're experiencing anxiety. Take time for self-care."},
]

OPPORTUNITY_EVENTS = [
    {"name": "Job Offer", "severity": "major", "reward_rlm": 500, "description": "A company noticed your work and wants to hire you!", "action_required": True},
    {"name": "Investment Opportunity", "severity": "moderate", "reward_rlm": 200, "description": "A promising project is looking for investors.", "action_required": True},
    {"name": "Mentorship Request", "severity": "minor", "reward_rlm": 100, "description": "Someone wants you to be their mentor.", "action_required": True},
    {"name": "Collaboration Invite", "severity": "moderate", "reward_rlm": 300, "description": "A team wants to collaborate with you.", "action_required": True},
    {"name": "Skill Workshop", "severity": "minor", "reward_rlm": 50, "description": "Free workshop available to boost your skills.", "action_required": True},
    {"name": "Lucky Find", "severity": "minor", "reward_rlm": 25, "description": "You found some RLM tokens!", "action_required": False},
]

EXPENSE_EVENTS = [
    {"name": "Equipment Repair", "severity": "minor", "cost_rlm": 50, "description": "Your virtual equipment needs maintenance."},
    {"name": "Subscription Renewal", "severity": "minor", "cost_rlm": 30, "description": "Time to renew your platform subscription."},
    {"name": "Emergency Fund", "severity": "moderate", "cost_rlm": 150, "description": "Unexpected expense requires your attention."},
    {"name": "Training Course", "severity": "minor", "cost_rlm": 75, "description": "Invest in your education."},
    {"name": "Health Recovery", "severity": "moderate", "cost_rlm": 100, "description": "Medical expenses for your avatar."},
]

SOCIAL_EVENTS = [
    {"name": "Friend Request", "severity": "minor", "description": "Someone wants to connect with you!", "action_required": True},
    {"name": "Community Event", "severity": "minor", "description": "A community gathering is happening nearby.", "action_required": True},
    {"name": "Birthday Celebration", "severity": "minor", "reward_rlm": 10, "description": "A friend is celebrating their birthday!"},
    {"name": "Group Invitation", "severity": "minor", "description": "You've been invited to join a group.", "action_required": True},
]

MINI_TASKS = [
    {"type": "job", "name": "Quick Review", "description": "Review a document for a colleague", "reward_rlm": 15, "time_limit_mins": 30},
    {"type": "job", "name": "Data Entry", "description": "Enter some data into the system", "reward_rlm": 20, "time_limit_mins": 45},
    {"type": "decision", "name": "Choose Path", "description": "Make a decision about your next project", "reward_rlm": 10, "time_limit_mins": 60},
    {"type": "action", "name": "Help a Newbie", "description": "Assist a new user with their first steps", "reward_rlm": 25, "time_limit_mins": 20},
    {"type": "social", "name": "Send Encouragement", "description": "Send a supportive message to someone", "reward_rlm": 5, "time_limit_mins": 10},
    {"type": "learning", "name": "Quick Quiz", "description": "Complete a short knowledge quiz", "reward_rlm": 15, "time_limit_mins": 15},
    {"type": "job", "name": "Bug Report", "description": "Report a bug you've found", "reward_rlm": 30, "time_limit_mins": 20},
    {"type": "action", "name": "Daily Check-in", "description": "Log your daily progress", "reward_rlm": 5, "time_limit_mins": 5},
]

# ============== MODELS ==============

class EventResponse(BaseModel):
    event_id: str
    accepted: bool
    response_data: Optional[Dict[str, Any]] = None

class TaskCompletion(BaseModel):
    task_id: str
    result: Optional[str] = None

# ============== HELPER FUNCTIONS ==============

def serialize_doc(doc):
    if doc is None:
        return None
    if '_id' in doc:
        del doc['_id']
    return doc

async def create_notification(user_id: str, title: str, message: str, event_type: str, event_id: str = None):
    """Create a notification for a user"""
    notification = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "title": title,
        "message": message,
        "type": event_type,
        "event_id": event_id,
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.notifications.insert_one(notification)
    return notification

# ============== EVENT ENDPOINTS ==============

@router.post("/generate")
async def generate_random_event(current_user: dict = Depends(get_current_user)):
    """Generate a random event for the user"""
    
    # Determine event type based on weighted random
    event_types = [
        (EventType.ILLNESS, 15),
        (EventType.OPPORTUNITY, 30),
        (EventType.EXPENSE, 20),
        (EventType.SOCIAL, 25),
        (EventType.DISCOVERY, 10),
    ]
    
    total_weight = sum(w for _, w in event_types)
    r = random.randint(1, total_weight)
    
    cumulative = 0
    selected_type = EventType.SOCIAL
    for event_type, weight in event_types:
        cumulative += weight
        if r <= cumulative:
            selected_type = event_type
            break
    
    # Select random event from template
    if selected_type == EventType.ILLNESS:
        template = random.choice(ILLNESS_EVENTS)
        event_data = {
            "type": EventType.ILLNESS,
            "energy_cost": template["energy_cost"],
            "duration_hours": template["duration_hours"],
        }
    elif selected_type == EventType.OPPORTUNITY:
        template = random.choice(OPPORTUNITY_EVENTS)
        event_data = {
            "type": EventType.OPPORTUNITY,
            "reward_rlm": template.get("reward_rlm", 0),
            "action_required": template.get("action_required", False),
        }
    elif selected_type == EventType.EXPENSE:
        template = random.choice(EXPENSE_EVENTS)
        event_data = {
            "type": EventType.EXPENSE,
            "cost_rlm": template["cost_rlm"],
        }
    else:
        template = random.choice(SOCIAL_EVENTS)
        event_data = {
            "type": EventType.SOCIAL,
            "reward_rlm": template.get("reward_rlm", 0),
            "action_required": template.get("action_required", False),
        }
    
    event = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "name": template["name"],
        "description": template["description"],
        "severity": template["severity"],
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
        **event_data
    }
    
    await db.random_events.insert_one(event)
    
    # Create notification
    await create_notification(
        current_user["id"],
        f"🎲 {template['name']}",
        template["description"],
        selected_type,
        event["id"]
    )
    
    return {"event": serialize_doc(event), "message": "New event generated!"}

@router.get("/active")
async def get_active_events(current_user: dict = Depends(get_current_user)):
    """Get all active events for the user"""
    
    events = await db.random_events.find({
        "user_id": current_user["id"],
        "status": "active"
    }).sort("created_at", -1).to_list(20)
    
    return {"events": [serialize_doc(e) for e in events]}

@router.post("/{event_id}/respond")
async def respond_to_event(
    event_id: str,
    response: EventResponse,
    current_user: dict = Depends(get_current_user)
):
    """Respond to an event (accept/decline opportunity, pay expense, etc.)"""
    
    event = await db.random_events.find_one({
        "id": event_id,
        "user_id": current_user["id"],
        "status": "active"
    })
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    result = {"message": "Event processed"}
    
    if event["type"] == EventType.OPPORTUNITY and response.accepted:
        # Grant reward
        result["reward_rlm"] = event.get("reward_rlm", 0)
        result["message"] = f"Opportunity accepted! You earned {result['reward_rlm']} RLM"
    elif event["type"] == EventType.EXPENSE and response.accepted:
        # Deduct cost
        result["cost_rlm"] = event.get("cost_rlm", 0)
        result["message"] = f"Expense paid: {result['cost_rlm']} RLM"
    elif event["type"] == EventType.ILLNESS:
        # Apply health effect
        await db.avatar_health.update_one(
            {"user_id": current_user["id"]},
            {"$inc": {"energy_level": -event.get("energy_cost", 10)}}
        )
        result["message"] = "Health effect applied. Consider resting."
    
    await db.random_events.update_one(
        {"id": event_id},
        {"$set": {
            "status": "resolved" if response.accepted else "declined",
            "resolved_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return result

# ============== MINI-TASKS ENDPOINTS ==============

@router.get("/tasks")
async def get_available_tasks(current_user: dict = Depends(get_current_user)):
    """Get available mini-tasks"""
    
    # Check existing pending tasks
    existing = await db.mini_tasks.find({
        "user_id": current_user["id"],
        "status": TaskStatus.PENDING
    }).to_list(10)
    
    if len(existing) < 3:
        # Generate new tasks
        num_to_generate = 3 - len(existing)
        for _ in range(num_to_generate):
            template = random.choice(MINI_TASKS)
            task = {
                "id": str(uuid.uuid4()),
                "user_id": current_user["id"],
                "type": template["type"],
                "name": template["name"],
                "description": template["description"],
                "reward_rlm": template["reward_rlm"],
                "time_limit_mins": template["time_limit_mins"],
                "status": TaskStatus.PENDING,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=template["time_limit_mins"] * 2)).isoformat()
            }
            await db.mini_tasks.insert_one(task)
            existing.append(task)
    
    return {"tasks": [serialize_doc(t) for t in existing]}

@router.post("/tasks/{task_id}/accept")
async def accept_task(task_id: str, current_user: dict = Depends(get_current_user)):
    """Accept a mini-task"""
    
    task = await db.mini_tasks.find_one({
        "id": task_id,
        "user_id": current_user["id"],
        "status": TaskStatus.PENDING
    })
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    await db.mini_tasks.update_one(
        {"id": task_id},
        {"$set": {
            "status": TaskStatus.ACCEPTED,
            "accepted_at": datetime.now(timezone.utc).isoformat(),
            "deadline": (datetime.now(timezone.utc) + timedelta(minutes=task["time_limit_mins"])).isoformat()
        }}
    )
    
    return {"message": "Task accepted!", "deadline_mins": task["time_limit_mins"]}

@router.post("/tasks/{task_id}/complete")
async def complete_task(
    task_id: str,
    completion: TaskCompletion,
    current_user: dict = Depends(get_current_user)
):
    """Complete a mini-task"""
    
    task = await db.mini_tasks.find_one({
        "id": task_id,
        "user_id": current_user["id"],
        "status": TaskStatus.ACCEPTED
    })
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found or not accepted")
    
    # Check if within deadline
    deadline = datetime.fromisoformat(task["deadline"].replace('Z', '+00:00'))
    now = datetime.now(timezone.utc)
    
    on_time = now <= deadline
    reward = task["reward_rlm"] if on_time else task["reward_rlm"] // 2
    
    await db.mini_tasks.update_one(
        {"id": task_id},
        {"$set": {
            "status": TaskStatus.COMPLETED,
            "completed_at": now.isoformat(),
            "on_time": on_time,
            "final_reward": reward
        }}
    )
    
    # Create notification
    await create_notification(
        current_user["id"],
        "✅ Task Completed!",
        f"You earned {reward} RLM" + (" (on time bonus!)" if on_time else " (late penalty)"),
        "task_complete",
        task_id
    )
    
    return {
        "message": "Task completed!",
        "reward_rlm": reward,
        "on_time": on_time
    }

# ============== OBJECTIVES ENDPOINTS ==============

@router.get("/objectives")
async def get_user_objectives(current_user: dict = Depends(get_current_user)):
    """Get user's current objectives and next steps"""
    
    # Check user's progress and generate objectives
    identity = await db.avatar_identities.find_one({"user_id": current_user["id"]})
    career = await db.avatar_careers.find_one({"user_id": current_user["id"]})
    relationships = await db.relationships.count_documents({
        "$or": [{"user_id": current_user["id"]}, {"target_user_id": current_user["id"]}],
        "status": "active"
    })
    
    objectives = []
    
    # Identity objective
    if not identity or not identity.get("display_name"):
        objectives.append({
            "id": "create_identity",
            "title": "Create Your Avatar",
            "description": "Set up your avatar identity with name, age, and biography",
            "priority": "high",
            "reward_rlm": 50,
            "category": "identity",
            "completed": False
        })
    else:
        objectives.append({
            "id": "create_identity",
            "title": "Create Your Avatar",
            "description": "Avatar created successfully!",
            "priority": "high",
            "reward_rlm": 50,
            "category": "identity",
            "completed": True
        })
    
    # Career objective
    if not career:
        objectives.append({
            "id": "set_career",
            "title": "Choose Your Career",
            "description": "Select a career path and start your professional journey",
            "priority": "high",
            "reward_rlm": 75,
            "category": "career",
            "completed": False
        })
    else:
        objectives.append({
            "id": "set_career",
            "title": "Choose Your Career",
            "description": f"Working as {career.get('title', 'Professional')}",
            "priority": "high",
            "reward_rlm": 75,
            "category": "career",
            "completed": True
        })
    
    # Social objective
    if relationships < 1:
        objectives.append({
            "id": "make_friend",
            "title": "Make a Connection",
            "description": "Connect with another user in the metaverse",
            "priority": "medium",
            "reward_rlm": 30,
            "category": "social",
            "completed": False
        })
    
    # Daily objectives
    objectives.extend([
        {
            "id": "daily_checkin",
            "title": "Daily Check-in",
            "description": "Log your daily emotional state",
            "priority": "low",
            "reward_rlm": 10,
            "category": "daily",
            "completed": False
        },
        {
            "id": "complete_task",
            "title": "Complete a Mini-Task",
            "description": "Finish at least one mini-task today",
            "priority": "low",
            "reward_rlm": 15,
            "category": "daily",
            "completed": False
        },
        {
            "id": "explore_zone",
            "title": "Explore a Zone",
            "description": "Visit a new zone in the 3D metaverse",
            "priority": "low",
            "reward_rlm": 20,
            "category": "exploration",
            "completed": False
        }
    ])
    
    return {"objectives": objectives}

# ============== NOTIFICATIONS ENDPOINTS ==============

@router.get("/notifications")
async def get_notifications(
    unread_only: bool = False,
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """Get user notifications"""
    
    query = {"user_id": current_user["id"]}
    if unread_only:
        query["read"] = False
    
    notifications = await db.notifications.find(query).sort("created_at", -1).limit(limit).to_list(limit)
    
    unread_count = await db.notifications.count_documents({
        "user_id": current_user["id"],
        "read": False
    })
    
    return {
        "notifications": [serialize_doc(n) for n in notifications],
        "unread_count": unread_count
    }

@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, current_user: dict = Depends(get_current_user)):
    """Mark a notification as read"""
    
    await db.notifications.update_one(
        {"id": notification_id, "user_id": current_user["id"]},
        {"$set": {"read": True, "read_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"message": "Notification marked as read"}

@router.post("/notifications/read-all")
async def mark_all_notifications_read(current_user: dict = Depends(get_current_user)):
    """Mark all notifications as read"""
    
    await db.notifications.update_many(
        {"user_id": current_user["id"], "read": False},
        {"$set": {"read": True, "read_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"message": "All notifications marked as read"}

# ============== DAY/NIGHT CYCLE ==============

@router.get("/world/time")
async def get_world_time():
    """Get current world time (day/night cycle)"""
    
    # 1 real hour = 1 virtual day
    now = datetime.now(timezone.utc)
    virtual_hour = (now.hour * 24 + now.minute * 0.4) % 24
    
    if 6 <= virtual_hour < 12:
        period = "morning"
        description = "The sun rises over the metaverse"
    elif 12 <= virtual_hour < 18:
        period = "afternoon"
        description = "The day is in full swing"
    elif 18 <= virtual_hour < 21:
        period = "evening"
        description = "The sun sets on the horizon"
    else:
        period = "night"
        description = "Stars illuminate the metaverse"
    
    return {
        "virtual_hour": round(virtual_hour, 1),
        "period": period,
        "description": description,
        "is_day": 6 <= virtual_hour < 18,
        "sun_position": (virtual_hour - 6) / 12 if 6 <= virtual_hour < 18 else 0
    }

# ============== NPC ACTIVITY ==============

@router.get("/npcs")
async def get_active_npcs():
    """Get active NPCs in the metaverse"""
    
    npcs = [
        {
            "id": "mentor_aria",
            "name": "Aria",
            "role": "Mentor",
            "location": "Learning Zone",
            "activity": "Teaching a class on blockchain basics",
            "available": True,
            "avatar": "👩‍🏫"
        },
        {
            "id": "trader_max",
            "name": "Max",
            "role": "Trader",
            "location": "Marketplace",
            "activity": "Negotiating a deal",
            "available": False,
            "avatar": "🧑‍💼"
        },
        {
            "id": "guide_luna",
            "name": "Luna",
            "role": "Guide",
            "location": "Social Plaza",
            "activity": "Welcoming new users",
            "available": True,
            "avatar": "👩‍🎤"
        },
        {
            "id": "healer_sage",
            "name": "Sage",
            "role": "Healer",
            "location": "Wellness Center",
            "activity": "Meditation session",
            "available": True,
            "avatar": "🧘"
        },
        {
            "id": "banker_vault",
            "name": "Vault",
            "role": "Banker",
            "location": "Treasury",
            "activity": "Processing transactions",
            "available": True,
            "avatar": "🏦"
        },
        {
            "id": "recruiter_hire",
            "name": "Alex",
            "role": "Recruiter",
            "location": "Jobs Hub",
            "activity": "Reviewing applications",
            "available": True,
            "avatar": "👔"
        },
    ]
    
    # Randomly update availability
    for npc in npcs:
        npc["available"] = random.random() > 0.3
    
    return {"npcs": npcs}
