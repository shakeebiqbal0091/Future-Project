from typing import Any, Dict, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, constr, validator
from app.models.models import StatusEnum, TaskStatusEnum, WorkflowStatusEnum, RoleEnum, PlanEnum, IntegrationStatusEnum, ModelEnum, ToolEnum


class IntegrationCreate(BaseModel):
    type: constr(min_length=1, max_length=50)
    name: constr(min_length=1, max_length=100)
    credentials_encrypted: constr(min_length=1)
    config: Dict[str, Any] = Field(default_factory=dict)
    status: IntegrationStatusEnum = IntegrationStatusEnum.connected

    class Config:
        from_attributes = True


class IntegrationUpdate(BaseModel):
    type: Optional[constr(min_length=1, max_length=50)] = None
    name: Optional[constr(min_length=1, max_length=100)] = None
    credentials_encrypted: Optional[constr(min_length=1)] = None
    config: Optional[Dict[str, Any]] = None
    status: Optional[IntegrationStatusEnum] = None

    class Config:
        from_attributes = True


class Integration(BaseModel):
    id: str
    organization_id: str
    type: str
    name: str
    credentials_encrypted: str
    config: Dict[str, Any]
    status: str
    last_sync: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class IntegrationList(BaseModel):
    integrations: List[Integration]
    total: int
    page: int
    size: int


class IntegrationCreateResponse(BaseModel):
    integration: Integration
    message: str = "Integration created successfully"


class IntegrationUpdateResponse(BaseModel):
    integration: Integration
    message: str = "Integration updated successfully"


class IntegrationDeleteResponse(BaseModel):
    message: str = "Integration deleted successfully"


class IntegrationTestResponse(BaseModel):
    success: bool
    message: str
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class IntegrationAction(BaseModel):
    name: str
    description: str
    parameters: Optional[Dict[str, Any]] = None


class IntegrationActionsResponse(BaseModel):
    actions: List[IntegrationAction]


class IntegrationValidationError(BaseModel):
    field: str
    message: str


class IntegrationValidationErrorResponse(BaseModel):
    detail: str
    errors: List[IntegrationValidationError]
    timestamp: datetime = datetime.utcnow()


class IntegrationErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
    timestamp: datetime = datetime.utcnow()


class RateLimitHeaders(BaseModel):
    X_RATELIMIT_LIMIT: int
    X_RATELIMIT_REMAINING: int
    X_RATELIMIT_RESET: int