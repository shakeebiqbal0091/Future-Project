from typing import Any, Dict, Optional, List
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
from app.core.integrations.slack_integration_manager import SlackIntegrationManager

router = APIRouter()

# Authentication dependencies
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# Helper functions
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends()) -> User:
    return AuthHandler.get_current_active_user(token, db)

async def get_current_org(user: User = Depends(get_current_user)) -> User:
    return user

# Rate limiting configurations
RATE_LIMIT_CREATE = {"key": "integrations:create", "max_requests": 10, "window_seconds": 3600}
RATE_LIMIT_UPDATE = {"key": "integrations:update", "max_requests": 20, "window_seconds": 3600}
RATE_LIMIT_DELETE = {"key": "integrations:delete", "max_requests": 20, "window_seconds": 3600}
RATE_LIMIT_TEST = {"key": "integrations:test", "max_requests": 50, "window_seconds": 3600}

# Slack-specific validation
async def validate_slack_integration_data(integration_data: Dict[str, Any], db: Session) -> List[Any]:
    errors = []

    # Validate type
    if not integration_data.get("type"):
        errors.append({"field": "type", "message": "Integration type is required"})
    elif integration_data["type"] != "slack":
        errors.append({"field": "type", "message": "Invalid integration type for Slack"})

    # Validate name
    if not integration_data.get("name"):
        errors.append({"field": "name", "message": "Integration name is required"})
    elif len(integration_data["name"]) > 100:
        errors.append({"field": "name", "message": "Integration name must be less than 100 characters"})

    # Validate credentials
    if not integration_data.get("credentials_encrypted"):
        errors.append({"field": "credentials_encrypted", "message": "Credentials are required"})

    # Validate config structure
    config = integration_data.get("config", {})
    if "bot_token" not in config:
        errors.append({"field": "config.bot_token", "message": "Slack bot token is required"})

    return errors

# Helper function to get available actions for Slack integration
async def get_slack_integration_actions() -> List[Any]:
    return [
        {
            "name": "post_message",
            "description": "Post a message to Slack channel",
            "parameters": {
                "channel": "string (channel ID or name)",
                "text": "string",
                "thread_ts": "string (optional, for replying to threads)",
                "blocks": "list (optional, Block Kit blocks)"
            }
        },
        {
            "name": "update_message",
            "description": "Update an existing message",
            "parameters": {
                "channel": "string (channel ID)",
                "ts": "string (timestamp of message to update)",
                "text": "string",
                "blocks": "list (optional, Block Kit blocks)"
            }
        },
        {
            "name": "delete_message",
            "description": "Delete a message",
            "parameters": {
                "channel": "string (channel ID)",
                "ts": "string (timestamp of message to delete)"
            }
        },
        {
            "name": "upload_file",
            "description": "Upload a file to Slack",
            "parameters": {
                "channels": "string (comma-separated channel IDs)",
                "file_content": "bytes (file content)",
                "filename": "string",
                "title": "string (optional)",
                "initial_comment": "string (optional)"
            }
        },
        {
            "name": "create_channel",
            "description": "Create a new channel",
            "parameters": {
                "name": "string",
                "is_private": "boolean (optional, default false)"
            }
        },
        {
            "name": "archive_channel",
            "description": "Archive a channel",
            "parameters": {
                "channel_id": "string (channel ID)"
            }
        },
        {
            "name": "invite_user_to_channel",
            "description": "Invite a user to a channel",
            "parameters": {
                "channel_id": "string (channel ID)",
                "user_id": "string (user ID)"
            }
        }
    ]

# POST /api/v1/integrations/slack - Create a new Slack integration
@router.post("/integrations/slack", response_model=IntegrationCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_slack_integration(
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

    # Validate Slack-specific data
    errors.extend(await validate_slack_integration_data(integration_data.dict(), db))

    if len(errors) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Validation error",
            headers=RateLimiter.get_rate_limit_header(rate_limit_key, RATE_LIMIT_CREATE["max_requests"], RATE_LIMIT_CREATE["window_seconds"]),
            content={"detail": "Validation error", "errors": errors}.__str__()
        )

    # Create new integration
    new_integration = Integration(
        organization_id=current_user.id,
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
        ),
        message="Slack integration created successfully"
    )

# POST /api/v1/integrations/slack/test - Test Slack integration connection
@router.post("/integrations/slack/test", response_model=IntegrationTestResponse)
async def test_slack_integration(
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
            detail=f"Slack integration with id {integration_id} not found"
        )

    if integration.type != "slack":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Integration is not a Slack integration"
        )

    try:
        # Create SlackIntegrationManager instance
        slack_manager = SlackIntegrationManager(Integration(
            id=str(integration.id),
            organization_id=str(integration.organization_id),
            type=integration.type,
            name=integration.name,
            credentials_encrypted=integration.credentials_encrypted,
            config=integration.config,
            status=integration.status.value,
            last_sync=integration.last_sync,
            created_at=integration.created_at
        ))

        # Test connection
        result = slack_manager.test_connection()

        return result

    except Exception as e:
        return IntegrationTestResponse(
            success=False,
            message=f"Slack integration test failed: {str(e)}",
            error=str(e)
        )

# GET /api/v1/integrations/slack/actions - Get available Slack actions
@router.get("/integrations/slack/actions", response_model=IntegrationActionsResponse)
async def get_slack_actions(
    integration_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Find integration
    integration = db.query(Integration).filter(Integration.id == integration_id).first()

    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Slack integration with id {integration_id} not found"
        )

    if integration.type != "slack":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Integration is not a Slack integration"
        )

    try:
        # Create SlackIntegrationManager instance
        slack_manager = SlackIntegrationManager(Integration(
            id=str(integration.id),
            organization_id=str(integration.organization_id),
            type=integration.type,
            name=integration.name,
            credentials_encrypted=integration.credentials_encrypted,
            config=integration.config,
            status=integration.status.value,
            last_sync=integration.last_sync,
            created_at=integration.created_at
        ))

        # Get available actions
        actions = slack_manager.get_available_actions()

        return IntegrationActionsResponse(
            actions=actions
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get Slack actions: {str(e)}"
        )

# POST /api/v1/integrations/slack/action - Execute Slack action
@router.post("/integrations/slack/action", response_model=IntegrationTestResponse)
async def execute_slack_action(
    integration_id: str,
    action_name: str,
    action_params: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Find integration
    integration = db.query(Integration).filter(Integration.id == integration_id).first()

    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Slack integration with id {integration_id} not found"
        )

    if integration.type != "slack":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Integration is not a Slack integration"
        )

    try:
        # Create SlackIntegrationManager instance
        slack_manager = SlackIntegrationManager(Integration(
            id=str(integration.id),
            organization_id=str(integration.organization_id),
            type=integration.type,
            name=integration.name,
            credentials_encrypted=integration.credentials_encrypted,
            config=integration.config,
            status=integration.status.value,
            last_sync=integration.last_sync,
            created_at=integration.created_at
        ))

        # Execute the action
        result = slack_manager.execute_action(action_name, action_params)

        return result

    except Exception as e:
        return IntegrationTestResponse(
            success=False,
            message=f"Action '{action_name}' execution failed: {str(e)}",
            error=str(e)
        )

# Error handlers
@router.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred", "error_code": "INTERNAL_SERVER_ERROR", "timestamp": datetime.utcnow().isoformat()},
        headers=RateLimiter.get_rate_limit_header("slack:errors", 10, 3600)
    )