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
from app.models.models import User, Agent, AgentVersion, Task, TaskStatusEnum, StatusEnum, RoleEnum, PlanEnum, Workflow, WorkflowRun, TaskLog
from app.schemas.tasks import (
    Task, TaskList, TaskResponse, TaskLog, TaskLogList, TaskLogResponse,
    TaskMetrics, TaskMetricsResponse, TaskErrorResponse, TaskValidationError,
    TaskValidationErrorResponse, RateLimitHeaders, SecurityHeaders
)

router = APIRouter()


# Authentication dependencies
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


# Helper functions
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends()) -> User:
    return await AuthHandler.get_current_active_user(token, db)


async def get_current_org(user: User = Depends(get_current_user)) -> User:
    # In a real implementation, you would get the user's organization
    # For now, we'll assume the user belongs to one organization
    # This would typically involve a Membership model and Organization model
    # For simplicity, we'll return the user as the organization owner
    return user


# Rate limiting configurations
RATE_LIMIT_GET = {"key": "tasks:get", "max_requests": 100, "window_seconds": 3600}
RATE_LIMIT_LOGS = {"key": "tasks:logs", "max_requests": 100, "window_seconds": 3600}
RATE_LIMIT_METRICS = {"key": "tasks:metrics", "max_requests": 50, "window_seconds": 3600}


# GET /api/v1/tasks/{id} - Get task details
@router.get("/tasks/{task_id}", response_model=TaskResponse, status_code=status.HTTP_200_OK)
async def get_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Rate limiting
    rate_limit_key = f"{RATE_LIMIT_GET['key']}:{current_user.id}"
    if RateLimiter.is_rate_limited(rate_limit_key, RATE_LIMIT_GET["max_requests"], RATE_LIMIT_GET["window_seconds"]):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many task retrieval attempts. Try again later."
        )

    # Find task
    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found"
        )

    # Check authorization - ensure task belongs to current user's organization
    # Note: This is a simplified check. In a real implementation, you would check organization membership
    if task.workflow_run.workflow.organization_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this task"
        )

    return TaskResponse(
        task=Task(
            id=str(task.id),
            workflow_run_id=str(task.workflow_run_id),
            agent_id=str(task.agent_id),
            step_name=task.step_name,
            input=task.input,
            output=task.output,
            status=task.status.value,
            error=task.error,
            started_at=task.started_at,
            completed_at=task.completed_at,
            duration_ms=task.duration_ms,
            tokens_used=task.tokens_used,
            cost_usd=task.cost_usd
        )
    )


# GET /api/v1/tasks/{id}/logs - Get task logs
@router.get("/tasks/{task_id}/logs", response_model=TaskLogResponse, status_code=status.HTTP_200_OK)
async def get_task_logs(
    task_id: str,
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
            detail="Too many task log retrieval attempts. Try again later."
        )

    # Find task
    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found"
        )

    # Check authorization
    if task.workflow_run.workflow.organization_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this task's logs"
        )

    # Calculate offset
    offset = (page - 1) * size

    # Get total count
    total = db.query(TaskLog).filter(TaskLog.task_id == task_id).count()

    # Get paginated logs
    logs = db.query(TaskLog).filter(TaskLog.task_id == task_id).order_by(TaskLog.timestamp.desc()).offset(offset).limit(size).all()

    return TaskLogResponse(
        logs=TaskLogList(
            logs=[
                TaskLog(
                    id=str(log.id),
                    task_id=str(log.task_id),
                    timestamp=log.timestamp,
                    level=log.level.value,
                    message=log.message,
                    metadata=log.metadata
                ) for log in logs
            ],
            total=total,
            page=page,
            size=size
        ),
        message="Task logs retrieved successfully"
    )


# GET /api/v1/tasks/{id} - Get task details
@router.get("/tasks/{task_id}", response_model=TaskResponse, status_code=status.HTTP_200_OK)
async def get_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Rate limiting
    rate_limit_key = f"{RATE_LIMIT_GET['key']}:{current_user.id}"
    if RateLimiter.is_rate_limited(rate_limit_key, RATE_LIMIT_GET["max_requests"], RATE_LIMIT_GET["window_seconds"]):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many task retrieval attempts. Try again later."
        )

    # Find task
    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found"
        )

    # Check authorization - ensure task belongs to current user's organization
    # Note: This is a simplified check. In a real implementation, you would check organization membership
    if task.workflow_run.workflow.organization_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this task"
        )

    return TaskResponse(
        task=Task(
            id=str(task.id),
            workflow_run_id=str(task.workflow_run_id),
            agent_id=str(task.agent_id),
            step_name=task.step_name,
            input=task.input,
            output=task.output,
            status=task.status.value,
            error=task.error,
            started_at=task.started_at,
            completed_at=task.completed_at,
            duration_ms=task.duration_ms,
            tokens_used=task.tokens_used,
            cost_usd=task.cost_usd
        )
    )


# GET /api/v1/tasks/{id}/logs - Get task logs
@router.get("/tasks/{task_id}/logs", response_model=TaskLogResponse, status_code=status.HTTP_200_OK)
async def get_task_logs(
    task_id: str,
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
            detail="Too many task log retrieval attempts. Try again later."
        )

    # Find task
    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found"
        )

    # Check authorization
    if task.workflow_run.workflow.organization_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this task's logs"
        )

    # Calculate offset
    offset = (page - 1) * size

    # Get total count
    total = db.query(TaskLog).filter(TaskLog.task_id == task_id).count()

    # Get paginated logs
    logs = db.query(TaskLog).filter(TaskLog.task_id == task_id).order_by(TaskLog.timestamp.desc()).offset(offset).limit(size).all()

    return TaskLogResponse(
        logs=TaskLogList(
            logs=[
                TaskLog(
                    id=str(log.id),
                    task_id=str(log.task_id),
                    timestamp=log.timestamp,
                    level=log.level.value,
                    message=log.message,
                    metadata=log.metadata
                ) for log in logs
            ],
            total=total,
            page=page,
            size=size
        ),
        message="Task logs retrieved successfully"
    )


# GET /api/v1/tasks/{id}/metrics - Get task metrics
@router.get("/tasks/{task_id}/metrics", response_model=TaskMetricsResponse, status_code=status.HTTP_200_OK)
async def get_task_metrics(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Rate limiting
    rate_limit_key = f"{RATE_LIMIT_METRICS['key']}:{current_user.id}"
    if RateLimiter.is_rate_limited(rate_limit_key, RATE_LIMIT_METRICS["max_requests"], RATE_LIMIT_METRICS["window_seconds"]):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many task metrics retrieval attempts. Try again later."
        )

    # Find task
    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found"
        )

    # Check authorization
    if task.workflow_run.workflow.organization_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this task's metrics"
        )

    try:
        # Get task metrics (in a real implementation, this would query usage data)
        # For now, we'll simulate some metrics
        total_tasks = 1  # This specific task
        completed_tasks = 1 if task.status == TaskStatusEnum.completed else 0
        failed_tasks = 1 if task.status == TaskStatusEnum.failed else 0
        success_rate = 100.0 if task.status == TaskStatusEnum.completed else 0.0
        avg_execution_time_ms = task.duration_ms or 0
        total_tokens_used = task.tokens_used or 0
        total_cost_usd = task.cost_usd or 0.0

        tasks_by_status = {
            TaskStatusEnum.pending.value: 1 if task.status == TaskStatusEnum.pending else 0,
            TaskStatusEnum.running.value: 1 if task.status == TaskStatusEnum.running else 0,
            TaskStatusEnum.completed.value: 1 if task.status == TaskStatusEnum.completed else 0,
            TaskStatusEnum.failed.value: 1 if task.status == TaskStatusEnum.failed else 0,
            TaskStatusEnum.cancelled.value: 1 if task.status == TaskStatusEnum.cancelled else 0,
        }

        tasks_by_agent = {
            task.agent_id: 1
        }

        cost_by_day = {
            task.started_at.date().isoformat() if task.started_at else datetime.utcnow().date().isoformat(): total_cost_usd
        }

        metrics = TaskMetrics(
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            failed_tasks=failed_tasks,
            success_rate=success_rate,
            avg_execution_time_ms=avg_execution_time_ms,
            total_tokens_used=total_tokens_used,
            total_cost_usd=total_cost_usd,
            tasks_by_status=tasks_by_status,
            tasks_by_agent=tasks_by_agent,
            cost_by_day=cost_by_day
        )

        return TaskMetricsResponse(metrics=metrics)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task metrics: {str(e)}"
        )


# Error handler for validation errors
@router.exception_handler(TaskValidationErrorResponse)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=exc.json(),
        headers=RateLimiter.get_rate_limit_header("tasks:validation", 100, 3600)
    )


# Error handler for general errors
@router.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=TaskErrorResponse(
            detail="An unexpected error occurred",
            error_code="INTERNAL_SERVER_ERROR",
            timestamp=datetime.utcnow()
        ).json(),
        headers=RateLimiter.get_rate_limit_header("tasks:errors", 10, 3600)
    )
