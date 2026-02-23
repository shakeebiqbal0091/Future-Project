import asyncio
import logging
from typing import Dict, Any
from datetime import datetime, timedelta
from app.models.models import Organization, UsageMetric, MetricTypeEnum
from app.core.database import get_db

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiting system to prevent abuse and manage costs."""

    def __init__(
        self,
        default_limit: int = 1000,
        window_minutes: int = 60,
        burst_limit: int = 100,
        cost_threshold_usd: float = 100.0
    ):
        self.default_limit = default_limit
        self.window_minutes = window_minutes
        self.burst_limit = burst_limit
        self.cost_threshold_usd = cost_threshold_usd
        self.organization_limits = {}

    async def check_limits(self, organization_id: str):
        """Check if organization is within rate limits."""
        # Get organization-specific limits
        limits = self._get_organization_limits(organization_id)

        # Check API call rate limit
        await self._check_api_rate_limit(organization_id, limits)

        # Check cost limit
        await self._check_cost_limit(organization_id, limits)

        # Check concurrent execution limit
        await self._check_concurrent_limit(organization_id, limits)

    def _get_organization_limits(self, organization_id: str) -> Dict[str, Any]:
        """Get rate limits for organization."""
        if organization_id in self.organization_limits:
            return self.organization_limits[organization_id]

        # Get from database or use defaults
        db = get_db()
        organization = db.query(Organization).filter_by(id=organization_id).first()

        if organization:
            # Set limits based on plan
            plan_limits = {
                "free": {"api_calls": 1000, "cost_usd": 10.0, "concurrent": 2},
                "starter": {"api_calls": 5000, "cost_usd": 50.0, "concurrent": 5},
                "pro": {"api_calls": 20000, "cost_usd": 200.0, "concurrent": 20},
                "business": {"api_calls": 100000, "cost_usd": 1000.0, "concurrent": 100},
                "enterprise": {"api_calls": 500000, "cost_usd": 5000.0, "concurrent": 500}
            }
            limits = plan_limits.get(organization.plan.value, plan_limits["pro"])
        else:
            # Default limits for unknown organization
            limits = {
                "api_calls": self.default_limit,
                "cost_usd": self.cost_threshold_usd,
                "concurrent": 5
            }

        self.organization_limits[organization_id] = limits
        return limits

    async def _check_api_rate_limit(self, organization_id: str, limits: Dict[str, Any]):
        """Check API call rate limit."""
        window_start = datetime.utcnow() - timedelta(minutes=self.window_minutes)

        db = get_db()
        count = db.query(UsageMetric).filter(
            UsageMetric.organization_id == organization_id,
            UsageMetric.metric_type == MetricTypeEnum.api_calls,
            UsageMetric.date >= window_start.date()
        ).count()

        if count >= limits["api_calls"]:
            raise RateLimitError(
                f"API call limit exceeded: {count}/{limits['api_calls']} calls in last {self.window_minutes} minutes"
            )

    async def _check_cost_limit(self, organization_id: str, limits: Dict[str, Any]):
        """Check cost limit."""
        today = datetime.utcnow().date()

        db = get_db()
        total_cost = db.query(UsageMetric).filter(
            UsageMetric.organization_id == organization_id,
            UsageMetric.date == today,
            UsageMetric.metric_type == MetricTypeEnum.api_calls
        ).with_entities(
            (UsageMetric.cost_usd).label("total_cost")
        ).scalar()

        if total_cost and total_cost >= limits["cost_usd"]:
            raise RateLimitError(
                f"Cost limit exceeded: ${total_cost:.2f}/${limits['cost_usd']} today"
            )

    async def _check_concurrent_limit(self, organization_id: str, limits: Dict[str, Any]):
        """Check concurrent execution limit."""
        # This would check active tasks in production
        # For now, we'll use a simple counter
        if not hasattr(self, '_concurrent_tasks'):
            self._concurrent_tasks = {}

        current_concurrent = self._concurrent_tasks.get(organization_id, 0)
        if current_concurrent >= limits["concurrent"]:
            raise RateLimitError(
                f"Concurrent execution limit exceeded: {current_concurrent}/{limits['concurrent']} concurrent tasks"
            )

        # Increment counter
        self._concurrent_tasks[organization_id] = current_concurrent + 1

        # Decrement when task completes (would be called from task completion)
        # self._concurrent_tasks[organization_id] -= 1


class RateLimitError(Exception):
    """Custom exception for rate limit exceeded."""
    pass


# Global rate limiter instance
rate_limiter = RateLimiter()

def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance."""
    return rate_limiter