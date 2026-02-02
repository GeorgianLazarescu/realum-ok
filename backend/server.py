from fastapi import FastAPI, APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
import jwt
import bcrypt
import random

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Configuration
SECRET_KEY = os.environ.get('SECRET_KEY', 'realum-secret-key-2025')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

security = HTTPBearer(auto_error=False)

# Create the main app
app = FastAPI(title="REALUM API", description="Socio-Economic Simulation Platform")

# Create routers
api_router = APIRouter(prefix="/api")

# ==================== MODELS ====================

class UserRole:
    CITIZEN = "citizen"
    ENTREPRENEUR = "entrepreneur"
    LEADER = "leader"

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    username: str
    role: str = UserRole.CITIZEN

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    email: str
    username: str
    role: str
    wallet_address: Optional[str] = None
    realum_balance: float = 1000.0
    xp: int = 0
    level: int = 1
    badges: List[str] = []
    created_at: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class WalletConnect(BaseModel):
    wallet_address: str

class Transfer(BaseModel):
    to_user_id: str
    amount: float

class Job(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    title: str
    description: str
    company: str
    zone: str
    reward: float
    xp_reward: int
    duration_minutes: int
    required_level: int = 1
    status: str = "available"

class JobApplication(BaseModel):
    job_id: str

class Proposal(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    title: str
    description: str
    proposer_id: str
    proposer_name: str
    votes_for: int = 0
    votes_against: int = 0
    voters: List[str] = []
    status: str = "active"
    created_at: str
    ends_at: str

class CreateProposal(BaseModel):
    title: str
    description: str

class Vote(BaseModel):
    proposal_id: str
    vote: bool  # True = for, False = against

class LeaderboardEntry(BaseModel):
    rank: int
    user_id: str
    username: str
    level: int
    xp: int
    realum_balance: float
    badges_count: int

# ==================== AUTH HELPERS ====================

def create_access_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode = {"user_id": user_id, "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("user_id")
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user_id = verify_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

def calculate_level(xp: int) -> int:
    if xp < 100: return 1
    if xp < 300: return 2
    if xp < 600: return 3
    if xp < 1000: return 4
    if xp < 1500: return 5
    if xp < 2100: return 6
    if xp < 2800: return 7
    if xp < 3600: return 8
    if xp < 4500: return 9
    return 10

# ==================== AUTH ROUTES ====================

@api_router.post("/auth/register", response_model=TokenResponse)
async def register(user_data: UserCreate):
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    existing_username = await db.users.find_one({"username": user_data.username})
    if existing_username:
        raise HTTPException(status_code=400, detail="Username already taken")
    
    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    user_doc = {
        "id": user_id,
        "email": user_data.email,
        "username": user_data.username,
        "password_hash": hash_password(user_data.password),
        "role": user_data.role,
        "wallet_address": None,
        "realum_balance": 1000.0,
        "xp": 0,
        "level": 1,
        "badges": ["newcomer"],
        "active_jobs": [],
        "completed_jobs": [],
        "created_at": now,
        "updated_at": now
    }
    
    await db.users.insert_one(user_doc)
    
    token = create_access_token(user_id)
    user_response = UserResponse(
        id=user_id,
        email=user_data.email,
        username=user_data.username,
        role=user_data.role,
        realum_balance=1000.0,
        xp=0,
        level=1,
        badges=["newcomer"],
        created_at=now
    )
    
    return TokenResponse(access_token=token, user=user_response)

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token(user["id"])
    user_response = UserResponse(
        id=user["id"],
        email=user["email"],
        username=user["username"],
        role=user["role"],
        wallet_address=user.get("wallet_address"),
        realum_balance=user.get("realum_balance", 1000.0),
        xp=user.get("xp", 0),
        level=user.get("level", 1),
        badges=user.get("badges", []),
        created_at=user["created_at"]
    )
    
    return TokenResponse(access_token=token, user=user_response)

@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        username=current_user["username"],
        role=current_user["role"],
        wallet_address=current_user.get("wallet_address"),
        realum_balance=current_user.get("realum_balance", 1000.0),
        xp=current_user.get("xp", 0),
        level=current_user.get("level", 1),
        badges=current_user.get("badges", []),
        created_at=current_user["created_at"]
    )

# ==================== WALLET ROUTES ====================

@api_router.post("/wallet/connect")
async def connect_wallet(data: WalletConnect, current_user: dict = Depends(get_current_user)):
    if not data.wallet_address.startswith("0x") or len(data.wallet_address) != 42:
        raise HTTPException(status_code=400, detail="Invalid wallet address")
    
    existing = await db.users.find_one({"wallet_address": data.wallet_address})
    if existing and existing["id"] != current_user["id"]:
        raise HTTPException(status_code=400, detail="Wallet already connected to another account")
    
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$set": {"wallet_address": data.wallet_address, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Award badge for first wallet connection
    if "web3_pioneer" not in current_user.get("badges", []):
        await db.users.update_one(
            {"id": current_user["id"]},
            {"$addToSet": {"badges": "web3_pioneer"}, "$inc": {"xp": 50}}
        )
    
    return {"status": "connected", "wallet_address": data.wallet_address}

@api_router.get("/wallet/balance")
async def get_balance(current_user: dict = Depends(get_current_user)):
    return {
        "realum_balance": current_user.get("realum_balance", 0),
        "wallet_address": current_user.get("wallet_address")
    }

@api_router.post("/wallet/transfer")
async def transfer_coins(data: Transfer, current_user: dict = Depends(get_current_user)):
    if data.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    
    if current_user.get("realum_balance", 0) < data.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    recipient = await db.users.find_one({"id": data.to_user_id})
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")
    
    # Deduct from sender
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$inc": {"realum_balance": -data.amount}}
    )
    
    # Add to recipient
    await db.users.update_one(
        {"id": data.to_user_id},
        {"$inc": {"realum_balance": data.amount}}
    )
    
    # Log transaction
    tx_id = str(uuid.uuid4())
    await db.transactions.insert_one({
        "id": tx_id,
        "from_user_id": current_user["id"],
        "to_user_id": data.to_user_id,
        "amount": data.amount,
        "type": "transfer",
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    # Award badge for first transfer
    if "first_transaction" not in current_user.get("badges", []):
        await db.users.update_one(
            {"id": current_user["id"]},
            {"$addToSet": {"badges": "first_transaction"}, "$inc": {"xp": 25}}
        )
    
    return {"status": "success", "transaction_id": tx_id, "new_balance": current_user.get("realum_balance", 0) - data.amount}

@api_router.get("/wallet/transactions")
async def get_transactions(current_user: dict = Depends(get_current_user)):
    transactions = await db.transactions.find(
        {"$or": [{"from_user_id": current_user["id"]}, {"to_user_id": current_user["id"]}]},
        {"_id": 0}
    ).sort("created_at", -1).limit(50).to_list(50)
    return {"transactions": transactions}

# ==================== JOBS ROUTES ====================

@api_router.get("/jobs", response_model=List[Job])
async def get_jobs(current_user: dict = Depends(get_current_user)):
    jobs = await db.jobs.find({"status": "available"}, {"_id": 0}).to_list(100)
    user_level = current_user.get("level", 1)
    return [Job(**j) for j in jobs if j.get("required_level", 1) <= user_level]

@api_router.get("/jobs/active")
async def get_active_jobs(current_user: dict = Depends(get_current_user)):
    active_job_ids = current_user.get("active_jobs", [])
    if not active_job_ids:
        return {"jobs": []}
    jobs = await db.jobs.find({"id": {"$in": active_job_ids}}, {"_id": 0}).to_list(100)
    return {"jobs": jobs}

@api_router.post("/jobs/apply")
async def apply_for_job(data: JobApplication, current_user: dict = Depends(get_current_user)):
    job = await db.jobs.find_one({"id": data.job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.get("required_level", 1) > current_user.get("level", 1):
        raise HTTPException(status_code=400, detail="Level requirement not met")
    
    if data.job_id in current_user.get("active_jobs", []):
        raise HTTPException(status_code=400, detail="Already working on this job")
    
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$addToSet": {"active_jobs": data.job_id}}
    )
    
    return {"status": "applied", "job": job}

@api_router.post("/jobs/complete")
async def complete_job(data: JobApplication, current_user: dict = Depends(get_current_user)):
    if data.job_id not in current_user.get("active_jobs", []):
        raise HTTPException(status_code=400, detail="Not working on this job")
    
    job = await db.jobs.find_one({"id": data.job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    new_xp = current_user.get("xp", 0) + job.get("xp_reward", 10)
    new_level = calculate_level(new_xp)
    new_balance = current_user.get("realum_balance", 0) + job.get("reward", 50)
    
    update_data = {
        "$pull": {"active_jobs": data.job_id},
        "$addToSet": {"completed_jobs": data.job_id},
        "$set": {"xp": new_xp, "level": new_level, "realum_balance": new_balance}
    }
    
    # Check for badges
    completed_count = len(current_user.get("completed_jobs", [])) + 1
    badges_to_add = []
    if completed_count == 1:
        badges_to_add.append("first_job")
    if completed_count == 5:
        badges_to_add.append("worker_bee")
    if completed_count == 10:
        badges_to_add.append("job_master")
    
    if badges_to_add:
        update_data["$addToSet"]["badges"] = {"$each": badges_to_add}
    
    await db.users.update_one({"id": current_user["id"]}, update_data)
    
    # Log transaction
    await db.transactions.insert_one({
        "id": str(uuid.uuid4()),
        "from_user_id": "system",
        "to_user_id": current_user["id"],
        "amount": job.get("reward", 50),
        "type": "job_reward",
        "job_id": data.job_id,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "status": "completed",
        "reward": job.get("reward", 50),
        "xp_gained": job.get("xp_reward", 10),
        "new_balance": new_balance,
        "new_xp": new_xp,
        "new_level": new_level,
        "badges_earned": badges_to_add
    }

# ==================== VOTING/DAO ROUTES ====================

@api_router.get("/proposals", response_model=List[Proposal])
async def get_proposals():
    proposals = await db.proposals.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return [Proposal(**p) for p in proposals]

@api_router.post("/proposals", response_model=Proposal)
async def create_proposal(data: CreateProposal, current_user: dict = Depends(get_current_user)):
    if current_user.get("level", 1) < 2:
        raise HTTPException(status_code=400, detail="Must be at least level 2 to create proposals")
    
    proposal_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    ends_at = now + timedelta(days=7)
    
    proposal_doc = {
        "id": proposal_id,
        "title": data.title,
        "description": data.description,
        "proposer_id": current_user["id"],
        "proposer_name": current_user["username"],
        "votes_for": 0,
        "votes_against": 0,
        "voters": [],
        "status": "active",
        "created_at": now.isoformat(),
        "ends_at": ends_at.isoformat()
    }
    
    await db.proposals.insert_one(proposal_doc)
    
    # Award badge for first proposal
    if "civic_voice" not in current_user.get("badges", []):
        await db.users.update_one(
            {"id": current_user["id"]},
            {"$addToSet": {"badges": "civic_voice"}, "$inc": {"xp": 100}}
        )
    
    return Proposal(**proposal_doc)

@api_router.post("/proposals/vote")
async def vote_on_proposal(data: Vote, current_user: dict = Depends(get_current_user)):
    proposal = await db.proposals.find_one({"id": data.proposal_id}, {"_id": 0})
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    if proposal.get("status") != "active":
        raise HTTPException(status_code=400, detail="Proposal is not active")
    
    if current_user["id"] in proposal.get("voters", []):
        raise HTTPException(status_code=400, detail="Already voted on this proposal")
    
    update_field = "votes_for" if data.vote else "votes_against"
    await db.proposals.update_one(
        {"id": data.proposal_id},
        {"$inc": {update_field: 1}, "$addToSet": {"voters": current_user["id"]}}
    )
    
    # Award badge for first vote
    if "voter" not in current_user.get("badges", []):
        await db.users.update_one(
            {"id": current_user["id"]},
            {"$addToSet": {"badges": "voter"}, "$inc": {"xp": 25}}
        )
    
    return {"status": "voted", "vote": "for" if data.vote else "against"}

# ==================== LEADERBOARD ROUTES ====================

@api_router.get("/leaderboard", response_model=List[LeaderboardEntry])
async def get_leaderboard():
    users = await db.users.find(
        {},
        {"_id": 0, "id": 1, "username": 1, "level": 1, "xp": 1, "realum_balance": 1, "badges": 1}
    ).sort("xp", -1).limit(100).to_list(100)
    
    return [
        LeaderboardEntry(
            rank=i + 1,
            user_id=u["id"],
            username=u["username"],
            level=u.get("level", 1),
            xp=u.get("xp", 0),
            realum_balance=u.get("realum_balance", 0),
            badges_count=len(u.get("badges", []))
        )
        for i, u in enumerate(users)
    ]

# ==================== CITY/ZONES ROUTES ====================

class CityZone(BaseModel):
    id: str
    name: str
    description: str
    type: str
    jobs_count: int
    buildings: List[str]
    color: str

@api_router.get("/city/zones", response_model=List[CityZone])
async def get_city_zones():
    zones = await db.zones.find({}, {"_id": 0}).to_list(100)
    if not zones:
        # Return default zones if none exist
        return [
            CityZone(id="downtown", name="Downtown", description="The heart of REALUM - business and finance hub", type="commercial", jobs_count=12, buildings=["City Hall", "REALUM Bank", "Trade Center"], color="#00F0FF"),
            CityZone(id="tech-district", name="Tech District", description="Innovation and technology sector", type="tech", jobs_count=8, buildings=["Tech Hub", "Data Center", "Startup Garage"], color="#FF003C"),
            CityZone(id="industrial", name="Industrial Zone", description="Manufacturing and production facilities", type="industrial", jobs_count=15, buildings=["Factory A", "Warehouse", "Power Plant"], color="#F9F871"),
            CityZone(id="residential", name="Residential Area", description="Living quarters and community spaces", type="residential", jobs_count=5, buildings=["Apartments", "Community Center", "Park"], color="#00FF88"),
            CityZone(id="education", name="Education Campus", description="Learning and research institutions", type="education", jobs_count=6, buildings=["University", "Library", "Research Lab"], color="#9D4EDD"),
            CityZone(id="marketplace", name="Marketplace", description="Trading and commerce district", type="commerce", jobs_count=10, buildings=["Grand Bazaar", "Auction House", "NFT Gallery"], color="#FF6B35")
        ]
    return [CityZone(**z) for z in zones]

# ==================== BADGES ROUTES ====================

class Badge(BaseModel):
    id: str
    name: str
    description: str
    icon: str
    rarity: str

@api_router.get("/badges")
async def get_all_badges():
    return {
        "badges": [
            {"id": "newcomer", "name": "Newcomer", "description": "Welcome to REALUM!", "icon": "🌟", "rarity": "common"},
            {"id": "first_job", "name": "First Job", "description": "Completed your first job", "icon": "💼", "rarity": "common"},
            {"id": "worker_bee", "name": "Worker Bee", "description": "Completed 5 jobs", "icon": "🐝", "rarity": "uncommon"},
            {"id": "job_master", "name": "Job Master", "description": "Completed 10 jobs", "icon": "👔", "rarity": "rare"},
            {"id": "voter", "name": "Voter", "description": "Cast your first vote", "icon": "🗳️", "rarity": "common"},
            {"id": "civic_voice", "name": "Civic Voice", "description": "Created a proposal", "icon": "📢", "rarity": "uncommon"},
            {"id": "first_transaction", "name": "First Transaction", "description": "Made your first transfer", "icon": "💸", "rarity": "common"},
            {"id": "web3_pioneer", "name": "Web3 Pioneer", "description": "Connected a Web3 wallet", "icon": "🔗", "rarity": "uncommon"},
            {"id": "entrepreneur", "name": "Entrepreneur", "description": "Earned 10,000 REALUM", "icon": "💰", "rarity": "rare"},
            {"id": "citizen_elite", "name": "Citizen Elite", "description": "Reached level 10", "icon": "👑", "rarity": "legendary"}
        ]
    }

# ==================== STATS ROUTES ====================

@api_router.get("/stats/platform")
async def get_platform_stats():
    user_count = await db.users.count_documents({})
    total_transactions = await db.transactions.count_documents({})
    active_proposals = await db.proposals.count_documents({"status": "active"})
    total_jobs_completed = await db.users.aggregate([
        {"$project": {"completed_count": {"$size": {"$ifNull": ["$completed_jobs", []]}}}},
        {"$group": {"_id": None, "total": {"$sum": "$completed_count"}}}
    ]).to_list(1)
    
    return {
        "total_users": user_count,
        "total_transactions": total_transactions,
        "active_proposals": active_proposals,
        "jobs_completed": total_jobs_completed[0]["total"] if total_jobs_completed else 0,
        "total_realum_supply": 1000000000
    }

# ==================== SEED DATA ====================

@api_router.post("/seed")
async def seed_data():
    # Seed jobs
    jobs = [
        {"id": "job-1", "title": "Data Entry Clerk", "description": "Process citizen registration forms", "company": "City Hall", "zone": "downtown", "reward": 50, "xp_reward": 15, "duration_minutes": 30, "required_level": 1, "status": "available"},
        {"id": "job-2", "title": "Security Guard", "description": "Patrol the tech district", "company": "SecureTech", "zone": "tech-district", "reward": 75, "xp_reward": 20, "duration_minutes": 60, "required_level": 1, "status": "available"},
        {"id": "job-3", "title": "Factory Worker", "description": "Operate machinery at Factory A", "company": "REALUM Industries", "zone": "industrial", "reward": 100, "xp_reward": 30, "duration_minutes": 120, "required_level": 1, "status": "available"},
        {"id": "job-4", "title": "Junior Developer", "description": "Debug code at the Tech Hub", "company": "CodeForge", "zone": "tech-district", "reward": 150, "xp_reward": 50, "duration_minutes": 90, "required_level": 2, "status": "available"},
        {"id": "job-5", "title": "Bank Teller", "description": "Handle transactions at REALUM Bank", "company": "REALUM Bank", "zone": "downtown", "reward": 80, "xp_reward": 25, "duration_minutes": 45, "required_level": 1, "status": "available"},
        {"id": "job-6", "title": "Research Assistant", "description": "Assist with experiments at Research Lab", "company": "REALUM University", "zone": "education", "reward": 120, "xp_reward": 40, "duration_minutes": 60, "required_level": 2, "status": "available"},
        {"id": "job-7", "title": "Market Vendor", "description": "Sell goods at the Grand Bazaar", "company": "Self-employed", "zone": "marketplace", "reward": 60, "xp_reward": 18, "duration_minutes": 30, "required_level": 1, "status": "available"},
        {"id": "job-8", "title": "Community Manager", "description": "Organize events at Community Center", "company": "City Council", "zone": "residential", "reward": 90, "xp_reward": 35, "duration_minutes": 75, "required_level": 2, "status": "available"},
        {"id": "job-9", "title": "Senior Engineer", "description": "Lead development at Data Center", "company": "REALUM Tech", "zone": "tech-district", "reward": 250, "xp_reward": 80, "duration_minutes": 180, "required_level": 3, "status": "available"},
        {"id": "job-10", "title": "NFT Artist", "description": "Create digital art for NFT Gallery", "company": "CryptoArt Studios", "zone": "marketplace", "reward": 200, "xp_reward": 60, "duration_minutes": 120, "required_level": 2, "status": "available"},
        {"id": "job-11", "title": "Power Plant Operator", "description": "Monitor energy production", "company": "REALUM Energy", "zone": "industrial", "reward": 180, "xp_reward": 55, "duration_minutes": 150, "required_level": 3, "status": "available"},
        {"id": "job-12", "title": "Librarian", "description": "Organize digital archives", "company": "City Library", "zone": "education", "reward": 70, "xp_reward": 22, "duration_minutes": 40, "required_level": 1, "status": "available"}
    ]
    
    for job in jobs:
        await db.jobs.update_one({"id": job["id"]}, {"$set": job}, upsert=True)
    
    # Seed zones
    zones = [
        {"id": "downtown", "name": "Downtown", "description": "The heart of REALUM - business and finance hub", "type": "commercial", "jobs_count": 12, "buildings": ["City Hall", "REALUM Bank", "Trade Center"], "color": "#00F0FF"},
        {"id": "tech-district", "name": "Tech District", "description": "Innovation and technology sector", "type": "tech", "jobs_count": 8, "buildings": ["Tech Hub", "Data Center", "Startup Garage"], "color": "#FF003C"},
        {"id": "industrial", "name": "Industrial Zone", "description": "Manufacturing and production facilities", "type": "industrial", "jobs_count": 15, "buildings": ["Factory A", "Warehouse", "Power Plant"], "color": "#F9F871"},
        {"id": "residential", "name": "Residential Area", "description": "Living quarters and community spaces", "type": "residential", "jobs_count": 5, "buildings": ["Apartments", "Community Center", "Park"], "color": "#00FF88"},
        {"id": "education", "name": "Education Campus", "description": "Learning and research institutions", "type": "education", "jobs_count": 6, "buildings": ["University", "Library", "Research Lab"], "color": "#9D4EDD"},
        {"id": "marketplace", "name": "Marketplace", "description": "Trading and commerce district", "type": "commerce", "jobs_count": 10, "buildings": ["Grand Bazaar", "Auction House", "NFT Gallery"], "color": "#FF6B35"}
    ]
    
    for zone in zones:
        await db.zones.update_one({"id": zone["id"]}, {"$set": zone}, upsert=True)
    
    # Seed proposals
    proposals = [
        {
            "id": "prop-1",
            "title": "Increase Worker Minimum Wage",
            "description": "Proposal to increase the minimum job reward from 50 to 75 REALUM Coin for all entry-level positions.",
            "proposer_id": "system",
            "proposer_name": "City Council",
            "votes_for": 42,
            "votes_against": 18,
            "voters": [],
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "ends_at": (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
        },
        {
            "id": "prop-2",
            "title": "Build New Tech Innovation Center",
            "description": "Allocate 50,000 REALUM from the treasury to construct a new innovation center in the Tech District.",
            "proposer_id": "system",
            "proposer_name": "Tech Committee",
            "votes_for": 67,
            "votes_against": 23,
            "voters": [],
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "ends_at": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
        },
        {
            "id": "prop-3",
            "title": "Environmental Protection Act",
            "description": "Implement green initiatives across all industrial zones to reduce carbon footprint by 30%.",
            "proposer_id": "system",
            "proposer_name": "Green Party",
            "votes_for": 89,
            "votes_against": 11,
            "voters": [],
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "ends_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        }
    ]
    
    for prop in proposals:
        await db.proposals.update_one({"id": prop["id"]}, {"$set": prop}, upsert=True)
    
    return {"status": "seeded", "jobs": len(jobs), "zones": len(zones), "proposals": len(proposals)}

# ==================== ROOT ROUTES ====================

@api_router.get("/")
async def root():
    return {"message": "Welcome to REALUM API", "version": "1.0.0"}

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

# Include router
app.include_router(api_router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
