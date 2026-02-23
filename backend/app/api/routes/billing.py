from typing import Any, Dict, Optional, List
from datetime import datetime, timedelta, calendar
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.core.security.auth_handler import AuthHandler
from app.core.security.utils import RateLimiter, InputValidator
from app.models.models import User, Organization, UsageMetric, Task, Agent, WorkflowRun, Membership, PlanEnum, RoleEnum, TaskLog
from app.schemas.billing import (
    Subscription, Invoice, Usage, StripePortal, SubscriptionResponse,
    InvoiceResponse, UsageResponse, StripePortalResponse, BillingErrorResponse,
    BillingValidationError, BillingValidationErrorResponse
)

router = APIRouter()

# Authentication dependencies
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# Helper functions
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends()) -> User:
    return await AuthHandler.get_current_active_user(token, db)

async def get_current_org(user: User = Depends(get_current_user), db: Session = Depends()) -> Organization:
    # Get the user's organization
    membership = db.query(Membership).filter(
        Membership.user_id == user.id,
        Membership.role.in_([RoleEnum.owner, RoleEnum.admin])
    ).first()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User must be organization owner or admin to access billing"
        )

    return membership.organization

# Rate limiting configurations
RATE_LIMIT_SUBSCRIPTION = {"key": "billing:subscription", "max_requests": 100, "window_seconds": 3600}
RATE_LIMIT_INVOICES = {"key": "billing:invoices", "max_requests": 100, "window_seconds": 3600}
RATE_LIMIT_USAGE = {"key": "billing:usage", "max_requests": 100, "window_seconds": 3600}
RATE_LIMIT_PORTAL = {"key": "billing:portal", "max_requests": 100, "window_seconds": 3600}

# GET /api/v1/billing/subscription - Current subscription
@router.get("/billing/subscription", response_model=SubscriptionResponse)
async def get_current_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Rate limiting
    org = await get_current_org(current_user, db)
    rate_limit_key = f"{RATE_LIMIT_SUBSCRIPTION['key']}:{org.id}"
    if RateLimiter.is_rate_limited(rate_limit_key, RATE_LIMIT_SUBSCRIPTION["max_requests"], RATE_LIMIT_SUBSCRIPTION["window_seconds"]):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many subscription requests. Try again later."
        )

    try:
        # Get subscription details
        plan = org.plan.value
        stripe_customer_id = org.stripe_customer_id
        billing_email = org.billing_email

        # Get current usage
        current_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        next_month = (current_month + timedelta(days=32)).replace(day=1)

        # Calculate usage metrics
        usage_metrics = db.query(UsageMetric).filter(
            UsageMetric.organization_id == org.id,
            UsageMetric.date >= current_month.date(),
            UsageMetric.date < next_month.date()
        ).all()

        total_tasks = 0
        total_tokens = 0
        total_api_calls = 0
        total_cost = 0.0

        for metric in usage_metrics:
            if metric.metric_type == MetricTypeEnum.tasks:
                total_tasks += metric.value
            elif metric.metric_type == MetricTypeEnum.tokens:
                total_tokens += metric.value
            elif metric.metric_type == MetricTypeEnum.api_calls:
                total_api_calls += metric.value
            if metric.cost_usd:
                total_cost += metric.cost_usd

        # Get plan limits
        plan_limits = {
            "free": {"monthly_cost": 0, "included_tasks": 100, "included_tokens": 10000, "included_api_calls": 1000},
            "starter": {"monthly_cost": 99, "included_tasks": 1000, "included_tokens": 100000, "included_api_calls": 10000},
            "pro": {"monthly_cost": 299, "included_tasks": 10000, "included_tokens": 1000000, "included_api_calls": 100000},
            "business": {"monthly_cost": 799, "included_tasks": 50000, "included_tokens": 5000000, "included_api_calls": 500000},
            "enterprise": {"monthly_cost": None, "included_tasks": None, "included_tokens": None, "included_api_calls": None}  # Custom pricing
        }

        plan_info = plan_limits.get(plan, {})
        included_tasks = plan_info.get("included_tasks", 0)
        included_tokens = plan_info.get("included_tokens", 0)
        included_api_calls = plan_info.get("included_api_calls", 0)

        # Calculate overage
        tasks_overage = max(0, total_tasks - included_tasks)
        tokens_overage = max(0, total_tokens - included_tokens)
        api_calls_overage = max(0, total_api_calls - included_api_calls)

        # Calculate overage costs (example rates)
        task_overage_cost = tasks_overage * 0.01  # $0.01 per additional task
        token_overage_cost = tokens_overage * 0.00001  # $0.00001 per additional token
        api_call_overage_cost = api_calls_overage * 0.001  # $0.001 per additional API call

        total_overage_cost = task_overage_cost + token_overage_cost + api_call_overage_cost

        # Calculate total cost
        base_cost = plan_info.get("monthly_cost", 0)
        total_cost = base_cost + total_overage_cost

        # Calculate usage percentages
        tasks_usage_percentage = (total_tasks / included_tasks * 100) if included_tasks else 0
        tokens_usage_percentage = (total_tokens / included_tokens * 100) if included_tokens else 0
        api_calls_usage_percentage = (total_api_calls / included_api_calls * 100) if included_api_calls else 0

        subscription = Subscription(
            plan=plan,
            stripe_customer_id=stripe_customer_id,
            billing_email=billing_email,
            base_cost=base_cost,
            total_cost=total_cost,
            current_usage={
                "tasks": total_tasks,
                "tokens": total_tokens,
                "api_calls": total_api_calls,
                "cost": total_cost
            },
            included_limits={
                "tasks": included_tasks,
                "tokens": included_tokens,
                "api_calls": included_api_calls
            },
            overage={
                "tasks": tasks_overage,
                "tokens": tokens_overage,
                "api_calls": api_calls_overage,
                "cost": total_overage_cost
            },
            usage_percentages={
                "tasks": tasks_usage_percentage,
                "tokens": tokens_usage_percentage,
                "api_calls": api_calls_usage_percentage
            },
            plan_limits=plan_info,
            next_billing_date=str((current_month + timedelta(days=calendar.monthrange(current_month.year, current_month.month)[1])).date())
        )

        return SubscriptionResponse(subscription=subscription)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get subscription: {str(e)}"
        )


# POST /api/v1/billing/subscription - Upgrade/downgrade plan
@router.post("/billing/subscription", response_model=SubscriptionResponse)
async def update_subscription(
    new_plan: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Rate limiting
    org = await get_current_org(current_user, db)
    rate_limit_key = f"{RATE_LIMIT_SUBSCRIPTION['key']}:{org.id}"
    if RateLimiter.is_rate_limited(rate_limit_key, RATE_LIMIT_SUBSCRIPTION["max_requests"], RATE_LIMIT_SUBSCRIPTION["window_seconds"]):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many subscription update requests. Try again later."
        )

    # Validate new plan
    valid_plans = ["free", "starter", "pro", "business", "enterprise"]
    if new_plan not in valid_plans:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid plan: {new_plan}. Valid plans are: {', '.join(valid_plans)}"
        )

    try:
        # Update organization plan
        org.plan = PlanEnum(new_plan)
        org.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(org)

        # Return updated subscription info
        return await get_current_subscription(current_user, db)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update subscription: {str(e)}"
        )


# GET /api/v1/billing/invoices - List invoices
@router.get("/billing/invoices", response_model=InvoiceResponse)
async def list_invoices(
    page: int = 1,
    size: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Rate limiting
    org = await get_current_org(current_user, db)
    rate_limit_key = f"{RATE_LIMIT_INVOICES['key']}:{org.id}"
    if RateLimiter.is_rate_limited(rate_limit_key, RATE_LIMIT_INVOICES["max_requests"], RATE_LIMIT_INVOICES["window_seconds"]):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many invoice list requests. Try again later."
        )

    # Calculate offset
    offset = (page - 1) * size

    try:
        # In a real implementation, this would query the Stripe API or a database table
        # For now, we'll simulate invoice data
        invoices = [
            {
                "id": f"inv_{i}",
                "number": f"#{1000 + i}",
                "date": (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d"),
                "due_date": (datetime.utcnow() - timedelta(days=i-5)).strftime("%Y-%m-%d"),
                "amount": round(99 + (i * 10) + (i * 0.5), 2),
                "currency": "usd",
                "status": "paid" if i % 2 == 0 else "pending",
                "pdf_url": f"https://example.com/invoices/inv_{i}.pdf"
            }
            for i in range(page * size, (page - 1) * size, -1)
        ]

        # Get total count (in real implementation, this would be from database or API)
        total = 50  # Simulate total of 50 invoices

        return InvoiceResponse(
            invoices=invoices,
            total=total,
            page=page,
            size=size
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list invoices: {str(e)}"
        )


# GET /api/v1/billing/usage - Current period usage
@router.get("/billing/usage", response_model=UsageResponse)
async def get_current_usage(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Rate limiting
    org = await get_current_org(current_user, db)
    rate_limit_key = f"{RATE_LIMIT_USAGE['key']}:{org.id}"
    if RateLimiter.is_rate_limited(rate_limit_key, RATE_LIMIT_USAGE["max_requests"], RATE_LIMIT_USAGE["window_seconds"]):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many usage requests. Try again later."
        )

    try:
        # Get current period usage (this month)
        current_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        next_month = (current_month + timedelta(days=32)).replace(day=1)

        usage_metrics = db.query(UsageMetric).filter(
            UsageMetric.organization_id == org.id,
            UsageMetric.date >= current_month.date(),
            UsageMetric.date < next_month.date()
        ).all()

        total_tasks = 0
        total_tokens = 0
        total_api_calls = 0
        total_cost = 0.0

        for metric in usage_metrics:
            if metric.metric_type == MetricTypeEnum.tasks:
                total_tasks += metric.value
            elif metric.metric_type == MetricTypeEnum.tokens:
                total_tokens += metric.value
            elif metric.metric_type == MetricTypeEnum.api_calls:
                total_api_calls += metric.value
            if metric.cost_usd:
                total_cost += metric.cost_usd

        # Get plan info
        plan = org.plan.value
        plan_limits = {
            "free": {"included_tasks": 100, "included_tokens": 10000, "included_api_calls": 1000},
            "starter": {"included_tasks": 1000, "included_tokens": 100000, "included_api_calls": 10000},
            "pro": {"included_tasks": 10000, "included_tokens": 1000000, "included_api_calls": 100000},
            "business": {"included_tasks": 50000, "included_tokens": 5000000, "included_api_calls": 500000},
            "enterprise": {"included_tasks": None, "included_tokens": None, "included_api_calls": None}
        }

        plan_info = plan_limits.get(plan, {})
        included_tasks = plan_info.get("included_tasks", 0)
        included_tokens = plan_info.get("included_tokens", 0)
        included_api_calls = plan_info.get("included_api_calls", 0)

        # Calculate usage percentages
        tasks_usage_percentage = (total_tasks / included_tasks * 100) if included_tasks else 0
        tokens_usage_percentage = (total_tokens / included_tokens * 100) if included_tokens else 0
        api_calls_usage_percentage = (total_api_calls / included_api_calls * 100) if included_api_calls else 0

        usage = Usage(
            period={
                "start": str(current_month.date()),
                "end": str((next_month - timedelta(days=1)).date())
            },
            current_usage={
                "tasks": total_tasks,
                "tokens": total_tokens,
                "api_calls": total_api_calls,
                "cost": total_cost
            },
            included_limits={
                "tasks": included_tasks,
                "tokens": included_tokens,
                "api_calls": included_api_calls
            },
            usage_percentages={
                "tasks": tasks_usage_percentage,
                "tokens": tokens_usage_percentage,
                "api_calls": api_calls_usage_percentage
            },
            remaining_limits={
                "tasks": max(0, included_tasks - total_tasks) if included_tasks else None,
                "tokens": max(0, included_tokens - total_tokens) if included_tokens else None,
                "api_calls": max(0, included_api_calls - total_api_calls) if included_api_calls else None
            },
            plan=plan
        )

        return UsageResponse(usage=usage)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get current usage: {str(e)}"
        )


# POST /api/v1/billing/portal - Get Stripe portal URL
@router.post("/billing/portal", response_model=StripePortalResponse)
async def get_stripe_portal_url(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Rate limiting
    org = await get_current_org(current_user, db)
    rate_limit_key = f"{RATE_LIMIT_PORTAL['key']}:{org.id}"
    if RateLimiter.is_rate_limited(rate_limit_key, RATE_LIMIT_PORTAL["max_requests"], RATE_LIMIT_PORTAL["window_seconds"]):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many portal URL requests. Try again later."
        )

    try:
        # In a real implementation, this would create a Stripe session
        # For now, we'll simulate the URL
        stripe_customer_id = org.stripe_customer_id

        if not stripe_customer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organization is not connected to Stripe"
            )

        # Simulate Stripe portal URL (in real implementation, use stripe.checkout.sessions.create)
        portal_url = f"https://billing.stripe.com/p/{stripe_customer_id}"

        stripe_portal = StripePortal(
            url=portal_url,
            expires_at=str((datetime.utcnow() + timedelta(hours=1)).isoformat()),
            customer_id=stripe_customer_id,
            return_url="https://yourapp.com/billing"
        )

        return StripePortalResponse(stripe_portal=stripe_portal)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get Stripe portal URL: {str(e)}"
        )

# Error handler for validation errors
@router.exception_handler(BillingValidationErrorResponse)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=exc.json(),
        headers=RateLimiter.get_rate_limit_header("billing:validation", 100, 3600)
    )

# Error handler for general errors
@router.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=BillingErrorResponse(
            detail="An unexpected error occurred",
            error_code="INTERNAL_SERVER_ERROR",
            timestamp=datetime.utcnow()
        ).json(),
        headers=RateLimiter.get_rate_limit_header("billing:errors", 10, 3600)
    )