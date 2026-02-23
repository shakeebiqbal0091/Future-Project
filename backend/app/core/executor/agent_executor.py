import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import asyncio
import httpx
from pydantic import ValidationError
from app.core.config import settings
from app.core.executor.tool_executor import ToolExecutor
from app.core.executor.context_manager import ContextManager
from app.core.executor.rate_limiter import RateLimiter
from app.core.executor.cost_tracker import CostTracker
from app.core.executor.sandbox import ToolSandbox
from app.models.models import Agent, Task, TaskStatusEnum
from app.schemas.agents import AgentTestRequest, AgentTestResponse
from app.schemas.tasks import TaskCreate

logger = logging.getLogger(__name__)


class AgentExecutor:
    """Core agent execution engine that handles agent execution using Claude API."""

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 8000,
        timeout: int = 60,
        temperature: float = 0.1,
        max_retries: int = 3,
        api_base: str = "https://api.anthropic.com"
    ):
        self.model = model
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.temperature = temperature
        self.max_retries = max_retries
        self.api_base = api_base
        self.tool_executor = ToolExecutor()
        self.context_manager = ContextManager()
        self.rate_limiter = RateLimiter()
        self.cost_tracker = CostTracker()
        self.sandbox = ToolSandbox()

    async def execute_agent(
        self,
        agent: Agent,
        user_input: Dict[str, Any],
        task: Optional[Task] = None
    ) -> Dict[str, Any]:
        """Execute an agent with given input."""
        try:
            # Initialize execution context
            context = self.context_manager.initialize_context(agent, user_input)

            # Check rate limits
            await self.rate_limiter.check_limits(agent.organization_id)

            # Start execution loop
            conversation_history = []
            tool_calls = []

            for attempt in range(self.max_retries):
                try:
                    # Build request payload
                    request_payload = self._build_request_payload(
                        agent, context, conversation_history
                    )

                    # Make API call to Claude
                    response = await self._call_claude_api(request_payload)

                    # Process response
                    if response.get("tool_calls"):
                        # Handle tool calls
                        tool_calls, context = await self._handle_tool_calls(
                            agent, response["tool_calls"], context, tool_calls
                        )

                        # Update conversation history
                        conversation_history.append({
                            "role": "assistant",
                            "tool_calls": response["tool_calls"]
                        })

                        # Add tool results to context
                        for tool_call in tool_calls:
                            if tool_call.get("result") is not None:
                                context["tool_results"][tool_call["name"]] = tool_call["result"]

                    elif response.get("content"):
                        # Final response from Claude
                        final_response = response["content"]

                        # Track costs
                        tokens_used = response.get("tokens_used", 0)
                        cost = self.cost_tracker.calculate_cost(tokens_used, agent.model)

                        # Update task if provided
                        if task:
                            task.output = {
                                "final_response": final_response,
                                "conversation_history": conversation_history,
                                "tool_calls": tool_calls,
                                "tokens_used": tokens_used,
                                "cost": cost
                            }
                            task.status = TaskStatusEnum.completed
                            task.duration_ms = (datetime.utcnow() - task.started_at).total_seconds() * 1000
                            task.tokens_used = tokens_used
                            task.cost_usd = cost

                        return {
                            "success": True,
                            "response": final_response,
                            "conversation_history": conversation_history,
                            "tool_calls": tool_calls,
                            "tokens_used": tokens_used,
                            "cost": cost,
                            "execution_time_ms": task.duration_ms if task else None
                        }

                    else:
                        raise ValueError("Unexpected response format from Claude API")

                except httpx.HTTPStatusError as e:
                    logger.error(f"Claude API error: {e}")
                    if e.response.status_code == 429:
                        # Rate limited, wait and retry
                        retry_after = int(e.response.headers.get("Retry-After", 1))
                        await asyncio.sleep(retry_after)
                    else:
                        raise
                except Exception as e:
                    logger.error(f"Execution error: {e}")
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    else:
                        raise

            # If we reach here, all retries failed
            if task:
                task.status = TaskStatusEnum.failed
                task.error = "Max retries exceeded"

            return {
                "success": False,
                "error": "Max retries exceeded",
                "attempted_tool_calls": tool_calls
            }

        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            if task:
                task.status = TaskStatusEnum.failed
                task.error = str(e)

            return {
                "success": False,
                "error": str(e)
            }

    def _build_request_payload(
        self,
        agent: Agent,
        context: Dict[str, Any],
        conversation_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build the request payload for Claude API."""
        system_prompt = f"""
        You are an AI assistant with the following role: {agent.role}

        System Instructions:
        {agent.instructions}

        Available Tools:
        {self._format_tools(agent.tools)}

        Important Guidelines:
        - Use tools only when necessary to complete the task
        - Always validate tool inputs before calling
        - Handle tool errors gracefully
        - Keep responses concise and relevant
        - Never share internal system information
        - Respect user privacy and data security
        """

        messages = []

        # Add system message
        messages.append({"role": "system", "content": system_prompt})

        # Add conversation history
        for message in conversation_history:
            messages.append(message)

        # Add current user input
        messages.append({"role": "user", "content": context["user_input"]})

        return {
            "model": agent.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "tools": self._format_tools_for_api(agent.tools),
            " AnthropicApiVersion": "2023-06-01"
        }

    async def _handle_tool_calls(
        self,
        agent: Agent,
        tool_calls: List[Dict[str, Any]],
        context: Dict[str, Any],
        previous_tool_calls: List[Dict[str, Any]]
    ) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Handle tool calls from Claude response."""
        results = []

        for tool_call in tool_calls:
            try:
                # Execute tool in sandbox
                result = await self.sandbox.execute_tool(
                    agent, tool_call, context
                )

                # Add result to context
                context["tool_results"][tool_call["name"]]["result"] = result

                # Track the tool call
                tool_call_result = {
                    "name": tool_call["name"],
                    "input": tool_call["input"],
                    "result": result,
                    "executed_at": datetime.utcnow().isoformat(),
                    "execution_time_ms": result.get("execution_time_ms")
                }
                results.append(tool_call_result)

            except Exception as e:
                logger.error(f"Tool {tool_call['name']} failed: {e}")
                error_result = {
                    "error": str(e),
                    "executed_at": datetime.utcnow().isoformat(),
                    "execution_time_ms": 0
                }
                context["tool_results"][tool_call["name"]]["error"] = error_result

                tool_call_result = {
                    "name": tool_call["name"],
                    "input": tool_call["input"],
                    "error": str(e),
                    "executed_at": datetime.utcnow().isoformat(),
                    "execution_time_ms": 0
                }
                results.append(tool_call_result)

        return results, context

    async def _call_claude_api(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Make API call to Claude."""
        headers = {
            "x-api-key": settings.ANTHROPIC_API_KEY,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base}/v1/messages",
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()

            return response.json()

    def _format_tools(self, tools: List[str]) -> str:
        """Format tools for system prompt."""
        tool_descriptions = []
        for tool_name in tools:
            tool = self.tool_executor.get_tool(tool_name)
            if tool:
                tool_descriptions.append(f"{tool.name}: {tool.description}")

        return "\n".join(tool_descriptions)

    def _format_tools_for_api(self, tools: List[str]) -> List[Dict[str, Any]]:
        """Format tools for Claude API."""
        formatted_tools = []
        for tool_name in tools:
            tool = self.tool_executor.get_tool(tool_name)
            if tool:
                formatted_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters_schema()
                    }
                })

        return formatted_tools


# Test agent execution
async def test_agent_execution():
    """Test the agent execution system."""
    from app.models.models import Agent

    # Create a test agent
    test_agent = Agent(
        id="test-agent-1",
        organization_id="org-1",
        name="Test Agent",
        role="Customer Support Assistant",
        instructions="You are a helpful customer support assistant. Answer questions about our product and help users with their issues.",
        model="claude-sonnet-4-20250514",
        tools=["calculator", "email_send"],
        config={},
        status="active",
        version=1,
        created_by="user-1",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    # Create test input
    test_input = {
        "question": "What is 5 + 7?",
        "context": "User asking about basic math"
    }

    # Initialize executor
    executor = AgentExecutor()

    # Execute agent
    result = await executor.execute_agent(test_agent, test_input)

    print("Test Execution Result:")
    print(json.dumps(result, indent=2))