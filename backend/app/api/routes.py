from fastapi import APIRouter
from .agents import router as agent_router
from .auth import router as auth_router
from .organizations import router as organization_router
from .workflows import router as workflow_router
from .tasks import router as task_router
from .integrations import router as integration_router
from .analytics import router as analytics_router
from .billing import router as billing_router

router = APIRouter()

@router.get("/")
async def api_root():
    return {"message": "API v1", "version": "1.0.0"}

router.include_router(agent_router, prefix="/api/v1/agents", tags=["agents"])
router.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
router.include_router(organization_router, prefix="/api/v1/organizations", tags=["organizations"])
router.include_router(workflow_router, prefix="/api/v1/workflows", tags=["workflows"])
router.include_router(task_router, prefix="/api/v1/tasks", tags=["tasks"])
router.include_router(integration_router, prefix="/api/v1/integrations", tags=["integrations"])
router.include_router(analytics_router, prefix="/api/v1/analytics", tags=["analytics"])
router.include_router(billing_router, prefix="/api/v1/billing", tags=["billing"])