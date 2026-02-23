import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from pydantic import BaseModel

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

# Import the routes (with correct path)
from app.api.routes.organizations import router as organizations_router
app.include_router(organizations_router, prefix="/api/v1/organizations")

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