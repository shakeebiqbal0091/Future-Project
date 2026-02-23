from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List, Optional

from ..shared.database import get_db
from ..shared.security import get_current_active_user, get_current_active_superuser
from ..shared.models import User, OrganizationMember, Agent, Workflow, Task
from ..shared.schemas import (
    User, UserCreate, UserUpdate, Organization, OrganizationMember,
    Pagination, PaginatedResponse
)
from ..shared.utils import (
    paginate_query, create_paginated_response,
    filter_by_organization, get_user_organizations
)

router = APIRouter()


@router.get("/", response_model=List[User])
def get_users(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    pagination: Pagination = Depends()
):
    """Get all users (admin only)."""

    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can access this endpoint"
        )

    query = db.query(User)
    paginated_query, total_count = paginate_query(db, query, pagination)
    items = paginated_query.all()

    return create_paginated_response(items, total_count, pagination)


@router.get("/{user_id}", response_model=User)
def get_user(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user by ID."""

    # Allow users to view their own profile or admin to view any profile
    if current_user.id != user_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own profile"
        )

    db_user = db.query(User).filter(User.id == user_id).first()

    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return User.from_orm(db_user)


@router.put("/{user_id}", response_model=User)
def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update user (admin only or self-update)."""

    db_user = db.query(User).filter(User.id == user_id).first()

    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Only superuser can update other users, or user can update themselves
    if current_user.id != user_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own profile"
        )

    if user_update.email:
        # Check if email is already taken by another user
        existing_user = db.query(User).filter(
            User.email == user_update.email,
            User.id != user_id
        ).first()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use"
            )

        db_user.email = user_update.email

    if user_update.username:
        # Check if username is already taken by another user
        existing_user = db.query(User).filter(
            User.username == user_update.username,
            User.id != user_id
        ).first()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already in use"
            )

        db_user.username = user_update.username

    if user_update.full_name:
        db_user.full_name = user_update.full_name

    if user_update.password:
        db_user.hashed_password = hash_password(user_update.password)

    if current_user.is_superuser:
        # Superuser can update additional fields
        if hasattr(user_update, 'is_active') and user_update.is_active is not None:
            db_user.is_active = user_update.is_active
        if hasattr(user_update, 'is_superuser') and user_update.is_superuser is not None:
            db_user.is_superuser = user_update.is_superuser

    db.commit()
    db.refresh(db_user)

    return User.from_orm(db_user)


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete user (admin only)."""

    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can delete users"
        )

    db_user = db.query(User).filter(User.id == user_id).first()

    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Soft delete - mark as inactive
    db_user.is_active = False
    db.commit()

    return {"message": "User deactivated successfully"}


@router.get("/{user_id}/organizations", response_model=List[Organization])
def get_user_organizations_endpoint(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get organizations for a specific user."""

    # Allow users to view their own organizations or admin to view any user's organizations
    if current_user.id != user_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own organizations"
        )

    return get_user_organizations(db, user_id)


@router.get("/{user_id}/agents", response_model=List[User])
def get_user_agents(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    pagination: Pagination = Depends()
):
    """Get agents created by a user."""

    # Allow users to view their own agents or admin to view any user's agents
    if current_user.id != user_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own agents"
        )

    # Get organizations the user belongs to
    user_organizations = get_user_organizations(db, user_id)
    organization_ids = [org.id for org in user_organizations]

    from ..shared.models import Agent
    query = db.query(Agent).filter(
        Agent.creator_id == user_id,
        Agent.organization_id.in_(organization_ids)
    )

    paginated_query, total_count = paginate_query(db, query, pagination)
    items = paginated_query.all()

    return create_paginated_response(items, total_count, pagination)


@router.get("/{user_id}/workflows", response_model=List[Workflow])
def get_user_workflows(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    pagination: Pagination = Depends()
):
    """Get workflows created by a user."""

    # Allow users to view their own workflows or admin to view any user's workflows
    if current_user.id != user_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own workflows"
        )

    # Get organizations the user belongs to
    user_organizations = get_user_organizations(db, user_id)
    organization_ids = [org.id for org in user_organizations]

    from ..shared.models import Workflow
    query = db.query(Workflow).filter(
        Workflow.creator_id == user_id,
        Workflow.organization_id.in_(organization_ids)
    )

    paginated_query, total_count = paginate_query(db, query, pagination)
    items = paginated_query.all()

    return create_paginated_response(items, total_count, pagination)


@router.get("/{user_id}/tasks", response_model=List[Task])
def get_user_tasks(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    pagination: Pagination = Depends()
):
    """Get tasks created by a user."""

    # Allow users to view their own tasks or admin to view any user's tasks
    if current_user.id != user_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own tasks"
        )

    # Get organizations the user belongs to
    user_organizations = get_user_organizations(db, user_id)
    organization_ids = [org.id for org in user_organizations]

    from ..shared.models import Task
    query = db.query(Task).filter(
        Task.creator_id == user_id,
        Task.organization_id.in_(organization_ids)
    )

    paginated_query, total_count = paginate_query(db, query, pagination)
    items = paginated_query.all()

    return create_paginated_response(items, total_count, pagination)


@router.get("/{user_id}/stats", response_model=dict)
def get_user_stats(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user statistics."""

    # Allow users to view their own stats or admin to view any user's stats
    if current_user.id != user_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own statistics"
        )

    from ..shared.models import Agent, Workflow, Task

    # Get organizations the user belongs to
    user_organizations = get_user_organizations(db, user_id)
    organization_ids = [org.id for org in user_organizations]

    agent_count = db.query(Agent).filter(
        Agent.creator_id == user_id,
        Agent.organization_id.in_(organization_ids)
    ).count()

    workflow_count = db.query(Workflow).filter(
        Workflow.creator_id == user_id,
        Workflow.organization_id.in_(organization_ids)
    ).count()

    task_count = db.query(Task).filter(
        Task.creator_id == user_id,
        Task.organization_id.in_(organization_ids)
    ).count()

    return {
        "user": {
            "id": user_id,
            "username": current_user.username
        },
        "stats": {
            "agents": agent_count,
            "workflows": workflow_count,
            "tasks": task_count,
            "total_entities": agent_count + workflow_count + task_count
        }
    }


@router.get("/me/stats", response_model=dict)
def get_current_user_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current user's statistics."""

    return get_user_stats(current_user.id, current_user, db)