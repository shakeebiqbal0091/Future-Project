from typing import Any, Dict, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, constr, validator
from app.models.models import StatusEnum, TaskStatusEnum, WorkflowStatusEnum, RoleEnum, PlanEnum, IntegrationStatusEnum, ModelEnum, ToolEnum


class Task(BaseModel):
    id: str
    workflow_run_id: str
    agent_id: str
    step_name: str
    input: Dict[str, Any]
    output: Optional[Dict[str, Any]] = None
    status: str
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    tokens_used: Optional[int] = None
    cost_usd: Optional[float] = None

    class Config:
        from_attributes = True


class TaskList(BaseModel):
    tasks: List[Task]
    total: int
    page: int
    size: int


class TaskResponse(BaseModel):
    task: Task
    message: str = "Task retrieved successfully"


class TaskLog(BaseModel):
    id: str
    task_id: str
    timestamp: datetime
    level: str  # debug, info, warning, error
    message: str
    metadata: Optional[Dict[str, Any]] = None


class TaskLogList(BaseModel):
    logs: List[TaskLog]
    total: int
    page: int
    size: int


class TaskLogResponse(BaseModel):
    logs: TaskLogList
    message: str = "Task logs retrieved successfully"


class TaskMetrics(BaseModel):
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    success_rate: float
    avg_execution_time_ms: float
    total_tokens_used: int
    total_cost_usd: float
    tasks_by_status: Dict[str, int]
    tasks_by_agent: Dict[str, int]
    cost_by_day: Dict[str, float]


class TaskMetricsResponse(BaseModel):
    metrics: TaskMetrics
    message: str = "Task metrics retrieved successfully"


class TaskErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
    timestamp: datetime = datetime.utcnow()


class TaskValidationError(BaseModel):
    field: str
    message: str


class TaskValidationErrorResponse(BaseModel):
    detail: str
    errors: Optional[List[TaskValidationError]] = None
    timestamp: datetime = datetime.utcnow()


class RateLimitHeaders(BaseModel):
    X_RATELIMIT_LIMIT: int
    X_RATELIMIT_REMAINING: int
    X_RATELIMIT_RESET: int


class SecurityHeaders(BaseModel):
    X_CONTENT_TYPE_OPTIONS: str = "nosniff"
    X_FRAME_OPTIONS: str = "DENY"
    X_XSS_PROTECTION: str = "1; mode=block"
    STRICT_TRANSPORT_SECURITY: str = "max-age=31536000; includeSubDomains"
    REFERER_POLICY: str = "strict-origin-when-cross-origin"
    CONTENT_SECURITY_POLICY: str = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' https:; connect-src 'self' https:; frame-ancestors 'none';"
