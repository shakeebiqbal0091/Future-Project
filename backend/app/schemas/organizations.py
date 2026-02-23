from typing import Any, Dict, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, constr, validator
from app.models.models import StatusEnum, TaskStatusEnum, WorkflowStatusEnum, RoleEnum, PlanEnum, IntegrationStatusEnum, ModelEnum, ToolEnum


class OrganizationCreate(BaseModel):
    name: constr(min_length=1, max_length=100)
    billing_email: Optional[str] = None
    plan: Optional[PlanEnum] = PlanEnum.free

    class Config:
        from_attributes = True


class OrganizationUpdate(BaseModel):
    name: Optional[constr(min_length=1, max_length=100)] = None
    billing_email: Optional[str] = None
    plan: Optional[PlanEnum] = None

    class Config:
        from_attributes = True


class Organization(BaseModel):
    id: str
    name: str
    plan: str
    billing_email: Optional[str]
    stripe_customer_id: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MemberCreate(BaseModel):
    user_id: str
    role: RoleEnum = RoleEnum.member

    class Config:
        from_attributes = True


class MemberUpdate(BaseModel):
    role: Optional[RoleEnum] = None

    class Config:
        from_attributes = True


class Member(BaseModel):
    id: str
    user_id: str
    organization_id: str
    role: str
    joined_at: datetime
    user: Dict[str, Any]  # User information

    class Config:
        from_attributes = True


class OrganizationWithMembers(BaseModel):
    organization: Organization
    members: List[Member]


class OrganizationList(BaseModel):
    organizations: List[Organization]
    total: int
    page: int
    size: int


class MemberList(BaseModel):
    members: List[Member]
    total: int
    page: int
    size: int


class OrganizationCreateResponse(BaseModel):
    organization: Organization
    message: str = "Organization created successfully"


class OrganizationUpdateResponse(BaseModel):
    organization: Organization
    message: str = "Organization updated successfully"


class OrganizationDeleteResponse(BaseModel):
    message: str = "Organization deleted successfully"


class MemberCreateResponse(BaseModel):
    member: Member
    message: str = "Member invited successfully"


class MemberUpdateResponse(BaseModel):
    member: Member
    message: str = "Member updated successfully"


class MemberDeleteResponse(BaseModel):
    message: str = "Member removed successfully"


class OrganizationValidationError(BaseModel):
    field: str
    message: str


class OrganizationValidationErrorResponse(BaseModel):
    detail: str
    errors: List[OrganizationValidationError]
    timestamp: datetime = datetime.utcnow()


class OrganizationErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
    timestamp: datetime = datetime.utcnow()


class RateLimitHeaders(BaseModel):
    X_RATELIMIT_LIMIT: int
    X_RATELIMIT_REMAINING: int
    X_RATELIMIT_RESET: int


class SecurityHeaders(BaseModel):
    X_CONTENT_TYPE_OPTIONS: str = "nosniff"
    X_FRAME_OPTIONS: str = "DENY"
    X_XSS_PROTECTION: str = "1; mode=block"
    STRICT_TRANSPORT_SECURITY: str = "max-age=31536000; includeSubDomains"
    REFERER_POLICY: str = "strict-origin-when-cross-origin"
    CONTENT_SECURITY_POLICY: str = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' https:; connect-src 'self' https:; frame-ancestors 'none';"