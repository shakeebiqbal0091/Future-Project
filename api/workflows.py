from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List, Optional, Dict

from api.schemas import (
    WorkflowCreate, WorkflowUpdate, WorkflowResponse, ErrorResponse,
    PaginationResponse, SortOrder, Filter
)
from core.database import get_db
from core.auth import get_current_user, get_current_active_user, get_current_organization

router = APIRouter()


@router.post("/", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    workflow: WorkflowCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Get user's organization
    organization = get_current_organization(current_user, db)
    if not organization:
        raise HTTPException(status_code=404, detail="User not part of any organization")

    # Validate triggers and steps
    if not workflow.triggers and not workflow.steps:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workflow must have at least one trigger or step"
        )

    db_workflow = Workflow(
        name=workflow.name,
        description=workflow.description,
        triggers=workflow.triggers,
        steps=workflow.steps,
        is_active=workflow.is_active,
        organization_id=organization.id,
        created_by=current_user.id
    )
    db.add(db_workflow)
    db.commit()
    db.refresh(db_workflow)

    return db_workflow


@router.get("/", response_model=List[WorkflowResponse])
async def get_workflows(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Get user's organization
    organization = get_current_organization(current_user, db)
    if not organization:
        raise HTTPException(status_code=404, detail="User not part of any organization")

    workflows = db.query(Workflow).filter(Workflow.organization_id == organization.id).offset(skip).limit(limit).all()
    return workflows


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Check if user has access to this workflow
    organization = get_current_organization(current_user, db)
    if workflow.organization_id != organization.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this workflow")

    return workflow


@router.put("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: int,
    workflow_update: WorkflowUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Check if user has access to this workflow
    organization = get_current_organization(current_user, db)
    if workflow.organization_id != organization.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this workflow")

    workflow.name = workflow_update.name or workflow.name
    workflow.description = workflow_update.description or workflow.description
    workflow.triggers = workflow_update.triggers or workflow.triggers
    workflow.steps = workflow_update.steps or workflow.steps
    workflow.is_active = workflow_update.is_active if workflow_update.is_active is not None else workflow.is_active

    db.commit()
    db.refresh(workflow)
    return workflow


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Check if user has access to this workflow
    organization = get_current_organization(current_user, db)
    if workflow.organization_id != organization.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this workflow")

    db.delete(workflow)
    db.commit()


@router.post("/{workflow_id}/execute")
async def execute_workflow(
    workflow_id: int,
    input_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Check if user has access to this workflow
    organization = get_current_organization(current_user, db)
    if workflow.organization_id != organization.id:
        raise HTTPException(status_code=403, detail="Not authorized to execute this workflow")

    # Check if workflow is active
    if not workflow.is_active:
        raise HTTPException(status_code=400, detail="Workflow is not active")

    # Execute workflow - in real implementation, this would run the actual workflow
    execution_result = {
        "workflow_id": workflow.id,
        "workflow_name": workflow.name,
        "execution_id": f"exec_{workflow_id}_{int(datetime.utcnow().timestamp())}",
        "status": "running",
        "steps_executed": 0,
        "total_steps": len(workflow.steps),
        "input_data": input_data,
        "started_at": datetime.utcnow().isoformat()
    }

    return execution_result


@router.websocket("/{workflow_id}/ws")
async def workflow_websocket_endpoint(
    workflow_id: int,
    websocket: WebSocket,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Check if user has access to this workflow
    organization = get_current_organization(current_user, db)
    if workflow.organization_id != organization.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this workflow")

    await websocket.accept()
    try:
        while True:
            # In a real implementation, this would receive workflow events
            data = await websocket.receive_text()
            await websocket.send_text(f"Workflow event: {data}")
    except WebSocketDisconnect:
        pass


@router.get("/search")
async def search_workflows(
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

    q = db.query(Workflow).filter(Workflow.organization_id == organization.id)

    # Apply filters
    if filters:
        for filter in filters:
            if filter.operator == "eq":
                q = q.filter(getattr(Workflow, filter.field) == filter.value)
            elif filter.operator == "ne":
                q = q.filter(getattr(Workflow, filter.field) != filter.value)
            elif filter.operator == "contains":
                q = q.filter(getattr(Workflow, filter.field).ilike(f"%{filter.value}%"))
            # Add more operators as needed

    # Apply search query
    q = q.filter(
        Workflow.name.ilike(f"%{query}%") |
        Workflow.description.ilike(f"%{query}%")
    )

    # Apply sorting
    if sort:
        sort_field = getattr(Workflow, sort.field)
        if sort.direction == "desc":
            sort_field = sort_field.desc()
        q = q.order_by(sort_field)

    total = q.count()
    workflows = q.offset(skip).limit(limit).all()

    return PaginationResponse(
        items=workflows,
        total=total,
        page=(skip // limit) + 1,
        size=limit,
        total_pages=(total + limit - 1) // limit
    )


@router.get("/{workflow_id}/usage")
async def get_workflow_usage(
    workflow_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Check if user has access to this workflow
    organization = get_current_organization(current_user, db)
    if workflow.organization_id != organization.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this workflow")

    # Get usage statistics for the last 30 days
    from datetime import datetime, timedelta
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)

    tasks_count = db.query(Task).filter(
        Task.workflow_id == workflow_id,
        Task.created_at >= thirty_days_ago
    ).count()

    return {
        "workflow_id": workflow.id,
        "name": workflow.name,
        "tasks_executed_last_30_days": tasks_count,
        "triggers": workflow.triggers,
        "steps_count": len(workflow.steps)
    }