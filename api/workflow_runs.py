from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from api.schemas import (
    WorkflowRunCreate, WorkflowRunUpdate, WorkflowRunResponse, ErrorResponse,
    PaginationResponse, SortOrder, Filter
)
from core.database import get_db
from core.auth import get_current_user, get_current_active_user, get_current_organization

router = APIRouter()


@router.get("/{run_id}", response_model=WorkflowRunResponse)
async def get_workflow_run(
    run_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
    if run is None:
        raise HTTPException(status_code=404, detail="Workflow run not found")

    # Check if user has access to this run
    organization = get_current_organization(current_user, db)
    if run.organization_id != organization.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this workflow run")

    # Get workflow name for response
    workflow = db.query(Workflow).filter(Workflow.id == run.workflow_id).first()
    run.workflow_name = workflow.name if workflow else "Unknown Workflow"

    return run


@router.post("/{run_id}/cancel", response_model=WorkflowRunResponse)
async def cancel_workflow_run(
    run_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
    if run is None:
        raise HTTPException(status_code=404, detail="Workflow run not found")

    # Check if user has access to this run
    organization = get_current_organization(current_user, db)
    if run.organization_id != organization.id:
        raise HTTPException(status_code=403, detail="Not authorized to cancel this workflow run")

    # Only allow cancellation if run is in progress
    if run.status != "running":
        raise HTTPException(status_code=400, detail="Workflow run is not in progress and cannot be cancelled")

    run.status = "cancelled"
    run.completed_at = datetime.utcnow()
    run.error_message = "Cancelled by user"
    db.commit()

    return run


@router.get("/{run_id}/logs", response_model=List[TaskLogResponse])
async def get_workflow_run_logs(
    run_id: int,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
    if run is None:
        raise HTTPException(status_code=404, detail="Workflow run not found")

    # Check if user has access to this run
    organization = get_current_organization(current_user, db)
    if run.organization_id != organization.id:
        raise HTTPException(status_code=403, detail="Not authorized to access logs for this workflow run")

    # Get all task logs for this workflow run
    task_logs = db.query(TaskLog).join(Task).filter(Task.workflow_run_id == run_id).order_by(TaskLog.timestamp.desc()).limit(limit).all()

    return task_logs


@router.post("/{run_id}/retry", response_model=WorkflowRunResponse)
async def retry_workflow_run(
    run_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
    if run is None:
        raise HTTPException(status_code=404, detail="Workflow run not found")

    # Check if user has access to this run
    organization = get_current_organization(current_user, db)
    if run.organization_id != organization.id:
        raise HTTPException(status_code=403, detail="Not authorized to retry this workflow run")

    # Only allow retry if run failed or was cancelled
    if run.status not in ["failed", "cancelled"]:
        raise HTTPException(status_code=400, detail="Workflow run is not in a retryable state")

    # Create new run with same input data
    new_run = WorkflowRun(
        workflow_id=run.workflow_id,
        status="pending",
        input_data=run.input_data,
        organization_id=organization.id,
        created_by=current_user.id
    )
    db.add(new_run)
    db.commit()
    db.refresh(new_run)

    # Add workflow name to response
    workflow = db.query(Workflow).filter(Workflow.id == new_run.workflow_id).first()
    new_run.workflow_name = workflow.name if workflow else "Unknown Workflow"

    return new_run


@router.get("/", response_model=List[WorkflowRunResponse])
async def get_workflow_runs(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    workflow_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Get user's organization
    organization = get_current_organization(current_user, db)
    if not organization:
        raise HTTPException(status_code=404, detail="User not part of any organization")

    q = db.query(WorkflowRun).filter(WorkflowRun.organization_id == organization.id)

    # Apply filters
    if status:
        q = q.filter(WorkflowRun.status == status)
    if workflow_id:
        q = q.filter(WorkflowRun.workflow_id == workflow_id)

    runs = q.offset(skip).limit(limit).all()

    # Add workflow names to responses
    for run in runs:
        workflow = db.query(Workflow).filter(Workflow.id == run.workflow_id).first()
        run.workflow_name = workflow.name if workflow else "Unknown Workflow"

    return runs


@router.get("/search")
async def search_workflow_runs(
    query: str = Query(..., min_length=2),
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = None,
    workflow_id: Optional[int] = None,
    sort: Optional[SortOrder] = None,
    filters: Optional[List[Filter]] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    organization = get_current_organization(current_user, db)
    if not organization:
        raise HTTPException(status_code=404, detail="User not part of any organization")

    q = db.query(WorkflowRun).filter(WorkflowRun.organization_id == organization.id)

    # Apply filters
    if filters:
        for filter in filters:
            if filter.operator == "eq":
                q = q.filter(getattr(WorkflowRun, filter.field) == filter.value)
            elif filter.operator == "ne":
                q = q.filter(getattr(WorkflowRun, filter.field) != filter.value)
            elif filter.operator == "contains":
                q = q.filter(getattr(WorkflowRun, filter.field).ilike(f"%{filter.value}%"))
            # Add more operators as needed

    # Apply status and workflow filters
    if status:
        q = q.filter(WorkflowRun.status == status)
    if workflow_id:
        q = q.filter(WorkflowRun.workflow_id == workflow_id)

    # Apply search query
    q = q.filter(
        WorkflowRun.error_message.ilike(f"%{query}%") |
        WorkflowRun.input_data.ilike(f"%{query}%") |
        WorkflowRun.output_data.ilike(f"%{query}%")
    )

    # Apply sorting
    if sort:
        sort_field = getattr(WorkflowRun, sort.field)
        if sort.direction == "desc":
            sort_field = sort_field.desc()
        q = q.order_by(sort_field)

    total = q.count()
    runs = q.offset(skip).limit(limit).all()

    # Add workflow names to responses
    for run in runs:
        workflow = db.query(Workflow).filter(Workflow.id == run.workflow_id).first()
        run.workflow_name = workflow.name if workflow else "Unknown Workflow"

    return PaginationResponse(
        items=runs,
        total=total,
        page=(skip // limit) + 1,
        size=limit,
        total_pages=(total + limit - 1) // limit
    )


@router.get("/analytics")
async def get_workflow_run_analytics(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    organization = get_current_organization(current_user, db)
    if not organization:
        raise HTTPException(status_code=404, detail="User not part of any organization")

    # Get analytics for the last 30 days
    from datetime import datetime, timedelta
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)

    runs_count = db.query(WorkflowRun).filter(
        WorkflowRun.organization_id == organization.id,
        WorkflowRun.created_at >= thirty_days_ago
    ).count()

    completed_runs = db.query(WorkflowRun).filter(
        WorkflowRun.organization_id == organization.id,
        WorkflowRun.status == "completed",
        WorkflowRun.created_at >= thirty_days_ago
    ).count()

    failed_runs = db.query(WorkflowRun).filter(
        WorkflowRun.organization_id == organization.id,
        WorkflowRun.status == "failed",
        WorkflowRun.created_at >= thirty_days_ago
    ).count()

    average_duration = db.query(WorkflowRun.duration_ms).filter(
        WorkflowRun.organization_id == organization.id,
        WorkflowRun.status == "completed",
        WorkflowRun.created_at >= thirty_days_ago,
        WorkflowRun.duration_ms != None
    ).all()

    avg_duration = sum([r[0] for r in average_duration]) / len(average_duration) if average_duration else 0

    return {
        "organization_id": organization.id,
        "runs_last_30_days": runs_count,
        "completed_runs": completed_runs,
        "failed_runs": failed_runs,
        "success_rate": (completed_runs / runs_count * 100) if runs_count > 0 else 0,
        "average_duration_ms": avg_duration
    }