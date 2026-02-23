from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, ForeignKey, JSON, Float, Enum, UUID
from uuid import uuid4, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.database import Base
from enum import Enum as PyEnum


class UserRole(PyEnum):
    member = "member"
    owner = "owner"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    role = Column(Enum(UserRole), default=UserRole.member)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    organization = relationship("Organization", back_populates="members")
    created_agents = relationship("Agent", back_populates="creator")
    created_workflows = relationship("Workflow", back_populates="creator")
    created_tasks = relationship("Task", back_populates="creator")
    created_integrations = relationship("Integration", back_populates="creator")


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    slug = Column(String, unique=True, index=True, nullable=False)
    is_active = Column(Boolean, default=True)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    owner = relationship("User", foreign_keys=[owner_id])
    members = relationship("Member", back_populates="organization")
    agents = relationship("Agent", back_populates="organization")
    workflows = relationship("Workflow", back_populates="organization")
    tasks = relationship("Task", back_populates="organization")
    integrations = relationship("Integration", back_populates="organization")
    subscriptions = relationship("Subscription", back_populates="organization")
    invoices = relationship("Invoice", back_populates="organization")
    payment_methods = relationship("PaymentMethod", back_populates="organization")
    workflow_runs = relationship("WorkflowRun", back_populates="organization")
    usage_alerts = relationship("UsageAlerts", back_populates="organization", uselist=False)
    organization_settings = relationship("OrganizationSettings", back_populates="organization", uselist=False)


class Member(Base):
    __tablename__ = "members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.member)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")
    organization = relationship("Organization", back_populates="members")


class Agent(Base):
    __tablename__ = "agents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    agent_type = Column(String, nullable=False)  # llm, rule_based, hybrid
    model = Column(String, nullable=False)
    api_key = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    organization = relationship("Organization", back_populates="agents")
    creator = relationship("User", foreign_keys=[created_by])
    tasks = relationship("Task", back_populates="agent")


class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    triggers = Column(JSON, nullable=False, default=[])  # List of trigger definitions
    steps = Column(JSON, nullable=False, default=[])  # List of step definitions
    is_active = Column(Boolean, default=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    organization = relationship("Organization", back_populates="workflows")
    creator = relationship("User", foreign_keys=[created_by])
    runs = relationship("WorkflowRun", back_populates="workflow")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=True)
    input_data = Column(JSON, nullable=False, default={})
    output_data = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    status = Column(String, nullable=False)  # pending, running, completed, failed, cancelled
    priority = Column(String, nullable=False)  # low, normal, high, critical
    execution_time = Column(Float, nullable=True)  # in seconds
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    organization = relationship("Organization", back_populates="tasks")
    creator = relationship("User", foreign_keys=[created_by])
    agent = relationship("Agent", back_populates="tasks")
    workflow_run = relationship("WorkflowRun", back_populates="tasks")
    logs = relationship("TaskLog", back_populates="task")


class Integration(Base):
    __tablename__ = "integrations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    integration_type = Column(String, nullable=False)  # webhook, api, database, file_system, cloud_service
    config = Column(JSON, nullable=False, default={})
    is_active = Column(Boolean, default=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    organization = relationship("Organization", back_populates="integrations")
    creator = relationship("User", foreign_keys=[created_by])


class Analytics(Base):
    __tablename__ = "analytics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    metric_name = Column(String, nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    tags = Column(JSON, nullable=False, default=[])
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)

    organization = relationship("Organization")


class BillingPlan(Base):
    __tablename__ = "billing_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    currency = Column(String, nullable=False)
    features = Column(JSON, nullable=False, default={})
    max_agents = Column(Integer, nullable=False, default=0)
    max_workflows = Column(Integer, nullable=False, default=0)
    max_tasks_per_month = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("billing_plans.id"), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    status = Column(String, nullable=False)  # active, trial, cancelled, expired
    current_period_start = Column(DateTime(timezone=True), nullable=False)
    current_period_end = Column(DateTime(timezone=True), nullable=False)
    cancel_at_period_end = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    organization = relationship("Organization", back_populates="subscriptions")
    plan = relationship("BillingPlan")


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    number = Column(String, unique=True, nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    issue_date = Column(DateTime(timezone=True), nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String, nullable=False)
    status = Column(String, nullable=False)  # draft, sent, paid, overdue
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    pdf_url = Column(String, nullable=True)
    items = Column(JSON, nullable=False, default=[])
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    organization = relationship("Organization", back_populates="invoices")


class PaymentMethod(Base):
    __tablename__ = "payment_methods"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    type = Column(String, nullable=False)  # credit_card, bank_account, etc.
    last_four = Column(String, nullable=False)
    card_brand = Column(String, nullable=True)
    expiration_month = Column(Integer, nullable=True)
    expiration_year = Column(Integer, nullable=True)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    organization = relationship("Organization", back_populates="payment_methods")


class UsageAlerts(Base):
    __tablename__ = "usage_alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, unique=True)
    agents = Column(Integer, nullable=True)  # Alert when agents exceed this percentage
    workflows = Column(Integer, nullable=True)  # Alert when workflows exceed this percentage
    tasks = Column(Integer, nullable=True)  # Alert when tasks exceed this percentage
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    organization = relationship("Organization", back_populates="usage_alerts")


class OrganizationSettings(Base):
    __tablename__ = "organization_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, unique=True)
    alerts_webhook = Column(String, nullable=True)
    default_agent_type = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflows.id"), nullable=False)
    status = Column(String, nullable=False)  # pending, running, completed, failed, cancelled
    input_data = Column(JSON, nullable=False, default={})
    output_data = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    organization = relationship("Organization", back_populates="workflow_runs")
    creator = relationship("User", foreign_keys=[created_by])
    workflow = relationship("Workflow", back_populates="runs")
    tasks = relationship("Task", back_populates="workflow_run")


class TaskLog(Base):
    __tablename__ = "task_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    level = Column(String, nullable=False)  # debug, info, warning, error
    message = Column(Text, nullable=False)
    metadata = Column(JSON, nullable=True)

    task = relationship("Task", back_populates="logs")