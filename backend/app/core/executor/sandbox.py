import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from app.core.executor.tool_executor import ToolExecutor, get_tool_executor
from app.models.models import Agent, Task, TaskStatusEnum

logger = logging.getLogger(__name__)


class ToolSandbox:
    """Tool execution sandbox with security controls and resource limits."""

    def __init__(
        self,
        max_execution_time_ms: int = 30000,
        max_memory_mb: int = 256,
        max_output_size_kb: int = 100,
        network_whitelist: List[str] = None,
        cost_per_execution_usd: float = 0.001
    ):
        self.max_execution_time_ms = max_execution_time_ms
        self.max_memory_mb = max_memory_mb
        self.max_output_size_kb = max_output_size_kb
        self.network_whitelist = network_whitelist or [
            "api.anthropic.com",
            "hooks.slack.com",
            "gmail.googleapis.com",
            "example.com"  # Replace with actual domains
        ]
        self.cost_per_execution_usd = cost_per_execution_usd
        self.tool_executor = get_tool_executor()

    async def execute_tool(
        self,
        agent: Agent,
        tool_call: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a tool call with security sandboxing."""
        tool_name = tool_call["name"]
        tool_input = tool_call["input"]

        # Security: Validate tool permissions
        if tool_name not in agent.tools:
            raise PermissionError(f"Tool {tool_name} not permitted for agent {agent.id}")

        # Security: Validate input against schema
        if not self._validate_tool_input(tool_name, tool_input):
            raise ValueError(f"Invalid input for tool {tool_name}")

        # Security: Check network restrictions if applicable
        if "url" in tool_input:
            self._check_network_restrictions(tool_input["url"])

        # Security: Rate limiting per tool
        await self._check_tool_rate_limit(agent.id, tool_name)

        # Security: Cost tracking
        await self._track_tool_cost(agent.organization_id, tool_name)

        # Execute tool with timeout
        try:
            result = await self._execute_with_timeout(
                self._execute_tool_internal,
                agent,
                tool_name,
                tool_input,
                context
            )
            return result

        except asyncio.TimeoutError:
            raise TimeoutError(f"Tool {tool_name} execution timed out after {self.max_execution_time_ms}ms")
        except Exception as e:
            logger.error(f"Tool {tool_name} execution failed: {e}")
            raise

    async def _execute_tool_internal(
        self,
        agent: Agent,
        tool_name: str,
        tool_input: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Internal tool execution with resource monitoring."""
        start_time = datetime.utcnow()

        # Execute the tool
        result = self.tool_executor.tools[tool_name].execute(tool_input)

        # Monitor resource usage
        execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        output_size = len(json.dumps(result)) / 1024  # KB

        # Security: Check resource limits
        if execution_time > self.max_execution_time_ms:
            raise ValueError(f"Tool execution exceeded time limit: {execution_time}ms > {self.max_execution_time_ms}ms")

        if output_size > self.max_output_size_kb:
            raise ValueError(f"Tool output exceeded size limit: {output_size}KB > {self.max_output_size_kb}KB")

        # Add execution metadata
        result["execution_time_ms"] = execution_time
        result["timestamp"] = datetime.utcnow().isoformat()

        return result

    async def _execute_with_timeout(
        self,
        coro,
        *args,
        **kwargs
    ):
        """Execute coroutine with timeout."""
        return await asyncio.wait_for(coro(*args, **kwargs), timeout=self.max_execution_time_ms / 1000)

    def _validate_tool_input(self, tool_name: str, input_data: Dict[str, Any]) -> bool:
        """Validate tool input against schema."""
        tool = self.tool_executor.get_tool(tool_name)
        if not tool:
            return False

        return tool.validate_input(input_data)

    def _check_network_restrictions(self, url: str):
        """Check if URL is allowed based on network whitelist."""
        from urllib.parse import urlparse

        parsed = urlparse(url)
        if not parsed.netloc:
            return

        # Check against whitelist
        if not any(domain in parsed.netloc for domain in self.network_whitelist):
            raise PermissionError(f"URL {url} not in allowed network whitelist")

        # Additional security checks
        if self._is_private_ip(parsed.netloc):
            raise PermissionError(f"Private IP addresses are not allowed: {parsed.netloc}")

    def _is_private_ip(self, netloc: str) -> bool:
        """Check if netloc is a private IP address."""
        import ipaddress

        # Extract IP address from netloc
        import re
        ip_match = re.match(r'(\d+\.\d+\.\d+\.\d+)', netloc)
        if ip_match:
            ip = ip_match.group(1)
            try:
                ip_obj = ipaddress.ip_address(ip)
                return ip_obj.is_private
            except ValueError:
                return False

        return False

    async def _check_tool_rate_limit(self, agent_id: str, tool_name: str):
        """Check rate limits for tool usage."""
        # This is a simple in-memory rate limiter
        # In production, use Redis or database-based rate limiting
        from collections import defaultdict
        import time

        if not hasattr(self, '_rate_limits'):
            self._rate_limits = defaultdict(lambda: defaultdict(list))

        now = time.time()
        window_seconds = 60  # 1 minute window
        max_calls = 60  # 60 calls per minute

        # Clean old entries
        agent_limits = self._rate_limits[agent_id]
        for tool, timestamps in list(agent_limits.items()):
            agent_limits[tool] = [ts for ts in timestamps if now - ts < window_seconds]

        # Check limit
        recent_calls = agent_limits[tool_name]
        if len(recent_calls) >= max_calls:
            raise RateLimitExceededError(f"Tool {tool_name} rate limit exceeded")

        # Record this call
        recent_calls.append(now)

    async def _track_tool_cost(self, organization_id: str, tool_name: str):
        """Track cost of tool execution."""
        # This is a simple cost tracker
        # In production, integrate with actual billing system
        from app.models.models import UsageMetric, MetricTypeEnum
        from app.core.database import get_db

        # Create usage metric record
        usage_metric = UsageMetric(
            organization_id=organization_id,
            date=datetime.utcnow().date(),
            metric_type=MetricTypeEnum.api_calls,
            value=1,
            cost_usd=self.cost_per_execution_usd
        )

        # Save to database
        db = get_db()
        db.add(usage_metric)
        db.commit()


class RateLimitExceededError(Exception):
    """Custom exception for rate limit exceeded."""
    pass


# Global sandbox instance
sandbox = ToolSandbox()

def get_sandbox() -> ToolSandbox:
    """Get the global tool sandbox instance."""
    return sandbox