import pyotp
import qrcode
from io import BytesIO
import base64
from datetime import datetime, timedelta
from typing import Optional, Dict
import secrets
import json

class TwoFactorAuth:
    def __init__(self):
        self.backup_codes_cache: Dict[str, list] = {}
        self.recovery_attempts: Dict[str, int] = {}

    def generate_secret(self) -> str:
        return pyotp.random_base32()

    def generate_qr_code(self, user_email: str, secret: str, issuer: str = "REALUM") -> str:
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=user_email,
            issuer_name=issuer
        )

        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        return f"data:image/png;base64,{img_base64}"

    def verify_totp(self, secret: str, token: str) -> bool:
        try:
            totp = pyotp.TOTP(secret)
            return totp.verify(token, valid_window=1)
        except Exception:
            return False

    def generate_backup_codes(self, count: int = 10) -> list:
        codes = []
        for _ in range(count):
            code = '-'.join([
                secrets.token_hex(2).upper()
                for _ in range(3)
            ])
            codes.append(code)
        return codes

    def hash_backup_code(self, code: str) -> str:
        import hashlib
        return hashlib.sha256(code.encode()).hexdigest()

    async def verify_backup_code(self, user_id: str, code: str, stored_codes: list) -> bool:
        hashed_input = self.hash_backup_code(code.upper().replace(" ", "-"))

        for stored_hash in stored_codes:
            if secrets.compare_digest(hashed_input, stored_hash):
                return True
        return False

    async def remove_used_backup_code(self, stored_codes: list, used_code: str) -> list:
        hashed_used = self.hash_backup_code(used_code.upper().replace(" ", "-"))
        return [code for code in stored_codes if code != hashed_used]

    def check_rate_limit(self, user_id: str, max_attempts: int = 5) -> bool:
        attempts = self.recovery_attempts.get(user_id, 0)
        if attempts >= max_attempts:
            return False

        self.recovery_attempts[user_id] = attempts + 1
        return True

    def reset_rate_limit(self, user_id: str):
        if user_id in self.recovery_attempts:
            del self.recovery_attempts[user_id]

    def generate_recovery_token(self) -> str:
        return secrets.token_urlsafe(32)

    async def send_2fa_code_via_sms(self, phone_number: str) -> str:
        code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
        return code

    def validate_phone_number(self, phone: str) -> bool:
        import re
        pattern = r'^\+?[1-9]\d{1,14}$'
        return bool(re.match(pattern, phone))

two_factor_auth = TwoFactorAuth()

class TwoFactorSession:
    def __init__(self):
        self.pending_verifications: Dict[str, dict] = {}

    def create_verification_session(
        self,
        user_id: str,
        method: str,
        expires_in_minutes: int = 10
    ) -> str:
        session_id = secrets.token_urlsafe(16)
        expiry = datetime.now() + timedelta(minutes=expires_in_minutes)

        self.pending_verifications[session_id] = {
            "user_id": user_id,
            "method": method,
            "expiry": expiry,
            "verified": False
        }

        return session_id

    def verify_session(self, session_id: str) -> Optional[str]:
        if session_id not in self.pending_verifications:
            return None

        session = self.pending_verifications[session_id]
        if session["expiry"] < datetime.now():
            del self.pending_verifications[session_id]
            return None

        if not session["verified"]:
            return None

        user_id = session["user_id"]
        del self.pending_verifications[session_id]
        return user_id

    def mark_session_verified(self, session_id: str) -> bool:
        if session_id in self.pending_verifications:
            self.pending_verifications[session_id]["verified"] = True
            return True
        return False

    def cleanup_expired_sessions(self):
        now = datetime.now()
        expired = [
            sid for sid, data in self.pending_verifications.items()
            if data["expiry"] < now
        ]
        for sid in expired:
            del self.pending_verifications[sid]

two_factor_session = TwoFactorSession()
