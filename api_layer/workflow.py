from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import json
import asyncio

from ..shared.database import get_db
from ..shared.security import get_current_active_user, get_current_active_superuser, get_current_organization_member
from ..shared.models import User, Organization, Agent, Workflow, Task
from ..shared.schemas import (
    Workflow, WorkflowCreate, WorkflowUpdate, Agent, Task,
    Pagination, PaginatedResponse, WorkflowExecuteRequest, WebSocketMessage
)
from ..shared.utils import (
    paginate_query, create_paginated_response,
    filter_by_organization, get_user_organizations
)

router = APIRouter()


@router.get("/", response_model=List[Workflow])
def get_workflows(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    organization_id: Optional[int] = None,
    pagination: Pagination = Depends()
):
    """Get all workflows (filtered by organization if specified)."""

    # If organization_id is specified, verify user has access
    if organization_id:
        org_query = db.query(Organization).filter(Organization.id == organization_id)
        org_query = filter_by_organization(db, org_query, organization_id, current_user)
        organization = org_query.first()
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found or access denied"
            )

        # Get workflows for this organization
        query = db.query(Workflow).filter(
            Workflow.organization_id == organization_id
        )
    else:
        # Get workflows for all organizations the user belongs to
        user_organizations = get_user_organizations(db, current_user.id)
        organization_ids = [org.id for org in user_organizations]
        query = db.query(Workflow).filter(
            Workflow.organization_id.in_(organization_ids)
        )

    paginated_query, total_count = paginate_query(db, query, pagination)
    items = paginated_query.all()

    return create_paginated_response(items, total_count, pagination)


@router.post("/", response_model=Workflow)
def create_workflow(
    workflow_data: WorkflowCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Create a new workflow."""

    # Verify user belongs to the specified organization
    org_query = db.query(Organization).filter(Organization.id == workflow_data.organization_id)
    org_query = filter_by_organization(db, org_query, workflow_data.organization_id, current_user)
    organization = org_query.first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found or access denied"
        )

    # Check if user is member of this organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == workflow_data.organization_id
    ).first()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this organization"
        )

    # Only owners and admins can create workflows
    if member.role not in ["owner", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owners and admins can create workflows"
        )

    # Validate agent if specified
    if workflow_data.agent_id:
        agent = db.query(Agent).filter(Agent.id == workflow_data.agent_id).first()
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found"
            )

        # Verify agent belongs to the same organization
        if agent.organization_id != workflow_data.organization_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Agent must belong to the same organization as the workflow"
            )

    # Create workflow
    workflow = Workflow(
        name=workflow_data.name,
        description=workflow_data.description,
        definition=workflow_data.definition,
        status=workflow_data.status,
        organization_id=workflow_data.organization_id,
        creator_id=current_user.id,
        agent_id=workflow_data.agent_id
    )

    db.add(workflow)
    db.commit()
    db.refresh(workflow)

    return Workflow.from_orm(workflow)


@router.get("/{workflow_id}", response_model=Workflow)
def get_workflow(
    workflow_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get workflow by ID."""

    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found"
        )

    # Verify user has access to this workflow's organization
    org_query = db.query(Organization).filter(Organization.id == workflow.organization_id)
    org_query = filter_by_organization(db, org_query, workflow.organization_id, current_user)
    organization = org_query.first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found or access denied"
        )

    return Workflow.from_orm(workflow)


@router.put("/{workflow_id}", response_model=Workflow)
def update_workflow(
    workflow_id: int,
    workflow_update: WorkflowUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update workflow."""

    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found"
        )

    # Verify user has access to this workflow's organization
    org_query = db.query(Organization).filter(Organization.id == workflow.organization_id)
    org_query = filter_by_organization(db, org_query, workflow.organization_id, current_user)
    organization = org_query.first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found or access denied"
        )

    # Check if user is member of this organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == workflow.organization_id
    ).first()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this organization"
        )

    # Only owners and admins can update workflows
    if member.role not in ["owner", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owners and admins can update workflows"
        )

    # Validate agent if being updated
    if workflow_update.agent_id is not None:
        if workflow_update.agent_id:
            agent = db.query(Agent).filter(Agent.id == workflow_update.agent_id).first()
            if not agent:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Agent not found"
                )

            # Verify agent belongs to the same organization
            if agent.organization_id != workflow.organization_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Agent must belong to the same organization as the workflow"
                )
        else:
            # agent_id is being set to None
            pass

    if workflow_update.name:
        workflow.name = workflow_update.name

    if workflow_update.description:
        workflow.description = workflow_update.description

    if workflow_update.definition is not None:
        workflow.definition = workflow_update.definition

    if workflow_update.status is not None:
        # Validate status change
        valid_transitions = {
            "draft": ["active", "inactive", "draft"],
            "active": ["inactive", "active"],
            "inactive": ["active", "inactive"]
        }

        if workflow_update.status not in valid_transitions.get(workflow.status, []):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status transition from {workflow.status} to {workflow_update.status}"
            )

        workflow.status = workflow_update.status

    if workflow_update.agent_id is not None:
        workflow.agent_id = workflow_update.agent_id

    db.commit()
    db.refresh(workflow)

    return Workflow.from_orm(workflow)


@router.delete("/{workflow_id}")
def delete_workflow(
    workflow_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete workflow."""

    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found"
        )

    # Verify user has access to this workflow's organization
    org_query = db.query(Organization).filter(Organization.id == workflow.organization_id)
    org_query = filter_by_organization(db, org_query, workflow.organization_id, current_user)
    organization = org_query.first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found or access denied"
        )

    # Check if user is member of this organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == workflow.organization_id
    ).first()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this organization"
        )

    # Only owners and admins can delete workflows
    if member.role not in ["owner", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owners and admins can delete workflows"
        )

    # Check if workflow has active tasks
    from ..shared.models import Task
    active_tasks = db.query(Task).filter(
        Task.workflow_id == workflow_id,
        Task.status.in_(['pending', 'running'])
    ).count()

    if active_tasks > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete workflow because it has active tasks"
        )

    db.delete(workflow)
    db.commit()

    return {"message": "Workflow deleted successfully"}


@router.post("/{workflow_id}/execute", response_model=Dict[str, Any])
def execute_workflow(
    workflow_id: int,
    execute_request: WorkflowExecuteRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Execute a workflow."""

    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found"
        )

    # Verify user has access to this workflow's organization
    org_query = db.query(Organization).filter(Organization.id == workflow.organization_id)
    org_query = filter_by_organization(db, org_query, workflow.organization_id, current_user)
    organization = org_query.first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found or access denied"
        )

    # Check if workflow is active
    if workflow.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workflow is not active and cannot be executed"
        )

    # Check if workflow has an agent
    if not workflow.agent_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workflow does not have an assigned agent"
        )

    # Create a new task for this execution
    from ..shared.models import Task
    task = Task(
        name=f"Execution of workflow '{workflow.name}'",
        description=f"Automated execution of workflow {workflow.name}",
        input_data=execute_request.input_data or {},
        status="pending",
        organization_id=workflow.organization_id,
        workflow_id=workflow_id,
        creator_id=current_user.id
    )

    db.add(task)
    db.commit()
    db.refresh(task)

    # In a real implementation, you would:
    # 1. Validate the workflow definition
    # 2. Create a task queue entry
    # 3. Start the workflow execution
    # For now, we'll just return the task ID

    return {
        "task_id": task.id,
        "workflow_id": workflow.id,
        "status": "pending",
        "execution_mode": "async" if execute_request.async_execution else "sync"
    }


@router.get("/{workflow_id}/tasks", response_model=List[Task])
def get_workflow_tasks(
    workflow_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    pagination: Pagination = Depends()
):
    """Get tasks for a workflow."""

    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found"
        )

    # Verify user has access to this workflow's organization
    org_query = db.query(Organization).filter(Organization.id == workflow.organization_id)
    org_query = filter_by_organization(db, org_query, workflow.organization_id, current_user)
    organization = org_query.first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found or access denied"
        )

    from ..shared.models import Task
    query = db.query(Task).filter(
        Task.workflow_id == workflow_id
    )

    paginated_query, total_count = paginate_query(db, query, pagination)
    items = paginated_query.all()

    return create_paginated_response(items, total_count, pagination)


@router.get("/{workflow_id}/definition", response_model=Dict[str, Any])
def get_workflow_definition(
    workflow_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get workflow definition (for visualization)."""

    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found"
        )

    # Verify user has access to this workflow's organization
    org_query = db.query(Organization).filter(Organization.id == workflow.organization_id)
    org_query = filter_by_organization(db, org_query, workflow.organization_id, current_user)
    organization = org_query.first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found or access denied"
        )

    # In a real implementation, you would validate and process the definition
    # For now, we'll just return it
    return {
        "workflow_id": workflow.id,
        "name": workflow.name,
        "definition": workflow.definition,
        "status": workflow.status
    }


@router.get("/{workflow_id}/stats", response_model=dict)
def get_workflow_stats(
    workflow_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get workflow statistics."""

    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found"
        )

    # Verify user has access to this workflow's organization
    org_query = db.query(Organization).filter(Organization.id == workflow.organization_id)
    org_query = filter_by_organization(db, org_query, workflow.organization_id, current_user)
    organization = org_query.first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found or access denied"
        )

    from ..shared.models import Task

    # Get task statistics
    total_tasks = db.query(Task).filter(Task.workflow_id == workflow_id).count()
    completed_tasks = db.query(Task).filter(
        Task.workflow_id == workflow_id,
        Task.status == "completed"
    ).count()
    failed_tasks = db.query(Task).filter(
        Task.workflow_id == workflow_id,
        Task.status == "failed"
    ).count()
    pending_tasks = db.query(Task).filter(
        Task.workflow_id == workflow_id,
        Task.status == "pending"
    ).count()
    running_tasks = db.query(Task).filter(
        Task.workflow_id == workflow_id,
        Task.status == "running"
    ).count()

    # Get execution time statistics
    from sqlalchemy import func
    avg_execution_time = db.query(func.avg(Task.execution_time)).filter(
        Task.workflow_id == workflow_id,
        Task.execution_time.is_not(None)
    ).scalar() or 0

    # Get recent activity
    recent_tasks = db.query(Task).filter(
        Task.workflow_id == workflow_id
    ).order_by(Task.created_at.desc()).limit(5).all()

    return {
        "workflow": {
            "id": workflow.id,
            "name": workflow.name,
            "status": workflow.status,
            "agent_id": workflow.agent_id
        },
        "task_statistics": {
            "total": total_tasks,
            "completed": completed_tasks,
            "failed": failed_tasks,
            "pending": pending_tasks,
            "running": running_tasks,
            "success_rate": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        },
        "performance": {
            "average_execution_time": avg_execution_time,  # in seconds
            "tasks_per_day": total_tasks / 30  # average per day (assuming 30-day period)
        },
        "recent_activity": [{
            "task_id": task.id,
            "name": task.name,
            "status": task.status,
            "created_at": task.created_at.isoformat()
        } for task in recent_tasks]
    }


@router.websocket("/{workflow_id}/ws")
def workflow_websocket(
    workflow_id: int,
    websocket: WebSocket,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Real-time workflow monitoring via WebSocket."""

    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found"
        )

    # Verify user has access to this workflow's organization
    org_query = db.query(Organization).filter(Organization.id == workflow.organization_id)
    org_query = filter_by_organization(db, org_query, workflow.organization_id, current_user)
    organization = org_query.first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found or access denied"
        )

    await websocket.accept()

    try:
        # In a real implementation, you would:
        # 1. Subscribe to workflow task updates
        # 2. Send real-time status updates
        # 3. Handle task completion/failure events
        # For now, we'll just send a welcome message

        welcome_message = WebSocketMessage(
            type="status_update",
            data={
                "workflow_id": workflow.id,
                "name": workflow.name,
                "status": workflow.status,
                "message": "Connected to workflow monitoring"
            },
            timestamp=datetime.datetime.now()
        )

        await websocket.send_json(welcome_message.model_dump())

        # Keep the connection open
        while True:
            await asyncio.sleep(30)  # Send keep-alive every 30 seconds
            keep_alive = WebSocketMessage(
                type="keep_alive",
                data={"message": "Connection alive"},
                timestamp=datetime.datetime.now()
            )
            await websocket.send_json(keep_alive.model_dump())

    except WebSocketDisconnect:
        print(f"Client disconnected from workflow {workflow_id}")
    finally:
        await websocket.close()