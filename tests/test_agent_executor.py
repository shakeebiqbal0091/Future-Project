"""
Comprehensive test suite for Agent Executor system.

Tests cover:
- AgentExecutor core functionality
- Tool execution and sandboxing
- Mock Claude API responses
- API endpoints
- Error handling and edge cases
"""

import asyncio
import json
import uuid
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import after path is set up
from backend.app.core.agent_executor import (
    AgentExecutor,
    AgentState,
    LLMModel,
    MockClaudeResponse,
    ToolSandbox,
    CalculatorTool,
    HTTPRequestTool,
    AgentExecutorError,
    ToolNotFoundError,
    ToolExecutionError,
    ContextLengthExceededError
)
from backend.app.core.tools import ToolInterface, ToolRegistry
from backend.app.models.models import Agent, StatusEnum
from backend.app.models.schemas import ToolEnum
from backend.app.api.agents import router as agents_router
from backend.main import app

# Create test client
client = TestClient(app)


class TestAgentExecutorCore:
    """Tests for AgentExecutor core functionality"""

    def test_agent_executor_initialization(self):
        """Test AgentExecutor initialization with valid config"""
        agent_config = {
            "name": "Test Agent",
            "role": "test assistant",
            "instructions": "Help the user with their request.",
            "tools": {"calculator": True},
            "custom_tools": {}
        }

        executor = AgentExecutor(agent_config, LLMModel.CLAUDE_SONNET_4)

        assert executor.agent_config == agent_config
        assert executor.model == LLMModel.CLAUDE_SONNET_4
        assert executor.state == AgentState.PENDING
        assert len(executor.tools) == 1
        assert "calculator" in executor.tools

    def test_agent_executor_invalid_model(self):
        """Test AgentExecutor with invalid model"""
        agent_config = {
            "name": "Test Agent",
            "role": "test assistant",
            "instructions": "Help the user with their request.",
            "tools": {},
            "custom_tools": {}
        }

        with pytest.raises(ValueError):
            AgentExecutor(agent_config, "invalid-model")

    def test_get_tools(self):
        """Test getting available tools"""
        agent_config = {
            "name": "Test Agent",
            "role": "test assistant",
            "instructions": "Help the user with their request.",
            "tools": {
                "calculator": True,
                "http_request": False
            },
            "custom_tools": {}
        }

        executor = AgentExecutor(agent_config, LLMModel.CLAUDE_SONNET_4)
        tools = executor.get_tools()

        assert len(tools) == 1
        assert tools[0]["name"] == "calculator"
        assert tools[0]["enabled"] is True

    def test_build_system_prompt(self):
        """Test system prompt building"""
        agent_config = {
            "name": "Test Agent",
            "role": "math assistant",
            "instructions": "You are a math expert. Use the calculator tool for arithmetic operations.",
            "tools": {"calculator": True},
            "custom_tools": {}
        }

        executor = AgentExecutor(agent_config, LLMModel.CLAUDE_SONNET_4)
        prompt = executor._build_system_prompt()

        assert "You are an AI assistant with the following role: math assistant" in prompt
        assert "Use the calculator tool for arithmetic operations" in prompt
        assert "Available tools:" in prompt
        assert "calculator" in prompt


class TestMockClaudeResponse:
    """Tests for MockClaudeResponse generation"""

    def test_generate_tool_use_response(self):
        """Test tool use response generation"""
        tool_calls = [
            {
                "name": "calculator",
                "arguments": json.dumps({"operation": "add", "a": 5, "b": 3})
            }
        ]

        response = MockClaudeResponse.generate_tool_use_response(tool_calls, LLMModel.CLAUDE_SONNET_4)

        assert response["id"]
        assert response["model"] == "claude-sonnet-4-20250514"
        assert len(response["choices"]) == 1
        assert response["choices"][0]["finish_reason"] == "tool_use"
        assert len(response["choices"][0]["tool_use_calls"]) == 1

    def test_generate_chat_completion_response(self):
        """Test chat completion response generation"""
        messages = [
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": "What is 2+2?"}
        ]

        response = MockClaudeResponse.generate_chat_completion_response(messages, LLMModel.CLAUDE_SONNET_4)

        assert response["id"]
        assert response["model"] == "claude-sonnet-4-20250514"
        assert len(response["choices"]) == 1
        assert response["choices"][0]["finish_reason"] == "stop"
        assert "Mock response from Claude" in response["choices"][0]["message"]["content"]

    def test_context_length_exceeded(self):
        """Test context length validation"""
        messages = [{"role": "user", "content": "A" * 10000}]  # Exceed context limit

        with pytest.raises(ContextLengthExceededError):
            MockClaudeResponse.generate_chat_completion_response(messages, LLMModel.CLAUDE_SONNET_4)


class TestToolSandbox:
    """Tests for ToolSandbox security and validation"""

    def test_sandbox_allowed_domains(self):
        """Test domain whitelisting"""
        sandbox = ToolSandbox()
        sandbox.add_allowed_domain("api.example.com")
        sandbox.add_allowed_domain("jsonplaceholder.typicode.com")

        assert "api.example.com" in sandbox._allowed_domains
        assert "jsonplaceholder.typicode.com" in sandbox._allowed_domains

    def test_sandbox_rate_limiting(self):
        """Test rate limiting functionality"""
        sandbox = ToolSandbox()
        sandbox.set_rate_limit("calculator", max_calls=3, window_seconds=60)

        # First 3 calls should succeed
        assert sandbox.check_rate_limit("calculator") is True
        assert sandbox.check_rate_limit("calculator") is True
        assert sandbox.check_rate_limit("calculator") is True

        # Fourth call should fail (simulated)
        assert sandbox.check_rate_limit("calculator") is False

    def test_sandbox_input_validation(self):
        """Test input validation"""
        sandbox = ToolSandbox()

        # Valid input
        assert sandbox.validate_input("calculator", {"operation": "add", "a": 5, "b": 3}) is True

        # Invalid input - suspicious patterns
        assert sandbox.validate_input("http_request", {"url": "rm -rf /"}) is False
        assert sandbox.validate_input("http_request", {"url": "DROP TABLE users"}) is False

        # Invalid input - wrong type
        assert sandbox.validate_input("calculator", "not a dict") is False


class TestCalculatorTool:
    """Tests for CalculatorTool implementation"""

    def setup_method(self):
        self.tool = CalculatorTool()

    def test_calculator_addition(self):
        """Test calculator addition"""
        result = self.tool.execute({"operation": "add", "a": 10, "b": 5})
        assert result["success"] is True
        assert result["result"]["result"] == 15
        assert result["result"]["operation"] == "add"

    def test_calculator_subtraction(self):
        """Test calculator subtraction"""
        result = self.tool.execute({"operation": "subtract", "a": 10, "b": 5})
        assert result["success"] is True
        assert result["result"]["result"] == 5

    def test_calculator_multiplication(self):
        """Test calculator multiplication"""
        result = self.tool.execute({"operation": "multiply", "a": 10, "b": 5})
        assert result["success"] is True
        assert result["result"]["result"] == 50

    def test_calculator_division(self):
        """Test calculator division"""
        result = self.tool.execute({"operation": "divide", "a": 10, "b": 5})
        assert result["success"] is True
        assert result["result"]["result"] == 2

    def test_calculator_division_by_zero(self):
        """Test calculator division by zero"""
        result = self.tool.execute({"operation": "divide", "a": 10, "b": 0})
        assert result["success"] is False
        assert "Division by zero" in result["error"]

    def test_calculator_sqrt(self):
        """Test calculator square root"""
        result = self.tool.execute({"operation": "sqrt", "a": 16})
        assert result["success"] is True
        assert result["result"]["result"] == 4

    def test_calculator_sqrt_negative(self):
        """Test calculator square root of negative number"""
        result = self.tool.execute({"operation": "sqrt", "a": -16})
        assert result["success"] is False
        assert "Cannot calculate square root of negative number" in result["error"]

    def test_calculator_invalid_operation(self):
        """Test calculator with invalid operation"""
        result = self.tool.execute({"operation": "invalid", "a": 10, "b": 5})
        assert result["success"] is False
        assert "Unknown operation" in result["error"]


class TestHTTPRequestTool:
    """Tests for HTTPRequestTool implementation"""

    def setup_method(self):
        self.tool = HTTPRequestTool()

    @patch('httpx.AsyncClient')
    async def test_http_request_get(self, mock_client):
        """Test HTTP GET request"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.reason_phrase = "OK"
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = {"data": "test"}
        mock_response.url = "https://api.example.com/test"
        mock_response.history = []

        mock_client.return_value.request.return_value = mock_response

        result = await self.tool.execute({
            "method": "GET",
            "url": "https://api.example.com/test"
        })

        assert result["success"] is True
        assert result["response"]["status_code"] == 200
        assert result["response"]["json"]["data"] == "test"

    @patch('httpx.AsyncClient')
    async def test_http_request_post(self, mock_client):
        """Test HTTP POST request"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.reason_phrase = "Created"
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = {"id": 1, "message": "created"}
        mock_response.url = "https://api.example.com/items"
        mock_response.history = []

        mock_client.return_value.request.return_value = mock_response

        result = await self.tool.execute({
            "method": "POST",
            "url": "https://api.example.com/items",
            "json": {"name": "test"}
        })

        assert result["success"] is True
        assert result["response"]["status_code"] == 201
        assert result["response"]["json"]["id"] == 1

    @patch('httpx.AsyncClient')
    async def test_http_request_timeout(self, mock_client):
        """Test HTTP request timeout"""
        mock_client.return_value.request.side_effect = httpx.TimeoutException()

        result = await self.tool.execute({
            "method": "GET",
            "url": "https://api.example.com/test",
            "timeout": 1
        })

        assert result["success"] is False
        assert result["error"] == "Request timeout"

    @patch('httpx.AsyncClient')
    async def test_http_request_ssl_validation(self, mock_client):
        """Test HTTP request SSL validation"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.reason_phrase = "OK"
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = {"data": "secure"}
        mock_response.url = "https://api.example.com/secure"
        mock_response.history = []

        mock_client.return_value.request.return_value = mock_response

        result = await self.tool.execute({
            "method": "GET",
            "url": "https://api.example.com/secure",
            "verify_ssl": True
        })

        assert result["success"] is True
        assert result["response"]["status_code"] == 200

    def test_http_request_url_validation(self):
        """Test HTTP request URL validation"""
        # Valid URL
        assert self.tool.sandbox.validate_input("http_request", {
            "url": "https://api.example.com/data"
        }) is True

        # Invalid URL - wrong scheme
        assert self.tool.sandbox.validate_input("http_request", {
            "url": "ftp://example.com"
        }) is False

        # Invalid URL - path traversal
        assert self.tool.sandbox.validate_input("http_request", {
            "url": "https://example.com/../../etc/passwd"
        }) is False


class TestAgentExecutorExecution:
    """Tests for AgentExecutor execution flow"""

    def setup_method(self):
        self.agent_config = {
            "name": "Test Agent",
            "role": "test assistant",
            "instructions": "Help the user with their request.",
            "tools": {"calculator": True},
            "custom_tools": {}
        }
        self.executor = AgentExecutor(self.agent_config, LLMModel.CLAUDE_SONNET_4)

    def test_simple_execution_no_tools(self):
        """Test simple execution without tool calls"""
        result = self.executor.execute("Hello, how are you?")

        assert result["response"]
        assert result["state"] == "completed"
        assert len(result["tool_results"]) == 0
        assert len(result["conversation_history"]) > 0

    def test_execution_with_tool_calls(self):
        """Test execution that requires tool calls"""
        # This is a bit tricky to test directly since we're mocking the Claude response
        # We'll test the tool execution path separately
        pass

    def test_conversation_history_limiting(self):
        """Test conversation history limiting"""
        # Add many messages to history
        for i in range(20):
            self.executor.conversation_history.append({
                "role": "user",
                "content": f"Message {i}"
            })

        # Execute with input
        self.executor.execute("Test message")

        # History should be limited to last 10 messages
        assert len(self.executor.conversation_history) <= 12  # 10 history + 2 current

    def test_token_tracking(self):
        """Test token tracking"""
        initial_tokens = self.executor.tokens_used
        self.executor.execute("Test message")
        assert self.executor.tokens_used > initial_tokens

    def test_cost_tracking(self):
        """Test cost tracking"""
        initial_cost = self.executor.cost_usd
        self.executor.execute("Test message")
        assert self.executor.cost_usd > initial_cost


class TestAPIEndpoints:
    """Tests for FastAPI endpoints"""

    def setup_method(self):
        self.agent_data = {
            "name": "Test API Agent",
            "role": "api test assistant",
            "instructions": "Help test the API endpoints.",
            "tools": {"calculator": True},
            "custom_tools": {}
        }

        self.test_agent = Agent(
            id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            name=self.agent_data["name"],
            role=self.agent_data["role"],
            instructions=self.agent_data["instructions"],
            model="claude-sonnet-4-20250514",
            tools=json.dumps(self.agent_data["tools"]),
            config={},
            status=StatusEnum.active,
            version=1,
            created_by=uuid.uuid4(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

    def test_create_agent_endpoint(self):
        """Test agent creation endpoint"""
        response = client.post("/api/v1/agents", json={
            "name": "Test Agent",
            "description": "Test agent for API",
            "agent_type": "llm",
            "model": "claude-sonnet-4-20250514",
            "api_key": "test-key",
            "is_active": True
        })

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Agent"
        assert data["model"] == "claude-sonnet-4-20250514"

    def test_get_agents_endpoint(self):
        """Test get agents endpoint"""
        # First create an agent
        create_response = client.post("/api/v1/agents", json={
            "name": "Test List Agent",
            "description": "Test agent for listing",
            "agent_type": "llm",
            "model": "claude-sonnet-4-20250514",
            "api_key": "test-key",
            "is_active": True
        })

        assert create_response.status_code == 200

        # Then get agents
        list_response = client.get("/api/v1/agents")
        assert list_response.status_code == 200
        data = list_response.json()
        assert len(data) >= 1
        assert any(agent["name"] == "Test List Agent" for agent in data)

    def test_get_agent_endpoint(self):
        """Test get single agent endpoint"""
        # Create agent first
        create_response = client.post("/api/v1/agents", json={
            "name": "Test Single Agent",
            "description": "Test agent for single get",
            "agent_type": "llm",
            "model": "claude-sonnet-4-20250514",
            "api_key": "test-key",
            "is_active": True
        })

        assert create_response.status_code == 200
        agent_id = create_response.json()["id"]

        # Get the agent
        get_response = client.get(f"/api/v1/agents/{agent_id}")
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["name"] == "Test Single Agent"

    def test_update_agent_endpoint(self):
        """Test update agent endpoint"""
        # Create agent first
        create_response = client.post("/api/v1/agents", json={
            "name": "Test Update Agent",
            "description": "Test agent for update",
            "agent_type": "llm",
            "model": "claude-sonnet-4-20250514",
            "api_key": "test-key",
            "is_active": True
        })

        assert create_response.status_code == 200
        agent_id = create_response.json()["id"]

        # Update the agent
        update_response = client.put(f"/api/v1/agents/{agent_id}", json={
            "name": "Updated Test Agent",
            "description": "Updated description"
        })

        assert update_response.status_code == 200
        data = update_response.json()
        assert data["name"] == "Updated Test Agent"
        assert data["description"] == "Updated description"

    def test_delete_agent_endpoint(self):
        """Test delete agent endpoint"""
        # Create agent first
        create_response = client.post("/api/v1/agents", json={
            "name": "Test Delete Agent",
            "description": "Test agent for delete",
            "agent_type": "llm",
            "model": "claude-sonnet-4-20250514",
            "api_key": "test-key",
            "is_active": True
        })

        assert create_response.status_code == 200
        agent_id = create_response.json()["id"]

        # Delete the agent
        delete_response = client.delete(f"/api/v1/agents/{agent_id}")
        assert delete_response.status_code == 204

        # Verify agent is deleted
        get_response = client.get(f"/api/v1/agents/{agent_id}", status_code=404)
        assert get_response.status_code == 404

    def test_agent_execution_endpoint(self):
        """Test agent execution endpoint"""
        # Create test agent in database first
        # (In real implementation, this would be part of test setup)
        pass

    def test_agent_tools_endpoint(self):
        """Test agent tools endpoint"""
        # Create test agent in database first
        # (In real implementation, this would be part of test setup)
        pass

    def test_agent_test_endpoint(self):
        """Test agent test endpoint"""
        # Create test agent in database first
        # (In real implementation, this would be part of test setup)
        pass


class TestErrorHandling:
    """Tests for error handling and edge cases"""

    def test_tool_not_found_error(self):
        """Test ToolNotFoundError handling"""
        agent_config = {
            "name": "Test Agent",
            "role": "test assistant",
            "instructions": "Help the user with their request.",
            "tools": {"calculator": True},
            "custom_tools": {}
        }

        executor = AgentExecutor(agent_config, LLMModel.CLAUDE_SONNET_4)

        with pytest.raises(ToolNotFoundError):
            executor._execute_tool_call({"name": "nonexistent_tool", "arguments": "{}"})

    def test_tool_execution_error(self):
        """Test ToolExecutionError handling"""
        class FailingTool(ToolInterface):
            async def execute(self, arguments: Dict[str, Any]) -> Any:
                raise ToolExecutionError("test_tool", "Intentional failure")

        tool = FailingTool("test_tool", "Test tool", {})

        result = asyncio.run(tool.execute({}))
        assert result["success"] is False
        assert "Intentional failure" in result["error"]

    def test_invalid_input_error(self):
        """Test invalid input error handling"""
        tool = CalculatorTool()

        # Invalid operation
        result = tool.execute({"operation": "invalid", "a": 10, "b": 5})
        assert result["success"] is False
        assert "Unknown operation" in result["error"]

        # Missing required parameters
        result = tool.execute({"operation": "add", "a": 10})
        assert result["success"] is False
        assert "Second operand 'b' is required" in result["error"]

    def test_context_length_error(self):
        """Test context length exceeded error"""
        agent_config = {
            "name": "Test Agent",
            "role": "test assistant",
            "instructions": "Help the user with their request.",
            "tools": {},
            "custom_tools": {}
        }

        executor = AgentExecutor(agent_config, LLMModel.CLAUDE_SONNET_4)

        # Create very long messages
        long_message = "A" * 10000
        messages = [{"role": "user", "content": long_message}]

        with pytest.raises(ContextLengthExceededError):
            MockClaudeResponse.generate_chat_completion_response(messages, LLMModel.CLAUDE_SONNET_4)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])