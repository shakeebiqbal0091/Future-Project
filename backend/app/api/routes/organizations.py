# Organizations and Members API Routes
from typing import Any, Dict, Optional, List
from datetime import datetime, timedelta
import jwt
import redis
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr, constr
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.core.security.auth_handler import AuthHandler
from app.core.security.utils import PasswordUtils, JWTUtils, RateLimiter, InputValidator
from app.models.models import User, Organization, Membership, RoleEnum, PlanEnum
from app.schemas.organizations import (
    OrganizationCreate, OrganizationUpdate, Organization, MemberCreate, MemberUpdate, Member,
    OrganizationWithMembers, OrganizationList, MemberList, OrganizationCreateResponse,
    OrganizationUpdateResponse, OrganizationDeleteResponse, MemberCreateResponse,
    MemberUpdateResponse, MemberDeleteResponse, OrganizationValidationError,
    OrganizationValidationErrorResponse, OrganizationErrorResponse
)

router = APIRouter()

@router.get("/api/v1/organizations", response_model=Organization)
def get_current_organization(
    current_user: User = Depends(AuthHandler.get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get the current user's organization.

    Only users who are members of an organization can access this endpoint.
    Returns organization details including name, plan, and billing information.
    """
    # Rate limiting
    rate_limit_key = f"org:get:{current_user.id}"
    if RateLimiter.is_rate_limited(rate_limit_key, 60, 60):  # 60 requests per minute
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Try again later."
        )

    # Find the organization that the user belongs to
    membership = db.query(Membership).filter(
        Membership.user_id == current_user.id,
        Membership.role.in_([RoleEnum.owner, RoleEnum.admin, RoleEnum.member, RoleEnum.viewer])
    ).first()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No organization found for the current user"
        )

    organization = db.query(Organization).filter(
        Organization.id == membership.organization_id
    ).first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    return organization


@router.put("/api/v1/organizations", response_model=OrganizationUpdateResponse)
def update_organization(
    organization_data: OrganizationUpdate,
    current_user: User = Depends(AuthHandler.get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update organization details.

    Only organization owners and admins can update organization settings.
    Supported fields: name, billing_email, plan.
    """
    # Rate limiting
    rate_limit_key = f"org:update:{current_user.id}"
    if RateLimiter.is_rate_limited(rate_limit_key, 30, 60):  # 30 requests per minute
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Try again later."
        )

    # Check if user has permission
    membership = db.query(Membership).filter(
        Membership.user_id == current_user.id,
        Membership.role.in_([RoleEnum.owner, RoleEnum.admin])
    ).first()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owners and admins can update organization settings"
        )

    organization = db.query(Organization).filter(
        Organization.id == membership.organization_id
    ).first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    # Update organization fields
    if organization_data.name:
        organization.name = organization_data.name
    if organization_data.billing_email:
        organization.billing_email = organization_data.billing_email
    if organization_data.plan:
        organization.plan = organization_data.plan

    db.commit()
    db.refresh(organization)

    return OrganizationUpdateResponse(organization=organization)


@router.get("/api/v1/organizations/members", response_model=MemberList)
def list_members(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(AuthHandler.get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List members of the current user's organization.

    Role-based access control:
    - Owners and admins can view all members
    - Members and viewers can only see their own membership
    - Pagination support with configurable page size
    """
    # Check if user has permission
    membership = db.query(Membership).filter(
        Membership.user_id == current_user.id
    ).first()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No organization found for the current user"
        )

    # Determine what members to show based on role
    if membership.role in [RoleEnum.owner, RoleEnum.admin]:
        # Owners and admins can see all members
        query = db.query(Membership).filter(
            Membership.organization_id == membership.organization_id
        )
    else:
        # Members and viewers can only see their own membership
        query = db.query(Membership).filter(
            Membership.id == membership.id
        )

    # Pagination
    total = query.count()
    members = query.offset((page - 1) * size).limit(size).all()

    # Convert to response model with user info
    member_list = []
    for member in members:
        user = db.query(User).filter(User.id == member.user_id).first()
        if user:
            member_list.append(Member(
                id=str(member.id),
                user_id=str(member.user_id),
                organization_id=str(member.organization_id),
                role=member.role.value,
                joined_at=member.joined_at,
                user={
                    "id": str(user.id),
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.full_name,
                    "email_verified": user.email_verified
                }
            ))

    return MemberList(members=member_list, total=total, page=page, size=size)


@router.post("/api/v1/organizations/members", response_model=MemberCreateResponse)
def invite_member(
    member_data: MemberCreate,
    current_user: User = Depends(AuthHandler.get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Invite a new member to the organization.

    Only organization owners and admins can invite members.
    Supports role assignment (owner, admin, member, viewer).
    """
    # Rate limiting
    rate_limit_key = f"org:invite:{current_user.id}"
    if RateLimiter.is_rate_limited(rate_limit_key, 10, 3600):  # 10 invites per hour
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many member invitations. Try again later."
        )

    # Check if user has permission
    membership = db.query(Membership).filter(
        Membership.user_id == current_user.id,
        Membership.role.in_([RoleEnum.owner, RoleEnum.admin])
    ).first()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owners and admins can invite members"
        )

    # Check if user already exists in the organization
    existing_membership = db.query(Membership).filter(
        Membership.organization_id == membership.organization_id,
        Membership.user_id == member_data.user_id
    ).first()

    if existing_membership:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this organization"
        )

    # Check if user exists
    user = db.query(User).filter(User.id == member_data.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Create new membership
    new_membership = Membership(
        user_id=member_data.user_id,
        organization_id=membership.organization_id,
        role=member_data.role
    )
    db.add(new_membership)
    db.commit()
    db.refresh(new_membership)

    # Return member with user info
    return MemberCreateResponse(
        member=Member(
            id=str(new_membership.id),
            user_id=str(new_membership.user_id),
            organization_id=str(new_membership.organization_id),
            role=new_membership.role.value,
            joined_at=new_membership.joined_at,
            user={
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "email_verified": user.email_verified
            }
        )
    )


@router.delete("/api/v1/organizations/members/{member_id}", response_model=MemberDeleteResponse)
def remove_member(
    member_id: str,
    current_user: User = Depends(AuthHandler.get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Remove a member from the organization.

    Only organization owners and admins can remove members.
    Owners cannot remove themselves from the organization.
    """
    # Rate limiting
    rate_limit_key = f"org:remove:{current_user.id}"
    if RateLimiter.is_rate_limited(rate_limit_key, 10, 60):  # 10 requests per minute
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Try again later."
        )

    # Check if user has permission
    membership = db.query(Membership).filter(
        Membership.user_id == current_user.id,
        Membership.role.in_([RoleEnum.owner, RoleEnum.admin])
    ).first()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owners and admins can remove members"
        )

    # Get the member to remove
    member_to_remove = db.query(Membership).filter(
        Membership.id == member_id,
        Membership.organization_id == membership.organization_id
    ).first()

    if not member_to_remove:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found in this organization"
        )

    # Owners cannot remove themselves
    if member_to_remove.user_id == current_user.id and membership.role == RoleEnum.owner:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Owners cannot remove themselves from the organization"
        )

    # Delete the membership
    db.delete(member_to_remove)
    db.commit()

    return MemberDeleteResponse()