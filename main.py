from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from dotenv import load_dotenv
import os

from api.auth import auth_router
from api.users import users_router
from api.organizations import orgs_router
from api.agents import agents_router
from api.workflows import workflows_router
from api.tasks import tasks_router
from api.integrations import integrations_router
from api.analytics import analytics_router
from api.billing import billing_router
from core.config import settings
from core.auth import get_current_user
from core.exceptions import setup_exception_handlers

load_dotenv()

app = FastAPI(
    title="AI Agent Orchestration Platform API",
    description="Comprehensive API for managing AI agents, workflows, and orchestration",
    version="1.0.0"
)

# Setup exception handlers
setup_exception_handlers(app)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trusted Host Middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"],  # Configure allowed hosts in production
)

# Mount routers
app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(users_router, prefix="/api/v1/users", tags=["users"])
app.include_router(orgs_router, prefix="/api/v1/organizations", tags=["organizations"])
app.include_router(agents_router, prefix="/api/v1/agents", tags=["agents"])
app.include_router(workflows_router, prefix="/api/v1/workflows", tags=["workflows"])
app.include_router(tasks_router, prefix="/api/v1/tasks", tags=["tasks"])
app.include_router(integrations_router, prefix="/api/v1/integrations", tags=["integrations"])
app.include_router(analytics_router, prefix="/api/v1/analytics", tags=["analytics"])
app.include_router(billing_router, prefix="/api/v1/billing", tags=["billing"])

# Health check endpoint
@app.get("/")
async def root():
    return {"message": "AI Agent Orchestration Platform API", "status": "running"}

# WebSocket for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Message text was: {data}")
    except Exception:
        pass
    finally:
        await websocket.close()