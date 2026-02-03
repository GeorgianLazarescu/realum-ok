from pydantic import BaseModel, EmailStr, Field, validator, constr
from typing import Optional, List
from datetime import datetime
import re
import html

class UserRegistrationSchema(BaseModel):
    username: constr(min_length=3, max_length=30, strip_whitespace=True)
    email: EmailStr
    password: constr(min_length=8, max_length=128)
    full_name: Optional[constr(max_length=100)] = None

    @validator('username')
    def validate_username(cls, v):
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Username can only contain letters, numbers, underscores, and hyphens')
        return v.lower()

    @validator('password')
    def validate_password(cls, v):
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        return v

    @validator('full_name')
    def validate_full_name(cls, v):
        if v:
            return html.escape(v.strip())
        return v

class UserLoginSchema(BaseModel):
    email: EmailStr
    password: str

class CourseCreateSchema(BaseModel):
    title: constr(min_length=3, max_length=200, strip_whitespace=True)
    description: constr(max_length=5000)
    category: constr(max_length=50)
    difficulty: constr(regex='^(beginner|intermediate|advanced)$')
    duration_hours: int = Field(ge=1, le=1000)
    price_tokens: int = Field(ge=0, le=1000000)

    @validator('title', 'description', 'category')
    def sanitize_text(cls, v):
        return html.escape(v.strip())

class ProjectCreateSchema(BaseModel):
    title: constr(min_length=3, max_length=200, strip_whitespace=True)
    description: constr(max_length=10000)
    required_skills: List[constr(max_length=50)]
    budget_tokens: int = Field(ge=0, le=10000000)
    deadline: Optional[datetime] = None

    @validator('title', 'description')
    def sanitize_text(cls, v):
        return html.escape(v.strip())

    @validator('required_skills')
    def validate_skills(cls, v):
        if len(v) > 20:
            raise ValueError('Maximum 20 skills allowed')
        return [html.escape(skill.strip()) for skill in v]

class ProposalCreateSchema(BaseModel):
    title: constr(min_length=10, max_length=200, strip_whitespace=True)
    description: constr(min_length=50, max_length=10000)
    voting_period_days: int = Field(ge=1, le=30, default=7)
    required_quorum: int = Field(ge=1, le=100, default=20)

    @validator('title', 'description')
    def sanitize_text(cls, v):
        return html.escape(v.strip())

class MessageSchema(BaseModel):
    content: constr(min_length=1, max_length=5000, strip_whitespace=True)
    recipient_id: Optional[str] = None
    channel_id: Optional[str] = None

    @validator('content')
    def sanitize_content(cls, v):
        v_clean = html.escape(v.strip())
        if re.search(r'<script|javascript:|onerror=|onclick=', v_clean.lower()):
            raise ValueError('Invalid content detected')
        return v_clean

class CommentSchema(BaseModel):
    content: constr(min_length=1, max_length=2000, strip_whitespace=True)
    parent_id: Optional[str] = None

    @validator('content')
    def sanitize_content(cls, v):
        return html.escape(v.strip())

class SearchQuerySchema(BaseModel):
    query: constr(min_length=1, max_length=200, strip_whitespace=True)
    category: Optional[constr(max_length=50)] = None
    filters: Optional[dict] = None
    page: int = Field(ge=1, default=1)
    page_size: int = Field(ge=1, le=100, default=20)

    @validator('query')
    def sanitize_query(cls, v):
        v_clean = re.sub(r'[^\w\s\-]', '', v)
        return v_clean.strip()

class ProfileUpdateSchema(BaseModel):
    full_name: Optional[constr(max_length=100)] = None
    bio: Optional[constr(max_length=500)] = None
    location: Optional[constr(max_length=100)] = None
    website: Optional[constr(max_length=200)] = None
    skills: Optional[List[constr(max_length=50)]] = None

    @validator('full_name', 'bio', 'location')
    def sanitize_text(cls, v):
        if v:
            return html.escape(v.strip())
        return v

    @validator('website')
    def validate_website(cls, v):
        if v:
            if not re.match(r'^https?://', v):
                raise ValueError('Website must start with http:// or https://')
            return v
        return v

    @validator('skills')
    def validate_skills(cls, v):
        if v and len(v) > 50:
            raise ValueError('Maximum 50 skills allowed')
        return [html.escape(skill.strip()) for skill in v] if v else v

class TransactionSchema(BaseModel):
    recipient_id: str
    amount: int = Field(ge=1, le=1000000)
    transaction_type: constr(regex='^(transfer|payment|reward|refund)$')
    description: Optional[constr(max_length=500)] = None

    @validator('description')
    def sanitize_description(cls, v):
        if v:
            return html.escape(v.strip())
        return v

def sanitize_sql_input(value: str) -> str:
    if not value:
        return value
    dangerous_patterns = [
        r"('\s*(OR|AND)\s*'?\d+'?\s*=\s*'?\d+'?)",
        r"(--|\#|\/\*|\*\/)",
        r"(\bDROP\b|\bDELETE\b|\bTRUNCATE\b|\bEXEC\b|\bEXECUTE\b)",
        r"(\bUNION\b.*\bSELECT\b)",
        r"(\bINSERT\b.*\bINTO\b)",
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, value, re.IGNORECASE):
            raise ValueError("Potential SQL injection detected")

    return value.strip()

def validate_uuid(uuid_string: str) -> bool:
    uuid_pattern = re.compile(
        r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$',
        re.IGNORECASE
    )
    return bool(uuid_pattern.match(uuid_string))
