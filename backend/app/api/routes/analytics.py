from typing import Any, Dict, Optional, List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.core.security.auth_handler import AuthHandler
from app.core.security.utils import RateLimiter, InputValidator
from app.models.models import User, Organization, UsageMetric, Task, Agent, WorkflowRun, TaskStatusEnum, MetricTypeEnum, PlanEnum
from app.schemas.analytics import (
    UsageStatistics, CostBreakdown, PerformanceMetrics, AgentAnalytics,
    UsageStatisticsResponse, CostBreakdownResponse, PerformanceMetricsResponse,
    AgentAnalyticsResponse, AnalyticsErrorResponse, AnalyticsValidationError,
    AnalyticsValidationErrorResponse
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
        Membership.role.in_([RoleEnum.owner, RoleEnum.admin, RoleEnum.member])
    ).first()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not a member of any organization"
        )

    return membership.organization

# Rate limiting configurations
RATE_LIMIT_USAGE = {"key": "analytics:usage", "max_requests": 100, "window_seconds": 3600}
RATE_LIMIT_COSTS = {"key": "analytics:costs", "max_requests": 100, "window_seconds": 3600}
RATE_LIMIT_PERFORMANCE = {"key": "analytics:performance", "max_requests": 100, "window_seconds": 3600}
RATE_LIMIT_AGENTS = {"key": "analytics:agents", "max_requests": 100, "window_seconds": 3600}

# GET /api/v1/analytics/usage - Usage statistics
@router.get("/analytics/usage", response_model=UsageStatisticsResponse)
async def get_usage_statistics(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Rate limiting
    org = await get_current_org(current_user, db)
    rate_limit_key = f"{RATE_LIMIT_USAGE['key']}:{org.id}"
    if RateLimiter.is_rate_limited(rate_limit_key, RATE_LIMIT_USAGE["max_requests"], RATE_LIMIT_USAGE["window_seconds"]):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many usage statistics requests. Try again later."
        )

    # Validate date range
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start date must be before end date"
        )

    # Set default date range to last 30 days if not provided
    if not start_date or not end_date:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)

    try:
        # Get usage metrics for the organization
        metrics = db.query(UsageMetric).filter(
            UsageMetric.organization_id == org.id,
            UsageMetric.date >= start_date.date(),
            UsageMetric.date <= end_date.date()
        ).all()

        # Calculate statistics
        total_tasks = 0
        total_tokens = 0
        total_api_calls = 0
        total_cost = 0.0
        tasks_by_day = {}
        tokens_by_day = {}
        api_calls_by_day = {}
        cost_by_day = {}

        for metric in metrics:
            if metric.metric_type == MetricTypeEnum.tasks:
                total_tasks += metric.value
                tasks_by_day[str(metric.date)] = metric.value
            elif metric.metric_type == MetricTypeEnum.tokens:
                total_tokens += metric.value
                tokens_by_day[str(metric.date)] = metric.value
            elif metric.metric_type == MetricTypeEnum.api_calls:
                total_api_calls += metric.value
                api_calls_by_day[str(metric.date)] = metric.value

            if metric.cost_usd:
                total_cost += metric.cost_usd
                cost_by_day[str(metric.date)] = metric.cost_usd

        # Get task statistics for additional insights
        total_completed_tasks = db.query(Task).filter(
            Task.organization_id == org.id,
            Task.status == TaskStatusEnum.completed,
            Task.completed_at >= start_date,
            Task.completed_at <= end_date
        ).count()

        total_failed_tasks = db.query(Task).filter(
            Task.organization_id == org.id,
            Task.status == TaskStatusEnum.failed,
            Task.completed_at >= start_date,
            Task.completed_at <= end_date
        ).count()

        success_rate = (total_completed_tasks / (total_completed_tasks + total_failed_tasks) * 100) if (total_completed_tasks + total_failed_tasks) > 0 else 0

        # Get average cost per task
        avg_cost_per_task = (total_cost / total_tasks) if total_tasks > 0 else 0

        usage_stats = UsageStatistics(
            total_tasks=total_tasks,
            total_tokens=total_tokens,
            total_api_calls=total_api_calls,
            total_cost=total_cost,
            avg_cost_per_task=avg_cost_per_task,
            success_rate=success_rate,
            tasks_by_day=tasks_by_day,
            tokens_by_day=tokens_by_day,
            api_calls_by_day=api_calls_by_day,
            cost_by_day=cost_by_day,
            date_range={
                "start": str(start_date.date()),
                "end": str(end_date.date())
            }
        )

        return UsageStatisticsResponse(usage_stats=usage_stats)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get usage statistics: {str(e)}"
        )


# GET /api/v1/analytics/costs - Cost breakdown
@router.get("/analytics/costs", response_model=CostBreakdownResponse)
async def get_cost_breakdown(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Rate limiting
    org = await get_current_org(current_user, db)
    rate_limit_key = f"{RATE_LIMIT_COSTS['key']}:{org.id}"
    if RateLimiter.is_rate_limited(rate_limit_key, RATE_LIMIT_COSTS["max_requests"], RATE_LIMIT_COSTS["window_seconds"]):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many cost breakdown requests. Try again later."
        )

    # Validate date range
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start date must be before end date"
        )

    # Set default date range to last 30 days if not provided
    if not start_date or not end_date:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)

    try:
        # Get cost data from usage metrics
        metrics = db.query(UsageMetric).filter(
            UsageMetric.organization_id == org.id,
            UsageMetric.date >= start_date.date(),
            UsageMetric.date <= end_date.date(),
            UsageMetric.cost_usd.isnot(None)
        ).all()

        # Calculate cost breakdown
        cost_by_day = {}
        cost_by_metric_type = {"tasks": 0.0, "tokens": 0.0, "api_calls": 0.0}
        cost_by_agent = {}
        cost_by_workflow = {}

        for metric in metrics:
            # Cost by day
            if str(metric.date) not in cost_by_day:
                cost_by_day[str(metric.date)] = 0.0
            cost_by_day[str(metric.date)] += metric.cost_usd

            # Cost by metric type
            if metric.cost_usd:
                if metric.metric_type == MetricTypeEnum.tasks:
                    cost_by_metric_type["tasks"] += metric.cost_usd
                elif metric.metric_type == MetricTypeEnum.tokens:
                    cost_by_metric_type["tokens"] += metric.cost_usd
                elif metric.metric_type == MetricTypeEnum.api_calls:
                    cost_by_metric_type["api_calls"] += metric.cost_usd

        # Get task-level cost data
        tasks = db.query(Task).filter(
            Task.organization_id == org.id,
            Task.cost_usd.isnot(None),
            Task.completed_at >= start_date,
            Task.completed_at <= end_date
        ).all()

        for task in tasks:
            # Cost by agent
            if task.agent_id:
                if task.agent_id not in cost_by_agent:
                    cost_by_agent[task.agent_id] = 0.0
                cost_by_agent[task.agent_id] += task.cost_usd

            # Cost by workflow
            if task.workflow_run_id:
                workflow_run = db.query(WorkflowRun).filter(
                    WorkflowRun.id == task.workflow_run_id
                ).first()
                if workflow_run and workflow_run.workflow_id:
                    if workflow_run.workflow_id not in cost_by_workflow:
                        cost_by_workflow[workflow_run.workflow_id] = 0.0
                    cost_by_workflow[workflow_run.workflow_id] += task.cost_usd

        # Get total costs and averages
        total_cost = sum(cost_by_day.values())
        avg_daily_cost = (total_cost / len(cost_by_day)) if cost_by_day else 0

        # Get organization plan info
        plan = org.plan.value
        plan_limits = {
            "free": {"monthly_cost": 0, "included_tasks": 100, "included_tokens": 10000},
            "starter": {"monthly_cost": 99, "included_tasks": 1000, "included_tokens": 100000},
            "pro": {"monthly_cost": 299, "included_tasks": 10000, "included_tokens": 1000000},
            "business": {"monthly_cost": 799, "included_tasks": 50000, "included_tokens": 5000000},
            "enterprise": {"monthly_cost": None, "included_tasks": None, "included_tokens": None}  # Custom pricing
        }

        cost_breakdown = CostBreakdown(
            total_cost=total_cost,
            avg_daily_cost=avg_daily_cost,
            cost_by_day=cost_by_day,
            cost_by_metric_type=cost_by_metric_type,
            cost_by_agent=cost_by_agent,
            cost_by_workflow=cost_by_workflow,
            plan=plan,
            plan_limits=plan_limits.get(plan, {}),
            projected_monthly_cost=(avg_daily_cost * 30),
            percentage_of_plan_limit=(total_cost / plan_limits.get(plan, {}).get("monthly_cost", 1)) * 100 if plan_limits.get(plan, {}).get("monthly_cost") else None,
            date_range={
                "start": str(start_date.date()),
                "end": str(end_date.date())
            }
        )

        return CostBreakdownResponse(cost_breakdown=cost_breakdown)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cost breakdown: {str(e)}"
        )


# GET /api/v1/analytics/performance - Performance metrics
@router.get("/analytics/performance", response_model=PerformanceMetricsResponse)
async def get_performance_metrics(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Rate limiting
    org = await get_current_org(current_user, db)
    rate_limit_key = f"{RATE_LIMIT_PERFORMANCE['key']}:{org.id}"
    if RateLimiter.is_rate_limited(rate_limit_key, RATE_LIMIT_PERFORMANCE["max_requests"], RATE_LIMIT_PERFORMANCE["window_seconds"]):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many performance metrics requests. Try again later."
        )

    # Validate date range
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start date must be before end date"
        )

    # Set default date range to last 30 days if not provided
    if not start_date or not end_date:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)

    try:
        # Get task performance data
        tasks = db.query(Task).filter(
            Task.organization_id == org.id,
            Task.status.in_([TaskStatusEnum.completed, TaskStatusEnum.failed]),
            Task.completed_at >= start_date,
            Task.completed_at <= end_date
        ).all()

        # Calculate performance metrics
        total_tasks = len(tasks)
        completed_tasks = sum(1 for task in tasks if task.status == TaskStatusEnum.completed)
        failed_tasks = sum(1 for task in tasks if task.status == TaskStatusEnum.failed)

        success_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        failure_rate = (failed_tasks / total_tasks * 100) if total_tasks > 0 else 0

        # Calculate average execution time
        total_execution_time = sum(task.duration_ms for task in tasks if task.duration_ms)
        avg_execution_time = (total_execution_time / total_tasks) if total_tasks > 0 else 0

        # Calculate p95 execution time
        sorted_durations = sorted([task.duration_ms for task in tasks if task.duration_ms])
        p95_index = max(0, int(len(sorted_durations) * 0.95) - 1)
        p95_execution_time = sorted_durations[p95_index] if sorted_durations else 0

        # Calculate success rate by day
        tasks_by_day = {}
        success_rate_by_day = {}
        for task in tasks:
            task_date = str(task.completed_at.date())
            if task_date not in tasks_by_day:
                tasks_by_day[task_date] = {"completed": 0, "failed": 0}

            if task.status == TaskStatusEnum.completed:
                tasks_by_day[task_date]["completed"] += 1
            else:
                tasks_by_day[task_date]["failed"] += 1

        for date, counts in tasks_by_day.items():
            total_day_tasks = counts["completed"] + counts["failed"]
            success_rate_by_day[date] = (counts["completed"] / total_day_tasks * 100) if total_day_tasks > 0 else 0

        # Calculate error types (from task logs)
        error_types = {}
        task_logs = db.query(TaskLog).filter(
            TaskLog.task_id.in_([task.id for task in tasks]),
            TaskLog.level == "error"
        ).all()

        for log in task_logs:
            error_message = log.message
            if error_message not in error_types:
                error_types[error_message] = 0
            error_types[error_message] += 1

        # Calculate agent performance
        agent_performance = {}
        for task in tasks:
            if task.agent_id:
                if task.agent_id not in agent_performance:
                    agent_performance[task.agent_id] = {"completed": 0, "failed": 0, "total_time": 0, "task_count": 0}

                agent_performance[task.agent_id]["task_count"] += 1
                if task.status == TaskStatusEnum.completed:
                    agent_performance[task.agent_id]["completed"] += 1
                    agent_performance[task.agent_id]["total_time"] += task.duration_ms
                else:
                    agent_performance[task.agent_id]["failed"] += 1

        # Calculate average performance per agent
        avg_performance_by_agent = {}
        for agent_id, stats in agent_performance.items():
            total_tasks_agent = stats["completed"] + stats["failed"]
            success_rate_agent = (stats["completed"] / total_tasks_agent * 100) if total_tasks_agent > 0 else 0
            avg_time_agent = (stats["total_time"] / stats["completed"]) if stats["completed"] > 0 else 0

            avg_performance_by_agent[agent_id] = {
                "success_rate": success_rate_agent,
                "avg_execution_time_ms": avg_time_agent,
                "task_count": stats["task_count"]
            }

        performance_metrics = PerformanceMetrics(
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            failed_tasks=failed_tasks,
            success_rate=success_rate,
            failure_rate=failure_rate,
            avg_execution_time_ms=avg_execution_time,
            p95_execution_time_ms=p95_execution_time,
            tasks_by_day=tasks_by_day,
            success_rate_by_day=success_rate_by_day,
            error_types=error_types,
            avg_performance_by_agent=avg_performance_by_agent,
            date_range={
                "start": str(start_date.date()),
                "end": str(end_date.date())
            }
        )

        return PerformanceMetricsResponse(performance_metrics=performance_metrics)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get performance metrics: {str(e)}"
        )


# GET /api/v1/analytics/agents - Agent-level analytics
@router.get("/analytics/agents", response_model=AgentAnalyticsResponse)
async def get_agent_analytics(
    agent_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Rate limiting
    org = await get_current_org(current_user, db)
    rate_limit_key = f"{RATE_LIMIT_AGENTS['key']}:{org.id}"
    if RateLimiter.is_rate_limited(rate_limit_key, RATE_LIMIT_AGENTS["max_requests"], RATE_LIMIT_AGENTS["window_seconds"]):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many agent analytics requests. Try again later."
        )

    # Validate date range
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start date must be before end date"
        )

    # Set default date range to last 30 days if not provided
    if not start_date or not end_date:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)

    try:
        # Get agents for the organization
        query = db.query(Agent).filter(Agent.organization_id == org.id)

        if agent_id:
            query = query.filter(Agent.id == agent_id)

        agents = query.all()

        if not agents:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No agents found for the organization"
            )

        # Get all tasks for the date range
        all_tasks = db.query(Task).filter(
            Task.organization_id == org.id,
            Task.completed_at >= start_date,
            Task.completed_at <= end_date
        ).all()

        # Calculate agent-level analytics
        agent_analytics = []

        for agent in agents:
            # Get tasks for this specific agent
            agent_tasks = [task for task in all_tasks if task.agent_id == agent.id]

            if not agent_tasks and not agent_id:
                # Skip agents with no tasks unless specific agent is requested
                continue

            total_tasks = len(agent_tasks)
            completed_tasks = sum(1 for task in agent_tasks if task.status == TaskStatusEnum.completed)
            failed_tasks = sum(1 for task in agent_tasks if task.status == TaskStatusEnum.failed)

            success_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            failure_rate = (failed_tasks / total_tasks * 100) if total_tasks > 0 else 0

            # Calculate average execution time
            total_execution_time = sum(task.duration_ms for task in agent_tasks if task.duration_ms)
            avg_execution_time = (total_execution_time / total_tasks) if total_tasks > 0 else 0

            # Calculate p95 execution time
            sorted_durations = sorted([task.duration_ms for task in agent_tasks if task.duration_ms])
            p95_index = max(0, int(len(sorted_durations) * 0.95) - 1)
            p95_execution_time = sorted_durations[p95_index] if sorted_durations else 0

            # Calculate token usage
            total_tokens = sum(task.tokens_used for task in agent_tasks if task.tokens_used)
            avg_tokens_per_task = (total_tokens / total_tasks) if total_tasks > 0 else 0

            # Calculate cost
            total_cost = sum(task.cost_usd for task in agent_tasks if task.cost_usd)
            avg_cost_per_task = (total_cost / total_tasks) if total_tasks > 0 else 0

            # Get error types
            agent_task_ids = [task.id for task in agent_tasks]
            error_types = {}
            if agent_task_ids:
                task_logs = db.query(TaskLog).filter(
                    TaskLog.task_id.in_(agent_task_ids),
                    TaskLog.level == "error"
                ).all()

                for log in task_logs:
                    error_message = log.message
                    if error_message not in error_types:
                        error_types[error_message] = 0
                    error_types[error_message] += 1

            # Get tools usage
            tools_usage = {}
            for task in agent_tasks:
                if task.input and "tools" in task.input:
                    for tool in task.input["tools"]:
                        tool_name = tool.get("name", "unknown")
                        if tool_name not in tools_usage:
                            tools_usage[tool_name] = 0
                        tools_usage[tool_name] += 1

            # Get performance trends
            tasks_by_day = {}
            success_rate_by_day = {}
            for task in agent_tasks:
                task_date = str(task.completed_at.date())
                if task_date not in tasks_by_day:
                    tasks_by_day[task_date] = {"completed": 0, "failed": 0}

                if task.status == TaskStatusEnum.completed:
                    tasks_by_day[task_date]["completed"] += 1
                else:
                    tasks_by_day[task_date]["failed"] += 1

            for date, counts in tasks_by_day.items():
                total_day_tasks = counts["completed"] + counts["failed"]
                success_rate_by_day[date] = (counts["completed"] / total_day_tasks * 100) if total_day_tasks > 0 else 0

            # Get agent model info
            agent_model = agent.model
            agent_tools = agent.tools

            agent_data = AgentAnalytics(
                agent_id=str(agent.id),
                agent_name=agent.name,
                agent_role=agent.role,
                agent_model=agent_model,
                agent_tools=agent_tools,
                total_tasks=total_tasks,
                completed_tasks=completed_tasks,
                failed_tasks=failed_tasks,
                success_rate=success_rate,
                failure_rate=failure_rate,
                avg_execution_time_ms=avg_execution_time,
                p95_execution_time_ms=p95_execution_time,
                total_tokens=total_tokens,
                avg_tokens_per_task=avg_tokens_per_task,
                total_cost=total_cost,
                avg_cost_per_task=avg_cost_per_task,
                error_types=error_types,
                tools_usage=tools_usage,
                tasks_by_day=tasks_by_day,
                success_rate_by_day=success_rate_by_day,
                date_range={
                    "start": str(start_date.date()),
                    "end": str(end_date.date())
                }
            )

            agent_analytics.append(agent_data)

        return AgentAnalyticsResponse(agent_analytics=agent_analytics)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get agent analytics: {str(e)}"
        )

# Error handler for validation errors
@router.exception_handler(AnalyticsValidationErrorResponse)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=exc.json(),
        headers=RateLimiter.get_rate_limit_header("analytics:validation", 100, 3600)
    )

# Error handler for general errors
@router.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=AnalyticsErrorResponse(
            detail="An unexpected error occurred",
            error_code="INTERNAL_SERVER_ERROR",
            timestamp=datetime.utcnow()
        ).json(),
        headers=RateLimiter.get_rate_limit_header("analytics:errors", 10, 3600)
    )