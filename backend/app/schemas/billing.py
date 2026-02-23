from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, constr, validator
from app.models.models import StatusEnum, TaskStatusEnum, WorkflowStatusEnum, RoleEnum, PlanEnum, MetricTypeEnum


class Subscription(BaseModel):
    plan: str
    stripe_customer_id: Optional[str]
    billing_email: Optional[str]
    base_cost: float
    total_cost: float
    current_usage: Dict[str, Any]
    included_limits: Dict[str, Any]
    overage: Dict[str, Any]
    usage_percentages: Dict[str, float]
    plan_limits: Dict[str, Any]
    next_billing_date: str


class Invoice(BaseModel):
    id: str
    number: str
    date: str
    due_date: str
    amount: float
    currency: str
    status: str
    pdf_url: str


class Usage(BaseModel):
    period: Dict[str, str]
    current_usage: Dict[str, Any]
    included_limits: Dict[str, Any]
    usage_percentages: Dict[str, float]
    remaining_limits: Dict[str, Optional[int]]
    plan: str


class StripePortal(BaseModel):
    url: str
    expires_at: str
    customer_id: str
    return_url: str


class SubscriptionResponse(BaseModel):
    subscription: Subscription


class InvoiceResponse(BaseModel):
    invoices: List[Invoice]
    total: int
    page: int
    size: int


class UsageResponse(BaseModel):
    usage: Usage


class StripePortalResponse(BaseModel):
    stripe_portal: StripePortal


class BillingValidationError(BaseModel):
    field: str
    message: str


class BillingValidationErrorResponse(BaseModel):
    detail: str
    errors: List[BillingValidationError]
    timestamp: datetime = datetime.utcnow()


class BillingErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
    timestamp: datetime = datetime.utcnow()