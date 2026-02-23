from typing import Any, Dict, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, constr, validator
from app.models.models import StatusEnum, TaskStatusEnum, WorkflowStatusEnum, RoleEnum, PlanEnum, IntegrationStatusEnum, ModelEnum, ToolEnum


class AgentCreate(BaseModel):
    name: constr(min_length=1, max_length=100)
    role: constr(min_length=1, max_length=100)
    instructions: constr(min_length=1)
    model: ModelEnum
    tools: List[ToolEnum] = Field(default_factory=list)
    config: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True


class AgentUpdate(BaseModel):
    name: Optional[constr(min_length=1, max_length=100)] = None
    role: Optional[constr(min_length=1, max_length=100)] = None
    instructions: Optional[constr(min_length=1)] = None
    model: Optional[ModelEnum] = None
    tools: Optional[List[ToolEnum]] = None
    config: Optional[Dict[str, Any]] = None
    status: Optional[StatusEnum] = None

    class Config:
        from_attributes = True


class Agent(BaseModel):
    id: str
    organization_id: str
    name: str
    role: str
    instructions: str
    model: str
    tools: List[str]
    config: Dict[str, Any]
    status: str
    version: int
    created_by: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AgentVersion(BaseModel):
    id: str
    agent_id: str
    version: int
    config: Dict[str, Any]
    deployed_at: datetime
    deployed_by: str

    class Config:
        from_attributes = True


class AgentTestRequest(BaseModel):
    input: Dict[str, Any]


class AgentTestResponse(BaseModel):
    success: bool
    message: str
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class AgentMetrics(BaseModel):
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    success_rate: float
    avg_execution_time_ms: float
    total_tokens_used: int
    total_cost_usd: float
    tasks_by_status: Dict[str, int]
    tasks_by_hour: Dict[str, int]
    cost_by_day: Dict[str, float]


class AgentList(BaseModel):
    agents: List[Agent]
    total: int
    page: int
    size: int


class AgentVersionList(BaseModel):
    versions: List[AgentVersion]
    total: int
    page: int
    size: int


class AgentCreateResponse(BaseModel):
    agent: Agent
    message: str = "Agent created successfully"


class AgentUpdateResponse(BaseModel):
    agent: Agent
    message: str = "Agent updated successfully"


class AgentDeleteResponse(BaseModel):
    message: str = "Agent deleted successfully"


class AgentDeployResponse(BaseModel):
    version: AgentVersion
    message: str = "Agent version deployed successfully"


class AgentTestResponse(BaseModel):
    success: bool
    message: str
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class AgentMetricsResponse(BaseModel):
    metrics: AgentMetrics


class AgentValidationError(BaseModel):
    field: str
    message: str


class AgentValidationErrorResponse(BaseModel):
    detail: str
    errors: List[AgentValidationError]
    timestamp: datetime = datetime.utcnow()


class AgentErrorResponse(BaseModel):
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