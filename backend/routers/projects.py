from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime, timezone
import uuid

from ..core.database import db
from ..core.auth import get_current_user
from ..models.project import Project, ProjectCreate, TaskCreate
from ..services.token_service import add_xp, award_badge, create_transaction

router = APIRouter(prefix="/projects", tags=["Projects"])

@router.get("")
async def get_projects(status: Optional[str] = None, category: Optional[str] = None):
    query = {}
    if status:
        query["status"] = status
    if category:
        query["category"] = category
    projects = await db.projects.find(query, {"_id": 0}).to_list(100)
    return {"projects": projects}

@router.get("/{project_id}")
async def get_project(project_id: str):
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.post("")
async def create_project(
    data: ProjectCreate,
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] not in ["creator", "partner"]:
        raise HTTPException(status_code=403, detail="Only creators and partners can create projects")
    
    project = {
        "id": str(uuid.uuid4()),
        "title": data.title,
        "description": data.description,
        "category": data.category,
        "creator_id": current_user["id"],
        "creator_name": current_user["username"],
        "budget_rlm": data.budget_rlm,
        "status": "active",
        "progress": 0,
        "participants": [current_user["id"]],
        "tasks": [],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.projects.insert_one(project)
    
    # Award project creator badge
    await award_badge(current_user["id"], "project_pioneer")
    
    return {"status": "created", "project_id": project["id"]}

@router.post("/{project_id}/join")
async def join_project(project_id: str, current_user: dict = Depends(get_current_user)):
    project = await db.projects.find_one({"id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if current_user["id"] in project.get("participants", []):
        raise HTTPException(status_code=400, detail="Already a participant")
    
    await db.projects.update_one(
        {"id": project_id},
        {"$push": {"participants": current_user["id"]}}
    )
    
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$addToSet": {"projects_joined": project_id}}
    )
    
    return {"status": "joined", "project": project["title"]}

@router.post("/{project_id}/task")
async def add_project_task(
    project_id: str,
    data: TaskCreate,
    current_user: dict = Depends(get_current_user)
):
    project = await db.projects.find_one({"id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project["creator_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Only project creator can add tasks")
    
    task = {
        "id": str(uuid.uuid4()),
        "title": data.title,
        "description": data.description,
        "assignee_id": None,
        "status": "open",
        "reward_rlm": data.reward_rlm,
        "xp_reward": data.xp_reward
    }
    
    await db.projects.update_one(
        {"id": project_id},
        {"$push": {"tasks": task}}
    )
    
    return {"status": "task_added", "task_id": task["id"]}

@router.post("/{project_id}/task/{task_id}/complete")
async def complete_project_task(
    project_id: str,
    task_id: str,
    current_user: dict = Depends(get_current_user)
):
    project = await db.projects.find_one({"id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if current_user["id"] not in project.get("participants", []):
        raise HTTPException(status_code=403, detail="Not a project participant")
    
    task = next((t for t in project.get("tasks", []) if t["id"] == task_id), None)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task["status"] == "completed":
        raise HTTPException(status_code=400, detail="Task already completed")
    
    # Update task status
    await db.projects.update_one(
        {"id": project_id, "tasks.id": task_id},
        {"$set": {"tasks.$.status": "completed", "tasks.$.assignee_id": current_user["id"]}}
    )
    
    # Calculate new progress
    tasks = project.get("tasks", [])
    completed_tasks = sum(1 for t in tasks if t["status"] == "completed") + 1
    progress = (completed_tasks / len(tasks) * 100) if tasks else 100
    
    await db.projects.update_one(
        {"id": project_id},
        {"$set": {"progress": progress}}
    )
    
    # Award rewards
    if task.get("reward_rlm", 0) > 0:
        await db.users.update_one(
            {"id": current_user["id"]},
            {"$inc": {"realum_balance": task["reward_rlm"]}}
        )
        await create_transaction(
            current_user["id"], "credit", task["reward_rlm"],
            f"Task completed: {task['title']}"
        )
    
    if task.get("xp_reward", 0) > 0:
        await add_xp(current_user["id"], task["xp_reward"])
    
    return {
        "status": "completed",
        "reward_rlm": task.get("reward_rlm", 0),
        "xp_reward": task.get("xp_reward", 0),
        "project_progress": progress
    }
