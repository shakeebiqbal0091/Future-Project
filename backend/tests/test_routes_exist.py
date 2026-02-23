from fastapi.testclient import TestClient
from app.api.routes import auth_router

client = TestClient(auth_router)

def test_auth_routes_exist():
    """Test that auth routes exist"""
    # Test register endpoint exists
    response = client.post("/api/v1/auth/register")
    assert response.status_code == 422  # Should fail validation, but endpoint exists

    # Test login endpoint exists
    response = client.post("/api/v1/auth/login")
    assert response.status_code == 422  # Should fail validation, but endpoint exists

    # Test me endpoint exists
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401  # Should fail authentication, but endpoint exists

    # Test update me endpoint exists
    response = client.put("/api/v1/auth/me")
    assert response.status_code == 401  # Should fail authentication, but endpoint exists

    # Test logout endpoint exists
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 401  # Should fail authentication, but endpoint exists

    # Test refresh endpoint exists
    response = client.post("/api/v1/auth/refresh")
    assert response.status_code == 401  # Should fail authentication, but endpoint exists

    # Test password reset request endpoint exists
    response = client.post("/api/v1/auth/reset-password-request")
    assert response.status_code == 422  # Should fail validation, but endpoint exists

    # Test password reset endpoint exists
    response = client.post("/api/v1/auth/reset-password")
    assert response.status_code == 422  # Should fail validation, but endpoint exists

    # Test change password endpoint exists
    response = client.post("/api/v1/auth/change-password")
    assert response.status_code == 401  # Should fail authentication, but endpoint exists

    # Test email verification endpoint exists
    response = client.post("/api/v1/auth/verify-email")
    assert response.status_code == 422  # Should fail validation, but endpoint exists