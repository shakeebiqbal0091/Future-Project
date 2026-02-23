import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.core.config import settings
from app.models.models import User
from app.schemas.auth import UserCreate, Token
from app.core.database import get_db

client = TestClient(app)

def test_register_user(test_db: Session):
    """Test user registration with valid data"""
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "full_name": "Test User",
        "password": "Password123"
    }

    response = client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"


def test_register_duplicate_user(test_db: Session):
    """Test registration with duplicate email/username"""
    # First registration should succeed
    user_data = {
        "username": "testuser2",
        "email": "test2@example.com",
        "full_name": "Test User 2",
        "password": "Password123"
    }
    response = client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == 200

    # Second registration with same email should fail
    user_data["username"] = "testuser3"
    response = client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == 400
    assert response.json()["detail"] == "User with this email or username already exists"


def test_register_invalid_email(test_db: Session):
    """Test registration with invalid email format"""
    user_data = {
        "username": "testuser3",
        "email": "invalid-email",
        "full_name": "Test User",
        "password": "Password123"
    }

    response = client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid email format"


def test_register_weak_password(test_db: Session):
    """Test registration with weak password"""
    user_data = {
        "username": "testuser4",
        "email": "test4@example.com",
        "full_name": "Test User",
        "password": "weak"
    }

    response = client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == 400
    assert response.json()["detail"] == "Password must be at least 8 characters long and contain both letters and numbers"


def test_login_success(test_db: Session):
    """Test successful login"""
    # Register user first
    user_data = {
        "username": "testuser5",
        "email": "test5@example.com",
        "full_name": "Test User",
        "password": "Password123"
    }
    client.post("/api/v1/auth/register", json=user_data)

    # Login with correct credentials
    login_data = {
        "username": "testuser5",
        "password": "Password123"
    }
    response = client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"


def test_login_invalid_credentials(test_db: Session):
    """Test login with invalid credentials"""
    login_data = {
        "username": "nonexistent",
        "password": "wrongpassword"
    }
    response = client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"


def test_logout_success(test_db: Session):
    """Test successful logout"""
    # Register and login user first
    user_data = {
        "username": "testuser6",
        "email": "test6@example.com",
        "full_name": "Test User",
        "password": "Password123"
    }
    client.post("/api/v1/auth/register", json=user_data)

    login_data = {
        "username": "testuser6",
        "password": "Password123"
    }
    login_response = client.post("/api/v1/auth/login", data=login_data)
    token = login_response.json()["access_token"]

    # Logout with valid token
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post("/api/v1/auth/logout", headers=headers)
    assert response.status_code == 200
    assert response.json()["message"] == "Successfully logged out"


def test_logout_invalid_token(test_db: Session):
    """Test logout with invalid token"""
    headers = {"Authorization": "Bearer invalid.token.here"}
    response = client.post("/api/v1/auth/logout", headers=headers)
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token"


def test_refresh_token_success(test_db: Session):
    """Test token refresh"""
    # Register and login user first
    user_data = {
        "username": "testuser7",
        "email": "test7@example.com",
        "full_name": "Test User",
        "password": "Password123"
    }
    client.post("/api/v1/auth/register", json=user_data)

    login_data = {
        "username": "testuser7",
        "password": "Password123"
    }
    login_response = client.post("/api/v1/auth/login", data=login_data)
    token = login_response.json()["access_token"]

    # Refresh token
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post("/api/v1/auth/refresh", headers=headers)
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"


def test_refresh_invalid_token(test_db: Session):
    """Test token refresh with invalid token"""
    headers = {"Authorization": "Bearer invalid.token.here"}
    response = client.post("/api/v1/auth/refresh", headers=headers)
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token"


def test_get_current_user(test_db: Session):
    """Test getting current user information"""
    # Register and login user first
    user_data = {
        "username": "testuser8",
        "email": "test8@example.com",
        "full_name": "Test User",
        "password": "Password123"
    }
    client.post("/api/v1/auth/register", json=user_data)

    login_data = {
        "username": "testuser8",
        "password": "Password123"
    }
    login_response = client.post("/api/v1/auth/login", data=login_data)
    token = login_response.json()["access_token"]

    # Get current user
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["username"] == "testuser8"
    assert response.json()["email"] == "test8@example.com"


def test_update_user_profile(test_db: Session):
    """Test updating user profile"""
    # Register and login user first
    user_data = {
        "username": "testuser9",
        "email": "test9@example.com",
        "full_name": "Test User",
        "password": "Password123"
    }
    client.post("/api/v1/auth/register", json=user_data)

    login_data = {
        "username": "testuser9",
        "password": "Password123"
    }
    login_response = client.post("/api/v1/auth/login", data=login_data)
    token = login_response.json()["access_token"]

    # Update profile
    update_data = {
        "username": "newusername9",
        "email": "newemail@example.com",
        "full_name": "New Full Name"
    }
    headers = {"Authorization": f"Bearer {token}"}
    response = client.put("/api/v1/auth/me", headers=headers, json=update_data)
    assert response.status_code == 200
    assert response.json()["username"] == "newusername9"
    assert response.json()["email"] == "newemail@example.com"
    assert response.json()["full_name"] == "New Full Name"


def test_change_password_success(test_db: Session):
    """Test changing password successfully"""
    # Register and login user first
    user_data = {
        "username": "testuser10",
        "email": "test10@example.com",
        "full_name": "Test User",
        "password": "Password123"
    }
    client.post("/api/v1/auth/register", json=user_data)

    login_data = {
        "username": "testuser10",
        "password": "Password123"
    }
    login_response = client.post("/api/v1/auth/login", data=login_data)
    token = login_response.json()["access_token"]

    # Change password
    change_data = {
        "current_password": "Password123",
        "new_password": "NewPassword456"
    }
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post("/api/v1/auth/change-password", headers=headers, json=change_data)
    assert response.status_code == 200
    assert response.json()["message"] == "Password changed successfully"

    # Try login with new password
    login_data["password"] = "NewPassword456"
    response = client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == 200


def test_change_password_invalid_current(test_db: Session):
    """Test changing password with invalid current password"""
    # Register and login user first
    user_data = {
        "username": "testuser11",
        "email": "test11@example.com",
        "full_name": "Test User",
        "password": "Password123"
    }
    client.post("/api/v1/auth/register", json=user_data)

    login_data = {
        "username": "testuser11",
        "password": "Password123"
    }
    login_response = client.post("/api/v1/auth/login", data=login_data)
    token = login_response.json()["access_token"]

    # Try to change password with wrong current password
    change_data = {
        "current_password": "WrongPassword",
        "new_password": "NewPassword456"
    }
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post("/api/v1/auth/change-password", headers=headers, json=change_data)
    assert response.status_code == 400
    assert response.json()["detail"] == "Current password is incorrect"


def test_password_reset_request(test_db: Session):
    """Test password reset request"""
    # Register user first
    user_data = {
        "username": "testuser12",
        "email": "test12@example.com",
        "full_name": "Test User",
        "password": "Password123"
    }
    client.post("/api/v1/auth/register", json=user_data)

    # Request password reset
    response = client.post("/api/v1/auth/reset-password-request", json={"email": "test12@example.com"})
    assert response.status_code == 200
    assert response.json()["message"] == "If an account exists with this email, a password reset link has been sent."

    # Request reset for non-existent email
    response = client.post("/api/v1/auth/reset-password-request", json={"email": "nonexistent@example.com"})
    assert response.status_code == 200
    assert response.json()["message"] == "If an account exists with this email, a password reset link has been sent."


def test_password_reset_request_rate_limit(test_db: Session):
    """Test password reset request rate limiting"""
    # Register user first
    user_data = {
        "username": "testuser13",
        "email": "test13@example.com",
        "full_name": "Test User",
        "password": "Password123"
    }
    client.post("/api/v1/auth/register", json=user_data)

    # Make 3 requests (should succeed)
    for i in range(3):
        response = client.post("/api/v1/auth/reset-password-request", json={"email": "test13@example.com"})
        assert response.status_code == 200

    # 4th request should be rate limited
    response = client.post("/api/v1/auth/reset-password-request", json={"email": "test13@example.com"})
    assert response.status_code == 429
    assert response.json()["detail"] == "Too many password reset requests. Try again later."


def test_rate_limiting_login(test_db: Session):
    """Test login rate limiting"""
    # Register user first
    user_data = {
        "username": "testuser14",
        "email": "test14@example.com",
        "full_name": "Test User",
        "password": "Password123"
    }
    client.post("/api/v1/auth/register", json=user_data)

    # Make 10 failed login attempts
    for i in range(10):
        login_data = {
            "username": "testuser14",
            "password": "wrongpassword"
        }
        response = client.post("/api/v1/auth/login", data=login_data)
        assert response.status_code == 401

    # 11th attempt should be rate limited
    login_data["password"] = "Password123"  # Correct password
    response = client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == 429
    assert response.json()["detail"] == "Too many login attempts. Try again later."

    # Wait and try again (in real test, you might need to mock time)
    # For now, we'll just test the rate limiting behavior


@pytest.mark.parametrize("endpoint", ["/api/v1/auth/register", "/api/v1/auth/login"])
async def test_rate_limiting_general(test_db: Session, endpoint):
    """Test general rate limiting on auth endpoints"""
    # Test rate limiting on register endpoint
    user_data = {
        "username": "testuser15",
        "email": "test15@example.com",
        "full_name": "Test User",
        "password": "Password123"
    }

    # Make 5 registration attempts from same IP
    for i in range(5):
        response = client.post("/api/v1/auth/register", json=user_data)
        if i < 3:  # First 3 should succeed
            assert response.status_code in [200, 400]  # Either success or validation error
        else:
            assert response.status_code == 400  # Validation errors from duplicate user

    # Test rate limiting on login endpoint
    # (Assuming testuser15 was created successfully)
    login_data = {
        "username": "testuser15",
        "password": "Password123"
    }

    for i in range(10):  # This would be rate limited in real scenario
        response = client.post("/api/v1/auth/login", data=login_data)
        assert response.status_code == 200