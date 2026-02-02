from pydantic import BaseModel, ConfigDict
from typing import List, Optional

class Lesson(BaseModel):
    id: str
    title: str
    content: str
    duration_minutes: int
    quiz: Optional[dict] = None

class Course(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    title: str
    description: str
    category: str
    difficulty: str
    duration_hours: int
    xp_reward: int
    rlm_reward: float
    lessons: List[Lesson] = []
    badge_awarded: Optional[str] = None
