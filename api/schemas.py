from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from uuid import UUID


class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, max_length=100)
    is_active: bool = True
    is_superuser: bool = False


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    organization_id: Optional[UUID] = None
    role: str = "member"

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class OrganizationBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    slug: str = Field(..., min_length=2, max_length=50)
    is_active: bool = True


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class OrganizationResponse(OrganizationBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    member_count: int = 0
    owner_id: UUID

    class Config:
        from_attributes = True


class AgentBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    agent_type: str = Field(..., regex="^(llm|rule_based|hybrid)$")
    model: str = Field(..., min_length=1, max_length=100)
    api_key: Optional[str] = Field(None, min_length=10, max_length=255)
    is_active: bool = True


class AgentCreate(AgentBase):
    pass


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    agent_type: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None
    is_active: Optional[bool] = None


class AgentResponse(AgentBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    organization_id: UUID
    created_by: UUID

    class Config:
        from_attributes = True


class WorkflowBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    triggers: List[str] = Field(default_factory=list)
    steps: List[dict] = Field(default_factory=list)
    is_active: bool = True


class WorkflowCreate(WorkflowBase):
    pass


class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    triggers: Optional[List[str]] = None
    steps: Optional[List[dict]] = None
    is_active: Optional[bool] = None


class WorkflowResponse(WorkflowBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    organization_id: UUID
    created_by: UUID

    class Config:
        from_attributes = True


class TaskBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    agent_id: UUID
    workflow_id: Optional[int] = None
    input_data: dict = Field(default_factory=dict)
    status: str = Field(default="pending", regex="^(pending|running|completed|failed|cancelled)$")
    priority: str = Field(default="normal", regex="^(low|normal|high|critical)$")


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    agent_id: Optional[int] = None
    workflow_id: Optional[int] = None
    input_data: Optional[dict] = None
    status: Optional[str] = None
    priority: Optional[str] = None


class TaskResponse(TaskBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    organization_id: UUID
    created_by: UUID
    output_data: Optional[dict] = None
    error_message: Optional[str] = None
    execution_time: Optional[float] = None

    class Config:
        from_attributes = True


class IntegrationBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    integration_type: str = Field(..., regex="^(webhook|api|database|file_system|cloud_service)$")
    config: dict = Field(default_factory=dict)
    is_active: bool = True


class IntegrationCreate(IntegrationBase):
    pass


class IntegrationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    config: Optional[dict] = None
    is_active: Optional[bool] = None


class IntegrationResponse(IntegrationBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    organization_id: UUID
    created_by: UUID

    class Config:
        from_attributes = True


class AnalyticsBase(BaseModel):
    metric_name: str = Field(..., min_length=1, max_length=100)
    value: float
    unit: str = Field(..., min_length=1, max_length=50)
    tags: List[str] = Field(default_factory=list)
    timestamp: datetime


class AnalyticsResponse(AnalyticsBase):
    id: UUID

    class Config:
        from_attributes = True


class BillingPlanBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    price: float = Field(..., ge=0)
    currency: str = Field(default="USD", regex="^[A-Z]{3}$")
    features: dict = Field(default_factory=dict)
    max_agents: int = Field(default=0)
    max_workflows: int = Field(default=0)
    max_tasks_per_month: int = Field(default=0)


class BillingPlanResponse(BillingPlanBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    is_active: bool = True

    class Config:
        from_attributes = True


class SubscriptionBase(BaseModel):
    plan_id: UUID
    organization_id: UUID
    status: str = Field(default="active", regex="^(active|trial|cancelled|expired)$")
    current_period_start: datetime
    current_period_end: datetime


class SubscriptionResponse(SubscriptionBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UsageResponse(BaseModel):
    organization_id: UUID
    current_period_start: datetime
    current_period_end: datetime
    agents_used: int
    workflows_used: int
    tasks_executed: int
    storage_used: int

    class Config:
        from_attributes = True


class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
    field_errors: Optional[dict] = None


class PaginationResponse(BaseModel):
    items: List[dict]
    total: int
    page: int
    size: int
    total_pages: int


class SortOrder(BaseModel):
    field: str
    direction: str = Field(default="asc", regex="^(asc|desc)$")


class Filter(BaseModel):
    field: str
    operator: str = Field(default="eq", regex="^(eq|ne|gt|lt|gte|lte|contains|startswith|endswith)$")
    value: str


class WorkflowRunBase(BaseModel):
    workflow_id: UUID
    status: str = Field(default="pending", regex="^(pending|running|completed|failed|cancelled)$")
    input_data: dict = Field(default_factory=dict)
    output_data: Optional[dict] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None


class WorkflowRunCreate(WorkflowRunBase):
    pass


class WorkflowRunUpdate(BaseModel):
    status: Optional[str] = None
    output_data: Optional[dict] = None
    error_message: Optional[str] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None


class WorkflowRunResponse(WorkflowRunBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    organization_id: UUID
    created_by: UUID
    workflow_name: str
    tasks: List[TaskResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class TaskLogResponse(BaseModel):
    id: UUID
    task_id: UUID
    timestamp: datetime
    level: str  # debug, info, warning, error
    message: str
    metadata: Optional[dict] = None

    class Config:
        from_attributes = True


class EmailVerification(BaseModel):
    email: EmailStr
    verification_code: str


class PasswordReset(BaseModel):
    email: EmailStr


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    username: Optional[str] = None