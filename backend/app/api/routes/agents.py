import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.models.models import Agent, Task, TaskStatusEnum
from app.schemas.agents import (
    AgentCreate, AgentUpdate, Agent, AgentTestRequest, AgentTestResponse,
    AgentMetrics, AgentList, AgentVersionList, AgentCreateResponse,
    AgentUpdateResponse, AgentDeleteResponse, AgentDeployResponse
)
from app.core.database import get_db
from app.core.executor import AgentExecutor, ToolSandbox, RateLimitExceededError
from app.core.auth import get_current_user, get_current_organization
from app.core.exceptions import BusinessLogicError

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize executor with proper configuration
agent_executor = AgentExecutor(
    model="claude-sonnet-4-20250514",
    max_tokens=8000,
    timeout=60,
    temperature=0.1,
    max_retries=3
)


@router.post("/", response_model=AgentCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent_create: AgentCreate,
    organization_id: str = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """Create a new agent."""
    try:
        # Create agent
        db_agent = Agent(
            id=str(uuid.uuid4()),
            organization_id=organization_id,
            name=agent_create.name,
            role=agent_create.role,
            instructions=agent_create.instructions,
            model=agent_create.model,
            tools=agent_create.tools,
            config=agent_create.config,
            status="active",
            version=1,
            created_by=get_current_user().id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        db.add(db_agent)
        db.commit()
        db.refresh(db_agent)

        return AgentCreateResponse(agent=Agent.from_orm(db_agent))

    except Exception as e:
        logger.error(f"Failed to create agent: {e}")
        raise HTTPException(status_code=500, detail="Failed to create agent")


@router.get("/", response_model=AgentList)
async def list_agents(
    page: int = 1,
    size: int = 10,
    organization_id: str = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """List agents with pagination."""
    offset = (page - 1) * size
    agents_query = db.query(Agent).filter_by(organization_id=organization_id)

    total = agents_query.count()
    agents = agents_query.offset(offset).limit(size).all()

    return AgentList(
        agents=[Agent.from_orm(agent) for agent in agents],
        total=total,
        page=page,
        size=size
    )


@router.get("/{agent_id}", response_model=Agent)
async def get_agent(
    agent_id: str,
    organization_id: str = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """Get agent details."""
    agent = db.query(Agent).filter_by(
        id=agent_id,
        organization_id=organization_id
    ).first()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    return Agent.from_orm(agent)


@router.put("/{agent_id}", response_model=AgentUpdateResponse)
async def update_agent(
    agent_id: str,
    agent_update: AgentUpdate,
    organization_id: str = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """Update agent configuration."""
    agent = db.query(Agent).filter_by(
        id=agent_id,
        organization_id=organization_id
    ).first()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Update fields
    if agent_update.name:
        agent.name = agent_update.name
    if agent_update.role:
        agent.role = agent_update.role
    if agent_update.instructions:
        agent.instructions = agent_update.instructions
    if agent_update.model:
        agent.model = agent_update.model
    if agent_update.tools is not None:
        agent.tools = agent_update.tools
    if agent_update.config is not None:
        agent.config = agent_update.config
    if agent_update.status:
        agent.status = agent_update.status

    agent.updated_at = datetime.utcnow()
    db.commit()

    return AgentUpdateResponse(agent=Agent.from_orm(agent))


@router.delete("/{agent_id}", response_model=AgentDeleteResponse)
async def delete_agent(
    agent_id: str,
    organization_id: str = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """Delete an agent."""
    agent = db.query(Agent).filter_by(
        id=agent_id,
        organization_id=organization_id
    ).first()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    db.delete(agent)
    db.commit()

    return AgentDeleteResponse()


@router.post("/{agent_id}/execute", response_model=Dict[str, Any])
async def execute_agent(
    agent_id: str,
    input_data: Dict[str, Any],
    organization_id: str = Depends(get_current_organization),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Execute an agent with given input."""
    agent = db.query(Agent).filter_by(
        id=agent_id,
        organization_id=organization_id
    ).first()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    if agent.status != "active":
        raise HTTPException(status_code=400, detail="Agent is not active")

    # Create task record
    task = Task(
        id=str(uuid.uuid4()),
        workflow_run_id=None,  # No workflow for direct execution
        agent_id=agent_id,
        step_name="direct_execution",
        input=input_data,
        status="pending",
        created_at=datetime.utcnow(),
        started_at=datetime.utcnow()
    )
    db.add(task)
    db.commit()

    try:
        # Execute agent
        result = await agent_executor.execute_agent(agent, input_data, task)

        # Update task with result
        task.status = "completed" if result["success"] else "failed"
        task.duration_ms = result.get("execution_time_ms")
        task.tokens_used = result.get("tokens_used")
        task.cost_usd = result.get("cost")
        db.commit()

        return result

    except RateLimitExceededError:
        task.status = "failed"
        task.error = "Rate limit exceeded"
        db.commit()
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    except Exception as e:
        logger.error(f"Agent execution failed: {e}")
        task.status = "failed"
        task.error = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Execution failed: {str(e)}")


@router.post("/{agent_id}/test", response_model=AgentTestResponse)
async def test_agent(
    agent_id: str,
    test_request: AgentTestRequest,
    organization_id: str = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """Test agent functionality."""
    agent = db.query(Agent).filter_by(
        id=agent_id,
        organization_id=organization_id
    ).first()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    try:
        # Test execution
        result = await agent_executor.execute_agent(agent, test_request.input)

        return AgentTestResponse(
            success=result["success"],
            message="Test completed successfully" if result["success"] else "Test failed",
            output=result.get("response"),
            error=result.get("error")
        )

    except Exception as e:
        logger.error(f"Agent test failed: {e}")
        return AgentTestResponse(
            success=False,
            message=f"Test failed: {str(e)}",
            error=str(e)
        )


@router.get("/{agent_id}/metrics", response_model=AgentMetrics)
async def get_agent_metrics(
    agent_id: str,
    organization_id: str = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """Get agent performance metrics."""
    agent = db.query(Agent).filter_by(
        id=agent_id,
        organization_id=organization_id
    ).first()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Calculate metrics
    tasks = db.query(Task).filter_by(agent_id=agent_id).all()
    total_tasks = len(tasks)
    completed_tasks = len([t for t in tasks if t.status == "completed"])
    failed_tasks = len([t for t in tasks if t.status == "failed"])
    success_rate = completed_tasks / total_tasks if total_tasks > 0 else 0

    if tasks:
        avg_execution_time = sum(t.duration_ms for t in tasks if t.duration_ms) / len(tasks)
        total_tokens = sum(t.tokens_used for t in tasks if t.tokens_used)
        total_cost = sum(t.cost_usd for t in tasks if t.cost_usd)
    else:
        avg_execution_time = 0
        total_tokens = 0
        total_cost = 0.0

    # Get task distribution by status
    tasks_by_status = {}
    for task in tasks:
        tasks_by_status[task.status] = tasks_by_status.get(task.status, 0) + 1

    return AgentMetrics(
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        failed_tasks=failed_tasks,
        success_rate=success_rate,
        avg_execution_time_ms=avg_execution_time,
        total_tokens_used=total_tokens,
        total_cost_usd=total_cost,
        tasks_by_status=tasks_by_status,
        tasks_by_hour={},  # TODO: Implement hourly breakdown
        cost_by_day={}     # TODO: Implement daily cost breakdown
    )


@router.get("/{agent_id}/tools", response_model=List[Dict[str, Any]])
async def list_agent_tools(
    agent_id: str,
    organization_id: str = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """List available tools for agent."""
    agent = db.query(Agent).filter_by(
        id=agent_id,
        organization_id=organization_id
    ).first()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Get tool information from executor
    tool_executor = agent_executor.tool_executor
    all_tools = tool_executor.get_all_tools()

    agent_tools = []
    for tool_name in agent.tools:
        tool = all_tools.get(tool_name)
        if tool:
            agent_tools.append({
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters_schema()
            })

    return agent_tools


@router.post("/{agent_id}/deploy", response_model=AgentDeployResponse)
async def deploy_agent_version(
    agent_id: str,
    organization_id: str = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """Deploy a new version of the agent."""
    agent = db.query(Agent).filter_by(
        id=agent_id,
        organization_id=organization_id
    ).first()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Create new version
    from app.models.models import AgentVersion
    new_version = AgentVersion(
        id=str(uuid.uuid4()),
        agent_id=agent_id,
        version=agent.version + 1,
        config=agent.config,
        deployed_at=datetime.utcnow(),
        deployed_by=get_current_user().id
    )

    db.add(new_version)
    agent.version = new_version.version
    agent.updated_at = datetime.utcnow()
    db.commit()

    return AgentDeployResponse(
        version=AgentVersion.from_orm(new_version)
    )


@router.get("/{agent_id}/versions", response_model=AgentVersionList)
async def list_agent_versions(
    agent_id: str,
    page: int = 1,
    size: int = 10,
    organization_id: str = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """List agent versions with pagination."""
    offset = (page - 1) * size

    from app.models.models import AgentVersion
    versions_query = db.query(AgentVersion).filter_by(agent_id=agent_id)

    total = versions_query.count()
    versions = versions_query.offset(offset).limit(size).all()

    return AgentVersionList(
        versions=[AgentVersion.from_orm(v) for v in versions],
        total=total,
        page=page,
        size=size
    )


@router.exception_handler(RateLimitExceededError)
async def rate_limit_exception_handler(request, exc):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded", "error": str(exc)},
    )


@router.exception_handler(BusinessLogicError)
async def business_logic_exception_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"detail": "Business logic error", "error": str(exc)},
    )


@router.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unexpected error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)},
    )