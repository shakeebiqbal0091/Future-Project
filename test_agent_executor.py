import asyncio
import logging
from app.models.models import Agent, Task, TaskStatusEnum
from app.schemas.agents import AgentCreate, AgentTestRequest
from app.core.executor import AgentExecutor, ToolExecutor, ToolSandbox
from app.core.database import get_db
from app.core.auth import get_current_user
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_agent_executor():
    """Test the complete agent executor system."""
    # Initialize components
    agent_executor = AgentExecutor()
    tool_executor = ToolExecutor()
    tool_sandbox = ToolSandbox()

    # Create a test agent
    test_agent = Agent(
        id="test-agent-1",
        organization_id="org-1",
        name="Test Calculator Agent",
        role="Math Assistant",
        instructions="You are a math assistant. Use the calculator tool to perform arithmetic operations. Always validate inputs and handle errors gracefully.",
        model="claude-sonnet-4-20250514",
        tools=["calculator"],
        config={
            "preferred_operations": ["add", "multiply"],
            "max_numbers": 2
        },
        status="active",
        version=1,
        created_by="user-1",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    # Test 1: Simple calculation
    logger.info("=== Test 1: Simple Addition ===")
    test_input_1 = {
        "question": "What is 5 + 7?",
        "context": "User asking about basic addition"
    }

    result_1 = await agent_executor.execute_agent(test_agent, test_input_1)
    logger.info(f"Test 1 Result: {result_1}")

    # Test 2: Complex calculation with tool calling
    logger.info("\n=== Test 2: Complex Calculation with Tool Calling ===")
    test_input_2 = {
        "question": "Calculate (12 * 8) + (15 - 3)",
        "context": "User asking about complex arithmetic"
    }

    result_2 = await agent_executor.execute_agent(test_agent, test_input_2)
    logger.info(f"Test 2 Result: {result_2}")

    # Test 3: Invalid operation (should fail gracefully)
    logger.info("\n=== Test 3: Invalid Operation ===")
    test_input_3 = {
        "question": "What is 10 / 0?",
        "context": "User asking about division by zero"
    }

    result_3 = await agent_executor.execute_agent(test_agent, test_input_3)
    logger.info(f"Test 3 Result: {result_3}")

    # Test 4: Tool execution directly
    logger.info("\n=== Test 4: Direct Tool Execution ===")
    calculator_tool = tool_executor.get_tool("calculator")
    tool_input = {
        "operation": "multiply",
        "a": 15.5,
        "b": 4.2
    }

    # Test in sandbox
    try:
        tool_result = await tool_sandbox.execute_tool(test_agent, {
            "name": "calculator",
            "input": tool_input
        }, {})
        logger.info(f"Tool Result: {tool_result}")
    except Exception as e:
        logger.error(f"Tool execution failed: {e}")

    # Test 5: Agent testing endpoint simulation
    logger.info("\n=== Test 5: Agent Testing Simulation ===")
    test_request = AgentTestRequest(input=test_input_1)
    test_response = await agent_executor.execute_agent(test_agent, test_request.input)
    logger.info(f"Test Response: {test_response}")

    # Summary
    logger.info("\n=== Execution Summary ===")
    logger.info(f"Total tests completed: 5")
    logger.info(f"Successful executions: {sum(1 for r in [result_1, result_2, result_3, test_response] if r[\"success\"])}")
    logger.info(f"Failed executions: {sum(1 for r in [result_1, result_2, result_3, test_response] if not r[\"success\"])}")


if __name__ == "__main__":
    asyncio.run(test_agent_executor())