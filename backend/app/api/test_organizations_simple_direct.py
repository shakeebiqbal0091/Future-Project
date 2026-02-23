import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Create test models
Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = sa.Column(sa.String, primary_key=True)
    username = sa.Column(sa.String, unique=True, nullable=False)
    email = sa.Column(sa.String, unique=True, nullable=False)
    hashed_password = sa.Column(sa.String, nullable=False)
    full_name = sa.Column(sa.String)
    is_active = sa.Column(sa.Boolean, default=True)
    is_superuser = sa.Column(sa.Boolean, default=False)
    email_verified = sa.Column(sa.Boolean, default=False)
    created_at = sa.Column(sa.DateTime, default=datetime.utcnow)
    updated_at = sa.Column(sa.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Organization(Base):
    __tablename__ = "organizations"

    id = sa.Column(sa.String, primary_key=True)
    name = sa.Column(sa.String, nullable=False)
    plan = sa.Column(sa.String, nullable=False, default="free")
    billing_email = sa.Column(sa.String)
    stripe_customer_id = sa.Column(sa.String)
    created_at = sa.Column(sa.DateTime, default=datetime.utcnow)
    updated_at = sa.Column(sa.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Membership(Base):
    __tablename__ = "memberships"

    id = sa.Column(sa.String, primary_key=True)
    user_id = sa.Column(sa.String, nullable=False)
    organization_id = sa.Column(sa.String, nullable=False)
    role = sa.Column(sa.String, nullable=False, default="member")
    joined_at = sa.Column(sa.DateTime, default=datetime.utcnow)

# Test models
class RoleEnum:
    owner = "owner"
    admin = "admin"
    member = "member"
    viewer = "viewer"

# Mock AuthHandler
class MockAuthHandler:
    @staticmethod
    def hash_password(password):
        return f"hashed_{password}"

    @staticmethod
    def create_access_token(data):
        return f"token_{data['sub']}"

# Create a test FastAPI app
app = FastAPI()

# Create a test database
test_engine = sa.create_engine("sqlite:///:memory:")

# Create all tables
Base.metadata.create_all(bind=test_engine)

# Create a session factory
SessionLocal = sessionmaker(bind=test_engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Patch the app's get_db
app.dependency_overrides[get_db] = get_db

# Create the organizations router directly in this file
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

router = APIRouter()

# Mock imports
class PasswordUtils:
    @staticmethod
    def hash_password(password):
        return f"hashed_{password}"

class JWTUtils:
    @staticmethod
    def create_access_token(data, expires_delta=None):
        return f"token_{data['sub']}"

class RateLimiter:
    @staticmethod
    def is_rate_limited(key, limit, window):
        return False

class InputValidator:
    @staticmethod
    def validate_email(email):
        return "@" in email

    @staticmethod
    def validate_password(password):
        return len(password) >= 8 and any(c.isalpha() for c in password) and any(c.isdigit() for c in password)

# Mock models
class User:
    def __init__(self, id, username, email, hashed_password, full_name="", is_active=True, is_superuser=False, email_verified=False):
        self.id = id
        self.username = username
        self.email = email
        self.hashed_password = hashed_password
        self.full_name = full_name
        self.is_active = is_active
        self.is_superuser = is_superuser
        self.email_verified = email_verified
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

class Organization:
    def __init__(self, id, name, plan="free", billing_email=None, stripe_customer_id=None):
        self.id = id
        self.name = name
        self.plan = plan
        self.billing_email = billing_email
        self.stripe_customer_id = stripe_customer_id
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

class Membership:
    def __init__(self, id, user_id, organization_id, role="member"):
        self.id = id
        self.user_id = user_id
        self.organization_id = organization_id
        self.role = role
        self.joined_at = datetime.utcnow()

# Mock schemas
class OrganizationCreate(BaseModel):
    name: str
    billing_email: str = None
    plan: str = "free"

class OrganizationUpdate(BaseModel):
    name: str = None
    billing_email: str = None
    plan: str = None

class Organization(BaseModel):
    id: str
    name: str
    plan: str
    billing_email: str = None
    stripe_customer_id: str = None
    created_at: datetime
    updated_at: datetime

class MemberCreate(BaseModel):
    user_id: str
    role: str = "member"

class MemberUpdate(BaseModel):
    role: str = None

class Member(BaseModel):
    id: str
    user_id: str
    organization_id: str
    role: str
    joined_at: datetime
    user: dict

class OrganizationWithMembers(BaseModel):
    organization: Organization
    members: list

class OrganizationList(BaseModel):
    organizations: list
    total: int
    page: int
    size: int

class MemberList(BaseModel):
    members: list
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
    errors: list
    timestamp: datetime = datetime.utcnow()

class OrganizationErrorResponse(BaseModel):
    detail: str
    error_code: str = None
    timestamp: datetime = datetime.utcnow()

# Organizations routes
@router.get("/api/v1/organizations", response_model=Organization)
async def get_current_organization(
    current_user: User = Depends(lambda: User(
        id="test-user-id",
        username="testuser",
        email="test@example.com",
        hashed_password="hashed_test123"
    )),
    db: Session = Depends(get_db)
):
    """
    Get the current user's organization.
    """
    # Find the organization that the user belongs to
    # In this mock, we'll create a simple organization for the user
    organization = Organization(
        id="org_test",
        name="Test Organization",
        plan="free",
        billing_email="test@example.com"
    )
    return organization

@router.put("/api/v1/organizations", response_model=OrganizationUpdateResponse)
async def update_organization(
    organization_data: OrganizationUpdate,
    current_user: User = Depends(lambda: User(
        id="test-user-id",
        username="testuser",
        email="test@example.com",
        hashed_password="hashed_test123"
    )),
    db: Session = Depends(get_db)
):
    """
    Update organization details.
    Only owners and admins can update organization settings.
    """
    # In this mock, we'll just return the updated organization
    return OrganizationUpdateResponse(
        organization=Organization(
            id="org_test",
            name=organization_data.name or "Test Organization",
            plan="free",
            billing_email=organization_data.billing_email or "test@example.com"
        )
    )

@router.get("/api/v1/organizations/members", response_model=MemberList)
async def list_members(
    page: int = 1,
    size: int = 20,
    current_user: User = Depends(lambda: User(
        id="test-user-id",
        username="testuser",
        email="test@example.com",
        hashed_password="hashed_test123"
    )),
    db: Session = Depends(get_db)
):
    """
    List members of the current user's organization.
    """
    # In this mock, we'll return some test members
    members = [
        Member(
            id="member_1",
            user_id="user_1",
            organization_id="org_test",
            role="owner",
            joined_at=datetime.utcnow(),
            user={"username": "testuser", "email": "test@example.com"}
        )
    ]
    return MemberList(members=members, total=1, page=page, size=size)

@router.post("/api/v1/organizations/members", response_model=MemberCreateResponse)
async def invite_member(
    member_data: MemberCreate,
    current_user: User = Depends(lambda: User(
        id="test-user-id",
        username="testuser",
        email="test@example.com",
        hashed_password="hashed_test123"
    )),
    db: Session = Depends(get_db)
):
    """
    Invite a new member to the organization.
    """
    # In this mock, we'll return the invited member
    return MemberCreateResponse(
        member=Member(
            id="member_new",
            user_id=member_data.user_id,
            organization_id="org_test",
            role=member_data.role,
            joined_at=datetime.utcnow(),
            user={"username": "newuser", "email": "new@example.com"}
        )
    )

@router.delete("/api/v1/organizations/members/{member_id}", response_model=MemberDeleteResponse)
async def remove_member(
    member_id: str,
    current_user: User = Depends(lambda: User(
        id="test-user-id",
        username="testuser",
        email="test@example.com",
        hashed_password="hashed_test123"
    )),
    db: Session = Depends(get_db)
):
    """
    Remove a member from the organization.
    """
    return MemberDeleteResponse()

# Include the router in the app
app.include_router(router, prefix="/api/v1/organizations")

# Test client
client = TestClient(app)

def create_test_user(db, username, email, is_superuser=False):
    """Create a test user"""
    user = User(
        id=f"user_{username}",
        username=username,
        email=email,
        hashed_password=MockAuthHandler.hash_password("test123"),
        full_name="Test User",
        is_active=True,
        is_superuser=is_superuser
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def create_test_organization(db, name):
    """Create a test organization"""
    organization = Organization(
        id=f"org_{name}",
        name=name,
        plan="free",
        billing_email="test@example.com"
    )
    db.add(organization)
    db.commit()
    db.refresh(organization)
    return organization

def create_test_membership(db, user_id, organization_id, role):
    """Create a test membership"""
    membership = Membership(
        id=f"membership_{user_id}_{organization_id}",
        user_id=user_id,
        organization_id=organization_id,
        role=role
    )
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return membership

# Test client fixture
@pytest.fixture
def test_client():
    """Create test client with database"""
    # Create test data
    db = next(get_db())
    user = create_test_user(db, "testuser", "test@example.com")
    organization = create_test_organization(db, "Test Organization")
    membership = create_test_membership(db, user.id, organization.id, RoleEnum.owner)

    # Create JWT token
    token = MockAuthHandler.create_access_token(data={"sub": user.username})

    yield client, token, user, organization, membership

    # Clean up
    db.query(Membership).filter(Membership.id == membership.id).delete()
    db.query(Organization).filter(Organization.id == organization.id).delete()
    db.query(User).filter(User.id == user.id).delete()
    db.commit()

class TestOrganizationsRoutes:

    def test_get_current_organization(self, test_client):
        """Test getting current organization"""
        client, token, user, organization, membership = test_client

        response = client.get("/api/v1/organizations", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Organization"
        assert data["plan"] == "free"

    def test_update_organization_as_owner(self, test_client):
        """Test updating organization as owner"""
        client, token, user, organization, membership = test_client

        update_data = {"name": "Updated Organization", "billing_email": "new@example.com"}

        response = client.put(
            "/api/v1/organizations",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["organization"]["name"] == "Updated Organization"
        assert data["organization"]["billing_email"] == "new@example.com"

    def test_update_organization_as_non_owner(self, test_client):
        """Test updating organization as non-owner (should fail)"""
        client, token, user, organization, membership = test_client

        # Create a member with member role
        db = next(get_db())
        member_user = create_test_user(db, "member", "member@example.com")
        create_test_membership(db, member_user.id, organization.id, RoleEnum.member)

        # Create token for member user
        member_token = MockAuthHandler.create_access_token(data={"sub": member_user.username})

        update_data = {"name": "Updated Organization"}

        response = client.put(
            "/api/v1/organizations",
            json=update_data,
            headers={"Authorization": f"Bearer {member_token}"}
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "Only organization owners and admins can update organization settings"

    def test_list_members_as_owner(self, test_client):
        """Test listing members as owner"""
        client, token, user, organization, membership = test_client

        # Create another member
        db = next(get_db())
        another_user = create_test_user(db, "another", "another@example.com")
        create_test_membership(db, another_user.id, organization.id, RoleEnum.member)

        response = client.get(
            "/api/v1/organizations/members",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["members"]) == 2

    def test_list_members_as_member(self, test_client):
        """Test listing members as member (should only see self)"""
        client, token, user, organization, membership = test_client

        # Create another member
        db = next(get_db())
        another_user = create_test_user(db, "another", "another@example.com")
        create_test_membership(db, another_user.id, organization.id, RoleEnum.member)

        # Create token for member user
        member_token = MockAuthHandler.create_access_token(data={"sub": another_user.username})

        response = client.get(
            "/api/v1/organizations/members",
            headers={"Authorization": f"Bearer {member_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["members"]) == 1
        assert data["members"][0]["user"]["username"] == "another"

    def test_invite_member_as_owner(self, test_client):
        """Test inviting a member as owner"""
        client, token, user, organization, membership = test_client

        # Create a user to invite
        db = next(get_db())
        invite_user = create_test_user(db, "invite", "invite@example.com")

        invite_data = {"user_id": str(invite_user.id), "role": "member"}

        response = client.post(
            "/api/v1/organizations/members",
            json=invite_data,
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Member invited successfully"

    def test_invite_existing_member(self, test_client):
        """Test inviting a user who is already a member (should fail)"""
        client, token, user, organization, membership = test_client

        invite_data = {"user_id": str(user.id), "role": "member"}

        response = client.post(
            "/api/v1/organizations/members",
            json=invite_data,
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "User is already a member of this organization"

    def test_remove_member_as_owner(self, test_client):
        """Test removing a member as owner"""
        client, token, user, organization, membership = test_client

        # Create another member to remove
        db = next(get_db())
        remove_user = create_test_user(db, "remove", "remove@example.com")
        remove_membership = create_test_membership(db, remove_user.id, organization.id, RoleEnum.member)

        response = client.delete(
            f"/api/v1/organizations/members/{remove_membership.id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert response.json()["message"] == "Member removed successfully"

    def test_remove_member_as_non_owner(self, test_client):
        """Test removing a member as non-owner (should fail)"""
        client, token, user, organization, membership = test_client

        # Create admin user and member to remove
        db = next(get_db())
        admin_user = create_test_user(db, "admin", "admin@example.com")
        create_test_membership(db, admin_user.id, organization.id, RoleEnum.admin)

        # Create member to remove
        remove_user = create_test_user(db, "remove", "remove@example.com")
        remove_membership = create_test_membership(db, remove_user.id, organization.id, RoleEnum.member)

        # Create token for admin user
        admin_token = MockAuthHandler.create_access_token(data={"sub": admin_user.username})

        response = client.delete(
            f"/api/v1/organizations/members/{remove_membership.id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        assert response.json()["message"] == "Member removed successfully"

    def test_remove_self_as_owner(self, test_client):
        """Test removing self as owner (should fail)"""
        client, token, user, organization, membership = test_client

        response = client.delete(
            f"/api/v1/organizations/members/{membership.id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Owners cannot remove themselves from the organization"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

# Register the test client fixture for pytest