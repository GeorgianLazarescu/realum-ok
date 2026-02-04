from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
import secrets
import hashlib
from core.auth import get_current_user
from core.database import supabase

router = APIRouter(prefix="/api/partners", tags=["Partners"])

class PartnerCreate(BaseModel):
    organization_name: str
    contact_email: EmailStr
    contact_name: str
    website: Optional[str] = None
    description: Optional[str] = None
    integration_type: str

class APIKeyCreate(BaseModel):
    name: str
    permissions: List[str]
    rate_limit: Optional[int] = 1000

class WebhookCreate(BaseModel):
    url: str
    events: List[str]
    secret: Optional[str] = None

@router.post("/apply")
async def apply_for_partnership(partner: PartnerCreate, current_user: dict = Depends(get_current_user)):
    try:
        data = {
            "user_id": current_user["id"],
            "organization_name": partner.organization_name,
            "contact_email": partner.contact_email,
            "contact_name": partner.contact_name,
            "website": partner.website,
            "description": partner.description,
            "integration_type": partner.integration_type,
            "status": "pending",
            "tier": "free"
        }

        result = supabase.table("partners").insert(data).execute()
        return {"message": "Partnership application submitted", "partner": result.data[0]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/my-partnerships")
async def get_my_partnerships(current_user: dict = Depends(get_current_user)):
    try:
        result = supabase.table("partners").select("*").eq("user_id", current_user["id"]).execute()
        return {"partnerships": result.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/api-keys")
async def create_api_key(key_data: APIKeyCreate, current_user: dict = Depends(get_current_user)):
    try:
        partner_result = supabase.table("partners").select("id").eq("user_id", current_user["id"]).eq("status", "approved").execute()

        if not partner_result.data:
            raise HTTPException(status_code=403, detail="No approved partnership found")

        partner_id = partner_result.data[0]["id"]

        api_key = secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        data = {
            "partner_id": partner_id,
            "name": key_data.name,
            "key_hash": key_hash,
            "permissions": key_data.permissions,
            "rate_limit": key_data.rate_limit,
            "is_active": True
        }

        result = supabase.table("partner_api_keys").insert(data).execute()

        return {
            "message": "API key created",
            "api_key": api_key,
            "key_id": result.data[0]["id"],
            "warning": "Save this key securely. It won't be shown again."
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/api-keys")
async def list_api_keys(current_user: dict = Depends(get_current_user)):
    try:
        partner_result = supabase.table("partners").select("id").eq("user_id", current_user["id"]).execute()

        if not partner_result.data:
            return {"api_keys": []}

        partner_id = partner_result.data[0]["id"]

        result = supabase.table("partner_api_keys").select("id, name, permissions, rate_limit, is_active, created_at, last_used").eq("partner_id", partner_id).execute()

        return {"api_keys": result.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/api-keys/{key_id}")
async def revoke_api_key(key_id: str, current_user: dict = Depends(get_current_user)):
    try:
        partner_result = supabase.table("partners").select("id").eq("user_id", current_user["id"]).execute()

        if not partner_result.data:
            raise HTTPException(status_code=403, detail="No partnership found")

        partner_id = partner_result.data[0]["id"]

        supabase.table("partner_api_keys").update({"is_active": False}).eq("id", key_id).eq("partner_id", partner_id).execute()

        return {"message": "API key revoked"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/webhooks")
async def create_webhook(webhook: WebhookCreate, current_user: dict = Depends(get_current_user)):
    try:
        partner_result = supabase.table("partners").select("id").eq("user_id", current_user["id"]).eq("status", "approved").execute()

        if not partner_result.data:
            raise HTTPException(status_code=403, detail="No approved partnership found")

        partner_id = partner_result.data[0]["id"]

        secret = webhook.secret or secrets.token_urlsafe(32)

        data = {
            "partner_id": partner_id,
            "url": webhook.url,
            "events": webhook.events,
            "secret": secret,
            "is_active": True
        }

        result = supabase.table("partner_webhooks").insert(data).execute()

        return {
            "message": "Webhook created",
            "webhook": result.data[0],
            "secret": secret
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/webhooks")
async def list_webhooks(current_user: dict = Depends(get_current_user)):
    try:
        partner_result = supabase.table("partners").select("id").eq("user_id", current_user["id"]).execute()

        if not partner_result.data:
            return {"webhooks": []}

        partner_id = partner_result.data[0]["id"]

        result = supabase.table("partner_webhooks").select("id, url, events, is_active, created_at").eq("partner_id", partner_id).execute()

        return {"webhooks": result.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/stats")
async def get_partner_stats(current_user: dict = Depends(get_current_user)):
    try:
        partner_result = supabase.table("partners").select("id").eq("user_id", current_user["id"]).execute()

        if not partner_result.data:
            return {"stats": None}

        partner_id = partner_result.data[0]["id"]

        api_calls_result = supabase.table("partner_api_usage").select("*").eq("partner_id", partner_id).execute()

        total_calls = len(api_calls_result.data) if api_calls_result.data else 0

        return {
            "stats": {
                "total_api_calls": total_calls,
                "partner_id": partner_id
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

async def verify_api_key(api_key: str = Header(None, alias="X-API-Key")):
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")

    key_hash = hashlib.sha256(api_key.encode()).hexdigest()

    result = supabase.table("partner_api_keys").select("*, partners(*)").eq("key_hash", key_hash).eq("is_active", True).execute()

    if not result.data:
        raise HTTPException(status_code=401, detail="Invalid API key")

    key_data = result.data[0]

    supabase.table("partner_api_keys").update({"last_used": datetime.utcnow().isoformat()}).eq("id", key_data["id"]).execute()

    supabase.table("partner_api_usage").insert({
        "partner_id": key_data["partner_id"],
        "endpoint": "/api/partner-endpoint",
        "method": "GET"
    }).execute()

    return key_data

@router.get("/public/courses", dependencies=[Depends(verify_api_key)])
async def get_courses_api():
    try:
        result = supabase.table("courses").select("*").eq("status", "published").execute()
        return {"courses": result.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/public/jobs", dependencies=[Depends(verify_api_key)])
async def get_jobs_api():
    try:
        result = supabase.table("jobs").select("*").eq("status", "open").execute()
        return {"jobs": result.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
