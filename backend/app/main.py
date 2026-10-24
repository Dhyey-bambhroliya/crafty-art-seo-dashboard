import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.core.database import init_db
from backend.app.core.scheduler import start_scheduler, shutdown_scheduler

# Import routes
from backend.app.api.routes import auth, users, categories, pages, dashboard, alerts, gsc

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("crafty_art_seo")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize Database and Start Scheduler
    logger.info("Initializing database models...")
    init_db()
    logger.info("Database initialized successfully.")
    
    try:
        start_scheduler()
    except Exception as e:
        logger.warning(f"Could not start background scheduler: {str(e)}")
        
    yield
    
    # Shutdown
    logger.info("Shutting down background scheduler...")
    shutdown_scheduler()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Production-grade SEO Management & Monitoring Dashboard for Crafty Art.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration for Vite Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoints for Render and uptime pingers
@app.get("/api/health", tags=["Health"])
@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "app": settings.PROJECT_NAME,
        "version": "1.0.0"
    }

# Register API Routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(users.router, prefix=settings.API_V1_STR)
app.include_router(categories.router, prefix=settings.API_V1_STR)
app.include_router(pages.router, prefix=settings.API_V1_STR)
app.include_router(dashboard.router, prefix=settings.API_V1_STR)
app.include_router(alerts.router, prefix=settings.API_V1_STR)
app.include_router(gsc.router, prefix=settings.API_V1_STR)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
