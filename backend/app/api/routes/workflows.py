from typing import Any, Dict, Optional
from datetime import datetime, timedelta
import jwt
import redis
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.core.security.auth_handler import AuthHandler
from app.core.security.utils import PasswordUtils, JWTUtils, RateLimiter, InputValidator
from app.models.models import User, Agent, AgentVersion, Task, TaskStatusEnum, StatusEnum, RoleEnum, PlanEnum, Workflow, WorkflowRun, WorkflowStatusEnum
from app.schemas.workflows import (
    WorkflowCreate, WorkflowUpdate, Workflow, WorkflowRunCreate, WorkflowValidationResponse,
    WorkflowRunList, WorkflowList, WorkflowCreateResponse, WorkflowUpdateResponse,
    WorkflowDeleteResponse, WorkflowRunResponse, WorkflowValidationError,
    WorkflowValidationErrorResponse, WorkflowErrorResponse, RateLimitHeaders
)

router = APIRouter()


# Authentication dependencies
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


# Helper functions
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends()) -> User:
    return await AuthHandler.get_current_active_user(token, db)


async def get_current_org(user: User = Depends(get_current_user)) -> User:
    # In a real implementation, you would get the user's organization
    # For now, we'll assume the user belongs to one organization
    # This would typically involve a Membership model and Organization model
    # For simplicity, we'll return the user as the organization owner
    return user


# Rate limiting configurations
RATE_LIMIT_CREATE = {"key": "workflows:create", "max_requests": 10, "window_seconds": 3600}
RATE_LIMIT_UPDATE = {"key": "workflows:update", "max_requests": 20, "window_seconds": 3600}
RATE_LIMIT_DELETE = {"key": "workflows:delete", "max_requests": 20, "window_seconds": 3600}
RATE_LIMIT_EXECUTE = {"key": "workflows:execute", "max_requests": 50, "window_seconds": 3600}


# POST /api/v1/workflows - Create a new workflow
@router.post("/workflows", response_model=WorkflowCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    workflow_data: WorkflowCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Rate limiting
    rate_limit_key = f"{RATE_LIMIT_CREATE['key']}:{current_user.id}"
    if RateLimiter.is_rate_limited(rate_limit_key, RATE_LIMIT_CREATE["max_requests"], RATE_LIMIT_CREATE["window_seconds"]):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many workflow creation attempts. Try again later."
        )

    # Validate input
    errors = []

    if not InputValidator.validate_input(workflow_data.dict()):
        errors.append(WorkflowValidationError(field="general", message="Invalid input data"))

    # Validate workflow definition (basic validation)
    try:
        if not isinstance(workflow_data.definition, dict):
            errors.append(WorkflowValidationError(field="definition", message="Definition must be a dictionary"))
        elif "nodes" not in workflow_data.definition or "edges" not in workflow_data.definition:
            errors.append(WorkflowValidationError(field="definition", message="Definition must contain nodes and edges"))
        elif not isinstance(workflow_data.definition["nodes"], list) or not isinstance(workflow_data.definition["edges"], list):
            errors.append(WorkflowValidationError(field="definition", message="Nodes and edges must be lists"))
    except Exception as e:
        errors.append(WorkflowValidationError(field="definition", message=f"Invalid workflow definition: {str(e)}"))

    if len(errors) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Validation error",
            headers=RateLimiter.get_rate_limit_header(rate_limit_key, RATE_LIMIT_CREATE["max_requests"], RATE_LIMIT_CREATE["window_seconds"]),
            content=WorkflowValidationErrorResponse(
                detail="Validation error",
                errors=errors
            ).json()
        )

    # Create new workflow
    new_workflow = Workflow(
        organization_id=current_user.id,  # In real implementation, this would be the user's organization ID
        name=workflow_data.name,
        description=workflow_data.description,
        definition=workflow_data.definition,
        status=WorkflowStatusEnum.draft,
        created_by=current_user.id
    )

    db.add(new_workflow)
    db.commit()
    db.refresh(new_workflow)

    return WorkflowCreateResponse(
        workflow=Workflow(
            id=str(new_workflow.id),
            organization_id=str(new_workflow.organization_id),
            name=new_workflow.name,
            description=new_workflow.description,
            definition=new_workflow.definition,
            status=new_workflow.status.value,
            created_by=str(new_workflow.created_by),
            created_at=new_workflow.created_at,
            updated_at=new_workflow.updated_at
        )
    )


# GET /api/v1/workflows - List workflows with pagination
@router.get("/workflows", response_model=WorkflowList)
async def list_workflows(
    page: int = 1,
    size: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Calculate offset
    offset = (page - 1) * size

    # Get total count
    total = db.query(Workflow).count()

    # Get paginated workflows
    workflows = db.query(Workflow).offset(offset).limit(size).all()

    return WorkflowList(
        workflows=[
            Workflow(
                id=str(workflow.id),
                organization_id=str(workflow.organization_id),
                name=workflow.name,
                description=workflow.description,
                definition=workflow.definition,
                status=workflow.status.value,
                created_by=str(workflow.created_by),
                created_at=workflow.created_at,
                updated_at=workflow.updated_at
            ) for workflow in workflows
        ],
        total=total,
        page=page,
        size=size
    )


# GET /api/v1/workflows/{id} - Get workflow details
@router.get("/workflows/{workflow_id}", response_model=Workflow)
async def get_workflow(
    workflow_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Find workflow
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow with id {workflow_id} not found"
        )

    return Workflow(
        id=str(workflow.id),
        organization_id=str(workflow.organization_id),
        name=workflow.name,
        description=workflow.description,
        definition=workflow.definition,
        status=workflow.status.value,
        created_by=str(workflow.created_by),
        created_at=workflow.created_at,
        updated_at=workflow.updated_at
    )


# PUT /api/v1/workflows/{id} - Update workflow
@router.put("/workflows/{workflow_id}", response_model=WorkflowUpdateResponse)
async def update_workflow(
    workflow_id: str,
    workflow_update: WorkflowUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Rate limiting
    rate_limit_key = f"{RATE_LIMIT_UPDATE['key']}:{current_user.id}"
    if RateLimiter.is_rate_limited(rate_limit_key, RATE_LIMIT_UPDATE["max_requests"], RATE_LIMIT_UPDATE["window_seconds"]):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many workflow update attempts. Try again later."
        )

    # Find workflow
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow with id {workflow_id} not found"
        )

    # Update workflow fields if provided
    if workflow_update.name is not None:
        workflow.name = workflow_update.name
    if workflow_update.description is not None:
        workflow.description = workflow_update.description
    if workflow_update.definition is not None:
        # Validate new definition
        try:
            if not isinstance(workflow_update.definition, dict):
                raise ValueError("Definition must be a dictionary")
            elif "nodes" not in workflow_update.definition or "edges" not in workflow_update.definition:
                raise ValueError("Definition must contain nodes and edges")
            elif not isinstance(workflow_update.definition["nodes"], list) or not isinstance(workflow_update.definition["edges"], list):
                raise ValueError("Nodes and edges must be lists")
            workflow.definition = workflow_update.definition
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid workflow definition: {str(e)}"
            )
    if workflow_update.status is not None:
        workflow.status = workflow_update.status

    workflow.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(workflow)

    return WorkflowUpdateResponse(
        workflow=Workflow(
            id=str(workflow.id),
            organization_id=str(workflow.organization_id),
            name=workflow.name,
            description=workflow.description,
            definition=workflow.definition,
            status=workflow.status.value,
            created_by=str(workflow.created_by),
            created_at=workflow.created_at,
            updated_at=workflow.updated_at
        )
    )


# DELETE /api/v1/workflows/{id} - Delete workflow
@router.delete("/workflows/{workflow_id}", response_model=WorkflowDeleteResponse)
async def delete_workflow(
    workflow_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Rate limiting
    rate_limit_key = f"{RATE_LIMIT_DELETE['key']}:{current_user.id}"
    if RateLimiter.is_rate_limited(rate_limit_key, RATE_LIMIT_DELETE["max_requests"], RATE_LIMIT_DELETE["window_seconds"]):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many workflow deletion attempts. Try again later."
        )

    # Find workflow
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow with id {workflow_id} not found"
        )

    # Delete workflow
    db.delete(workflow)
    db.commit()

    return WorkflowDeleteResponse()


# POST /api/v1/workflows/{id}/run - Execute workflow
@router.post("/workflows/{workflow_id}/run", response_model=WorkflowRunResponse)
async def execute_workflow(
    workflow_id: str,
    run_request: WorkflowRunCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Rate limiting
    rate_limit_key = f"{RATE_LIMIT_EXECUTE['key']}:{current_user.id}"
    if RateLimiter.is_rate_limited(rate_limit_key, RATE_LIMIT_EXECUTE["max_requests"], RATE_LIMIT_EXECUTE["window_seconds"]):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many workflow execution attempts. Try again later."
        )

    # Find workflow
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow with id {workflow_id} not found"
        )

    # Check if workflow is in draft status
    if workflow.status == WorkflowStatusEnum.draft:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot execute workflow in draft status. Please activate the workflow first."
        )

    try:
        # Create workflow run
        workflow_run = WorkflowRun(
            workflow_id=workflow_id,
            status=TaskStatusEnum.running,
            input=run_request.input,
            started_at=datetime.utcnow()
        )

        db.add(workflow_run)
        db.commit()
        db.refresh(workflow_run)

        # TODO: Implement actual workflow execution logic here
        # This would involve:
        # 1. Parsing the workflow definition
        # 2. Executing each step in sequence or parallel
        # 3. Handling errors and retries
        # 4. Collecting outputs

        # Simulate workflow execution for now
        output = {
            "result": "Simulated workflow execution completed",
            "status": "success",
            "steps_executed": 3
        }

        workflow_run.status = TaskStatusEnum.completed
        workflow_run.output = output
        workflow_run.completed_at = datetime.utcnow()
        workflow_run.duration_ms = (workflow_run.completed_at - workflow_run.started_at).total_seconds() * 1000

        db.commit()
        db.refresh(workflow_run)

        return WorkflowRunResponse(
            run=WorkflowRun(
                id=str(workflow_run.id),
                workflow_id=str(workflow_run.workflow_id),
                status=workflow_run.status.value,
                input=workflow_run.input,
                output=workflow_run.output,
                error=workflow_run.error,
                started_at=workflow_run.started_at,
                completed_at=workflow_run.completed_at,
                duration_ms=workflow_run.duration_ms
            )
        )

    except Exception as e:
        # Mark run as failed
        if 'workflow_run' in locals():
            workflow_run.status = TaskStatusEnum.failed
            workflow_run.error = str(e)
            workflow_run.completed_at = datetime.utcnow()
            workflow_run.duration_ms = (workflow_run.completed_at - workflow_run.started_at).total_seconds() * 1000 if workflow_run.started_at else 0
            db.commit()
            db.refresh(workflow_run)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute workflow: {str(e)}"
        )


# GET /api/v1/workflows/{id}/runs - List workflow runs
@router.get("/workflows/{workflow_id}/runs", response_model=WorkflowRunList)
async def list_workflow_runs(
    workflow_id: str,
    page: int = 1,
    size: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Find workflow
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow with id {workflow_id} not found"
        )

    # Calculate offset
    offset = (page - 1) * size

    # Get total count
    total = db.query(WorkflowRun).filter(WorkflowRun.workflow_id == workflow_id).count()

    # Get paginated runs
    runs = db.query(WorkflowRun).filter(WorkflowRun.workflow_id == workflow_id).offset(offset).limit(size).all()

    return WorkflowRunList(
        runs=[
            WorkflowRun(
                id=str(run.id),
                workflow_id=str(run.workflow_id),
                status=run.status.value,
                input=run.input,
                output=run.output,
                error=run.error,
                started_at=run.started_at,
                completed_at=run.completed_at,
                duration_ms=run.duration_ms
            ) for run in runs
        ],
        total=total,
        page=page,
        size=size
    )


# GET /api/v1/workflows/{id}/validate - Validate workflow definition
@router.get("/workflows/{workflow_id}/validate", response_model=WorkflowValidationResponse)
async def validate_workflow(
    workflow_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Find workflow
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow with id {workflow_id} not found"
        )

    errors = []
warnings = []
suggestions = []

    try:
        # Basic validation
        if not isinstance(workflow.definition, dict):
            errors.append("Definition must be a dictionary")
        elif "nodes" not in workflow.definition or "edges" not in workflow.definition:
            errors.append("Definition must contain nodes and edges")
        elif not isinstance(workflow.definition["nodes"], list) or not isinstance(workflow.definition["edges"], list):
            errors.append("Nodes and edges must be lists")
        else:
            # Check for empty nodes
            if len(workflow.definition["nodes"]) == 0:
                errors.append("Workflow must have at least one node")

            # Check for orphan nodes (nodes not connected by any edge)
            connected_nodes = set()
            for edge in workflow.definition["edges"]:
                if "source" in edge and "target" in edge:
                    connected_nodes.add(edge["source"])
                    connected_nodes.add(edge["target"])
            for node in workflow.definition["nodes"]:
                if "id" in node and node["id"] not in connected_nodes:
                    warnings.append(f"Node {node["id"]} is not connected to any other node")

            # Check for circular dependencies (basic check)
            # This is a simplified check - real implementation would need more complex graph traversal
            for edge in workflow.definition["edges"]:
                if edge.get("source") == edge.get("target"):
                    errors.append(f"Circular dependency detected: node {edge["source"]} points to itself")

            # Check for duplicate node IDs
            node_ids = [node.get("id") for node in workflow.definition["nodes"] if "id" in node]
            if len(node_ids) != len(set(node_ids)):
                errors.append("Duplicate node IDs found in workflow definition")

            # Suggestions for improvement
            if len(workflow.definition["nodes"]) > 10:
                suggestions.append("Consider breaking this workflow into smaller sub-workflows for better maintainability")

    except Exception as e:
        errors.append(f"Validation error: {str(e)}")

    return WorkflowValidationResponse(
        valid=len(errors) == 0,
        errors=errors if len(errors) > 0 else None,
        warnings=warnings if len(warnings) > 0 else None,
        suggestions=suggestions if len(suggestions) > 0 else None
    )


# Error handler for validation errors
@router.exception_handler(WorkflowValidationErrorResponse)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=exc.json(),
        headers=RateLimiter.get_rate_limit_header("workflows:validation", 100, 3600)
    )


# Error handler for general errors
@router.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=WorkflowErrorResponse(
            detail="An unexpected error occurred",
            error_code="INTERNAL_SERVER_ERROR",
            timestamp=datetime.utcnow()
        ).json(),
        headers=RateLimiter.get_rate_limit_header("workflows:errors", 10, 3600)
    )