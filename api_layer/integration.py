from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import json
import httpx
from pydantic import ValidationError

from ..shared.database import get_db
from ..shared.security import get_current_active_user, get_current_active_superuser, get_current_organization_member
from ..shared.models import User, Organization, Integration
from ..shared.schemas import (
    Integration, IntegrationCreate, IntegrationUpdate, User, Organization,
    Pagination, PaginatedResponse
)
from ..shared.utils import (
    paginate_query, create_paginated_response,
    filter_by_organization, get_user_organizations
)

router = APIRouter()


@router.get("/", response_model=List[Integration])
def get_integrations(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    organization_id: Optional[int] = None,
    integration_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    pagination: Pagination = Depends()
):
    """Get all integrations with filtering options."""

    # Build base query
    query = db.query(Integration)

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

        query = query.filter(Integration.organization_id == organization_id)
    else:
        # Get integrations for all organizations the user belongs to
        user_organizations = get_user_organizations(db, current_user.id)
        organization_ids = [org.id for org in user_organizations]
        query = query.filter(Integration.organization_id.in_(organization_ids))

    # Filter by type
    if integration_type:
        query = query.filter(Integration.type == integration_type)

    # Filter by active status
    if is_active is not None:
        query = query.filter(Integration.is_active == is_active)

    # Order by creation date (newest first)
    query = query.order_by(Integration.created_at.desc())

    paginated_query, total_count = paginate_query(db, query, pagination)
    items = paginated_query.all()

    return create_paginated_response(items, total_count, pagination)


@router.post("/", response_model=Integration)
def create_integration(
    integration_data: IntegrationCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Create a new integration."""

    # Verify user belongs to the specified organization
    org_query = db.query(Organization).filter(Organization.id == integration_data.organization_id)
    org_query = filter_by_organization(db, org_query, integration_data.organization_id, current_user)
    organization = org_query.first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found or access denied"
        )

    # Check if user is member of this organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == integration_data.organization_id
    ).first()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this organization"
        )

    # Only owners and admins can create integrations
    if member.role not in ["owner", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owners and admins can create integrations"
        )

    # Check if integration with same name already exists in organization
    existing_integration = db.query(Integration).filter(
        Integration.name == integration_data.name,
        Integration.organization_id == integration_data.organization_id
    ).first()

    if existing_integration:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Integration with this name already exists in the organization"
        )

    # Validate integration type and configuration
    try:
        validate_integration_configuration(integration_data.type, integration_data.config)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid configuration for {integration_data.type}: {str(e)}"
        )

    # Create integration
    integration = Integration(
        name=integration_data.name,
        type=integration_data.type,
        config=integration_data.config,
        is_active=True,
        organization_id=integration_data.organization_id
    )

    db.add(integration)
    db.commit()
    db.refresh(integration)

    return Integration.from_orm(integration)


@router.get("/{integration_id}", response_model=Integration)
def get_integration(
    integration_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get integration by ID."""

    integration = db.query(Integration).filter(Integration.id == integration_id).first()

    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found"
        )

    # Verify user has access to this integration's organization
    org_query = db.query(Organization).filter(Organization.id == integration.organization_id)
    org_query = filter_by_organization(db, org_query, integration.organization_id, current_user)
    organization = org_query.first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found or access denied"
        )

    return Integration.from_orm(integration)


@router.put("/{integration_id}", response_model=Integration)
def update_integration(
    integration_id: int,
    integration_update: IntegrationUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update integration."""

    integration = db.query(Integration).filter(Integration.id == integration_id).first()

    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found"
        )

    # Verify user has access to this integration's organization
    org_query = db.query(Organization).filter(Organization.id == integration.organization_id)
    org_query = filter_by_organization(db, org_query, integration.organization_id, current_user)
    organization = org_query.first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found or access denied"
        )

    # Check if user is member of this organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == integration.organization_id
    ).first()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this organization"
        )

    # Only owners and admins can update integrations
    if member.role not in ["owner", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owners and admins can update integrations"
        )

    # Validate configuration if being updated
    if integration_update.config is not None:
        try:
            validate_integration_configuration(integration.type, integration_update.config)
        except ValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid configuration for {integration.type}: {str(e)}"
            )

    if integration_update.name:
        # Check if new name conflicts with existing integration in same organization
        existing_integration = db.query(Integration).filter(
            Integration.name == integration_update.name,
            Integration.organization_id == integration.organization_id,
            Integration.id != integration_id
        ).first()

        if existing_integration:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Integration with this name already exists in the organization"
            )

        integration.name = integration_update.name

    if integration_update.config is not None:
        integration.config = integration_update.config

    if integration_update.is_active is not None:
        integration.is_active = integration_update.is_active

    db.commit()
    db.refresh(integration)

    return Integration.from_orm(integration)


@router.delete("/{integration_id}")
def delete_integration(
    integration_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete integration."""

    integration = db.query(Integration).filter(Integration.id == integration_id).first()

    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found"
        )

    # Verify user has access to this integration's organization
    org_query = db.query(Organization).filter(Organization.id == integration.organization_id)
    org_query = filter_by_organization(db, org_query, integration.organization_id, current_user)
    organization = org_query.first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found or access denied"
        )

    # Check if user is member of this organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == integration.organization_id
    ).first()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this organization"
        )

    # Only owners and admins can delete integrations
    if member.role not in ["owner", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owners and admins can delete integrations"
        )

    db.delete(integration)
    db.commit()

    return {"message": "Integration deleted successfully"}


@router.post("/{integration_id}/test")
def test_integration(
    integration_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Test integration connectivity."""

    integration = db.query(Integration).filter(Integration.id == integration_id).first()

    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found"
        )

    # Verify user has access to this integration's organization
    org_query = db.query(Organization).filter(Organization.id == integration.organization_id)
    org_query = filter_by_organization(db, org_query, integration.organization_id, current_user)
    organization = org_query.first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found or access denied"
        )

    # Test the integration based on its type
    try:
        if integration.type == "slack":
            return test_slack_integration(integration)
        elif integration.type == "teams":
            return test_teams_integration(integration)
        elif integration.type == "email":
            return test_email_integration(integration)
        elif integration.type == "webhook":
            return test_webhook_integration(integration)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported integration type: {integration.type}"
            )
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/{integration_id}/sync")
def sync_integration(
    integration_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Sync integration data."""

    integration = db.query(Integration).filter(Integration.id == integration_id).first()

    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found"
        )

    # Verify user has access to this integration's organization
    org_query = db.query(Organization).filter(Organization.id == integration.organization_id)
    org_query = filter_by_organization(db, org_query, integration.organization_id, current_user)
    organization = org_query.first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found or access denied"
        )

    # Check if user is member of this organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == integration.organization_id
    ).first()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this organization"
        )

    # Only owners and admins can sync integrations
    if member.role not in ["owner", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owners and admins can sync integrations"
        )

    # Perform sync based on integration type
    try:
        if integration.type == "slack":
            return sync_slack_integration(integration)
        elif integration.type == "teams":
            return sync_teams_integration(integration)
        elif integration.type == "email":
            return sync_email_integration(integration)
        elif integration.type == "webhook":
            return sync_webhook_integration(integration)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported integration type: {integration.type}"
            )
    except Exception as e:
        return {"success": False, "error": str(e), "message": "Sync failed"}


@router.get("/types", response_model=List[Dict[str, Any]])
def get_integration_types():
    """Get available integration types."""

    return [
        {
            "type": "slack",
            "name": "Slack",
            "description": "Slack workspace integration",
            "icon": "💬",
            "config_fields": [
                {"name": "webhook_url", "type": "string", "required": True, "description": "Slack webhook URL"},
                {"name": "channel", "type": "string", "required": True, "description": "Slack channel to post to"},
                {"name": "bot_name", "type": "string", "required": False, "description": "Bot display name"}
            ]
        },
        {
            "type": "teams",
            "name": "Microsoft Teams",
            "description": "Microsoft Teams integration",
            "icon": "💼",
            "config_fields": [
                {"name": "webhook_url", "type": "string", "required": True, "description": "Teams webhook URL"},
                {"name": "team_name", "type": "string", "required": True, "description": "Team name"},
                {"name": "bot_name", "type": "string", "required": False, "description": "Bot display name"}
            ]
        },
        {
            "type": "email",
            "name": "Email",
            "description": "Email notifications",
            "icon": "✉️",
            "config_fields": [
                {"name": "smtp_host", "type": "string", "required": True, "description": "SMTP host"},
                {"name": "smtp_port", "type": "integer", "required": True, "description": "SMTP port"},
                {"name": "username", "type": "string", "required": True, "description": "SMTP username"},
                {"name": "password", "type": "string", "required": True, "description": "SMTP password"},
                {"name": "from_email", "type": "string", "required": True, "description": "From email address"},
                {"name": "from_name", "type": "string", "required": False, "description": "From name"}
            ]
        },
        {
            "type": "webhook",
            "name": "Webhook",
            "description": "Custom webhook integration",
            "icon": "🔗",
            "config_fields": [
                {"name": "endpoint", "type": "string", "required": True, "description": "Webhook endpoint URL"},
                {"name": "method", "type": "string", "required": False, "description": "HTTP method (GET, POST, PUT, etc.)"},
                {"name": "headers", "type": "object", "required": False, "description": "Custom headers"},
                {"name": "auth_type", "type": "string", "required": False, "description": "Authentication type (none, basic, bearer)"}
            ]
        },
        {
            "type": "github",
            "name": "GitHub",
            "description": "GitHub integration",
            "icon": "🐙",
            "config_fields": [
                {"name": "token", "type": "string", "required": True, "description": "GitHub personal access token"},
                {"name": "repository", "type": "string", "required": True, "description": "Repository name (owner/repo)"},
                {"name": "events", "type": "array", "required": False, "description": "Events to subscribe to"}
            ]
        },
        {
            "type": "gitlab",
            "name": "GitLab",
            "description": "GitLab integration",
            "icon": "🦖",
            "config_fields": [
                {"name": "token", "type": "string", "required": True, "description": "GitLab personal access token"},
                {"name": "project_id", "type": "integer", "required": True, "description": "Project ID"},
                {"name": "webhook_url", "type": "string", "required": True, "description": "Webhook URL"}
            ]
        }
    ]


@router.get("/{integration_id}/stats", response_model=Dict[str, Any])
def get_integration_stats(
    integration_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get integration statistics."""

    integration = db.query(Integration).filter(Integration.id == integration_id).first()

    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found"
        )

    # Verify user has access to this integration's organization
    org_query = db.query(Organization).filter(Organization.id == integration.organization_id)
    org_query = filter_by_organization(db, org_query, integration.organization_id, current_user)
    organization = org_query.first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found or access denied"
        )

    # In a real implementation, you would query integration usage metrics
    # For now, we'll return sample data

    return {
        "integration": {
            "id": integration.id,
            "name": integration.name,
            "type": integration.type,
            "is_active": integration.is_active
        },
        "usage": {
            "total_messages": 1234,
            "success_rate": 98.5,  # percentage
            "last_7d_messages": 234,
            "last_30d_messages": 890,
            "errors": 12
        },
        "performance": {
            "average_response_time": 0.25,  # in seconds
            "peak_hour": "14:00",
            "messages_per_hour": 15.2
        },
        "health": {
            "status": "healthy" if integration.is_active else "inactive",
            "last_sync": (datetime.datetime.now() - datetime.timedelta(hours=1)).isoformat(),
            "next_sync": (datetime.datetime.now() + datetime.timedelta(hours=1)).isoformat()
        }
    }


@router.get("/{integration_id}/activity", response_model=List[Dict[str, Any]])
def get_integration_activity(
    integration_id: int,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get recent integration activity."""

    integration = db.query(Integration).filter(Integration.id == integration_id).first()

    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found"
        )

    # Verify user has access to this integration's organization
    org_query = db.query(Organization).filter(Organization.id == integration.organization_id)
    org_query = filter_by_organization(db, org_query, integration.organization_id, current_user)
    organization = org_query.first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found or access denied"
        )

    # In a real implementation, you would retrieve activity logs from a logging system
    # For now, we'll return sample activity based on integration type

    activity = []

    if integration.type == "slack":
        activity = [
            {
                "timestamp": (datetime.datetime.now() - datetime.timedelta(minutes=5)).isoformat(),
                "event": "message_sent",
                "channel": integration.config.get("channel", "#general"),
                "message": "Hello from AI Agent Platform!",
                "status": "success"
            },
            {
                "timestamp": (datetime.datetime.now() - datetime.timedelta(minutes=30)).isoformat(),
                "event": "message_sent",
                "channel": integration.config.get("channel", "#general"),
                "message": "Workflow completed: User onboarding",
                "status": "success"
            }
        ][:limit]
    elif integration.type == "email":
        activity = [
            {
                "timestamp": (datetime.datetime.now() - datetime.timedelta(minutes=10)).isoformat(),
                "event": "email_sent",
                "to": "user@example.com",
                "subject": "Your workflow has completed",
                "status": "success"
            },
            {
                "timestamp": (datetime.datetime.now() - datetime.timedelta(hours=1)).isoformat(),
                "event": "email_sent",
                "to": "admin@example.com",
                "subject": "System alert: High token usage",
                "status": "success"
            }
        ][:limit]

    return activity


def validate_integration_configuration(integration_type: str, config: Dict[str, Any]):
    """Validate integration configuration based on type."""

    # In a real implementation, you would use Pydantic models or custom validation logic
    # For now, we'll do basic validation

    if integration_type == "slack":
        if "webhook_url" not in config or not config["webhook_url"]:
            raise ValueError("Slack integration requires webhook_url")
        if "channel" not in config or not config["channel"]:
            raise ValueError("Slack integration requires channel")
    elif integration_type == "teams":
        if "webhook_url" not in config or not config["webhook_url"]:
            raise ValueError("Teams integration requires webhook_url")
        if "team_name" not in config or not config["team_name"]:
            raise ValueError("Teams integration requires team_name")
    elif integration_type == "email":
        required_fields = ["smtp_host", "smtp_port", "username", "password", "from_email"]
        for field in required_fields:
            if field not in config or not config[field]:
                raise ValueError(f"Email integration requires {field}")
    elif integration_type == "webhook":
        if "endpoint" not in config or not config["endpoint"]:
            raise ValueError("Webhook integration requires endpoint")
    # Add validation for other integration types as needed


def test_slack_integration(integration: Integration) -> Dict[str, Any]:
    """Test Slack integration connectivity."""

    import requests
    from requests.exceptions import RequestException

    webhook_url = integration.config.get("webhook_url")
    channel = integration.config.get("channel", "#general")

    test_message = {
        "text": "🚀 AI Agent Platform Integration Test",
        "channel": channel,
        "username": integration.config.get("bot_name", "AI Agent")
    }

    try:
        response = requests.post(webhook_url, json=test_message, timeout=10)
        response.raise_for_status()

        return {"success": True, "message": "Slack integration test successful"}

    except RequestException as e:
        return {"success": False, "error": str(e)}


def test_teams_integration(integration: Integration) -> Dict[str, Any]:
    """Test Microsoft Teams integration connectivity."""

    import requests
    from requests.exceptions import RequestException

    webhook_url = integration.config.get("webhook_url")

    test_message = {
        "@type": "MessageCard",
        "themeColor": "0078D7",
        "title": "🚀 AI Agent Platform Integration Test",
        "text": "Microsoft Teams integration is working correctly!"
    }

    try:
        response = requests.post(webhook_url, json=test_message, timeout=10)
        response.raise_for_status()

        return {"success": True, "message": "Teams integration test successful"}

    except RequestException as e:
        return {"success": False, "error": str(e)}


def test_email_integration(integration: Integration) -> Dict[str, Any]:
    """Test email integration connectivity."""

    import smtplib
    from email.message import EmailMessage

    try:
        # Test SMTP connection
        with smtplib.SMTP(integration.config["smtp_host"], integration.config["smtp_port"]) as server:
            server.starttls()
            server.login(integration.config["username"], integration.config["password"])

        return {"success": True, "message": "Email integration test successful"}

    except Exception as e:
        return {"success": False, "error": str(e)}


def test_webhook_integration(integration: Integration) -> Dict[str, Any]:
    """Test webhook integration connectivity."""

    import requests
    from requests.exceptions import RequestException

    endpoint = integration.config.get("endpoint")
    method = integration.config.get("method", "POST")

    test_payload = {
        "test": True,
        "message": "AI Agent Platform webhook test",
        "timestamp": datetime.datetime.now().isoformat()
    }

    headers = integration.config.get("headers", {})

    try:
        if method.upper() == "GET":
            response = requests.get(endpoint, params=test_payload, headers=headers, timeout=10)
        else:
            response = requests.post(endpoint, json=test_payload, headers=headers, timeout=10)

        response.raise_for_status()

        return {"success": True, "message": "Webhook integration test successful"}

    except RequestException as e:
        return {"success": False, "error": str(e)}


def sync_slack_integration(integration: Integration) -> Dict[str, Any]:
    """Sync Slack integration data (e.g., channels, users)."""

    # In a real implementation, you would use the Slack API to sync data
    # For now, we'll return sample data

    return {
        "success": True,
        "message": "Slack integration synced successfully",
        "data": {
            "channels": ["#general", "#development", "#marketing"],
            "users_synced": 45,
            "last_sync": datetime.datetime.now().isoformat()
        }
    }


def sync_teams_integration(integration: Integration) -> Dict[str, Any]:
    """Sync Teams integration data."""

    # In a real implementation, you would use the Microsoft Graph API to sync data
    # For now, we'll return sample data

    return {
        "success": True,
        "message": "Teams integration synced successfully",
        "data": {
            "teams": ["Engineering", "Marketing", "Sales"],
            "users_synced": 120,
            "last_sync": datetime.datetime.now().isoformat()
        }
    }


def sync_email_integration(integration: Integration) -> Dict[str, Any]:
    """Sync email integration data (e.g., contacts, templates)."""

    # In a real implementation, you would sync email contacts or templates
    # For now, we'll return sample data

    return {
        "success": True,
        "message": "Email integration synced successfully",
        "data": {
            "contacts_synced": 345,
            "templates_available": 12,
            "last_sync": datetime.datetime.now().isoformat()
        }
    }


def sync_webhook_integration(integration: Integration) -> Dict[str, Any]:
    """Sync webhook integration data (e.g., test payload)."""

    # For webhooks, sync might mean testing the endpoint
    return test_webhook_integration(integration)