from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from core.auth import get_current_user
from core.database import db
from services.token_service import TokenService

router = APIRouter(prefix="/api/subdaos", tags=["SubDAOs"])
token_service = TokenService()

class SubDAOCreate(BaseModel):
    name: str
    description: str
    category: str
    parent_dao_id: Optional[str] = None
    budget_request: float
    governance_model: str

class BudgetAllocation(BaseModel):
    amount: float
    purpose: str

class MemberInvite(BaseModel):
    user_id: str
    role: str

@router.post("/create")
async def create_subdao(subdao: SubDAOCreate, current_user: dict = Depends(get_current_user)):
    try:
        data = {
            "name": subdao.name,
            "description": subdao.description,
            "category": subdao.category,
            "parent_dao_id": subdao.parent_dao_id,
            "creator_id": current_user["id"],
            "budget_allocated": 0,
            "budget_requested": subdao.budget_request,
            "governance_model": subdao.governance_model,
            "status": "pending_approval",
            "member_count": 1
        }

        result = supabase.table("subdaos").insert(data).execute()
        subdao_id = result.data[0]["id"]

        member_data = {
            "subdao_id": subdao_id,
            "user_id": current_user["id"],
            "role": "founder",
            "voting_power": 100
        }

        supabase.table("subdao_members").insert(member_data).execute()

        return {
            "message": "Sub-DAO created successfully",
            "subdao": result.data[0]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/list")
async def list_subdaos(
    status: Optional[str] = None,
    category: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    try:
        query = supabase.table("subdaos").select("*, users(username, avatar)")

        if status:
            query = query.eq("status", status)
        if category:
            query = query.eq("category", category)

        result = query.order("created_at", desc=True).execute()

        return {"subdaos": result.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{subdao_id}")
async def get_subdao_details(subdao_id: str, current_user: dict = Depends(get_current_user)):
    try:
        subdao_result = supabase.table("subdaos").select("*, users(username, avatar)").eq("id", subdao_id).execute()

        if not subdao_result.data:
            raise HTTPException(status_code=404, detail="Sub-DAO not found")

        members_result = supabase.table("subdao_members").select("*, users(username, avatar)").eq("subdao_id", subdao_id).execute()

        proposals_result = supabase.table("subdao_proposals").select("*").eq("subdao_id", subdao_id).execute()

        return {
            "subdao": subdao_result.data[0],
            "members": members_result.data,
            "proposals": proposals_result.data
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{subdao_id}/allocate-budget")
async def allocate_budget(
    subdao_id: str,
    allocation: BudgetAllocation,
    current_user: dict = Depends(get_current_user)
):
    try:
        subdao_result = supabase.table("subdaos").select("*").eq("id", subdao_id).execute()

        if not subdao_result.data:
            raise HTTPException(status_code=404, detail="Sub-DAO not found")

        subdao = subdao_result.data[0]

        if subdao["status"] != "active":
            raise HTTPException(status_code=400, detail="Sub-DAO must be active to receive budget allocation")

        current_budget = float(subdao.get("budget_allocated", 0))
        new_budget = current_budget + allocation.amount

        supabase.table("subdaos").update({"budget_allocated": new_budget}).eq("id", subdao_id).execute()

        allocation_data = {
            "subdao_id": subdao_id,
            "amount": allocation.amount,
            "purpose": allocation.purpose,
            "allocated_by": current_user["id"]
        }

        supabase.table("subdao_budget_allocations").insert(allocation_data).execute()

        return {
            "message": "Budget allocated successfully",
            "new_budget": new_budget
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{subdao_id}/invite")
async def invite_member(
    subdao_id: str,
    invite: MemberInvite,
    current_user: dict = Depends(get_current_user)
):
    try:
        member_check = supabase.table("subdao_members").select("role").eq("subdao_id", subdao_id).eq("user_id", current_user["id"]).execute()

        if not member_check.data or member_check.data[0]["role"] not in ["founder", "admin"]:
            raise HTTPException(status_code=403, detail="Only founders and admins can invite members")

        existing_member = supabase.table("subdao_members").select("*").eq("subdao_id", subdao_id).eq("user_id", invite.user_id).execute()

        if existing_member.data:
            raise HTTPException(status_code=400, detail="User is already a member")

        member_data = {
            "subdao_id": subdao_id,
            "user_id": invite.user_id,
            "role": invite.role,
            "voting_power": 10
        }

        result = supabase.table("subdao_members").insert(member_data).execute()

        subdao_result = supabase.table("subdaos").select("member_count").eq("id", subdao_id).execute()
        current_count = subdao_result.data[0].get("member_count", 0)
        supabase.table("subdaos").update({"member_count": current_count + 1}).eq("id", subdao_id).execute()

        return {
            "message": "Member invited successfully",
            "member": result.data[0]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{subdao_id}/approve")
async def approve_subdao(subdao_id: str, current_user: dict = Depends(get_current_user)):
    try:
        user_result = supabase.table("users").select("role").eq("id", current_user["id"]).execute()

        if not user_result.data or user_result.data[0].get("role") not in ["partner", "evaluator"]:
            raise HTTPException(status_code=403, detail="Only partners and evaluators can approve sub-DAOs")

        supabase.table("subdaos").update({"status": "active"}).eq("id", subdao_id).execute()

        return {"message": "Sub-DAO approved successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/my-subdaos")
async def get_my_subdaos(current_user: dict = Depends(get_current_user)):
    try:
        created_result = supabase.table("subdaos").select("*").eq("creator_id", current_user["id"]).execute()

        member_result = supabase.table("subdao_members").select("subdao_id").eq("user_id", current_user["id"]).execute()

        member_subdao_ids = [m["subdao_id"] for m in member_result.data] if member_result.data else []
        member_subdaos = []

        if member_subdao_ids:
            for subdao_id in member_subdao_ids:
                subdao_result = supabase.table("subdaos").select("*").eq("id", subdao_id).execute()
                if subdao_result.data:
                    member_subdaos.extend(subdao_result.data)

        return {
            "created_subdaos": created_result.data,
            "member_subdaos": member_subdaos
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/hierarchy")
async def get_dao_hierarchy():
    try:
        all_subdaos = supabase.table("subdaos").select("*").eq("status", "active").execute()

        root_daos = []
        child_daos = {}

        for subdao in all_subdaos.data if all_subdaos.data else []:
            parent_id = subdao.get("parent_dao_id")

            if not parent_id:
                root_daos.append(subdao)
            else:
                if parent_id not in child_daos:
                    child_daos[parent_id] = []
                child_daos[parent_id].append(subdao)

        def build_tree(dao):
            dao_id = dao["id"]
            dao["children"] = child_daos.get(dao_id, [])
            for child in dao["children"]:
                build_tree(child)
            return dao

        hierarchy = [build_tree(dao) for dao in root_daos]

        return {"hierarchy": hierarchy}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/stats")
async def get_subdao_stats():
    try:
        all_subdaos = supabase.table("subdaos").select("*").execute()

        total_subdaos = len(all_subdaos.data) if all_subdaos.data else 0
        total_budget = sum(float(s.get("budget_allocated", 0)) for s in all_subdaos.data) if all_subdaos.data else 0

        status_breakdown = {}
        for subdao in all_subdaos.data if all_subdaos.data else []:
            status = subdao.get("status", "unknown")
            status_breakdown[status] = status_breakdown.get(status, 0) + 1

        category_breakdown = {}
        for subdao in all_subdaos.data if all_subdaos.data else []:
            category = subdao.get("category", "unknown")
            category_breakdown[category] = category_breakdown.get(category, 0) + 1

        return {
            "stats": {
                "total_subdaos": total_subdaos,
                "total_budget_allocated": total_budget,
                "status_breakdown": status_breakdown,
                "category_breakdown": category_breakdown
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
