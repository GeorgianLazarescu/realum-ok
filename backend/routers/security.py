from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Optional
from backend.core.auth import get_current_user, require_admin
from backend.core.two_factor import two_factor_auth, two_factor_session
from backend.core.gdpr import GDPRCompliance
from backend.core.database import get_supabase
from backend.core.validation import UserRegistrationSchema
from backend.core.logging import audit_logger
from pydantic import BaseModel

router = APIRouter(prefix="/api/security", tags=["security"])

class Enable2FAResponse(BaseModel):
    secret: str
    qr_code: str
    backup_codes: list

class Verify2FARequest(BaseModel):
    token: str

class VerifyBackupCodeRequest(BaseModel):
    code: str

class ConsentUpdateRequest(BaseModel):
    consent_type: str
    value: bool

@router.post("/2fa/enable")
async def enable_2fa(
    request: Request,
    current_user: dict = Depends(get_current_user),
    supabase = Depends(get_supabase)
):
    try:
        user_email = current_user.get("email")

        secret = two_factor_auth.generate_secret()
        qr_code = two_factor_auth.generate_qr_code(user_email, secret)
        backup_codes = two_factor_auth.generate_backup_codes()

        hashed_codes = [two_factor_auth.hash_backup_code(code) for code in backup_codes]

        supabase.table("users").update({
            "two_factor_secret": secret,
            "two_factor_backup_codes": hashed_codes,
            "two_factor_enabled": False
        }).eq("id", current_user["id"]).execute()

        await audit_logger.log_security_event(
            event_type="2fa_setup_initiated",
            severity="info",
            details={"user_id": current_user["id"]},
            ip_address=request.client.host if request.client else None,
            user_id=current_user["id"]
        )

        return Enable2FAResponse(
            secret=secret,
            qr_code=qr_code,
            backup_codes=backup_codes
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/2fa/verify")
async def verify_2fa(
    request: Request,
    verify_request: Verify2FARequest,
    current_user: dict = Depends(get_current_user),
    supabase = Depends(get_supabase)
):
    try:
        user_data = supabase.table("users").select("two_factor_secret").eq("id", current_user["id"]).execute()

        if not user_data.data:
            raise HTTPException(status_code=404, detail="User not found")

        secret = user_data.data[0].get("two_factor_secret")
        if not secret:
            raise HTTPException(status_code=400, detail="2FA not set up")

        is_valid = two_factor_auth.verify_totp(secret, verify_request.token)

        if not is_valid:
            await audit_logger.log_security_event(
                event_type="2fa_verification_failed",
                severity="warning",
                details={"user_id": current_user["id"]},
                ip_address=request.client.host if request.client else None,
                user_id=current_user["id"]
            )
            raise HTTPException(status_code=400, detail="Invalid 2FA code")

        supabase.table("users").update({
            "two_factor_enabled": True
        }).eq("id", current_user["id"]).execute()

        await audit_logger.log_security_event(
            event_type="2fa_enabled",
            severity="info",
            details={"user_id": current_user["id"]},
            ip_address=request.client.host if request.client else None,
            user_id=current_user["id"]
        )

        return {"message": "2FA enabled successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/2fa/disable")
async def disable_2fa(
    request: Request,
    verify_request: Verify2FARequest,
    current_user: dict = Depends(get_current_user),
    supabase = Depends(get_supabase)
):
    try:
        user_data = supabase.table("users").select("two_factor_secret, two_factor_enabled").eq("id", current_user["id"]).execute()

        if not user_data.data or not user_data.data[0].get("two_factor_enabled"):
            raise HTTPException(status_code=400, detail="2FA not enabled")

        secret = user_data.data[0].get("two_factor_secret")
        is_valid = two_factor_auth.verify_totp(secret, verify_request.token)

        if not is_valid:
            raise HTTPException(status_code=400, detail="Invalid 2FA code")

        supabase.table("users").update({
            "two_factor_enabled": False,
            "two_factor_secret": None,
            "two_factor_backup_codes": None
        }).eq("id", current_user["id"]).execute()

        await audit_logger.log_security_event(
            event_type="2fa_disabled",
            severity="warning",
            details={"user_id": current_user["id"]},
            ip_address=request.client.host if request.client else None,
            user_id=current_user["id"]
        )

        return {"message": "2FA disabled successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/2fa/verify-backup-code")
async def verify_backup_code(
    request: Request,
    verify_request: VerifyBackupCodeRequest,
    current_user: dict = Depends(get_current_user),
    supabase = Depends(get_supabase)
):
    try:
        if not two_factor_auth.check_rate_limit(current_user["id"]):
            raise HTTPException(status_code=429, detail="Too many attempts. Please try again later.")

        user_data = supabase.table("users").select("two_factor_backup_codes").eq("id", current_user["id"]).execute()

        if not user_data.data:
            raise HTTPException(status_code=404, detail="User not found")

        backup_codes = user_data.data[0].get("two_factor_backup_codes", [])
        is_valid = await two_factor_auth.verify_backup_code(current_user["id"], verify_request.code, backup_codes)

        if not is_valid:
            raise HTTPException(status_code=400, detail="Invalid backup code")

        remaining_codes = await two_factor_auth.remove_used_backup_code(backup_codes, verify_request.code)

        supabase.table("users").update({
            "two_factor_backup_codes": remaining_codes
        }).eq("id", current_user["id"]).execute()

        two_factor_auth.reset_rate_limit(current_user["id"])

        await audit_logger.log_security_event(
            event_type="2fa_backup_code_used",
            severity="warning",
            details={"user_id": current_user["id"], "remaining_codes": len(remaining_codes)},
            ip_address=request.client.host if request.client else None,
            user_id=current_user["id"]
        )

        return {"message": "Backup code verified", "remaining_codes": len(remaining_codes)}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/gdpr/export")
async def export_user_data(
    format: str = "json",
    current_user: dict = Depends(get_current_user),
    supabase = Depends(get_supabase)
):
    try:
        gdpr = GDPRCompliance(supabase)
        data = await gdpr.export_user_data(current_user["id"], format)

        await audit_logger.log_data_access(
            user_id=current_user["id"],
            resource_type="user_data_export",
            resource_id=current_user["id"],
            ip_address=None
        )

        return {"data": data, "format": format}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/gdpr/delete-account")
async def delete_account(
    request: Request,
    hard_delete: bool = False,
    current_user: dict = Depends(get_current_user),
    supabase = Depends(get_supabase)
):
    try:
        gdpr = GDPRCompliance(supabase)
        success = await gdpr.delete_user_account(current_user["id"], hard_delete)

        if success:
            await audit_logger.log_security_event(
                event_type="account_deleted",
                severity="critical",
                details={"user_id": current_user["id"], "hard_delete": hard_delete},
                ip_address=request.client.host if request.client else None,
                user_id=current_user["id"]
            )

            return {"message": "Account deleted successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete account")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/gdpr/consent")
async def get_consent(
    current_user: dict = Depends(get_current_user),
    supabase = Depends(get_supabase)
):
    try:
        gdpr = GDPRCompliance(supabase)
        consent = await gdpr.get_consent_status(current_user["id"])
        return consent

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/gdpr/consent")
async def update_consent(
    request: Request,
    consent_request: ConsentUpdateRequest,
    current_user: dict = Depends(get_current_user),
    supabase = Depends(get_supabase)
):
    try:
        gdpr = GDPRCompliance(supabase)
        success = await gdpr.update_consent(
            current_user["id"],
            consent_request.consent_type,
            consent_request.value
        )

        if success:
            await audit_logger.log_security_event(
                event_type="consent_updated",
                severity="info",
                details={
                    "user_id": current_user["id"],
                    "consent_type": consent_request.consent_type,
                    "value": consent_request.value
                },
                ip_address=request.client.host if request.client else None,
                user_id=current_user["id"]
            )

            return {"message": "Consent updated successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to update consent")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
