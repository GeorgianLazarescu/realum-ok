from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import secrets
import hashlib
from datetime import datetime, timedelta

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' https:; "
            "frame-ancestors 'none';"
        )

        return response

class CSRFProtection:
    def __init__(self):
        self.tokens = {}

    def generate_token(self, session_id: str) -> str:
        token = secrets.token_urlsafe(32)
        expiry = datetime.now() + timedelta(hours=1)
        self.tokens[session_id] = {
            "token": token,
            "expiry": expiry
        }
        return token

    def validate_token(self, session_id: str, token: str) -> bool:
        if session_id not in self.tokens:
            return False

        stored = self.tokens[session_id]
        if stored["expiry"] < datetime.now():
            del self.tokens[session_id]
            return False

        is_valid = secrets.compare_digest(stored["token"], token)
        if is_valid:
            del self.tokens[session_id]

        return is_valid

    def cleanup_expired(self):
        now = datetime.now()
        expired = [
            sid for sid, data in self.tokens.items()
            if data["expiry"] < now
        ]
        for sid in expired:
            del self.tokens[sid]

csrf_protection = CSRFProtection()

class IPWhitelistMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, admin_ips: list = None):
        super().__init__(app)
        self.admin_ips = admin_ips or []

    async def dispatch(self, request: Request, call_next: Callable):
        if request.url.path.startswith("/admin") or request.url.path.startswith("/api/admin"):
            client_ip = request.headers.get("X-Forwarded-For", request.client.host)
            if client_ip:
                client_ip = client_ip.split(",")[0].strip()

            if self.admin_ips and client_ip not in self.admin_ips:
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Access forbidden: IP not whitelisted"}
                )

        response = await call_next(request)
        return response

def generate_secure_token(length: int = 32) -> str:
    return secrets.token_urlsafe(length)

def hash_sensitive_data(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()

def verify_hash(data: str, hashed: str) -> bool:
    return secrets.compare_digest(hash_sensitive_data(data), hashed)

class RequestSizeMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_size: int = 10 * 1024 * 1024):
        super().__init__(app)
        self.max_size = max_size

    async def dispatch(self, request: Request, call_next: Callable):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_size:
            return JSONResponse(
                status_code=413,
                content={"detail": "Request entity too large"}
            )

        response = await call_next(request)
        return response

async def validate_request_origin(request: Request, allowed_origins: list):
    origin = request.headers.get("origin")
    if origin and origin not in allowed_origins:
        raise HTTPException(
            status_code=403,
            detail="Origin not allowed"
        )

def generate_api_key() -> str:
    prefix = "realum"
    key = secrets.token_urlsafe(32)
    return f"{prefix}_{key}"

def validate_api_key_format(api_key: str) -> bool:
    if not api_key.startswith("realum_"):
        return False
    if len(api_key) != 50:
        return False
    return True
