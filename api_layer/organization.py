from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List, Optional

from ..shared.database import get_db
from ..shared.security import get_current_active_user, get_current_active_superuser, get_current_organization_member
from ..shared.models import User, Organization, OrganizationMember, Agent, Workflow, Task
from ..shared.schemas import (
    Organization, OrganizationCreate, OrganizationUpdate, OrganizationMember,
    User, Pagination, PaginatedResponse
)
from ..shared.utils import (
    paginate_query, create_paginated_response,
    filter_by_organization, get_user_organizations
)

router = APIRouter()


@router.get("/", response_model=List[Organization])
def get_organizations(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    pagination: Pagination = Depends()
):
    """Get all organizations the user belongs to."""

    # Get organizations the user belongs to
    user_organizations = get_user_organizations(db, current_user.id)
    organization_ids = [org.id for org in user_organizations]

    query = db.query(Organization).filter(
        Organization.id.in_(organization_ids)
    )

    paginated_query, total_count = paginate_query(db, query, pagination)
    items = paginated_query.all()

    return create_paginated_response(items, total_count, pagination)


@router.post("/", response_model=Organization)
def create_organization(
    organization_data: OrganizationCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Create a new organization."""

    # Create organization
    organization_slug = create_slug(organization_data.slug)
    organization = Organization(
        name=organization_data.name,
        slug=organization_slug,
        description=organization_data.description,
        is_active=True
    )

    db.add(organization)
    db.commit()

    # Add current user as owner
    member = OrganizationMember(
        user_id=current_user.id,
        organization_id=organization.id,
        role="owner"
    )
    db.add(member)
    db.commit()
    db.refresh(organization)

    return Organization.from_orm(organization)


@router.get("/{organization_id}", response_model=Organization)
def get_organization(
    organization_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get organization by ID."""

    # Verify user has access to this organization
    org_query = db.query(Organization).filter(Organization.id == organization_id)
    org_query = filter_by_organization(db, org_query, organization_id, current_user)
    organization = org_query.first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found or access denied"
        )

    return Organization.from_orm(organization)


@router.put("/{organization_id}", response_model=Organization)
def update_organization(
    organization_id: int,
    organization_update: OrganizationUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update organization."""

    # Verify user has access to this organization
    org_query = db.query(Organization).filter(Organization.id == organization_id)
    org_query = filter_by_organization(db, org_query, organization_id, current_user)
    organization = org_query.first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found or access denied"
        )

    # Check if user is member of this organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == organization_id
    ).first()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this organization"
        )

    # Only owners and admins can update organization
    if member.role not in ["owner", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owners and admins can update organization settings"
        )

    if organization_update.name:
        organization.name = organization_update.name

    if organization_update.description:
        organization.description = organization_update.description

    db.commit()
    db.refresh(organization)

    return Organization.from_orm(organization)


@router.delete("/{organization_id}")
def delete_organization(
    organization_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete organization (only if user is owner)."""

    # Verify user has access to this organization
    org_query = db.query(Organization).filter(Organization.id == organization_id)
    org_query = filter_by_organization(db, org_query, organization_id, current_user)
    organization = org_query.first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found or access denied"
        )

    # Check if user is owner of this organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.role == "owner"
    ).first()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owners can delete the organization"
        )

    # Soft delete - mark as inactive
    organization.is_active = False
    db.commit()

    return {"message": "Organization deactivated successfully"}


@router.get("/{organization_id}/members", response_model=List[OrganizationMember])
def get_organization_members_endpoint(
    organization_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get members of an organization."""

    # Verify user has access to this organization
    org_query = db.query(Organization).filter(Organization.id == organization_id)
    org_query = filter_by_organization(db, org_query, organization_id, current_user)
    organization = org_query.first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found or access denied"
        )

    # Check if user is member of this organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == organization_id
    ).first()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this organization"
        )

    # Get all members
    members = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == organization_id
    ).all()

    # Include user details
    from ..shared.models import User
    for member in members:
        member.user = db.query(User).filter(User.id == member.user_id).first()

    return members


@router.post("/{organization_id}/members", response_model=OrganizationMember)
def add_organization_member(
    organization_id: int,
    member_data: OrganizationMember,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Add member to organization."""

    # Verify user has access to this organization
    org_query = db.query(Organization).filter(Organization.id == organization_id)
    org_query = filter_by_organization(db, org_query, organization_id, current_user)
    organization = org_query.first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found or access denied"
        )

    # Check if user is owner of this organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.role == "owner"
    ).first()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owners can add members"
        )

    # Check if user already exists in organization
    existing_member = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == member_data.user_id,
        OrganizationMember.organization_id == organization_id
    ).first()

    if existing_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this organization"
        )

    # Check if user exists
    db_user = db.query(User).filter(User.id == member_data.user_id).first()

    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Create new member
    new_member = OrganizationMember(
        user_id=member_data.user_id,
        organization_id=organization_id,
        role=member_data.role
    )

    db.add(new_member)
    db.commit()

    # Include user details
    new_member.user = db_user

    return new_member


@router.put("/{organization_id}/members/{user_id}", response_model=OrganizationMember)
def update_organization_member(
    organization_id: int,
    user_id: int,
    member_update: OrganizationMember,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update organization member (only owner can update)."""

    # Verify user has access to this organization
    org_query = db.query(Organization).filter(Organization.id == organization_id)
    org_query = filter_by_organization(db, org_query, organization_id, current_user)
    organization = org_query.first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found or access denied"
        )

    # Check if user is owner of this organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.role == "owner"
    ).first()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owners can update members"
        )

    # Get the member to update
    db_member = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user_id,
        OrganizationMember.organization_id == organization_id
    ).first()

    if not db_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found in organization"
        )

    # Owners cannot change their own role
    if db_member.user_id == current_user.id and member_update.role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot change your own role"
        )

    db_member.role = member_update.role
    db.commit()

    # Include user details
    db_member.user = db.query(User).filter(User.id == user_id).first()

    return db_member


@router.delete("/{organization_id}/members/{user_id}")
def remove_organization_member(
    organization_id: int,
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Remove member from organization."""

    # Verify user has access to this organization
    org_query = db.query(Organization).filter(Organization.id == organization_id)
    org_query = filter_by_organization(db, org_query, organization_id, current_user)
    organization = org_query.first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found or access denied"
        )

    # Check if user is owner of this organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.role == "owner"
    ).first()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owners can remove members"
        )

    # Get the member to remove
    db_member = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user_id,
        OrganizationMember.organization_id == organization_id
    ).first()

    if not db_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found in organization"
        )

    # Owners cannot remove themselves
    if db_member.user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot remove yourself from the organization"
        )

    db.delete(db_member)
    db.commit()

    return {"message": "Member removed successfully"}


@router.get("/{organization_id}/stats", response_model=dict)
def get_organization_stats_endpoint(
    organization_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get detailed organization statistics."""

    # Verify user has access to this organization
    org_query = db.query(Organization).filter(Organization.id == organization_id)
    org_query = filter_by_organization(db, org_query, organization_id, current_user)
    organization = org_query.first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found or access denied"
        )

    from ..shared.models import Agent, Workflow, Task

    # Basic stats
    agent_count = db.query(Agent).filter(
        Agent.organization_id == organization_id
    ).count()

    workflow_count = db.query(Workflow).filter(
        Workflow.organization_id == organization_id
    ).count()

    task_count = db.query(Task).filter(
        Task.organization_id == organization_id
    ).count()

    # Member stats
    total_members = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == organization_id
    ).count()

    owner_count = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.role == "owner"
    ).count()

    admin_count = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.role == "admin"
    ).count()

    member_count = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.role == "member"
    ).count()

    return {
        "organization": {
            "id": organization.id,
            "name": organization.name,
            "slug": organization.slug
        },
        "entity_counts": {
            "agents": agent_count,
            "workflows": workflow_count,
            "tasks": task_count,
            "total_entities": agent_count + workflow_count + task_count
        },
        "member_stats": {
            "total_members": total_members,
            "owners": owner_count,
            "admins": admin_count,
            "members": member_count
        },
        "active_status": organization.is_active
    }


@router.get("/{organization_id}/usage", response_model=dict)
def get_organization_usage(
    organization_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get organization usage statistics."""

    # Verify user has access to this organization
    org_query = db.query(Organization).filter(Organization.id == organization_id)
    org_query = filter_by_organization(db, org_query, organization_id, current_user)
    organization = org_query.first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found or access denied"
        )

    # In a real implementation, you would query usage metrics
    # For now, we'll return sample data

    return {
        "organization": {
            "id": organization.id,
            "name": organization.name
        },
        "usage": {
            "total_tasks": 1234,
            "completed_tasks": 1100,
            "failed_tasks": 134,
            "average_execution_time": 2.5,  # in seconds
            "token_usage": 567890,
            "cost_estimate": "$123.45"
        },
        "recent_activity": {
            "last_7d_tasks": 234,
            "last_30d_tasks": 890,
            "active_agents": 5,
            "active_workflows": 12
        }
    }


@router.get("/{organization_id}/agents", response_model=List[Agent])
def get_organization_agents(
    organization_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    pagination: Pagination = Depends()
):
    """Get all agents in an organization."""

    # Verify user has access to this organization
    org_query = db.query(Organization).filter(Organization.id == organization_id)
    org_query = filter_by_organization(db, org_query, organization_id, current_user)
    organization = org_query.first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found or access denied"
        )

    from ..shared.models import Agent
    query = db.query(Agent).filter(
        Agent.organization_id == organization_id
    )

    paginated_query, total_count = paginate_query(db, query, pagination)
    items = paginated_query.all()

    return create_paginated_response(items, total_count, pagination)


@router.get("/{organization_id}/workflows", response_model=List[Workflow])
def get_organization_workflows(
    organization_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    pagination: Pagination = Depends()
):
    """Get all workflows in an organization."""

    # Verify user has access to this organization
    org_query = db.query(Organization).filter(Organization.id == organization_id)
    org_query = filter_by_organization(db, org_query, organization_id, current_user)
    organization = org_query.first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found or access denied"
        )

    from ..shared.models import Workflow
    query = db.query(Workflow).filter(
        Workflow.organization_id == organization_id
    )

    paginated_query, total_count = paginate_query(db, query, pagination)
    items = paginated_query.all()

    return create_paginated_response(items, total_count, pagination)


@router.get("/{organization_id}/tasks", response_model=List[Task])
def get_organization_tasks(
    organization_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    pagination: Pagination = Depends()
):
    """Get all tasks in an organization."""

    # Verify user has access to this organization
    org_query = db.query(Organization).filter(Organization.id == organization_id)
    org_query = filter_by_organization(db, org_query, organization_id, current_user)
    organization = org_query.first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found or access denied"
        )

    from ..shared.models import Task
    query = db.query(Task).filter(
        Task.organization_id == organization_id
    )

    paginated_query, total_count = paginate_query(db, query, pagination)
    items = paginated_query.all()

    return create_paginated_response(items, total_count, pagination)


@router.get("/{organization_id}/activity", response_model=List[dict])
def get_organization_activity(
    organization_id: int,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get recent activity in an organization."""

    # Verify user has access to this organization
    org_query = db.query(Organization).filter(Organization.id == organization_id)
    org_query = filter_by_organization(db, org_query, organization_id, current_user)
    organization = org_query.first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found or access denied"
        )

    from sqlalchemy import union_all
    from ..shared.models import Task, Workflow, Agent

    # Recent tasks
    task_activity = db.query(
        Task.id.label('id'),
        Task.name.label('name'),
        Task.status.label('status'),
        Task.created_at.label('timestamp'),
        func.literal('task').label('type')
    ).filter(Task.organization_id == organization_id)
    .order_by(Task.created_at.desc()).limit(limit)

    # Recent workflows
    workflow_activity = db.query(
        Workflow.id.label('id'),
        Workflow.name.label('name'),
        Workflow.status.label('status'),
        Workflow.created_at.label('timestamp'),
        func.literal('workflow').label('type')
    ).filter(Workflow.organization_id == organization_id)
    .order_by(Workflow.created_at.desc()).limit(limit)

    # Recent agents
    agent_activity = db.query(
        Agent.id.label('id'),
        Agent.name.label('name'),
        func.literal('active').label('status'),
        Agent.created_at.label('timestamp'),
        func.literal('agent').label('type')
    ).filter(Agent.organization_id == organization_id)
    .order_by(Agent.created_at.desc()).limit(limit)

    # Combine and get most recent
    activity = union_all(task_activity, workflow_activity, agent_activity)
    activity = activity.order_by(desc('timestamp')).limit(limit).all()

    return [dict(row) for row in activity]