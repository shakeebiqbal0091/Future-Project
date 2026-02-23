from typing import Any, Dict, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, constr, validator
from app.models.models import StatusEnum, TaskStatusEnum, WorkflowStatusEnum, RoleEnum, PlanEnum, IntegrationStatusEnum, ModelEnum, ToolEnum


class WorkflowCreate(BaseModel):
    name: constr(min_length=1, max_length=100)
    description: Optional[constr(min_length=1, max_length=500)] = None
    definition: Dict[str, Any]  # Workflow graph definition

    class Config:
        from_attributes = True


class WorkflowUpdate(BaseModel):
    name: Optional[constr(min_length=1, max_length=100)] = None
    description: Optional[constr(min_length=1, max_length=500)] = None
    definition: Optional[Dict[str, Any]] = None
    status: Optional[WorkflowStatusEnum] = None

    class Config:
        from_attributes = True


class Workflow(BaseModel):
    id: str
    organization_id: str
    name: str
    description: Optional[str] = None
    definition: Dict[str, Any]
    status: str
    created_by: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WorkflowRun(BaseModel):
    id: str
    workflow_id: str
    status: str
    input: Dict[str, Any]
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None

    class Config:
        from_attributes = True


class WorkflowRunCreate(BaseModel):
    workflow_id: str
    input: Dict[str, Any]

    class Config:
        from_attributes = True


class WorkflowValidationResponse(BaseModel):
    valid: bool
    errors: Optional[List[str]] = None
    warnings: Optional[List[str]] = None
    suggestions: Optional[List[str]] = None


class WorkflowRunList(BaseModel):
    runs: List[WorkflowRun]
    total: int
    page: int
    size: int


class WorkflowList(BaseModel):
    workflows: List[Workflow]
    total: int
    page: int
    size: int


class WorkflowCreateResponse(BaseModel):
    workflow: Workflow
    message: str = "Workflow created successfully"


class WorkflowUpdateResponse(BaseModel):
    workflow: Workflow
    message: str = "Workflow updated successfully"


class WorkflowDeleteResponse(BaseModel):
    message: str = "Workflow deleted successfully"


class WorkflowRunResponse(BaseModel):
    run: WorkflowRun
    message: str = "Workflow execution started"


class WorkflowValidationError(BaseModel):
    field: str
    message: str


class WorkflowValidationErrorResponse(BaseModel):
    detail: str
    errors: Optional[List[WorkflowValidationError]] = None
    timestamp: datetime = datetime.utcnow()


class WorkflowErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
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