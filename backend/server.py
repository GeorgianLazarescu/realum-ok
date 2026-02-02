from fastapi import FastAPI, APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
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

# Token Economy Configuration
TOKEN_BURN_RATE = 0.02  # 2% of transactions get burned
INITIAL_BALANCE = 1000.0

security = HTTPBearer(auto_error=False)

# Create the main app
app = FastAPI(title="REALUM API", description="Educational & Economic Metaverse Platform")

# Create routers
api_router = APIRouter(prefix="/api")

# ==================== MODELS ====================

class UserRole:
    CREATOR = "creator"           # Uploads resources, designs, and ideas
    CONTRIBUTOR = "contributor"   # Completes tasks and joins projects
    EVALUATOR = "evaluator"       # Validates quality and gives feedback
    PARTNER = "partner"           # External partner, posts missions and pays with RLM
    CITIZEN = "citizen"           # Default role

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
    realum_balance: float = INITIAL_BALANCE
    xp: int = 0
    level: int = 1
    badges: List[str] = []
    skills: List[str] = []
    courses_completed: List[str] = []
    projects_joined: List[str] = []
    created_at: str
    avatar_url: Optional[str] = None
    language: str = "en"

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class WalletConnect(BaseModel):
    wallet_address: str

class Transfer(BaseModel):
    to_user_id: str
    amount: float
    reason: Optional[str] = None

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
    required_role: Optional[str] = None
    skills_required: List[str] = []
    status: str = "available"
    creator_id: Optional[str] = None

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

class ProposalCreate(BaseModel):
    title: str
    description: str

class VoteRequest(BaseModel):
    vote_type: str  # "for" or "against"

class CityZone(BaseModel):
    id: str
    name: str
    description: str
    type: str
    jobs_count: int
    buildings: List[str]
    color: str
    features: List[str] = []
    position_3d: Dict[str, float] = {}

# ==================== NEW MODELS FOR ENHANCED FEATURES ====================

class Course(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    title: str
    description: str
    category: str  # tech, economics, civic, creative, language
    difficulty: str  # beginner, intermediate, advanced
    duration_hours: int
    xp_reward: int
    rlm_reward: float
    skills_gained: List[str] = []
    lessons: List[Dict[str, Any]] = []
    quiz_questions: List[Dict[str, Any]] = []
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    enrolled_count: int = 0
    completion_rate: float = 0

class CourseEnrollment(BaseModel):
    course_id: str

class LessonProgress(BaseModel):
    course_id: str
    lesson_id: str
    completed: bool = True
    score: Optional[int] = None

class Project(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    title: str
    description: str
    creator_id: str
    creator_name: str
    category: str
    status: str = "active"  # active, completed, archived
    budget_rlm: float
    participants: List[str] = []
    tasks: List[Dict[str, Any]] = []
    progress: float = 0
    position_3d: Dict[str, float] = {}  # For 3D map
    island_type: str = "default"  # For 3D visualization
    created_at: str

class ProjectCreate(BaseModel):
    title: str
    description: str
    category: str
    budget_rlm: float

class MarketplaceItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    title: str
    description: str
    category: str  # design, code, document, template, course, service
    price_rlm: float
    seller_id: str
    seller_name: str
    file_url: Optional[str] = None
    preview_url: Optional[str] = None
    downloads: int = 0
    rating: float = 0
    reviews: List[Dict[str, Any]] = []
    status: str = "available"
    created_at: str

class MarketplaceItemCreate(BaseModel):
    title: str
    description: str
    category: str
    price_rlm: float
    file_url: Optional[str] = None
    preview_url: Optional[str] = None

class ValidationRequest(BaseModel):
    item_type: str  # task, project, marketplace_item
    item_id: str
    rating: int  # 1-5
    feedback: str

class TokenBurnEvent(BaseModel):
    amount: float
    reason: str
    timestamp: str

# ==================== AUTH HELPERS ====================

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_access_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {"user_id": user_id, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        user = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def calculate_level(xp: int) -> int:
    """Level up every 500 XP"""
    return max(1, (xp // 500) + 1)

async def burn_tokens(amount: float, reason: str):
    """Burn tokens and record the event"""
    burn_event = {
        "id": str(uuid.uuid4()),
        "amount": amount,
        "reason": reason,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    await db.token_burns.insert_one(burn_event)
    # Update total burned
    await db.platform_stats.update_one(
        {"id": "main"},
        {"$inc": {"total_tokens_burned": amount}},
        upsert=True
    )
    return burn_event

async def award_badge(user_id: str, badge_id: str):
    """Award a badge to a user if they don't have it"""
    await db.users.update_one(
        {"id": user_id, "badges": {"$ne": badge_id}},
        {"$addToSet": {"badges": badge_id}}
    )

# ==================== AUTH ENDPOINTS ====================

@api_router.post("/auth/register", response_model=TokenResponse)
async def register(user_data: UserCreate):
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    # Assign initial badges based on role
    initial_badges = ["newcomer"]
    if user_data.role == UserRole.CREATOR:
        initial_badges.append("creator_starter")
    elif user_data.role == UserRole.EVALUATOR:
        initial_badges.append("quality_guardian")
    elif user_data.role == UserRole.PARTNER:
        initial_badges.append("partner_pioneer")
    
    user = {
        "id": user_id,
        "email": user_data.email,
        "username": user_data.username,
        "password": hash_password(user_data.password),
        "role": user_data.role,
        "wallet_address": None,
        "realum_balance": INITIAL_BALANCE,
        "xp": 0,
        "level": 1,
        "badges": initial_badges,
        "skills": [],
        "courses_completed": [],
        "projects_joined": [],
        "created_at": now,
        "avatar_url": None,
        "language": "en"
    }
    
    await db.users.insert_one(user)
    
    # Create wallet
    await db.wallets.insert_one({
        "user_id": user_id,
        "balance": INITIAL_BALANCE,
        "transactions": [{
            "id": str(uuid.uuid4()),
            "type": "credit",
            "amount": INITIAL_BALANCE,
            "description": "Welcome bonus",
            "timestamp": now
        }]
    })
    
    token = create_access_token(user_id)
    user.pop("password")
    user.pop("_id", None)
    
    return TokenResponse(access_token=token, user=UserResponse(**user))

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email})
    if not user or not verify_password(credentials.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token(user["id"])
    user.pop("password")
    user.pop("_id", None)
    
    return TokenResponse(access_token=token, user=UserResponse(**user))

@api_router.get("/auth/me", response_model=UserResponse)
async def get_current_user_profile(current_user: dict = Depends(get_current_user)):
    return UserResponse(**current_user)

@api_router.put("/auth/profile")
async def update_profile(
    updates: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    allowed_fields = ["username", "avatar_url", "language", "skills"]
    filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}
    
    if filtered_updates:
        await db.users.update_one(
            {"id": current_user["id"]},
            {"$set": filtered_updates}
        )
    
    updated_user = await db.users.find_one({"id": current_user["id"]}, {"_id": 0, "password": 0})
    return updated_user

# ==================== WALLET & TOKEN ECONOMY ====================

@api_router.get("/wallet")
async def get_wallet(current_user: dict = Depends(get_current_user)):
    wallet = await db.wallets.find_one({"user_id": current_user["id"]}, {"_id": 0})
    if not wallet:
        wallet = {
            "user_id": current_user["id"],
            "balance": current_user.get("realum_balance", INITIAL_BALANCE),
            "transactions": []
        }
    return wallet

@api_router.get("/wallet/transactions")
async def get_transactions(current_user: dict = Depends(get_current_user)):
    wallet = await db.wallets.find_one({"user_id": current_user["id"]}, {"_id": 0})
    if not wallet:
        return {"transactions": []}
    return {"transactions": wallet.get("transactions", [])[-50:]}  # Last 50 transactions

@api_router.post("/wallet/connect")
async def connect_wallet(data: WalletConnect, current_user: dict = Depends(get_current_user)):
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$set": {"wallet_address": data.wallet_address}}
    )
    await award_badge(current_user["id"], "web3_pioneer")
    return {"status": "connected", "wallet_address": data.wallet_address}

@api_router.post("/wallet/transfer")
async def transfer_tokens(data: Transfer, current_user: dict = Depends(get_current_user)):
    if data.amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid amount")
    
    if current_user["realum_balance"] < data.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    recipient = await db.users.find_one({"id": data.to_user_id})
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")
    
    # Calculate burn amount (token recycling)
    burn_amount = data.amount * TOKEN_BURN_RATE
    transfer_amount = data.amount - burn_amount
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Deduct from sender
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$inc": {"realum_balance": -data.amount}}
    )
    
    # Credit to recipient (minus burn)
    await db.users.update_one(
        {"id": data.to_user_id},
        {"$inc": {"realum_balance": transfer_amount}}
    )
    
    # Record transactions
    sender_tx = {
        "id": str(uuid.uuid4()),
        "type": "debit",
        "amount": data.amount,
        "to_user": recipient["username"],
        "description": data.reason or "Transfer",
        "burned": burn_amount,
        "timestamp": now
    }
    
    recipient_tx = {
        "id": str(uuid.uuid4()),
        "type": "credit",
        "amount": transfer_amount,
        "from_user": current_user["username"],
        "description": data.reason or "Transfer received",
        "timestamp": now
    }
    
    await db.wallets.update_one(
        {"user_id": current_user["id"]},
        {"$push": {"transactions": sender_tx}},
        upsert=True
    )
    
    await db.wallets.update_one(
        {"user_id": data.to_user_id},
        {"$push": {"transactions": recipient_tx}},
        upsert=True
    )
    
    # Burn tokens
    if burn_amount > 0:
        await burn_tokens(burn_amount, f"Transfer tax: {current_user['username']} -> {recipient['username']}")
    
    # Award badges
    await award_badge(current_user["id"], "first_transaction")
    
    return {
        "status": "success",
        "amount_sent": data.amount,
        "amount_received": transfer_amount,
        "amount_burned": burn_amount,
        "new_balance": current_user["realum_balance"] - data.amount
    }

@api_router.get("/token/stats")
async def get_token_stats():
    stats = await db.platform_stats.find_one({"id": "main"}, {"_id": 0})
    total_supply = await db.users.aggregate([
        {"$group": {"_id": None, "total": {"$sum": "$realum_balance"}}}
    ]).to_list(1)
    
    return {
        "total_supply": total_supply[0]["total"] if total_supply else 0,
        "total_burned": stats.get("total_tokens_burned", 0) if stats else 0,
        "burn_rate": TOKEN_BURN_RATE * 100,
        "initial_allocation": INITIAL_BALANCE
    }

@api_router.get("/token/burns")
async def get_burn_history():
    burns = await db.token_burns.find({}, {"_id": 0}).sort("timestamp", -1).to_list(50)
    return {"burns": burns}

# ==================== JOBS & MARKETPLACE ====================

@api_router.get("/jobs", response_model=List[Job])
async def get_jobs(zone: Optional[str] = None, role: Optional[str] = None):
    query = {"status": "available"}
    if zone:
        query["zone"] = zone
    if role:
        query["required_role"] = role
    
    jobs = await db.jobs.find(query, {"_id": 0}).to_list(100)
    return [Job(**j) for j in jobs]

@api_router.post("/jobs/{job_id}/apply")
async def apply_for_job(job_id: str, current_user: dict = Depends(get_current_user)):
    job = await db.jobs.find_one({"id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check if user already has this job active
    existing_active = await db.active_jobs.find_one({
        "job_id": job_id,
        "user_id": current_user["id"],
        "status": "in_progress"
    })
    if existing_active:
        raise HTTPException(status_code=400, detail="You already have this job in progress")
    
    if job.get("required_level", 1) > current_user.get("level", 1):
        raise HTTPException(status_code=400, detail=f"Requires level {job['required_level']}")
    
    if job.get("required_role") and job["required_role"] != current_user["role"]:
        raise HTTPException(status_code=400, detail=f"Requires {job['required_role']} role")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Create active job for this user
    await db.active_jobs.insert_one({
        "id": str(uuid.uuid4()),
        "job_id": job_id,
        "user_id": current_user["id"],
        "started_at": now,
        "status": "in_progress"
    })
    
    # Jobs are reusable - don't change job status to in_progress
    # This allows multiple users to take the same job
    
    return {"status": "applied", "job": job}

@api_router.get("/jobs/active")
async def get_active_jobs(current_user: dict = Depends(get_current_user)):
    active = await db.active_jobs.find(
        {"user_id": current_user["id"], "status": "in_progress"},
        {"_id": 0}
    ).to_list(10)
    
    result = []
    for aj in active:
        job = await db.jobs.find_one({"id": aj["job_id"]}, {"_id": 0})
        if job:
            result.append({**aj, "job": job})
    
    return {"active_jobs": result}

@api_router.post("/jobs/{job_id}/complete")
async def complete_job(job_id: str, current_user: dict = Depends(get_current_user)):
    active_job = await db.active_jobs.find_one({
        "job_id": job_id,
        "user_id": current_user["id"],
        "status": "in_progress"
    })
    
    if not active_job:
        raise HTTPException(status_code=404, detail="No active job found")
    
    job = await db.jobs.find_one({"id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Calculate rewards with potential bonus for role match
    reward = job["reward"]
    xp_reward = job["xp_reward"]
    
    if job.get("required_role") == current_user["role"]:
        reward *= 1.1  # 10% bonus for role match
        xp_reward = int(xp_reward * 1.1)
    
    # Update user
    new_xp = current_user.get("xp", 0) + xp_reward
    new_level = calculate_level(new_xp)
    new_balance = current_user.get("realum_balance", 0) + reward
    
    await db.users.update_one(
        {"id": current_user["id"]},
        {
            "$set": {"xp": new_xp, "level": new_level, "realum_balance": new_balance},
            "$inc": {"jobs_completed": 1}
        }
    )
    
    # Add skills from job
    if job.get("skills_required"):
        await db.users.update_one(
            {"id": current_user["id"]},
            {"$addToSet": {"skills": {"$each": job["skills_required"]}}}
        )
    
    # Record transaction
    await db.wallets.update_one(
        {"user_id": current_user["id"]},
        {"$push": {"transactions": {
            "id": str(uuid.uuid4()),
            "type": "credit",
            "amount": reward,
            "description": f"Job completed: {job['title']}",
            "timestamp": now
        }}},
        upsert=True
    )
    
    # Update job and active job
    # Jobs remain available for other users - only update the active_job record
    await db.active_jobs.update_one(
        {"job_id": job_id, "user_id": current_user["id"], "status": "in_progress"},
        {"$set": {"status": "completed", "completed_at": now}}
    )
    
    # Award badges
    await award_badge(current_user["id"], "first_job")
    
    jobs_done = await db.active_jobs.count_documents({
        "user_id": current_user["id"],
        "status": "completed"
    })
    
    if jobs_done >= 5:
        await award_badge(current_user["id"], "worker_bee")
    if jobs_done >= 10:
        await award_badge(current_user["id"], "job_master")
    
    # Check for level-up badge
    if new_level >= 10:
        await award_badge(current_user["id"], "citizen_elite")
    
    return {
        "status": "completed",
        "reward": reward,
        "xp_gained": xp_reward,
        "new_level": new_level,
        "new_balance": new_balance,
        "level_up": new_level > current_user.get("level", 1)
    }

# ==================== MARKETPLACE ====================

@api_router.get("/marketplace")
async def get_marketplace_items(category: Optional[str] = None):
    query = {"status": "available"}
    if category:
        query["category"] = category
    
    items = await db.marketplace.find(query, {"_id": 0}).to_list(100)
    return {"items": items}

@api_router.post("/marketplace")
async def create_marketplace_item(
    item: MarketplaceItemCreate,
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] not in [UserRole.CREATOR, UserRole.PARTNER]:
        raise HTTPException(status_code=403, detail="Only Creators or Partners can list items")
    
    now = datetime.now(timezone.utc).isoformat()
    
    new_item = {
        "id": str(uuid.uuid4()),
        "title": item.title,
        "description": item.description,
        "category": item.category,
        "price_rlm": item.price_rlm,
        "seller_id": current_user["id"],
        "seller_name": current_user["username"],
        "file_url": item.file_url,
        "preview_url": item.preview_url,
        "downloads": 0,
        "rating": 0,
        "reviews": [],
        "status": "available",
        "created_at": now
    }
    
    await db.marketplace.insert_one(new_item)
    await award_badge(current_user["id"], "creator_first_item")
    
    return {"status": "created", "item": {k: v for k, v in new_item.items() if k != "_id"}}

@api_router.post("/marketplace/{item_id}/purchase")
async def purchase_item(item_id: str, current_user: dict = Depends(get_current_user)):
    item = await db.marketplace.find_one({"id": item_id})
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    if item["seller_id"] == current_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot purchase own item")
    
    if current_user["realum_balance"] < item["price_rlm"]:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Calculate burn
    burn_amount = item["price_rlm"] * TOKEN_BURN_RATE
    seller_amount = item["price_rlm"] - burn_amount
    
    # Transfer funds
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$inc": {"realum_balance": -item["price_rlm"]}}
    )
    
    await db.users.update_one(
        {"id": item["seller_id"]},
        {"$inc": {"realum_balance": seller_amount}}
    )
    
    # Record transactions
    await db.wallets.update_one(
        {"user_id": current_user["id"]},
        {"$push": {"transactions": {
            "id": str(uuid.uuid4()),
            "type": "debit",
            "amount": item["price_rlm"],
            "description": f"Purchased: {item['title']}",
            "timestamp": now
        }}},
        upsert=True
    )
    
    await db.wallets.update_one(
        {"user_id": item["seller_id"]},
        {"$push": {"transactions": {
            "id": str(uuid.uuid4()),
            "type": "credit",
            "amount": seller_amount,
            "from_user": current_user["username"],
            "description": f"Sold: {item['title']}",
            "timestamp": now
        }}},
        upsert=True
    )
    
    # Update item stats
    await db.marketplace.update_one(
        {"id": item_id},
        {"$inc": {"downloads": 1}}
    )
    
    # Burn tokens
    if burn_amount > 0:
        await burn_tokens(burn_amount, f"Marketplace sale: {item['title']}")
    
    return {
        "status": "purchased",
        "item": item["title"],
        "amount_paid": item["price_rlm"],
        "seller_received": seller_amount,
        "amount_burned": burn_amount
    }

# ==================== LEARNING ZONE ====================

@api_router.get("/courses")
async def get_courses(category: Optional[str] = None, difficulty: Optional[str] = None):
    query = {}
    if category:
        query["category"] = category
    if difficulty:
        query["difficulty"] = difficulty
    
    courses = await db.courses.find(query, {"_id": 0}).to_list(100)
    return {"courses": courses}

@api_router.get("/courses/{course_id}")
async def get_course(course_id: str, current_user: dict = Depends(get_current_user)):
    course = await db.courses.find_one({"id": course_id}, {"_id": 0})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Get user's progress
    enrollment = await db.course_enrollments.find_one({
        "user_id": current_user["id"],
        "course_id": course_id
    }, {"_id": 0})
    
    return {
        "course": course,
        "enrollment": enrollment
    }

@api_router.post("/courses/{course_id}/enroll")
async def enroll_in_course(course_id: str, current_user: dict = Depends(get_current_user)):
    course = await db.courses.find_one({"id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    existing = await db.course_enrollments.find_one({
        "user_id": current_user["id"],
        "course_id": course_id
    })
    
    if existing:
        raise HTTPException(status_code=400, detail="Already enrolled")
    
    now = datetime.now(timezone.utc).isoformat()
    
    enrollment = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "course_id": course_id,
        "progress": 0,
        "lessons_completed": [],
        "quiz_scores": [],
        "started_at": now,
        "completed_at": None
    }
    
    await db.course_enrollments.insert_one(enrollment)
    await db.courses.update_one({"id": course_id}, {"$inc": {"enrolled_count": 1}})
    
    return {"status": "enrolled", "course": course["title"]}

@api_router.post("/courses/{course_id}/lesson/{lesson_id}/complete")
async def complete_lesson(
    course_id: str,
    lesson_id: str,
    score: Optional[int] = None,
    current_user: dict = Depends(get_current_user)
):
    enrollment = await db.course_enrollments.find_one({
        "user_id": current_user["id"],
        "course_id": course_id
    })
    
    if not enrollment:
        raise HTTPException(status_code=400, detail="Not enrolled in this course")
    
    course = await db.courses.find_one({"id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Update lesson completion
    await db.course_enrollments.update_one(
        {"user_id": current_user["id"], "course_id": course_id},
        {
            "$addToSet": {"lessons_completed": lesson_id},
            "$push": {"quiz_scores": {"lesson_id": lesson_id, "score": score, "completed_at": now}} if score else {}
        }
    )
    
    # Calculate progress
    total_lessons = len(course.get("lessons", []))
    completed_lessons = len(enrollment.get("lessons_completed", [])) + 1
    progress = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 100
    
    await db.course_enrollments.update_one(
        {"user_id": current_user["id"], "course_id": course_id},
        {"$set": {"progress": progress}}
    )
    
    # Check if course is complete
    course_completed = progress >= 100
    rewards = {"xp": 0, "rlm": 0, "skills": []}
    
    if course_completed:
        rewards["xp"] = course.get("xp_reward", 50)
        rewards["rlm"] = course.get("rlm_reward", 25)
        rewards["skills"] = course.get("skills_gained", [])
        
        # Award rewards
        new_xp = current_user.get("xp", 0) + rewards["xp"]
        new_level = calculate_level(new_xp)
        
        await db.users.update_one(
            {"id": current_user["id"]},
            {
                "$set": {"xp": new_xp, "level": new_level},
                "$inc": {"realum_balance": rewards["rlm"]},
                "$addToSet": {
                    "courses_completed": course_id,
                    "skills": {"$each": rewards["skills"]}
                }
            }
        )
        
        await db.course_enrollments.update_one(
            {"user_id": current_user["id"], "course_id": course_id},
            {"$set": {"completed_at": now, "progress": 100}}
        )
        
        # Award badges
        await award_badge(current_user["id"], "first_course")
        
        courses_done = len(current_user.get("courses_completed", [])) + 1
        if courses_done >= 5:
            await award_badge(current_user["id"], "knowledge_seeker")
        if courses_done >= 10:
            await award_badge(current_user["id"], "master_learner")
    
    return {
        "status": "completed",
        "progress": progress,
        "course_completed": course_completed,
        "rewards": rewards if course_completed else None
    }

# ==================== PROJECTS ====================

@api_router.get("/projects")
async def get_projects(status: Optional[str] = None, category: Optional[str] = None):
    query = {}
    if status:
        query["status"] = status
    if category:
        query["category"] = category
    
    projects = await db.projects.find(query, {"_id": 0}).to_list(100)
    return {"projects": projects}

@api_router.get("/projects/{project_id}")
async def get_project(project_id: str):
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@api_router.post("/projects")
async def create_project(
    project: ProjectCreate,
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] not in [UserRole.CREATOR, UserRole.PARTNER]:
        raise HTTPException(status_code=403, detail="Only Creators or Partners can create projects")
    
    if current_user["realum_balance"] < project.budget_rlm:
        raise HTTPException(status_code=400, detail="Insufficient balance for project budget")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Generate 3D position for the project island
    existing_projects = await db.projects.count_documents({})
    angle = (existing_projects * 45) % 360
    radius = 50 + (existing_projects // 8) * 30
    
    import math
    position_3d = {
        "x": radius * math.cos(math.radians(angle)),
        "y": 0,
        "z": radius * math.sin(math.radians(angle))
    }
    
    island_types = ["default", "tech", "creative", "education", "commerce", "civic"]
    
    new_project = {
        "id": str(uuid.uuid4()),
        "title": project.title,
        "description": project.description,
        "creator_id": current_user["id"],
        "creator_name": current_user["username"],
        "category": project.category,
        "status": "active",
        "budget_rlm": project.budget_rlm,
        "participants": [current_user["id"]],
        "tasks": [],
        "progress": 0,
        "position_3d": position_3d,
        "island_type": island_types[existing_projects % len(island_types)],
        "created_at": now
    }
    
    # Deduct budget from creator
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$inc": {"realum_balance": -project.budget_rlm}}
    )
    
    await db.projects.insert_one(new_project)
    
    # Award badges
    await award_badge(current_user["id"], "project_creator")
    
    return {"status": "created", "project": {k: v for k, v in new_project.items() if k != "_id"}}

@api_router.post("/projects/{project_id}/join")
async def join_project(project_id: str, current_user: dict = Depends(get_current_user)):
    project = await db.projects.find_one({"id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if current_user["id"] in project.get("participants", []):
        raise HTTPException(status_code=400, detail="Already a participant")
    
    await db.projects.update_one(
        {"id": project_id},
        {"$addToSet": {"participants": current_user["id"]}}
    )
    
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$addToSet": {"projects_joined": project_id}}
    )
    
    return {"status": "joined", "project": project["title"]}

@api_router.post("/projects/{project_id}/task")
async def add_project_task(
    project_id: str,
    task: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    project = await db.projects.find_one({"id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project["creator_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Only project creator can add tasks")
    
    new_task = {
        "id": str(uuid.uuid4()),
        "title": task.get("title", "Task"),
        "description": task.get("description", ""),
        "reward_rlm": task.get("reward_rlm", 10),
        "xp_reward": task.get("xp_reward", 20),
        "status": "open",
        "assigned_to": None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.projects.update_one(
        {"id": project_id},
        {"$push": {"tasks": new_task}}
    )
    
    return {"status": "created", "task": new_task}

@api_router.post("/projects/{project_id}/task/{task_id}/complete")
async def complete_project_task(
    project_id: str,
    task_id: str,
    current_user: dict = Depends(get_current_user)
):
    project = await db.projects.find_one({"id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    task = None
    for t in project.get("tasks", []):
        if t["id"] == task_id:
            task = t
            break
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Award rewards from project budget
    reward = task.get("reward_rlm", 10)
    xp_reward = task.get("xp_reward", 20)
    
    # Update user
    new_xp = current_user.get("xp", 0) + xp_reward
    new_level = calculate_level(new_xp)
    
    await db.users.update_one(
        {"id": current_user["id"]},
        {
            "$set": {"xp": new_xp, "level": new_level},
            "$inc": {"realum_balance": reward}
        }
    )
    
    # Update task status
    await db.projects.update_one(
        {"id": project_id, "tasks.id": task_id},
        {"$set": {"tasks.$.status": "completed", "tasks.$.completed_by": current_user["id"]}}
    )
    
    # Recalculate project progress
    all_tasks = project.get("tasks", [])
    completed_tasks = len([t for t in all_tasks if t.get("status") == "completed"]) + 1
    progress = (completed_tasks / len(all_tasks) * 100) if all_tasks else 100
    
    await db.projects.update_one(
        {"id": project_id},
        {"$set": {"progress": progress}}
    )
    
    return {
        "status": "completed",
        "reward": reward,
        "xp_gained": xp_reward,
        "project_progress": progress
    }

# ==================== VALIDATION (EVALUATOR ROLE) ====================

@api_router.post("/validate")
async def validate_contribution(
    validation: ValidationRequest,
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] != UserRole.EVALUATOR:
        raise HTTPException(status_code=403, detail="Only Evaluators can validate")
    
    now = datetime.now(timezone.utc).isoformat()
    
    validation_record = {
        "id": str(uuid.uuid4()),
        "evaluator_id": current_user["id"],
        "evaluator_name": current_user["username"],
        "item_type": validation.item_type,
        "item_id": validation.item_id,
        "rating": validation.rating,
        "feedback": validation.feedback,
        "created_at": now
    }
    
    await db.validations.insert_one(validation_record)
    
    # Award XP to evaluator
    xp_reward = 15
    new_xp = current_user.get("xp", 0) + xp_reward
    new_level = calculate_level(new_xp)
    
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$set": {"xp": new_xp, "level": new_level}}
    )
    
    # If it's a marketplace item, update its rating
    if validation.item_type == "marketplace_item":
        await db.marketplace.update_one(
            {"id": validation.item_id},
            {
                "$push": {"reviews": validation_record},
                "$set": {"rating": validation.rating}  # Simplified - could average
            }
        )
    
    # Award badges
    await award_badge(current_user["id"], "first_validation")
    
    validations_done = await db.validations.count_documents({"evaluator_id": current_user["id"]})
    if validations_done >= 10:
        await award_badge(current_user["id"], "quality_guardian")
    if validations_done >= 50:
        await award_badge(current_user["id"], "master_evaluator")
    
    return {
        "status": "validated",
        "xp_earned": xp_reward
    }

# ==================== DAO & GOVERNANCE ====================

@api_router.get("/proposals", response_model=List[Proposal])
async def get_proposals(status: Optional[str] = None):
    query = {}
    if status:
        query["status"] = status
    
    proposals = await db.proposals.find(query, {"_id": 0}).to_list(100)
    return [Proposal(**p) for p in proposals]

@api_router.post("/proposals")
async def create_proposal(
    proposal: ProposalCreate,
    current_user: dict = Depends(get_current_user)
):
    if current_user.get("level", 1) < 2:
        raise HTTPException(status_code=403, detail="Requires level 2 to create proposals")
    
    now = datetime.now(timezone.utc)
    
    new_proposal = {
        "id": str(uuid.uuid4()),
        "title": proposal.title,
        "description": proposal.description,
        "proposer_id": current_user["id"],
        "proposer_name": current_user["username"],
        "votes_for": 0,
        "votes_against": 0,
        "voters": [],
        "status": "active",
        "created_at": now.isoformat(),
        "ends_at": (now + timedelta(days=7)).isoformat()
    }
    
    await db.proposals.insert_one(new_proposal)
    await award_badge(current_user["id"], "civic_voice")
    
    return {"status": "created", "proposal": {k: v for k, v in new_proposal.items() if k != "_id"}}

@api_router.post("/proposals/{proposal_id}/vote")
async def vote_on_proposal(
    proposal_id: str,
    vote: VoteRequest,
    current_user: dict = Depends(get_current_user)
):
    proposal = await db.proposals.find_one({"id": proposal_id})
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    if proposal["status"] != "active":
        raise HTTPException(status_code=400, detail="Proposal is not active")
    
    if current_user["id"] in proposal.get("voters", []):
        raise HTTPException(status_code=400, detail="Already voted")
    
    update_field = "votes_for" if vote.vote_type == "for" else "votes_against"
    
    await db.proposals.update_one(
        {"id": proposal_id},
        {
            "$inc": {update_field: 1},
            "$push": {"voters": current_user["id"]}
        }
    )
    
    # Award badges
    await award_badge(current_user["id"], "voter")
    
    votes_cast = await db.proposals.count_documents({"voters": current_user["id"]})
    if votes_cast >= 10:
        await award_badge(current_user["id"], "decident_activ")
    
    return {"status": "voted", "vote_type": vote.vote_type}

# ==================== CITY ZONES ====================

@api_router.get("/city/zones", response_model=List[CityZone])
async def get_city_zones():
    zones = await db.zones.find({}, {"_id": 0}).to_list(100)
    if not zones:
        return get_default_zones()
    return [CityZone(**z) for z in zones]

def get_default_zones():
    return [
        CityZone(id="hub", name="Central HUB", description="The heart of REALUM - active projects and community gathering", type="hub", jobs_count=5, buildings=["Project Tower", "Community Hall", "Info Center", "Welcome Desk"], color="#FFD700", features=["Live Projects", "Community Events", "Announcements"], position_3d={"x": 0, "y": 0, "z": 0}),
        CityZone(id="marketplace", name="Marketplace", description="Trade digital resources, designs, and services", type="commerce", jobs_count=15, buildings=["Grand Bazaar", "NFT Gallery", "Auction House", "Creator Studio", "Digital Mall"], color="#FF6B35", features=["Buy/Sell Resources", "NFT Trading", "Service Exchange"], position_3d={"x": 60, "y": 0, "z": 30}),
        CityZone(id="learning", name="Learning Zone", description="Courses, lessons, and skill development", type="education", jobs_count=12, buildings=["REALUM Academy", "Skill Labs", "Virtual Library", "Workshop Hall", "Certification Center"], color="#9D4EDD", features=["Video Courses", "Interactive Lessons", "Skill Badges"], position_3d={"x": -50, "y": 0, "z": 40}),
        CityZone(id="dao", name="DAO Arena", description="Community governance and collective decision-making", type="civic", jobs_count=8, buildings=["Council Chamber", "Voting Hall", "Proposal Forum", "Treasury View"], color="#40C4FF", features=["Proposals", "Voting", "Governance"], position_3d={"x": 0, "y": 0, "z": -60}),
        CityZone(id="tech-district", name="Tech District", description="Innovation, development, and blockchain infrastructure", type="tech", jobs_count=20, buildings=["Tech Hub", "Data Center", "Smart Contract Lab", "AI Research"], color="#FF003C", features=["Development Tasks", "Smart Contracts", "Tech Projects"], position_3d={"x": 70, "y": 0, "z": -40}),
        CityZone(id="residential", name="Residential District", description="Living quarters, social spaces, and community", type="residential", jobs_count=10, buildings=["Citizen Apartments", "Community Center", "Wellness Hub", "Ambassador Hall"], color="#00FF88", features=["Social Connections", "Ambassador Network", "Community"], position_3d={"x": -60, "y": 0, "z": -30}),
        CityZone(id="industrial", name="Industrial Zone", description="Production, manufacturing, and resource processing", type="industrial", jobs_count=15, buildings=["Factory Complex", "Warehouse", "Processing Plant", "Energy Grid"], color="#F9F871", features=["Production Tasks", "Resource Processing", "Energy"], position_3d={"x": 50, "y": 0, "z": 60}),
        CityZone(id="cultural", name="Cultural Quarter", description="Art, events, and creative expression", type="cultural", jobs_count=8, buildings=["Digital Museum", "Event Arena", "Art Gallery", "Performance Hall"], color="#E040FB", features=["Virtual Events", "Art Exhibitions", "Performances"], position_3d={"x": -40, "y": 0, "z": 70})
    ]

# ==================== LEADERBOARD ====================

@api_router.get("/leaderboard")
async def get_leaderboard():
    users = await db.users.find(
        {},
        {"_id": 0, "password": 0}
    ).sort("xp", -1).to_list(50)
    
    leaderboard = []
    for i, user in enumerate(users):
        leaderboard.append({
            "rank": i + 1,
            "id": user["id"],
            "username": user["username"],
            "role": user.get("role", "citizen"),
            "level": user.get("level", 1),
            "xp": user.get("xp", 0),
            "badges_count": len(user.get("badges", [])),
            "realum_balance": user.get("realum_balance", 0),
            "avatar_url": user.get("avatar_url")
        })
    
    return {"leaderboard": leaderboard}

# ==================== BADGES ====================

@api_router.get("/badges")
async def get_all_badges():
    return {
        "badges": [
            # Common Badges
            {"id": "newcomer", "name": "Newcomer", "description": "Welcome to REALUM!", "icon": "🌟", "rarity": "common"},
            {"id": "first_job", "name": "First Salary", "description": "Completed your first job", "icon": "💼", "rarity": "common"},
            {"id": "voter", "name": "Voter", "description": "Cast your first vote", "icon": "🗳️", "rarity": "common"},
            {"id": "first_transaction", "name": "First Transaction", "description": "Made your first transfer", "icon": "💸", "rarity": "common"},
            {"id": "first_course", "name": "First Course", "description": "Completed your first course", "icon": "📖", "rarity": "common"},
            {"id": "first_validation", "name": "First Validation", "description": "Validated your first contribution", "icon": "✓", "rarity": "common"},
            
            # Role-based badges
            {"id": "creator_starter", "name": "Creator Starter", "description": "Started as a Creator", "icon": "🎨", "rarity": "uncommon"},
            {"id": "quality_guardian", "name": "Quality Guardian", "description": "Started as an Evaluator", "icon": "🛡️", "rarity": "uncommon"},
            {"id": "partner_pioneer", "name": "Partner Pioneer", "description": "Joined as an External Partner", "icon": "🤝", "rarity": "uncommon"},
            {"id": "creator_first_item", "name": "First Creation", "description": "Listed first item in marketplace", "icon": "🎪", "rarity": "uncommon"},
            
            # Achievement badges
            {"id": "worker_bee", "name": "Worker Bee", "description": "Completed 5 jobs", "icon": "🐝", "rarity": "uncommon"},
            {"id": "civic_voice", "name": "Civic Voice", "description": "Created a proposal", "icon": "📢", "rarity": "uncommon"},
            {"id": "web3_pioneer", "name": "Web3 Pioneer", "description": "Connected a Web3 wallet", "icon": "🔗", "rarity": "uncommon"},
            {"id": "knowledge_seeker", "name": "Knowledge Seeker", "description": "Completed 5 courses", "icon": "📚", "rarity": "uncommon"},
            {"id": "project_creator", "name": "Project Creator", "description": "Created a project", "icon": "🏗️", "rarity": "uncommon"},
            {"id": "decident_activ", "name": "Active Decider", "description": "Voted on 10+ proposals", "icon": "⚖️", "rarity": "uncommon"},
            
            # Rare badges
            {"id": "job_master", "name": "Job Master", "description": "Completed 10+ jobs", "icon": "👔", "rarity": "rare"},
            {"id": "entrepreneur", "name": "Entrepreneur", "description": "Earned 10,000+ REALUM", "icon": "💰", "rarity": "rare"},
            {"id": "master_learner", "name": "Master Learner", "description": "Completed 10 courses", "icon": "🎓", "rarity": "rare"},
            {"id": "master_evaluator", "name": "Master Evaluator", "description": "Validated 50+ contributions", "icon": "⭐", "rarity": "rare"},
            
            # Legendary badges
            {"id": "citizen_elite", "name": "Citizen Elite", "description": "Reached level 10", "icon": "👑", "rarity": "legendary"},
            {"id": "realum_og", "name": "REALUM OG", "description": "Founding member", "icon": "🏆", "rarity": "legendary"},
            {"id": "dao_architect", "name": "DAO Architect", "description": "Major governance contributor", "icon": "🏛️", "rarity": "legendary"}
        ]
    }

# ==================== PLATFORM STATS ====================

@api_router.get("/stats")
async def get_platform_stats():
    users_count = await db.users.count_documents({})
    transactions = await db.wallets.aggregate([
        {"$unwind": "$transactions"},
        {"$count": "total"}
    ]).to_list(1)
    proposals_count = await db.proposals.count_documents({})
    jobs_completed = await db.active_jobs.count_documents({"status": "completed"})
    courses_count = await db.courses.count_documents({})
    projects_count = await db.projects.count_documents({})
    marketplace_items = await db.marketplace.count_documents({})
    
    stats = await db.platform_stats.find_one({"id": "main"}, {"_id": 0})
    
    return {
        "total_users": users_count,
        "total_transactions": transactions[0]["total"] if transactions else 0,
        "active_proposals": proposals_count,
        "jobs_completed": jobs_completed,
        "courses_available": courses_count,
        "active_projects": projects_count,
        "marketplace_items": marketplace_items,
        "tokens_burned": stats.get("total_tokens_burned", 0) if stats else 0
    }

# ==================== USER SIMULATION (Andreea, Vlad, Sorin) ====================

@api_router.post("/simulation/setup")
async def setup_simulation():
    """Set up the Andreea, Vlad, Sorin simulation"""
    now = datetime.now(timezone.utc).isoformat()
    
    # Create Andreea (Creator)
    andreea = {
        "id": "andreea-001",
        "email": "andreea@realum.io",
        "username": "Andreea",
        "password": hash_password("Andreea123!"),
        "role": UserRole.CREATOR,
        "wallet_address": None,
        "realum_balance": 1500.0,
        "xp": 250,
        "level": 1,
        "badges": ["newcomer", "creator_starter", "creator_first_item"],
        "skills": ["UI Design", "Figma", "Adobe XD"],
        "courses_completed": [],
        "projects_joined": [],
        "created_at": now,
        "avatar_url": None,
        "language": "ro"
    }
    
    # Create Vlad (Contributor)
    vlad = {
        "id": "vlad-001",
        "email": "vlad@realum.io",
        "username": "Vlad",
        "password": hash_password("Vlad123!"),
        "role": UserRole.CONTRIBUTOR,
        "wallet_address": None,
        "realum_balance": 800.0,
        "xp": 150,
        "level": 1,
        "badges": ["newcomer", "first_job", "worker_bee"],
        "skills": ["React", "JavaScript", "CSS"],
        "courses_completed": [],
        "projects_joined": [],
        "created_at": now,
        "avatar_url": None,
        "language": "ro"
    }
    
    # Create Sorin (Evaluator)
    sorin = {
        "id": "sorin-001",
        "email": "sorin@realum.io",
        "username": "Sorin",
        "password": hash_password("Sorin123!"),
        "role": UserRole.EVALUATOR,
        "wallet_address": None,
        "realum_balance": 1200.0,
        "xp": 300,
        "level": 1,
        "badges": ["newcomer", "quality_guardian", "first_validation"],
        "skills": ["Quality Assurance", "Code Review", "Testing"],
        "courses_completed": [],
        "projects_joined": [],
        "created_at": now,
        "avatar_url": None,
        "language": "ro"
    }
    
    # Upsert users
    for user in [andreea, vlad, sorin]:
        await db.users.update_one({"id": user["id"]}, {"$set": user}, upsert=True)
        await db.wallets.update_one(
            {"user_id": user["id"]},
            {"$set": {"user_id": user["id"], "balance": user["realum_balance"], "transactions": []}},
            upsert=True
        )
    
    # Create Andreea's marketplace item (UI Design)
    marketplace_item = {
        "id": "andreea-design-001",
        "title": "Modern Dashboard UI Kit",
        "description": "Complete UI design kit with 50+ components for dashboard applications",
        "category": "design",
        "price_rlm": 150.0,
        "seller_id": "andreea-001",
        "seller_name": "Andreea",
        "file_url": None,
        "preview_url": None,
        "downloads": 0,
        "rating": 0,
        "reviews": [],
        "status": "available",
        "created_at": now
    }
    
    await db.marketplace.update_one({"id": marketplace_item["id"]}, {"$set": marketplace_item}, upsert=True)
    
    return {
        "status": "simulation_ready",
        "users": [
            {"username": "Andreea", "role": "Creator", "balance": 1500, "email": "andreea@realum.io"},
            {"username": "Vlad", "role": "Contributor", "balance": 800, "email": "vlad@realum.io"},
            {"username": "Sorin", "role": "Evaluator", "balance": 1200, "email": "sorin@realum.io"}
        ],
        "marketplace_item": marketplace_item["title"],
        "password_for_all": "Username123! (e.g., Andreea123!)"
    }

@api_router.post("/simulation/step/{step}")
async def run_simulation_step(step: int):
    """Run a specific step of the simulation"""
    now = datetime.now(timezone.utc).isoformat()
    
    if step == 1:
        # Step 1: Vlad purchases Andreea's design
        item = await db.marketplace.find_one({"id": "andreea-design-001"})
        if not item:
            return {"error": "Run /simulation/setup first"}
        
        price = item["price_rlm"]
        burn_amount = price * TOKEN_BURN_RATE
        seller_amount = price - burn_amount
        
        # Vlad pays
        await db.users.update_one({"id": "vlad-001"}, {"$inc": {"realum_balance": -price}})
        # Andreea receives
        await db.users.update_one({"id": "andreea-001"}, {"$inc": {"realum_balance": seller_amount}})
        
        # Record transactions
        await db.wallets.update_one(
            {"user_id": "vlad-001"},
            {"$push": {"transactions": {
                "id": str(uuid.uuid4()),
                "type": "debit",
                "amount": price,
                "description": f"Purchased: {item['title']} from Andreea",
                "timestamp": now
            }}}
        )
        
        await db.wallets.update_one(
            {"user_id": "andreea-001"},
            {"$push": {"transactions": {
                "id": str(uuid.uuid4()),
                "type": "credit",
                "amount": seller_amount,
                "from_user": "Vlad",
                "description": f"Sold: {item['title']}",
                "timestamp": now
            }}}
        )
        
        await burn_tokens(burn_amount, "Simulation: Vlad purchased Andreea's design")
        
        return {
            "step": 1,
            "action": "Vlad purchased Andreea's UI Design",
            "vlad_paid": price,
            "andreea_received": seller_amount,
            "tokens_burned": burn_amount,
            "balances": {
                "vlad": 800 - price,
                "andreea": 1500 + seller_amount
            }
        }
    
    elif step == 2:
        # Step 2: Vlad completes a task using the design
        task_reward = 100.0
        xp_reward = 50
        
        await db.users.update_one(
            {"id": "vlad-001"},
            {"$inc": {"realum_balance": task_reward, "xp": xp_reward}}
        )
        
        await db.wallets.update_one(
            {"user_id": "vlad-001"},
            {"$push": {"transactions": {
                "id": str(uuid.uuid4()),
                "type": "credit",
                "amount": task_reward,
                "description": "Task completed: Implement Dashboard using UI Kit",
                "timestamp": now
            }}}
        )
        
        vlad = await db.users.find_one({"id": "vlad-001"}, {"_id": 0, "password": 0})
        
        return {
            "step": 2,
            "action": "Vlad completed a task using Andreea's design",
            "reward_earned": task_reward,
            "xp_earned": xp_reward,
            "vlad_new_balance": vlad["realum_balance"]
        }
    
    elif step == 3:
        # Step 3: Sorin validates Vlad's work
        validation_reward = 25.0
        xp_reward = 15
        
        await db.users.update_one(
            {"id": "sorin-001"},
            {"$inc": {"realum_balance": validation_reward, "xp": xp_reward}}
        )
        
        await db.wallets.update_one(
            {"user_id": "sorin-001"},
            {"$push": {"transactions": {
                "id": str(uuid.uuid4()),
                "type": "credit",
                "amount": validation_reward,
                "description": "Validation reward: Approved Vlad's Dashboard implementation",
                "timestamp": now
            }}}
        )
        
        # Record validation
        await db.validations.insert_one({
            "id": str(uuid.uuid4()),
            "evaluator_id": "sorin-001",
            "evaluator_name": "Sorin",
            "item_type": "task",
            "item_id": "vlad-dashboard-task",
            "rating": 5,
            "feedback": "Excellent implementation! Clean code and great use of the UI kit.",
            "created_at": now
        })
        
        # Get final balances
        andreea = await db.users.find_one({"id": "andreea-001"}, {"_id": 0, "password": 0})
        vlad = await db.users.find_one({"id": "vlad-001"}, {"_id": 0, "password": 0})
        sorin = await db.users.find_one({"id": "sorin-001"}, {"_id": 0, "password": 0})
        
        return {
            "step": 3,
            "action": "Sorin validated Vlad's work",
            "sorin_reward": validation_reward,
            "final_balances": {
                "andreea": andreea["realum_balance"],
                "vlad": vlad["realum_balance"],
                "sorin": sorin["realum_balance"]
            },
            "token_flow_summary": {
                "andreea_earned": "147 RLM from design sale",
                "vlad_earned": "100 RLM from task completion, spent 150 RLM on design",
                "sorin_earned": "25 RLM from validation",
                "tokens_burned": "3 RLM (2% of 150 RLM sale)"
            }
        }
    
    return {"error": "Invalid step. Use 1, 2, or 3"}

@api_router.get("/simulation/status")
async def get_simulation_status():
    """Get current simulation status"""
    andreea = await db.users.find_one({"id": "andreea-001"}, {"_id": 0, "password": 0})
    vlad = await db.users.find_one({"id": "vlad-001"}, {"_id": 0, "password": 0})
    sorin = await db.users.find_one({"id": "sorin-001"}, {"_id": 0, "password": 0})
    
    if not all([andreea, vlad, sorin]):
        return {"status": "not_initialized", "message": "Run POST /api/simulation/setup first"}
    
    andreea_wallet = await db.wallets.find_one({"user_id": "andreea-001"}, {"_id": 0})
    vlad_wallet = await db.wallets.find_one({"user_id": "vlad-001"}, {"_id": 0})
    sorin_wallet = await db.wallets.find_one({"user_id": "sorin-001"}, {"_id": 0})
    
    return {
        "status": "ready",
        "users": {
            "andreea": {
                "role": andreea["role"],
                "balance": andreea["realum_balance"],
                "xp": andreea["xp"],
                "transactions": len(andreea_wallet.get("transactions", [])) if andreea_wallet else 0
            },
            "vlad": {
                "role": vlad["role"],
                "balance": vlad["realum_balance"],
                "xp": vlad["xp"],
                "transactions": len(vlad_wallet.get("transactions", [])) if vlad_wallet else 0
            },
            "sorin": {
                "role": sorin["role"],
                "balance": sorin["realum_balance"],
                "xp": sorin["xp"],
                "transactions": len(sorin_wallet.get("transactions", [])) if sorin_wallet else 0
            }
        }
    }

# ==================== SEED DATA ====================

@api_router.post("/seed")
async def seed_data():
    # Clear existing seed data first to avoid duplicates
    await db.jobs.delete_many({"id": {"$regex": "^job-"}})
    await db.zones.delete_many({})
    await db.proposals.delete_many({"id": {"$regex": "^prop-"}})
    await db.courses.delete_many({"id": {"$regex": "^course-"}})
    await db.projects.delete_many({"id": {"$regex": "^proj-"}})
    await db.marketplace.delete_many({"id": {"$regex": "^mkt-"}})
    
    # Seed comprehensive jobs
    jobs = [
        # HUB Jobs
        {"id": "job-1", "title": "Community Manager", "description": "Manage community events and announcements in the Central HUB", "company": "REALUM Core", "zone": "hub", "reward": 100, "xp_reward": 35, "duration_minutes": 60, "required_level": 1, "skills_required": ["Communication"], "status": "available"},
        {"id": "job-2", "title": "Welcome Guide", "description": "Help new users navigate REALUM", "company": "REALUM Core", "zone": "hub", "reward": 50, "xp_reward": 20, "duration_minutes": 30, "required_level": 1, "skills_required": [], "status": "available"},
        
        # Marketplace Jobs
        {"id": "job-3", "title": "NFT Artist", "description": "Create digital art for the NFT Gallery", "company": "CryptoArt Studios", "zone": "marketplace", "reward": 200, "xp_reward": 65, "duration_minutes": 120, "required_level": 2, "required_role": "creator", "skills_required": ["Digital Art", "NFT"], "status": "available"},
        {"id": "job-4", "title": "Market Vendor", "description": "Assist with digital goods transactions", "company": "Grand Bazaar", "zone": "marketplace", "reward": 60, "xp_reward": 18, "duration_minutes": 30, "required_level": 1, "skills_required": [], "status": "available"},
        {"id": "job-5", "title": "Auction Manager", "description": "Host and manage digital asset auctions", "company": "Auction House", "zone": "marketplace", "reward": 175, "xp_reward": 55, "duration_minutes": 90, "required_level": 3, "skills_required": ["Sales"], "status": "available"},
        
        # Learning Zone Jobs
        {"id": "job-6", "title": "Teaching Assistant", "description": "Support students in virtual learning environments", "company": "REALUM Academy", "zone": "learning", "reward": 95, "xp_reward": 30, "duration_minutes": 60, "required_level": 1, "skills_required": ["Teaching"], "status": "available"},
        {"id": "job-7", "title": "Course Creator", "description": "Design gamified educational content", "company": "REALUM Learn", "zone": "learning", "reward": 250, "xp_reward": 80, "duration_minutes": 150, "required_level": 3, "required_role": "creator", "skills_required": ["Content Creation", "Education"], "status": "available"},
        {"id": "job-8", "title": "Librarian", "description": "Organize and manage digital archives", "company": "Virtual Library", "zone": "learning", "reward": 70, "xp_reward": 22, "duration_minutes": 40, "required_level": 1, "skills_required": [], "status": "available"},
        
        # DAO Jobs
        {"id": "job-9", "title": "Proposal Reviewer", "description": "Review and summarize DAO proposals", "company": "REALUM DAO", "zone": "dao", "reward": 120, "xp_reward": 45, "duration_minutes": 60, "required_level": 2, "required_role": "evaluator", "skills_required": ["Analysis"], "status": "available"},
        {"id": "job-10", "title": "Governance Analyst", "description": "Analyze voting patterns and governance metrics", "company": "REALUM DAO", "zone": "dao", "reward": 180, "xp_reward": 60, "duration_minutes": 90, "required_level": 3, "skills_required": ["Data Analysis"], "status": "available"},
        
        # Tech District Jobs
        {"id": "job-11", "title": "Junior Developer", "description": "Debug code and fix bugs at the Tech Hub", "company": "CodeForge", "zone": "tech-district", "reward": 150, "xp_reward": 50, "duration_minutes": 90, "required_level": 2, "required_role": "contributor", "skills_required": ["JavaScript", "React"], "status": "available"},
        {"id": "job-12", "title": "Smart Contract Auditor", "description": "Review and audit blockchain smart contracts", "company": "REALUM Tech", "zone": "tech-district", "reward": 300, "xp_reward": 100, "duration_minutes": 180, "required_level": 4, "skills_required": ["Solidity", "Security"], "status": "available"},
        {"id": "job-13", "title": "UI/UX Designer", "description": "Design user interfaces for REALUM apps", "company": "Design Studio", "zone": "tech-district", "reward": 200, "xp_reward": 70, "duration_minutes": 120, "required_level": 2, "required_role": "creator", "skills_required": ["UI Design", "Figma"], "status": "available"},
        
        # Industrial Jobs
        {"id": "job-14", "title": "Factory Worker", "description": "Process digital resources in the factory", "company": "REALUM Industries", "zone": "industrial", "reward": 80, "xp_reward": 25, "duration_minutes": 60, "required_level": 1, "skills_required": [], "status": "available"},
        {"id": "job-15", "title": "Quality Inspector", "description": "Ensure digital products meet standards", "company": "Quality Control", "zone": "industrial", "reward": 130, "xp_reward": 42, "duration_minutes": 75, "required_level": 2, "required_role": "evaluator", "skills_required": ["Quality Assurance"], "status": "available"},
        
        # Residential Jobs  
        {"id": "job-16", "title": "Ambassador", "description": "Represent REALUM and onboard new users", "company": "Ambassador Network", "zone": "residential", "reward": 160, "xp_reward": 55, "duration_minutes": 90, "required_level": 3, "skills_required": ["Communication", "Onboarding"], "status": "available"},
        {"id": "job-17", "title": "Community Support", "description": "Help residents with questions and issues", "company": "Support Center", "zone": "residential", "reward": 75, "xp_reward": 28, "duration_minutes": 45, "required_level": 1, "skills_required": [], "status": "available"},
        
        # Cultural Jobs
        {"id": "job-18", "title": "Event Organizer", "description": "Plan and execute virtual events", "company": "Event Arena", "zone": "cultural", "reward": 140, "xp_reward": 48, "duration_minutes": 90, "required_level": 2, "skills_required": ["Event Planning"], "status": "available"},
        {"id": "job-19", "title": "Art Curator", "description": "Curate exhibitions in the Digital Museum", "company": "Digital Museum", "zone": "cultural", "reward": 170, "xp_reward": 58, "duration_minutes": 100, "required_level": 3, "required_role": "evaluator", "skills_required": ["Art Curation"], "status": "available"},
        {"id": "job-20", "title": "Content Moderator", "description": "Review and moderate community content", "company": "REALUM Core", "zone": "hub", "reward": 90, "xp_reward": 32, "duration_minutes": 60, "required_level": 2, "required_role": "evaluator", "skills_required": ["Moderation"], "status": "available"}
    ]
    
    for job in jobs:
        await db.jobs.update_one({"id": job["id"]}, {"$set": job}, upsert=True)
    
    # Seed zones
    zones = get_default_zones()
    for zone in zones:
        zone_dict = zone.model_dump() if hasattr(zone, 'model_dump') else zone.__dict__
        await db.zones.update_one({"id": zone_dict["id"]}, {"$set": zone_dict}, upsert=True)
    
    # Seed proposals
    now = datetime.now(timezone.utc)
    proposals = [
        {"id": "prop-1", "title": "Increase Minimum Task Reward", "description": "Raise the minimum task reward from 50 to 75 RLM to ensure fair compensation for all contributors.", "proposer_id": "system", "proposer_name": "DAO Council", "votes_for": 142, "votes_against": 38, "voters": [], "status": "active", "created_at": now.isoformat(), "ends_at": (now + timedelta(days=5)).isoformat()},
        {"id": "prop-2", "title": "Launch Creator Grant Program", "description": "Establish a 50,000 RLM fund to support promising creators with grants for innovative projects.", "proposer_id": "system", "proposer_name": "Creator Committee", "votes_for": 234, "votes_against": 12, "voters": [], "status": "active", "created_at": now.isoformat(), "ends_at": (now + timedelta(days=7)).isoformat()},
        {"id": "prop-3", "title": "Multilingual Platform Expansion", "description": "Fund translation and localization for 10 additional languages to expand REALUM globally.", "proposer_id": "system", "proposer_name": "Global Team", "votes_for": 189, "votes_against": 21, "voters": [], "status": "active", "created_at": now.isoformat(), "ends_at": (now + timedelta(days=10)).isoformat()},
        {"id": "prop-4", "title": "NGO Partnership Framework", "description": "Create a formal framework for partnering with NGOs to bring educational opportunities to underserved communities.", "proposer_id": "system", "proposer_name": "Partnership Team", "votes_for": 267, "votes_against": 8, "voters": [], "status": "active", "created_at": now.isoformat(), "ends_at": (now + timedelta(days=14)).isoformat()},
        {"id": "prop-5", "title": "Token Burn Rate Adjustment", "description": "Reduce token burn rate from 2% to 1.5% to encourage more marketplace activity.", "proposer_id": "system", "proposer_name": "Economics Team", "votes_for": 156, "votes_against": 87, "voters": [], "status": "active", "created_at": now.isoformat(), "ends_at": (now + timedelta(days=5)).isoformat()}
    ]
    
    for prop in proposals:
        await db.proposals.update_one({"id": prop["id"]}, {"$set": prop}, upsert=True)
    
    # Seed courses
    courses = [
        {
            "id": "course-1",
            "title": "Introduction to REALUM",
            "description": "Learn the basics of the REALUM ecosystem, token economy, and how to get started.",
            "category": "basics",
            "difficulty": "beginner",
            "duration_hours": 2,
            "xp_reward": 100,
            "rlm_reward": 50,
            "skills_gained": ["REALUM Basics"],
            "lessons": [
                {"id": "l1", "title": "Welcome to REALUM", "type": "video", "duration_minutes": 15, "content": "Introduction video"},
                {"id": "l2", "title": "Understanding RLM Tokens", "type": "text", "duration_minutes": 10, "content": "Token economy explanation"},
                {"id": "l3", "title": "Your First Steps", "type": "interactive", "duration_minutes": 20, "content": "Interactive tutorial"}
            ],
            "quiz_questions": [
                {"id": "q1", "question": "What is RLM?", "options": ["REALUM Coin", "Real Money", "Random Luck Module"], "correct": 0},
                {"id": "q2", "question": "How can you earn RLM?", "options": ["Completing tasks", "Buying only", "It's free"], "correct": 0}
            ],
            "thumbnail_url": None,
            "enrolled_count": 0,
            "completion_rate": 0
        },
        {
            "id": "course-2",
            "title": "Web3 and Blockchain Fundamentals",
            "description": "Understand blockchain technology, smart contracts, and decentralized applications.",
            "category": "tech",
            "difficulty": "intermediate",
            "duration_hours": 5,
            "xp_reward": 250,
            "rlm_reward": 100,
            "skills_gained": ["Blockchain", "Web3", "Smart Contracts"],
            "lessons": [
                {"id": "l1", "title": "What is Blockchain?", "type": "video", "duration_minutes": 30, "content": "Blockchain basics"},
                {"id": "l2", "title": "Smart Contracts Explained", "type": "text", "duration_minutes": 25, "content": "Smart contract fundamentals"},
                {"id": "l3", "title": "Connecting Wallets", "type": "interactive", "duration_minutes": 20, "content": "Hands-on wallet connection"},
                {"id": "l4", "title": "DeFi Basics", "type": "video", "duration_minutes": 35, "content": "Introduction to DeFi"}
            ],
            "quiz_questions": [
                {"id": "q1", "question": "What ensures blockchain security?", "options": ["Cryptography", "Passwords only", "Firewalls"], "correct": 0},
                {"id": "q2", "question": "What are smart contracts?", "options": ["Self-executing code", "Legal documents", "Email agreements"], "correct": 0}
            ],
            "thumbnail_url": None,
            "enrolled_count": 0,
            "completion_rate": 0
        },
        {
            "id": "course-3",
            "title": "DAO Governance Mastery",
            "description": "Learn how decentralized autonomous organizations work and how to participate effectively.",
            "category": "civic",
            "difficulty": "intermediate",
            "duration_hours": 4,
            "xp_reward": 200,
            "rlm_reward": 75,
            "skills_gained": ["DAO Governance", "Voting", "Proposal Writing"],
            "lessons": [
                {"id": "l1", "title": "What is a DAO?", "type": "video", "duration_minutes": 20, "content": "DAO fundamentals"},
                {"id": "l2", "title": "Voting Mechanisms", "type": "text", "duration_minutes": 15, "content": "How voting works"},
                {"id": "l3", "title": "Writing Effective Proposals", "type": "interactive", "duration_minutes": 30, "content": "Proposal workshop"},
                {"id": "l4", "title": "Quadratic Voting", "type": "video", "duration_minutes": 25, "content": "Advanced voting systems"}
            ],
            "quiz_questions": [
                {"id": "q1", "question": "Who controls a DAO?", "options": ["Token holders", "A CEO", "The government"], "correct": 0}
            ],
            "thumbnail_url": None,
            "enrolled_count": 0,
            "completion_rate": 0
        },
        {
            "id": "course-4",
            "title": "Digital Art & NFT Creation",
            "description": "Master the art of creating digital assets and minting NFTs for the marketplace.",
            "category": "creative",
            "difficulty": "beginner",
            "duration_hours": 6,
            "xp_reward": 300,
            "rlm_reward": 125,
            "skills_gained": ["Digital Art", "NFT Creation", "Marketplace"],
            "lessons": [
                {"id": "l1", "title": "Digital Art Tools", "type": "video", "duration_minutes": 40, "content": "Tool overview"},
                {"id": "l2", "title": "Creating Your First NFT", "type": "interactive", "duration_minutes": 45, "content": "Hands-on NFT creation"},
                {"id": "l3", "title": "Marketplace Strategies", "type": "text", "duration_minutes": 20, "content": "Selling tips"},
                {"id": "l4", "title": "Building Your Brand", "type": "video", "duration_minutes": 30, "content": "Personal branding"}
            ],
            "quiz_questions": [
                {"id": "q1", "question": "What does NFT stand for?", "options": ["Non-Fungible Token", "New File Type", "Network Function Test"], "correct": 0}
            ],
            "thumbnail_url": None,
            "enrolled_count": 0,
            "completion_rate": 0
        },
        {
            "id": "course-5",
            "title": "Token Economics 101",
            "description": "Deep dive into tokenomics, understanding supply, demand, and economic models.",
            "category": "economics",
            "difficulty": "advanced",
            "duration_hours": 8,
            "xp_reward": 400,
            "rlm_reward": 200,
            "skills_gained": ["Tokenomics", "Economic Analysis", "Financial Modeling"],
            "lessons": [
                {"id": "l1", "title": "Supply and Demand", "type": "video", "duration_minutes": 45, "content": "Economic fundamentals"},
                {"id": "l2", "title": "Token Burning Mechanisms", "type": "text", "duration_minutes": 30, "content": "Deflationary models"},
                {"id": "l3", "title": "Incentive Design", "type": "interactive", "duration_minutes": 40, "content": "Creating incentives"},
                {"id": "l4", "title": "Case Studies", "type": "video", "duration_minutes": 50, "content": "Real-world examples"}
            ],
            "quiz_questions": [
                {"id": "q1", "question": "What happens when tokens are burned?", "options": ["Supply decreases", "Supply increases", "Nothing"], "correct": 0}
            ],
            "thumbnail_url": None,
            "enrolled_count": 0,
            "completion_rate": 0
        }
    ]
    
    for course in courses:
        await db.courses.update_one({"id": course["id"]}, {"$set": course}, upsert=True)
    
    # Seed sample projects
    projects = [
        {
            "id": "proj-1",
            "title": "REALUM Mobile App",
            "description": "Build a mobile-first version of the REALUM platform",
            "creator_id": "system",
            "creator_name": "REALUM Core",
            "category": "tech",
            "status": "active",
            "budget_rlm": 5000,
            "participants": [],
            "tasks": [
                {"id": "t1", "title": "Design mobile wireframes", "description": "Create UI mockups", "reward_rlm": 200, "xp_reward": 80, "status": "open"},
                {"id": "t2", "title": "Implement React Native shell", "description": "Set up the app structure", "reward_rlm": 300, "xp_reward": 120, "status": "open"}
            ],
            "progress": 0,
            "position_3d": {"x": 30, "y": 0, "z": 20},
            "island_type": "tech",
            "created_at": now.isoformat()
        },
        {
            "id": "proj-2",
            "title": "Community Art Collection",
            "description": "Collaborative NFT art collection representing REALUM's vision",
            "creator_id": "system",
            "creator_name": "Art Collective",
            "category": "creative",
            "status": "active",
            "budget_rlm": 3000,
            "participants": [],
            "tasks": [
                {"id": "t1", "title": "Create concept art", "description": "Design 10 unique concepts", "reward_rlm": 150, "xp_reward": 60, "status": "open"},
                {"id": "t2", "title": "Mint NFT collection", "description": "Prepare and mint the final pieces", "reward_rlm": 250, "xp_reward": 100, "status": "open"}
            ],
            "progress": 0,
            "position_3d": {"x": -40, "y": 0, "z": 35},
            "island_type": "creative",
            "created_at": now.isoformat()
        },
        {
            "id": "proj-3",
            "title": "Educational Partnership Program",
            "description": "Establish partnerships with universities for course content",
            "creator_id": "system",
            "creator_name": "Education Team",
            "category": "education",
            "status": "active",
            "budget_rlm": 8000,
            "participants": [],
            "tasks": [
                {"id": "t1", "title": "Research potential partners", "description": "Identify 20 universities", "reward_rlm": 100, "xp_reward": 40, "status": "open"},
                {"id": "t2", "title": "Create partnership proposal", "description": "Draft formal proposal", "reward_rlm": 200, "xp_reward": 80, "status": "open"},
                {"id": "t3", "title": "Outreach campaign", "description": "Contact potential partners", "reward_rlm": 150, "xp_reward": 60, "status": "open"}
            ],
            "progress": 0,
            "position_3d": {"x": -20, "y": 0, "z": -45},
            "island_type": "education",
            "created_at": now.isoformat()
        }
    ]
    
    for proj in projects:
        await db.projects.update_one({"id": proj["id"]}, {"$set": proj}, upsert=True)
    
    # Seed marketplace items
    marketplace_items = [
        {"id": "mkt-1", "title": "Cyberpunk UI Kit", "description": "Complete UI component library with 100+ elements", "category": "design", "price_rlm": 150, "seller_id": "system", "seller_name": "REALUM Store", "downloads": 45, "rating": 4.8, "reviews": [], "status": "available", "created_at": now.isoformat()},
        {"id": "mkt-2", "title": "Smart Contract Templates", "description": "5 ready-to-use smart contract templates", "category": "code", "price_rlm": 200, "seller_id": "system", "seller_name": "REALUM Store", "downloads": 32, "rating": 4.5, "reviews": [], "status": "available", "created_at": now.isoformat()},
        {"id": "mkt-3", "title": "Project Management Course", "description": "Advanced project management for Web3", "category": "course", "price_rlm": 100, "seller_id": "system", "seller_name": "REALUM Academy", "downloads": 78, "rating": 4.9, "reviews": [], "status": "available", "created_at": now.isoformat()},
        {"id": "mkt-4", "title": "Avatar Pack - Neon Series", "description": "10 unique neon-style avatars", "category": "design", "price_rlm": 50, "seller_id": "system", "seller_name": "REALUM Store", "downloads": 120, "rating": 4.7, "reviews": [], "status": "available", "created_at": now.isoformat()}
    ]
    
    for item in marketplace_items:
        await db.marketplace.update_one({"id": item["id"]}, {"$set": item}, upsert=True)
    
    return {
        "status": "seeded",
        "jobs": len(jobs),
        "zones": len(zones),
        "proposals": len(proposals),
        "courses": len(courses),
        "projects": len(projects),
        "marketplace_items": len(marketplace_items)
    }

# ==================== HEALTH CHECK ====================

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

# ==================== SETUP ====================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
