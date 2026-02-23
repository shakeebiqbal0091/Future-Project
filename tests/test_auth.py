import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from core.models import User, Organization, Member

from main import app

client = TestClient(app)


@pytest.fixture
def test_user(db: Session):
    user = User(
        email="test@example.com",
        username="testuser",
        full_name="Test User",
        hashed_password="hashed_password",
        is_active=True,
        is_superuser=False
    )
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def test_organization(db: Session, test_user):
    org = Organization(
        name="Test Organization",
        description="Test org",
        slug="test-org",
        is_active=True,
        owner_id=test_user.id
    )
    db.add(org)
    db.commit()
    return org


@pytest.fixture
def test_member(db: Session, test_user, test_organization):
    member = Member(
        user_id=test_user.id,
        organization_id=test_organization.id,
        role="owner"
    )
    db.add(member)
    db.commit()
    return member


class TestAuth:
    def test_register(self, db: Session):
        response = client.post("/api/v1/auth/register", json={
            "email": "newuser@example.com",
            "username": "newuser",
            "full_name": "New User",
            "password": "password123"
        })
        assert response.status_code == 201
        assert "access_token" in response.json()

    def test_register_duplicate_email(self, db: Session, test_user):
        response = client.post("/api/v1/auth/register", json={
            "email": test_user.email,
            "username": "duplicate",
            "full_name": "Duplicate",
            "password": "password123"
        })
        assert response.status_code == 400
        assert response.json()["detail"] == "Email already registered"

    def test_login_success(self, db: Session, test_user):
        # Create test user with hashed password
        test_user.hashed_password = "hashed_password"
        db.commit()

        response = client.post("/api/v1/auth/login", data={
            "username": test_user.email,
            "password": "password"
        })
        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_login_failure(self, db: Session, test_user):
        response = client.post("/api/v1/auth/login", data={
            "username": test_user.email,
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        assert response.json()["detail"] == "Incorrect email or password"

    def test_get_current_user(self, db: Session, test_user, test_organization, test_member):
        # Login to get token
        login_response = client.post("/api/v1/auth/login", data={
            "username": test_user.email,
            "password": "password"
        })
        token = login_response.json()["access_token"]

        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["email"] == test_user.email

    def test_update_current_user(self, db: Session, test_user, test_organization, test_member):
        # Login to get token
        login_response = client.post("/api/v1/auth/login", data={
            "username": test_user.email,
            "password": "password"
        })
        token = login_response.json()["access_token"]

        response = client.put(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "email": "updated@example.com",
                "username": "updateduser",
                "full_name": "Updated User"
            }
        )
        assert response.status_code == 200
        assert response.json()["email"] == "updated@example.com"

    def test_logout(self, db: Session, test_user, test_organization, test_member):
        # Login to get token
        login_response = client.post("/api/v1/auth/login", data={
            "username": test_user.email,
            "password": "password"
        })
        token = login_response.json()["access_token"]

        response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Logout successful"