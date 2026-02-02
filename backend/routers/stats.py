from fastapi import APIRouter
from ..core.database import db

router = APIRouter(tags=["Stats & Leaderboard"])

@router.get("/leaderboard")
async def get_leaderboard():
    users = await db.users.find(
        {}, 
        {"_id": 0, "password": 0}
    ).sort("xp", -1).limit(50).to_list(50)
    
    leaderboard = []
    for i, user in enumerate(users, 1):
        leaderboard.append({
            "rank": i,
            "id": user["id"],
            "username": user["username"],
            "role": user["role"],
            "xp": user.get("xp", 0),
            "level": user.get("level", 1),
            "realum_balance": user.get("realum_balance", 0),
            "badges_count": len(user.get("badges", []))
        })
    
    return {"leaderboard": leaderboard}

@router.get("/badges")
async def get_all_badges():
    # Static badge definitions
    badges = [
        {"id": "newcomer", "name": "Newcomer", "description": "Welcome to REALUM!", "icon": "🌟", "rarity": "common"},
        {"id": "first_job", "name": "First Job", "description": "Complete your first job", "icon": "💼", "rarity": "common"},
        {"id": "first_vote", "name": "First Vote", "description": "Vote on your first proposal", "icon": "🗳️", "rarity": "common"},
        {"id": "lifelong_learner", "name": "Lifelong Learner", "description": "Enroll in your first course", "icon": "📚", "rarity": "common"},
        {"id": "project_pioneer", "name": "Project Pioneer", "description": "Create your first project", "icon": "🚀", "rarity": "uncommon"},
        {"id": "tech_master", "name": "Tech Master", "description": "Complete the tech course", "icon": "💻", "rarity": "rare"},
        {"id": "civic_leader", "name": "Civic Leader", "description": "Complete the civic course", "icon": "⚖️", "rarity": "rare"},
        {"id": "economics_guru", "name": "Economics Guru", "description": "Complete economics course", "icon": "📈", "rarity": "rare"},
        {"id": "creative_genius", "name": "Creative Genius", "description": "Complete creative course", "icon": "🎨", "rarity": "rare"},
        {"id": "validator", "name": "Quality Validator", "description": "Validate 10 contributions", "icon": "✅", "rarity": "uncommon"},
        {"id": "big_spender", "name": "Big Spender", "description": "Spend 1000 RLM", "icon": "💰", "rarity": "uncommon"},
        {"id": "wealthy", "name": "Wealthy Citizen", "description": "Accumulate 5000 RLM", "icon": "🏆", "rarity": "legendary"},
        {"id": "job_hunter", "name": "Job Hunter", "description": "Complete 10 jobs", "icon": "🎯", "rarity": "uncommon"},
        {"id": "mentor", "name": "Community Mentor", "description": "Help 5 newcomers", "icon": "🤝", "rarity": "rare"},
        {"id": "marketplace_mogul", "name": "Marketplace Mogul", "description": "Sell 10 items", "icon": "🛒", "rarity": "rare"},
        {"id": "dao_champion", "name": "DAO Champion", "description": "Create 5 passed proposals", "icon": "👑", "rarity": "legendary"},
        {"id": "level_10", "name": "Level 10", "description": "Reach level 10", "icon": "⭐", "rarity": "uncommon"},
        {"id": "level_25", "name": "Level 25", "description": "Reach level 25", "icon": "🌟", "rarity": "rare"},
        {"id": "level_50", "name": "Level 50", "description": "Reach level 50", "icon": "💫", "rarity": "legendary"},
        {"id": "early_adopter", "name": "Early Adopter", "description": "Join in the first month", "icon": "🏅", "rarity": "legendary"},
        {"id": "contributor_star", "name": "Star Contributor", "description": "Top 10 in contributions", "icon": "⭐", "rarity": "legendary"},
        {"id": "creator_elite", "name": "Elite Creator", "description": "Create 20+ resources", "icon": "🎖️", "rarity": "legendary"},
        {"id": "partner_network", "name": "Partner Network", "description": "Connect with 10 partners", "icon": "🤝", "rarity": "rare"}
    ]
    return {"badges": badges}

@router.get("/stats")
async def get_platform_stats():
    total_users = await db.users.count_documents({})
    jobs_completed = await db.transactions.count_documents({"description": {"$regex": "^Job completed"}})
    active_proposals = await db.proposals.count_documents({"status": "active"})
    courses_available = await db.courses.count_documents({})
    
    return {
        "total_users": total_users,
        "jobs_completed": jobs_completed,
        "active_proposals": active_proposals,
        "courses_available": courses_available
    }
