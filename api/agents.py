from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from api.schemas import (
    AgentCreate, AgentUpdate, AgentResponse, ErrorResponse,
    PaginationResponse, SortOrder, Filter
)
from core.database import get_db
from core.auth import get_current_user, get_current_active_user, get_current_organization

router = APIRouter()


@router.post("/", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent: AgentCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Get user's organization
    organization = get_current_organization(current_user, db)
    if not organization:
        raise HTTPException(status_code=404, detail="User not part of any organization")

    # Validate model
    if not agent.model.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Model cannot be empty"
        )

    db_agent = Agent(
        name=agent.name,
        description=agent.description,
        agent_type=agent.agent_type,
        model=agent.model,
        api_key=agent.api_key,
        is_active=agent.is_active,
        organization_id=organization.id,
        created_by=current_user.id
    )
    db.add(db_agent)
    db.commit()
    db.refresh(db_agent)

    return db_agent


@router.get("/", response_model=List[AgentResponse])
async def get_agents(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Get user's organization
    organization = get_current_organization(current_user, db)
    if not organization:
        raise HTTPException(status_code=404, detail="User not part of any organization")

    agents = db.query(Agent).filter(Agent.organization_id == organization.id).offset(skip).limit(limit).all()
    return agents


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Check if user has access to this agent
    organization = get_current_organization(current_user, db)
    if agent.organization_id != organization.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this agent")

    return agent


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: int,
    agent_update: AgentUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Check if user has access to this agent
    organization = get_current_organization(current_user, db)
    if agent.organization_id != organization.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this agent")

    agent.name = agent_update.name or agent.name
    agent.description = agent_update.description or agent.description
    agent.agent_type = agent_update.agent_type or agent.agent_type
    agent.model = agent_update.model or agent.model
    agent.api_key = agent_update.api_key or agent.api_key
    agent.is_active = agent_update.is_active if agent_update.is_active is not None else agent.is_active

    db.commit()
    db.refresh(agent)
    return agent


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Check if user has access to this agent
    organization = get_current_organization(current_user, db)
    if agent.organization_id != organization.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this agent")

    db.delete(agent)
    db.commit()


from typing import Dict
from fastapi import HTTPException
from app.core.agent_executor import AgentExecutor, LLMModel


@router.post("/{agent_id}/test")
async def test_agent(
    agent_id: int,
    input_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Check if user has access to this agent
    organization = get_current_organization(current_user, db)
    if agent.organization_id != organization.id:
        raise HTTPException(status_code=403, detail="Not authorized to test this agent")

    try:
        # Map model string to LLMModel enum
        model_map = {
            "claude-sonnet-4-20250514": LLMModel.CLAUDE_SONNET_4,
            "claude-opus-4-20250514": LLMModel.CLAUDE_OPUS_4,
            "claude-haiku-4-20250514": LLMModel.CLAUDE_HAIKU_4
        }
        model = model_map.get(agent.model, LLMModel.CLAUDE_SONNET_4)

        # Create agent configuration from database
        agent_config = {
            "name": agent.name,
            "role": agent.description or "assistant",
            "instructions": f"You are an AI assistant with the role: {agent.description or 'general assistant'}. Help the user with their request.",
            "tools": {},
            "custom_tools": {}
        }

        # Add enabled tools based on agent configuration
        if agent.tools and isinstance(agent.tools, dict):
            agent_config["tools"] = agent.tools

        # Create and execute agent
        executor = AgentExecutor(agent_config, model)
        result = executor.execute(input_data)

        return {
            "agent_id": agent.id,
            "model": agent.model,
            "test_input": input_data,
            "test_output": result,
            "success": result.get("state") == "completed",
            "timestamp": datetime.utcnow().isoformat(),
            "tokens_used": result.get("tokens_used"),
            "cost_usd": result.get("cost_usd"),
            "conversation_history": result.get("conversation_history")
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Agent execution failed: {str(e)}"
        )


@router.get("/search")
async def search_agents(
    query: str = Query(..., min_length=2),
    skip: int = 0,
    limit: int = 20,
    sort: Optional[SortOrder] = None,
    filters: Optional[List[Filter]] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    organization = get_current_organization(current_user, db)
    if not organization:
        raise HTTPException(status_code=404, detail="User not part of any organization")

    q = db.query(Agent).filter(Agent.organization_id == organization.id)

    # Apply filters
    if filters:
        for filter in filters:
            if filter.operator == "eq":
                q = q.filter(getattr(Agent, filter.field) == filter.value)
            elif filter.operator == "ne":
                q = q.filter(getattr(Agent, filter.field) != filter.value)
            elif filter.operator == "contains":
                q = q.filter(getattr(Agent, filter.field).ilike(f"%{filter.value}%")
            # Add more operators as needed

    # Apply search query
    q = q.filter(
        Agent.name.ilike(f"%{query}%") |
        Agent.description.ilike(f"%{query}%") |
        Agent.model.ilike(f"%{query}%")
    )

    # Apply sorting
    if sort:
        sort_field = getattr(Agent, sort.field)
        if sort.direction == "desc":
            sort_field = sort_field.desc()
        q = q.order_by(sort_field)

    total = q.count()
    agents = q.offset(skip).limit(limit).all()

    return PaginationResponse(
        items=agents,
        total=total,
        page=(skip // limit) + 1,
        size=limit,
        total_pages=(total + limit - 1) // limit
    )


@router.post("/{agent_id}/execute")
async def execute_agent(
    agent_id: int,
    input_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Check if user has access to this agent
    organization = get_current_organization(current_user, db)
    if agent.organization_id != organization.id:
        raise HTTPException(status_code=403, detail="Not authorized to execute this agent")

    try:
        # Map model string to LLMModel enum
        model_map = {
            "claude-sonnet-4-20250514": LLMModel.CLAUDE_SONNET_4,
            "claude-opus-4-20250514": LLMModel.CLAUDE_OPUS_4,
            "claude-haiku-4-20250514": LLMModel.CLAUDE_HAIKU_4
        }
        model = model_map.get(agent.model, LLMModel.CLAUDE_SONNET_4)

        # Create agent configuration from database
        agent_config = {
            "name": agent.name,
            "role": agent.description or "assistant",
            "instructions": f"You are an AI assistant with the role: {agent.description or 'general assistant'}. Help the user with their request.",
            "tools": {},
            "custom_tools": {}
        }

        # Add enabled tools based on agent configuration
        if agent.tools and isinstance(agent.tools, dict):
            agent_config["tools"] = agent.tools

        # Create and execute agent
        executor = AgentExecutor(agent_config, model)
        result = executor.execute(input_data)

        # Create task record
        task = Task(
            name=f"Execution of agent {agent.name}",
            description=f"Executed agent {agent.name} with input: {json.dumps(input_data, default=str)}",
            agent_id=agent.id,
            workflow_id=None,
            input_data=input_data,
            output_data=result,
            status=result.get("state", "completed"),
            created_by=current_user.id,
            organization_id=organization.id
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        return {
            "task_id": task.id,
            "agent_id": agent.id,
            "model": agent.model,
            "input": input_data,
            "output": result,
            "tokens_used": result.get("tokens_used"),
            "cost_usd": result.get("cost_usd"),
            "state": result.get("state"),
            "created_at": task.created_at.isoformat()
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Agent execution failed: {str(e)}"
        )


@router.get("/{agent_id}/tools")
async def get_agent_tools(
    agent_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Check if user has access to this agent
    organization = get_current_organization(current_user, db)
    if agent.organization_id != organization.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this agent's tools")

    try:
        # Map model string to LLMModel enum
        model_map = {
            "claude-sonnet-4-20250514": LLMModel.CLAUDE_SONNET_4,
            "claude-opus-4-20250514": LLMModel.CLAUDE_OPUS_4,
            "claude-haiku-4-20250514": LLMModel.CLAUDE_HAIKU_4
        }
        model = model_map.get(agent.model, LLMModel.CLAUDE_SONNET_4)

        # Create agent configuration from database
        agent_config = {
            "name": agent.name,
            "role": agent.description or "assistant",
            "instructions": f"You are an AI assistant with the role: {agent.description or 'general assistant'}. Help the user with their request.",
            "tools": {},
            "custom_tools": {}
        }

        # Add enabled tools based on agent configuration
        if agent.tools and isinstance(agent.tools, dict):
            agent_config["tools"] = agent.tools

        # Create executor to get tools
        executor = AgentExecutor(agent_config, model)
        tools = executor.get_tools()

        return {
            "agent_id": agent.id,
            "tools": tools,
            "total_tools": len(tools)
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve agent tools: {str(e)}"
        )


@router.get("/{agent_id}/usage")
async def get_agent_usage(
    agent_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Check if user has access to this agent
    organization = get_current_organization(current_user, db)
    if agent.organization_id != organization.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this agent")

    # Get usage statistics for the last 30 days
    from datetime import datetime, timedelta
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)

    tasks_count = db.query(Task).filter(
        Task.agent_id == agent_id,
        Task.created_at >= thirty_days_ago
    ).count()

    return {
        "agent_id": agent.id,
        "name": agent.name,
        "tasks_executed_last_30_days": tasks_count,
        "model": agent.model,
        "agent_type": agent.agent_type
    }