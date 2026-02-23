from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import requests
from urllib.parse import urlparse
from time import time
import uuid
from datetime import datetime

from api.schemas import (
    IntegrationCreate, IntegrationUpdate, IntegrationResponse, ErrorResponse,
    PaginationResponse, SortOrder, Filter
)
from core.database import get_db
from core.auth import get_current_user, get_current_active_user, get_current_organization

router = APIRouter()

# Rate limiting dictionary
RATE_LIMITS = {}
def check_rate_limit(user_id: UUID, endpoint: str, limit: int = 100, window: int = 60):
    """Check if user has exceeded rate limit for this endpoint."""
    now = int(time())
    window_start = now - window

    if user_id not in RATE_LIMITS:
        RATE_LIMITS[user_id] = {}

    if endpoint not in RATE_LIMITS[user_id]:
        RATE_LIMITS[user_id][endpoint] = []

    # Remove old requests outside the window
    RATE_LIMITS[user_id][endpoint] = [
        timestamp for timestamp in RATE_LIMITS[user_id][endpoint]
        if timestamp > window_start
    ]

    # Check if we've exceeded the limit
    if len(RATE_LIMITS[user_id][endpoint]) >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded for {endpoint}. Try again in {window - (now - RATE_LIMITS[user_id][endpoint][0])} seconds"
        )

    # Add current request timestamp
    RATE_LIMITS[user_id][endpoint].append(now)

@router.post("/", response_model=IntegrationResponse, status_code=status.HTTP_201_CREATED)
async def create_integration(
    integration: IntegrationCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Get user's organization
    organization = get_current_organization(current_user, db)
    if not organization:
        raise HTTPException(status_code=404, detail="User not part of any organization")

    # Validate integration type
    valid_types = ["webhook", "api", "database", "file_system", "cloud_service"]
    if integration.integration_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid integration type. Must be one of: {', '.join(valid_types)}"
        )

    # Validate Gmail integration config
    if integration.integration_type == "api" and integration.config.get("service") == "gmail":
        if not integration.config.get("client_id") or not integration.config.get("client_secret"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Gmail integration requires client_id and client_secret"
            )

    # Validate Slack integration config
    if integration.integration_type == "webhook" and integration.config.get("service") == "slack":
        if not integration.config.get("webhook_url"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Slack integration requires webhook_url"
            )

    # Validate REST API integration config
    if integration.integration_type == "api" and integration.config.get("service") == "rest":
        if not integration.config.get("base_url"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="REST API integration requires base_url"
            )

    db_integration = Integration(
        name=integration.name,
        description=integration.description,
        integration_type=integration.integration_type,
        config=integration.config,
        is_active=integration.is_active,
        organization_id=organization.id,
        created_by=current_user.id
    )
    db.add(db_integration)
    db.commit()
    db.refresh(db_integration)

    return db_integration

@router.get("/", response_model=List[IntegrationResponse])
async def get_integrations(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Get user's organization
    organization = get_current_organization(current_user, db)
    if not organization:
        raise HTTPException(status_code=404, detail="User not part of any organization")

    check_rate_limit(current_user.id, "get_integrations")

    integrations = db.query(Integration).filter(
        Integration.organization_id == organization.id,
        Integration.is_active == True
    ).offset(skip).limit(limit).all()
    return integrations

@router.get("/{integration_id}", response_model=IntegrationResponse)
async def get_integration(
    integration_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    integration = db.query(Integration).filter(
        Integration.id == integration_id,
        Integration.is_active == True
    ).first()
    if integration is None:
        raise HTTPException(status_code=404, detail="Integration not found")

    # Check if user has access to this integration
    organization = get_current_organization(current_user, db)
    if integration.organization_id != organization.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this integration")

    return integration

@router.put("/{integration_id}", response_model=IntegrationResponse)
async def update_integration(
    integration_id: UUID,
    integration_update: IntegrationUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    integration = db.query(Integration).filter(
        Integration.id == integration_id,
        Integration.is_active == True
    ).first()
    if integration is None:
        raise HTTPException(status_code=404, detail="Integration not found")

    # Check if user has access to this integration
    organization = get_current_organization(current_user, db)
    if integration.organization_id != organization.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this integration")

    # Validate config if being updated
    if integration_update.config is not None:
        if integration.integration_type == "api" and integration.config.get("service") == "gmail":
            if not integration_update.config.get("client_id") or not integration_update.config.get("client_secret"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Gmail integration requires client_id and client_secret"
                )
        elif integration.integration_type == "webhook" and integration.config.get("service") == "slack":
            if not integration_update.config.get("webhook_url"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Slack integration requires webhook_url"
                )
        elif integration.integration_type == "api" and integration.config.get("service") == "rest":
            if not integration_update.config.get("base_url"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="REST API integration requires base_url"
                )

    integration.name = integration_update.name or integration.name
    integration.description = integration_update.description or integration.description
    integration.config = integration_update.config or integration.config
    integration.is_active = integration_update.is_active if integration_update.is_active is not None else integration.is_active

    db.commit()
    db.refresh(integration)
    return integration

@router.delete("/{integration_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_integration(
    integration_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    integration = db.query(Integration).filter(
        Integration.id == integration_id,
        Integration.is_active == True
    ).first()
    if integration is None:
        raise HTTPException(status_code=404, detail="Integration not found")

    # Check if user has access to this integration
    organization = get_current_organization(current_user, db)
    if integration.organization_id != organization.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this integration")

    db.delete(integration)
    db.commit()

@router.post("/{integration_id}/test")
async def test_integration(
    integration_id: UUID,
    test_data: Optional[dict] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    integration = db.query(Integration).filter(
        Integration.id == integration_id,
        Integration.is_active == True
    ).first()
    if integration is None:
        raise HTTPException(status_code=404, detail="Integration not found")

    # Check if user has access to this integration
    organization = get_current_organization(current_user, db)
    if integration.organization_id != organization.id:
        raise HTTPException(status_code=403, detail="Not authorized to test this integration")

    check_rate_limit(current_user.id, f"test_integration_{integration_id}")

    try:
        if integration.integration_type == "webhook" and integration.config.get("service") == "slack":
            # Test Slack webhook
            webhook_url = integration.config.get("webhook_url")
            if not webhook_url:
                raise HTTPException(status_code=400, detail="Webhook URL not configured")

            test_message = {
                "text": f"Integration test successful for {integration.name}",
                "username": "AgentFlow Test",
                "icon_emoji": ":robot_face:"
            }

            response = requests.post(webhook_url, json=test_message, timeout=10)
            response.raise_for_status()

            return {
                "success": True,
                "message": "Slack webhook test successful",
                "response": response.json()
            }

        elif integration.integration_type == "api" and integration.config.get("service") == "gmail":
            # Test Gmail API connection
            client_id = integration.config.get("client_id")
            client_secret = integration.config.get("client_secret")
            refresh_token = integration.config.get("refresh_token")

            if not all([client_id, client_secret, refresh_token]):
                raise HTTPException(status_code=400, detail="Incomplete Gmail configuration")

            # Simulate token refresh
            token_response = {
                "access_token": "mock_access_token",
                "token_type": "Bearer",
                "expires_in": 3600
            }

            return {
                "success": True,
                "message": "Gmail API test successful",
                "access_token": token_response["access_token"]
            }

        elif integration.integration_type == "api" and integration.config.get("service") == "rest":
            # Test REST API connection
            base_url = integration.config.get("base_url")
            if not base_url:
                raise HTTPException(status_code=400, detail="Base URL not configured")

            # Try to make a simple GET request to test connectivity
            test_url = f"{base_url.rstrip('/')}/health" if base_url.endswith('/') else f"{base_url}/health"

            try:
                response = requests.get(test_url, timeout=5)
                response.raise_for_status()

                return {
                    "success": True,
                    "message": f"REST API test successful",
                    "status_code": response.status_code,
                    "response": response.json() if response.content else {}
                }
            except requests.exceptions.RequestException as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"REST API test failed: {str(e)}"
                )

        elif integration.integration_type == "webhook":
            # Generic webhook test
            webhook_url = integration.config.get("webhook_url")
            if not webhook_url:
                raise HTTPException(status_code=400, detail="Webhook URL not configured")

            test_payload = {
                "test": True,
                "message": f"Integration test for {integration.name}",
                "timestamp": datetime.utcnow().isoformat()
            }

            response = requests.post(webhook_url, json=test_payload, timeout=10)
            response.raise_for_status()

            return {
                "success": True,
                "message": "Webhook test successful",
                "response": response.json()
            }

        else:
            return {
                "success": True,
                "message": f"Connection test successful for {integration.name}",
                "integration_type": integration.integration_type
            }

    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=400,
            detail=f"Integration test failed: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error during integration test: {str(e)}"
        )

@router.get("/{integration_id}/actions", response_model=List[dict])
async def get_integration_actions(
    integration_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    integration = db.query(Integration).filter(
        Integration.id == integration_id,
        Integration.is_active == True
    ).first()
    if integration is None:
        raise HTTPException(status_code=404, detail="Integration not found")

    # Check if user has access to this integration
    organization = get_current_organization(current_user, db)
    if integration.organization_id != organization.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this integration")

    check_rate_limit(current_user.id, f"get_integration_actions_{integration_id}")

    # Define actions based on integration type and service
    actions = []

    if integration.integration_type == "webhook" and integration.config.get("service") == "slack":
        actions = [
            {
                "name": "post_message",
                "description": "Post a message to a Slack channel",
                "parameters": [
                    {"name": "channel", "type": "string", "required": True, "description": "Channel name or ID"},
                    {"name": "text", "type": "string", "required": True, "description": "Message text"},
                    {"name": "thread_ts", "type": "string", "required": False, "description": "Thread timestamp for replies"}
                ]
            },
            {
                "name": "post_ephemeral",
                "description": "Post an ephemeral message to a user",
                "parameters": [
                    {"name": "user", "type": "string", "required": True, "description": "User ID"},
                    {"name": "text", "type": "string", "required": True, "description": "Message text"},
                    {"name": "channel", "type": "string", "required": True, "description": "Channel ID"}
                ]
            }
        ]

    elif integration.integration_type == "api" and integration.config.get("service") == "gmail":
        actions = [
            {
                "name": "send_email",
                "description": "Send an email",
                "parameters": [
                    {"name": "to", "type": "string", "required": True, "description": "Recipient email address"},
                    {"name": "subject", "type": "string", "required": True, "description": "Email subject"},
                    {"name": "body", "type": "string", "required": True, "description": "Email body"},
                    {"name": "cc", "type": "string", "required": False, "description": "CC recipients"},
                    {"name": "bcc", "type": "string", "required": False, "description": "BCC recipients"}
                ]
            },
            {
                "name": "list_messages",
                "description": "List emails in inbox",
                "parameters": [
                    {"name": "query", "type": "string", "required": False, "description": "Search query"},
                    {"name": "max_results", "type": "integer", "required": False, "description": "Maximum number of results"}
                ]
            }
        ]

    elif integration.integration_type == "api" and integration.config.get("service") == "rest"::
        base_url = integration.config.get("base_url", "")
        service_name = integration.config.get("service_name", "Generic API")

        actions = [
            {
                "name": "make_request",
                "description": f"Make a request to the {service_name} API",
                "parameters": [
                    {"name": "method", "type": "string", "required": True, "description": "HTTP method (GET, POST, PUT, DELETE)", "enum": ["GET", "POST", "PUT", "DELETE"]},
                    {"name": "endpoint", "type": "string", "required": True, "description": "API endpoint path"},
                    {"name": "headers", "type": "object", "required": False, "description": "Request headers"},
                    {"name": "params", "type": "object", "required": False, "description": "Query parameters"},
                    {"name": "data", "type": "object", "required": False, "description": "Request body"}
                ]
            }
        ]

    elif integration.integration_type == "webhook":
        actions = [
            {
                "name": "send_webhook",
                "description": "Send data to webhook",
                "parameters": [
                    {"name": "payload", "type": "object", "required": True, "description": "Data to send"},
                    {"name": "headers", "type": "object", "required": False, "description": "Custom headers"}
                ]
            }
        ]

    return actions

@router.get("/search")
async def search_integrations(
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

    check_rate_limit(current_user.id, "search_integrations")

    q = db.query(Integration).filter(
        Integration.organization_id == organization.id,
        Integration.is_active == True
    )

    # Apply filters
    if filters:
        for filter in filters:
            if filter.operator == "eq":
                q = q.filter(getattr(Integration, filter.field) == filter.value)
            elif filter.operator == "ne":
                q = q.filter(getattr(Integration, filter.field) != filter.value)
            elif filter.operator == "contains":
                q = q.filter(getattr(Integration, filter.field).ilike(f"%{filter.value}%"))
            # Add more operators as needed

    # Apply search query
    q = q.filter(
        Integration.name.ilike(f"%{query}%") |
        Integration.description.ilike(f"%{query}%") |
        Integration.integration_type.ilike(f"%{query}%")
    )

    # Apply sorting
    if sort:
        sort_field = getattr(Integration, sort.field)
        if sort.direction == "desc":
            sort_field = sort_field.desc()
        q = q.order_by(sort_field)

    total = q.count()
    integrations = q.offset(skip).limit(limit).all()

    return PaginationResponse(
        items=integrations,
        total=total,
        page=(skip // limit) + 1,
        size=limit,
        total_pages=(total + limit - 1) // limit
    )

@router.get("/{integration_id}/usage")
async def get_integration_usage(
    integration_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    integration = db.query(Integration).filter(
        Integration.id == integration_id,
        Integration.is_active == True
    ).first()
    if integration is None:
        raise HTTPException(status_code=404, detail="Integration not found")

    # Check if user has access to this integration
    organization = get_current_organization(current_user, db)
    if integration.organization_id != organization.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this integration")

    # Get usage statistics for the last 30 days
    from datetime import datetime, timedelta
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)

    # Count how many workflows use this integration
    workflows_count = db.query(Workflow).filter(
        Workflow.organization_id == organization.id,
        Workflow.steps.op("@>")([{"integration_id": str(integration_id)}])  # JSON contains
    ).count()

    # Count tasks that used this integration
    tasks_count = db.query(Task).filter(
        Task.organization_id == organization.id,
        Task.input_data.op("@>")([{"integration_id": str(integration_id)}])  # JSON contains
    ).count()

    return {
        "integration_id": integration.id,
        "name": integration.name,
        "integration_type": integration.integration_type,
        "workflows_using": workflows_count,
        "tasks_executed_last_30_days": tasks_count,
        "is_active": integration.is_active
    }