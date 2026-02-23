from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, constr, validator
from app.models.models import StatusEnum, TaskStatusEnum, WorkflowStatusEnum, RoleEnum, PlanEnum, MetricTypeEnum


class UsageStatistics(BaseModel):
    total_tasks: int
    total_tokens: int
    total_api_calls: int
    total_cost: float
    avg_cost_per_task: float
    success_rate: float
    tasks_by_day: Dict[str, int]
    tokens_by_day: Dict[str, int]
    api_calls_by_day: Dict[str, int]
    cost_by_day: Dict[str, float]
    date_range: Dict[str, str]


class CostBreakdown(BaseModel):
    total_cost: float
    avg_daily_cost: float
    cost_by_day: Dict[str, float]
    cost_by_metric_type: Dict[str, float]
    cost_by_agent: Dict[str, float]
    cost_by_workflow: Dict[str, float]
    plan: str
    plan_limits: Dict[str, Any]
    projected_monthly_cost: float
    percentage_of_plan_limit: Optional[float]
    date_range: Dict[str, str]


class PerformanceMetrics(BaseModel):
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    success_rate: float
    failure_rate: float
    avg_execution_time_ms: float
    p95_execution_time_ms: float
    tasks_by_day: Dict[str, Dict[str, int]]
    success_rate_by_day: Dict[str, float]
    error_types: Dict[str, int]
    avg_performance_by_agent: Dict[str, Dict[str, float]]
    date_range: Dict[str, str]


class AgentAnalytics(BaseModel):
    agent_id: str
    agent_name: str
    agent_role: str
    agent_model: str
    agent_tools: List[str]
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    success_rate: float
    failure_rate: float
    avg_execution_time_ms: float
    p95_execution_time_ms: float
    total_tokens: int
    avg_tokens_per_task: float
    total_cost: float
    avg_cost_per_task: float
    error_types: Dict[str, int]
    tools_usage: Dict[str, int]
    tasks_by_day: Dict[str, Dict[str, int]]
    success_rate_by_day: Dict[str, float]
    date_range: Dict[str, str]


class UsageStatisticsResponse(BaseModel):
    usage_stats: UsageStatistics


class CostBreakdownResponse(BaseModel):
    cost_breakdown: CostBreakdown


class PerformanceMetricsResponse(BaseModel):
    performance_metrics: PerformanceMetrics


class AgentAnalyticsResponse(BaseModel):
    agent_analytics: List[AgentAnalytics]


class AnalyticsValidationError(BaseModel):
    field: str
    message: str


class AnalyticsValidationErrorResponse(BaseModel):
    detail: str
    errors: List[AnalyticsValidationError]
    timestamp: datetime = datetime.utcnow()


class AnalyticsErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
    timestamp: datetime = datetime.utcnow()