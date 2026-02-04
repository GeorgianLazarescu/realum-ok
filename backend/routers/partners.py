from fastapi import APIRouter, HTTPException, Depends, Header, Request
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
import uuid
import secrets
import hashlib
import hmac
from core.auth import get_current_user, require_admin
from core.database import db
from core.logging import audit_logger, get_logger

router = APIRouter(prefix="/api/partners", tags=["Partner Integration"])
logger = get_logger("partners")

class PartnerCreate(BaseModel):
    name: str
    description: Optional[str] = None
    website: Optional[str] = None
    contact_email: str
    integration_type: str  # api, oauth, webhook
    permissions: List[str] = []

class PartnerUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    contact_email: Optional[str] = None
    is_active: Optional[bool] = None

class WebhookCreate(BaseModel):
    event_type: str
    target_url: str
    secret: Optional[str] = None

class OAuthClientCreate(BaseModel):
    name: str
    redirect_uris: List[str]
    scopes: List[str] = ["read:profile"]

# Available permissions for partners
PARTNER_PERMISSIONS = [
    "read:users",
    "read:courses",
    "read:projects",
    "read:transactions",
    "read:proposals",
    "write:courses",
    "write:projects",
    "webhook:receive"
]

# Available OAuth scopes
OAUTH_SCOPES = [
    "read:profile",
    "read:balance",
    "read:courses",
    "read:achievements",
    "write:courses"
]

@router.post("/register")
async def register_partner(
    partner: PartnerCreate,
    current_user: dict = Depends(require_admin)
):
    """Register a new partner (admin only)"""
    try:
        partner_id = str(uuid.uuid4())
        api_key = f"rlm_pk_{secrets.token_hex(32)}"
        api_secret = secrets.token_hex(32)
        now = datetime.now(timezone.utc).isoformat()

        # Validate permissions
        for perm in partner.permissions:
            if perm not in PARTNER_PERMISSIONS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid permission: {perm}. Valid: {PARTNER_PERMISSIONS}"
                )

        partner_data = {
            "id": partner_id,
            "name": partner.name,
            "description": partner.description,
            "website": partner.website,
            "contact_email": partner.contact_email,
            "integration_type": partner.integration_type,
            "permissions": partner.permissions,
            "api_key": api_key,
            "api_secret_hash": hashlib.sha256(api_secret.encode()).hexdigest(),
            "is_active": True,
            "rate_limit": 1000,  # requests per hour
            "request_count": 0,
            "created_by": current_user["id"],
            "created_at": now,
            "updated_at": now
        }

        await db.partners.insert_one(partner_data)

        await audit_logger.log_security_event(
            event_type="partner_registered",
            severity="info",
            details={"partner_id": partner_id, "name": partner.name},
            user_id=current_user["id"]
        )

        return {
            "message": "Partner registered successfully",
            "partner_id": partner_id,
            "api_key": api_key,
            "api_secret": api_secret,  # Only shown once!
            "note": "Save the api_secret securely - it won't be shown again"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/list")
async def list_partners(current_user: dict = Depends(require_admin)):
    """List all partners (admin only)"""
    try:
        partners = await db.partners.find(
            {},
            {"_id": 0, "api_secret_hash": 0}
        ).to_list(100)

        return {"partners": partners}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{partner_id}")
async def get_partner_details(
    partner_id: str,
    current_user: dict = Depends(require_admin)
):
    """Get partner details (admin only)"""
    try:
        partner = await db.partners.find_one(
            {"id": partner_id},
            {"_id": 0, "api_secret_hash": 0}
        )

        if not partner:
            raise HTTPException(status_code=404, detail="Partner not found")

        # Get webhooks
        webhooks = await db.partner_webhooks.find(
            {"partner_id": partner_id},
            {"_id": 0, "secret": 0}
        ).to_list(50)

        # Get OAuth clients
        oauth_clients = await db.oauth_clients.find(
            {"partner_id": partner_id},
            {"_id": 0, "client_secret_hash": 0}
        ).to_list(10)

        # Get usage stats
        usage = await db.partner_api_logs.count_documents({"partner_id": partner_id})

        return {
            "partner": partner,
            "webhooks": webhooks,
            "oauth_clients": oauth_clients,
            "total_api_calls": usage
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/{partner_id}")
async def update_partner(
    partner_id: str,
    update: PartnerUpdate,
    current_user: dict = Depends(require_admin)
):
    """Update partner (admin only)"""
    try:
        partner = await db.partners.find_one({"id": partner_id})
        if not partner:
            raise HTTPException(status_code=404, detail="Partner not found")

        update_data = {k: v for k, v in update.dict().items() if v is not None}
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

        await db.partners.update_one(
            {"id": partner_id},
            {"$set": update_data}
        )

        return {"message": "Partner updated"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{partner_id}/rotate-key")
async def rotate_api_key(
    partner_id: str,
    current_user: dict = Depends(require_admin)
):
    """Rotate partner API key (admin only)"""
    try:
        partner = await db.partners.find_one({"id": partner_id})
        if not partner:
            raise HTTPException(status_code=404, detail="Partner not found")

        new_api_key = f"rlm_pk_{secrets.token_hex(32)}"
        new_api_secret = secrets.token_hex(32)

        await db.partners.update_one(
            {"id": partner_id},
            {"$set": {
                "api_key": new_api_key,
                "api_secret_hash": hashlib.sha256(new_api_secret.encode()).hexdigest(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )

        await audit_logger.log_security_event(
            event_type="partner_key_rotated",
            severity="warning",
            details={"partner_id": partner_id},
            user_id=current_user["id"]
        )

        return {
            "message": "API key rotated",
            "api_key": new_api_key,
            "api_secret": new_api_secret
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{partner_id}")
async def revoke_partner(
    partner_id: str,
    current_user: dict = Depends(require_admin)
):
    """Revoke partner access (admin only)"""
    try:
        partner = await db.partners.find_one({"id": partner_id})
        if not partner:
            raise HTTPException(status_code=404, detail="Partner not found")

        await db.partners.update_one(
            {"id": partner_id},
            {"$set": {
                "is_active": False,
                "revoked_at": datetime.now(timezone.utc).isoformat(),
                "revoked_by": current_user["id"]
            }}
        )

        await audit_logger.log_security_event(
            event_type="partner_revoked",
            severity="critical",
            details={"partner_id": partner_id, "name": partner["name"]},
            user_id=current_user["id"]
        )

        return {"message": "Partner access revoked"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ==================== WEBHOOKS ====================

@router.post("/{partner_id}/webhooks")
async def create_webhook(
    partner_id: str,
    webhook: WebhookCreate,
    current_user: dict = Depends(require_admin)
):
    """Create a webhook for a partner"""
    try:
        partner = await db.partners.find_one({"id": partner_id})
        if not partner:
            raise HTTPException(status_code=404, detail="Partner not found")

        if "webhook:receive" not in partner.get("permissions", []):
            raise HTTPException(status_code=403, detail="Partner doesn't have webhook permission")

        webhook_id = str(uuid.uuid4())
        webhook_secret = webhook.secret or secrets.token_hex(32)
        now = datetime.now(timezone.utc).isoformat()

        await db.partner_webhooks.insert_one({
            "id": webhook_id,
            "partner_id": partner_id,
            "event_type": webhook.event_type,
            "target_url": webhook.target_url,
            "secret": webhook_secret,
            "is_active": True,
            "created_at": now
        })

        return {
            "message": "Webhook created",
            "webhook_id": webhook_id,
            "secret": webhook_secret
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{partner_id}/webhooks/{webhook_id}")
async def delete_webhook(
    partner_id: str,
    webhook_id: str,
    current_user: dict = Depends(require_admin)
):
    """Delete a webhook"""
    try:
        result = await db.partner_webhooks.delete_one({
            "id": webhook_id,
            "partner_id": partner_id
        })

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Webhook not found")

        return {"message": "Webhook deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ==================== OAUTH ====================

@router.post("/{partner_id}/oauth/clients")
async def create_oauth_client(
    partner_id: str,
    client: OAuthClientCreate,
    current_user: dict = Depends(require_admin)
):
    """Create an OAuth client for a partner"""
    try:
        partner = await db.partners.find_one({"id": partner_id})
        if not partner:
            raise HTTPException(status_code=404, detail="Partner not found")

        client_id = f"rlm_oa_{secrets.token_hex(16)}"
        client_secret = secrets.token_hex(32)
        now = datetime.now(timezone.utc).isoformat()

        # Validate scopes
        for scope in client.scopes:
            if scope not in OAUTH_SCOPES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid scope: {scope}. Valid: {OAUTH_SCOPES}"
                )

        await db.oauth_clients.insert_one({
            "id": str(uuid.uuid4()),
            "client_id": client_id,
            "client_secret_hash": hashlib.sha256(client_secret.encode()).hexdigest(),
            "partner_id": partner_id,
            "name": client.name,
            "redirect_uris": client.redirect_uris,
            "scopes": client.scopes,
            "is_active": True,
            "created_at": now
        })

        return {
            "message": "OAuth client created",
            "client_id": client_id,
            "client_secret": client_secret
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ==================== PARTNER API (Authenticated by API Key) ====================

async def verify_partner_api_key(x_api_key: str = Header(...), x_api_secret: str = Header(...)):
    """Verify partner API key and secret"""
    partner = await db.partners.find_one({"api_key": x_api_key})
    
    if not partner:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    if not partner.get("is_active"):
        raise HTTPException(status_code=403, detail="Partner access revoked")
    
    # Verify secret
    secret_hash = hashlib.sha256(x_api_secret.encode()).hexdigest()
    if secret_hash != partner.get("api_secret_hash"):
        raise HTTPException(status_code=401, detail="Invalid API secret")
    
    # Check rate limit
    rate_limit = partner.get("rate_limit", 1000)
    request_count = partner.get("request_count", 0)
    
    if request_count >= rate_limit:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # Increment request count
    await db.partners.update_one(
        {"id": partner["id"]},
        {"$inc": {"request_count": 1}}
    )
    
    return partner

@router.get("/api/v1/users/count")
async def partner_get_user_count(partner: dict = Depends(verify_partner_api_key)):
    """Partner API: Get total user count"""
    if "read:users" not in partner.get("permissions", []):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    count = await db.users.count_documents({})
    return {"user_count": count}

@router.get("/api/v1/courses")
async def partner_get_courses(partner: dict = Depends(verify_partner_api_key)):
    """Partner API: Get courses"""
    if "read:courses" not in partner.get("permissions", []):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    courses = await db.courses.find(
        {},
        {"_id": 0, "id": 1, "title": 1, "category": 1, "difficulty": 1}
    ).to_list(100)
    
    return {"courses": courses}

@router.get("/api/v1/stats")
async def partner_get_stats(partner: dict = Depends(verify_partner_api_key)):
    """Partner API: Get platform stats"""
    users = await db.users.count_documents({})
    courses = await db.courses.count_documents({})
    projects = await db.projects.count_documents({})
    proposals = await db.proposals.count_documents({})
    
    return {
        "stats": {
            "total_users": users,
            "total_courses": courses,
            "total_projects": projects,
            "total_proposals": proposals
        }
    }

@router.get("/permissions")
async def get_available_permissions():
    """Get available partner permissions"""
    return {
        "permissions": PARTNER_PERMISSIONS,
        "oauth_scopes": OAUTH_SCOPES
    }
