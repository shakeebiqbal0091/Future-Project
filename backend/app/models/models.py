from sqlalchemy import Column, String, Integer, DateTime, Boolean, ForeignKey, Text, Float, JSON, func, Enum, Date
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base
from sqlalchemy.orm import relationship, backref
import enum
import uuid
from datetime import datetime
from typing import List, Dict, Optional
class StatusEnum(Enum):
    active = "active"
    inactive = "inactive"
    archived = "archived"

class TaskStatusEnum(Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"

class WorkflowStatusEnum(Enum):
    draft = "draft"
    active = "active"
    archived = "archived"

class LogLevelEnum(Enum):
    debug = "debug"
    info = "info"
    warning = "warning"
    error = "error"

class MetricTypeEnum(Enum):
    tasks = "tasks"
    tokens = "tokens"
    api_calls = "api_calls"

class RoleEnum(Enum):
    owner = "owner"
    admin = "admin"
    member = "member"
    viewer = "viewer"

class PlanEnum(Enum):
    free = "free"
    starter = "starter"
    pro = "pro"
    business = "business"
    enterprise = "enterprise"

class IntegrationStatusEnum(Enum):
    connected = "connected"
    error = "error"
    disconnected = "disconnected"

class ModelEnum(Enum):
    claude = "claude"
    gpt4 = "gpt4"
    gpt3_5 = "gpt3_5"
    gemini = "gemini"

class ToolEnum(Enum):
    calculator = "calculator"
    web_search = "web_search"
    http_request = "http_request"
    database_query = "database_query"
    email_send = "email_send"
    slack_post = "slack_post"

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    email_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    api_keys = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")

    # Helper methods
    def __repr__(self) -> str:
        return f"<User username={self.username} email={self.email}>"

class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    last_used_at = Column(DateTime)

    # Relationships
    user = relationship("User", back_populates="api_keys")

    def __repr__(self) -> str:
        return f"<ApiKey user_id={self.user_id} description={self.description}>"

# Add indexes for performance
User.__table_args__ = (
    {"schema": "public"},
)

ApiKey.__table_args__ = (
    {"schema": "public"},
)

class Organization(Base):
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    plan = Column(Enum(PlanEnum.free, PlanEnum.starter, PlanEnum.pro, PlanEnum.business, PlanEnum.enterprise), nullable=False, default=PlanEnum.free)
    billing_email = Column(String)
    stripe_customer_id = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    members = relationship("Membership", back_populates="organization", cascade="all, delete-orphan")
    agents = relationship("Agent", back_populates="organization", cascade="all, delete-orphan")
    workflows = relationship("Workflow", back_populates="organization", cascade="all, delete-orphan")
    integrations = relationship("Integration", back_populates="organization", cascade="all, delete-orphan")
    usage_metrics = relationship("UsageMetric", back_populates="organization", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Organization name={self.name} plan={self.plan.value}>"

class Membership(Base):
    __tablename__ = "memberships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    organization_id = Column(UUID, ForeignKey("organizations.id"), nullable=False)
    role = Column(Enum(RoleEnum.owner, RoleEnum.admin, RoleEnum.member, RoleEnum.viewer), nullable=False, default=RoleEnum.member)
    joined_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="memberships")
    organization = relationship("Organization", back_populates="memberships")

    def __repr__(self) -> str:
        return f"<Membership user_id={self.user_id} organization_id={self.organization_id} role={self.role.value}>"

class Agent(Base):
    __tablename__ = "agents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID, ForeignKey("organizations.id"), nullable=False)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False)
    instructions = Column(Text, nullable=False)
    model = Column(String, nullable=False)
    tools = Column(JSON, nullable=False, default=list)
    config = Column(JSON, nullable=False, default=dict)
    status = Column(Enum(StatusEnum.active, StatusEnum.inactive, StatusEnum.archived), nullable=False, default=StatusEnum.active)
    version = Column(Integer, nullable=False, default=1)
    created_by = Column(UUID, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organization = relationship("Organization", back_populates="agents")
    creator = relationship("User", foreign_keys=[created_by])
    versions = relationship("AgentVersion", back_populates="agent", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="agent", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Agent name={self.name} role={self.role} status={self.status.value}>"

class AgentVersion(Base):
    __tablename__ = "agent_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID, ForeignKey("agents.id"), nullable=False)
    version = Column(Integer, nullable=False)
    config = Column(JSON, nullable=False)
    deployed_at = Column(DateTime, default=datetime.utcnow)
    deployed_by = Column(UUID, ForeignKey("users.id"), nullable=False)

    # Relationships
    agent = relationship("Agent", back_populates="versions")
    deployer = relationship("User", foreign_keys=[deployed_by])

    def __repr__(self) -> str:
        return f"<AgentVersion agent_id={self.agent_id} version={self.version} deployed_at={self.deployed_at}>"

class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID, ForeignKey("organizations.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    definition = Column(JSON, nullable=False)
    status = Column(Enum(WorkflowStatusEnum.draft, WorkflowStatusEnum.active, WorkflowStatusEnum.archived), nullable=False, default=WorkflowStatusEnum.draft)
    created_by = Column(UUID, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organization = relationship("Organization", back_populates="workflows")
    creator = relationship("User", foreign_keys=[created_by])
    runs = relationship("WorkflowRun", back_populates="workflow", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Workflow name={self.name} status={self.status.value}>"

class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(UUID, ForeignKey("workflows.id"), nullable=False)
    status = Column(Enum(TaskStatusEnum.pending, TaskStatusEnum.running, TaskStatusEnum.completed, TaskStatusEnum.failed, TaskStatusEnum.cancelled), nullable=False, default=TaskStatusEnum.pending)
    input = Column(JSON, nullable=False)
    output = Column(JSON)
    error = Column(Text)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    duration_ms = Column(Integer)

    # Relationships
    workflow = relationship("Workflow", back_populates="runs")
    tasks = relationship("Task", back_populates="workflow_run", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<WorkflowRun workflow_id={self.workflow_id} status={self.status.value} duration={self.duration_ms}ms>"

class Task(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_run_id = Column(UUID, ForeignKey("workflow_runs.id"), nullable=False)
    agent_id = Column(UUID, ForeignKey("agents.id"), nullable=False)
    step_name = Column(String, nullable=False)
    input = Column(JSON, nullable=False)
    output = Column(JSON)
    status = Column(Enum(TaskStatusEnum.pending, TaskStatusEnum.running, TaskStatusEnum.completed, TaskStatusEnum.failed, TaskStatusEnum.cancelled), nullable=False, default=TaskStatusEnum.pending)
    error = Column(Text)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    duration_ms = Column(Integer)
    tokens_used = Column(Integer)
    cost_usd = Column(Float)

    # Relationships
    workflow_run = relationship("WorkflowRun", back_populates="tasks")
    agent = relationship("Agent", back_populates="tasks")
    logs = relationship("TaskLog", back_populates="task", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Task step_name={self.step_name} status={self.status.value} duration={self.duration_ms}ms>"

class TaskLog(Base):
    __tablename__ = "task_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID, ForeignKey("tasks.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    level = Column(Enum(LogLevelEnum.debug, LogLevelEnum.info, LogLevelEnum.warning, LogLevelEnum.error), nullable=False, default=LogLevelEnum.info)
    message = Column(Text, nullable=False)
    log_log_log_log_log_log_log_log_log_metadata = Column(JSON)

    # Relationships
    task = relationship("Task", back_populates="logs")

    def __repr__(self) -> str:
        return f"<TaskLog level={self.level.value} message={self.message[:50]}...>"

class Integration(Base):
    __tablename__ = "integrations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID, ForeignKey("organizations.id"), nullable=False)
    type = Column(String, nullable=False)
    name = Column(String, nullable=False)
    credentials_encrypted = Column(Text, nullable=False)
    config = Column(JSON, nullable=False, default=dict)
    status = Column(Enum(IntegrationStatusEnum.connected, IntegrationStatusEnum.error, IntegrationStatusEnum.disconnected), nullable=False, default=IntegrationStatusEnum.connected)
    last_sync = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    organization = relationship("Organization", back_populates="integrations")

    def __repr__(self) -> str:
        return f"<Integration type={self.type} name={self.name} status={self.status.value}>"

class UsageMetric(Base):
    __tablename__ = "usage_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID, ForeignKey("organizations.id"), nullable=False)
    date = Column(Date, nullable=False)
    metric_type = Column(Enum(MetricTypeEnum.tasks, MetricTypeEnum.tokens, MetricTypeEnum.api_calls), nullable=False)
    value = Column(Integer, nullable=False)
    cost_usd = Column(Float)

    # Relationships
    organization = relationship("Organization", back_populates="usage_metrics")

    def __repr__(self) -> str:
        return f"<UsageMetric date={self.date} type={self.metric_type.value} value={self.value}>"