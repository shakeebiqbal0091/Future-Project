from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from datetime import datetime, timedelta

from api.schemas import (
    TaskCreate, TaskUpdate, TaskResponse, ErrorResponse,
    PaginationResponse, SortOrder, Filter
)
from core.database import get_db
from core.auth import get_current_user, get_current_active_user, get_current_organization

router = APIRouter()


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task: TaskCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Get user's organization
    organization = get_current_organization(current_user, db)
    if not organization:
        raise HTTPException(status_code=404, detail="User not part of any organization")

    # Validate agent exists and belongs to organization
    agent = db.query(Agent).filter(Agent.id == task.agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent.organization_id != organization.id:
        raise HTTPException(status_code=403, detail="Agent does not belong to your organization")

    # Validate workflow if provided
    if task.workflow_id:
        workflow = db.query(Workflow).filter(Workflow.id == task.workflow_id).first()
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        if workflow.organization_id != organization.id:
            raise HTTPException(status_code=403, detail="Workflow does not belong to your organization")

    db_task = Task(
        name=task.name,
        description=task.description,
        agent_id=task.agent_id,
        workflow_id=task.workflow_id,
        input_data=task.input_data,
        status=task.status,
        priority=task.priority,
        organization_id=organization.id,
        created_by=current_user.id
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)

    return db_task


@router.get("/", response_model=List[TaskResponse])
async def get_tasks(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Get user's organization
    organization = get_current_organization(current_user, db)
    if not organization:
        raise HTTPException(status_code=404, detail="User not part of any organization")

    q = db.query(Task).filter(Task.organization_id == organization.id)

    # Apply filters
    if status:
        q = q.filter(Task.status == status)
    if priority:
        q = q.filter(Task.priority == priority)

    tasks = q.offset(skip).limit(limit).all()
    return tasks


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    # Check if user has access to this task
    organization = get_current_organization(current_user, db)
    if task.organization_id != organization.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this task")

    return task


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_update: TaskUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    # Check if user has access to this task
    organization = get_current_organization(current_user, db)
    if task.organization_id != organization.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this task")

    # Only allow certain fields to be updated
    if task_update.name is not None:
        task.name = task_update.name
    if task_update.description is not None:
        task.description = task_update.description
    if task_update.agent_id is not None:
        # Validate new agent
        agent = db.query(Agent).filter(Agent.id == task_update.agent_id).first()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        if agent.organization_id != organization.id:
            raise HTTPException(status_code=403, detail="Agent does not belong to your organization")
        task.agent_id = task_update.agent_id
    if task_update.workflow_id is not None:
        # Validate new workflow
        workflow = db.query(Workflow).filter(Workflow.id == task_update.workflow_id).first()
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        if workflow.organization_id != organization.id:
            raise HTTPException(status_code=403, detail="Workflow does not belong to your organization")
        task.workflow_id = task_update.workflow_id
    if task_update.input_data is not None:
        task.input_data = task_update.input_data
    if task_update.status is not None:
        # Only allow status changes to valid transitions
        valid_transitions = {
            "pending": ["running", "cancelled"],
            "running": ["completed", "failed", "cancelled"],
            "completed": [],
            "failed": [],
            "cancelled": []
        }
        if task_update.status not in valid_transitions.get(task.status, []):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status transition from {task.status} to {task_update.status}"
            )
        task.status = task_update.status
    if task_update.priority is not None:
        task.priority = task_update.priority

    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    # Check if user has access to this task
    organization = get_current_organization(current_user, db)
    if task.organization_id != organization.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this task")

    db.delete(task)
    db.commit()


@router.post("/{task_id}/execute")
async def execute_task(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    # Check if user has access to this task
    organization = get_current_organization(current_user, db)
    if task.organization_id != organization.id:
        raise HTTPException(status_code=403, detail="Not authorized to execute this task")

    # Check if task is already running
    if task.status == "running":
        raise HTTPException(status_code=400, detail="Task is already running")

    # Update task status to running
    task.status = "running"
    db.commit()

    # In a real implementation, this would execute the task asynchronously
    # This would typically call the agent's executor or integration
    from time import sleep
    sleep(2)  # Simulate work

    task.status = "completed"
    task.output_data = {"result": "Task completed successfully"}
    task.execution_time = 2.0
    db.commit()

    return task


@router.websocket("/{task_id}/ws")
async def task_websocket_endpoint(
    task_id: int,
    websocket: WebSocket,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    # Check if user has access to this task
    organization = get_current_organization(current_user, db)
    if task.organization_id != organization.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this task")

    await websocket.accept()
    try:
        while True:
            # In a real implementation, this would receive task events
            data = await websocket.receive_text()
            await websocket.send_text(f"Task event: {data}")
    except WebSocketDisconnect:
        pass


@router.get("/{task_id}/logs", response_model=List[TaskLogResponse])
async def get_task_logs(
    task_id: int,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    # Check if user has access to this task
    organization = get_current_organization(current_user, db)
    if task.organization_id != organization.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this task")

    # Get task logs from the database
    logs = db.query(TaskLog).filter(TaskLog.task_id == task_id).order_by(TaskLog.timestamp.desc()).limit(limit).all()

    return logs


@router.get("/search")
async def search_tasks(
    query: str = Query(..., min_length=2),
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    sort: Optional[SortOrder] = None,
    filters: Optional[List[Filter]] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    organization = get_current_organization(current_user, db)
    if not organization:
        raise HTTPException(status_code=404, detail="User not part of any organization")

    q = db.query(Task).filter(Task.organization_id == organization.id)

    # Apply filters
    if filters:
        for filter in filters:
            if filter.operator == "eq":
                q = q.filter(getattr(Task, filter.field) == filter.value)
            elif filter.operator == "ne":
                q = q.filter(getattr(Task, filter.field) != filter.value)
            elif filter.operator == "contains":
                q = q.filter(getattr(Task, filter.field).ilike(f"%{filter.value}%"))
            # Add more operators as needed

    # Apply status and priority filters
    if status:
        q = q.filter(Task.status == status)
    if priority:
        q = q.filter(Task.priority == priority)

    # Apply search query
    q = q.filter(
        Task.name.ilike(f"%{query}%") |
        Task.description.ilike(f"%{query}%")
    )

    # Apply sorting
    if sort:
        sort_field = getattr(Task, sort.field)
        if sort.direction == "desc":
            sort_field = sort_field.desc()
        q = q.order_by(sort_field)

    total = q.count()
    tasks = q.offset(skip).limit(limit).all()

    return PaginationResponse(
        items=tasks,
        total=total,
        page=(skip // limit) + 1,
        size=limit,
        total_pages=(total + limit - 1) // limit
    )


@router.get("/analytics")
async def get_task_analytics(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    organization = get_current_organization(current_user, db)
    if not organization:
        raise HTTPException(status_code=404, detail="User not part of any organization")

    # Get analytics for the last 30 days
    from datetime import datetime, timedelta
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)

    tasks_count = db.query(Task).filter(
        Task.organization_id == organization.id,
        Task.created_at >= thirty_days_ago
    ).count()

    completed_tasks = db.query(Task).filter(
        Task.organization_id == organization.id,
        Task.status == "completed",
        Task.created_at >= thirty_days_ago
    ).count()

    failed_tasks = db.query(Task).filter(
        Task.organization_id == organization.id,
        Task.status == "failed",
        Task.created_at >= thirty_days_ago
    ).count()

    average_execution_time = db.query(Task.execution_time).filter(
        Task.organization_id == organization.id,
        Task.status == "completed",
        Task.created_at >= thirty_days_ago,
        Task.execution_time != None
    ).all()

    avg_time = sum([t[0] for t in average_execution_time]) / len(average_execution_time) if average_execution_time else 0

    return {
        "organization_id": organization.id,
        "tasks_last_30_days": tasks_count,
        "completed_tasks": completed_tasks,
        "failed_tasks": failed_tasks,
        "success_rate": (completed_tasks / tasks_count * 100) if tasks_count > 0 else 0,
        "average_execution_time_seconds": avg_time
    }