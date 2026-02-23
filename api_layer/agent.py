@router.get("/{agent_id}/versions", response_model=List[AgentVersion])
def get_agent_versions(
    agent_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    pagination: Pagination = Depends()
):
    """Get agent versions."""

    agent = db.query(Agent).filter(Agent.id == agent_id).first()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    # Verify user has access to this agent's organization
    org_query = db.query(Organization).filter(Organization.id == agent.organization_id)
    org_query = filter_by_organization(db, org_query, agent.organization_id, current_user)
    organization = org_query.first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found or access denied"
        )

    from ..shared.models import AgentVersion
    query = db.query(AgentVersion).filter(
        AgentVersion.agent_id == agent_id
    )

    paginated_query, total_count = paginate_query(db, query, pagination)
    items = paginated_query.all()

    return create_paginated_response(items, total_count, pagination)


@router.post("/{agent_id}/deploy")
def deploy_agent_version(
    agent_id: UUID,
    version_data: AgentVersionCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Deploy a specific agent version."""

    # Verify user has access to this agent's organization
    agent = db.query(Agent).filter(Agent.id == agent_id).first()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    org_query = db.query(Organization).filter(Organization.id == agent.organization_id)
    org_query = filter_by_organization(db, org_query, agent.organization_id, current_user)
    organization = org_query.first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found or access denied"
        )

    # Check if user is member of this organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == agent.organization_id
    ).first()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this organization"
        )

    # Only owners and admins can deploy agent versions
    if member.role not in ["owner", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owners and admins can deploy agent versions"
        )

    # Check if this version already exists
    existing_version = db.query(AgentVersion).filter(
        AgentVersion.agent_id == agent_id,
        AgentVersion.version == version_data.version
    ).first()

    if existing_version:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Version {version_data.version} already exists for this agent"
        )

    # Create new agent version
    agent_version = AgentVersion(
        agent_id=agent_id,
        version=version_data.version,
        config=version_data.config,
        deployed_by=current_user.id
    )

    db.add(agent_version)
    db.commit()
    db.refresh(agent_version)

    # Update agent with the new version
    agent.version = version_data.version
    agent.config = version_data.config
    db.commit()
    db.refresh(agent)

    return {"message": "Agent version deployed successfully", "version": version_data.version}


@router.post("/{agent_id}/clone")
def clone_agent(
    agent_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Clone an existing agent."""

    agent = db.query(Agent).filter(Agent.id == agent_id).first()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    # Verify user has access to this agent's organization
    org_query = db.query(Organization).filter(Organization.id == agent.organization_id)
    org_query = filter_by_organization(db, org_query, agent.organization_id, current_user)
    organization = org_query.first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found or access denied"
        )

    # Check if user is member of this organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == agent.organization_id
    ).first()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this organization"
        )

    # Only owners and admins can clone agents
    if member.role not in ["owner", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owners and admins can clone agents"
        )

    # Create new agent with similar configuration
    new_agent = Agent(
        name=f"Clone of {agent.name}",
        role=agent.role,
        instructions=agent.instructions,
        model=agent.model,
        tools=agent.tools,
        config=agent.config,
        status=agent.status,
        version=agent.version,
        organization_id=agent.organization_id,
        created_by=current_user.id
    )

    db.add(new_agent)
    db.commit()
    db.refresh(new_agent)

    return {"message": "Agent cloned successfully", "new_agent_id": new_agent.id}


@router.get("/{agent_id}/workflows", response_model=List[Workflow])
def get_agent_workflows(
    agent_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    pagination: Pagination = Depends()
):
    """Get workflows using this agent."""

    agent = db.query(Agent).filter(Agent.id == agent_id).first()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    # Verify user has access to this agent's organization
    org_query = db.query(Organization).filter(Organization.id == agent.organization_id)
    org_query = filter_by_organization(db, org_query, agent.organization_id, current_user)
    organization = org_query.first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found or access denied"
        )

    from ..shared.models import Workflow
    query = db.query(Workflow).filter(
        Workflow.agent_id == agent_id
    )

    paginated_query, total_count = paginate_query(db, query, pagination)
    items = paginated_query.all()

    return create_paginated_response(items, total_count, pagination)


@router.get("/{agent_id}/tasks", response_model=List[Task])
def get_agent_tasks(
    agent_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    pagination: Pagination = Depends()
):
    """Get tasks executed by this agent."""

    agent = db.query(Agent).filter(Agent.id == agent_id).first()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    # Verify user has access to this agent's organization
    org_query = db.query(Organization).filter(Organization.id == agent.organization_id)
    org_query = filter_by_organization(db, org_query, agent.organization_id, current_user)
    organization = org_query.first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found or access denied"
        )

    from ..shared.models import Task
    query = db.query(Task).filter(
        Task.agent_id == agent_id
    )

    paginated_query, total_count = paginate_query(db, query, pagination)
    items = paginated_query.all()

    return create_paginated_response(items, total_count, pagination)


@router.get("/{agent_id}/stats", response_model=dict)
def get_agent_stats(
    agent_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get agent statistics."""

    agent = db.query(Agent).filter(Agent.id == agent_id).first()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    # Verify user has access to this agent's organization
    org_query = db.query(Organization).filter(Organization.id == agent.organization_id)
    org_query = filter_by_organization(db, org_query, agent.organization_id, current_user)
    organization = org_query.first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found or access denied"
        )

    # In a real implementation, you would query usage metrics
    # For now, we'll return sample data

    return {
        "agent": {
            "id": str(agent.id),
            "name": agent.name,
            "role": agent.role,
            "model": agent.model
        },
        "usage": {
            "total_tasks": 1234,
            "completed_tasks": 1100,
            "failed_tasks": 134,
            "average_execution_time": 2.5,  # in seconds
            "token_usage": 567890,
            "cost_estimate": "$123.45"
        },
        "performance": {
            "success_rate": 89.1,  # percentage
            "avg_response_time": 1.2,  # in seconds
            "error_rate": 10.9  # percentage
        },
        "recent_activity": {
            "last_7d_tasks": 234,
            "last_30d_tasks": 890,
            "active_workflows": 5
        }
    }


@router.get("/types", response_model=List[Dict[str, str]])
def get_agent_types():
    """Get available agent types."""

    return [
        {"type": "openai", "name": "OpenAI", "description": "OpenAI models like GPT-4, GPT-3.5"},
        {"type": "anthropic", "name": "Anthropic", "description": "Anthropic models like Claude"},
        {"type": "custom", "name": "Custom", "description": "Custom API endpoints"},
        {"type": "local", "name": "Local", "description": "Local models (coming soon)"}
    ]


@router.get("/models", response_model=List[Dict[str, str]])
def get_available_models(agent_type: str = "openai"):
    """Get available models for a specific agent type."""

    # In a real implementation, you would query the actual models from the provider
    # For now, we'll return sample data

    if agent_type == "openai":
        return [
            {"model": "gpt-4", "name": "GPT-4", "description": "Most capable model"},
            {"model": "gpt-4-turbo", "name": "GPT-4 Turbo", "description": "Cost-effective version of GPT-4"},
            {"model": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo", "description": "Fast and capable"}
        ]
    elif agent_type == "anthropic":
        return [
            {"model": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet", "description": "Most intelligent model"},
            {"model": "claude-3-5-haiku-20241022", "name": "Claude 3.5 Haiku", "description": "Fast and capable"},
            {"model": "claude-3-opus-20240229", "name": "Claude 3 Opus", "description": "Most powerful model"}
        ]
    elif agent_type == "custom":
        return [
            {"model": "custom-rest", "name": "REST API", "description": "Custom REST API endpoint"},
            {"model": "custom-grpc", "name": "gRPC", "description": "Custom gRPC endpoint"}
        ]
    else:
        return []