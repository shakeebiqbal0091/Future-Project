# Agent Executor System Documentation

## Overview

The Agent Executor system is the core execution engine for the AI Agent Orchestration Platform. It provides secure, scalable execution of AI agents with built-in tool integration, context management, and cost tracking.

## Architecture

```
┌───────────────────────────────────────────────────────────────────┐
│                    Agent Executor System                   │
├───────────────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                AgentExecutor Engine                │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                   Tool Framework                   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │               Mock Claude API Layer               │  │
│  └───────────────────────────────────────────────────────────────────┘  │
├───────────────────────────────────────────────────────────────────┤
│                    API Endpoints Layer                  │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │            POST /api/v1/agents/:id/execute         │  │
│  │            GET  /api/v1/agents/:id/tools          │  │
│  │            POST /api/v1/agents/:id/test           │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd ai-agent-orchestration

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration
```

### Basic Usage

```python
from backend.app.core.agent_executor import AgentExecutor, LLMModel

# Create agent configuration
agent_config = {
    "name": "Math Assistant",
    "role": "math expert",
    "instructions": "You are a math expert. Use the calculator tool for arithmetic operations.",
    "tools": {"calculator": True},
    "custom_tools": {}
}

# Initialize executor
executor = AgentExecutor(agent_config, LLMModel.CLAUDE_SONNET_4)

# Execute agent
result = executor.execute("What is 15 + 27?")

print(f"Result: {result['response']}")
print(f"Tokens used: {result['tokens_used']}")
print(f"Cost: ${result['cost_usd']:.4f}")
```

## API Documentation

### Agent Execution Endpoints

#### POST /api/v1/agents/{agent_id}/execute

Execute an agent with the given input.

**Request Body:**
```json
{
  "input": "What is 2 + 2?"
}
```

**Response:**
```json
{
  "task_id": "uuid",
  "agent_id": "uuid",
  "model": "claude-sonnet-4-20250514",
  "input": "What is 2 + 2?",
  "output": {
    "response": "The answer is 4",
    "tool_results": [],
    "conversation_history": [...],
    "tokens_used": 123,
    "cost_usd": 0.0001,
    "state": "completed"
  },
  "tokens_used": 123,
  "cost_usd": 0.0001,
  "state": "completed",
  "created_at": "2026-02-23T10:00:00Z"
}
```

#### GET /api/v1/agents/{agent_id}/tools

Get available tools for an agent.

**Response:**
```json
{
  "agent_id": "uuid",
  "tools": [
    {
      "name": "calculator",
      "description": "Performs arithmetic operations",
      "enabled": true
    }
  ],
  "total_tools": 1
}
```

#### POST /api/v1/agents/{agent_id}/test

Test an agent with sample input.

**Request Body:**
```json
{
  "input": "Test the calculator tool"
}
```

**Response:**
```json
{
  "agent_id": "uuid",
  "model": "claude-sonnet-4-20250514",
  "test_input": "Test the calculator tool",
  "test_output": {
    "response": "Test successful",
    "tool_results": [...],
    "conversation_history": [...],
    "tokens_used": 123,
    "cost_usd": 0.0001,
    "state": "completed"
  },
  "success": true,
  "timestamp": "2026-02-23T10:00:00Z",
  "tokens_used": 123,
  "cost_usd": 0.0001,
  "conversation_history": [...]
}
```

## Tool Framework

### Built-in Tools

#### CalculatorTool

Performs arithmetic operations with high precision.

**Parameters:**
```json
{
  "operation": "add|subtract|multiply|divide|power|sqrt|percent",
  "a": "number",
  "b": "number (optional for sqrt and percent)",
  "precision": "integer (default: 10)"
}
```

**Example:**
```json
{
  "operation": "add",
  "a": 15,
  "b": 27,
  "precision": 5
}
```

#### HTTPRequestTool

Makes secure HTTP API calls with comprehensive validation.

**Parameters:**
```json
{
  "method": "GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS",
  "url": "string",
  "headers": "object",
  "params": "object",
  "data": "object|string",
  "json": "object",
  "timeout": "integer (default: 30)",
  "max_redirects": "integer (default: 5)",
  "verify_ssl": "boolean (default: true)",
  "follow_redirects": "boolean (default: true)"
}
```

**Example:**
```json
{
  "method": "GET",
  "url": "https://api.example.com/data",
  "headers": {
    "Authorization": "Bearer token"
  },
  "timeout": 10
}
```

### Creating Custom Tools

1. **Extend ToolBase class:**
```python
from backend.app.core.agent_executor import ToolBase

class CustomTool(ToolBase):
    def __init__(self):
        super().__init__(
            name="custom_tool",
            description="Custom tool description"
        )

    def _execute_impl(self, arguments: dict) -> Any:
        # Implement tool logic here
        return {"result": "success"}
```

2. **Register the tool:**
```python
# Add to agent configuration
agent_config = {
    "name": "Custom Agent",
    "tools": {"custom_tool": True},
    "custom_tools": {
        "custom_tool": {
            "class": "CustomTool",
            "enabled": True
        }
    }
}
```

## Security Considerations

### Input Validation

- All tool inputs are validated against predefined schemas
- Suspicious patterns are detected and blocked
- URL validation for HTTP requests
- SQL injection prevention

### Rate Limiting

```python
from backend.app.core.agent_executor import ToolSandbox

sandbox = ToolSandbox()
sandbox.set_rate_limit("calculator", max_calls=100, window_seconds=60)
sandbox.set_rate_limit("http_request", max_calls=50, window_seconds=60)
```

### Domain Whitelisting

```python
sandbox.add_allowed_domain("api.example.com")
sandbox.add_allowed_domain("jsonplaceholder.typicode.com")
```

### Security Context

Each tool execution includes security context:
```python
security_context = {
    "user_id": "user-uuid",
    "organization_id": "org-uuid",
    "permissions": ["tool:calculator", "tool:http_request"],
    "rate_limit": {"calculator": 100, "http_request": 50},
    "sandbox": true
}
```

## Cost Management

### Token Tracking

The system automatically tracks token usage:
```python
result = executor.execute("Test message")
print(f"Tokens used: {result['tokens_used']}")
print(f"Cost: ${result['cost_usd']:.4f}")
```

### Cost Optimization Strategies

1. **Model Selection**
   - Use Claude Haiku for simple tasks
   - Use Claude Sonnet for general tasks
   - Use Claude Opus for complex reasoning

2. **Caching**
   - Implement query caching for frequent requests
   - Set appropriate TTL values

3. **Rate Limiting**
   - Set appropriate rate limits per tool
   - Use exponential backoff for retries

4. **Context Management**
   - Limit conversation history length
   - Use efficient prompt engineering

## Error Handling

### Common Errors

1. **ToolNotFoundError**
   - Raised when requested tool is not available
   - Check tool configuration and registration

2. **ToolExecutionError**
   - Raised when tool execution fails
   - Check tool implementation and input validation

3. **ContextLengthExceededError**
   - Raised when conversation context exceeds limits
   - Reduce conversation history or simplify prompts

4. **RateLimitExceededError**
   - Raised when rate limits are exceeded
   - Implement retry logic with backoff

### Error Response Format

```json
{
  "success": false,
  "error": "Error message",
  "tool_name": "tool_name",
  "code": "ERROR_CODE",
  "timestamp": "2026-02-23T10:00:00Z"
}
```

## Integration Examples

### Email Integration

```python
from backend.app.core.tools.email import EmailTool

email_tool = EmailTool()
result = email_tool.execute({
    "to": "user@example.com",
    "subject": "Test Email",
    "body": "This is a test email from the agent system."
})
```

### Slack Integration

```python
from backend.app.core.tools.slack import SlackTool

slack_tool = SlackTool()
result = slack_tool.execute({
    "channel": "#general",
    "text": "Hello from the agent system!",
    "thread_ts": "timestamp"
})
```

## Performance Considerations

### Concurrency

```python
import asyncio
from backend.app.core.agent_executor import AgentExecutor

async def execute_agents_concurrently():
    agent_configs = [config1, config2, config3]

    tasks = []
    for config in agent_configs:
        executor = AgentExecutor(config, LLMModel.CLAUDE_SONNET_4)
        task = asyncio.create_task(executor.execute("Concurrent test"))
        tasks.append(task)

    results = await asyncio.gather(*tasks)
    return results
```

### Caching Strategy

```python
from cachetools import TTLCache

# Cache for tool results
cache = TTLCache(maxsize=1000, ttl=3600)

def get_cached_tool_result(tool_name, arguments):
    key = f"{tool_name}:{json.dumps(arguments)}"
    if key in cache:
        return cache[key]

    result = execute_tool(tool_name, arguments)
    cache[key] = result
    return result
```

## Testing

### Unit Tests

```python
import pytest
from backend.app.core.agent_executor import AgentExecutor, LLMModel

def test_agent_executor_initialization():
    agent_config = {
        "name": "Test Agent",
        "role": "test assistant",
        "instructions": "Help the user with their request.",
        "tools": {"calculator": True},
        "custom_tools": {}
    }

    executor = AgentExecutor(agent_config, LLMModel.CLAUDE_SONNET_4)
    assert executor.model == LLMModel.CLAUDE_SONNET_4
    assert len(executor.tools) == 1
```

### Integration Tests

```python
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_agent_execution_endpoint():
    # Create test agent
    create_response = client.post("/api/v1/agents", json={
        "name": "Test Agent",
        "description": "Test agent",
        "agent_type": "llm",
        "model": "claude-sonnet-4-20250514",
        "api_key": "test-key",
        "is_active": True
    })

    assert create_response.status_code == 200
    agent_id = create_response.json()["id"]

    # Test execution
    execute_response = client.post(f"/api/v1/agents/{agent_id}/execute", json={
        "input": "Test execution"
    })

    assert execute_response.status_code == 200
    assert "task_id" in execute_response.json()
```

## Monitoring and Observability

### Metrics

- **Execution Time**: Track average execution time per agent
- **Success Rate**: Monitor task success/failure rates
- **Token Usage**: Track LLM token consumption
- **Cost Tracking**: Monitor cost per execution
- **Error Rates**: Track different error types

### Logging

```python
import logging
from backend.app.core.agent_executor import AgentExecutor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

executor = AgentExecutor(agent_config, LLMModel.CLAUDE_SONNET_4)
result = executor.execute("Test")

logger.info(f"Execution completed: {result['state']}")
logger.info(f"Tokens used: {result['tokens_used']}")
logger.info(f"Cost: ${result['cost_usd']:.4f}")
```

## Best Practices

### Prompt Engineering

1. **Clear Instructions**: Provide specific, actionable instructions
2. **Context Management**: Keep conversation history relevant
3. **Tool Usage**: Guide agents on when to use specific tools
4. **Error Handling**: Include instructions for handling failures

### Security

1. **Input Validation**: Always validate user inputs
2. **Rate Limiting**: Implement appropriate rate limits
3. **Audit Logging**: Log all tool executions
4. **Least Privilege**: Grant minimum required permissions

### Performance

1. **Model Selection**: Choose appropriate model for task complexity
2. **Caching**: Implement caching for frequent operations
3. **Batching**: Batch similar requests when possible
4. **Monitoring**: Monitor performance metrics regularly

## Troubleshooting

### Common Issues

1. **Tool Not Found**
   - Verify tool is registered and enabled
   - Check agent configuration
   - Ensure proper tool import

2. **Execution Timeout**
   - Increase timeout values
   - Optimize tool implementations
   - Check network connectivity

3. **Context Length Exceeded**
   - Reduce conversation history
   - Simplify prompts
   - Use more efficient token usage

4. **Authentication Issues**
   - Verify API keys and permissions
   - Check rate limits
   - Validate user authentication

### Debug Mode

Enable debug logging for detailed information:
```python
import os
os.environ['DEBUG'] = 'true'
```

## Future Enhancements

### Planned Features

1. **Multi-Agent Workflows**: Support for coordinating multiple agents
2. **Advanced Caching**: Implement distributed caching with invalidation
3. **Custom Tool Marketplace**: Enable sharing and discovery of custom tools
4. **Real-time Monitoring**: Add WebSocket-based monitoring
5. **Cost Optimization**: Implement automatic cost optimization suggestions

### Performance Improvements

1. **Parallel Execution**: Enable parallel tool execution
2. **Model Optimization**: Implement model-specific optimizations
3. **Memory Management**: Improve memory usage for large conversations
4. **Database Optimization**: Optimize database queries and indexing

## Support

For issues and questions:
- Check the troubleshooting section above
- Review the test cases for examples
- Consult the API documentation
- Open an issue in the repository

## Contributing

1. **Code Style**: Follow PEP 8 guidelines
2. **Testing**: Add tests for all new features
3. **Documentation**: Update documentation for changes
4. **Pull Requests**: Submit pull requests with clear descriptions