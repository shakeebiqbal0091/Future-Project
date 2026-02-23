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


@pytest.fixture
def test_superuser(db: Session):
    superuser = User(
        email="admin@example.com",
        username="admin",
        full_name="Admin User",
        hashed_password="hashed_password",
        is_active=True,
        is_superuser=True
    )
    db.add(superuser)
    db.commit()
    return superuser


class TestUsers:
    def test_get_users(self, db: Session, test_user, test_organization, test_member):
        # Login to get token
        login_response = client.post("/api/v1/auth/login", data={
            "username": test_user.email,
            "password": "password"
        })
        token = login_response.json()["access_token"]

        response = client.get(
            "/api/v1/users/",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert len(response.json()) >= 1

    def test_get_user(self, db: Session, test_user, test_organization, test_member):
        # Login to get token
        login_response = client.post("/api/v1/auth/login", data={
            "username": test_user.email,
            "password": "password"
        })
        token = login_response.json()["access_token"]

        response = client.get(
            f"/api/v1/users/{test_user.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["email"] == test_user.email

    def test_get_user_not_found(self, db: Session, test_user, test_organization, test_member):
        # Login to get token
        login_response = client.post("/api/v1/auth/login", data={
            "username": test_user.email,
            "password": "password"
        })
        token = login_response.json()["access_token"]

        response = client.get(
            "/api/v1/users/99999",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "User not found"

    def test_update_user(self, db: Session, test_user, test_organization, test_member):
        # Login to get token
        login_response = client.post("/api/v1/auth/login", data={
            "username": test_user.email,
            "password": "password"
        })
        token = login_response.json()["access_token"]

        response = client.put(
            f"/api/v1/users/{test_user.id}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "email": "updated@example.com",
                "username": "updateduser",
                "full_name": "Updated User",
                "is_active": True
            }
        )
        assert response.status_code == 200
        assert response.json()["email"] == "updated@example.com"

    def test_update_user_permissions(self, db: Session, test_user, test_organization, test_member, test_superuser):
        # Login as superuser
        login_response = client.post("/api/v1/auth/login", data={
            "username": test_superuser.email,
            "password": "password"
        })
        token = login_response.json()["access_token"]

        # Try to update another user
        response = client.put(
            f"/api/v1/users/{test_user.id}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "email": "updated@example.com",
                "is_active": False
            }
        )
        assert response.status_code == 200

    def test_update_user_permission_denied(self, db: Session, test_user, test_organization, test_member):
        # Create another test user
        another_user = User(
            email="another@example.com",
            username="another",
            full_name="Another User",
            hashed_password="hashed_password",
            is_active=True,
            is_superuser=False
        )
        db.add(another_user)
        db.commit()

        # Login as test_user
        login_response = client.post("/api/v1/auth/login", data={
            "username": test_user.email,
            "password": "password"
        })
        token = login_response.json()["access_token"]

        # Try to update another user (should fail)
        response = client.put(
            f"/api/v1/users/{another_user.id}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "email": "updated@example.com"
            }
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Not enough permissions"

    def test_delete_user(self, db: Session, test_user, test_organization, test_member):
        # Login to get token
        login_response = client.post("/api/v1/auth/login", data={
            "username": test_user.email,
            "password": "password"
        })
        token = login_response.json()["access_token"]

        response = client.delete(
            f"/api/v1/users/{test_user.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 204

    def test_get_user_organizations(self, db: Session, test_user, test_organization, test_member):
        # Login to get token
        login_response = client.post("/api/v1/auth/login", data={
            "username": test_user.email,
            "password": "password"
        })
        token = login_response.json()["access_token"]

        response = client.get(
            "/api/v1/users/me/organizations",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert len(response.json()) >= 1

    def test_search_users(self, db: Session, test_user, test_organization, test_member, test_superuser):
        # Login as superuser
        login_response = client.post("/api/v1/auth/login", data={
            "username": test_superuser.email,
            "password": "password"
        })
        token = login_response.json()["access_token"]

        response = client.get(
            "/api/v1/users/search",
            headers={"Authorization": f"Bearer {token}"},
            params={"query": "test"}
        )
        assert response.status_code == 200
        assert len(response.json()["items"]) >= 1

    def test_search_users_permission_denied(self, db: Session, test_user, test_organization, test_member):
        # Login as regular user
        login_response = client.post("/api/v1/auth/login", data={
            "username": test_user.email,
            "password": "password"
        })
        token = login_response.json()["access_token"]

        response = client.get(
            "/api/v1/users/search",
            headers={"Authorization": f"Bearer {token}"},
            params={"query": "test"}
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Search available only for superusers"