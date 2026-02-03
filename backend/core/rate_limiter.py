from datetime import datetime, timedelta
from typing import Dict, Optional
from collections import defaultdict
import asyncio
from fastapi import HTTPException, Request
from functools import wraps

class RateLimiter:
    def __init__(self):
        self.requests: Dict[str, list] = defaultdict(list)
        self.blocked_ips: Dict[str, datetime] = {}
        self.cleanup_task = None

    async def start(self):
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self):
        if self.cleanup_task:
            self.cleanup_task.cancel()

    async def _cleanup_loop(self):
        while True:
            await asyncio.sleep(60)
            await self._cleanup_old_requests()

    async def _cleanup_old_requests(self):
        now = datetime.now()
        cutoff = now - timedelta(minutes=10)

        for key in list(self.requests.keys()):
            self.requests[key] = [
                req_time for req_time in self.requests[key]
                if req_time > cutoff
            ]
            if not self.requests[key]:
                del self.requests[key]

        for ip in list(self.blocked_ips.keys()):
            if self.blocked_ips[ip] < now:
                del self.blocked_ips[ip]

    def get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def check_rate_limit(
        self,
        request: Request,
        max_requests: int = 100,
        window_minutes: int = 1,
        user_id: Optional[str] = None
    ) -> bool:
        client_ip = self.get_client_ip(request)

        if client_ip in self.blocked_ips:
            if self.blocked_ips[client_ip] > datetime.now():
                raise HTTPException(
                    status_code=429,
                    detail=f"IP blocked until {self.blocked_ips[client_ip].isoformat()}"
                )
            else:
                del self.blocked_ips[client_ip]

        key = f"{client_ip}:{user_id}" if user_id else client_ip
        now = datetime.now()
        window_start = now - timedelta(minutes=window_minutes)

        recent_requests = [
            req_time for req_time in self.requests[key]
            if req_time > window_start
        ]

        if len(recent_requests) >= max_requests:
            if len(recent_requests) >= max_requests * 2:
                self.blocked_ips[client_ip] = now + timedelta(hours=1)
                raise HTTPException(
                    status_code=429,
                    detail="Too many requests. IP blocked for 1 hour."
                )

            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Max {max_requests} requests per {window_minutes} minute(s)."
            )

        self.requests[key].append(now)
        return True

    async def block_ip(self, ip: str, duration_hours: int = 24):
        self.blocked_ips[ip] = datetime.now() + timedelta(hours=duration_hours)

    async def unblock_ip(self, ip: str):
        if ip in self.blocked_ips:
            del self.blocked_ips[ip]

    def get_rate_limit_tier(self, user_role: str) -> tuple:
        tiers = {
            "admin": (10000, 1),
            "premium": (1000, 1),
            "verified": (500, 1),
            "user": (100, 1),
            "anonymous": (20, 1)
        }
        return tiers.get(user_role, (100, 1))

rate_limiter = RateLimiter()

def rate_limit(max_requests: int = 100, window_minutes: int = 1):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if request:
                await rate_limiter.check_rate_limit(
                    request,
                    max_requests,
                    window_minutes
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator
