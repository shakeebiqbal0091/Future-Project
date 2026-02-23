from typing import Any, Dict, Optional
from datetime import datetime, timedelta
import jwt
import redis
from fastapi import APIRouter, Depends, HTTPException, status, Form
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, constr, Field
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.core.security.auth_handler import AuthHandler
from app.core.security.utils import PasswordUtils, JWTUtils, RateLimiter, InputValidator
from app.models.models import User
from app.schemas.auth import (
    UserCreate, UserLogin, Token, TokenData, PasswordReset,
    User, AuthResponse, ErrorResponse, ValidationErrorResponse, UserInDB
)

router = APIRouter()

@router.post("/register", response_model=Token)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Create new user account"""
    # Rate limiting
    rate_limit_key = f"auth:register:{user_data.email}"
    if RateLimiter.is_rate_limited(rate_limit_key, 5, 3600):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many registration attempts. Try again later."
        )

    # Validate email
    if not InputValidator.validate_email(user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format"
        )

    # Validate password
    if not InputValidator.validate_password(user_data.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long and contain both letters and numbers"
        )

    # Check if user already exists
    existing_user = db.query(User).filter(
        (User.email == user_data.email) | (User.username == user_data.username)
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email or username already exists"
        )

    # Create new user
    hashed_password = PasswordUtils.hash_password(user_data.password)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        is_active=True,
        is_superuser=False,
        email_verified=False
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Create access and refresh tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=30)
    access_token = JWTUtils.create_access_token(
        subject=new_user.username,
        expires_delta=access_token_expires
    )
    refresh_token = JWTUtils.create_refresh_token(
        subject=new_user.username,
        expires_delta=refresh_token_expires
    )

    # Store refresh token in Redis
    AuthHandler.redis_client.setex(
        f"refresh:{new_user.username}",
        timedelta(days=30),
        refresh_token
    )

    return Token(
        access_token=access_token,
        token_type="bearer"
    )

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login user and return JWT tokens"""
    # Rate limiting
    rate_limit_key = f"auth:login:{form_data.username}"
    if RateLimiter.is_rate_limited(rate_limit_key, 10, 900):  # 10 attempts per 15 minutes
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again later."
        )

    user = AuthHandler.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=30)
    access_token = JWTUtils.create_access_token(
        subject=user.username,
        expires_delta=access_token_expires
    )
    refresh_token = JWTUtils.create_refresh_token(
        subject=user.username,
        expires_delta=refresh_token_expires
    )

    # Store refresh token in Redis
    AuthHandler.redis_client.setex(
        f"refresh:{user.username}",
        timedelta(days=30),
        refresh_token
    )

    return Token(
        access_token=access_token,
        token_type="bearer"
    )

@router.post("/logout")
async def logout(token: str = Depends(OAuth2PasswordBearer(tokenUrl="/auth/login")), db: Session = Depends(get_db)):
    """Logout user by invalidating tokens"""
    try:
        payload = JWTUtils.verify_token(token)
        username = payload.username
        # Invalidate refresh token
        AuthHandler.redis_client.delete(f"refresh:{username}")
        # Blacklist access token
        AuthHandler.blacklist_token(token)
        return {"message": "Successfully logged out"}
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

@router.post("/refresh")
async def refresh_token(token: str = Depends(OAuth2PasswordBearer(tokenUrl="/auth/login"))):
    """Refresh access token using valid refresh token"""
    try:
        payload = JWTUtils.verify_token(token)
        username = payload.username

        # Get refresh token from Redis
        refresh_token = AuthHandler.redis_client.get(f"refresh:{username}")
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token not found or expired"
            )

        # Verify refresh token matches
        if refresh_token.decode() != token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

        # Create new access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = JWTUtils.create_access_token(
            subject=username,
            expires_delta=access_token_expires
        )

        return Token(
            access_token=access_token,
            token_type="bearer"
        )
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

@router.post("/verify-email")
async def verify_email(token: str, db: Session = Depends(get_db)):
    """Verify user's email address"""
    # Rate limiting
    rate_limit_key = f"auth:verify-email:{token}"
    if RateLimiter.is_rate_limited(rate_limit_key, 5, 3600):  # 5 attempts per hour
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many verification attempts. Try again later."
        )

    try:
        # Verify token (in real implementation, this would be a separate email verification token)
        # For now, we'll simulate verification
        payload = JWTUtils.verify_token(token)
        username = payload.username
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User not found"
            )

        if user.email_verified:
            return {"message": "Email is already verified"}

        # Mark email as verified
        user.email_verified = True
        db.commit()
        db.refresh(user)

        return {"message": "Email verified successfully"}
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token"
        )

@router.post("/reset-password-request")
async def password_reset_request(email: EmailStr, db: Session = Depends(get_db)):
    """Request password reset (sends email with reset link)"""
    # Rate limiting
    rate_limit_key = f"auth:reset:{email}"
    if RateLimiter.is_rate_limited(rate_limit_key, 3, 3600):  # 3 requests per hour
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many password reset requests. Try again later."
        )

    # Check if user exists
    user = db.query(User).filter(User.email == email).first()
    if not user:
        # Don't reveal if user exists or not for security reasons
        return {"message": "If an account exists with this email, a password reset link has been sent."}

    # In a real implementation, you would:
    # 1. Generate a secure reset token
    # 2. Save it to the database with an expiration
    # 3. Send an email with the reset link
    # For now, we'll just return success
    return {"message": "If an account exists with this email, a password reset link has been sent."}

@router.post("/reset-password")
async def password_reset(reset_data: PasswordReset, db: Session = Depends(get_db)):
    """Reset password using reset token"""
    # Rate limiting
    rate_limit_key = f"auth:reset-password:{reset_data.reset_token}"
    if RateLimiter.is_rate_limited(rate_limit_key, 3, 1800):  # 3 attempts per 30 minutes
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many password reset attempts. Try again later."
        )

    # Validate new password
    if not InputValidator.validate_password(reset_data.new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters long and contain both letters and numbers"
        )

    # In a real implementation, you would:
    # 1. Verify the reset token (check if it's valid and not expired)
    # 2. Find the user associated with the token
    # 3. Update the password
    # 4. Invalidate the reset token
    # For now, we'll just return success
    #
    # user = db.query(User).filter(User.reset_token == reset_data.reset_token).first()
    # if not user:
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail="Invalid or expired reset token"
    #     )
    #
    # user.hashed_password = PasswordUtils.hash_password(reset_data.new_password)
    # user.reset_token = None  # Invalidate the token
    # user.reset_token_expires_at = None
    # db.commit()
    # db.refresh(user)

    return {"message": "Password reset successful"}

@router.get("/me", response_model=User)
async def read_users_me(current_user: User = Depends(AuthHandler.get_current_active_user)):
    """Get current user's profile"""
    return current_user

@router.put("/me", response_model=User)
async def update_users_me(
    update_data: UserCreate,
    current_user: User = Depends(AuthHandler.get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update current user's profile"""
    # Rate limiting
    rate_limit_key = f"auth:update-me:{current_user.username}"
    if RateLimiter.is_rate_limited(rate_limit_key, 5, 3600):  # 5 attempts per hour
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many update attempts. Try again later."
        )

    # Validate email if provided
    if update_data.email and not InputValidator.validate_email(update_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format"
        )

    # Check if email is already taken by another user
    if update_data.email and update_data.email != current_user.email:
        existing_user = db.query(User).filter(
            User.email == update_data.email
        ).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already taken by another user"
            )

    # Update user profile
    if update_data.username:
        current_user.username = update_data.username
    if update_data.email:
        current_user.email = update_data.email
    if update_data.full_name:
        current_user.full_name = update_data.full_name

    db.commit()
    db.refresh(current_user)

    return current_user

@router.post("/change-password", response_model=Dict[str, str])
async def change_password(
    current_password: str,
    new_password: str,
    token: str = Depends(OAuth2PasswordBearer(tokenUrl="/auth/login")),
    db: Session = Depends(get_db)
):
    """Change current user's password"""
    # Rate limiting
    username = JWTUtils.verify_token(token).username
    rate_limit_key = f"auth:change-password:{username}"
    if RateLimiter.is_rate_limited(rate_limit_key, 3, 3600):  # 3 attempts per hour
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many password change attempts. Try again later."
        )

    # Get current user
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

    # Validate current password
    if not PasswordUtils.verify_password(current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    # Validate new password
    if not InputValidator.validate_password(new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters long and contain both letters and numbers"
        )

    # Update password
    user.hashed_password = PasswordUtils.hash_password(new_password)
    db.commit()
    db.refresh(user)

    return {"message": "Password changed successfully"}