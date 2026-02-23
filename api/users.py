from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from api.schemas import (
    UserResponse, UserUpdate, OrganizationResponse, ErrorResponse,
    PaginationResponse, SortOrder, Filter
)
from core.database import get_db
from core.auth import get_current_user, get_current_active_user, get_current_organization

router = APIRouter()


@router.get("/", response_model=List[UserResponse])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    users = db.query(User).offset(skip).limit(limit).all()
    return users


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Check permissions - only superusers or same user can update
    if not (current_user.is_superuser or current_user.id == user_id):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    user.email = user_update.email or user.email
    user.username = user_update.username or user.username
    user.full_name = user_update.full_name or user.full_name
    user.is_active = user_update.is_active if user_update.is_active is not None else user.is_active

    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Check permissions - only superusers or same user can delete
    if not (current_user.is_superuser or current_user.id == user_id):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    db.delete(user)
    db.commit()


@router.get("/me/organizations", response_model=List[OrganizationResponse])
async def get_user_organizations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    organizations = db.query(Organization).join(Organization.members).filter(Member.user_id == current_user.id).all()
    return organizations


@router.get("/search")
async def search_users(
    query: str = Query(..., min_length=2),
    skip: int = 0,
    limit: int = 20,
    sort: Optional[SortOrder] = None,
    filters: Optional[List[Filter]] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Search available only for superusers")

    q = db.query(User)

    # Apply filters
    if filters:
        for filter in filters:
            if filter.operator == "eq":
                q = q.filter(getattr(User, filter.field) == filter.value)
            elif filter.operator == "ne":
                q = q.filter(getattr(User, filter.field) != filter.value)
            # Add more operators as needed

    # Apply search query
    q = q.filter(
        User.email.ilike(f"%{query}%") |
        User.username.ilike(f"%{query}%") |
        User.full_name.ilike(f"%{query}%")
    )

    # Apply sorting
    if sort:
        sort_field = getattr(User, sort.field)
        if sort.direction == "desc":
            sort_field = sort_field.desc()
        q = q.order_by(sort_field)

    total = q.count()
    users = q.offset(skip).limit(limit).all()

    return PaginationResponse(
        items=users,
        total=total,
        page=(skip // limit) + 1,
        size=limit,
        total_pages=(total + limit - 1) // limit
    )