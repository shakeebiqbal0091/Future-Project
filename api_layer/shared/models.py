from sqlalchemy.dialects.postgresql import UUID as UUIDType, ENUM as EnumType, JSONB as JSONBType, BYTEA as BYTEAType
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    organizations = relationship("OrganizationMember", back_populates="user")
    agents = relationship("Agent", back_populates="creator")
    workflows = relationship("Workflow", back_populates="creator")
    tasks = relationship("Task", back_populates="creator")

class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    members = relationship("OrganizationMember", back_populates="organization")
    agents = relationship("Agent", back_populates="organization")
    workflows = relationship("Workflow", back_populates="organization")

class OrganizationMember(Base):
    __tablename__ = "organization_members"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    role = Column(String, nullable=False)  # admin, member, owner
    joined_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="organizations")
    organization = relationship("Organization", back_populates="members")

class Agent(Base):
    __tablename__ = "agents"

    id = Column(UUIDType, primary_key=True, index=True, default=uuid.uuid4)
    organization_id = Column(UUIDType, ForeignKey("organizations.id"), nullable=False)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False)  # e.g., "sales assistant"
    instructions = Column(Text, nullable=False)  # system prompt
    model = Column(String, nullable=False)  # e.g., "claude-sonnet-4-20250514"
    tools = Column(JSONBType, nullable=True)  # enabled tools
    config = Column(JSONBType, nullable=True)  # additional settings
    status = Column(EnumType("active", "inactive", "archived", name="agent_status"), default="active")
    version = Column(Integer, default=1)
    created_by = Column(UUIDType, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    creator = relationship("User", back_populates="agents")
    organization = relationship("Organization", back_populates="agents")
    workflows = relationship("Workflow", back_populates="agent")
    usage_metrics = relationship("UsageMetric", back_populates="agent")
    versions = relationship("AgentVersion", back_populates="agent", order_by=lambda: desc(AgentVersion.version))

class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    definition = Column(JSON, nullable=False)  # Workflow definition
    status = Column(String, default="draft")  # draft, active, inactive
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    creator = relationship("User", back_populates="workflows")
    organization = relationship("Organization", back_populates="workflows")
    agent = relationship("Agent", back_populates="workflows")
    tasks = relationship("Task", back_populates="workflow")

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    input_data = Column(JSON, nullable=False)
    output_data = Column(JSON, nullable=True)
    status = Column(String, default="pending")  # pending, running, completed, failed
    error_message = Column(Text, nullable=True)
    execution_time = Column(Float, nullable=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=True)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    creator = relationship("User", back_populates="tasks")
    workflow = relationship("Workflow", back_populates="tasks")
    organization = relationship("Organization", back_populates="tasks")

class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id = Column(UUIDType, primary_key=True, index=True, default=uuid.uuid4)
    workflow_id = Column(UUIDType, ForeignKey("workflows.id"), nullable=False)
    status = Column(EnumType("pending", "running", "completed", "failed", "cancelled", name="workflow_run_status"), default="pending")
    input = Column(JSONBType, nullable=False)
    output = Column(JSONBType, nullable=True)
    error = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)

    workflow = relationship("Workflow", back_populates="runs")
    tasks = relationship("Task", back_populates="workflow_run")

class TaskLog(Base):
    __tablename__ = "task_logs"

    id = Column(UUIDType, primary_key=True, index=True, default=uuid.uuid4)
    task_id = Column(UUIDType, ForeignKey("tasks.id"), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    level = Column(EnumType("debug", "info", "warning", "error", name="log_level"), default="info")
    message = Column(Text, nullable=False)
    metadata = Column(JSONBType, nullable=True)

    task = relationship("Task", back_populates="logs")

class UsageMetric(Base):
    __tablename__ = "usage_metrics"

    id = Column(UUIDType, primary_key=True, index=True, default=uuid.uuid4)
    organization_id = Column(UUIDType, ForeignKey("organizations.id"), nullable=False)
    agent_id = Column(UUIDType, ForeignKey("agents.id"), nullable=True)
    task_id = Column(UUIDType, ForeignKey("tasks.id"), nullable=True)
    metric_type = Column(EnumType("tasks", "tokens", "api_calls", name="metric_type"), nullable=False)
    value = Column(Integer, nullable=False)
    cost_usd = Column(Float, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    organization = relationship("Organization", back_populates="usage_metrics")
    agent = relationship("Agent", back_populates="usage_metrics")
    task = relationship("Task", back_populates="usage_metrics")

class AgentVersion(Base):
    __tablename__ = "agent_versions"

    id = Column(UUIDType, primary_key=True, index=True, default=uuid.uuid4)
    agent_id = Column(UUIDType, ForeignKey("agents.id"), nullable=False)
    version = Column(Integer, nullable=False)
    config = Column(JSONBType, nullable=False)  # snapshot of agent config
    deployed_at = Column(DateTime(timezone=True), server_default=func.now())
    deployed_by = Column(UUIDType, ForeignKey("users.id"), nullable=False)

    agent = relationship("Agent", back_populates="versions")
    deployed_by_user = relationship("User", foreign_keys=[deployed_by])

# Add relationships for back_populates
def _setup_relationships():
    Organization.members = relationship("OrganizationMember", back_populates="organization")
    Organization.agents = relationship("Agent", back_populates="organization")
    Organization.workflows = relationship("Workflow", back_populates="organization")
    Organization.integrations = relationship("Integration", back_populates="organization")
    Organization.usage_metrics = relationship("UsageMetric", back_populates="organization")
    Organization.subscription = relationship("Subscription", back_populates="organization")

    User.organizations = relationship("OrganizationMember", back_populates="user")
    User.agents = relationship("Agent", back_populates="creator")
    User.workflows = relationship("Workflow", back_populates="creator")
    User.tasks = relationship("Task", back_populates="creator")

    Agent.creator = relationship("User", back_populates="agents")
    Agent.organization = relationship("Organization", back_populates="agents")
    Agent.workflows = relationship("Workflow", back_populates="agent")
    Agent.usage_metrics = relationship("UsageMetric", back_populates="agent")
    Agent.versions = relationship("AgentVersion", back_populates="agent", order_by=lambda: desc(AgentVersion.version))

    Workflow.creator = relationship("User", back_populates="workflows")
    Workflow.organization = relationship("Organization", back_populates="workflows")
    Workflow.agent = relationship("Agent", back_populates="workflows")
    Workflow.tasks = relationship("Task", back_populates="workflow")
    Workflow.runs = relationship("WorkflowRun", back_populates="workflow")

    Task.creator = relationship("User", back_populates="tasks")
    Task.workflow = relationship("Workflow", back_populates="tasks")
    Task.organization = relationship("Organization", back_populates="tasks")
    Task.usage_metrics = relationship("UsageMetric", back_populates="task")
    Task.logs = relationship("TaskLog", back_populates="task")

    TaskLog.task = relationship("Task", back_populates="logs")

_setup_relationships()