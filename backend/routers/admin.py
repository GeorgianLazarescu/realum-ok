from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel
import uuid

from core.database import db
from core.auth import get_current_user, admin_required

router = APIRouter(tags=["Admin"])

@router.post("/seed")
async def seed_database():
    """Seed the database with initial data"""
    now = datetime.now(timezone.utc).isoformat()
    
    # Seed Zones
    zones = [
        {"id": "hub", "name": "Central HUB", "description": "The heart of REALUM - connect, collaborate, and discover", "type": "social", "color": "#00F0FF", "buildings": []},
        {"id": "marketplace", "name": "Marketplace", "description": "Trade digital resources and services", "type": "commerce", "color": "#FF6B35", "buildings": []},
        {"id": "learning", "name": "Learning Zone", "description": "Courses, workshops, and skill development", "type": "education", "color": "#9D4EDD", "buildings": []},
        {"id": "dao", "name": "DAO Arena", "description": "Community governance and voting", "type": "governance", "color": "#40C4FF", "buildings": []},
        {"id": "tech-district", "name": "Tech District", "description": "Technology projects and innovations", "type": "tech", "color": "#FF003C", "buildings": []},
        {"id": "residential", "name": "Residential Area", "description": "Community living and social spaces", "type": "social", "color": "#00FF88", "buildings": []},
        {"id": "industrial", "name": "Industrial Zone", "description": "Production and manufacturing projects", "type": "production", "color": "#F9F871", "buildings": []},
        {"id": "cultural", "name": "Cultural Center", "description": "Arts, events, and cultural activities", "type": "culture", "color": "#E040FB", "buildings": []}
    ]
    await db.zones.delete_many({})
    await db.zones.insert_many(zones)
    
    # Seed Jobs
    jobs = [
        {"id": str(uuid.uuid4()), "title": "UI/UX Designer", "description": "Design intuitive interfaces for metaverse apps", "company": "REALUM Labs", "zone": "hub", "reward": 150, "xp_reward": 200, "duration_minutes": 60, "required_level": 1},
        {"id": str(uuid.uuid4()), "title": "Smart Contract Developer", "description": "Develop and audit blockchain contracts", "company": "ChainTech", "zone": "tech-district", "reward": 300, "xp_reward": 400, "duration_minutes": 120, "required_level": 3, "required_role": "contributor"},
        {"id": str(uuid.uuid4()), "title": "Content Writer", "description": "Create engaging content for the learning zone", "company": "EduMetaverse", "zone": "learning", "reward": 80, "xp_reward": 100, "duration_minutes": 45, "required_level": 1},
        {"id": str(uuid.uuid4()), "title": "Community Manager", "description": "Manage and grow the REALUM community", "company": "REALUM DAO", "zone": "dao", "reward": 120, "xp_reward": 150, "duration_minutes": 90, "required_level": 2},
        {"id": str(uuid.uuid4()), "title": "3D Artist", "description": "Create 3D assets for the metaverse", "company": "MetaArt Studio", "zone": "cultural", "reward": 200, "xp_reward": 250, "duration_minutes": 90, "required_level": 2, "required_role": "creator"},
        {"id": str(uuid.uuid4()), "title": "Market Analyst", "description": "Analyze marketplace trends and data", "company": "MetaMarket", "zone": "marketplace", "reward": 100, "xp_reward": 120, "duration_minutes": 60, "required_level": 2},
        {"id": str(uuid.uuid4()), "title": "Event Coordinator", "description": "Plan and execute virtual events", "company": "EventMeta", "zone": "cultural", "reward": 90, "xp_reward": 110, "duration_minutes": 75, "required_level": 1},
        {"id": str(uuid.uuid4()), "title": "Quality Tester", "description": "Test and validate platform features", "company": "QA Labs", "zone": "tech-district", "reward": 70, "xp_reward": 80, "duration_minutes": 45, "required_level": 1, "required_role": "evaluator"},
        {"id": str(uuid.uuid4()), "title": "Resource Curator", "description": "Curate educational resources", "company": "LearnHub", "zone": "learning", "reward": 60, "xp_reward": 70, "duration_minutes": 30, "required_level": 1},
        {"id": str(uuid.uuid4()), "title": "Partnership Manager", "description": "Manage external partnerships", "company": "REALUM Partners", "zone": "hub", "reward": 180, "xp_reward": 220, "duration_minutes": 120, "required_level": 3, "required_role": "partner"}
    ]
    await db.jobs.delete_many({})
    await db.jobs.insert_many(jobs)
    
    # Seed Courses
    courses = [
        {
            "id": str(uuid.uuid4()), "title": "REALUM Basics", "description": "Learn the fundamentals of the REALUM ecosystem",
            "category": "basics", "difficulty": "beginner", "duration_hours": 2, "xp_reward": 100, "rlm_reward": 50,
            "lessons": [{"id": "l1", "title": "Introduction", "content": "Welcome to REALUM", "duration_minutes": 15}],
            "badge_awarded": None
        },
        {
            "id": str(uuid.uuid4()), "title": "Blockchain Fundamentals", "description": "Understand blockchain technology and Web3",
            "category": "tech", "difficulty": "intermediate", "duration_hours": 5, "xp_reward": 300, "rlm_reward": 150,
            "lessons": [{"id": "l1", "title": "What is Blockchain?", "content": "Introduction to blockchain", "duration_minutes": 30}],
            "badge_awarded": "tech_master"
        },
        {
            "id": str(uuid.uuid4()), "title": "Token Economics", "description": "Learn how token economies work",
            "category": "economics", "difficulty": "intermediate", "duration_hours": 4, "xp_reward": 250, "rlm_reward": 120,
            "lessons": [{"id": "l1", "title": "Token Basics", "content": "Understanding tokens", "duration_minutes": 25}],
            "badge_awarded": "economics_guru"
        },
        {
            "id": str(uuid.uuid4()), "title": "Community Governance", "description": "Participate effectively in DAO governance",
            "category": "civic", "difficulty": "beginner", "duration_hours": 3, "xp_reward": 150, "rlm_reward": 75,
            "lessons": [{"id": "l1", "title": "What is a DAO?", "content": "Introduction to DAOs", "duration_minutes": 20}],
            "badge_awarded": "civic_leader"
        },
        {
            "id": str(uuid.uuid4()), "title": "Digital Art Creation", "description": "Create and sell digital art in the metaverse",
            "category": "creative", "difficulty": "intermediate", "duration_hours": 6, "xp_reward": 350, "rlm_reward": 180,
            "lessons": [{"id": "l1", "title": "Digital Art Tools", "content": "Introduction to tools", "duration_minutes": 35}],
            "badge_awarded": "creative_genius"
        }
    ]
    await db.courses.delete_many({})
    await db.courses.insert_many(courses)
    
    # Seed Proposals
    proposals = [
        {"id": str(uuid.uuid4()), "title": "Increase Learning Rewards", "description": "Proposal to increase XP rewards for completing courses by 20%", "proposer_id": "system", "proposer_name": "REALUM Team", "status": "active", "votes_for": 45, "votes_against": 12, "voters": [], "created_at": now},
        {"id": str(uuid.uuid4()), "title": "New Cultural Events", "description": "Fund weekly virtual cultural events in the Cultural Center", "proposer_id": "system", "proposer_name": "REALUM Team", "status": "active", "votes_for": 32, "votes_against": 8, "voters": [], "created_at": now},
        {"id": str(uuid.uuid4()), "title": "Partner Program Expansion", "description": "Expand the partner program to include more NGOs", "proposer_id": "system", "proposer_name": "REALUM Team", "status": "active", "votes_for": 28, "votes_against": 5, "voters": [], "created_at": now},
        {"id": str(uuid.uuid4()), "title": "Reduce Transaction Fee", "description": "Lower the token burn rate from 2% to 1.5%", "proposer_id": "system", "proposer_name": "REALUM Team", "status": "active", "votes_for": 15, "votes_against": 22, "voters": [], "created_at": now},
        {"id": str(uuid.uuid4()), "title": "Mobile App Development", "description": "Fund development of a native mobile app", "proposer_id": "system", "proposer_name": "REALUM Team", "status": "active", "votes_for": 52, "votes_against": 3, "voters": [], "created_at": now}
    ]
    await db.proposals.delete_many({})
    await db.proposals.insert_many(proposals)
    
    # Seed Marketplace Items
    items = [
        {"id": str(uuid.uuid4()), "title": "Metaverse UI Kit", "description": "Complete UI component library", "category": "design", "price_rlm": 150, "seller_id": "system", "seller_name": "REALUM Shop", "downloads": 45, "rating": 4.8, "created_at": now},
        {"id": str(uuid.uuid4()), "title": "Smart Contract Templates", "description": "Ready-to-use contract templates", "category": "code", "price_rlm": 200, "seller_id": "system", "seller_name": "REALUM Shop", "downloads": 32, "rating": 4.5, "created_at": now},
        {"id": str(uuid.uuid4()), "title": "Business Plan Template", "description": "Complete business plan for metaverse projects", "category": "document", "price_rlm": 80, "seller_id": "system", "seller_name": "REALUM Shop", "downloads": 28, "rating": 4.2, "created_at": now},
        {"id": str(uuid.uuid4()), "title": "3D Avatar Pack", "description": "Collection of customizable 3D avatars", "category": "design", "price_rlm": 300, "seller_id": "system", "seller_name": "REALUM Shop", "downloads": 67, "rating": 4.9, "created_at": now}
    ]
    await db.marketplace.delete_many({})
    await db.marketplace.insert_many(items)
    
    # Seed Projects
    projects = [
        {"id": str(uuid.uuid4()), "title": "Community Garden", "description": "Virtual community garden project", "category": "civic", "creator_id": "system", "creator_name": "REALUM Team", "budget_rlm": 500, "status": "active", "progress": 35, "participants": [], "tasks": [], "created_at": now},
        {"id": str(uuid.uuid4()), "title": "Education Portal", "description": "Build a comprehensive education portal", "category": "education", "creator_id": "system", "creator_name": "REALUM Team", "budget_rlm": 1000, "status": "active", "progress": 60, "participants": [], "tasks": [], "created_at": now},
        {"id": str(uuid.uuid4()), "title": "Art Gallery", "description": "Virtual art gallery for community artists", "category": "creative", "creator_id": "system", "creator_name": "REALUM Team", "budget_rlm": 750, "status": "active", "progress": 20, "participants": [], "tasks": [], "created_at": now}
    ]
    await db.projects.delete_many({})
    await db.projects.insert_many(projects)
    
    return {
        "status": "seeded",
        "zones": len(zones),
        "jobs": len(jobs),
        "courses": len(courses),
        "proposals": len(proposals),
        "marketplace_items": len(items),
        "projects": len(projects)
    }

@router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

@router.get("/status")
async def app_status():
    return {
        "status": "running",
        "version": "2.0.0",
        "refactored": True,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

class SeasonalRewardCreate(BaseModel):
    event_name: str
    description: Optional[str] = None
    start_date: str
    end_date: str
    base_reward_multiplier: float = 2.0
    bonus_tokens: int = 1000
    is_active: bool = True

@router.post("/seasonal-rewards")
async def create_seasonal_reward(
    reward: SeasonalRewardCreate,
    current_user: dict = Depends(admin_required)
):
    """Create a new seasonal reward event (admin only)"""
    seasonal_id = str(uuid.uuid4())

    await db.seasonal_rewards.insert_one({
        "id": seasonal_id,
        "event_name": reward.event_name,
        "description": reward.description,
        "start_date": reward.start_date,
        "end_date": reward.end_date,
        "base_reward_multiplier": reward.base_reward_multiplier,
        "bonus_tokens": reward.bonus_tokens,
        "is_active": reward.is_active,
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc).isoformat()
    })

    return {
        "message": "Seasonal reward created successfully",
        "reward_id": seasonal_id
    }

@router.get("/seasonal-rewards")
async def list_all_seasonal_rewards(current_user: dict = Depends(admin_required)):
    """List all seasonal rewards (admin only)"""
    rewards = await db.seasonal_rewards.find({}, {"_id": 0}).sort("created_at", -1).to_list(50)

    return {"rewards": rewards}

@router.patch("/seasonal-rewards/{reward_id}")
async def update_seasonal_reward(
    reward_id: str,
    is_active: Optional[bool] = None,
    current_user: dict = Depends(admin_required)
):
    """Update seasonal reward status (admin only)"""
    update_data = {}
    if is_active is not None:
        update_data["is_active"] = is_active

    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided")

    result = await db.seasonal_rewards.update_one(
        {"id": reward_id},
        {"$set": update_data}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Seasonal reward not found")

    return {"message": "Seasonal reward updated successfully"}
