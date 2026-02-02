from pydantic import BaseModel, ConfigDict
from typing import List, Optional

class Proposal(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    title: str
    description: str
    proposer_id: str
    proposer_name: str
    status: str = "active"
    votes_for: int = 0
    votes_against: int = 0
    voters: List[str] = []
    created_at: str

class VoteRequest(BaseModel):
    vote_type: str  # "for" or "against"

class ProposalCreate(BaseModel):
    title: str
    description: str

class CityZone(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    description: str
    type: str
    color: str
    buildings: List[dict] = []
    jobs_count: int = 0
