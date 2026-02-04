from fastapi import APIRouter, Depends, HTTPException, Request, Response
from typing import Optional
from datetime import datetime, timedelta
from core.auth import get_current_user, require_admin, get_client_ip
from core.two_factor import two_factor_auth, two_factor_session
from core.gdpr import gdpr_compliance
from core.database import db
from core.logging import audit_logger
from pydantic import BaseModel, EmailStr
import secrets

router = APIRouter(prefix="/api/security", tags=["security"])

# ============== Request/Response Models ==============

class Enable2FAResponse(BaseModel):
    secret: str
    qr_code: str
    backup_codes: list
    message: str

class Verify2FARequest(BaseModel):
    token: str

class VerifyBackupCodeRequest(BaseModel):
    code: str

class ConsentUpdateRequest(BaseModel):
    consent_type: str
    value: bool

class ScheduleDeletionRequest(BaseModel):
    days_from_now: int = 30

class EmailVerificationRequest(BaseModel):
    token: str

# ============== Two-Factor Authentication ==============

@router.post("/2fa/enable", response_model=Enable2FAResponse)
async def enable_2fa(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Enable Two-Factor Authentication for the current user.
    Returns a QR code for Google Authenticator and backup codes.
    """
    try:
        user_email = current_user.get("email")
        user_id = current_user.get("id")

        # Generate 2FA secret and QR code
        secret = two_factor_auth.generate_secret()
        qr_code = two_factor_auth.generate_qr_code(user_email, secret)
        backup_codes = two_factor_auth.generate_backup_codes()

        # Hash backup codes for storage
        hashed_codes = [two_factor_auth.hash_backup_code(code) for code in backup_codes]

        # Store 2FA setup in database (not yet enabled until verified)
        await db.users.update_one(
            {"id": user_id},
            {"$set": {
                "two_factor_secret": secret,
                "two_factor_backup_codes": hashed_codes,
                "two_factor_enabled": False,
                "two_factor_setup_at": datetime.now()
            }}
        )

        # Log security event
        await audit_logger.log_security_event(
            event_type="2fa_setup_initiated",
            severity="info",
            details={"user_id": user_id},
            ip_address=get_client_ip(request),
            user_id=user_id
        )

        return Enable2FAResponse(
            secret=secret,
            qr_code=qr_code,
            backup_codes=backup_codes,
            message="Scan QR code with your authenticator app, then verify with a code"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/2fa/verify")
async def verify_2fa(
    request: Request,
    verify_request: Verify2FARequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Verify 2FA token and enable 2FA for the user.
    """
    try:
        user_id = current_user.get("id")
        
        # Get user's 2FA secret
        user_data = await db.users.find_one({"id": user_id}, {"two_factor_secret": 1})

        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")

        secret = user_data.get("two_factor_secret")
        if not secret:
            raise HTTPException(status_code=400, detail="2FA not set up. Call /2fa/enable first")

        # Verify the TOTP token
        is_valid = two_factor_auth.verify_totp(secret, verify_request.token)

        if not is_valid:
            await audit_logger.log_security_event(
                event_type="2fa_verification_failed",
                severity="warning",
                details={"user_id": user_id},
                ip_address=get_client_ip(request),
                user_id=user_id
            )
            raise HTTPException(status_code=400, detail="Invalid 2FA code")

        # Enable 2FA
        await db.users.update_one(
            {"id": user_id},
            {"$set": {
                "two_factor_enabled": True,
                "two_factor_enabled_at": datetime.now()
            }}
        )

        await audit_logger.log_security_event(
            event_type="2fa_enabled",
            severity="info",
            details={"user_id": user_id},
            ip_address=get_client_ip(request),
            user_id=user_id
        )

        return {"message": "2FA enabled successfully", "success": True}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/2fa/disable")
async def disable_2fa(
    request: Request,
    verify_request: Verify2FARequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Disable 2FA for the current user. Requires valid 2FA token.
    """
    try:
        user_id = current_user.get("id")
        
        user_data = await db.users.find_one(
            {"id": user_id},
            {"two_factor_secret": 1, "two_factor_enabled": 1}
        )

        if not user_data or not user_data.get("two_factor_enabled"):
            raise HTTPException(status_code=400, detail="2FA not enabled")

        secret = user_data.get("two_factor_secret")
        is_valid = two_factor_auth.verify_totp(secret, verify_request.token)

        if not is_valid:
            raise HTTPException(status_code=400, detail="Invalid 2FA code")

        await db.users.update_one(
            {"id": user_id},
            {"$set": {
                "two_factor_enabled": False,
                "two_factor_secret": None,
                "two_factor_backup_codes": None,
                "two_factor_disabled_at": datetime.now()
            }}
        )

        await audit_logger.log_security_event(
            event_type="2fa_disabled",
            severity="warning",
            details={"user_id": user_id},
            ip_address=get_client_ip(request),
            user_id=user_id
        )

        return {"message": "2FA disabled successfully", "success": True}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/2fa/verify-backup-code")
async def verify_backup_code(
    request: Request,
    verify_request: VerifyBackupCodeRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Verify and use a backup code for 2FA recovery.
    """
    try:
        user_id = current_user.get("id")
        
        # Check rate limiting
        if not two_factor_auth.check_rate_limit(user_id):
            raise HTTPException(status_code=429, detail="Too many attempts. Please try again later.")

        user_data = await db.users.find_one(
            {"id": user_id},
            {"two_factor_backup_codes": 1}
        )

        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")

        backup_codes = user_data.get("two_factor_backup_codes", [])
        is_valid = await two_factor_auth.verify_backup_code(user_id, verify_request.code, backup_codes)

        if not is_valid:
            raise HTTPException(status_code=400, detail="Invalid backup code")

        # Remove used backup code
        remaining_codes = await two_factor_auth.remove_used_backup_code(backup_codes, verify_request.code)

        await db.users.update_one(
            {"id": user_id},
            {"$set": {"two_factor_backup_codes": remaining_codes}}
        )

        two_factor_auth.reset_rate_limit(user_id)

        await audit_logger.log_security_event(
            event_type="2fa_backup_code_used",
            severity="warning",
            details={"user_id": user_id, "remaining_codes": len(remaining_codes)},
            ip_address=get_client_ip(request),
            user_id=user_id
        )

        return {
            "message": "Backup code verified successfully",
            "remaining_codes": len(remaining_codes),
            "success": True
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/2fa/regenerate-backup-codes")
async def regenerate_backup_codes(
    request: Request,
    verify_request: Verify2FARequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Regenerate backup codes (requires valid 2FA token).
    """
    try:
        user_id = current_user.get("id")
        
        user_data = await db.users.find_one(
            {"id": user_id},
            {"two_factor_secret": 1, "two_factor_enabled": 1}
        )

        if not user_data or not user_data.get("two_factor_enabled"):
            raise HTTPException(status_code=400, detail="2FA not enabled")

        secret = user_data.get("two_factor_secret")
        is_valid = two_factor_auth.verify_totp(secret, verify_request.token)

        if not is_valid:
            raise HTTPException(status_code=400, detail="Invalid 2FA code")

        # Generate new backup codes
        backup_codes = two_factor_auth.generate_backup_codes()
        hashed_codes = [two_factor_auth.hash_backup_code(code) for code in backup_codes]

        await db.users.update_one(
            {"id": user_id},
            {"$set": {
                "two_factor_backup_codes": hashed_codes,
                "two_factor_codes_regenerated_at": datetime.now()
            }}
        )

        await audit_logger.log_security_event(
            event_type="2fa_backup_codes_regenerated",
            severity="info",
            details={"user_id": user_id},
            ip_address=get_client_ip(request),
            user_id=user_id
        )

        return {
            "message": "Backup codes regenerated successfully",
            "backup_codes": backup_codes,
            "success": True
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/2fa/status")
async def get_2fa_status(current_user: dict = Depends(get_current_user)):
    """
    Get 2FA status for the current user.
    """
    try:
        user_id = current_user.get("id")
        
        user_data = await db.users.find_one(
            {"id": user_id},
            {
                "two_factor_enabled": 1,
                "two_factor_enabled_at": 1,
                "two_factor_backup_codes": 1
            }
        )

        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")

        backup_codes = user_data.get("two_factor_backup_codes", [])

        return {
            "enabled": user_data.get("two_factor_enabled", False),
            "enabled_at": user_data.get("two_factor_enabled_at"),
            "backup_codes_remaining": len(backup_codes) if backup_codes else 0
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============== GDPR Compliance ==============

@router.get("/gdpr/export")
async def export_user_data(
    request: Request,
    format: str = "json",
    current_user: dict = Depends(get_current_user)
):
    """
    Export all user data (GDPR Data Portability - Article 20).
    """
    try:
        user_id = current_user.get("id")
        data = await gdpr_compliance.export_user_data(user_id, format)

        await gdpr_compliance.log_data_access(
            user_id=user_id,
            accessed_by=user_id,
            purpose="self_data_export",
            ip_address=get_client_ip(request)
        )

        return {
            "data": data,
            "format": format,
            "exported_at": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/gdpr/delete-account")
async def delete_account(
    request: Request,
    hard_delete: bool = False,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete user account (GDPR Right to Erasure - Article 17).
    Soft delete by default (anonymizes data), hard delete removes all data.
    """
    try:
        user_id = current_user.get("id")
        success = await gdpr_compliance.delete_user_account(user_id, hard_delete)

        if success:
            await audit_logger.log_security_event(
                event_type="account_deleted",
                severity="critical",
                details={"user_id": user_id, "hard_delete": hard_delete},
                ip_address=get_client_ip(request),
                user_id=user_id
            )

            return {
                "message": "Account deleted successfully",
                "type": "hard_delete" if hard_delete else "soft_delete"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to delete account")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/gdpr/schedule-deletion")
async def schedule_deletion(
    request: Request,
    deletion_request: ScheduleDeletionRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Schedule account deletion for a future date.
    """
    try:
        user_id = current_user.get("id")
        deletion_date = datetime.now() + timedelta(days=deletion_request.days_from_now)
        
        success = await gdpr_compliance.schedule_data_deletion(user_id, deletion_date)

        if success:
            await audit_logger.log_security_event(
                event_type="deletion_scheduled",
                severity="warning",
                details={"user_id": user_id, "scheduled_for": deletion_date.isoformat()},
                ip_address=get_client_ip(request),
                user_id=user_id
            )

            return {
                "message": "Account deletion scheduled",
                "scheduled_for": deletion_date.isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to schedule deletion")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/gdpr/cancel-deletion")
async def cancel_deletion(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Cancel a scheduled account deletion.
    """
    try:
        user_id = current_user.get("id")
        success = await gdpr_compliance.cancel_scheduled_deletion(user_id)

        if success:
            return {"message": "Scheduled deletion cancelled"}
        else:
            return {"message": "No scheduled deletion found"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/gdpr/consent")
async def get_consent(current_user: dict = Depends(get_current_user)):
    """
    Get user consent status for various data processing activities.
    """
    try:
        user_id = current_user.get("id")
        consent = await gdpr_compliance.get_consent_status(user_id)
        return consent

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/gdpr/consent")
async def update_consent(
    request: Request,
    consent_request: ConsentUpdateRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Update user consent for a specific data processing activity.
    """
    try:
        user_id = current_user.get("id")
        
        # Validate consent type
        valid_consent_types = [
            "marketing_emails", "data_analytics", "third_party_sharing",
            "cookie_consent", "personalization", "newsletter"
        ]
        
        if consent_request.consent_type not in valid_consent_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid consent type. Valid types: {valid_consent_types}"
            )
        
        success = await gdpr_compliance.update_consent(
            user_id,
            consent_request.consent_type,
            consent_request.value
        )

        if success:
            await audit_logger.log_security_event(
                event_type="consent_updated",
                severity="info",
                details={
                    "user_id": user_id,
                    "consent_type": consent_request.consent_type,
                    "value": consent_request.value
                },
                ip_address=get_client_ip(request),
                user_id=user_id
            )

            return {"message": "Consent updated successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to update consent")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/gdpr/retention-policy")
async def get_retention_policy(current_user: dict = Depends(get_current_user)):
    """
    Get data retention policy information.
    """
    try:
        user_id = current_user.get("id")
        info = await gdpr_compliance.get_data_retention_info(user_id)
        return info

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/gdpr/access-history")
async def get_access_history(
    days: int = 30,
    current_user: dict = Depends(get_current_user)
):
    """
    Get history of who accessed the user's data.
    """
    try:
        user_id = current_user.get("id")
        history = await gdpr_compliance.get_data_access_history(user_id, days)
        return {"history": history, "days": days}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============== Email Verification ==============

@router.post("/email/request-verification")
async def request_email_verification(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Request email verification token.
    """
    try:
        user_id = current_user.get("id")
        email = current_user.get("email")
        
        if current_user.get("email_verified"):
            return {"message": "Email already verified"}
        
        # Generate verification token
        token = secrets.token_urlsafe(32)
        expiry = datetime.now() + timedelta(hours=24)
        
        await db.email_verifications.update_one(
            {"user_id": user_id},
            {"$set": {
                "user_id": user_id,
                "email": email,
                "token": token,
                "expires_at": expiry,
                "created_at": datetime.now()
            }},
            upsert=True
        )
        
        # In production, send email here
        # For now, return the token (in production, this would be sent via email)
        
        await audit_logger.log_security_event(
            event_type="email_verification_requested",
            severity="info",
            details={"user_id": user_id, "email": email},
            ip_address=get_client_ip(request),
            user_id=user_id
        )
        
        return {
            "message": "Verification email sent",
            "verification_token": token,  # Remove in production - send via email
            "expires_at": expiry.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/email/verify")
async def verify_email(
    request: Request,
    verification: EmailVerificationRequest
):
    """
    Verify email with token.
    """
    try:
        # Find verification record
        record = await db.email_verifications.find_one({
            "token": verification.token,
            "expires_at": {"$gt": datetime.now()}
        })
        
        if not record:
            raise HTTPException(status_code=400, detail="Invalid or expired verification token")
        
        user_id = record.get("user_id")
        
        # Mark email as verified
        await db.users.update_one(
            {"id": user_id},
            {"$set": {
                "email_verified": True,
                "email_verified_at": datetime.now()
            }}
        )
        
        # Delete verification record
        await db.email_verifications.delete_one({"token": verification.token})
        
        await audit_logger.log_security_event(
            event_type="email_verified",
            severity="info",
            details={"user_id": user_id},
            ip_address=get_client_ip(request),
            user_id=user_id
        )
        
        return {"message": "Email verified successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============== Security Status ==============

@router.get("/status")
async def get_security_status(current_user: dict = Depends(get_current_user)):
    """
    Get overall security status for the user.
    """
    try:
        user_id = current_user.get("id")
        
        user_data = await db.users.find_one(
            {"id": user_id},
            {
                "two_factor_enabled": 1,
                "email_verified": 1,
                "last_password_change": 1,
                "created_at": 1
            }
        )
        
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Calculate security score
        score = 0
        recommendations = []
        
        if user_data.get("email_verified"):
            score += 25
        else:
            recommendations.append("Verify your email address")
        
        if user_data.get("two_factor_enabled"):
            score += 50
        else:
            recommendations.append("Enable two-factor authentication")
        
        last_password_change = user_data.get("last_password_change")
        if last_password_change:
            days_since_change = (datetime.now() - last_password_change).days
            if days_since_change < 90:
                score += 25
            else:
                recommendations.append("Consider updating your password")
        else:
            recommendations.append("Consider updating your password")
        
        return {
            "security_score": score,
            "max_score": 100,
            "email_verified": user_data.get("email_verified", False),
            "two_factor_enabled": user_data.get("two_factor_enabled", False),
            "last_password_change": user_data.get("last_password_change"),
            "recommendations": recommendations
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============== Admin Security Endpoints ==============

@router.get("/admin/audit-logs", dependencies=[Depends(require_admin)])
async def get_audit_logs(
    user_id: Optional[str] = None,
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    days: int = 7,
    limit: int = 100
):
    """
    Get security audit logs (admin only).
    """
    try:
        query = {}
        cutoff = datetime.now() - timedelta(days=days)
        query["timestamp"] = {"$gte": cutoff.isoformat()}
        
        if user_id:
            query["user_id"] = user_id
        if event_type:
            query["event_type"] = event_type
        if severity:
            query["details.severity"] = severity
        
        logs = await db.audit_logs.find(
            query,
            {"_id": 0}
        ).sort("timestamp", -1).limit(limit).to_list(None)
        
        return {"logs": logs, "count": len(logs)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
