import os
import logging
from datetime import datetime
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, pool
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

from .shared.database import get_db
from .shared.security import get_current_active_user
from .core.router import router as core_router
from .auth import router as auth_router
from .user import router as user_router
from .organization import router as org_router
from .agent import router as agent_router
from .workflow import router as workflow_router
from .task import router as task_router
from .integration import router as integration_router
from .analytics import router as analytics_router
from .billing import router as billing_router
from .core.middleware_setup import setup_middleware

load_dotenv()

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")
engine = create_engine(
    DATABASE_URL,
    poolclass=pool.QueuePool,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_timeout=30
)
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False
)
Base = declarative_base()

# Create FastAPI app
app = FastAPI(
    title="AI Agent Orchestration Platform API",
    description="A comprehensive API for managing AI agents, workflows, and tasks",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup middleware
app = setup_middleware(app, logger)

# Include routers
app.include_router(
    core_router,
    prefix="/api/v1",
    tags=["Core"],
    dependencies=[Depends(get_db)],
    responses={404: {"description": "Not found"}}
)

app.include_router(
    auth_router,
    prefix="/api/v1/auth",
    tags=["Auth"],
    responses={404: {"description": "Not found"}}
)

app.include_router(
    user_router,
    prefix="/api/v1/users",
    tags=["Users"],
    dependencies=[Depends(get_db), Depends(get_current_active_user)],
    responses={404: {"description": "Not found"}}
)

app.include_router(
    org_router,
    prefix="/api/v1/organizations",
    tags=["Organizations"],
    dependencies=[Depends(get_db), Depends(get_current_active_user)],
    responses={404: {"description": "Not found"}}
)

app.include_router(
    agent_router,
    prefix="/api/v1/agents",
    tags=["Agents"],
    dependencies=[Depends(get_db), Depends(get_current_active_user)],
    responses={404: {"description": "Not found"}}
)

app.include_router(
    workflow_router,
    prefix="/api/v1/workflows",
    tags=["Workflows"],
    dependencies=[Depends(get_db), Depends(get_current_active_user)],
    responses={404: {"description": "Not found"}}
)

app.include_router(
    task_router,
    prefix="/api/v1/tasks",
    tags=["Tasks"],
    dependencies=[Depends(get_db), Depends(get_current_active_user)],
    responses={404: {"description": "Not found"}}
)

app.include_router(
    integration_router,
    prefix="/api/v1/integrations",
    tags=["Integrations"],
    dependencies=[Depends(get_db), Depends(get_current_active_user)],
    responses={404: {"description": "Not found"}}
)

app.include_router(
    analytics_router,
    prefix="/api/v1/analytics",
    tags=["Analytics"],
    dependencies=[Depends(get_db), Depends(get_current_active_user)],
    responses={404: {"description": "Not found"}}
)

app.include_router(
    billing_router,
    prefix="/api/v1/billing",
    tags=["Billing"],
    dependencies=[Depends(get_db), Depends(get_current_active_user)],
    responses={404: {"description": "Not found"}}
)

@app.get("/")
def read_root():
    """Root endpoint."""
    return {
        "message": "AI Agent Orchestration Platform API",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "auth": "/api/v1/auth",
            "users": "/api/v1/users",
            "organizations": "/api/v1/organizations",
            "agents": "/api/v1/agents",
            "workflows": "/api/v1/workflows",
            "tasks": "/api/v1/tasks",
            "integrations": "/api/v1/integrations",
            "analytics": "/api/v1/analytics",
            "billing": "/api/v1/billing"
        }
    }

@app.get("/health")
def health_check():
    """Health check endpoint."""
    try:
        # Test database connection
        db = next(get_db())
        db.execute("SELECT 1")
        db.close()

        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "database": "connected",
            "api": "operational"
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

@app.get("/metrics")
def get_metrics():
    """Get API metrics."""
    # In a real implementation, you would gather metrics from monitoring system
    return {
        "timestamp": datetime.now().isoformat(),
        "requests": {
            "total": 1234,
            "per_minute": 45,
            "success_rate": 98.5
        },
        "response_times": {
            "average": 125.4,  # in ms
            "p95": 250.1,
            "p99": 500.3
        },
        "active_connections": 15,
        "uptime": "99.9%"
    }

@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info("AI Agent Orchestration Platform API starting up...")

    # Create database tables if they don't exist
    try:
        from .shared.models import Base
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created/verified")
    except Exception as e:
        logger.error(f"Failed to create database tables: {str(e)}")
        raise

    logger.info("API startup complete")

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info("AI Agent Orchestration Platform API shutting down...")

    # Close database connections
    try:
        engine.dispose()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database connections: {str(e)}")

    logger.info("API shutdown complete")

if __name__ == "__main__":
    import uvicorn

    # Configure uvicorn
    uvicorn_config = {
        "host": "0.0.0.0",
        "port": 8000,
        "log_level": "info",
        "workers": int(os.getenv("WORKERS", 1)),
        "reload": os.getenv("DEBUG", "false").lower() == "true"
    }

    logger.info(f"Starting API server with config: {uvicorn_config}")
    uvicorn.run(app, **uvicorn_config)