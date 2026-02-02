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
            # Common Badges (Entry Level)
            {"id": "newcomer", "name": "Newcomer", "description": "Welcome to REALUM! Your journey begins here.", "icon": "🌟", "rarity": "common"},
            {"id": "first_job", "name": "First Salary", "description": "Completed your first job and earned your first REALUM", "icon": "💼", "rarity": "common"},
            {"id": "voter", "name": "Voter", "description": "Cast your first vote in a DAO proposal", "icon": "🗳️", "rarity": "common"},
            {"id": "first_transaction", "name": "First Transaction", "description": "Made your first REALUM transfer", "icon": "💸", "rarity": "common"},
            {"id": "explorer", "name": "Explorer", "description": "Visited all city zones", "icon": "🧭", "rarity": "common"},
            {"id": "debutant", "name": "Debutant", "description": "Completed your first task in the platform", "icon": "🎯", "rarity": "common"},
            
            # Uncommon Badges (Intermediate)
            {"id": "worker_bee", "name": "Worker Bee", "description": "Completed 5 jobs across REALUM", "icon": "🐝", "rarity": "uncommon"},
            {"id": "civic_voice", "name": "Civic Voice", "description": "Created your first DAO proposal", "icon": "📢", "rarity": "uncommon"},
            {"id": "web3_pioneer", "name": "Web3 Pioneer", "description": "Connected a MetaMask wallet", "icon": "🔗", "rarity": "uncommon"},
            {"id": "realum_pioneer", "name": "REALUM Pioneer", "description": "Early adopter badge for founding members", "icon": "🚀", "rarity": "uncommon"},
            {"id": "mentor", "name": "Digital Mentor", "description": "Helped guide new users in the ecosystem", "icon": "🎓", "rarity": "uncommon"},
            {"id": "decident_activ", "name": "Active Decider", "description": "Voted on 10+ proposals", "icon": "⚖️", "rarity": "uncommon"},
            {"id": "beta_contributor", "name": "Beta Contributor", "description": "Participated in beta testing", "icon": "🧪", "rarity": "uncommon"},
            {"id": "wallet_wizard", "name": "Wallet Wizard", "description": "Mastered the REALUM wallet features", "icon": "✨", "rarity": "uncommon"},
            
            # Rare Badges (Advanced)
            {"id": "job_master", "name": "Job Master", "description": "Completed 10+ jobs with excellence", "icon": "👔", "rarity": "rare"},
            {"id": "entrepreneur", "name": "Entrepreneur", "description": "Earned 10,000+ REALUM Coins", "icon": "💰", "rarity": "rare"},
            {"id": "problem_solver", "name": "Problem Solver", "description": "Multiple accepted proposals", "icon": "💡", "rarity": "rare"},
            {"id": "impact_maker", "name": "Impact Maker", "description": "Involvement in critical community sprints", "icon": "⚡", "rarity": "rare"},
            {"id": "dao_educator", "name": "DAO Educator", "description": "Created guides or mentored others in DAO", "icon": "📚", "rarity": "rare"},
            {"id": "code_commando", "name": "Code Commando", "description": "Completed technical tasks in Tech District", "icon": "💻", "rarity": "rare"},
            {"id": "growth_booster", "name": "Growth Booster", "description": "Promoted campaigns and grew the community", "icon": "📈", "rarity": "rare"},
            
            # Epic Badges (Expert)
            {"id": "core_builder", "name": "Core Builder", "description": "Long-term contributor to REALUM ecosystem", "icon": "🏗️", "rarity": "epic"},
            {"id": "validator", "name": "Ethical Validator", "description": "Elected community validator", "icon": "✅", "rarity": "epic"},
            {"id": "ambassador", "name": "Ambassador", "description": "Official REALUM community ambassador", "icon": "🌍", "rarity": "epic"},
            {"id": "dao_architect", "name": "DAO Architect", "description": "Participated in major accepted proposals", "icon": "🏛️", "rarity": "epic"},
            
            # Legendary Badges (Elite)
            {"id": "citizen_elite", "name": "Citizen Elite", "description": "Reached level 10 - maximum citizen status", "icon": "👑", "rarity": "legendary"},
            {"id": "realum_og", "name": "REALUM OG", "description": "Founding member of the REALUM ecosystem", "icon": "🏆", "rarity": "legendary"},
            {"id": "dao_founder", "name": "DAO Founder", "description": "Founding contributor to REALUM DAO", "icon": "⭐", "rarity": "legendary"},
            {"id": "founding_strategist", "name": "Founding Strategist", "description": "Key strategic contributor since inception", "icon": "🎖️", "rarity": "legendary"},
            {"id": "validator_senior", "name": "Senior Validator", "description": "Top-tier community validator status", "icon": "🛡️", "rarity": "legendary"}
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
    # Seed comprehensive jobs from the REALUM document
    jobs = [
        # Downtown Jobs
        {"id": "job-1", "title": "Data Entry Clerk", "description": "Process citizen registration forms at City Hall", "company": "City Hall", "zone": "downtown", "reward": 50, "xp_reward": 15, "duration_minutes": 30, "required_level": 1, "status": "available"},
        {"id": "job-2", "title": "Bank Teller", "description": "Handle REALUM Coin transactions and citizen accounts", "company": "REALUM Bank", "zone": "downtown", "reward": 80, "xp_reward": 25, "duration_minutes": 45, "required_level": 1, "status": "available"},
        {"id": "job-3", "title": "Trade Analyst", "description": "Analyze market trends and economic data", "company": "Trade Center", "zone": "downtown", "reward": 150, "xp_reward": 50, "duration_minutes": 90, "required_level": 2, "status": "available"},
        {"id": "job-4", "title": "City Administrator", "description": "Manage municipal services and citizen requests", "company": "City Hall", "zone": "downtown", "reward": 200, "xp_reward": 70, "duration_minutes": 120, "required_level": 3, "status": "available"},
        
        # Tech District Jobs
        {"id": "job-5", "title": "Junior Developer", "description": "Debug code and fix bugs at the Tech Hub", "company": "CodeForge", "zone": "tech-district", "reward": 150, "xp_reward": 50, "duration_minutes": 90, "required_level": 2, "status": "available"},
        {"id": "job-6", "title": "Senior Engineer", "description": "Lead development projects at the Data Center", "company": "REALUM Tech", "zone": "tech-district", "reward": 300, "xp_reward": 100, "duration_minutes": 180, "required_level": 4, "status": "available"},
        {"id": "job-7", "title": "Security Guard", "description": "Patrol and secure the tech infrastructure", "company": "SecureTech", "zone": "tech-district", "reward": 75, "xp_reward": 20, "duration_minutes": 60, "required_level": 1, "status": "available"},
        {"id": "job-8", "title": "Startup Founder Assistant", "description": "Help entrepreneurs launch their ventures", "company": "Startup Garage", "zone": "tech-district", "reward": 120, "xp_reward": 40, "duration_minutes": 75, "required_level": 2, "status": "available"},
        {"id": "job-9", "title": "Smart Contract Auditor", "description": "Review and audit blockchain smart contracts", "company": "REALUM DAO", "zone": "tech-district", "reward": 250, "xp_reward": 85, "duration_minutes": 150, "required_level": 3, "status": "available"},
        
        # Industrial Zone Jobs
        {"id": "job-10", "title": "Factory Worker", "description": "Operate machinery and production lines", "company": "REALUM Industries", "zone": "industrial", "reward": 100, "xp_reward": 30, "duration_minutes": 120, "required_level": 1, "status": "available"},
        {"id": "job-11", "title": "Warehouse Manager", "description": "Manage inventory and logistics operations", "company": "Central Warehouse", "zone": "industrial", "reward": 140, "xp_reward": 45, "duration_minutes": 90, "required_level": 2, "status": "available"},
        {"id": "job-12", "title": "Power Plant Operator", "description": "Monitor and control energy production systems", "company": "REALUM Energy", "zone": "industrial", "reward": 180, "xp_reward": 60, "duration_minutes": 150, "required_level": 3, "status": "available"},
        {"id": "job-13", "title": "Quality Inspector", "description": "Ensure products meet quality standards", "company": "REALUM Industries", "zone": "industrial", "reward": 110, "xp_reward": 35, "duration_minutes": 60, "required_level": 2, "status": "available"},
        
        # Residential Area Jobs
        {"id": "job-14", "title": "Community Manager", "description": "Organize events and manage community spaces", "company": "Community Center", "zone": "residential", "reward": 90, "xp_reward": 35, "duration_minutes": 75, "required_level": 2, "status": "available"},
        {"id": "job-15", "title": "Park Maintenance", "description": "Maintain green spaces and recreational areas", "company": "Parks Department", "zone": "residential", "reward": 60, "xp_reward": 18, "duration_minutes": 45, "required_level": 1, "status": "available"},
        {"id": "job-16", "title": "Wellness Coach", "description": "Guide residents in health and fitness programs", "company": "Wellness Hub", "zone": "residential", "reward": 100, "xp_reward": 32, "duration_minutes": 60, "required_level": 2, "status": "available"},
        {"id": "job-17", "title": "Social Worker", "description": "Support citizens with social services and guidance", "company": "Community Center", "zone": "residential", "reward": 130, "xp_reward": 45, "duration_minutes": 90, "required_level": 2, "status": "available"},
        
        # Education Campus Jobs
        {"id": "job-18", "title": "Research Assistant", "description": "Assist professors with research experiments", "company": "REALUM University", "zone": "education", "reward": 120, "xp_reward": 40, "duration_minutes": 60, "required_level": 2, "status": "available"},
        {"id": "job-19", "title": "Librarian", "description": "Organize and manage digital archives and resources", "company": "City Library", "zone": "education", "reward": 70, "xp_reward": 22, "duration_minutes": 40, "required_level": 1, "status": "available"},
        {"id": "job-20", "title": "Teaching Assistant", "description": "Support students in virtual learning environments", "company": "REALUM University", "zone": "education", "reward": 95, "xp_reward": 30, "duration_minutes": 60, "required_level": 1, "status": "available"},
        {"id": "job-21", "title": "Lab Technician", "description": "Maintain and operate research equipment", "company": "Research Lab", "zone": "education", "reward": 140, "xp_reward": 48, "duration_minutes": 90, "required_level": 2, "status": "available"},
        {"id": "job-22", "title": "Course Creator", "description": "Design gamified educational content", "company": "REALUM Learn", "zone": "education", "reward": 200, "xp_reward": 70, "duration_minutes": 120, "required_level": 3, "status": "available"},
        
        # Marketplace Jobs
        {"id": "job-23", "title": "Market Vendor", "description": "Sell goods and services at the Grand Bazaar", "company": "Self-employed", "zone": "marketplace", "reward": 60, "xp_reward": 18, "duration_minutes": 30, "required_level": 1, "status": "available"},
        {"id": "job-24", "title": "NFT Artist", "description": "Create and mint digital art for the NFT Gallery", "company": "CryptoArt Studios", "zone": "marketplace", "reward": 200, "xp_reward": 65, "duration_minutes": 120, "required_level": 2, "status": "available"},
        {"id": "job-25", "title": "Auction Manager", "description": "Host and manage digital asset auctions", "company": "Auction House", "zone": "marketplace", "reward": 175, "xp_reward": 55, "duration_minutes": 90, "required_level": 3, "status": "available"},
        {"id": "job-26", "title": "Content Creator", "description": "Produce engaging digital content for the platform", "company": "Creator Network", "zone": "marketplace", "reward": 150, "xp_reward": 50, "duration_minutes": 90, "required_level": 2, "status": "available"},
        {"id": "job-27", "title": "Freelance Designer", "description": "Create UI elements, avatars, and digital assets", "company": "REALUM Creators", "zone": "marketplace", "reward": 180, "xp_reward": 60, "duration_minutes": 100, "required_level": 2, "status": "available"},
        
        # Special/Cross-Zone Jobs
        {"id": "job-28", "title": "DAO Validator", "description": "Verify proposals and ensure governance integrity", "company": "REALUM DAO", "zone": "downtown", "reward": 250, "xp_reward": 90, "duration_minutes": 120, "required_level": 4, "status": "available"},
        {"id": "job-29", "title": "Community Ambassador", "description": "Represent REALUM and onboard new citizens", "company": "Ambassador Hub", "zone": "residential", "reward": 160, "xp_reward": 55, "duration_minutes": 90, "required_level": 3, "status": "available"},
        {"id": "job-30", "title": "Mentor", "description": "Guide new users through the REALUM ecosystem", "company": "Mentorship Network", "zone": "education", "reward": 140, "xp_reward": 50, "duration_minutes": 75, "required_level": 3, "status": "available"}
    ]
    
    for job in jobs:
        await db.jobs.update_one({"id": job["id"]}, {"$set": job}, upsert=True)
    
    # Seed comprehensive zones with thematic buildings from document
    zones = [
        {
            "id": "downtown",
            "name": "Downtown",
            "description": "The administrative and financial heart of REALUM - home to government, banking, and business institutions",
            "type": "commercial",
            "jobs_count": 8,
            "buildings": ["City Hall", "REALUM Bank", "Trade Center", "DAO Council Chamber", "Treasury Building"],
            "color": "#00F0FF",
            "features": ["Virtual Administration", "Simulated Taxes", "Company Registration"]
        },
        {
            "id": "tech-district",
            "name": "Tech District",
            "description": "Innovation and technology hub - startups, data centers, and blockchain infrastructure",
            "type": "tech",
            "jobs_count": 10,
            "buildings": ["Tech Hub", "Data Center", "Startup Garage", "AI Research Center", "Smart Contract Lab"],
            "color": "#FF003C",
            "features": ["Smart Contracts", "AI Assistants", "Blockchain Integration"]
        },
        {
            "id": "industrial",
            "name": "Industrial Zone",
            "description": "Manufacturing, production, and energy generation facilities powering the REALUM economy",
            "type": "industrial",
            "jobs_count": 8,
            "buildings": ["Factory Alpha", "Central Warehouse", "Power Plant", "Logistics Hub", "Recycling Center"],
            "color": "#F9F871",
            "features": ["Production Economy", "Supply Chain", "Energy Grid"]
        },
        {
            "id": "residential",
            "name": "Residential District",
            "description": "Living quarters, wellness centers, and community spaces for REALUM citizens",
            "type": "residential",
            "jobs_count": 8,
            "buildings": ["Citizen Apartments", "Community Center", "Central Park", "Wellness Hub", "Ambassador Hub"],
            "color": "#00FF88",
            "features": ["Social Connections", "Health & Wellness", "Community Events"]
        },
        {
            "id": "education",
            "name": "Education Campus",
            "description": "Virtual universities, libraries, and research institutions for learning and skill development",
            "type": "education",
            "jobs_count": 10,
            "buildings": ["REALUM University", "City Library", "Research Lab", "Virtual Academy", "Skill Center"],
            "color": "#9D4EDD",
            "features": ["Gamified Learning", "Skill Certification", "Research Projects"]
        },
        {
            "id": "marketplace",
            "name": "Marketplace",
            "description": "Digital commerce, NFT galleries, and creator economy district for trading and creativity",
            "type": "commerce",
            "jobs_count": 10,
            "buildings": ["Grand Bazaar", "NFT Gallery", "Auction House", "Creator Studio", "Digital Mall"],
            "color": "#FF6B35",
            "features": ["NFT Trading", "Digital Assets", "Creator Economy"]
        },
        {
            "id": "cultural",
            "name": "Cultural Quarter",
            "description": "Museums, exhibition halls, and virtual event spaces celebrating art and heritage",
            "type": "cultural",
            "jobs_count": 6,
            "buildings": ["Digital Museum", "Exhibition Hall", "Concert Arena", "Art Gallery", "Heritage Center"],
            "color": "#E040FB",
            "features": ["Virtual Events", "Digital Art", "Cultural NFTs"]
        },
        {
            "id": "civic",
            "name": "Civic Center",
            "description": "Citizen engagement, voting facilities, and participatory governance spaces",
            "type": "civic",
            "jobs_count": 5,
            "buildings": ["Agora Forum", "Voting Center", "Citizen Bureau", "Ethics Council", "Public Square"],
            "color": "#40C4FF",
            "features": ["DAO Governance", "Public Voting", "Civic Participation"]
        }
    ]
    
    for zone in zones:
        await db.zones.update_one({"id": zone["id"]}, {"$set": zone}, upsert=True)
    
    # Seed comprehensive proposals from document themes
    proposals = [
        {
            "id": "prop-1",
            "title": "Increase Worker Minimum Wage",
            "description": "Proposal to increase the minimum job reward from 50 to 75 REALUM Coin for all entry-level positions, ensuring fair compensation for all citizens.",
            "proposer_id": "system",
            "proposer_name": "City Council",
            "votes_for": 142,
            "votes_against": 38,
            "voters": [],
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "ends_at": (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
        },
        {
            "id": "prop-2",
            "title": "Build New Tech Innovation Center",
            "description": "Allocate 50,000 REALUM from the treasury to construct a new innovation center in the Tech District, creating 20 new jobs and boosting technological advancement.",
            "proposer_id": "system",
            "proposer_name": "Tech Committee",
            "votes_for": 167,
            "votes_against": 43,
            "voters": [],
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "ends_at": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
        },
        {
            "id": "prop-3",
            "title": "Environmental Protection Act",
            "description": "Implement green initiatives across all industrial zones to reduce carbon footprint by 30%. Includes carbon token rewards for eco-friendly activities.",
            "proposer_id": "system",
            "proposer_name": "Green Party",
            "votes_for": 189,
            "votes_against": 21,
            "voters": [],
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "ends_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        },
        {
            "id": "prop-4",
            "title": "REALUM Learn Expansion",
            "description": "Fund the creation of 50 new gamified courses across technology, economics, and civic education. All course completions will award badges convertible to NFTs.",
            "proposer_id": "system",
            "proposer_name": "Education Board",
            "votes_for": 234,
            "votes_against": 12,
            "voters": [],
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "ends_at": (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
        },
        {
            "id": "prop-5",
            "title": "Quadratic Voting Implementation",
            "description": "Introduce quadratic voting for strategic decisions and grant allocation, giving more weight to passionate voters while preventing plutocracy.",
            "proposer_id": "system",
            "proposer_name": "DAO Governance Team",
            "votes_for": 156,
            "votes_against": 67,
            "voters": [],
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "ends_at": (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()
        },
        {
            "id": "prop-6",
            "title": "Micro-Grant Program Launch",
            "description": "Establish a 100,000 REALUM fund for community micro-grants. Citizens can apply for grants up to 1,000 REALUM for small community initiatives and projects.",
            "proposer_id": "system",
            "proposer_name": "Community Development",
            "votes_for": 198,
            "votes_against": 34,
            "voters": [],
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "ends_at": (datetime.now(timezone.utc) + timedelta(days=8)).isoformat()
        },
        {
            "id": "prop-7",
            "title": "Cultural Heritage NFT Collection",
            "description": "Create an official REALUM cultural heritage NFT collection, tokenizing art, traditions, and historical monuments with proceeds supporting local artists.",
            "proposer_id": "system",
            "proposer_name": "Cultural Committee",
            "votes_for": 145,
            "votes_against": 28,
            "voters": [],
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "ends_at": (datetime.now(timezone.utc) + timedelta(days=6)).isoformat()
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
