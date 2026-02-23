from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import statistics

from api.schemas import (
    ErrorResponse, PaginationResponse, SortOrder, Filter
)
from core.database import get_db
from core.auth import get_current_user, get_current_active_user, get_current_organization

router = APIRouter()


@router.get("/usage")
async def get_usage_analytics(
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

    completed_tasks = db.query(Task).filter(
        Task.organization_id == organization.id,
        Task.status == "completed",
        Task.created_at >= start_date
    ).count()

    failed_tasks = db.query(Task).filter(
        Task.organization_id == organization.id,
        Task.status == "failed",
        Task.created_at >= start_date
    ).count()

    # Get execution time data
    execution_times = db.query(Task.execution_time).filter(
        Task.organization_id == organization.id,
        Task.status == "completed",
        Task.execution_time != None,
        Task.created_at >= start_date
    ).all()

    execution_times = [et[0] for et in execution_times if et[0] is not None]
    avg_execution_time = statistics.mean(execution_times) if execution_times else 0
    median_execution_time = statistics.median(execution_times) if execution_times else 0

    # Get task creation trends
    from collections import defaultdict
    tasks_by_day = defaultdict(int)
    task_creation_data = db.query(
        Task.created_at,
        Task.status
    ).filter(
        Task.organization_id == organization.id,
        Task.created_at >= start_date
    ).all()

    for task in task_creation_data:
        task_date = task[0].date()
        tasks_by_day[task_date] += 1

    # Convert to list of dicts for JSON serialization
    task_creation_trends = [
        {"date": str(date), "tasks": count}
        for date, count in sorted(tasks_by_day.items())
    ]

    return {
        "organization_id": organization.id,
        "period": period,
        "start_date": start_date.isoformat(),
        "end_date": datetime.utcnow().isoformat(),
        "tasks": {
            "total": tasks_count,
            "completed": completed_tasks,
            "failed": failed_tasks,
            "success_rate": (completed_tasks / tasks_count * 100) if tasks_count > 0 else 0,
            "creation_trends": task_creation_trends
        },
        "workflows": {
            "total": workflows_count
        },
        "agents": {
            "total": agents_count,
            "active": active_agents
        },
        "performance": {
            "average_execution_time_seconds": avg_execution_time,
            "median_execution_time_seconds": median_execution_time
        }
    }


@router.get("/performance")
async def get_performance_analytics(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    organization = get_current_organization(current_user, db)
    if not organization:
        raise HTTPException(status_code=404, detail="User not part of any organization")

    # Get performance metrics for the last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)

    # Task performance metrics
    task_metrics = db.query(
        Task.status,
        db.func.count(Task.id).label('count'),
        db.func.avg(Task.execution_time).label('avg_time'),
        db.func.min(Task.execution_time).label('min_time'),
        db.func.max(Task.execution_time).label('max_time')
    ).filter(
        Task.organization_id == organization.id,
        Task.created_at >= thirty_days_ago
    ).group_by(Task.status).all()

    task_performance = {}
    for status, count, avg_time, min_time, max_time in task_metrics:
        task_performance[status] = {
            "count": count,
            "average_execution_time": avg_time or 0,
            "min_execution_time": min_time or 0,
            "max_execution_time": max_time or 0
        }

    # Agent performance metrics
    agent_metrics = db.query(
        Agent.id,
        Agent.name,
        Agent.agent_type,
        db.func.count(Task.id).label('task_count'),
        db.func.avg(Task.execution_time).label('avg_time')
    ).outerjoin(Task).filter(
        Agent.organization_id == organization.id,
        Task.created_at >= thirty_days_ago
    ).group_by(Agent.id, Agent.name, Agent.agent_type).all()

    agent_performance = []
    for agent_id, name, agent_type, task_count, avg_time in agent_metrics:
        agent_performance.append({
            "agent_id": agent_id,
            "name": name,
            "agent_type": agent_type,
            "tasks_executed": task_count or 0,
            "average_execution_time": avg_time or 0
        })

    # Workflow performance metrics
    workflow_metrics = db.query(
        Workflow.id,
        Workflow.name,
        db.func.count(Task.id).label('task_count'),
        db.func.avg(Task.execution_time).label('avg_time')
    ).outerjoin(Task).filter(
        Workflow.organization_id == organization.id,
        Task.created_at >= thirty_days_ago
    ).group_by(Workflow.id, Workflow.name).all()

    workflow_performance = []
    for workflow_id, name, task_count, avg_time in workflow_metrics:
        workflow_performance.append({
            "workflow_id": workflow_id,
            "name": name,
            "tasks_executed": task_count or 0,
            "average_execution_time": avg_time or 0
        })

    return {
        "organization_id": organization.id,
        "task_performance": task_performance,
        "agent_performance": agent_performance,
        "workflow_performance": workflow_performance,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/costs")
async def get_cost_analytics(
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

    # Get cost data
    tasks = db.query(Task).filter(
        Task.organization_id == organization.id,
        Task.created_at >= start_date
    ).all()

    total_cost = sum(task.cost_usd for task in tasks if task.cost_usd is not None)
    token_cost = sum(task.tokens_used * 0.00002 for task in tasks if task.tokens_used is not None)  # $0.00002 per token
    api_call_cost = len(tasks) * 0.0001  # $0.0001 per API call

    # Get cost breakdown by agent
    agent_cost_breakdown = db.query(
        Agent.id,
        Agent.name,
        db.func.sum(Task.cost_usd).label('total_cost'),
        db.func.count(Task.id).label('task_count')
    ).outerjoin(Task).filter(
        Agent.organization_id == organization.id,
        Task.created_at >= start_date
    ).group_by(Agent.id, Agent.name).all()

    agent_costs = []
    for agent_id, name, total_cost, task_count in agent_cost_breakdown:
        agent_costs.append({
            "agent_id": agent_id,
            "name": name,
            "total_cost": total_cost or 0,
            "task_count": task_count or 0,
            "average_cost_per_task": (total_cost / task_count) if task_count > 0 else 0
        })

    # Get cost breakdown by workflow
    workflow_cost_breakdown = db.query(
        Workflow.id,
        Workflow.name,
        db.func.sum(Task.cost_usd).label('total_cost'),
        db.func.count(Task.id).label('task_count')
    ).outerjoin(Task).filter(
        Workflow.organization_id == organization.id,
        Task.created_at >= start_date
    ).group_by(Workflow.id, Workflow.name).all()

    workflow_costs = []
    for workflow_id, name, total_cost, task_count in workflow_cost_breakdown:
        workflow_costs.append({
            "workflow_id": workflow_id,
            "name": name,
            "total_cost": total_cost or 0,
            "task_count": task_count or 0,
            "average_cost_per_task": (total_cost / task_count) if task_count > 0 else 0
        })

    return {
        "organization_id": organization.id,
        "period": period,
        "start_date": start_date.isoformat(),
        "end_date": datetime.utcnow().isoformat(),
        "cost_summary": {
            "total_cost": total_cost,
            "token_cost": token_cost,
            "api_call_cost": api_call_cost,
            "total_tasks": len(tasks)
        },
        "cost_breakdown": {
            "by_agent": agent_costs,
            "by_workflow": workflow_costs
        },
        "cost_trends": {
            "daily_average": total_cost / days if days > 0 else 0,
            "monthly_projection": total_cost * (30 / days) if days > 0 else 0
        },
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/agents")
async def get_agent_analytics(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    organization = get_current_organization(current_user, db)
    if not organization:
        raise HTTPException(status_code=404, detail="User not part of any organization")

    # Get agent analytics
    agents = db.query(Agent).filter(Agent.organization_id == organization.id).all()

    agent_stats = []
    for agent in agents:
        # Get task statistics for each agent
        tasks = db.query(Task).filter(
            Task.agent_id == agent.id,
            Task.created_at >= datetime.utcnow() - timedelta(days=30)
        ).all()

        task_count = len(tasks)
        completed_tasks = sum(1 for t in tasks if t.status == "completed")
        failed_tasks = sum(1 for t in tasks if t.status == "failed")
        avg_execution_time = statistics.mean([t.execution_time for t in tasks if t.execution_time]) if tasks else 0

        agent_stats.append({
            "agent_id": agent.id,
            "name": agent.name,
            "agent_type": agent.agent_type,
            "model": agent.model,
            "tasks_executed_last_30_days": task_count,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "success_rate": (completed_tasks / task_count * 100) if task_count > 0 else 0,
            "average_execution_time_seconds": avg_execution_time,
            "is_active": agent.is_active
        })

    # Sort by tasks executed
    agent_stats.sort(key=lambda x: x["tasks_executed_last_30_days"], reverse=True)

    return {
        "organization_id": organization.id,
        "total_agents": len(agents),
        "active_agents": sum(1 for a in agents if a.is_active),
        "agent_statistics": agent_stats,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/workflows")
async def get_workflow_analytics(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    organization = get_current_organization(current_user, db)
    if not organization:
        raise HTTPException(status_code=404, detail="User not part of any organization")

    # Get workflow analytics
    workflows = db.query(Workflow).filter(Workflow.organization_id == organization.id).all()

    workflow_stats = []
    for workflow in workflows:
        # Get task statistics for each workflow
        tasks = db.query(Task).filter(
            Task.workflow_id == workflow.id,
            Task.created_at >= datetime.utcnow() - timedelta(days=30)
        ).all()

        task_count = len(tasks)
        completed_tasks = sum(1 for t in tasks if t.status == "completed")
        failed_tasks = sum(1 for t in tasks if t.status == "failed")
        avg_execution_time = statistics.mean([t.execution_time for t in tasks if t.execution_time]) if tasks else 0

        workflow_stats.append({
            "workflow_id": workflow.id,
            "name": workflow.name,
            "triggers": workflow.triggers,
            "steps_count": len(workflow.steps),
            "tasks_executed_last_30_days": task_count,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "success_rate": (completed_tasks / task_count * 100) if task_count > 0 else 0,
            "average_execution_time_seconds": avg_execution_time,
            "is_active": workflow.is_active
        })

    # Sort by tasks executed
    workflow_stats.sort(key=lambda x: x["tasks_executed_last_30_days"], reverse=True)

    return {
        "organization_id": organization.id,
        "total_workflows": len(workflows),
        "active_workflows": sum(1 for w in workflows if w.is_active),
        "workflow_statistics": workflow_stats,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/alerts")
async def get_alerts(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    organization = get_current_organization(current_user, db)
    if not organization:
        raise HTTPException(status_code=404, detail="User not part of any organization")

    # Get alerts based on analytics
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)

    alerts = []

    # Check for high failure rate
    tasks = db.query(Task).filter(
        Task.organization_id == organization.id,
        Task.created_at >= thirty_days_ago
    ).all()

    if tasks:
        completed_tasks = sum(1 for t in tasks if t.status == "completed")
        failed_tasks = sum(1 for t in tasks if t.status == "failed")
        total_tasks = len(tasks)

        failure_rate = failed_tasks / total_tasks
        if failure_rate > 0.2:  # More than 20% failure rate
            alerts.append({
                "severity": "high",
                "type": "failure_rate",
                "message": f"High failure rate detected: {failure_rate*100:.1f}% of tasks are failing",
                "details": {
                    "total_tasks": total_tasks,
                    "failed_tasks": failed_tasks,
                    "failure_rate": failure_rate
                }
            })

    # Check for slow execution times
    slow_tasks = db.query(Task).filter(
        Task.organization_id == organization.id,
        Task.execution_time != None,
        Task.execution_time > 30,  # More than 30 seconds
        Task.created_at >= thirty_days_ago
    ).count()

    if slow_tasks > 10:  # More than 10 slow tasks
        alerts.append({
            "severity": "medium",
            "type": "slow_tasks",
            "message": f"Multiple slow tasks detected: {slow_tasks} tasks took more than 30 seconds",
            "details": {
                "slow_tasks_count": slow_tasks
            }
        })

    # Check for inactive agents
    inactive_agents = db.query(Agent).filter(
        Agent.organization_id == organization.id,
        Agent.is_active == True,
        ~db.exists().where(Task.agent_id == Agent.id)
    ).count()

    if inactive_agents > 0:
        alerts.append({
            "severity": "low",
            "type": "inactive_agents",
            "message": f"{inactive_agents} active agents have not executed any tasks recently",
            "details": {
                "inactive_agents_count": inactive_agents
            }
        })

    return {
        "organization_id": organization.id,
        "alerts": alerts,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/export")
async def export_analytics(
    format: str = Query("json", regex="^(json|csv|xml)$"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    organization = get_current_organization(current_user, db)
    if not organization:
        raise HTTPException(status_code=404, detail="User not part of any organization")

    # Get comprehensive analytics data
    usage_data = await get_usage_analytics(current_user, db)
    performance_data = await get_performance_analytics(current_user, db)
    agent_data = await get_agent_analytics(current_user, db)
    workflow_data = await get_workflow_analytics(current_user, db)

    # Prepare export data
    export_data = {
        "organization_id": organization.id,
        "timestamp": datetime.utcnow().isoformat(),
        "usage": usage_data,
        "performance": performance_data,
        "agents": agent_data,
        "workflows": workflow_data
    }

    if format == "json":
        return export_data
    elif format == "csv":
        # Convert to CSV format
        import csv
        from io import StringIO
        output = StringIO()
        writer = csv.writer(output)

        # Write headers
        writer.writerow(["Metric", "Value"])

        # Write usage data
        writer.writerow(["Total Tasks", usage_data["tasks"]["total"]])
        writer.writerow(["Completed Tasks", usage_data["tasks"]["completed"]])
        writer.writerow(["Failed Tasks", usage_data["tasks"]["failed"]])
        writer.writerow(["Success Rate", f"{usage_data["tasks"]["success_rate"]:.1f}%"])

        # Write performance data
        writer.writerow([])  # Empty row
        writer.writerow(["Average Execution Time (s)", usage_data["performance"]["average_execution_time_seconds"]])

        return {"data": output.getvalue(), "format": "csv"}
    elif format == "xml":
        # Convert to XML format
        from dicttoxml import dicttoxml
        xml_data = dicttoxml(export_data, custom_root='analytics', attr_type=False)
        return {"data": xml_data.decode('utf-8'), "format": "xml"}
    else:
        raise HTTPException(status_code=400, detail="Unsupported export format")


@router.post("/alerts/webhook")
async def set_alerts_webhook(
    webhook_url: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    organization = get_current_organization(current_user, db)
    if not organization:
        raise HTTPException(status_code=404, detail="User not part of any organization")

    # Validate URL
    parsed = urlparse(webhook_url)
    if not parsed.scheme or not parsed.netloc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook URL"
        )

    # Store webhook URL in organization settings
    org_settings = db.query(OrganizationSettings).filter(
        OrganizationSettings.organization_id == organization.id
    ).first()

    if not org_settings:
        org_settings = OrganizationSettings(
            organization_id=organization.id,
            alerts_webhook=webhook_url
        )
        db.add(org_settings)
    else:
        org_settings.alerts_webhook = webhook_url

    db.commit()
    return {"message": "Alerts webhook updated successfully"}