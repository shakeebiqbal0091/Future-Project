from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from api.schemas import (
    ErrorResponse, PaginationResponse, SortOrder, Filter
)
from core.database import get_db
from core.auth import get_current_user, get_current_active_user, get_current_organization

router = APIRouter()


@router.get("/plans")
async def get_billing_plans(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    organization = get_current_organization(current_user, db)
    if not organization:
        raise HTTPException(status_code=404, detail="User not part of any organization")

    # Get available billing plans
    plans = db.query(BillingPlan).filter(BillingPlan.is_active == True).all()

    # Get user's current subscription
    subscription = db.query(Subscription).filter(
        Subscription.organization_id == organization.id,
        Subscription.status == "active"
    ).first()

    current_plan_id = subscription.plan_id if subscription else None

    plans_data = []
    for plan in plans:
        is_current_plan = plan.id == current_plan_id
        plans_data.append({
            "id": plan.id,
            "name": plan.name,
            "description": plan.description,
            "price": plan.price,
            "currency": plan.currency,
            "features": plan.features,
            "max_agents": plan.max_agents,
            "max_workflows": plan.max_workflows,
            "max_tasks_per_month": plan.max_tasks_per_month,
            "is_current_plan": is_current_plan,
            "is_recommended": plan.id == 2,  # Example: recommend standard plan
            "savings": plan.savings if hasattr(plan, 'savings') else 0
        })

    return {
        "organization_id": organization.id,
        "current_plan_id": current_plan_id,
        "plans": plans_data,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/subscription")
async def get_subscription_info(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    organization = get_current_organization(current_user, db)
    if not organization:
        raise HTTPException(status_code=404, detail="User not part of any organization")

    subscription = db.query(Subscription).filter(
        Subscription.organization_id == organization.id,
        Subscription.status == "active"
    ).first()

    if not subscription:
        return {
            "organization_id": organization.id,
            "status": "no_active_subscription",
            "message": "No active subscription found",
            "timestamp": datetime.utcnow().isoformat()
        }

    # Get plan details
    plan = db.query(BillingPlan).filter(BillingPlan.id == subscription.plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Billing plan not found")

    # Calculate usage
    usage = await get_usage_analytics(current_user, db)

    return {
        "organization_id": organization.id,
        "subscription": {
            "id": subscription.id,
            "plan": {
                "id": plan.id,
                "name": plan.name,
                "price": plan.price,
                "currency": plan.currency,
                "features": plan.features,
                "max_agents": plan.max_agents,
                "max_workflows": plan.max_workflows,
                "max_tasks_per_month": plan.max_tasks_per_month
            },
            "status": subscription.status,
            "current_period_start": subscription.current_period_start.isoformat(),
            "current_period_end": subscription.current_period_end.isoformat(),
            "next_billing_date": (subscription.current_period_end + timedelta(days=30)).isoformat() if subscription.current_period_end else None,
            "cancel_at_period_end": subscription.cancel_at_period_end or False
        },
        "usage": {
            "agents_used": usage["agents"]["total"],
            "workflows_used": usage["workflows"]["total"],
            "tasks_executed_this_month": usage["tasks"]["total"],
            "usage_percentage": {
                "agents": (usage["agents"]["total"] / plan.max_agents * 100) if plan.max_agents > 0 else 0,
                "workflows": (usage["workflows"]["total"] / plan.max_workflows * 100) if plan.max_workflows > 0 else 0,
                "tasks": (usage["tasks"]["total"] / plan.max_tasks_per_month * 100) if plan.max_tasks_per_month > 0 else 0
            }
        },
        "usage_alerts": {
            "agents_near_limit": usage["usage_percentage"]["agents"] > 80,
            "workflows_near_limit": usage["usage_percentage"]["workflows"] > 80,
            "tasks_near_limit": usage["usage_percentage"]["tasks"] > 80
        },
        "upgrade_recommendations": [],
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/subscription/upgrade")
async def upgrade_subscription(
    plan_id: int,
    payment_method_id: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    organization = get_current_organization(current_user, db)
    if not organization:
        raise HTTPException(status_code=404, detail="User not part of any organization")

    # Get the new plan
    new_plan = db.query(BillingPlan).filter(
        BillingPlan.id == plan_id,
        BillingPlan.is_active == True
    ).first()

    if not new_plan:
        raise HTTPException(status_code=404, detail="Billing plan not found")

    # Get current subscription
    current_subscription = db.query(Subscription).filter(
        Subscription.organization_id == organization.id,
        Subscription.status == "active"
    ).first()

    # Validate payment (simplified - in real implementation, integrate with payment processor)
    if not payment_method_id:
        # Check if payment method exists for organization
        payment_method = db.query(PaymentMethod).filter(
            PaymentMethod.organization_id == organization.id,
            PaymentMethod.is_default == True
        ).first()

        if not payment_method:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No payment method available. Please add a payment method first."
            )

    # Calculate prorated amount if upgrading (simplified)
    prorated_amount = 0  # In real implementation, calculate based on time remaining

    # Create new subscription
    new_subscription = Subscription(
        plan_id=new_plan.id,
        organization_id=organization.id,
        status="active",
        current_period_start=datetime.utcnow(),
        current_period_end=datetime.utcnow() + timedelta(days=30),  # 30-day billing cycle
        cancel_at_period_end=False
    )

    db.add(new_subscription)
    db.commit()

    # Cancel old subscription if exists
    if current_subscription:
        current_subscription.status = "cancelled"
        current_subscription.cancel_at_period_end = False
        db.commit()

    return {
        "message": "Subscription upgraded successfully",
        "new_plan": {
            "id": new_plan.id,
            "name": new_plan.name,
            "price": new_plan.price,
            "currency": new_plan.currency
        },
        "prorated_amount": prorated_amount,
        "next_billing_date": new_subscription.current_period_end.isoformat(),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/subscription/cancel")
async def cancel_subscription(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    organization = get_current_organization(current_user, db)
    if not organization:
        raise HTTPException(status_code=404, detail="User not part of any organization")

    subscription = db.query(Subscription).filter(
        Subscription.organization_id == organization.id,
        Subscription.status == "active"
    ).first()

    if not subscription:
        raise HTTPException(status_code=404, detail="No active subscription found")

    # Set to cancel at period end
    subscription.cancel_at_period_end = True
    subscription.status = "cancelled"
    db.commit()

    return {
        "message": "Subscription will be cancelled at the end of the current period",
        "cancellation_effective_date": subscription.current_period_end.isoformat(),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/usage")
async def get_detailed_usage(
    period: str = Query("30d", regex="^(7d|30d|90d|1y)$"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    organization = get_current_organization(current_user, db)
    if not organization:
        raise HTTPException(status_code=404, detail="User not part of any organization")

    # Calculate time period
    period_map = {
        "7d": 7,
        "30d": 30,
        "90d": 90,
        "1y": 365
    }
    days = period_map[period]
    start_date = datetime.utcnow() - timedelta(days=days)

    # Get usage data
    tasks_count = db.query(Task).filter(
        Task.organization_id == organization.id,
        Task.created_at >= start_date
    ).count()

    workflows_count = db.query(Workflow).filter(
        Workflow.organization_id == organization.id,
        Workflow.created_at >= start_date
    ).count()

    agents_count = db.query(Agent).filter(
        Agent.organization_id == organization.id,
        Agent.created_at >= start_date
    ).count()

    active_agents = db.query(Agent).filter(
        Agent.organization_id == organization.id,
        Agent.is_active == True
    ).count()

    # Get detailed task statistics
    task_stats = db.query(
        db.func.date(Task.created_at).label('date'),
        db.func.count(Task.id).label('total'),
        db.func.sum(db.case([(Task.status == 'completed', 1)], else_=0)).label('completed'),
        db.func.sum(db.case([(Task.status == 'failed', 1)], else_=0)).label('failed'),
        db.func.sum(db.case([(Task.status == 'running', 1)], else_=0)).label('running')
    ).filter(
        Task.organization_id == organization.id,
        Task.created_at >= start_date
    ).group_by('date').all()

    task_breakdown = []
    for date, total, completed, failed, running in task_stats:
        task_breakdown.append({
            "date": date.isoformat() if hasattr(date, 'isoformat') else str(date),
            "total_tasks": total,
            "completed_tasks": completed,
            "failed_tasks": failed,
            "running_tasks": running,
            "success_rate": (completed / total * 100) if total > 0 else 0
        })

    # Get agent usage statistics
    agent_usage = db.query(
        Agent.id,
        Agent.name,
        db.func.count(Task.id).label('task_count'),
        db.func.avg(Task.execution_time).label('avg_execution_time')
    ).outerjoin(Task).filter(
        Agent.organization_id == organization.id,
        Task.created_at >= start_date
    ).group_by(Agent.id, Agent.name).all()\n
    agent_statistics = []
    for agent_id, name, task_count, avg_execution_time in agent_usage:
        agent_statistics.append({
            "agent_id": agent_id,
            "name": name,
            "tasks_executed": task_count or 0,
            "average_execution_time_seconds": avg_execution_time or 0
        })

    return {
        "organization_id": organization.id,
        "period": period,
        "start_date": start_date.isoformat(),
        "end_date": datetime.utcnow().isoformat(),
        "usage_summary": {
            "total_tasks": tasks_count,
            "total_workflows": workflows_count,
            "total_agents": agents_count,
            "active_agents": active_agents
        },
        "task_breakdown": task_breakdown,
        "agent_statistics": agent_statistics,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/invoices")
async def get_invoices(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    organization = get_current_organization(current_user, db)
    if not organization:
        raise HTTPException(status_code=404, detail="User not part of any organization")

    # Get invoices for organization
    invoices = db.query(Invoice).filter(
        Invoice.organization_id == organization.id
    ).order_by(Invoice.issue_date.desc()).all()

    invoice_data = []
    for invoice in invoices:
        invoice_data.append({
            "id": invoice.id,
            "number": invoice.number,
            "issue_date": invoice.issue_date.isoformat(),
            "due_date": invoice.due_date.isoformat(),
            "amount": invoice.amount,
            "currency": invoice.currency,
            "status": invoice.status,
            "period_start": invoice.period_start.isoformat(),
            "period_end": invoice.period_end.isoformat(),
            "pdf_url": invoice.pdf_url,
            "items": invoice.items
        })

    return {
        "organization_id": organization.id,
        "invoices": invoice_data,
        "total_invoices": len(invoices),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/payment-methods")
async def get_payment_methods(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    organization = get_current_organization(current_user, db)
    if not organization:
        raise HTTPException(status_code=404, detail="User not part of any organization")

    payment_methods = db.query(PaymentMethod).filter(
        PaymentMethod.organization_id == organization.id
    ).all()

    methods_data = []
    for method in payment_methods:
        methods_data.append({
            "id": method.id,
            "type": method.type,
            "last_four": method.last_four,
            "card_brand": method.card_brand,
            "expiration_month": method.expiration_month,
            "expiration_year": method.expiration_year,
            "is_default": method.is_default,
            "created_at": method.created_at.isoformat()
        })

    return {
        "organization_id": organization.id,
        "payment_methods": methods_data,
        "default_payment_method_id": next((m["id"] for m in methods_data if m["is_default"]), None),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/portal")
async def get_stripe_portal_url(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    organization = get_current_organization(current_user, db)
    if not organization:
        raise HTTPException(status_code=404, detail="User not part of any organization")

    # Get organization's Stripe customer ID
    stripe_customer_id = organization.stripe_customer_id
    if not stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No Stripe customer ID found for this organization"
        )

    # In a real implementation, you would create a Stripe session
    # For now, return a mock URL
    return {
        "organization_id": organization.id,
        "stripe_portal_url": f"https://billing.stripe.com/payments/{stripe_customer_id}",
        "stripe_customer_id": stripe_customer_id,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/invoices/pdf")
async def get_invoice_pdf(
    invoice_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    organization = get_current_organization(current_user, db)
    if not organization:
        raise HTTPException(status_code=404, detail="User not part of any organization")

    # Get invoice
    invoice = db.query(Invoice).filter(
        Invoice.organization_id == organization.id,
        Invoice.id == invoice_id
    ).first()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    return {
        "organization_id": organization.id,
        "invoice_id": invoice.id,
        "pdf_url": invoice.pdf_url,
        "download_url": f"/api/v1/billing/invoices/{invoice.id}/download",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/subscription/usage")
async def get_current_period_usage(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    organization = get_current_organization(current_user, db)
    if not organization:
        raise HTTPException(status_code=404, detail="User not part of any organization")

    # Get current subscription
    subscription = db.query(Subscription).filter(
        Subscription.organization_id == organization.id,
        Subscription.status == "active"
    ).first()

    if not subscription:
        return {
            "organization_id": organization.id,
            "status": "no_active_subscription",
            "usage": {
                "agents": 0,
                "workflows": 0,
                "tasks": 0,
                "tokens": 0,
                "api_calls": 0
            },
            "usage_percentage": {
                "agents": 0,
                "workflows": 0,
                "tasks": 0
            },
            "limits": {
                "agents": 0,
                "workflows": 0,
                "tasks": 0
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    # Get usage data
    usage_data = await get_detailed_usage("30d", current_user, db)

    # Get plan limits
    plan = db.query(BillingPlan).filter(BillingPlan.id == subscription.plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Billing plan not found")

    # Calculate usage percentages
    usage_percentage = {
        "agents": (usage_data["usage_summary"]["active_agents"] / plan.max_agents * 100) if plan.max_agents > 0 else 0,
        "workflows": (usage_data["usage_summary"]["total_workflows"] / plan.max_workflows * 100) if plan.max_workflows > 0 else 0,
        "tasks": (usage_data["usage_summary"]["total_tasks"] / plan.max_tasks_per_month * 100) if plan.max_tasks_per_month > 0 else 0
    }

    return {
        "organization_id": organization.id,
        "subscription_id": subscription.id,
        "plan_id": plan.id,
        "usage": {
            "agents": usage_data["usage_summary"]["active_agents"],
            "workflows": usage_data["usage_summary"]["total_workflows"],
            "tasks": usage_data["usage_summary"]["total_tasks"],
            "tokens": sum(task.tokens_used for task in db.query(Task).filter(
                Task.organization_id == organization.id,
                Task.created_at >= datetime.utcnow() - timedelta(days=30)
            ).all() if task.tokens_used is not None),
            "api_calls": len(db.query(Task).filter(
                Task.organization_id == organization.id,
                Task.created_at >= datetime.utcnow() - timedelta(days=30)
            ).all())
        },
        "usage_percentage": usage_percentage,
        "limits": {
            "agents": plan.max_agents,
            "workflows": plan.max_workflows,
            "tasks": plan.max_tasks_per_month
        },
        "near_limits": {
            "agents": usage_percentage["agents"] > 80,
            "workflows": usage_percentage["workflows"] > 80,
            "tasks": usage_percentage["tasks"] > 80
        },
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/subscription/upgrade")
async def upgrade_subscription(
    plan_id: int,
    payment_method_id: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    organization = get_current_organization(current_user, db)
    if not organization:
        raise HTTPException(status_code=404, detail="User not part of any organization")

    # Get the new plan
    new_plan = db.query(BillingPlan).filter(
        BillingPlan.id == plan_id,
        BillingPlan.is_active == True
    ).first()

    if not new_plan:
        raise HTTPException(status_code=404, detail="Billing plan not found")

    # Get current subscription
    current_subscription = db.query(Subscription).filter(
        Subscription.organization_id == organization.id,
        Subscription.status == "active"
    ).first()

    # Validate payment (simplified - in real implementation, integrate with payment processor)
    if not payment_method_id:
        # Check if payment method exists for organization
        payment_method = db.query(PaymentMethod).filter(
            PaymentMethod.organization_id == organization.id,
            PaymentMethod.is_default == True
        ).first()

        if not payment_method:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No payment method available. Please add a payment method first."
            )

    # Calculate prorated amount if upgrading (simplified)
    prorated_amount = 0  # In real implementation, calculate based on time remaining

    # Create new subscription
    new_subscription = Subscription(
        plan_id=new_plan.id,
        organization_id=organization.id,
        status="active",
        current_period_start=datetime.utcnow(),
        current_period_end=datetime.utcnow() + timedelta(days=30),  # 30-day billing cycle
        cancel_at_period_end=False
    )

    db.add(new_subscription)
    db.commit()

    # Cancel old subscription if exists
    if current_subscription:
        current_subscription.status = "cancelled"
        current_subscription.cancel_at_period_end = False
        db.commit()

    return {
        "message": "Subscription upgraded successfully",
        "new_plan": {
            "id": new_plan.id,
            "name": new_plan.name,
            "price": new_plan.price,
            "currency": new_plan.currency
        },
        "prorated_amount": prorated_amount,
        "next_billing_date": new_subscription.current_period_end.isoformat(),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/subscription/downgrade")
async def downgrade_subscription(
    plan_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    organization = get_current_organization(current_user, db)
    if not organization:
        raise HTTPException(status_code=404, detail="User not part of any organization")

    # Get the new plan
    new_plan = db.query(BillingPlan).filter(
        BillingPlan.id == plan_id,
        BillingPlan.is_active == True
    ).first()

    if not new_plan:
        raise HTTPException(status_code=404, detail="Billing plan not found")

    # Check if current usage exceeds new plan limits
    current_usage = await get_current_period_usage(current_user, db)
    if (current_usage["usage"]["agents"] > new_plan.max_agents or
        current_usage["usage"]["workflows"] > new_plan.max_workflows or
        current_usage["usage"]["tasks"] > new_plan.max_tasks_per_month):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current usage exceeds limits of the new plan. Please reduce usage before downgrading."
        )

    # Get current subscription
    current_subscription = db.query(Subscription).filter(
        Subscription.organization_id == organization.id,
        Subscription.status == "active"
    ).first()

    # Create new subscription
    new_subscription = Subscription(
        plan_id=new_plan.id,
        organization_id=organization.id,
        status="active",
        current_period_start=datetime.utcnow(),
        current_period_end=datetime.utcnow() + timedelta(days=30),  # 30-day billing cycle
        cancel_at_period_end=False
    )

    db.add(new_subscription)
    db.commit()

    # Cancel old subscription
    if current_subscription:
        current_subscription.status = "cancelled"
        current_subscription.cancel_at_period_end = False
        db.commit()

    return {
        "message": "Subscription downgraded successfully",
        "new_plan": {
            "id": new_plan.id,
            "name": new_plan.name,
            "price": new_plan.price,
            "currency": new_plan.currency
        },
        "timestamp": datetime.utcnow().isoformat()
    }