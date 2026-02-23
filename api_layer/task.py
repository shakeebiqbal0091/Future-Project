from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import datetime
import json

from ..shared.database import get_db
from ..shared.security import get_current_active_user, get_current_active_superuser, get_current_organization_member
from ..shared.models import User, Organization, Agent, Workflow, Task
from ..shared.schemas import (
    Task, TaskCreate, TaskUpdate, User, Workflow, Agent,
    Pagination, PaginatedResponse, WebSocketMessage
)
from ..shared.utils import (
    paginate_query, create_paginated_response,
    filter_by_organization, get_user_organizations
)

router = APIRouter()


@router.get("/", response_model=List[Task])
def get_tasks(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    organization_id: Optional[int] = None,
    status: Optional[str] = None,
    workflow_id: Optional[int] = None,
    pagination: Pagination = Depends()
):
    """Get all tasks with filtering options."""

    # Build base query
    query = db.query(Task)

    # Filter by organization if specified
    if organization_id:
        org_query = db.query(Organization).filter(Organization.id == organization_id)
        org_query = filter_by_organization(db, org_query, organization_id, current_user)
        organization = org_query.first()
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found or access denied"
            )

        query = query.filter(Task.organization_id == organization_id)
    else:
        # Get tasks for all organizations the user belongs to
        user_organizations = get_user_organizations(db, current_user.id)
        organization_ids = [org.id for org in user_organizations]
        query = query.filter(Task.organization_id.in_(organization_ids))

    # Filter by status
    if status:
        query = query.filter(Task.status == status)

    # Filter by workflow
    if workflow_id:
        query = query.filter(Task.workflow_id == workflow_id)

    # Order by creation date (newest first)
    query = query.order_by(Task.created_at.desc())

    paginated_query, total_count = paginate_query(db, query, pagination)
    items = paginated_query.all()

    return create_paginated_response(items, total_count, pagination)


@router.post("/", response_model=Task)
def create_task(
    task_data: TaskCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Create a new task."""

    # Verify user belongs to the specified organization
    org_query = db.query(Organization).filter(Organization.id == task_data.organization_id)
    org_query = filter_by_organization(db, org_query, task_data.organization_id, current_user)
    organization = org_query.first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found or access denied"
        )

    # Check if user is member of this organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == task_data.organization_id
    ).first()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this organization"
        )

    # Validate workflow if specified
    if task_data.workflow_id:
        workflow = db.query(Workflow).filter(Workflow.id == task_data.workflow_id).first()
        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )

        # Verify workflow belongs to the same organization
        if workflow.organization_id != task_data.organization_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Workflow must belong to the same organization as the task"
            )

        # Verify workflow is active
        if workflow.status != "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Workflow is not active and cannot be used for task creation"
            )

    # Create task
    task = Task(
        name=task_data.name,
        description=task_data.description,
        input_data=task_data.input_data,
        status="pending",
        organization_id=task_data.organization_id,
        workflow_id=task_data.workflow_id,
        creator_id=current_user.id
    )

    db.add(task)
    db.commit()
    db.refresh(task)

    return Task.from_orm(task)


@router.get("/{task_id}", response_model=Task)
def get_task(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get task by ID."""

    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Verify user has access to this task's organization
    org_query = db.query(Organization).filter(Organization.id == task.organization_id)
    org_query = filter_by_organization(db, org_query, task.organization_id, current_user)
    organization = org_query.first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found or access denied"
        )

    return Task.from_orm(task)


@router.put("/{task_id}", response_model=Task)
def update_task(
    task_id: int,
    task_update: TaskUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update task."""

    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Verify user has access to this task's organization
    org_query = db.query(Organization).filter(Organization.id == task.organization_id)
    org_query = filter_by_organization(db, org_query, task.organization_id, current_user)
    organization = org_query.first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found or access denied"
        )

    # Check if user is member of this organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == task.organization_id
    ).first()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this organization"
        )

    # Only owners and admins can update tasks, or the task creator can update their own tasks
    if member.role not in ["owner", "admin"] and current_user.id != task.creator_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owners, admins, or task creators can update tasks"
        )

    if task_update.name:
        task.name = task_update.name

    if task_update.description:
        task.description = task_update.description

    if task_update.input_data is not None:
        task.input_data = task_update.input_data

    if task_update.status is not None:
        # Validate status transition
        valid_transitions = {
            "pending": ["running", "failed"],
            "running": ["completed", "failed"],
            "completed": [],
            "failed": []
        }

        if task_update.status not in valid_transitions.get(task.status, []):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status transition from {task.status} to {task_update.status}"
            )

        task.status = task_update.status

        # Reset error message when task succeeds
        if task_update.status == "completed":
            task.error_message = None

    db.commit()
    db.refresh(task)

    return Task.from_orm(task)


@router.delete("/{task_id}")
def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete task."""

    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Verify user has access to this task's organization
    org_query = db.query(Organization).filter(Organization.id == task.organization_id)
    org_query = filter_by_organization(db, org_query, task.organization_id, current_user)
    organization = org_query.first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found or access denied"
        )

    # Check if user is member of this organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == task.organization_id
    ).first()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this organization"
        )

    # Only owners and admins can delete tasks, or the task creator can delete their own tasks
    if member.role not in ["owner", "admin"] and current_user.id != task.creator_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owners, admins, or task creators can delete tasks"
        )

    # Cannot delete running tasks
    if task.status == "running":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a running task"
        )

    db.delete(task)
    db.commit()

    return {"message": "Task deleted successfully"}


@router.post("/{task_id}/execute")
def execute_task(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Execute a task."""

    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Verify user has access to this task's organization
    org_query = db.query(Organization).filter(Organization.id == task.organization_id)
    org_query = filter_by_organization(db, org_query, task.organization_id, current_user)
    organization = org_query.first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found or access denied"
        )

    # Check if user is member of this organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == task.organization_id
    ).first()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this organization"
        )

    # Only owners, admins, and task creators can execute tasks
    if member.role not in ["owner", "admin"] and current_user.id != task.creator_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owners, admins, or task creators can execute tasks"
        )

    # Cannot execute a task that's already running or completed
    if task.status in ["running", "completed", "failed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot execute task in {task.status} state"
        )

    # In a real implementation, you would:
    # 1. Validate the task input data
    # 2. Create a job in the task queue
    # 3. Update task status to running
    # For now, we'll just update the status

    task.status = "running"
    task.updated_at = datetime.datetime.now()
    db.commit()

    # Simulate task execution (in real implementation, this would be async)
    # This is just a placeholder for demonstration
    try:
        # Simulate some processing
        import time
        time.sleep(2)  # Simulate processing time

        # For demonstration, let's assume the task succeeds
        task.status = "completed"
        task.output_data = {"result": "Task completed successfully"}
        task.execution_time = 2.5  # in seconds

    except Exception as e:
        task.status = "failed"
        task.error_message = str(e)

    task.updated_at = datetime.datetime.now()
    db.commit()

    return Task.from_orm(task)


@router.get("/{task_id}/logs", response_model=List[Dict[str, Any]])
def get_task_logs(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get task execution logs."""

    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Verify user has access to this task's organization
    org_query = db.query(Organization).filter(Organization.id == task.organization_id)
    org_query = filter_by_organization(db, org_query, task.organization_id, current_user)
    organization = org_query.first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found or access denied"
        )

    # In a real implementation, you would retrieve logs from a logging system
    # For now, we'll return sample logs based on task status

    logs = []

    if task.status == "completed":
        logs = [
            {
                "timestamp": task.created_at.isoformat(),
                "level": "INFO",
                "message": f"Task '{task.name}' started successfully"
            },
            {
                "timestamp": (task.created_at + datetime.timedelta(seconds=1)).isoformat(),
                "level": "INFO",
                "message": f"Processing input data: {json.dumps(task.input_data, indent=2)}"
            },
            {
                "timestamp": (task.created_at + datetime.timedelta(seconds=2)).isoformat(),
                "level": "INFO",
                "message": f"Task completed successfully"
            }
        ]
    elif task.status == "failed":
        logs = [
            {
                "timestamp": task.created_at.isoformat(),
                "level": "INFO",
                "message": f"Task '{task.name}' started successfully"
            },
            {
                "timestamp": (task.created_at + datetime.timedelta(seconds=1)).isoformat(),
                "level": "ERROR",
                "message": f"Task failed: {task.error_message}"
            }
        ]
    else:
        logs = [
            {
                "timestamp": task.created_at.isoformat(),
                "level": "INFO",
                "message": f"Task '{task.name}' is {task.status}"
            }
        ]

    return logs


@router.get("/{task_id}/output", response_model=Dict[str, Any])
def get_task_output(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get task execution output."""

    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Verify user has access to this task's organization
    org_query = db.query(Organization).filter(Organization.id == task.organization_id)
    org_query = filter_by_organization(db, org_query, task.organization_id, current_user)
    organization = org_query.first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found or access denied"
        )

    if not task.output_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No output data available"
        )

    return task.output_data


@router.get("/{task_id}/details", response_model=Dict[str, Any])
def get_task_details(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get detailed task information including related entities."""

    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Verify user has access to this task's organization
    org_query = db.query(Organization).filter(Organization.id == task.organization_id)
    org_query = filter_by_organization(db, org_query, task.organization_id, current_user)
    organization = org_query.first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found or access denied"
        )

    # Get related entities
    workflow = None
    if task.workflow_id:
        workflow = db.query(Workflow).filter(Workflow.id == task.workflow_id).first()

    creator = db.query(User).filter(User.id == task.creator_id).first()

    return {
        "task": {
            "id": task.id,
            "name": task.name,
            "description": task.description,
            "status": task.status,
            "input_data": task.input_data,
            "output_data": task.output_data,
            "error_message": task.error_message,
            "execution_time": task.execution_time,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat()
        },
        "organization": {
            "id": organization.id,
            "name": organization.name,
            "slug": organization.slug
        },
        "workflow": {
            "id": workflow.id if workflow else None,
            "name": workflow.name if workflow else None
        } if workflow else None,
        "creator": {
            "id": creator.id,
            "username": creator.username,
            "full_name": creator.full_name,
            "email": creator.email
        } if creator else None
    }


@router.get("/{task_id}/events", response_model=List[Dict[str, Any]])
def get_task_events(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get task lifecycle events."""

    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Verify user has access to this task's organization
    org_query = db.query(Organization).filter(Organization.id == task.organization_id)
    org_query = filter_by_organization(db, org_query, task.organization_id, current_user)
    organization = org_query.first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found or access denied"
        )

    # In a real implementation, you would retrieve events from an event store
    # For now, we'll create sample events based on task status

    events = [
        {
            "event_id": f"event-{task_id}-created",
            "type": "task_created",
            "data": {
                "task_id": task.id,
                "name": task.name,
                "input_data": task.input_data
            },
            "timestamp": task.created_at.isoformat(),
            "user_id": task.creator_id
        }
    ]

    if task.status == "running":
        events.append({
            "event_id": f"event-{task_id}-started",
            "type": "task_started",
            "data": {},
            "timestamp": task.updated_at.isoformat(),
            "user_id": task.creator_id
        })
    elif task.status == "completed":
        events.extend([
            {
                "event_id": f"event-{task_id}-started",
                "type": "task_started",
                "data": {},
                "timestamp": task.created_at.isoformat(),
                "user_id": task.creator_id
            },
            {
                "event_id": f"event-{task_id}-completed",
                "type": "task_completed",
                "data": {
                    "execution_time": task.execution_time,
                    "output_data": task.output_data
                },
                "timestamp": task.updated_at.isoformat(),
                "user_id": task.creator_id
            }
        ])
    elif task.status == "failed":
        events.extend([
            {
                "event_id": f"event-{task_id}-started",
                "type": "task_started",
                "data": {},
                "timestamp": task.created_at.isoformat(),
                "user_id": task.creator_id
            },
            {
                "event_id": f"event-{task_id}-failed",
                "type": "task_failed",
                "data": {
                    "error_message": task.error_message
                },
                "timestamp": task.updated_at.isoformat(),
                "user_id": task.creator_id
            }
        ])

    return events


@router.get("/stats", response_model=Dict[str, Any])
def get_tasks_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get global task statistics."""

    # Get tasks for all organizations the user belongs to
    user_organizations = get_user_organizations(db, current_user.id)
    organization_ids = [org.id for org in user_organizations]

    from sqlalchemy import func

    # Get overall statistics
    total_tasks = db.query(Task).filter(
        Task.organization_id.in_(organization_ids)
    ).count()

    completed_tasks = db.query(Task).filter(
        Task.organization_id.in_(organization_ids),
        Task.status == "completed"
    ).count()

    failed_tasks = db.query(Task).filter(
        Task.organization_id.in_(organization_ids),
        Task.status == "failed"
    ).count()

    pending_tasks = db.query(Task).filter(
        Task.organization_id.in_(organization_ids),
        Task.status == "pending"
    ).count()

    running_tasks = db.query(Task).filter(
        Task.organization_id.in_(organization_ids),
        Task.status == "running"
    ).count()

    # Get execution time statistics
    avg_execution_time = db.query(func.avg(Task.execution_time)).filter(
        Task.organization_id.in_(organization_ids),
        Task.execution_time.is_not(None)
    ).scalar() or 0

    # Get recent activity
    recent_tasks = db.query(Task).filter(
        Task.organization_id.in_(organization_ids)
    ).order_by(Task.created_at.desc()).limit(5).all()

    return {
        "statistics": {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "pending_tasks": pending_tasks,
            "running_tasks": running_tasks,
            "success_rate": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
            "average_execution_time": avg_execution_time  # in seconds
        },
        "recent_activity": [{
            "task_id": task.id,
            "name": task.name,
            "status": task.status,
            "created_at": task.created_at.isoformat(),
            "organization_id": task.organization_id
        } for task in recent_tasks]
    }


@router.get("/{task_id}/related", response_model=Dict[str, Any])
def get_task_related_entities(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get related entities for a task."""

    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Verify user has access to this task's organization
    org_query = db.query(Organization).filter(Organization.id == task.organization_id)
    org_query = filter_by_organization(db, org_query, task.organization_id, current_user)
    organization = org_query.first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found or access denied"
        )

    # Get related entities
    related_entities = {
        "organization": {
            "id": organization.id,
            "name": organization.name,
            "slug": organization.slug
        },
        "workflow": None,
        "creator": None
    }

    if task.workflow_id:
        workflow = db.query(Workflow).filter(Workflow.id == task.workflow_id).first()
        if workflow:
            related_entities["workflow"] = {
                "id": workflow.id,
                "name": workflow.name,
                "status": workflow.status
            }

    creator = db.query(User).filter(User.id == task.creator_id).first()
    if creator:
        related_entities["creator"] = {
            "id": creator.id,
            "username": creator.username,
            "full_name": creator.full_name,
            "email": creator.email
        }

    return related_entities


@router.get("/export", response_model=List[Dict[str, Any]])
def export_tasks(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    status: Optional[str] = None,
    start_date: Optional[datetime.datetime] = None,
    end_date: Optional[datetime.datetime] = None
):
    """Export tasks data."""

    # Get tasks for all organizations the user belongs to
    user_organizations = get_user_organizations(db, current_user.id)
    organization_ids = [org.id for org in user_organizations]

    query = db.query(Task).filter(
        Task.organization_id.in_(organization_ids)
    )

    # Apply filters
    if status:
        query = query.filter(Task.status == status)

    if start_date:
        query = query.filter(Task.created_at >= start_date)

    if end_date:
        query = query.filter(Task.created_at <= end_date)

    tasks = query.all()

    # Prepare export data
    export_data = []
    for task in tasks:
        export_data.append({
            "task_id": task.id,
            "name": task.name,
            "description": task.description,
            "status": task.status,
            "input_data": task.input_data,
            "output_data": task.output_data,
            "error_message": task.error_message,
            "execution_time": task.execution_time,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
            "organization_id": task.organization_id,
            "workflow_id": task.workflow_id,
            "creator_id": task.creator_id
        })

    return export_data