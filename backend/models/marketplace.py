from pydantic import BaseModel, ConfigDict
from typing import List, Optional

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

class MarketplaceItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    title: str
    description: str
    category: str
    price_rlm: float
    seller_id: str
    seller_name: str
    downloads: int = 0
    rating: float = 0.0

class MarketplaceCreate(BaseModel):
    title: str
    description: str
    category: str
    price_rlm: float
