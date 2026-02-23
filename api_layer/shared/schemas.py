from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr, validator
from pydantic_settings import BaseSettings

# Request/Response Schemas

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    password: Optional[str] = None

class User(UserBase):
    id: int
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class OrganizationBase(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None

class OrganizationCreate(OrganizationBase):
    pass

class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class Organization(OrganizationBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    member_count: int = 0

    class Config:
        from_attributes = True

class OrganizationMember(BaseModel):
    user_id: int
    organization_id: int
    role: str
    joined_at: datetime
    user: User

class AgentBase(BaseModel):
    name: str
    role: str  # e.g., "sales assistant"
    instructions: str  # system prompt
    model: str  # e.g., "claude-sonnet-4-20250514"
    tools: Optional[List[str]] = None  # enabled tools
    config: Optional[Dict[str, Any]] = None  # additional settings

class AgentCreate(AgentBase):
    organization_id: UUID

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    instructions: Optional[str] = None
    model: Optional[str] = None
    tools: Optional[List[str]] = None
    config: Optional[Dict[str, Any]] = None
    status: Optional[str] = None

class Agent(AgentBase):
    id: UUID
    organization_id: UUID
    status: str
    version: int
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class WorkflowBase(BaseModel):
    name: str
    description: Optional[str] = None
    definition: Dict[str, Any]  # Workflow definition
    status: str = "draft"

class WorkflowCreate(WorkflowBase):
    organization_id: UUID

class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    definition: Optional[Dict[str, Any]] = None
    status: Optional[str] = None

class Workflow(WorkflowBase):
    id: UUID
    organization_id: UUID
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class TaskBase(BaseModel):
    step_name: str
    input: Dict[str, Any]

class TaskCreate(TaskBase):
    workflow_run_id: UUID
    agent_id: UUID

class TaskUpdate(BaseModel):
    step_name: Optional[str] = None
    input: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    error: Optional[str] = None
    output: Optional[Dict[str, Any]] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    tokens_used: Optional[int] = None
    cost_usd: Optional[float] = None

class Task(TaskBase):
    id: UUID
    workflow_run_id: UUID
    agent_id: UUID
    status: str
    error: Optional[str] = None
    output: Optional[Dict[str, Any]] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    tokens_used: Optional[int] = None
    cost_usd: Optional[float] = None

    class Config:
        from_attributes = True

class IntegrationBase(BaseModel):
    name: str
    type: str  # slack, teams, email, etc.
    config: Dict[str, Any]

class IntegrationCreate(IntegrationBase):
    pass

class IntegrationUpdate(BaseModel):
    name: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

class Integration(IntegrationBase):
    id: int
    is_active: bool
    organization_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UsageMetricBase(BaseModel):
    metric_type: str
    value: int
    cost_usd: Optional[float] = None

class UsageMetric(UsageMetricBase):
    id: UUID
    organization_id: UUID
    agent_id: Optional[UUID] = None
    task_id: Optional[UUID] = None
    timestamp: datetime

    class Config:
        from_attributes = True

class SubscriptionBase(BaseModel):
    plan_type: str  # free, pro, enterprise
    current_period_start: datetime
    current_period_end: datetime

class Subscription(SubscriptionBase):
    id: int
    organization_id: int
    status: str
    stripe_subscription_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class Pagination(BaseModel):
    page: int = 1
    limit: int = 100
    sort_by: Optional[str] = None
    sort_order: str = "asc"  # asc, desc
    filters: Optional[Dict[str, Any]] = None

class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    limit: int
    total_pages: int

class ErrorResponse(BaseModel):
    detail: str
    code: Optional[str] = None
    errors: Optional[List[Dict[str, str]]] = None

class AuthResponse(BaseModel):
    user: User
    token: Token

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordReset(BaseModel):
    token: str
    new_password: str

class ProfileUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None

class Settings(BaseModel):
    notifications: bool = True
    email_updates: bool = True
    theme: str = "light"

class AnalyticsQuery(BaseModel):
    metric: str
    group_by: Optional[str] = None
    time_range: Optional[str] = None  # last_7d, last_30d, custom
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class AnalyticsResponse(BaseModel):
    metric: str
    data: List[Dict[str, Any]]
    summary: Dict[str, float]

class BillingUpdate(BaseModel):
    plan_type: Optional[str] = None
    card_token: Optional[str] = None

class AgentVersionBase(BaseModel):
    version: int
    config: Dict[str, Any]
    deployed_at: datetime
    deployed_by: UUID

class AgentVersionCreate(BaseModel):
    agent_id: UUID
    version: int
    config: Dict[str, Any]

class AgentVersion(AgentVersionBase):
    id: UUID
    agent_id: UUID

    class Config:
        from_attributes = True

class WorkflowRunBase(BaseModel):
    workflow_id: UUID
    status: str
    input: Dict[str, Any]
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None

class WorkflowRunCreate(WorkflowRunBase):
    pass

class WorkflowRun(WorkflowRunBase):
    id: UUID

    class Config:
        from_attributes = True

class TaskLogBase(BaseModel):
    task_id: UUID
    timestamp: datetime
    level: str
    message: str
    metadata: Optional[Dict[str, Any]] = None

class TaskLogCreate(TaskLogBase):
    pass

class TaskLog(TaskLogBase):
    id: UUID

    class Config:
        from_attributes = True


# Agent Test Schemas

class AgentTestRequest(BaseModel):
    input: Dict[str, Any]
    expected_output: Optional[Dict[str, Any]] = None


class AgentTestResponse(BaseModel):
    success: bool
    actual_output: Dict[str, Any]
    duration_ms: int
    tokens_used: int
    cost_usd: float
    errors: Optional[List[str]] = None


# Agent Metrics Schemas

class AgentMetrics(BaseModel):
    agent_id: UUID
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    average_execution_time_ms: float
    tokens_used: int
    cost_usd: float
    tools_usage: Dict[str, int]
    last_used_at: Optional[datetime] = None


# Agent Version Schemas

class AgentVersionBase(BaseModel):
    version: int
    config: Dict[str, Any]
    deployed_at: datetime
    deployed_by: UUID


class AgentVersionCreate(BaseModel):
    agent_id: UUID
    version: int
    config: Dict[str, Any]


class AgentVersion(AgentVersionBase):
    id: UUID
    agent_id: UUID

    class Config:
        from_attributes = True


# Workflow Run Schemas

class WorkflowRunBase(BaseModel):
    workflow_id: UUID
    status: str
    input: Dict[str, Any]
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None


class WorkflowRunCreate(WorkflowRunBase):
    pass


class WorkflowRun(WorkflowRunBase):
    id: UUID

    class Config:
        from_attributes = True