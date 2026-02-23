from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from typing import List

from ..shared.database import get_db
from ..shared.security import get_current_active_user, get_current_active_superuser
from ..shared.models import User, Organization, Agent, Workflow, Task
from ..shared.schemas import (
    User, Organization, Agent, Workflow, Task,
    Pagination, PaginatedResponse
)
from ..shared.utils import (
    paginate_query, create_paginated_response,
    filter_by_organization
)

router = APIRouter()


@router.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": __import__("datetime").datetime.now().isoformat()}


@router.get("/ping")
def ping():
    return {"message": "pong"}


@router.get("/version")
def get_version():
    return {"version": "1.0.0", "api": "AI Agent Orchestration Platform"}


@router.get("/me", response_model=User)
def get_current_user_profile(current_user: User = Depends(get_current_active_user)):
    """Get current user's profile."""
    return current_user


@router.get("/me/organizations", response_model=List[Organization])
def get_user_organizations(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all organizations the user belongs to."""
    from ..shared.utils import get_user_organizations
    return get_user_organizations(db, current_user.id)


@router.get("/organizations/{organization_id}/stats", response_model=dict)
def get_organization_stats(
    organization_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get organization statistics."""
    # Filter by organization and user permissions
    query = db.query(Organization).filter(Organization.id == organization_id)
    query = filter_by_organization(db, query, organization_id, current_user)
    organization = query.first()

    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Get stats
    from ..shared.models import Agent, Workflow, Task

    agent_count = db.query(Agent).filter(
        Agent.organization_id == organization_id
    ).count()

    workflow_count = db.query(Workflow).filter(
        Workflow.organization_id == organization_id
    ).count()

    task_count = db.query(Task).filter(
        Task.organization_id == organization_id
    ).count()

    return {
        "organization": {
            "id": organization.id,
            "name": organization.name,
            "slug": organization.slug
        },
        "stats": {
            "agents": agent_count,
            "workflows": workflow_count,
            "tasks": task_count,
            "total_entities": agent_count + workflow_count + task_count
        }
    }


@router.get("/search", response_model=PaginatedResponse)
def search(
    q: str,
    entity_type: Optional[str] = None,
    organization_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    pagination: Pagination = Depends()
):
    """Search across entities."""
    from sqlalchemy import or_

    # Build base query based on entity type
    if entity_type == "user":
        from ..shared.models import User
        query = db.query(User)
        query = query.filter(or_(
            User.email.ilike(f"%{q}%"),
            User.username.ilike(f"%{q}%"),
            User.full_name.ilike(f"%{q}%")
        ))
    elif entity_type == "agent":
        from ..shared.models import Agent
        query = db.query(Agent)
        query = query.filter(or_(
            Agent.name.ilike(f"%{q}%"),
            Agent.description.ilike(f"%{q}%")
        ))
    elif entity_type == "workflow":
        from ..shared.models import Workflow
        query = db.query(Workflow)
        query = query.filter(or_(
            Workflow.name.ilike(f"%{q}%"),
            Workflow.description.ilike(f"%{q}%")
        ))
    elif entity_type == "task":
        from ..shared.models import Task
        query = db.query(Task)
        query = query.filter(or_(
            Task.name.ilike(f"%{q}%"),
            Task.description.ilike(f"%{q}%")
        ))
    else:
        # Search across all entities
        from sqlalchemy import union_all
        from ..shared.models import User, Agent, Workflow, Task

        user_query = db.query(
            User.id.label('id'),
            User.email.label('name'),
            User.full_name.label('description'),
            func.literal('user').label('type')
        ).filter(or_(
            User.email.ilike(f"%{q}%"),
            User.username.ilike(f"%{q}%"),
            User.full_name.ilike(f"%{q}%")
        ))

        agent_query = db.query(
            Agent.id.label('id'),
            Agent.name.label('name'),
            Agent.description.label('description'),
            func.literal('agent').label('type')
        ).filter(or_(
            Agent.name.ilike(f"%{q}%"),
            Agent.description.ilike(f"%{q}%")
        ))

        workflow_query = db.query(
            Workflow.id.label('id'),
            Workflow.name.label('name'),
            Workflow.description.label('description'),
            func.literal('workflow').label('type')
        ).filter(or_(
            Workflow.name.ilike(f"%{q}%"),
            Workflow.description.ilike(f"%{q}%")
        ))

        task_query = db.query(
            Task.id.label('id'),
            Task.name.label('name'),
            Task.description.label('description'),
            func.literal('task').label('type')
        ).filter(or_(
            Task.name.ilike(f"%{q}%"),
            Task.description.ilike(f"%{q}%")
        ))

        query = union_all(user_query, agent_query, workflow_query, task_query)

    # Filter by organization if specified
    if organization_id:
        from ..shared.models import Organization
        query = query.filter(Organization.id == organization_id)

    # Apply pagination
    paginated_query, total_count = paginate_query(db, query, pagination)
    items = paginated_query.all()

    return create_paginated_response(items, total_count, pagination)


@router.get("/activity", response_model=List[dict])
def get_recent_activity(
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get recent activity across the platform."""
    from sqlalchemy import union_all
    from ..shared.models import Task, Workflow, Agent

    # Recent tasks
    task_activity = db.query(
        Task.id.label('id'),
        Task.name.label('name'),
        Task.status.label('status'),
        Task.created_at.label('timestamp'),
        func.literal('task').label('type')
    ).order_by(Task.created_at.desc()).limit(limit)

    # Recent workflows
    workflow_activity = db.query(
        Workflow.id.label('id'),
        Workflow.name.label('name'),
        Workflow.status.label('status'),
        Workflow.created_at.label('timestamp'),
        func.literal('workflow').label('type')
    ).order_by(Workflow.created_at.desc()).limit(limit)

    # Recent agents
    agent_activity = db.query(
        Agent.id.label('id'),
        Agent.name.label('name'),
        func.literal('active').label('status'),
        Agent.created_at.label('timestamp'),
        func.literal('agent').label('type')
    ).order_by(Agent.created_at.desc()).limit(limit)

    # Combine and get most recent
    activity = union_all(task_activity, workflow_activity, agent_activity)
    activity = activity.order_by(desc('timestamp')).limit(limit).all()

    return [dict(row) for row in activity]