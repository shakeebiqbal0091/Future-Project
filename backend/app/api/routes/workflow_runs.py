from typing import Any, Dict, Optional
from datetime import datetime, timedelta
import jwt
import redis
from fastapi import APIRouter, Depends, HTTPException, status, JSONResponse
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.core.security.auth_handler import AuthHandler
from app.core.security.utils import PasswordUtils, JWTUtils, RateLimiter, InputValidator
from app.models.models import User, Agent, AgentVersion, Task, TaskStatusEnum, StatusEnum, RoleEnum, PlanEnum, Workflow, WorkflowRun, WorkflowStatusEnum
from app.schemas.workflows import (
    WorkflowRun, WorkflowRunCreate, WorkflowRunList, WorkflowRunResponse,
    WorkflowErrorResponse, RateLimitHeaders
)

router = APIRouter()

# Authentication dependencies
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# Helper functions
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends()) -> User:
    return await AuthHandler.get_current_active_user(token, db)

async def get_current_org(user: User = Depends(get_current_user)) -> User:
    return user

# Rate limiting configurations
RATE_LIMIT_GET = {"key": "runs:get", "max_requests": 100, "window_seconds": 3600}
RATE_LIMIT_CANCEL = {"key": "runs:cancel", "max_requests": 50, "window_seconds": 3600}
RATE_LIMIT_LOGS = {"key": "runs:logs", "max_requests": 100, "window_seconds": 3600}
RATE_LIMIT_RETRY = {"key": "runs:retry", "max_requests": 50, "window_seconds": 3600}

# GET /api/v1/runs/{id} - Get run details
@router.get("/runs/{run_id}", response_model=WorkflowRunResponse, status_code=status.HTTP_200_OK)
async def get_run_details(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Rate limiting
    rate_limit_key = f"{RATE_LIMIT_GET['key']}:{current_user.id}"
    if RateLimiter.is_rate_limited(rate_limit_key, RATE_LIMIT_GET["max_requests"], RATE_LIMIT_GET["window_seconds"]):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many run details retrieval attempts. Try again later."
        )

    # Find run
    run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow run with id {run_id} not found"
        )

    # Check authorization - ensure run belongs to current user's organization
    if run.workflow.organization_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this workflow run"
        )

    return WorkflowRunResponse(
        run=WorkflowRun(
            id=str(run.id),
            workflow_id=str(run.workflow_id),
            status=run.status.value,
            input=run.input,
            output=run.output,
            error=run.error,
            started_at=run.started_at,
            completed_at=run.completed_at,
            duration_ms=run.duration_ms
        )
    )

# POST /api/v1/runs/{id}/cancel - Cancel run
@router.post("/runs/{run_id}/cancel", response_model=WorkflowRunResponse, status_code=status.HTTP_200_OK)
async def cancel_run(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Rate limiting
    rate_limit_key = f"{RATE_LIMIT_CANCEL['key']}:{current_user.id}"
    if RateLimiter.is_rate_limited(rate_limit_key, RATE_LIMIT_CANCEL["max_requests"], RATE_LIMIT_CANCEL["window_seconds"]):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many run cancellation attempts. Try again later."
        )

    # Find run
    run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow run with id {run_id} not found"
        )

    # Check authorization
    if run.workflow.organization_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to cancel this workflow run"
        )

    # Only allow cancellation for running or pending runs
    if run.status not in [TaskStatusEnum.pending, TaskStatusEnum.running]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel workflow run in {run.status.value} status"
        )

    try:
        # Cancel the run
        run.status = TaskStatusEnum.cancelled
        run.completed_at = datetime.utcnow()
        run.duration_ms = (run.completed_at - run.started_at).total_seconds() * 1000 if run.started_at else 0
        db.commit()
        db.refresh(run)

        return WorkflowRunResponse(
            run=WorkflowRun(
                id=str(run.id),
                workflow_id=str(run.workflow_id),
                status=run.status.value,
                input=run.input,
                output=run.output,
                error=run.error,
                started_at=run.started_at,
                completed_at=run.completed_at,
                duration_ms=run.duration_ms
            ),
            message="Workflow run cancelled successfully"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel workflow run: {str(e)}"
        )

# GET /api/v1/runs/{id}/logs - Get execution logs
@router.get("/runs/{run_id}/logs", response_model=WorkflowRunResponse, status_code=status.HTTP_200_OK)
async def get_run_logs(
    run_id: str,
    page: int = 1,
    size: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Rate limiting
    rate_limit_key = f"{RATE_LIMIT_LOGS['key']}:{current_user.id}"
    if RateLimiter.is_rate_limited(rate_limit_key, RATE_LIMIT_LOGS["max_requests"], RATE_LIMIT_LOGS["window_seconds"]):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many run log retrieval attempts. Try again later."
        )

    # Find run
    run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow run with id {run_id} not found"
        )

    # Check authorization
    if run.workflow.organization_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this workflow run's logs"
        )

    # Calculate offset
    offset = (page - 1) * size

    # Get total count of logs
    total_logs = db.query(TaskLog).filter(TaskLog.task_id.in_(
        db.query(Task.id).filter(Task.workflow_run_id == run_id)
    )).count()

    # Get paginated logs
    logs = db.query(TaskLog).filter(TaskLog.task_id.in_(
        db.query(Task.id).filter(Task.workflow_run_id == run_id)
    )).order_by(TaskLog.timestamp.desc()).offset(offset).limit(size).all()

    # Build log response
    logs_list = [
        {
            "id": str(log.id),
            "task_id": str(log.task_id),
            "timestamp": log.timestamp,
            "level": log.level.value,
            "message": log.message,
            "metadata": log.metadata
        }
        for log in logs
    ]

    return WorkflowRunResponse(
        run=WorkflowRun(
            id=str(run.id),
            workflow_id=str(run.workflow_id),
            status=run.status.value,
            input=run.input,
            output=run.output,
            error=run.error,
            started_at=run.started_at,
            completed_at=run.completed_at,
            duration_ms=run.duration_ms
        ),
        logs={
            "logs": logs_list,
            "total": total_logs,
            "page": page,
            "size": size
        },
        message="Workflow run logs retrieved successfully"
    )

# POST /api/v1/runs/{id}/retry - Retry failed run
@router.post("/runs/{run_id}/retry", response_model=WorkflowRunResponse, status_code=status.HTTP_200_OK)
async def retry_run(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Rate limiting
    rate_limit_key = f"{RATE_LIMIT_RETRY['key']}:{current_user.id}"
    if RateLimiter.is_rate_limited(rate_limit_key, RATE_LIMIT_RETRY["max_requests"], RATE_LIMIT_RETRY["window_seconds"]):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many run retry attempts. Try again later."
        )

    # Find run
    run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow run with id {run_id} not found"
        )

    # Check authorization
    if run.workflow.organization_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to retry this workflow run"
        )

    # Only allow retry for failed or cancelled runs
    if run.status not in [TaskStatusEnum.failed, TaskStatusEnum.cancelled]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot retry workflow run in {run.status.value} status"
        )

    try:
        # Create a new run based on the failed/cancelled one
        new_run = WorkflowRun(
            workflow_id=run.workflow_id,
            status=TaskStatusEnum.running,
            input=run.input,
            started_at=datetime.utcnow()
        )

        db.add(new_run)
        db.commit()
        db.refresh(new_run)

        return WorkflowRunResponse(
            run=WorkflowRun(
                id=str(new_run.id),
                workflow_id=str(new_run.workflow_id),
                status=new_run.status.value,
                input=new_run.input,
                output=new_run.output,
                error=new_run.error,
                started_at=new_run.started_at,
                completed_at=new_run.completed_at,
                duration_ms=new_run.duration_ms
            ),
            message="Workflow run retried successfully"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retry workflow run: {str(e)}"
        )

# Error handler for validation errors
@router.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=WorkflowErrorResponse(
            detail="An unexpected error occurred",
            error_code="INTERNAL_SERVER_ERROR",
            timestamp=datetime.utcnow()
        ).json(),
        headers=RateLimiter.get_rate_limit_header("runs:errors", 10, 3600)
    )