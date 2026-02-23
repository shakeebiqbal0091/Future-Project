from typing import Any, Dict, Optional
from datetime import datetime, timedelta
import jwt
import redis
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.core.security.auth_handler import AuthHandler
from app.core.security.utils import PasswordUtils, JWTUtils, RateLimiter, InputValidator
from app.models.models import User, Agent, AgentVersion, Task, TaskStatusEnum, StatusEnum, RoleEnum, PlanEnum, Integration, IntegrationStatusEnum
from app.schemas.integrations import (
    IntegrationCreate, IntegrationUpdate, Integration, IntegrationList,
    IntegrationCreateResponse, IntegrationUpdateResponse, IntegrationDeleteResponse,
    IntegrationTestResponse, IntegrationAction, IntegrationActionsResponse,
    IntegrationValidationError, IntegrationValidationErrorResponse, IntegrationErrorResponse,
    RateLimitHeaders
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
RATE_LIMIT_CREATE = {"key": "integrations:create", "max_requests": 10, "window_seconds": 3600}
RATE_LIMIT_UPDATE = {"key": "integrations:update", "max_requests": 20, "window_seconds": 3600}
RATE_LIMIT_DELETE = {"key": "integrations:delete", "max_requests": 20, "window_seconds": 3600}
RATE_LIMIT_TEST = {"key": "integrations:test", "max_requests": 50, "window_seconds": 3600}


# Helper functions for integration validation
async def validate_integration_data(integration_data: Dict[str, Any], db: Session) -> List[IntegrationValidationError]:
    errors = []

    # Validate type
    if not integration_data.get("type"):
        errors.append(IntegrationValidationError(field="type", message="Integration type is required"))
    elif integration_data["type"] not in ["gmail", "slack", "rest_api", "webhook"]:
        errors.append(IntegrationValidationError(field="type", message="Invalid integration type"))

    # Validate name
    if not integration_data.get("name"):
        errors.append(IntegrationValidationError(field="name", message="Integration name is required"))
    elif len(integration_data["name"]) > 100:
        errors.append(IntegrationValidationError(field="name", message="Integration name must be less than 100 characters"))

    # Validate credentials (basic check)
    if not integration_data.get("credentials_encrypted"):
        errors.append(IntegrationValidationError(field="credentials_encrypted", message="Credentials are required"))

    # Validate config structure based on type
    integration_type = integration_data.get("type", "")
    config = integration_data.get("config", {})

    if integration_type == "gmail":
        if "access_token" not in config:
            errors.append(IntegrationValidationError(field="config.access_token", message="Gmail access token is required"))
        if "refresh_token" not in config:
            errors.append(IntegrationValidationError(field="config.refresh_token", message="Gmail refresh token is required"))
    elif integration_type == "slack":
        if "bot_token" not in config:
            errors.append(IntegrationValidationError(field="config.bot_token", message="Slack bot token is required"))
    elif integration_type == "rest_api":
        if "base_url" not in config:
            errors.append(IntegrationValidationError(field="config.base_url", message="Base URL is required for REST API integration"))
        if "auth_type" not in config:
            errors.append(IntegrationValidationError(field="config.auth_type", message="Auth type is required for REST API integration"))
    elif integration_type == "webhook":
        if "endpoint_url" not in config:
            errors.append(IntegrationValidationError(field="config.endpoint_url", message="Endpoint URL is required for webhook integration"))

    return errors


# Helper function to get available actions for integration type
async def get_integration_actions(integration_type: str) -> List[IntegrationAction]:
    actions = []

    if integration_type == "gmail":
        actions = [
            IntegrationAction(
                name="send_email",
                description="Send an email",
                parameters={
                    "to": "string (email address)",
                    "subject": "string",
                    "body": "string",
                    "cc": "string (optional)",
                    "bcc": "string (optional)"
                }
            ),
            IntegrationAction(
                name="read_emails",
                description="Read emails from inbox",
                parameters={
                    "query": "string (search query)",
                    "limit": "integer (max 100)"
                }
            )
        ]
    elif integration_type == "slack":
        actions = [
            IntegrationAction(
                name="post_message",
                description="Post message to Slack channel",
                parameters={
                    "channel": "string (channel ID or name)",
                    "text": "string",
                    "thread_ts": "string (optional, for replying to threads)"
                }
            ),
            IntegrationAction(
                name="create_channel",
                description="Create a new Slack channel",
                parameters={
                    "name": "string",
                    "is_private": "boolean (optional, default false)"
                }
            )
        ]
    elif integration_type == "rest_api":
        actions = [
            IntegrationAction(
                name="make_request",
                description="Make HTTP request to external API",
                parameters={
                    "method": "string (GET, POST, PUT, DELETE)",
                    "endpoint": "string (relative endpoint)",
                    "headers": "object (optional)",
                    "body": "object (optional)"
                }
            )
        ]
    elif integration_type == "webhook":
        actions = [
            IntegrationAction(
                name="receive_webhook",
                description="Receive webhook data",
                parameters={
                    "event_type": "string",
                    "payload": "object"
                }
            )
        ]

    return actions


# POST /api/v1/integrations - Create a new integration
@router.post("/integrations", response_model=IntegrationCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_integration(
    integration_data: IntegrationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Rate limiting
    rate_limit_key = f"{RATE_LIMIT_CREATE['key']}:{current_user.id}"
    if RateLimiter.is_rate_limited(rate_limit_key, RATE_LIMIT_CREATE["max_requests"], RATE_LIMIT_CREATE["window_seconds"]):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many integration creation attempts. Try again later."
        )

    # Validate input
    errors = []

    # Additional validation using helper function
    errors.extend(await validate_integration_data(integration_data.dict(), db))

    if len(errors) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Validation error",
            headers=RateLimiter.get_rate_limit_header(rate_limit_key, RATE_LIMIT_CREATE["max_requests"], RATE_LIMIT_CREATE["window_seconds"]),
            content=IntegrationValidationErrorResponse(
                detail="Validation error",
                errors=errors
            ).json()
        )

    # Create new integration
    new_integration = Integration(
        organization_id=current_user.id,  # In real implementation, this would be the user's organization ID
        type=integration_data.type,
        name=integration_data.name,
        credentials_encrypted=integration_data.credentials_encrypted,
        config=integration_data.config,
        status=integration_data.status
    )

    db.add(new_integration)
    db.commit()
    db.refresh(new_integration)

    return IntegrationCreateResponse(
        integration=Integration(
            id=str(new_integration.id),
            organization_id=str(new_integration.organization_id),
            type=new_integration.type,
            name=new_integration.name,
            credentials_encrypted=new_integration.credentials_encrypted,
            config=new_integration.config,
            status=new_integration.status.value,
            last_sync=new_integration.last_sync,
            created_at=new_integration.created_at
        )
    )


# GET /api/v1/integrations - List integrations with pagination
@router.get("/integrations", response_model=IntegrationList)
async def list_integrations(
    page: int = 1,
    size: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Calculate offset
    offset = (page - 1) * size

    # Get total count
    total = db.query(Integration).count()

    # Get paginated integrations
    integrations = db.query(Integration).offset(offset).limit(size).all()

    return IntegrationList(
        integrations=[
            Integration(
                id=str(integration.id),
                organization_id=str(integration.organization_id),
                type=integration.type,
                name=integration.name,
                credentials_encrypted=integration.credentials_encrypted,
                config=integration.config,
                status=integration.status.value,
                last_sync=integration.last_sync,
                created_at=integration.created_at
            ) for integration in integrations
        ],
        total=total,
        page=page,
        size=size
    )


# GET /api/v1/integrations/{id} - Get integration details
@router.get("/integrations/{integration_id}", response_model=Integration)
async def get_integration(
    integration_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Find integration
    integration = db.query(Integration).filter(Integration.id == integration_id).first()

    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Integration with id {integration_id} not found"
        )

    return Integration(
        id=str(integration.id),
        organization_id=str(integration.organization_id),
        type=integration.type,
        name=integration.name,
        credentials_encrypted=integration.credentials_encrypted,
        config=integration.config,
        status=integration.status.value,
        last_sync=integration.last_sync,
        created_at=integration.created_at
    )


# PUT /api/v1/integrations/{id} - Update integration
@router.put("/integrations/{integration_id}", response_model=IntegrationUpdateResponse)
async def update_integration(
    integration_id: str,
    integration_update: IntegrationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Rate limiting
    rate_limit_key = f"{RATE_LIMIT_UPDATE['key']}:{current_user.id}"
    if RateLimiter.is_rate_limited(rate_limit_key, RATE_LIMIT_UPDATE["max_requests"], RATE_LIMIT_UPDATE["window_seconds"]):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many integration update attempts. Try again later."
        )

    # Find integration
    integration = db.query(Integration).filter(Integration.id == integration_id).first()

    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Integration with id {integration_id} not found"
        )

    # Update integration fields if provided
    if integration_update.type is not None:
        integration.type = integration_update.type
    if integration_update.name is not None:
        integration.name = integration_update.name
    if integration_update.credentials_encrypted is not None:
        integration.credentials_encrypted = integration_update.credentials_encrypted
    if integration_update.config is not None:
        integration.config = integration_update.config
    if integration_update.status is not None:
        integration.status = integration_update.status

    integration.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(integration)

    return IntegrationUpdateResponse(
        integration=Integration(
            id=str(integration.id),
            organization_id=str(integration.organization_id),
            type=integration.type,
            name=integration.name,
            credentials_encrypted=integration.credentials_encrypted,
            config=integration.config,
            status=integration.status.value,
            last_sync=integration.last_sync,
            created_at=integration.created_at
        )
    )


# DELETE /api/v1/integrations/{id} - Delete integration
@router.delete("/integrations/{integration_id}", response_model=IntegrationDeleteResponse)
async def delete_integration(
    integration_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Rate limiting
    rate_limit_key = f"{RATE_LIMIT_DELETE['key']}:{current_user.id}"
    if RateLimiter.is_rate_limited(rate_limit_key, RATE_LIMIT_DELETE["max_requests"], RATE_LIMIT_DELETE["window_seconds"]):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many integration deletion attempts. Try again later."
        )

    # Find integration
    integration = db.query(Integration).filter(Integration.id == integration_id).first()

    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Integration with id {integration_id} not found"
        )

    # Delete integration
    db.delete(integration)
    db.commit()

    return IntegrationDeleteResponse()


# POST /api/v1/integrations/{id}/test - Test integration connection
@router.post("/integrations/{integration_id}/test", response_model=IntegrationTestResponse)
async def test_integration(
    integration_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Rate limiting
    rate_limit_key = f"{RATE_LIMIT_TEST['key']}:{current_user.id}"
    if RateLimiter.is_rate_limited(rate_limit_key, RATE_LIMIT_TEST["max_requests"], RATE_LIMIT_TEST["window_seconds"]):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many integration test attempts. Try again later."
        )

    # Find integration
    integration = db.query(Integration).filter(Integration.id == integration_id).first()

    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Integration with id {integration_id} not found"
        )

    try:
        # Simulate integration test (in a real implementation, this would test the actual connection)
        # For now, we'll just return a success response based on the integration type
        test_result = {
            "type": integration.type,
            "status": "connected",
            "timestamp": datetime.utcnow().isoformat()
        }

        # Simulate different test behaviors based on integration type
        if integration.type == "gmail":
            test_result["message"] = "Gmail connection test successful"
        elif integration.type == "slack":
            test_result["message"] = "Slack connection test successful"
        elif integration.type == "rest_api":
            test_result["message"] = "REST API connection test successful"
        elif integration.type == "webhook":
            test_result["message"] = "Webhook configuration test successful"

        return IntegrationTestResponse(
            success=True,
            message=f"{integration.type} integration test completed successfully",
            output=test_result
        )

    except Exception as e:
        return IntegrationTestResponse(
            success=False,
            message=f"{integration.type} integration test failed",
            error=str(e)
        )


# GET /api/v1/integrations/{id}/actions - List available actions for integration
@router.get("/integrations/{integration_id}/actions", response_model=IntegrationActionsResponse)
async def get_integration_actions(
    integration_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Find integration
    integration = db.query(Integration).filter(Integration.id == integration_id).first()

    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Integration with id {integration_id} not found"
        )

    # Get available actions based on integration type
    actions = await get_integration_actions(integration.type)

    return IntegrationActionsResponse(
        actions=actions
    )


# Error handler for validation errors
@router.exception_handler(IntegrationValidationErrorResponse)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=exc.json(),
        headers=RateLimiter.get_rate_limit_header("integrations:validation", 100, 3600)
    )


# Error handler for general errors
@router.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=IntegrationErrorResponse(
            detail="An unexpected error occurred",
            error_code="INTERNAL_SERVER_ERROR",
            timestamp=datetime.utcnow()
        ).json(),
        headers=RateLimiter.get_rate_limit_header("integrations:errors", 10, 3600)
    )