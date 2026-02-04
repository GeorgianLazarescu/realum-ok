from fastapi import FastAPI, Request, HTTPException
from starlette.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import time
from contextlib import asynccontextmanager

from routers.auth import router as auth_router
from routers.wallet import router as wallet_router, token_router
from routers.jobs import router as jobs_router
from routers.courses import router as courses_router
from routers.dao import router as dao_router
from routers.projects import router as projects_router
from routers.simulation import router as simulation_router
from routers.stats import router as stats_router
from routers.admin import router as admin_router
from routers.daily import router as daily_router
from routers.referral import router as referral_router
from routers.security import router as security_router
from routers.monitoring import router as monitoring_router
from routers.notifications import router as notifications_router
from routers.chat import router as chat_router
from routers.content import router as content_router
from routers.advanced_features import router as advanced_features_router
from routers.partners import router as partners_router
from routers.analytics import router as analytics_router
from routers.badges import router as badges_router
from routers.feedback import router as feedback_router
from routers.bounties import router as bounties_router
from routers.disputes import router as disputes_router
from routers.reputation import router as reputation_router
from routers.subdaos import router as subdaos_router
from routers.search import router as search_router
from routers.moderation import router as moderation_router
from routers.social import router as social_router
from routers.achievements import router as achievements_router
from routers.seo import router as seo_router
from routers.recommendations import router as recommendations_router
from routers.defi import router as defi_router

from core.security import SecurityHeadersMiddleware, RequestSizeMiddleware
from core.rate_limiter import rate_limiter
from core.backup import database_backup
from core.logging import setup_logging, performance_logger, error_tracker
from core.database import db
import asyncio

setup_logging(log_level="INFO", log_file="realum.log")
logger = logging.getLogger("realum")

async def create_database_indexes():
    """Create MongoDB indexes for performance and security"""
    try:
        # Users collection indexes
        await db.users.create_index("id", unique=True)
        await db.users.create_index("email", unique=True)
        await db.users.create_index("username", unique=True)
        await db.users.create_index("role")
        await db.users.create_index("created_at")
        
        # Transactions collection indexes
        await db.transactions.create_index("user_id")
        await db.transactions.create_index("timestamp")
        await db.transactions.create_index([("user_id", 1), ("timestamp", -1)])
        
        # Audit logs indexes
        await db.audit_logs.create_index("timestamp")
        await db.audit_logs.create_index("user_id")
        await db.audit_logs.create_index("event_type")
        await db.audit_logs.create_index([("timestamp", -1)])
        
        # Email verifications
        await db.email_verifications.create_index("token")
        await db.email_verifications.create_index("user_id")
        await db.email_verifications.create_index("expires_at", expireAfterSeconds=0)
        
        # Password resets
        await db.password_resets.create_index("token")
        await db.password_resets.create_index("user_id")
        await db.password_resets.create_index("expires_at", expireAfterSeconds=0)
        
        # User consent
        await db.user_consent.create_index("user_id", unique=True)
        
        # Consent history
        await db.consent_history.create_index("user_id")
        await db.consent_history.create_index("changed_at")
        
        # Data access log
        await db.data_access_log.create_index("user_id")
        await db.data_access_log.create_index("accessed_at")
        
        # Scheduled deletions
        await db.scheduled_deletions.create_index("user_id")
        await db.scheduled_deletions.create_index("scheduled_for")
        await db.scheduled_deletions.create_index("status")
        
        # Jobs
        await db.jobs.create_index("zone")
        await db.jobs.create_index("status")
        await db.jobs.create_index("created_at")
        
        # Courses
        await db.courses.create_index("category")
        await db.courses.create_index("difficulty")
        
        # Proposals
        await db.proposals.create_index("status")
        await db.proposals.create_index("creator_id")
        
        # Messages (for chat)
        await db.messages.create_index([("sender_id", 1), ("recipient_id", 1)])
        await db.messages.create_index("channel_id")
        await db.messages.create_index("created_at")
        
        logger.info("Database indexes created successfully")
    except Exception as e:
        logger.error(f"Failed to create indexes: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting REALUM API...")
    
    # Create database indexes
    await create_database_indexes()
    
    # Start rate limiter
    await rate_limiter.start()
    
    # Start automatic backup scheduler
    backup_task = asyncio.create_task(database_backup.schedule_automatic_backups())

    yield

    logger.info("Shutting down REALUM API...")
    await rate_limiter.stop()
    backup_task.cancel()

app = FastAPI(
    title="REALUM API",
    description="Educational & Economic Metaverse Platform - Production Ready with P1 Security Modules",
    version="3.0.0",
    lifespan=lifespan
)

# Security Headers Middleware
app.add_middleware(SecurityHeadersMiddleware)

# Request Size Limit (10MB)
app.add_middleware(RequestSizeMiddleware, max_size=10 * 1024 * 1024)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate Limiting Middleware
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Apply rate limiting to all requests"""
    try:
        # Skip rate limiting for health checks
        if request.url.path in ["/", "/health", "/api/health", "/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)
        
        # Determine rate limit based on endpoint
        if request.url.path.startswith("/api/auth"):
            # Stricter limits for auth endpoints
            await rate_limiter.check_rate_limit(request, max_requests=20, window_minutes=1)
        elif request.url.path.startswith("/api/security"):
            # Moderate limits for security endpoints
            await rate_limiter.check_rate_limit(request, max_requests=30, window_minutes=1)
        else:
            # Standard limits for other endpoints
            await rate_limiter.check_rate_limit(request, max_requests=100, window_minutes=1)
        
        return await call_next(request)
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})

# Request Logging Middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests for monitoring"""
    start_time = time.time()
    
    try:
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000

        await performance_logger.log_request(
            method=request.method,
            path=request.url.path,
            duration_ms=duration_ms,
            status_code=response.status_code
        )

        return response
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        
        # Track error
        import traceback
        await error_tracker.track_error(
            error_type=type(e).__name__,
            error_message=str(e),
            stack_trace=traceback.format_exc(),
            context={"path": request.url.path, "method": request.method}
        )
        
        raise

# Include all routers
app.include_router(auth_router, prefix="/api")
app.include_router(wallet_router, prefix="/api")
app.include_router(token_router, prefix="/api")
app.include_router(jobs_router, prefix="/api")
app.include_router(courses_router, prefix="/api")
app.include_router(dao_router, prefix="/api")
app.include_router(projects_router, prefix="/api")
app.include_router(simulation_router, prefix="/api")
app.include_router(stats_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(daily_router, prefix="/api")
app.include_router(referral_router, prefix="/api")
app.include_router(notifications_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(content_router, prefix="/api")
app.include_router(advanced_features_router, prefix="/api")
app.include_router(security_router)
app.include_router(monitoring_router)
app.include_router(partners_router)
app.include_router(analytics_router)
app.include_router(badges_router)
app.include_router(feedback_router)
app.include_router(bounties_router)
app.include_router(disputes_router)
app.include_router(reputation_router)
app.include_router(subdaos_router)
app.include_router(search_router, prefix="/api")
app.include_router(moderation_router, prefix="/api")
app.include_router(social_router, prefix="/api")
app.include_router(achievements_router, prefix="/api")
app.include_router(seo_router)
app.include_router(recommendations_router)
app.include_router(defi_router)

@app.get("/")
async def root():
    return {
        "name": "REALUM API",
        "version": "3.1.0",
        "status": "production-ready",
        "security": {
            "2fa_enabled": True,
            "gdpr_compliant": True,
            "rate_limiting": True,
            "automated_backups": True,
            "audit_logging": True,
            "password_complexity": True,
            "account_lockout": True,
            "email_verification": True
        },
        "total_modules": "130+",
        "p1_modules": [
            "Two-Factor Authentication (M124-128)",
            "GDPR Compliance & Data Portability (M129-133)",
            "Rate Limiting & DDoS Protection (M134-138)",
            "Centralized Logging & Error Tracking (M139-143)",
            "Automated Database Backups (M144-148)"
        ],
        "features": [
            "2FA Authentication (TOTP + Backup Codes)",
            "GDPR Compliance (Export, Delete, Consent)",
            "Rate Limiting (Per-endpoint limits)",
            "Automated MongoDB Backups",
            "Security Monitoring & Audit Logs",
            "Password Complexity Enforcement",
            "Account Lockout Protection",
            "Email Verification System",
            "Partner Integration API",
            "Advanced Analytics Dashboard",
            "Badge Evolution System",
            "Feedback & Contribution Rewards",
            "Task Bounty Marketplace",
            "Dispute Resolution System",
            "Multi-Dimensional Reputation Engine",
            "Sub-DAO Hierarchical System",
            "Advanced Search & Discovery",
            "Content Moderation Queue",
            "Social Features (Follow, Like, Comment)",
            "Advanced Achievement System"
        ],
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "version": "3.1.0",
        "security_modules": "enabled"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
