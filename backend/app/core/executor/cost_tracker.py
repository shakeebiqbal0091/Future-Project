import logging
from typing import Dict, Any
from datetime import datetime
from app.models.models import UsageMetric, MetricTypeEnum
from app.core.database import get_db

logger = logging.getLogger(__name__)


class CostTracker:
    """Track and calculate costs for agent executions."""

    def __init__(
        self,
        model_costs: Dict[str, float] = None,
        token_cost_per_million: float = 0.50,
        fixed_cost_per_task: float = 0.01
    ):
        self.model_costs = model_costs or {
            "claude-sonnet-4-20250514": 0.00003,  # $0.03 per 1K tokens
            "claude-opus-4-20250514": 0.00015,    # $0.15 per 1K tokens
            "claude-haiku-4-20250514": 0.00001,   # $0.01 per 1K tokens
            "gpt4": 0.00006,                       # $0.06 per 1K tokens
            "gpt3_5": 0.000016,                    # $0.016 per 1K tokens
            "gemini": 0.00004                      # $0.04 per 1K tokens
        }
        self.token_cost_per_million = token_cost_per_million  # $0.50 per million tokens
        self.fixed_cost_per_task = fixed_cost_per_task  # $0.01 per task

    def calculate_cost(self, tokens_used: int, model: str) -> float:
        """Calculate cost for a given number of tokens."""
        if tokens_used <= 0:
            return 0.0

        # Get model-specific cost
        model_cost_per_token = self.model_costs.get(model, self.token_cost_per_million / 1000)

        # Calculate token-based cost
        token_cost = (tokens_used / 1000000) * self.token_cost_per_million

        # Add fixed cost per task
        total_cost = token_cost + self.fixed_cost_per_task

        # Round to 6 decimal places (microdollars)
        return round(total_cost, 6)

    async def track_execution_cost(
        self,
        organization_id: str,
        task_id: str,
        tokens_used: int,
        model: str,
        cost_usd: float
    ):
        """Track execution cost in database."""
        try:
            # Create usage metric record
            usage_metric = UsageMetric(
                organization_id=organization_id,
                date=datetime.utcnow().date(),
                metric_type=MetricTypeEnum.tokens,
                value=tokens_used,
                cost_usd=cost_usd
            )

            # Create task cost record (if task tracking is enabled)
            # This would be linked to the actual task record

            # Save to database
            db = get_db()
            db.add(usage_metric)
            db.commit()

            logger.info(f"Tracked cost for task {task_id}: ${cost_usd:.6f} ({tokens_used} tokens)")

        except Exception as e:
            logger.error(f"Failed to track cost for task {task_id}: {e}")

    def get_cost_breakdown(self, organization_id: str, date: datetime.date = None) -> Dict[str, Any]:
        """Get cost breakdown for organization."""
        if date is None:
            date = datetime.utcnow().date()

        db = get_db()
        metrics = db.query(UsageMetric).filter(
            UsageMetric.organization_id == organization_id,
            UsageMetric.date == date
        ).all()

        breakdown = {
            "total_cost": 0.0,
            "token_cost": 0.0,
            "api_call_cost": 0.0,
            "fixed_cost": 0.0,
            "tokens_used": 0,
            "api_calls": 0,
            "cost_per_token": self.token_cost_per_million / 1000000,
            "fixed_cost_per_task": self.fixed_cost_per_task
        }

        for metric in metrics:
            if metric.metric_type == MetricTypeEnum.tokens:
                breakdown["tokens_used"] += metric.value
                breakdown["token_cost"] += metric.cost_usd
            elif metric.metric_type == MetricTypeEnum.api_calls:
                breakdown["api_calls"] += metric.value
                breakdown["api_call_cost"] += metric.cost_usd

        breakdown["total_cost"] = breakdown["token_cost"] + breakdown["api_call_cost"]
        breakdown["fixed_cost"] = breakdown["api_calls"] * self.fixed_cost_per_task
        breakdown["total_cost"] += breakdown["fixed_cost"]

        return breakdown


# Global cost tracker instance
cost_tracker = CostTracker()

def get_cost_tracker() -> CostTracker:
    """Get the global cost tracker instance."""
    return cost_tracker