from fastapi import APIRouter, HTTPException, status, Depends
from datetime import datetime, timezone, timedelta
import jwt
import bcrypt
import uuid

from ..core.database import db
from ..core.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_HOURS, INITIAL_BALANCE
from ..core.auth import get_current_user
from ..models.user import UserCreate, UserLogin, UserResponse, TokenResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=TokenResponse)
async def register(user_data: UserCreate):
    existing = await db.users.find_one({"$or": [{"email": user_data.email}, {"username": user_data.username}]})
    if existing:
        raise HTTPException(status_code=400, detail="Email or username already exists")
    
    hashed_password = bcrypt.hashpw(user_data.password.encode(), bcrypt.gensalt()).decode()
    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    user = {
        "id": user_id,
        "email": user_data.email,
        "username": user_data.username,
        "password": hashed_password,
        "role": user_data.role,
        "realum_balance": INITIAL_BALANCE,
        "wallet_address": None,
        "xp": 0,
        "level": 1,
        "badges": ["newcomer"],
        "skills": [],
        "courses_completed": [],
        "projects_joined": [],
        "created_at": now,
        "avatar_url": None,
        "language": "en"
    }
    
    await db.users.insert_one(user)
    
    # Create welcome transaction
    welcome_tx = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "type": "credit",
        "amount": INITIAL_BALANCE,
        "burned": 0,
        "description": "Welcome bonus",
        "timestamp": now
    }
    await db.transactions.insert_one(welcome_tx)
    
    token = jwt.encode(
        {"sub": user_id, "exp": datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)},
        SECRET_KEY, algorithm=ALGORITHM
    )
    
    user_response = {k: v for k, v in user.items() if k != "password"}
    return {"access_token": token, "user": user_response}

@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    if not user or not bcrypt.checkpw(credentials.password.encode(), user["password"].encode()):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    
    token = jwt.encode(
        {"sub": user["id"], "exp": datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)},
        SECRET_KEY, algorithm=ALGORITHM
    )
    
    user_response = {k: v for k, v in user.items() if k != "password"}
    return {"access_token": token, "user": user_response}

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: dict = Depends(get_current_user)):
    return current_user

@router.put("/profile")
async def update_profile(
    language: str = None,
    avatar_url: str = None,
    skills: list = None,
    current_user: dict = Depends(get_current_user)
):
    updates = {}
    if language: updates["language"] = language
    if avatar_url: updates["avatar_url"] = avatar_url
    if skills: updates["skills"] = skills
    
    if updates:
        await db.users.update_one({"id": current_user["id"]}, {"$set": updates})
    
    return {"status": "updated"}
