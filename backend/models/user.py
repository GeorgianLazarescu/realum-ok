from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
from core.config import INITIAL_BALANCE

class UserRole:
    CREATOR = "creator"
    CONTRIBUTOR = "contributor"
    EVALUATOR = "evaluator"
    PARTNER = "partner"
    CITIZEN = "citizen"

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
