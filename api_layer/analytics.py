from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import datetime
from sqlalchemy import func, extract, case

from ..shared.database import get_db
from ..shared.security import get_current_active_user, get_current_active_superuser, get_current_organization_member
from ..shared.models import User, Organization, Agent, Workflow, Task, UsageMetric
from ..shared.schemas import (
    AnalyticsQuery, AnalyticsResponse, UsageMetric,
    Pagination, PaginatedResponse
)
from ..shared.utils import (
    paginate_query, create_paginated_response,
    filter_by_organization, get_user_organizations
)

router = APIRouter()


@router.get("/usage", response_model=AnalyticsResponse)
def get_usage_metrics(
    query: AnalyticsQuery,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get usage metrics for the platform."""

    # Build base query
    query_base = db.query(
        UsageMetric.metric_type,
        UsageMetric.value,
        UsageMetric.unit,
        UsageMetric.timestamp,
        UsageMetric.organization_id,
        UsageMetric.agent_id,
        UsageMetric.task_id
    )

    # Filter by organization if specified
    if query.organization_id:
        org_query = db.query(Organization).filter(Organization.id == query.organization_id)
        org_query = filter_by_organization(db, org_query, query.organization_id, current_user)
        organization = org_query.first()
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found or access denied"
            )

        query_base = query_base.filter(UsageMetric.organization_id == query.organization_id)
    else:
        # Get metrics for all organizations the user belongs to
        user_organizations = get_user_organizations(db, current_user.id)
        organization_ids = [org.id for org in user_organizations]
        query_base = query_base.filter(UsageMetric.organization_id.in_(organization_ids))

    # Filter by metric type
    if query.metric:
        query_base = query_base.filter(UsageMetric.metric_type == query.metric)

    # Filter by time range
    start_date, end_date = get_time_range(query)
    if start_date and end_date:
        query_base = query_base.filter(UsageMetric.timestamp.between(start_date, end_date))

    # Apply grouping
    if query.group_by == "day":
        grouped_query = query_base.with_entities(
            func.date(UsageMetric.timestamp).label('date'),
            func.sum(UsageMetric.value).label('total_value'),
            UsageMetric.unit,
            UsageMetric.metric_type
        ).group_by(
            func.date(UsageMetric.timestamp),
            UsageMetric.unit,
            UsageMetric.metric_type
        ).order_by(func.date(UsageMetric.timestamp))
    elif query.group_by == "week":
        grouped_query = query_base.with_entities(
            func.date_trunc('week', UsageMetric.timestamp).label('week'),
            func.sum(UsageMetric.value).label('total_value'),
            UsageMetric.unit,
            UsageMetric.metric_type
        ).group_by(
            func.date_trunc('week', UsageMetric.timestamp),
            UsageMetric.unit,
            UsageMetric.metric_type
        ).order_by(func.date_trunc('week', UsageMetric.timestamp))
    elif query.group_by == "month":
        grouped_query = query_base.with_entities(
            func.date_trunc('month', UsageMetric.timestamp).label('month'),
            func.sum(UsageMetric.value).label('total_value'),
            UsageMetric.unit,
            UsageMetric.metric_type
        ).group_by(
            func.date_trunc('month', UsageMetric.timestamp),
            UsageMetric.unit,
            UsageMetric.metric_type
        ).order_by(func.date_trunc('month', UsageMetric.timestamp))
    elif query.group_by == "agent":
        grouped_query = query_base.with_entities(
            UsageMetric.agent_id,
            func.sum(UsageMetric.value).label('total_value'),
            UsageMetric.unit,
            UsageMetric.metric_type
        ).group_by(
            UsageMetric.agent_id,
            UsageMetric.unit,
            UsageMetric.metric_type
        ).order_by(func.sum(UsageMetric.value).desc())
    elif query.group_by == "organization":
        grouped_query = query_base.with_entities(
            UsageMetric.organization_id,
            func.sum(UsageMetric.value).label('total_value'),
            UsageMetric.unit,
            UsageMetric.metric_type
        ).group_by(
            UsageMetric.organization_id,
            UsageMetric.unit,
            UsageMetric.metric_type
        ).order_by(func.sum(UsageMetric.value).desc())
    else:
        # No grouping - return raw metrics
        grouped_query = query_base

    # Execute query
    results = grouped_query.all()

    # Format results
    data = []
    for row in results:
        data.append({
            "timestamp": row.date.isoformat() if hasattr(row, 'date') else row.week.isoformat() if hasattr(row, 'week') else row.month.isoformat() if hasattr(row, 'month') else None,
            "value": float(row.total_value) if hasattr(row, 'total_value') else float(row.value),
            "unit": row.unit,
            "metric_type": row.metric_type,
            "agent_id": row.agent_id if hasattr(row, 'agent_id') else None,
            "organization_id": row.organization_id if hasattr(row, 'organization_id') else None
        })

    # Calculate summary
    summary = calculate_summary(data, query.metric)

    return AnalyticsResponse(
        metric=query.metric,
        data=data,
        summary=summary
    )


@router.get("/performance", response_model=AnalyticsResponse)
def get_performance_metrics(
    query: AnalyticsQuery,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get performance metrics for the platform."""

    # Get task statistics
    task_query = db.query(
        Task.status,
        func.count(Task.id).label('count'),
        func.avg(Task.execution_time).label('avg_execution_time'),
        func.min(Task.execution_time).label('min_execution_time'),
        func.max(Task.execution_time).label('max_execution_time')
    )

    # Filter by organization
    if query.organization_id:
        org_query = db.query(Organization).filter(Organization.id == query.organization_id)
        org_query = filter_by_organization(db, org_query, query.organization_id, current_user)
        organization = org_query.first()
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found or access denied"
            )

        task_query = task_query.filter(Task.organization_id == query.organization_id)
    else:
        user_organizations = get_user_organizations(db, current_user.id)
        organization_ids = [org.id for org in user_organizations]
        task_query = task_query.filter(Task.organization_id.in_(organization_ids))

    # Filter by time range
    start_date, end_date = get_time_range(query)
    if start_date and end_date:
        task_query = task_query.filter(Task.created_at.between(start_date, end_date))

    task_query = task_query.group_by(Task.status)

    results = task_query.all()

    data = []
    for row in results:
        data.append({
            "status": row.status,
            "count": int(row.count),
            "average_execution_time": float(row.avg_execution_time) if row.avg_execution_time else 0,
            "min_execution_time": float(row.min_execution_time) if row.min_execution_time else 0,
            "max_execution_time": float(row.max_execution_time) if row.max_execution_time else 0
        })

    # Calculate success rate and other metrics
    total_tasks = sum(item['count'] for item in data)
    completed_tasks = next((item['count'] for item in data if item['status'] == 'completed'), 0)
    failed_tasks = next((item['count'] for item in data if item['status'] == 'failed'), 0)

    summary = {
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "failed_tasks": failed_tasks,
        "success_rate": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
        "average_execution_time": sum(item['count'] * item['average_execution_time'] for item in data if item['average_execution_time'] > 0) / total_tasks if total_tasks > 0 else 0
    }

    return AnalyticsResponse(
        metric="performance",
        data=data,
        summary=summary
    )


@router.get("/costs", response_model=AnalyticsResponse)
def get_cost_metrics(
    query: AnalyticsQuery,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get cost metrics for the platform."""

    # Get usage metrics related to costs
    cost_query = db.query(
        UsageMetric.metric_type,
        UsageMetric.value,
        UsageMetric.unit,
        UsageMetric.timestamp,
        UsageMetric.organization_id,
        UsageMetric.agent_id
    )

    # Filter by organization
    if query.organization_id:
        org_query = db.query(Organization).filter(Organization.id == query.organization_id)
        org_query = filter_by_organization(db, org_query, query.organization_id, current_user)
        organization = org_query.first()
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found or access denied"
            )

        cost_query = cost_query.filter(UsageMetric.organization_id == query.organization_id)
    else:
        user_organizations = get_user_organizations(db, current_user.id)
        organization_ids = [org.id for org in user_organizations]
        cost_query = cost_query.filter(UsageMetric.organization_id.in_(organization_ids))

    # Filter by cost-related metrics
    cost_metrics = ['token_usage', 'execution_cost', 'api_calls']
    if query.metric:
        if query.metric in cost_metrics:
            cost_query = cost_query.filter(UsageMetric.metric_type == query.metric)
        else:
            cost_query = cost_query.filter(UsageMetric.metric_type.in_(cost_metrics))
    else:
        cost_query = cost_query.filter(UsageMetric.metric_type.in_(cost_metrics))

    # Filter by time range
    start_date, end_date = get_time_range(query)
    if start_date and end_date:
        cost_query = cost_query.filter(UsageMetric.timestamp.between(start_date, end_date))

    # Group by day for cost analysis
    grouped_query = cost_query.with_entities(
        func.date(UsageMetric.timestamp).label('date'),
        func.sum(UsageMetric.value).label('total_value'),
        UsageMetric.unit,
        UsageMetric.metric_type
    ).group_by(
        func.date(UsageMetric.timestamp),
        UsageMetric.unit,
        UsageMetric.metric_type
    ).order_by(func.date(UsageMetric.timestamp))

    results = grouped_query.all()

    data = []
    for row in results:
        data.append({
            "date": row.date.isoformat(),
            "value": float(row.total_value),
            "unit": row.unit,
            "metric_type": row.metric_type
        })

    # Calculate cost summary
    total_cost = sum(item['value'] for item in data if item['metric_type'] in ['execution_cost', 'token_usage'])
    api_calls = sum(item['value'] for item in data if item['metric_type'] == 'api_calls')

    summary = {
        "total_cost": total_cost,
        "api_calls": api_calls,
        "cost_per_api_call": (total_cost / api_calls) if api_calls > 0 else 0,
        "daily_average_cost": (total_cost / len(set(item['date'] for item in data))) if data else 0
    }

    return AnalyticsResponse(
        metric="costs",
        data=data,
        summary=summary
    )


@router.get("/agents", response_model=AnalyticsResponse)
def get_agent_metrics(
    query: AnalyticsQuery,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get agent-specific metrics."""

    # Get agent usage statistics
    agent_query = db.query(
        Agent.id,
        Agent.name,
        Agent.type,
        Agent.model,
        func.count(Task.id).label('task_count'),
        func.avg(Task.execution_time).label('avg_execution_time'),
        func.sum(Task.execution_time).label('total_execution_time')
    )

    # Filter by organization
    if query.organization_id:
        org_query = db.query(Organization).filter(Organization.id == query.organization_id)
        org_query = filter_by_organization(db, org_query, query.organization_id, current_user)
        organization = org_query.first()
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found or access denied"
            )

        agent_query = agent_query.filter(Agent.organization_id == query.organization_id)
    else:
        user_organizations = get_user_organizations(db, current_user.id)
        organization_ids = [org.id for org in user_organizations]
        agent_query = agent_query.filter(Agent.organization_id.in_(organization_ids))

    # Join with tasks
    agent_query = agent_query.join(Task, Agent.id == Task.agent_id)

    # Filter by time range
    start_date, end_date = get_time_range(query)
    if start_date and end_date:
        agent_query = agent_query.filter(Task.created_at.between(start_date, end_date))

    agent_query = agent_query.group_by(Agent.id, Agent.name, Agent.type, Agent.model)

    results = agent_query.all()

    data = []
    for row in results:
        data.append({
            "agent_id": row.id,
            "name": row.name,
            "type": row.type,
            "model": row.model,
            "task_count": int(row.task_count),
            "average_execution_time": float(row.avg_execution_time) if row.avg_execution_time else 0,
            "total_execution_time": float(row.total_execution_time) if row.total_execution_time else 0
        })

    # Calculate summary
    total_tasks = sum(item['task_count'] for item in data)
    total_execution_time = sum(item['total_execution_time'] for item in data)

    summary = {
        "total_agents": len(data),
        "total_tasks": total_tasks,
        "total_execution_time": total_execution_time,
        "average_tasks_per_agent": (total_tasks / len(data)) if data else 0,
        "most_active_agent": max(data, key=lambda x: x['task_count']) if data else None
    }

    return AnalyticsResponse(
        metric="agents",
        data=data,
        summary=summary
    )


@router.get("/workflows", response_model=AnalyticsResponse)
def get_workflow_metrics(
    query: AnalyticsQuery,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get workflow-specific metrics."""

    # Get workflow usage statistics
    workflow_query = db.query(
        Workflow.id,
        Workflow.name,
        Workflow.status,
        func.count(Task.id).label('task_count'),
        func.avg(Task.execution_time).label('avg_execution_time'),
        func.sum(Task.execution_time).label('total_execution_time')
    )

    # Filter by organization
    if query.organization_id:
        org_query = db.query(Organization).filter(Organization.id == query.organization_id)
        org_query = filter_by_organization(db, org_query, query.organization_id, current_user)
        organization = org_query.first()
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found or access denied"
            )

        workflow_query = workflow_query.filter(Workflow.organization_id == query.organization_id)
    else:
        user_organizations = get_user_organizations(db, current_user.id)
        organization_ids = [org.id for org in user_organizations]
        workflow_query = workflow_query.filter(Workflow.organization_id.in_(organization_ids))

    # Join with tasks
    workflow_query = workflow_query.join(Task, Workflow.id == Task.workflow_id)

    # Filter by time range
    start_date, end_date = get_time_range(query)
    if start_date and end_date:
        workflow_query = workflow_query.filter(Task.created_at.between(start_date, end_date))

    workflow_query = workflow_query.group_by(Workflow.id, Workflow.name, Workflow.status)

    results = workflow_query.all()

    data = []
    for row in results:
        data.append({
            "workflow_id": row.id,
            "name": row.name,
            "status": row.status,
            "task_count": int(row.task_count),
            "average_execution_time": float(row.avg_execution_time) if row.avg_execution_time else 0,
            "total_execution_time": float(row.total_execution_time) if row.total_execution_time else 0
        })

    # Calculate summary
    total_workflows = len(data)
    total_tasks = sum(item['task_count'] for item in data)
    total_execution_time = sum(item['total_execution_time'] for item in data)

    summary = {
        "total_workflows": total_workflows,
        "total_tasks": total_tasks,
        "total_execution_time": total_execution_time,
        "active_workflows": len([item for item in data if item['status'] == 'active']),
        "average_tasks_per_workflow": (total_tasks / total_workflows) if total_workflows > 0 else 0
    }

    return AnalyticsResponse(
        metric="workflows",
        data=data,
        summary=summary
    )


@router.get("/reports", response_model=List[Dict[str, Any]])
def get_reports(
    query: AnalyticsQuery,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Generate comprehensive reports."""

    reports = []

    # Daily usage report
    if query.metric == "daily_usage" or not query.metric:
        daily_query = db.query(
            func.date(Task.created_at).label('date'),
            func.count(Task.id).label('task_count'),
            func.avg(Task.execution_time).label('avg_execution_time'),
            func.sum(Task.execution_time).label('total_execution_time')
        )

        # Filter by organization
        if query.organization_id:
            org_query = db.query(Organization).filter(Organization.id == query.organization_id)
            org_query = filter_by_organization(db, org_query, query.organization_id, current_user)
            organization = org_query.first()
            if not organization:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Organization not found or access denied"
                )

            daily_query = daily_query.filter(Task.organization_id == query.organization_id)
        else:
            user_organizations = get_user_organizations(db, current_user.id)
            organization_ids = [org.id for org in user_organizations]
            daily_query = daily_query.filter(Task.organization_id.in_(organization_ids))

        # Filter by time range
        start_date, end_date = get_time_range(query)
        if start_date and end_date:
            daily_query = daily_query.filter(Task.created_at.between(start_date, end_date))

        daily_query = daily_query.group_by(func.date(Task.created_at))
        daily_query = daily_query.order_by(func.date(Task.created_at))

        daily_results = daily_query.all()

        daily_report = {
            "report_type": "daily_usage",
            "title": "Daily Usage Report",
            "data": [],
            "summary": {}
        }

        for row in daily_results:
            daily_report["data"].append({
                "date": row.date.isoformat(),
                "task_count": int(row.task_count),
                "average_execution_time": float(row.avg_execution_time) if row.avg_execution_time else 0,
                "total_execution_time": float(row.total_execution_time) if row.total_execution_time else 0
            })

        if daily_results:
            total_tasks = sum(row.task_count for row in daily_results)
            total_days = len(daily_results)
            daily_report["summary"] = {
                "total_tasks": total_tasks,
                "average_tasks_per_day": total_tasks / total_days,
                "total_execution_time": sum(row.total_execution_time for row in daily_results),
                "average_execution_time": sum(row.total_execution_time for row in daily_results) / total_days
            }

        reports.append(daily_report)

    # Agent performance report
    if query.metric == "agent_performance" or not query.metric:
        agent_report = {
            "report_type": "agent_performance",
            "title": "Agent Performance Report",
            "data": [],
            "summary": {}
        }

        # Get agent statistics
        agent_stats_query = db.query(
            Agent.id,
            Agent.name,
            Agent.type,
            Agent.model,
            func.count(Task.id).label('task_count'),
            func.avg(Task.execution_time).label('avg_execution_time'),
            func.sum(Task.execution_time).label('total_execution_time'),
            func.sum(case([(Task.status == 'failed', 1)], else_=0)).label('failed_count')
        ).join(Task, Agent.id == Task.agent_id)

        # Filter by organization
        if query.organization_id:
            agent_stats_query = agent_stats_query.filter(Agent.organization_id == query.organization_id)
        else:
            user_organizations = get_user_organizations(db, current_user.id)
            organization_ids = [org.id for org in user_organizations]
            agent_stats_query = agent_stats_query.filter(Agent.organization_id.in_(organization_ids))

        # Filter by time range
        if start_date and end_date:
            agent_stats_query = agent_stats_query.filter(Task.created_at.between(start_date, end_date))

        agent_stats_query = agent_stats_query.group_by(Agent.id, Agent.name, Agent.type, Agent.model)
        agent_stats_query = agent_stats_query.order_by(func.count(Task.id).desc())

        agent_results = agent_stats_query.all()

        for row in agent_results:
            success_rate = ((row.task_count - row.failed_count) / row.task_count * 100) if row.task_count > 0 else 0
            agent_report["data"].append({
                "agent_id": row.id,
                "name": row.name,
                "type": row.type,
                "model": row.model,
                "task_count": int(row.task_count),
                "success_rate": success_rate,
                "average_execution_time": float(row.avg_execution_time) if row.avg_execution_time else 0,
                "total_execution_time": float(row.total_execution_time) if row.total_execution_time else 0,
                "failed_count": int(row.failed_count)
            })

        if agent_results:
            total_tasks = sum(row.task_count for row in agent_results)
            total_agents = len(agent_results)
            agent_report["summary"] = {
                "total_agents": total_agents,
                "total_tasks": total_tasks,
                "average_tasks_per_agent": total_tasks / total_agents,
                "average_success_rate": sum(
                    ((row.task_count - row.failed_count) / row.task_count * 100) for row in agent_results if row.task_count > 0
                ) / total_agents if total_agents > 0 else 0
            }

        reports.append(agent_report)

    return reports


@router.get("/export", response_model=List[Dict[str, Any]])
def export_analytics(
    query: AnalyticsQuery,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Export analytics data."""

    # Get all relevant data based on query
    data = []

    # Get task data
    task_query = db.query(Task)

    # Filter by organization
    if query.organization_id:
        org_query = db.query(Organization).filter(Organization.id == query.organization_id)
        org_query = filter_by_organization(db, org_query, query.organization_id, current_user)
        organization = org_query.first()
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found or access denied"
            )

        task_query = task_query.filter(Task.organization_id == query.organization_id)
    else:
        user_organizations = get_user_organizations(db, current_user.id)
        organization_ids = [org.id for org in user_organizations]
        task_query = task_query.filter(Task.organization_id.in_(organization_ids))

    # Filter by time range
    start_date, end_date = get_time_range(query)
    if start_date and end_date:
        task_query = task_query.filter(Task.created_at.between(start_date, end_date))

    tasks = task_query.all()

    for task in tasks:
        data.append({
            "task_id": task.id,
            "name": task.name,
            "status": task.status,
            "execution_time": float(task.execution_time) if task.execution_time else 0,
            "created_at": task.created_at.isoformat(),
            "organization_id": task.organization_id,
            "workflow_id": task.workflow_id,
            "creator_id": task.creator_id
        })

    return data


def get_time_range(query: AnalyticsQuery):
    """Get start and end dates from query."""

    start_date = None
    end_date = None

    if query.time_range:
        now = datetime.datetime.now()
        if query.time_range == "last_7d":
            start_date = now - datetime.timedelta(days=7)
            end_date = now
        elif query.time_range == "last_30d":
            start_date = now - datetime.timedelta(days=30)
            end_date = now
        elif query.time_range == "last_90d":
            start_date = now - datetime.timedelta(days=90)
            end_date = now
        elif query.time_range == "last_365d":
            start_date = now - datetime.timedelta(days=365)
            end_date = now
    else:
        start_date = query.start_date
        end_date = query.end_date

    return start_date, end_date


def calculate_summary(data: List[Dict[str, Any]], metric: str) -> Dict[str, Any]:
    """Calculate summary statistics for given data."""

    summary = {}

    if not data:
        return summary

    if metric in ["token_usage", "execution_time", "api_calls", "execution_cost"]:
        total_value = sum(item["value"] for item in data)
        average_value = total_value / len(data) if data else 0
        max_value = max(item["value"] for item in data)
        min_value = min(item["value"] for item in data)

        summary = {
            "total": total_value,
            "average": average_value,
            "max": max_value,
            "min": min_value,
            "count": len(data)
        }

    return summary