"""
FastAPI routes for Organization and Member management.

This module provides REST API endpoints for managing organizations and their members,
including role-based access control (RBAC) with owner, admin, member, and viewer roles.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from typing import List, Optional

from api.schemas import (
    OrganizationCreate, OrganizationUpdate, OrganizationResponse, UserResponse,
    PaginationResponse, SortOrder, Filter
)
from core.database import get_db
from core.auth import get_current_user, get_current_active_user, get_current_organization
from core.exceptions import BusinessLogicError
from core.config import settings

# Initialize router
router = APIRouter()

# Security scheme for rate limiting (placeholder - would be implemented via middleware)
security = HTTPBearer()


@router.get(
    "/",
    response_model=OrganizationResponse,
    summary="Get current organization",
    description="Get the organization of the currently authenticated user",
    responses={
        200: {"description": "Organization found"},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
    }
)
async def get_current_organization_endpoint(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get the organization associated with the current user.

    - Requires authentication
    - Returns the user's organization if they are a member
    - Includes role information
    """
    # Get user's organization through membership
    member = db.query(Member).filter(
        Member.user_id == current_user.id,
        Member.organization_id != None  # noqa: E711
    ).first()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not a member of any organization"
        )

    # Get the organization
    org = db.query(Organization).filter(Organization.id == member.organization_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    return org


@router.put(
    "/",
    response_model=OrganizationResponse,
    status_code=status.HTTP_200_OK,
    summary="Update organization",
    description="Update organization details. Only organization owner can perform this action.",
    responses={
        200: {"description": "Organization updated successfully"},
        400: {"description": "Invalid input"},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        404: {"description": "Organization not found"},
    }
)
async def update_organization_endpoint(
    organization_update: OrganizationUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update organization details.

    - Only organization owner can update organization
    - Partial updates supported
    - Validates organization exists and user has permission
    """
    # Get user's organization
    member = db.query(Member).filter(
        Member.user_id == current_user.id,
        Member.organization_id != None  # noqa: E711
    ).first()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not a member of any organization"
        )

    org = db.query(Organization).filter(Organization.id == member.organization_id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    # Check if user is owner
    if member.role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owner can update organization details"
        )

    # Update organization fields
    org.name = organization_update.name or org.name
    org.description = organization_update.description or org.description
    org.is_active = organization_update.is_active if organization_update.is_active is not None else org.is_active

    db.commit()
    db.refresh(org)

    return org


@router.get(
    "/members",
    response_model=List[UserResponse],
    summary="List organization members",
    description="List all members of the current user's organization with their roles",
    responses={
        200: {"description": "Members listed successfully"},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
    }
)
async def list_organization_members(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List all members of the user's organization.

    - Returns paginated list of members
    - Shows user details and their role in the organization
    - Any member can view the member list
    """
    # Get user's organization
    member = db.query(Member).filter(
        Member.user_id == current_user.id,
        Member.organization_id != None  # noqa: E711
    ).first()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not a member of any organization"
        )

    # Get all members of the organization
    members = (
        db.query(Member)
        .join(User)
        .filter(Member.organization_id == member.organization_id)
        .offset(skip)
        .limit(limit)
        .all()
    )

    # Format the response
    member_list = []
    for m in members:
        member_list.append({
            "id": m.user.id,
            "email": m.user.email,
            "username": m.user.username,
            "full_name": m.user.full_name,
            "role": m.role,
            "joined_at": m.joined_at,
        })

    return member_list


@router.post(
    "/members",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Invite member to organization",
    description="Invite a new member to the organization. Only organization owner can perform this action.",
    responses={
        201: {"description": "Member invited successfully"},
        400: {"description": "Invalid input"},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        404: {"description": "User not found"},
        409: {"description": "User already a member"},
    }
)
async def invite_organization_member(
    email: str = Query(..., description="Email of the user to invite"),
    role: str = Query("member", description="Role for the new member", regex="^(owner|admin|member|viewer)$"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Invite a new member to the organization.

    - Only organization owner can invite members
    - Validates user exists and is not already a member
    - Sets the specified role (owner, admin, member, viewer)
    """
    # Get user's organization
    member = db.query(Member).filter(
        Member.user_id == current_user.id,
        Member.organization_id != None  # noqa: E711
    ).first()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not a member of any organization"
        )

    # Check if user is owner
    if member.role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owner can invite members"
        )

    # Check if inviting another owner (only one owner allowed)
    if role == "owner":
        existing_owners = db.query(Member).filter(
            Member.organization_id == member.organization_id,
            Member.role == "owner"
        ).count()
        if existing_owners > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organization already has an owner. Only one owner is allowed."
            )

    # Find the user to invite by email
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check if user is already a member
    existing_member = db.query(Member).filter(
        Member.user_id == user.id,
        Member.organization_id == member.organization_id
    ).first()
    if existing_member:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a member of this organization"
        )

    # Create new membership
    new_member = Member(
        user_id=user.id,
        organization_id=member.organization_id,
        role=role
    )
    db.add(new_member)
    db.commit()

    # Return user information
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "full_name": user.full_name,
        "role": role,
        "joined_at": new_member.joined_at,
    }


@router.delete(
    "/members/{user_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Remove member from organization",
    description="Remove a member from the organization. Only organization owner can perform this action.",
    responses={
        200: {"description": "Member removed successfully"},
        400: {"description": "Cannot remove yourself"},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        404: {"description": "User not found or not a member"},
    }
)
async def remove_organization_member(
    user_id: UUID = Path(..., description="UUID of the user to remove"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Remove a member from the organization.

    - Only organization owner can remove members
    - Cannot remove yourself (owner must transfer ownership first)
    - Validates user exists and is a member
    """
    # Get user's organization
    member = db.query(Member).filter(
        Member.user_id == current_user.id,
        Member.organization_id != None  # noqa: E711
    ).first()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not a member of any organization"
        )

    # Check if user is owner
    if member.role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owner can remove members"
        )

    # Check if removing yourself
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove yourself. Transfer ownership first."
        )

    # Find the member to remove
    member_to_remove = db.query(Member).filter(
        Member.user_id == user_id,
        Member.organization_id == member.organization_id
    ).first()

    if not member_to_remove:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not a member of this organization"
        )

    # Remove the member
    db.delete(member_to_remove)
    db.commit()

    return {"message": "Member removed successfully"}


@router.get(
    "/search",
    response_model=PaginationResponse,
    summary="Search organizations",
    description="Search for organizations that the current user is a member of",
    responses={
        200: {"description": "Search results returned"},
        400: {"description": "Invalid query parameters"},
        401: {"description": "Unauthorized"},
    }
)
async def search_organizations(
    query: str = Query(..., min_length=2, description="Search query"),
    skip: int = 0,
    limit: int = 20,
    sort: Optional[SortOrder] = None,
    filters: Optional[List[Filter]] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Search for organizations that the current user is a member of.

    - Supports filtering, sorting, and pagination
    - Search across name, description, and slug
    - Returns paginated results with metadata
    """
    # Get organizations where user is a member
    q = db.query(Organization).join(Member).filter(Member.user_id == current_user.id)

    # Apply filters
    if filters:
        for filter in filters:
            if filter.operator == "eq":
                q = q.filter(getattr(Organization, filter.field) == filter.value)
            elif filter.operator == "ne":
                q = q.filter(getattr(Organization, filter.field) != filter.value)
            elif filter.operator == "gt":
                q = q.filter(getattr(Organization, filter.field) > filter.value)
            elif filter.operator == "lt":
                q = q.filter(getattr(Organization, filter.field) < filter.value)
            elif filter.operator == "gte":
                q = q.filter(getattr(Organization, filter.field) >= filter.value)
            elif filter.operator == "lte":
                q = q.filter(getattr(Organization, filter.field) <= filter.value)
            elif filter.operator == "contains":
                q = q.filter(getattr(Organization, filter.field).ilike(f"%{filter.value}%"))
            elif filter.operator == "startswith":
                q = q.filter(getattr(Organization, filter.field).ilike(f"{filter.value}%"))
            elif filter.operator == "endswith":
                q = q.filter(getattr(Organization, filter.field).ilike(f"%{filter.value}"))

    # Apply search query
    q = q.filter(
        Organization.name.ilike(f"%{query}%") |
        Organization.description.ilike(f"%{query}%") |
        Organization.slug.ilike(f"%{query}%")
    )

    # Apply sorting
    if sort:
        sort_field = getattr(Organization, sort.field)
        if sort.direction == "desc":
            sort_field = sort_field.desc()
        q = q.order_by(sort_field)

    total = q.count()
    organizations = q.offset(skip).limit(limit).all()

    # Get member counts for each organization
    org_ids = [org.id for org in organizations]
    member_counts = db.query(
        Member.organization_id,
        func.count(Member.id).label('member_count')
    ).filter(Member.organization_id.in_(org_ids)).group_by(Member.organization_id).all()

    member_count_dict = {mc[0]: mc[1] for mc in member_counts}

    # Format response
    org_responses = []
    for org in organizations:
        org_responses.append({
            "id": org.id,
            "name": org.name,
            "description": org.description,
            "slug": org.slug,
            "is_active": org.is_active,
            "created_at": org.created_at,
            "updated_at": org.updated_at,
            "member_count": member_count_dict.get(org.id, 0),
            "owner_id": org.owner_id,
        })

    return PaginationResponse(
        items=org_responses,
        total=total,
        page=(skip // limit) + 1,
        size=limit,
        total_pages=(total + limit - 1) // limit
    )