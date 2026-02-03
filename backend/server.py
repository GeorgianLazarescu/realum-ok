from fastapi import FastAPI, Request
from starlette.middleware.cors import CORSMiddleware
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

from core.security import SecurityHeadersMiddleware, RequestSizeMiddleware
from core.rate_limiter import rate_limiter
from core.backup import database_backup
from core.logging import setup_logging, performance_logger
import asyncio

setup_logging(log_level="INFO", log_file="realum.log")
logger = logging.getLogger("realum")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting REALUM API...")
    await rate_limiter.start()
    backup_task = asyncio.create_task(database_backup.schedule_automatic_backups())

    yield

    logger.info("Shutting down REALUM API...")
    await rate_limiter.stop()
    backup_task.cancel()

app = FastAPI(
    title="REALUM API",
    description="Educational & Economic Metaverse Platform - Production Ready",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestSizeMiddleware, max_size=10 * 1024 * 1024)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start_time) * 1000

    await performance_logger.log_request(
        method=request.method,
        path=request.url.path,
        duration_ms=duration_ms,
        status_code=response.status_code
    )

    return response

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
app.include_router(security_router)
app.include_router(monitoring_router)

@app.get("/")
async def root():
    return {
        "name": "REALUM API",
        "version": "2.0.0",
        "status": "production-ready",
        "security": "enabled",
        "features": [
            "2FA Authentication",
            "GDPR Compliance",
            "Rate Limiting",
            "Automated Backups",
            "Security Monitoring"
        ],
        "docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
