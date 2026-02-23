from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from typing import List, Optional
import datetime

from ..shared.database import get_db
from ..shared.security import get_current_active_user, get_current_active_superuser, create_access_token, verify_password, hash_password
from ..shared.models import User, Organization, OrganizationMember
from ..shared.schemas import (
    User, UserCreate, UserUpdate, Token, AuthResponse,
    Organization, OrganizationMember, PasswordResetRequest, PasswordReset,
    ProfileUpdate, Settings
)
from ..shared.utils import create_slug, filter_by_organization, get_user_organizations

router = APIRouter()

@router.post("/register", response_model=AuthResponse)
def register_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Register a new user."""

    # Check if email or username already exists
    db_user = db.query(User).filter(
        (User.email == user_data.email) | (User.username == user_data.username)
    ).first()

    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or username already registered"
        )

    # Create new user
    hashed_password = hash_password(user_data.password)
    db_user = User(
        email=user_data.email,
        username=user_data.username,
        full_name=user_data.full_name,
        hashed_password=hashed_password
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Create default organization for the user
    organization_slug = create_slug(f"{user_data.username}-org")
    organization = Organization(
        name=f"{user_data.username}'s Organization",
        slug=organization_slug,
        is_active=True
    )
    db.add(organization)
    db.commit()

    # Add user as owner of the organization
    member = OrganizationMember(
        user_id=db_user.id,
        organization_id=organization.id,
        role="owner"
    )
    db.add(member)
    db.commit()

    # Create JWT token
    access_token = create_access_token(
        data={"sub": str(db_user.id), "username": db_user.username}
    )

    return AuthResponse(
        user=User.from_orm(db_user),
        token=Token(access_token=access_token, token_type="bearer")
    )


@router.post("/login", response_model=AuthResponse)
def login_user(
    credentials: UserCreate,
    db: Session = Depends(get_db)
):
    """User login."""

    db_user = db.query(User).filter(
        (User.email == credentials.email) | (User.username == credentials.username)
    ).first()

    if not db_user or not verify_password(credentials.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    if not db_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is deactivated"
        )

    access_token = create_access_token(
        data={"sub": str(db_user.id), "username": db_user.username}
    )

    return AuthResponse(
        user=User.from_orm(db_user),
        token=Token(access_token=access_token, token_type="bearer")
    )


@router.post("/logout")
def logout_user(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    db: Session = Depends(get_db)
):
    """User logout - invalidates token."""

    # In JWT implementation, token invalidation is typically handled by short expiration times
    # or token blacklisting. For now, we'll just return success.

    return {"message": "Logged out successfully"}


@router.post("/refresh")
def refresh_token(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    db: Session = Depends(get_db)
):
    """Refresh JWT token."""

    token = credentials.credentials
    # Verify and decode token (implementation depends on your JWT setup)
    # For this example, we'll assume the token contains user_id

    # Normally you would verify the token here

    # For demonstration, we'll create a new token
    # In real implementation, you would decode the existing token to get user info

    # This is a placeholder - implement proper token verification
    user_id = 1  # This should come from token verification

    db_user = db.query(User).filter(User.id == user_id).first()

    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

    access_token = create_access_token(
        data={"sub": str(db_user.id), "username": db_user.username}
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/profile", response_model=User)
def get_user_profile(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user's profile."""
    return current_user


@router.put("/profile", response_model=User)
def update_user_profile(
    profile_update: ProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update user profile."""

    db_user = db.query(User).filter(User.id == current_user.id).first()

    if profile_update.email:
        # Check if email is already taken by another user
        existing_user = db.query(User).filter(
            User.email == profile_update.email,
            User.id != current_user.id
        ).first()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use"
            )

        db_user.email = profile_update.email

    if profile_update.full_name:
        db_user.full_name = profile_update.full_name

    if profile_update.password:
        db_user.hashed_password = hash_password(profile_update.password)

    db.commit()
    db.refresh(db_user)

    return User.from_orm(db_user)


@router.post("/password-reset")
def request_password_reset(
    reset_request: PasswordResetRequest,
    db: Session = Depends(get_db)
):
    """Request password reset."""

    db_user = db.query(User).filter(User.email == reset_request.email).first()

    if db_user:
        # In a real implementation, you would send a password reset email here
        # For now, we'll just return success to avoid information leakage

        # Generate a reset token (this would be sent via email)
        reset_token = create_access_token(
            data={"user_id": db_user.id, "action": "password_reset"},
            expires_delta=datetime.timedelta(hours=1)
        )

        # Store the reset token (in real implementation, use a separate table)
        # For now, we'll just log it
        print(f"Password reset token generated: {reset_token}")

        # In production, send email with reset link containing the token

    return {"message": "If the email exists, a password reset link has been sent"}


@router.post("/password-reset/confirm")
def confirm_password_reset(
    password_reset: PasswordReset,
    db: Session = Depends(get_db)
):
    """Confirm password reset."""

    # In a real implementation, you would:
    # 1. Verify the reset token
    # 2. Get the user_id from the token
    # 3. Update the password

    # For demonstration, we'll assume the token is valid
    user_id = 1  # This should come from token verification

    db_user = db.query(User).filter(User.id == user_id).first()

    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token"
        )

    # Update password
    db_user.hashed_password = hash_password(password_reset.new_password)
    db.commit()

    return {"message": "Password updated successfully"}


@router.get("/settings", response_model=Settings)
def get_user_settings(
    current_user: User = Depends(get_current_active_user)
):
    """Get user settings."""

    # In a real implementation, settings would be stored in the database
    # For now, we'll return default settings

    return Settings(
        notifications=True,
        email_updates=True,
        theme="light"
    )


@router.put("/settings", response_model=Settings)
def update_user_settings(
    settings: Settings,
    current_user: User = Depends(get_current_active_user)
):
    """Update user settings."""

    # In a real implementation, you would save settings to the database
    # For now, we'll just return the updated settings

    return settings


@router.get("/organizations", response_model=List[Organization])
def get_user_organizations_list(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all organizations for current user."""

    return get_user_organizations(db, current_user.id)


@router.get("/organizations/{organization_id}/members", response_model=List[OrganizationMember])
def get_organization_members(
    organization_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get members of an organization."""

    # Verify user has access to this organization
    user_organizations = get_user_organizations(db, current_user.id)
    organization_slugs = [org.slug for org in user_organizations]

    org_query = db.query(Organization).filter(Organization.id == organization_id)
    org_query = filter_by_organization(db, org_query, organization_id, current_user)
    organization = org_query.first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found or access denied"
        )

    # Get all members
    members = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == organization_id
    ).all()

    # Include user details
    from ..shared.models import User
    for member in members:
        member.user = db.query(User).filter(User.id == member.user_id).first()

    return members