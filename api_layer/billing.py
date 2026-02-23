from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import datetime
import stripe
from pydantic import ValidationError

from ..shared.database import get_db
from ..shared.security import get_current_active_user, get_current_active_superuser, get_current_organization_member
from ..shared.models import User, Organization, Subscription, UsageMetric
from ..shared.schemas import (
    Subscription, BillingUpdate, UsageMetric,
    Pagination, PaginatedResponse
)
from ..shared.utils import (
    paginate_query, create_paginated_response,
    filter_by_organization, get_user_organizations
)

router = APIRouter()


@router.get("/plans", response_model=List[Dict[str, Any]])
def get_available_plans():
    """Get available subscription plans."""

    return [
        {
            "id": "free",
            "name": "Free",
            "price": 0.0,
            "currency": "USD",
            "interval": "month",
            "features": [
                "Up to 100 tasks/month",
                "1 active workflow",
                "Community support",
                "Standard agents"
            ],
            "description": "Perfect for getting started with AI agents",
            "recommended": False
        },
        {
            "id": "pro",
            "name": "Pro",
            "price": 29.0,
            "currency": "USD",
            "interval": "month",
            "features": [
                "Up to 1,000 tasks/month",
                "10 active workflows",
                "Priority support",
                "Advanced agents",
                "API access",
                "Webhook integrations"
            ],
            "description": "For professional teams and power users",
            "recommended": True
        },
        {
            "id": "enterprise",
            "name": "Enterprise",
            "price": 299.0,
            "currency": "USD",
            "interval": "month",
            "features": [
                "Unlimited tasks",
                "Unlimited workflows",
                "24/7 priority support",
                "Custom agents",
                "On-premise deployment",
                "SLA",
                "Audit logs",
                "SSO integration"
            ],
            "description": "For large organizations with advanced needs",
            "recommended": False
        }
    ]


@router.get("/subscriptions", response_model=List[Subscription])
def get_subscriptions(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    organization_id: Optional[int] = None,
    pagination: Pagination = Depends()
):
    """Get subscriptions for the user's organizations."""

    # Get subscriptions for all organizations the user belongs to
    user_organizations = get_user_organizations(db, current_user.id)
    organization_ids = [org.id for org in user_organizations]

    query = db.query(Subscription).filter(
        Subscription.organization_id.in_(organization_ids)
    )

    paginated_query, total_count = paginate_query(db, query, pagination)
    items = paginated_query.all()

    return create_paginated_response(items, total_count, pagination)


@router.get("/subscriptions/{subscription_id}", response_model=Subscription)
def get_subscription(
    subscription_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get subscription details."""

    subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )

    # Verify user has access to this subscription's organization
    org_query = db.query(Organization).filter(Organization.id == subscription.organization_id)
    org_query = filter_by_organization(db, org_query, subscription.organization_id, current_user)
    organization = org_query.first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found or access denied"
        )

    return Subscription.from_orm(subscription)


@router.post("/subscriptions", response_model=Subscription)
def create_subscription(
    subscription_data: Subscription,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Create a new subscription."""

    # Verify user belongs to the specified organization
    org_query = db.query(Organization).filter(Organization.id == subscription_data.organization_id)
    org_query = filter_by_organization(db, org_query, subscription_data.organization_id, current_user)
    organization = org_query.first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found or access denied"
        )

    # Check if user is member of this organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == subscription_data.organization_id
    ).first()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this organization"
        )

    # Only owners and admins can manage subscriptions
    if member.role not in ["owner", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owners and admins can manage subscriptions"
        )

    # Validate plan type
    available_plans = [plan["id"] for plan in get_available_plans()]
    if subscription_data.plan_type not in available_plans:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid plan type. Available plans: {', '.join(available_plans)}"
        )

    # Check if organization already has an active subscription
    existing_subscription = db.query(Subscription).filter(
        Subscription.organization_id == subscription_data.organization_id,
        Subscription.status == "active"
    ).first()

    if existing_subscription:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization already has an active subscription"
        )

    # Create subscription
    current_period_start = datetime.datetime.now()
    current_period_end = current_period_start + datetime.timedelta(days=30)

    subscription = Subscription(
        organization_id=subscription_data.organization_id,
        plan_type=subscription_data.plan_type,
        status="active",
        current_period_start=current_period_start,
        current_period_end=current_period_end,
        stripe_subscription_id=None  # Will be set after payment processing
    )

    db.add(subscription)
    db.commit()
    db.refresh(subscription)

    return Subscription.from_orm(subscription)


@router.put("/subscriptions/{subscription_id}", response_model=Subscription)
def update_subscription(
    subscription_id: int,
    subscription_update: BillingUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update subscription (upgrade/downgrade)."""

    subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )

    # Verify user has access to this subscription's organization
    org_query = db.query(Organization).filter(Organization.id == subscription.organization_id)
    org_query = filter_by_organization(db, org_query, subscription.organization_id, current_user)
    organization = org_query.first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found or access denied"
        )

    # Check if user is member of this organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == subscription.organization_id
    ).first()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this organization"
        )

    # Only owners and admins can update subscriptions
    if member.role not in ["owner", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owners and admins can update subscriptions"
        )

    # Validate new plan type if provided
    if subscription_update.plan_type:
        available_plans = [plan["id"] for plan in get_available_plans()]
        if subscription_update.plan_type not in available_plans:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid plan type. Available plans: {', '.join(available_plans)}"
            )

        # Check if changing to the same plan
        if subscription_update.plan_type == subscription.plan_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot update to the same plan"
            )

        # Update subscription
        subscription.plan_type = subscription_update.plan_type
        subscription.current_period_start = datetime.datetime.now()
        subscription.current_period_end = subscription.current_period_start + datetime.timedelta(days=30)

    db.commit()
    db.refresh(subscription)

    return Subscription.from_orm(subscription)


@router.post("/subscriptions/{subscription_id}/cancel")
def cancel_subscription(
    subscription_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Cancel subscription."""

    subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )

    # Verify user has access to this subscription's organization
    org_query = db.query(Organization).filter(Organization.id == subscription.organization_id)
    org_query = filter_by_organization(db, org_query, subscription.organization_id, current_user)
    organization = org_query.first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found or access denied"
        )

    # Check if user is member of this organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == subscription.organization_id
    ).first()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this organization"
        )

    # Only owners and admins can cancel subscriptions
    if member.role not in ["owner", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owners and admins can cancel subscriptions"
        )

    # Cannot cancel if already cancelled or expired
    if subscription.status in ["cancelled", "expired"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Subscription is already cancelled or expired"
        )

    subscription.status = "cancelled"
    subscription.current_period_end = datetime.datetime.now()
    db.commit()

    return {"message": "Subscription cancelled successfully"}


@router.get("/usage", response_model=List[UsageMetric])
def get_usage_metrics_endpoint(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    organization_id: Optional[int] = None,
    metric_type: Optional[str] = None,
    start_date: Optional[datetime.datetime] = None,
    end_date: Optional[datetime.datetime] = None,
    pagination: Pagination = Depends()
):
    """Get usage metrics for the user's organizations."""

    # Build base query
    query = db.query(UsageMetric)

    # Filter by organization if specified
    if organization_id:
        org_query = db.query(Organization).filter(Organization.id == organization_id)
        org_query = filter_by_organization(db, org_query, organization_id, current_user)
        organization = org_query.first()
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found or access denied"
            )

        query = query.filter(UsageMetric.organization_id == organization_id)
    else:
        # Get usage for all organizations the user belongs to
        user_organizations = get_user_organizations(db, current_user.id)
        organization_ids = [org.id for org in user_organizations]
        query = query.filter(UsageMetric.organization_id.in_(organization_ids))

    # Filter by metric type
    if metric_type:
        query = query.filter(UsageMetric.metric_type == metric_type)

    # Filter by date range
    if start_date and end_date:
        query = query.filter(UsageMetric.timestamp.between(start_date, end_date))

    # Order by timestamp (newest first)
    query = query.order_by(UsageMetric.timestamp.desc())

    paginated_query, total_count = paginate_query(db, query, pagination)
    items = paginated_query.all()

    return create_paginated_response(items, total_count, pagination)


@router.post("/usage")
def record_usage_metric(
    metric_data: UsageMetric,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Record a usage metric (internal use)."""

    # Verify user belongs to the specified organization
    org_query = db.query(Organization).filter(Organization.id == metric_data.organization_id)
    org_query = filter_by_organization(db, org_query, metric_data.organization_id, current_user)
    organization = org_query.first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found or access denied"
        )

    # Check if user is member of this organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == metric_data.organization_id
    ).first()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this organization"
        )

    # Validate metric type
    valid_metric_types = [
        "token_usage", "execution_time", "api_calls", "cost", "storage_usage",
        "task_count", "workflow_count", "agent_count"
    ]

    if metric_data.metric_type not in valid_metric_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid metric type. Valid types: {', '.join(valid_metric_types)}"
        )

    # Create usage metric
    usage_metric = UsageMetric(
        organization_id=metric_data.organization_id,
        agent_id=metric_data.agent_id,
        task_id=metric_data.task_id,
        metric_type=metric_data.metric_type,
        value=metric_data.value,
        unit=metric_data.unit,
        timestamp=metric_data.timestamp or datetime.datetime.now()
    )

    db.add(usage_metric)
    db.commit()

    return {"message": "Usage metric recorded successfully", "metric_id": usage_metric.id}


@router.get("/limits", response_model=Dict[str, Any])
def get_subscription_limits(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current subscription limits and usage."""

    # Get all organizations the user belongs to
    user_organizations = get_user_organizations(db, current_user.id)
    organization_ids = [org.id for org in user_organizations]

    # Get active subscription for each organization
    subscriptions = db.query(Subscription).filter(
        Subscription.organization_id.in_(organization_ids),
        Subscription.status == "active"
    ).all()

    # Get usage metrics
    usage_query = db.query(
        UsageMetric.organization_id,
        UsageMetric.metric_type,
        func.sum(UsageMetric.value).label('total_value')
    ).filter(
        UsageMetric.organization_id.in_(organization_ids),
        UsageMetric.metric_type.in_(['token_usage', 'task_count'])
    ).group_by(
        UsageMetric.organization_id,
        UsageMetric.metric_type
    )

    usage_results = usage_query.all()

    # Prepare response
    limits_data = []
    for subscription in subscriptions:
        organization = next(
            org for org in user_organizations
            if org.id == subscription.organization_id
        )

        # Get usage for this organization
        org_usage = {}
        for row in usage_results:
            if row.organization_id == subscription.organization_id:
                org_usage[row.metric_type] = float(row.total_value)

        # Get plan limits
        plan_limits = get_plan_limits(subscription.plan_type)

        limits_data.append({
            "organization": {
                "id": organization.id,
                "name": organization.name,
                "slug": organization.slug
            },
            "subscription": {
                "id": subscription.id,
                "plan_type": subscription.plan_type,
                "status": subscription.status,
                "current_period_start": subscription.current_period_start.isoformat(),
                "current_period_end": subscription.current_period_end.isoformat()
            },
            "limits": {
                "token_limit": plan_limits.get("token_limit", 0),
                "task_limit": plan_limits.get("task_limit", 0),
                "workflow_limit": plan_limits.get("workflow_limit", 0),
                "agent_limit": plan_limits.get("agent_limit", 0)
            },
            "usage": {
                "token_usage": org_usage.get("token_usage", 0.0),
                "task_count": org_usage.get("task_count", 0),
                "workflow_count": get_entity_count(db, "Workflow", subscription.organization_id),
                "agent_count": get_entity_count(db, "Agent", subscription.organization_id)
            },
            "usage_percentage": {
                "token_usage": (org_usage.get("token_usage", 0.0) / plan_limits.get("token_limit", 1)) * 100 if plan_limits.get("token_limit", 0) > 0 else 0,
                "task_count": (org_usage.get("task_count", 0) / plan_limits.get("task_limit", 1)) * 100 if plan_limits.get("task_limit", 0) > 0 else 0,
                "workflow_count": (get_entity_count(db, "Workflow", subscription.organization_id) / plan_limits.get("workflow_limit", 1)) * 100 if plan_limits.get("workflow_limit", 0) > 0 else 0,
                "agent_count": (get_entity_count(db, "Agent", subscription.organization_id) / plan_limits.get("agent_limit", 1)) * 100 if plan_limits.get("agent_limit", 0) > 0 else 0
            },
            "limits_reached": {
                "token_usage": org_usage.get("token_usage", 0.0) >= plan_limits.get("token_limit", 0),
                "task_count": org_usage.get("task_count", 0) >= plan_limits.get("task_limit", 0),
                "workflow_count": get_entity_count(db, "Workflow", subscription.organization_id) >= plan_limits.get("workflow_limit", 0),
                "agent_count": get_entity_count(db, "Agent", subscription.organization_id) >= plan_limits.get("agent_limit", 0)
            }
        })

    return {"organizations": limits_data}


@router.get("/billing-history", response_model=List[Dict[str, Any]])
def get_billing_history(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    organization_id: Optional[int] = None,
    pagination: Pagination = Depends()
):
    """Get billing history (mock implementation)."""

    # In a real implementation, you would integrate with Stripe or another payment provider
    # For now, we'll return mock billing history

    # Get organizations the user belongs to
    if organization_id:
        org_query = db.query(Organization).filter(Organization.id == organization_id)
        org_query = filter_by_organization(db, org_query, organization_id, current_user)
        organization = org_query.first()
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found or access denied"
            )

        organization_ids = [organization_id]
    else:
        user_organizations = get_user_organizations(db, current_user.id)
        organization_ids = [org.id for org in user_organizations]

    billing_history = []

    for org_id in organization_ids:
        # Mock billing history for the last 6 months
        for month in range(6, 0, -1):
            billing_date = datetime.datetime.now() - datetime.timedelta(days=month*30)
            billing_history.append({
                "organization_id": org_id,
                "date": billing_date.isoformat(),
                "amount": get_mock_amount(org_id, billing_date),
                "currency": "USD",
                "description": f"Monthly subscription for {billing_date.strftime('%B %Y')}",
                "status": "paid",
                "invoice_id": f"inv-{org_id}-{billing_date.strftime('%Y%m')}"
            })

    # Sort by date and apply pagination
    billing_history.sort(key=lambda x: x["date"], reverse=True)

    paginated_query, total_count = paginate_query(db, billing_history, pagination)
    items = paginated_query.all()

    return create_paginated_response(items, total_count, pagination)


def get_mock_amount(organization_id: int, date: datetime.datetime) -> float:
    """Get mock amount for billing (based on plan)."""

    # In a real implementation, you would get this from your payment provider
    # For now, we'll return different amounts based on organization ID

    if organization_id % 3 == 0:
        return 29.0  # Pro plan
    elif organization_id % 3 == 1:
        return 299.0  # Enterprise plan
    else:
        return 0.0  # Free plan


def get_plan_limits(plan_type: str) -> Dict[str, int]:
    """Get limits for a subscription plan."""

    plan_limits = {
        "free": {
            "token_limit": 100000,
            "task_limit": 100,
            "workflow_limit": 1,
            "agent_limit": 3
        },
        "pro": {
            "token_limit": 1000000,
            "task_limit": 1000,
            "workflow_limit": 10,
            "agent_limit": 20
        },
        "enterprise": {
            "token_limit": float('inf'),
            "task_limit": float('inf'),
            "workflow_limit": float('inf'),
            "agent_limit": float('inf')
        }
    }

    return plan_limits.get(plan_type, plan_limits["free"])


def get_entity_count(db: Session, entity_name: str, organization_id: int) -> int:
    """Get count of entities for an organization."""

    from sqlalchemy import text

    query = f"SELECT COUNT(*) FROM {entity_name.lower()}s WHERE organization_id = :org_id"
    result = db.execute(text(query), {"org_id": organization_id}).scalar()

    return int(result) if result else 0