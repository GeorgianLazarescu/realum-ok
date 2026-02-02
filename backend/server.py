from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
import logging

# Import routers
from routers.auth import router as auth_router
from routers.wallet import router as wallet_router, token_router
from routers.jobs import router as jobs_router
from routers.courses import router as courses_router
from routers.dao import router as dao_router
from routers.projects import router as projects_router
from routers.simulation import router as simulation_router
from routers.stats import router as stats_router
from routers.admin import router as admin_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the main app
app = FastAPI(
    title="REALUM API",
    description="Educational & Economic Metaverse Platform - Refactored",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers under /api prefix
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

@app.get("/")
async def root():
    return {
        "name": "REALUM API",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
