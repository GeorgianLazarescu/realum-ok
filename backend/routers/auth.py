from fastapi import APIRouter, HTTPException, status, Depends, Request
from datetime import datetime, timezone, timedelta
import jwt
import bcrypt
import uuid
import re
import secrets

from core.database import db
from core.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_HOURS, INITIAL_BALANCE
from core.auth import get_current_user, get_client_ip
from core.logging import audit_logger
from models.user import UserCreate, UserLogin, UserResponse, TokenResponse
from pydantic import BaseModel, EmailStr
from typing import Optional

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Password complexity requirements
PASSWORD_MIN_LENGTH = 8
PASSWORD_REQUIREMENTS = {
    "uppercase": r"[A-Z]",
    "lowercase": r"[a-z]",
    "digit": r"\d",
    "special": r"[!@#$%^&*(),.?\":{}|<>]"
}

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

def validate_password(password: str) -> tuple[bool, list]:
    """Validate password complexity requirements"""
    errors = []
    
    if len(password) < PASSWORD_MIN_LENGTH:
        errors.append(f"Password must be at least {PASSWORD_MIN_LENGTH} characters")
    
    if not re.search(PASSWORD_REQUIREMENTS["uppercase"], password):
        errors.append("Password must contain at least one uppercase letter")
    
    if not re.search(PASSWORD_REQUIREMENTS["lowercase"], password):
        errors.append("Password must contain at least one lowercase letter")
    
    if not re.search(PASSWORD_REQUIREMENTS["digit"], password):
        errors.append("Password must contain at least one digit")
    
    if not re.search(PASSWORD_REQUIREMENTS["special"], password):
        errors.append("Password must contain at least one special character (!@#$%^&*(),.?\":{}|<>)")
    
    return len(errors) == 0, errors

@router.post("/register", response_model=TokenResponse)
async def register(user_data: UserCreate, request: Request):
    """Register a new user with password complexity validation"""
    
    # Validate password complexity
    is_valid, errors = validate_password(user_data.password)
    if not is_valid:
        raise HTTPException(status_code=400, detail={"message": "Password requirements not met", "errors": errors})
    
    existing = await db.users.find_one({"$or": [{"email": user_data.email}, {"username": user_data.username}]})
    if existing:
        raise HTTPException(status_code=400, detail="Email or username already exists")
    
    hashed_password = bcrypt.hashpw(user_data.password.encode(), bcrypt.gensalt()).decode()
    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    now_str = now.isoformat()
    
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
        "created_at": now_str,
        "avatar_url": None,
        "language": "en",
        "email_verified": False,
        "two_factor_enabled": False,
        "last_password_change": now,
        "failed_login_attempts": 0,
        "locked_until": None
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
        "timestamp": now_str
    }
    await db.transactions.insert_one(welcome_tx)
    
    # Generate email verification token
    verification_token = secrets.token_urlsafe(32)
    await db.email_verifications.insert_one({
        "user_id": user_id,
        "email": user_data.email,
        "token": verification_token,
        "expires_at": now + timedelta(hours=24),
        "created_at": now
    })
    
    # Log registration
    await audit_logger.log_security_event(
        event_type="user_registered",
        severity="info",
        details={"user_id": user_id, "email": user_data.email},
        ip_address=get_client_ip(request),
        user_id=user_id
    )
    
    token = jwt.encode(
        {"sub": user_id, "exp": datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)},
        SECRET_KEY, algorithm=ALGORITHM
    )
    
    user_response = {k: v for k, v in user.items() if k != "password"}
    return {"access_token": token, "user": user_response}

@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, request: Request):
    """Login with account lockout protection"""
    
    user = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    
    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")
    
    # Check if account is locked
    locked_until = user.get("locked_until")
    if locked_until:
        # Ensure both datetimes are timezone-aware for comparison
        current_time = datetime.now(timezone.utc)
        if isinstance(locked_until, str):
            # Parse ISO string to datetime
            from datetime import datetime as dt
            locked_until = dt.fromisoformat(locked_until.replace('Z', '+00:00'))
        elif locked_until.tzinfo is None:
            # Make naive datetime timezone-aware
            locked_until = locked_until.replace(tzinfo=timezone.utc)
        
        if locked_until > current_time:
            time_remaining = (locked_until - current_time).seconds // 60
            raise HTTPException(
                status_code=423, 
                detail=f"Account locked due to too many failed attempts. Try again in {time_remaining} minutes."
            )
    
    # Verify password
    if not bcrypt.checkpw(credentials.password.encode(), user["password"].encode()):
        # Increment failed attempts
        failed_attempts = user.get("failed_login_attempts", 0) + 1
        update_data = {"failed_login_attempts": failed_attempts}
        
        # Lock account after 5 failed attempts
        if failed_attempts >= 5:
            update_data["locked_until"] = datetime.now(timezone.utc) + timedelta(minutes=30)
            await audit_logger.log_security_event(
                event_type="account_locked",
                severity="warning",
                details={"user_id": user["id"], "failed_attempts": failed_attempts},
                ip_address=get_client_ip(request),
                user_id=user["id"]
            )
        
        await db.users.update_one({"id": user["id"]}, {"$set": update_data})
        raise HTTPException(status_code=400, detail="Invalid credentials")
    
    # Reset failed attempts on successful login
    await db.users.update_one(
        {"id": user["id"]}, 
        {"$set": {
            "failed_login_attempts": 0,
            "locked_until": None,
            "last_login": datetime.now(timezone.utc)
        }}
    )
    
    # Log successful login
    await audit_logger.log_login(
        user_id=user["id"],
        success=True,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent", "unknown")
    )
    
    # Check if 2FA is required
    requires_2fa = user.get("two_factor_enabled", False)
    
    token = jwt.encode(
        {
            "sub": user["id"], 
            "exp": datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS),
            "2fa_verified": not requires_2fa  # Only true if 2FA not enabled
        },
        SECRET_KEY, algorithm=ALGORITHM
    )
    
    user_response = {k: v for k, v in user.items() if k != "password"}
    user_response["requires_2fa"] = requires_2fa
    
    return {"access_token": token, "user": user_response}

@router.post("/login/2fa")
async def login_with_2fa(credentials: UserLogin, totp_code: str, request: Request):
    """Login with 2FA verification"""
    from core.two_factor import two_factor_auth
    
    user = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    
    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")
    
    if not bcrypt.checkpw(credentials.password.encode(), user["password"].encode()):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    
    if not user.get("two_factor_enabled"):
        raise HTTPException(status_code=400, detail="2FA not enabled for this account")
    
    # Verify TOTP
    secret = user.get("two_factor_secret")
    if not two_factor_auth.verify_totp(secret, totp_code):
        await audit_logger.log_security_event(
            event_type="2fa_login_failed",
            severity="warning",
            details={"user_id": user["id"]},
            ip_address=get_client_ip(request),
            user_id=user["id"]
        )
        raise HTTPException(status_code=400, detail="Invalid 2FA code")
    
    # Update last login
    await db.users.update_one(
        {"id": user["id"]}, 
        {"$set": {
            "failed_login_attempts": 0,
            "locked_until": None,
            "last_login": datetime.now(timezone.utc)
        }}
    )
    
    # Log successful 2FA login
    await audit_logger.log_login(
        user_id=user["id"],
        success=True,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent", "unknown")
    )
    
    token = jwt.encode(
        {
            "sub": user["id"], 
            "exp": datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS),
            "2fa_verified": True
        },
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

@router.post("/change-password")
async def change_password(
    password_data: PasswordChangeRequest,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Change password for authenticated user"""
    
    # Validate new password complexity
    is_valid, errors = validate_password(password_data.new_password)
    if not is_valid:
        raise HTTPException(status_code=400, detail={"message": "Password requirements not met", "errors": errors})
    
    # Verify current password
    user = await db.users.find_one({"id": current_user["id"]}, {"password": 1})
    if not bcrypt.checkpw(password_data.current_password.encode(), user["password"].encode()):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    # Hash new password
    new_hashed = bcrypt.hashpw(password_data.new_password.encode(), bcrypt.gensalt()).decode()
    
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$set": {
            "password": new_hashed,
            "last_password_change": datetime.now(timezone.utc)
        }}
    )
    
    await audit_logger.log_security_event(
        event_type="password_changed",
        severity="info",
        details={"user_id": current_user["id"]},
        ip_address=get_client_ip(request),
        user_id=current_user["id"]
    )
    
    return {"message": "Password changed successfully"}

@router.post("/forgot-password")
async def forgot_password(reset_request: PasswordResetRequest, request: Request):
    """Request password reset token"""
    
    user = await db.users.find_one({"email": reset_request.email})
    
    # Always return success to prevent email enumeration
    if not user:
        return {"message": "If an account exists with this email, a reset link will be sent"}
    
    # Generate reset token
    reset_token = secrets.token_urlsafe(32)
    expiry = datetime.now(timezone.utc) + timedelta(hours=1)
    
    await db.password_resets.update_one(
        {"user_id": user["id"]},
        {"$set": {
            "user_id": user["id"],
            "email": reset_request.email,
            "token": reset_token,
            "expires_at": expiry,
            "created_at": datetime.now(timezone.utc)
        }},
        upsert=True
    )
    
    await audit_logger.log_security_event(
        event_type="password_reset_requested",
        severity="info",
        details={"email": reset_request.email},
        ip_address=get_client_ip(request)
    )
    
    # In production, send email with reset link
    # For now, return token (remove in production)
    return {
        "message": "If an account exists with this email, a reset link will be sent",
        "reset_token": reset_token  # Remove in production
    }

@router.post("/reset-password")
async def reset_password(reset_data: PasswordResetConfirm, request: Request):
    """Reset password with token"""
    
    # Validate new password complexity
    is_valid, errors = validate_password(reset_data.new_password)
    if not is_valid:
        raise HTTPException(status_code=400, detail={"message": "Password requirements not met", "errors": errors})
    
    # Find reset token
    reset_record = await db.password_resets.find_one({
        "token": reset_data.token,
        "expires_at": {"$gt": datetime.now(timezone.utc)}
    })
    
    if not reset_record:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    
    user_id = reset_record["user_id"]
    
    # Hash new password
    new_hashed = bcrypt.hashpw(reset_data.new_password.encode(), bcrypt.gensalt()).decode()
    
    await db.users.update_one(
        {"id": user_id},
        {"$set": {
            "password": new_hashed,
            "last_password_change": datetime.now(timezone.utc),
            "failed_login_attempts": 0,
            "locked_until": None
        }}
    )
    
    # Delete reset token
    await db.password_resets.delete_one({"token": reset_data.token})
    
    await audit_logger.log_security_event(
        event_type="password_reset_completed",
        severity="info",
        details={"user_id": user_id},
        ip_address=get_client_ip(request),
        user_id=user_id
    )
    
    return {"message": "Password reset successfully"}

@router.get("/password-requirements")
async def get_password_requirements():
    """Get password complexity requirements"""
    return {
        "min_length": PASSWORD_MIN_LENGTH,
        "requirements": [
            "At least one uppercase letter (A-Z)",
            "At least one lowercase letter (a-z)",
            "At least one digit (0-9)",
            "At least one special character (!@#$%^&*(),.?\":{}|<>)"
        ]
    }
