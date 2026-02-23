from fastapi import APIRouter
from .agents import router as agents_router

router = APIRouter()

router.include_router(agents_router, prefix="/agents", tags=["agents"])

@router.get("/")
async def api_root():
    return {"message": "API v1 Agents", "version": "1.0.0"}