import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc
from sqlalchemy.sql import func

from .schemas import Pagination, PaginatedResponse

def validate_email(email: str) -> bool:
    regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(regex, email) is not None


def validate_slug(slug: str) -> bool:
    regex = r'^[a-z0-9-]+$'  # Lowercase, numbers, and hyphens only
    return re.match(regex, slug) is not None


def create_slug(name: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')


def paginate_query(
    db: Session,
    query,
    pagination: Pagination,
    default_sort: str = None
) -> tuple:
    """
    Apply pagination, sorting, and filtering to a query.
    Returns (paginated_query, total_count)
    """
    # Apply filters
    if pagination.filters:
        for field, value in pagination.filters.items():
            if isinstance(value, dict):
                # Handle complex filters like {"op": "gt", "value": 10}
                op = value.get("op", "eq")
                val = value.get("value")
                if op == "gt":
                    query = query.filter(getattr(query.column, field) > val)
                elif op == "lt":
                    query = query.filter(getattr(query.column, field) < val)
                elif op == "gte":
                    query = query.filter(getattr(query.column, field) >= val)
                elif op == "lte":
                    query = query.filter(getattr(query.column, field) <= val)
                elif op == "like":
                    query = query.filter(getattr(query.column, field).like(f"%{val}%"))
                elif op == "in":
                    query = query.filter(getattr(query.column, field).in_(val))
                elif op == "eq":
                    query = query.filter(getattr(query.column, field) == val)
            else:
                query = query.filter(getattr(query.column, field) == value)

    # Get total count
    total_count = query.count()

    # Apply sorting
    sort_field = pagination.sort_by or default_sort
    if sort_field:
        sort_field = sort_field.lstrip('-')
        if hasattr(query.column, sort_field):
            if pagination.sort_order == "desc":
                query = query.order_by(desc(getattr(query.column, sort_field)))
            else:
                query = query.order_by(asc(getattr(query.column, sort_field)))
    else:
        query = query.order_by(desc(query.column.id))

    # Apply pagination
    offset = (pagination.page - 1) * pagination.limit
    query = query.offset(offset).limit(pagination.limit)

    return query, total_count


def create_paginated_response(
    items: List[Any],
    total: int,
    pagination: Pagination
) -> PaginatedResponse:
    """Create a standardized paginated response."""
    total_pages = (total + pagination.limit - 1) // pagination.limit
    return PaginatedResponse(
        items=items,
        total=total,
        page=pagination.page,
        limit=pagination.limit,
        total_pages=total_pages
    )


def get_time_range(time_range: str) -> tuple:
    """Convert time range string to start and end dates."""
    end_date = datetime.utcnow()
    if time_range == "last_7d":
        start_date = end_date - timedelta(days=7)
    elif time_range == "last_30d":
        start_date = end_date - timedelta(days=30)
    elif time_range == "last_90d":
        start_date = end_date - timedelta(days=90)
    elif time_range == "last_365d":
        start_date = end_date - timedelta(days=365)
    elif time_range == "this_month":
        start_date = datetime(end_date.year, end_date.month, 1)
    elif time_range == "last_month":
        first = datetime(end_date.year, end_date.month, 1)
        start_date = first - timedelta(days=first.day)
        end_date = first - timedelta(seconds=1)
    else:
        start_date = None
        end_date = None
    return start_date, end_date


def filter_by_organization(db: Session, query, organization_id: int, user: User):
    """
    Filter query to only include items the user has access to in the organization.
    Superusers can access all organizations.
    """
    if user.is_superuser:
        return query.filter(query.column.organization_id == organization_id)

    # Check if user is member of organization
    from .models import OrganizationMember
    is_member = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user.id,
        OrganizationMember.organization_id == organization_id
    ).first()

    if not is_member:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access this organization"
        )

    return query.filter(query.column.organization_id == organization_id)


def get_organization_members(db: Session, organization_id: int):
    """Get all members of an organization."""
    from .models import OrganizationMember, User
    return db.query(OrganizationMember).join(User).filter(
        OrganizationMember.organization_id == organization_id
    ).all()


def get_user_organizations(db: Session, user_id: int):
    """Get all organizations a user belongs to."""
    from .models import OrganizationMember, Organization
    return db.query(Organization).join(OrganizationMember).filter(
        OrganizationMember.user_id == user_id
    ).all()


def get_organization_by_slug(db: Session, slug: str):
    """Get organization by slug."""
    from .models import Organization
    return db.query(Organization).filter(Organization.slug == slug).first()


def is_organization_member(db: Session, user_id: int, organization_id: int) -> bool:
    """Check if user is member of organization."""
    from .models import OrganizationMember
    return db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user_id,
        OrganizationMember.organization_id == organization_id
    ).first() is not None