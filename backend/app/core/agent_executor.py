"""
Core Agent Execution Engine for the AI Agent Orchestration Platform.
Handles execution of agents using Claude API, tool calling, and conversation management.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
from enum import Enum

import httpx
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security.auth_handler import AuthHandler
from app.models.models import Agent, Task, TaskStatusEnum, AgentStatusEnum, ModelEnum, StatusEnum
from app.models.schemas import ToolEnum, ModelEnum

logger = logging.getLogger(__name__)


class ToolCall(BaseModel):
    """Represents a tool call from an agent."""
    id: str = Field(..., description="Unique identifier for the tool call")
    function: str = Field(..., description="Name of the tool function")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Arguments for the tool function")
    return_type: str = Field(..., description="Expected return type")
    name: str = Field(..., description="Human-readable tool name")


class ToolResult(BaseModel):
    """Represents the result of a tool execution."""
    tool_call_id: str = Field(..., description="ID of the tool call this result corresponds to")
    content: Any = Field(..., description="The result content")
    error: Optional[str] = Field(None, description="Error message if tool execution failed")


class ExecutionContext(BaseModel):
    """Context for a single agent execution."""
    agent_id: str = Field(..., description="ID of the agent being executed")
    organization_id: str = Field(..., description="Organization ID")
    user_id: str = Field(..., description="User ID initiating the execution")
    input_data: Dict[str, Any] = Field(default_factory=dict, description="Input data for the agent")
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list, description="Conversation history")
    tool_calls: List[ToolCall] = Field(default_factory=list, description="Tool calls made during execution")
    current_step: int = Field(default=0, description="Current execution step")
    max_steps: int = Field(default=10, description="Maximum number of execution steps")
    timeout_seconds: int = Field(default=300, description="Execution timeout in seconds")


class ClaudeModel(str, Enum):
    """Available Claude models."""
    SONNET = "claude-3-sonnet-20240229"
    OPUS = "claude-3-opus-20240229"
    HAiku = "claude-3-haiku-20240307"


class AgentExecutor:
    """
    Core agent execution engine.
    Handles conversation with Claude API, tool calling, and execution orchestration.
    """

    def __init__(self, agent: Agent, user_id: str, organization_id: str):
        self.agent = agent
        self.user_id = user_id
        self.organization_id = organization_id
        self.http_client = httpx.AsyncClient(timeout=30.0)
        self.execution_id = None
        self.current_conversation: List[Dict[str, Any]] = []

        # Cost tracking
        self.tokens_used = 0
        self.cost_usd = 0.0

        # Rate limiting and security
        self.rate_limit_reset_time = None
        self.tokens_remaining = None
        self.api_call_count = 0
        self.max_api_calls_per_minute = 60  # Configurable based on plan
        self.max_tokens_per_execution = 8000  # Configurable based on plan
        self.max_cost_per_execution = 1.00   # Configurable based on plan

        # Configuration
        self.max_steps = agent.config.get("max_steps", 10) if agent.config else 10
        self.timeout_seconds = agent.config.get("timeout_seconds", 300) if agent.config else 300
        self.cost_per_token = self._get_cost_per_token(agent.model)

        # Available tools
        self.available_tools = self._initialize_tools()

        # Security context
        self.security_context = {
            "allowed_domains": self._get_allowed_domains(),
            "max_execution_time": self.timeout_seconds,
            "max_tokens": self.max_tokens_per_execution,
            "max_cost": self.max_cost_per_execution,
            "tool_permissions": self._get_tool_permissions()
        }

    def _get_allowed_domains(self) -> List[str]:
        """Get allowed domains for HTTP requests based on agent configuration."""
        allowed_domains = [
            "https://api.anthropic.com",
            "https://api.openai.com",
            "https://example.com"  # Replace with actual allowed domains
        ]

        # Add any domain-specific permissions from agent config
        if self.agent.config.get("allowed_domains"):
            allowed_domains.extend(self.agent.config["allowed_domains"])

        return list(set(allowed_domains))  # Remove duplicates

    def _get_tool_permissions(self) -> Dict[str, Any]:
        """Get tool permissions based on agent configuration."""
        return {
            "http_request": {
                "max_retries": 3,
                "timeout": 30,
                "allowed_methods": ["GET", "POST", "PUT", "DELETE"],
                "allowed_headers": ["Content-Type", "Authorization", "User-Agent"]
            },
            "email_send": {
                "max_recipients": 10,
                "max_size": 10 * 1024 * 1024,  # 10MB
                "required_fields": ["to", "subject", "body"]
            },
            "slack_post": {
                "max_message_length": 4000,
                "required_fields": ["channel", "text"]
            }
        }

    def _get_cost_per_token(self, model: str) -> float:
        """Get cost per token for the given model."""
        # Cost mapping (approximate values)
        model_costs = {
            "claude-3-sonnet-20240229": 0.00003,  # $0.03 per 1K tokens
            "claude-3-opus-20240229": 0.00015,    # $0.15 per 1K tokens
            "claude-3-haiku-20240307": 0.000015   # $0.015 per 1K tokens
        }
        return model_costs.get(model, 0.00003)

    def _initialize_tools(self) -> Dict[str, Any]:
        """Initialize available tools based on agent configuration."""
        tools = {}

        # Calculator tool
        if ToolEnum.calculator in self.agent.tools:
            tools[ToolEnum.calculator.value] = CalculatorTool()

        # HTTP Request tool
        if ToolEnum.http_request in self.agent.tools:
            tools[ToolEnum.http_request.value] = HTTPRequestTool()

        # Email tool
        if ToolEnum.email in self.agent.tools:
            tools[ToolEnum.email.value] = EmailTool()

        # Slack tool
        if ToolEnum.slack in self.agent.tools:
            tools[ToolEnum.slack.value] = SlackTool()

        # Web Search tool
        if ToolEnum.web_search in self.agent.tools:
            tools[ToolEnum.web_search.value] = WebSearchTool()

        # Database Query tool
        if ToolEnum.database_query in self.agent.tools:
            tools[ToolEnum.database_query.value] = DatabaseQueryTool()

        return tools

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the agent with the given input data.

        Args:
            input_data: Input data for the agent

        Returns:
            Execution result with output, tool calls, and metadata
        """
        try:
            self.execution_id = str(uuid.uuid4())

            # Initialize execution context
            context = ExecutionContext(
                agent_id=str(self.agent.id),
                organization_id=self.organization_id,
                user_id=self.user_id,
                input_data=input_data,
                max_steps=self.max_steps,
                timeout_seconds=self.timeout_seconds
            )

            # Start execution
            result = await self._execute_agent(context)

            # Calculate costs
            total_cost = self.tokens_used * self.cost_per_token

            return {
                "success": True,
                "execution_id": self.execution_id,
                "output": result.get("output"),
                "tool_calls": result.get("tool_calls", []),
                "tokens_used": self.tokens_used,
                "cost_usd": total_cost,
                "duration_ms": result.get("duration_ms"),
                "steps": result.get("steps", 0)
            }

        except Exception as e:
            logger.error(f"Agent execution failed: {str(e)}", exc_info=True)
            return {
                "success": False,
                "execution_id": self.execution_id,
                "error": str(e),
                "tokens_used": self.tokens_used,
                "cost_usd": self.cost_usd,
                "duration_ms": 0,
                "steps": 0
            }
        finally:
            await self.http_client.aclose()

    async def _execute_agent(self, context: ExecutionContext) -> Dict[str, Any]:
        """Main agent execution loop."""
        start_time = datetime.utcnow()

        # Initialize conversation
        self._add_to_conversation(
            role="system",
            content=f"You are an AI agent named {self.agent.name}. Your role is {self.agent.role}."
        )

        # Add agent instructions
        self._add_to_conversation(
            role="system",
            content=self.agent.instructions
        )

        # Add initial user message
        self._add_to_conversation(
            role="user",
            content=json.dumps(context.input_data)
        )

        step = 0
        while step < context.max_steps:
            # Check timeout
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            if elapsed > context.timeout_seconds:
                return {
                    "output": "Execution timeout exceeded",
                    "tool_calls": context.tool_calls,
                    "duration_ms": int(elapsed * 1000),
                    "steps": step
                }

            # Get agent response
            response = await self._get_agent_response()

            # Process response
            if "error" in response:
                return {
                    "output": f"Agent error: {response['error']}",
                    "tool_calls": context.tool_calls,
                    "duration_ms": int((datetime.utcnow() - start_time).total_seconds() * 1000),
                    "steps": step
                }

            # Check if response contains tool calls
            if "tool_calls" in response:
                tool_calls = response["tool_calls"]

                # Execute tool calls
                tool_results = await self._execute_tool_calls(tool_calls, context)

                # Add tool results to conversation
                for tool_result in tool_results:
                    if tool_result.error:
                        self._add_to_conversation(
                            role="assistant",
                            content=f"Error executing tool {tool_result.tool_call_id}: {tool_result.error}"
                        )
                    else:
                        self._add_to_conversation(
                            role="assistant",
                            content=f"Tool {tool_result.tool_call_id} result: {tool_result.content}"
                        )

                # Update context with tool results
                context.tool_calls.extend(tool_calls)
            else:
                # Final response from agent
                output = response.get("content", "No response from agent")

                return {
                    "output": output,
                    "tool_calls": context.tool_calls,
                    "duration_ms": int((datetime.utcnow() - start_time).total_seconds() * 1000),
                    "steps": step + 1
                }

            step += 1

        return {
            "output": "Maximum execution steps reached",
            "tool_calls": context.tool_calls,
            "duration_ms": int((datetime.utcnow() - start_time).total_seconds() * 1000),
            "steps": step
        }

    async def _get_agent_response(self) -> Dict[str, Any]:
        """Get response from Claude API."""
        messages = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in self.current_conversation
        ]

        try:
            response = await self.http_client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01"
                },
                json={
                    "model": self.agent.model,
                    "max_tokens": 4000,
                    "messages": messages,
                    "stream": False
                }
            )

            response_data = response.json()

            # Update token usage
            self.tokens_used += response_data.get("usage", {}).get("input_tokens", 0)
            self.tokens_used += response_data.get("usage", {}).get("output_tokens", 0)

            return response_data

        except Exception as e:
            logger.error(f"Error calling Claude API: {str(e)}")
            return {"error": f"API call failed: {str(e)}"}

    async def _execute_tool_calls(self, tool_calls: List[Dict[str, Any]], context: ExecutionContext) -> List[ToolResult]:
        """Execute a list of tool calls."""
        tool_results = []

        # Execute tool calls in parallel for better performance
        tasks = []
        for tool_call in tool_calls:
            tool_name = tool_call.get("function")
            arguments = tool_call.get("arguments", {})

            if tool_name in self.available_tools:
                tool = self.available_tools[tool_name]

                # Create a coroutine for each tool execution
                task = self._execute_single_tool_call(tool, tool_call, arguments)
                tasks.append(task)
            else:
                # Tool not found, create error result
                tool_result = ToolResult(
                    tool_call_id=tool_call.get("id", str(uuid.uuid4())),
                    content=None,
                    error=f"Tool {tool_name} not found"
                )
                tool_results.append(tool_result)

        # Wait for all tool executions to complete
        if tasks:
            completed_tasks = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for result in completed_tasks:
                if isinstance(result, Exception):
                    # Handle exceptions from asyncio.gather
                    tool_results.append(
                        ToolResult(
                            tool_call_id=str(uuid.uuid4()),
                            content=None,
                            error=f"Tool execution error: {str(result)}"
                        )
                    )
                else:
                    tool_results.append(result)

        return tool_results

    async def _execute_single_tool_call(self, tool: ToolInterface, tool_call: Dict[str, Any], arguments: Dict[str, Any]) -> ToolResult:
        """Execute a single tool call."""
        try:
            # Execute tool
            result = await tool.execute(arguments)

            # Create tool result
            tool_result = ToolResult(
                tool_call_id=tool_call.get("id", str(uuid.uuid4())),
                content=result,
                error=None
            )

        except Exception as e:
            logger.error(f"Error executing tool {tool_call.get(\"function\")}: {str(e)}", exc_info=True)

            tool_result = ToolResult(
                tool_call_id=tool_call.get("id", str(uuid.uuid4())),
                content=None,
                error=str(e)
            )

        return tool_result

    def _add_to_conversation(self, role: str, content: str):
        """Add message to conversation history."""
        self.current_conversation.append({
            "role": role,
            "content": content
        })


class ToolInterface:
    """Base interface for tools."""

    async def execute(self, arguments: Dict[str, Any]) -> Any:
        """Execute the tool with given arguments."""
        raise NotImplementedError("Tool must implement execute method")


class CalculatorTool(ToolInterface):
    """Calculator tool for arithmetic operations."""

    async def execute(self, arguments: Dict[str, Any]) -> float:
        """Execute calculator operation.

        Args:
            arguments: Dictionary containing operation and operands

        Returns:
            Result of the calculation

        Raises:
            ValueError: If invalid operation or operands
        """
        operation = arguments.get("operation")
        a = arguments.get("a")
        b = arguments.get("b")

        if operation not in ["add", "subtract", "multiply", "divide"]:
            raise ValueError(f"Invalid operation: {operation}")

        if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
            raise ValueError("Operands must be numbers")

        if operation == "add":
            return a + b
        elif operation == "subtract":
            return a - b
        elif operation == "multiply":
            return a * b
        elif operation == "divide":
            if b == 0:
                raise ValueError("Division by zero")
            return a / b


class HTTPRequestTool(ToolInterface):
    """HTTP Request tool for making API calls."""

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute HTTP request.

        Args:
            arguments: Dictionary containing method, url, headers, body

        Returns:
            Response from the HTTP request

        Raises:
            Exception: If request fails
        """
        method = arguments.get("method", "GET").upper()
        url = arguments.get("url")
        headers = arguments.get("headers", {})
        body = arguments.get("body", None)

        if not url:
            raise ValueError("URL is required")

        # Validate URL (basic whitelist check)
        if not url.startswith(("https://")):
            raise ValueError("Only HTTPS URLs are allowed")

        # Rate limiting and security headers
        headers["User-Agent"] = "AgentFlow/1.0"
        headers["X-Request-Source"] = "agent-orchestration"

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                if method == "GET":
                    response = await client.get(url, headers=headers)
                elif method == "POST":
                    response = await client.post(url, headers=headers, json=body)
                elif method == "PUT":
                    response = await client.put(url, headers=headers, json=body)
                elif method == "DELETE":
                    response = await client.delete(url, headers=headers)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                response.raise_for_status()

                return {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "content": response.json() if response.headers.get('content-type') == 'application/json' else response.text
                }

            except httpx.HTTPStatusError as e:
                return {
                    "error": f"HTTP {e.response.status_code}: {e.response.text}",
                    "status_code": e.response.status_code
                }
            except Exception as e:
                return {"error": str(e)}


class EmailTool(ToolInterface):
    """Email tool for sending emails."""

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Send email.

        Args:
            arguments: Dictionary containing to, subject, body, cc, bcc

        Returns:
            Email sending result

        Raises:
            Exception: If email sending fails
        """
        to = arguments.get("to")
        subject = arguments.get("subject")
        body = arguments.get("body")
        cc = arguments.get("cc")
        bcc = arguments.get("bcc")

        if not to:
            raise ValueError("Recipient email (to) is required")

        if not subject:
            raise ValueError("Email subject is required")

        if not body:
            raise ValueError("Email body is required")

        # In a real implementation, this would integrate with an email service
        # For now, we'll simulate email sending

        logger.info(f"Sending email to {to} with subject '{subject}'")

        return {
            "success": True,
            "message": "Email sent successfully",
            "to": to,
            "subject": subject,
            "cc": cc,
            "bcc": bcc
        }


class RateLimitExceededError(Exception):
    """Exception raised when rate limits are exceeded."""
    pass


class CostLimitExceededError(Exception):
    """Exception raised when cost limits are exceeded."""
    pass


async def _check_rate_limits(self):
    """Check rate limits and enforce limits."""
    from datetime import datetime
    now = datetime.utcnow()

    # Check API call rate limit
    if self.rate_limit_reset_time and now < self.rate_limit_reset_time:
        # Rate limit is still active
        raise RateLimitExceededError(f"Rate limit exceeded. Reset at {self.rate_limit_reset_time}")

    # Check if we need to reset rate limit
    if not self.rate_limit_reset_time or now >= self.rate_limit_reset_time:
        self.api_call_count = 0
        self.rate_limit_reset_time = now + timedelta(minutes=1)

    # Check if we've exceeded the limit
    if self.api_call_count >= self.max_api_calls_per_minute:
        raise RateLimitExceededError(f"Rate limit exceeded. Reset at {self.rate_limit_reset_time}")

    # Increment API call count
    self.api_call_count += 1


def _check_cost_limits(self, tokens_used: int) -> bool:
    """Check if cost limits are exceeded."""
    current_cost = tokens_used * self.cost_per_token
    total_cost = self.cost_usd + current_cost

    if total_cost > self.max_cost_per_execution:
        raise CostLimitExceededError("Cost limit exceeded for this execution")

    if tokens_used > self.max_tokens_per_execution:
        raise CostLimitExceededError("Token limit exceeded for this execution")

    return True
    """Exception raised when cost limits are exceeded."""
    pass


async def _check_rate_limits(self):
    """Check rate limits and enforce limits."""
    from datetime import datetime
    now = datetime.utcnow()

    # Check API call rate limit
    if self.rate_limit_reset_time and now < self.rate_limit_reset_time:
        # Rate limit is still active
        raise RateLimitExceededError(f"Rate limit exceeded. Reset at {self.rate_limit_reset_time}")

    # Check if we need to reset rate limit
    if not self.rate_limit_reset_time or now >= self.rate_limit_reset_time:
        self.api_call_count = 0
        self.rate_limit_reset_time = now + timedelta(minutes=1)

    # Check if we've exceeded the limit
    if self.api_call_count >= self.max_api_calls_per_minute:
        raise RateLimitExceededError(f"Rate limit exceeded. Reset at {self.rate_limit_reset_time}")

    # Increment API call count
    self.api_call_count += 1


def _check_cost_limits(self, tokens_used: int) -> bool:
    """Check if cost limits are exceeded."""
    current_cost = tokens_used * self.cost_per_token
    total_cost = self.cost_usd + current_cost

    if total_cost > self.max_cost_per_execution:
        raise CostLimitExceededError("Cost limit exceeded for this execution")

    if tokens_used > self.max_tokens_per_execution:
        raise CostLimitExceededError("Token limit exceeded for this execution")

    return True


class SlackTool(ToolInterface):
    """Slack tool for posting messages."""

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Post message to Slack.

        Args:
            arguments: Dictionary containing channel, text, thread_ts

        Returns:
            Slack posting result

        Raises:
            Exception: If posting fails
        """
        channel = arguments.get("channel")
        text = arguments.get("text")
        thread_ts = arguments.get("thread_ts")

        if not channel:
            raise ValueError("Slack channel is required")

        if not text:
            raise ValueError("Message text is required")

        # In a real implementation, this would use Slack API
        # For now, we'll simulate Slack posting

        logger.info(f"Posting to Slack channel {channel}: {text[:100]}...")

        return {
            "success": True,
            "message": "Message posted to Slack",
            "channel": channel,
            "text": text[:100] + "..." if len(text) > 100 else text,
            "thread_ts": thread_ts
        }


class WebSearchTool(ToolInterface):
    """Web Search tool for searching the web for information."""

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search the web for information.

        Args:
            arguments: Dictionary containing query and num_results

        Returns:
            Search results with titles, URLs, and snippets

        Raises:
            Exception: If search fails
        """
        query = arguments.get("query")
        num_results = arguments.get("num_results", 5)

        if not query:
            raise ValueError("Search query is required")

        if not isinstance(num_results, int) or num_results < 1 or num_results > 10:
            raise ValueError("num_results must be an integer between 1 and 10")

        # In a real implementation, this would use a search API like SerpApi, Bing Search, or Google Custom Search
        # For now, we'll simulate search results
        logger.info(f"Searching web for: {query}")

        # Simulate search results (in production, replace with actual API calls)
        results = []
        for i in range(num_results):
            results.append({
                "title": f"Search Result {i+1}: {query}",
                "url": f"https://example.com/result{i+1}",
                "snippet": f"This is a simulated snippet for search result {i+1} about {query}",
                "rank": i+1
            })

        return {
            "query": query,
            "num_results": num_results,
            "results": results,
            "total_results": num_results,
            "success": True
        }


class DatabaseQueryTool(ToolInterface):
    """Database Query tool for executing SQL queries against connected databases."""

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute SQL query against a database.

        Args:
            arguments: Dictionary containing query, database_id, and optional parameters

        Returns:
            Query results with rows and metadata

        Raises:
            Exception: If query execution fails
        """
        query = arguments.get("query")
        database_id = arguments.get("database_id")
        params = arguments.get("params", [])

        if not query:
            raise ValueError("SQL query is required")

        if not database_id:
            raise ValueError("Database ID is required")

        # In a real implementation, this would use SQLAlchemy or database-specific client
        # For now, we'll simulate query execution
        logger.info(f"Executing database query on {database_id}: {query[:100]}...")

        # Simulate query results (in production, replace with actual database execution)
        # For demonstration, we'll return a simple result set
        result = {
            "database_id": database_id,
            "query": query,
            "rows": [
                {"id": 1, "name": "Example Row 1", "value": 100},
                {"id": 2, "name": "Example Row 2", "value": 200}
            ],
            "columns": ["id", "name", "value"],
            "row_count": 2,
            "success": True
        }

        return result