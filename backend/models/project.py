from pydantic import BaseModel, ConfigDict
from typing import List, Optional

class ProjectTask(BaseModel):
    id: str
    title: str
    description: str
    assignee_id: Optional[str] = None
    status: str = "open"
    reward_rlm: float = 0
    xp_reward: int = 0

class Project(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    title: str
    description: str
    category: str
    creator_id: str
    creator_name: str
    budget_rlm: float
    status: str = "active"
    progress: float = 0
    participants: List[str] = []
    tasks: List[ProjectTask] = []
    created_at: str

class ProjectCreate(BaseModel):
    title: str
    description: str
    category: str
    budget_rlm: float

class TaskCreate(BaseModel):
    title: str
    description: str
    reward_rlm: float = 0
    xp_reward: int = 0

class Badge(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    description: str
    icon: str
    rarity: str
    requirement: Optional[str] = None
