import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.models.models import Agent, Task, AgentVersion
from app.schemas.agents import Agent, AgentList, AgentVersion, AgentMetrics
from app.schemas.marketplace import MarketplaceAgent, MarketplaceAgentList
from app.core.database import get_db
from app.core.auth import get_current_user, get_current_organization
from app.core.security import generate_access_token

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/agents", response_model=MarketplaceAgentList)
async def list_marketplace_agents(
    page: int = 1,
    size: int = 12,
    search: Optional[str] = None,
    category: Optional[str] = None,
    price: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List marketplace agents with filtering and pagination."""
    offset = (page - 1) * size

    # Base query for all agents that are active and public
    agents_query = db.query(Agent).filter_by(status="active")

    # Apply search filter
    if search:
        search_pattern = f"%{search}%"
        agents_query = agents_query.filter(
            Agent.name.ilike(search_pattern) |
            Agent.role.ilike(search_pattern) |
            Agent.instructions.ilike(search_pattern)
        )

    # Apply category filter
    if category and category != "all":
        agents_query = agents_query.filter(Agent.role.ilike(f"%{category}%"))

    # Apply price filter (for future pricing implementation)
    # For now, all agents are free in marketplace

    total = agents_query.count()
    agents = agents_query.offset(offset).limit(size).all()

    marketplace_agents = []
    for agent in agents:
        # Get basic metrics for display
        tasks = db.query(Task).filter_by(agent_id=agent.id).all()
        total_tasks = len(tasks)
        completed_tasks = len([t for t in tasks if t.status == "completed"])
        failed_tasks = len([t for t in tasks if t.status == "failed"])
        success_rate = completed_tasks / total_tasks if total_tasks > 0 else 0

        # Get latest version
        latest_version = db.query(AgentVersion).filter_by(agent_id=agent.id).order_by(
            AgentVersion.version.desc()
        ).first()

        marketplace_agents.append(MarketplaceAgent(
            id=agent.id,
            name=agent.name,
            description=agent.instructions[:200] + "..." if len(agent.instructions) > 200 else agent.instructions,
            category=agent.role.lower(),
            price=0.0,  # Free for MVP
            rating=4.5,  # Placeholder - would come from actual ratings
            reviews=42,  # Placeholder - would come from actual reviews
            author=agent.created_by,
            created_at=agent.created_at,
            version=latest_version.version if latest_version else 1,
            compatible=True,  # Assume compatible for MVP
            installed=False,  # Will be determined by user's organization
            tools=agent.tools,
            requirements=[]  # Placeholder for requirements
        ))

    return MarketplaceAgentList(
        agents=marketplace_agents,
        total=total,
        page=page,
        size=size
    )

@router.get("/agents/{agent_id}", response_model=MarketplaceAgent)
async def get_marketplace_agent(
    agent_id: str,
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific marketplace agent."""
    agent = db.query(Agent).filter_by(id=agent_id, status="active").first()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Get basic metrics for display
    tasks = db.query(Task).filter_by(agent_id=agent_id).all()
    total_tasks = len(tasks)
    completed_tasks = len([t for t in tasks if t.status == "completed"])
    failed_tasks = len([t for t in tasks if t.status == "failed"])
    success_rate = completed_tasks / total_tasks if total_tasks > 0 else 0

    # Get latest version
    latest_version = db.query(AgentVersion).filter_by(agent_id=agent_id).order_by(
        AgentVersion.version.desc()
    ).first()

    return MarketplaceAgent(
        id=agent.id,
        name=agent.name,
        description=agent.instructions,
        category=agent.role.lower(),
        price=0.0,  # Free for MVP
        rating=4.5,  # Placeholder - would come from actual ratings
        reviews=42,  # Placeholder - would come from actual reviews
        author=agent.created_by,
        created_at=agent.created_at,
        version=latest_version.version if latest_version else 1,
        compatible=True,  # Assume compatible for MVP
        installed=False,  # Will be determined by user's organization
        tools=agent.tools,
        requirements=[]  # Placeholder for requirements
    )

@router.post("/agents/{agent_id}/install")
async def install_marketplace_agent(
    agent_id: str,
    organization_id: str = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """Install a marketplace agent to the current organization."""
    # Get the marketplace agent
    agent = db.query(Agent).filter_by(id=agent_id, status="active").first()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Check if already installed in this organization
    existing_agent = db.query(Agent).filter_by(
        id=agent_id,
        organization_id=organization_id
    ).first()

    if existing_agent:
        raise HTTPException(status_code=400, detail="Agent already installed in this organization")

    # Create a copy of the agent for this organization
    new_agent = Agent(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        name=agent.name,
        role=agent.role,
        instructions=agent.instructions,
        model=agent.model,
        tools=agent.tools,
        config=agent.config,
        status="active",
        version=agent.version,
        created_by=get_current_user().id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    db.add(new_agent)
    db.commit()

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"message": "Agent installed successfully", "agent_id": new_agent.id}
    )

@router.get("/featured", response_model=MarketplaceAgentList)
async def get_featured_agents(
    size: int = 8,
    db: Session = Depends(get_db)
):
    """Get featured agents for homepage."""
    # For MVP, return top-rated agents
    agents_query = db.query(Agent).filter_by(status="active")

    # Sort by some criteria (for now, just take first N)
    agents = agents_query.order_by(Agent.created_at.desc()).limit(size).all()

    marketplace_agents = []
    for agent in agents:
        marketplace_agents.append(MarketplaceAgent(
            id=agent.id,
            name=agent.name,
            description=agent.instructions[:100] + "..." if len(agent.instructions) > 100 else agent.instructions,
            category=agent.role.lower(),
            price=0.0,
            rating=4.5,  # Placeholder
            reviews=42,  # Placeholder
            author=agent.created_by,
            created_at=agent.created_at,
            version=1,  # Placeholder
            compatible=True,
            installed=False,
            tools=agent.tools,
            requirements=[]
        ))

    return MarketplaceAgentList(
        agents=marketplace_agents,
        total=len(marketplace_agents),
        page=1,
        size=size
    )

@router.get("/categories", response_model=List[Dict[str, Any]])
async def get_marketplace_categories(
    db: Session = Depends(get_db)
):
    """Get available agent categories."""
    # Get distinct categories from active agents
    categories = db.query(Agent.role).filter_by(status="active").distinct().all()

    return [{"id": cat[0].lower(), "name": cat[0]} for cat in categories]