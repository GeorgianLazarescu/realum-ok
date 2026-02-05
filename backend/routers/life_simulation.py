"""
REALUM Life Simulation System
Comprehensive avatar life simulation with identity, health, relationships, emotions, ethics, careers, and spirituality.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from enum import Enum
import uuid

router = APIRouter(prefix="/api/life", tags=["Life Simulation"])

# Get database and auth
from core.database import get_db
from core.auth import get_current_user

# ============== ENUMS ==============

class GenderIdentity(str, Enum):
    MALE = "male"
    FEMALE = "female"
    NON_BINARY = "non_binary"
    FLUID = "fluid"
    OTHER = "other"
    PREFER_NOT_SAY = "prefer_not_say"

class BiologicalSex(str, Enum):
    MALE = "male"
    FEMALE = "female"
    INTERSEX = "intersex"
    NOT_SPECIFIED = "not_specified"

class RelationshipType(str, Enum):
    MARRIAGE = "marriage"
    PARTNERSHIP = "partnership"
    FAMILY = "family"
    FRIENDSHIP = "friendship"
    MENTORSHIP = "mentorship"
    BUSINESS = "business"

class RelationshipStatus(str, Enum):
    ACTIVE = "active"
    PENDING = "pending"
    DISSOLVED = "dissolved"
    BLOCKED = "blocked"

class EmotionalState(str, Enum):
    HAPPY = "happy"
    SAD = "sad"
    EXCITED = "excited"
    STRESSED = "stressed"
    CALM = "calm"
    ANXIOUS = "anxious"
    MOTIVATED = "motivated"
    TIRED = "tired"
    NEUTRAL = "neutral"

class CareerField(str, Enum):
    EDUCATION = "education"
    HEALTHCARE = "healthcare"
    TECHNOLOGY = "technology"
    ARTS = "arts"
    BUSINESS = "business"
    SCIENCE = "science"
    GOVERNANCE = "governance"
    SOCIAL_WORK = "social_work"
    FREELANCE = "freelance"
    VOLUNTEER = "volunteer"

class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    VULNERABLE = "vulnerable"
    RECOVERING = "recovering"
    CRITICAL = "critical"

# ============== MODELS ==============

class AvatarIdentity(BaseModel):
    display_name: str = Field(..., min_length=2, max_length=50)
    use_real_name: bool = False
    biological_sex: BiologicalSex = BiologicalSex.NOT_SPECIFIED
    gender_identity: GenderIdentity = GenderIdentity.PREFER_NOT_SAY
    avatar_age: int = Field(default=25, ge=18, le=100)
    biography: Optional[str] = Field(None, max_length=1000)
    pronouns: Optional[str] = Field(None, max_length=50)
    avatar_appearance: Optional[Dict[str, Any]] = None

class AvatarHealth(BaseModel):
    status: HealthStatus = HealthStatus.HEALTHY
    energy_level: int = Field(default=100, ge=0, le=100)
    stress_level: int = Field(default=0, ge=0, le=100)
    task_capacity: int = Field(default=100, ge=0, le=100)
    vulnerabilities: List[str] = []
    last_rest: Optional[datetime] = None

class EmotionalEntry(BaseModel):
    state: EmotionalState
    intensity: int = Field(default=50, ge=0, le=100)
    note: Optional[str] = Field(None, max_length=500)
    triggers: List[str] = []

class RelationshipRequest(BaseModel):
    target_user_id: str
    relationship_type: RelationshipType
    message: Optional[str] = Field(None, max_length=500)

class CareerProfile(BaseModel):
    field: CareerField
    title: str = Field(..., max_length=100)
    experience_years: int = Field(default=0, ge=0)
    skills: List[str] = []
    is_volunteer: bool = False

class ReflectionEntry(BaseModel):
    title: str = Field(..., max_length=200)
    content: str = Field(..., max_length=5000)
    mood: EmotionalState = EmotionalState.NEUTRAL
    tags: List[str] = []
    is_private: bool = True

class MoralAction(BaseModel):
    action_type: str
    description: str
    impact_score: int = Field(default=0, ge=-100, le=100)

# ============== HELPER FUNCTIONS ==============

def serialize_doc(doc):
    """Remove MongoDB _id and convert to serializable format"""
    if doc is None:
        return None
    if '_id' in doc:
        del doc['_id']
    return doc

# ============== IDENTITY ENDPOINTS ==============

@router.post("/avatar/identity")
async def create_or_update_identity(
    identity: AvatarIdentity,
    current_user: dict = Depends(get_current_user)
):
    """Create or update avatar identity"""
    db = get_db()
    
    avatar_data = {
        "user_id": current_user["id"],
        "display_name": identity.display_name,
        "use_real_name": identity.use_real_name,
        "biological_sex": identity.biological_sex,
        "gender_identity": identity.gender_identity,
        "avatar_age": identity.avatar_age,
        "biography": identity.biography,
        "pronouns": identity.pronouns,
        "avatar_appearance": identity.avatar_appearance or {},
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    existing = await db.avatar_identities.find_one({"user_id": current_user["id"]})
    
    if existing:
        await db.avatar_identities.update_one(
            {"user_id": current_user["id"]},
            {"$set": avatar_data}
        )
    else:
        avatar_data["created_at"] = datetime.now(timezone.utc).isoformat()
        await db.avatar_identities.insert_one(avatar_data)
    
    return {"message": "Identity saved", "identity": serialize_doc(avatar_data)}

@router.get("/avatar/identity")
async def get_identity(current_user: dict = Depends(get_current_user)):
    """Get current user's avatar identity"""
    db = get_db()
    identity = await db.avatar_identities.find_one({"user_id": current_user["id"]})
    
    if not identity:
        return {"identity": None, "message": "No identity created yet"}
    
    return {"identity": serialize_doc(identity)}

@router.get("/avatar/identity/{user_id}")
async def get_user_identity(user_id: str, current_user: dict = Depends(get_current_user)):
    """Get another user's public identity"""
    db = get_db()
    identity = await db.avatar_identities.find_one({"user_id": user_id})
    
    if not identity:
        raise HTTPException(status_code=404, detail="User identity not found")
    
    # Return only public info
    public_identity = {
        "display_name": identity.get("display_name"),
        "avatar_age": identity.get("avatar_age"),
        "biography": identity.get("biography"),
        "pronouns": identity.get("pronouns"),
        "gender_identity": identity.get("gender_identity") if not identity.get("use_real_name") else None
    }
    
    return {"identity": public_identity}

# ============== HEALTH ENDPOINTS ==============

@router.get("/health/status")
async def get_health_status(current_user: dict = Depends(get_current_user)):
    """Get avatar health status"""
    db = get_db()
    health = await db.avatar_health.find_one({"user_id": current_user["id"]})
    
    if not health:
        # Initialize health
        health = {
            "user_id": current_user["id"],
            "status": HealthStatus.HEALTHY,
            "energy_level": 100,
            "stress_level": 0,
            "task_capacity": 100,
            "vulnerabilities": [],
            "last_rest": datetime.now(timezone.utc).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.avatar_health.insert_one(health)
    
    return {"health": serialize_doc(health)}

@router.post("/health/rest")
async def take_rest(current_user: dict = Depends(get_current_user)):
    """Take rest to recover energy"""
    db = get_db()
    
    await db.avatar_health.update_one(
        {"user_id": current_user["id"]},
        {
            "$set": {
                "energy_level": 100,
                "stress_level": max(0, 0),  # Reset stress
                "task_capacity": 100,
                "last_rest": datetime.now(timezone.utc).isoformat()
            }
        },
        upsert=True
    )
    
    return {"message": "Rest taken, energy restored", "energy_level": 100}

@router.post("/health/activity")
async def record_activity(
    energy_cost: int = 10,
    stress_gain: int = 5,
    current_user: dict = Depends(get_current_user)
):
    """Record activity that affects health"""
    db = get_db()
    health = await db.avatar_health.find_one({"user_id": current_user["id"]})
    
    if not health:
        health = {"energy_level": 100, "stress_level": 0, "task_capacity": 100}
    
    new_energy = max(0, health.get("energy_level", 100) - energy_cost)
    new_stress = min(100, health.get("stress_level", 0) + stress_gain)
    new_capacity = max(0, 100 - new_stress)
    
    status = HealthStatus.HEALTHY
    if new_energy < 30 or new_stress > 70:
        status = HealthStatus.VULNERABLE
    if new_energy < 10 or new_stress > 90:
        status = HealthStatus.CRITICAL
    
    await db.avatar_health.update_one(
        {"user_id": current_user["id"]},
        {
            "$set": {
                "energy_level": new_energy,
                "stress_level": new_stress,
                "task_capacity": new_capacity,
                "status": status
            }
        },
        upsert=True
    )
    
    warning = None
    if status == HealthStatus.VULNERABLE:
        warning = "You're feeling tired. Consider taking a rest!"
    elif status == HealthStatus.CRITICAL:
        warning = "Critical! Your avatar needs rest immediately!"
    
    return {
        "energy_level": new_energy,
        "stress_level": new_stress,
        "task_capacity": new_capacity,
        "status": status,
        "warning": warning
    }

@router.post("/health/reset")
async def reset_avatar(current_user: dict = Depends(get_current_user)):
    """Reset avatar (symbolic death/rebirth)"""
    db = get_db()
    
    # Archive old data
    old_identity = await db.avatar_identities.find_one({"user_id": current_user["id"]})
    if old_identity:
        old_identity["archived_at"] = datetime.now(timezone.utc).isoformat()
        await db.avatar_archive.insert_one(serialize_doc(old_identity))
    
    # Reset everything
    await db.avatar_identities.delete_one({"user_id": current_user["id"]})
    await db.avatar_health.delete_one({"user_id": current_user["id"]})
    await db.avatar_emotions.delete_many({"user_id": current_user["id"]})
    await db.avatar_careers.delete_one({"user_id": current_user["id"]})
    
    return {"message": "Avatar reset complete. Start a new journey!", "reset": True}

# ============== RELATIONSHIPS ENDPOINTS ==============

@router.post("/relationships/request")
async def create_relationship_request(
    request: RelationshipRequest,
    current_user: dict = Depends(get_current_user)
):
    """Send a relationship request"""
    db = get_db()
    
    if request.target_user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot create relationship with yourself")
    
    # Check if relationship already exists
    existing = await db.relationships.find_one({
        "$or": [
            {"user_id": current_user["id"], "target_user_id": request.target_user_id},
            {"user_id": request.target_user_id, "target_user_id": current_user["id"]}
        ],
        "type": request.relationship_type,
        "status": {"$in": [RelationshipStatus.ACTIVE, RelationshipStatus.PENDING]}
    })
    
    if existing:
        raise HTTPException(status_code=400, detail="Relationship already exists or pending")
    
    relationship = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "target_user_id": request.target_user_id,
        "type": request.relationship_type,
        "status": RelationshipStatus.PENDING,
        "message": request.message,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.relationships.insert_one(relationship)
    
    return {"message": "Relationship request sent", "relationship": serialize_doc(relationship)}

@router.post("/relationships/{relationship_id}/accept")
async def accept_relationship(
    relationship_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Accept a relationship request"""
    db = get_db()
    
    relationship = await db.relationships.find_one({
        "id": relationship_id,
        "target_user_id": current_user["id"],
        "status": RelationshipStatus.PENDING
    })
    
    if not relationship:
        raise HTTPException(status_code=404, detail="Relationship request not found")
    
    await db.relationships.update_one(
        {"id": relationship_id},
        {
            "$set": {
                "status": RelationshipStatus.ACTIVE,
                "accepted_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {"message": "Relationship accepted", "status": RelationshipStatus.ACTIVE}

@router.post("/relationships/{relationship_id}/dissolve")
async def dissolve_relationship(
    relationship_id: str,
    reason: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Dissolve a relationship (divorce, end partnership, etc.)"""
    db = get_db()
    
    relationship = await db.relationships.find_one({
        "id": relationship_id,
        "$or": [
            {"user_id": current_user["id"]},
            {"target_user_id": current_user["id"]}
        ],
        "status": RelationshipStatus.ACTIVE
    })
    
    if not relationship:
        raise HTTPException(status_code=404, detail="Active relationship not found")
    
    await db.relationships.update_one(
        {"id": relationship_id},
        {
            "$set": {
                "status": RelationshipStatus.DISSOLVED,
                "dissolved_at": datetime.now(timezone.utc).isoformat(),
                "dissolution_reason": reason,
                "dissolved_by": current_user["id"]
            }
        }
    )
    
    return {"message": "Relationship dissolved", "status": RelationshipStatus.DISSOLVED}

@router.get("/relationships")
async def get_relationships(
    type_filter: Optional[RelationshipType] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get all relationships for current user"""
    db = get_db()
    
    query = {
        "$or": [
            {"user_id": current_user["id"]},
            {"target_user_id": current_user["id"]}
        ],
        "status": RelationshipStatus.ACTIVE
    }
    
    if type_filter:
        query["type"] = type_filter
    
    relationships = await db.relationships.find(query).to_list(100)
    
    return {"relationships": [serialize_doc(r) for r in relationships]}

@router.get("/relationships/pending")
async def get_pending_requests(current_user: dict = Depends(get_current_user)):
    """Get pending relationship requests"""
    db = get_db()
    
    incoming = await db.relationships.find({
        "target_user_id": current_user["id"],
        "status": RelationshipStatus.PENDING
    }).to_list(50)
    
    outgoing = await db.relationships.find({
        "user_id": current_user["id"],
        "status": RelationshipStatus.PENDING
    }).to_list(50)
    
    return {
        "incoming": [serialize_doc(r) for r in incoming],
        "outgoing": [serialize_doc(r) for r in outgoing]
    }

# ============== EMOTIONS ENDPOINTS ==============

@router.post("/emotions/log")
async def log_emotion(
    entry: EmotionalEntry,
    current_user: dict = Depends(get_current_user)
):
    """Log an emotional state"""
    db = get_db()
    
    emotion_log = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "state": entry.state,
        "intensity": entry.intensity,
        "note": entry.note,
        "triggers": entry.triggers,
        "logged_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.avatar_emotions.insert_one(emotion_log)
    
    # Update current emotional state
    await db.avatar_current_emotion.update_one(
        {"user_id": current_user["id"]},
        {"$set": {
            "state": entry.state,
            "intensity": entry.intensity,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }},
        upsert=True
    )
    
    return {"message": "Emotion logged", "entry": serialize_doc(emotion_log)}

@router.get("/emotions/current")
async def get_current_emotion(current_user: dict = Depends(get_current_user)):
    """Get current emotional state"""
    db = get_db()
    
    emotion = await db.avatar_current_emotion.find_one({"user_id": current_user["id"]})
    
    if not emotion:
        return {"emotion": {"state": EmotionalState.NEUTRAL, "intensity": 50}}
    
    return {"emotion": serialize_doc(emotion)}

@router.get("/emotions/history")
async def get_emotion_history(
    days: int = 7,
    current_user: dict = Depends(get_current_user)
):
    """Get emotional history"""
    db = get_db()
    
    emotions = await db.avatar_emotions.find({
        "user_id": current_user["id"]
    }).sort("logged_at", -1).limit(days * 10).to_list(100)
    
    return {"history": [serialize_doc(e) for e in emotions]}

# ============== CAREER ENDPOINTS ==============

@router.post("/career")
async def set_career(
    career: CareerProfile,
    current_user: dict = Depends(get_current_user)
):
    """Set or change career"""
    db = get_db()
    
    career_data = {
        "user_id": current_user["id"],
        "field": career.field,
        "title": career.title,
        "experience_years": career.experience_years,
        "skills": career.skills,
        "is_volunteer": career.is_volunteer,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    existing = await db.avatar_careers.find_one({"user_id": current_user["id"]})
    
    if existing:
        # Archive old career
        existing["ended_at"] = datetime.now(timezone.utc).isoformat()
        await db.avatar_career_history.insert_one(serialize_doc(existing))
        
        await db.avatar_careers.update_one(
            {"user_id": current_user["id"]},
            {"$set": career_data}
        )
    else:
        career_data["started_at"] = datetime.now(timezone.utc).isoformat()
        await db.avatar_careers.insert_one(career_data)
    
    return {"message": "Career updated", "career": serialize_doc(career_data)}

@router.get("/career")
async def get_career(current_user: dict = Depends(get_current_user)):
    """Get current career"""
    db = get_db()
    career = await db.avatar_careers.find_one({"user_id": current_user["id"]})
    
    if not career:
        return {"career": None, "message": "No career set"}
    
    return {"career": serialize_doc(career)}

@router.get("/career/history")
async def get_career_history(current_user: dict = Depends(get_current_user)):
    """Get career history"""
    db = get_db()
    history = await db.avatar_career_history.find({
        "user_id": current_user["id"]
    }).sort("ended_at", -1).to_list(20)
    
    return {"history": [serialize_doc(c) for c in history]}

# ============== ETHICS & REPUTATION ENDPOINTS ==============

@router.post("/ethics/action")
async def record_moral_action(
    action: MoralAction,
    current_user: dict = Depends(get_current_user)
):
    """Record a moral action that affects reputation"""
    db = get_db()
    
    action_record = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "action_type": action.action_type,
        "description": action.description,
        "impact_score": action.impact_score,
        "recorded_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.moral_actions.insert_one(action_record)
    
    # Update reputation score
    await db.avatar_reputation.update_one(
        {"user_id": current_user["id"]},
        {
            "$inc": {"total_score": action.impact_score, "action_count": 1},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
        },
        upsert=True
    )
    
    return {"message": "Action recorded", "impact": action.impact_score}

@router.get("/ethics/reputation")
async def get_reputation(current_user: dict = Depends(get_current_user)):
    """Get reputation score"""
    db = get_db()
    reputation = await db.avatar_reputation.find_one({"user_id": current_user["id"]})
    
    if not reputation:
        return {"reputation": {"total_score": 0, "action_count": 0, "level": "Neutral"}}
    
    score = reputation.get("total_score", 0)
    level = "Neutral"
    if score > 100:
        level = "Exemplary"
    elif score > 50:
        level = "Respected"
    elif score > 0:
        level = "Good"
    elif score < -50:
        level = "Questionable"
    elif score < -100:
        level = "Untrusted"
    
    return {
        "reputation": {
            "total_score": score,
            "action_count": reputation.get("action_count", 0),
            "level": level
        }
    }

# ============== SPIRITUALITY & REFLECTION ENDPOINTS ==============

@router.post("/reflection/journal")
async def create_journal_entry(
    entry: ReflectionEntry,
    current_user: dict = Depends(get_current_user)
):
    """Create a reflection/journal entry"""
    db = get_db()
    
    journal_entry = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "title": entry.title,
        "content": entry.content,
        "mood": entry.mood,
        "tags": entry.tags,
        "is_private": entry.is_private,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.reflection_journal.insert_one(journal_entry)
    
    return {"message": "Journal entry saved", "entry": serialize_doc(journal_entry)}

@router.get("/reflection/journal")
async def get_journal_entries(
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """Get journal entries"""
    db = get_db()
    
    entries = await db.reflection_journal.find({
        "user_id": current_user["id"]
    }).sort("created_at", -1).limit(limit).to_list(limit)
    
    return {"entries": [serialize_doc(e) for e in entries]}

@router.get("/reflection/meditation-spaces")
async def get_meditation_spaces():
    """Get available meditation/reflection spaces"""
    spaces = [
        {
            "id": "zen-garden",
            "name": "Zen Garden",
            "description": "A peaceful Japanese garden for meditation",
            "theme": "nature",
            "ambient_sound": "water_stream"
        },
        {
            "id": "starlight",
            "name": "Starlight Observatory",
            "description": "Gaze at the cosmos and contemplate existence",
            "theme": "space",
            "ambient_sound": "cosmic_hum"
        },
        {
            "id": "forest-sanctuary",
            "name": "Forest Sanctuary",
            "description": "A quiet forest clearing for inner peace",
            "theme": "forest",
            "ambient_sound": "birds_wind"
        },
        {
            "id": "temple-silence",
            "name": "Temple of Silence",
            "description": "A neutral spiritual space for all beliefs",
            "theme": "temple",
            "ambient_sound": "silence"
        }
    ]
    
    return {"spaces": spaces}

# ============== LIFE SUMMARY ==============

@router.get("/summary")
async def get_life_summary(current_user: dict = Depends(get_current_user)):
    """Get complete life summary for avatar"""
    db = get_db()
    
    identity = await db.avatar_identities.find_one({"user_id": current_user["id"]})
    health = await db.avatar_health.find_one({"user_id": current_user["id"]})
    emotion = await db.avatar_current_emotion.find_one({"user_id": current_user["id"]})
    career = await db.avatar_careers.find_one({"user_id": current_user["id"]})
    reputation = await db.avatar_reputation.find_one({"user_id": current_user["id"]})
    
    relationships_count = await db.relationships.count_documents({
        "$or": [
            {"user_id": current_user["id"]},
            {"target_user_id": current_user["id"]}
        ],
        "status": RelationshipStatus.ACTIVE
    })
    
    journal_count = await db.reflection_journal.count_documents({"user_id": current_user["id"]})
    
    return {
        "identity": serialize_doc(identity) if identity else None,
        "health": serialize_doc(health) if health else {"status": "healthy", "energy_level": 100},
        "current_emotion": serialize_doc(emotion) if emotion else {"state": "neutral", "intensity": 50},
        "career": serialize_doc(career) if career else None,
        "reputation": {
            "score": reputation.get("total_score", 0) if reputation else 0,
            "level": "Neutral"
        },
        "relationships_count": relationships_count,
        "journal_entries": journal_count
    }
