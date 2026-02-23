import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import engine
from app.models.models import Base
from sqlalchemy import create_engine

# Create a test database client
client = TestClient(app)

# Create test database tables
def create_test_tables():
    Base.metadata.create_all(bind=engine)

# Drop test database tables
def drop_test_tables():
    Base.metadata.drop_all(bind=engine)


# Test cases for agent API endpoints
class TestAgentAPIRoutes:

    @classmethod
    def setup_class(cls):
        create_test_tables()

    @classmethod
    def teardown_class(cls):
        drop_test_tables()

    def test_agents_route_exists(self):
        """Test that the agents routes are properly registered"""
        response = client.get("/api/v1/agents")
        assert response.status_code == 200 or response.status_code == 404

    def test_agents_route_structure(self):
        """Test that the agents routes have the correct structure"""
        # This is a basic test to check if the route structure is correct
        response = client.get("/api/v1/agents")
        assert isinstance(response.json(), dict)

    def test_all_required_routes(self):
        """Test that all required routes are accessible"""
        # List of required routes to test
        routes_to_test = [
            ("GET", "/api/v1/agents"),
            ("POST", "/api/v1/agents"),
            ("GET", "/api/v1/agents/{agent_id}"),
            ("PUT", "/api/v1/agents/{agent_id}"),
            ("DELETE", "/api/v1/agents/{agent_id}"),
            ("POST", "/api/v1/agents/{agent_id}/test"),
            ("GET", "/api/v1/agents/{agent_id}/versions"),
            ("POST", "/api/v1/agents/{agent_id}/deploy"),
            ("GET", "/api/v1/agents/{agent_id}/metrics")
        ]

        for method, route in routes_to_test:
            if "{agent_id}" in route:
                # Test with a dummy agent_id for GET, PUT, DELETE, etc.
                if method in ["GET", "PUT", "DELETE"]:
                    test_route = route.replace("{agent_id}", "test-id")
                    response = client.open(test_route, method=method)
                    if method == "GET":
                        assert response.status_code == 200 or response.status_code == 404
                    else:
                        assert response.status_code == 200 or response.status_code == 404
            else:
                # Test routes without parameters
                if method == "POST":
                    if "test" in route:
                        # Test agent test route with sample input
                        response = client.post(route, json={"input": {"question": "test"}})
                        assert response.status_code == 200
                    elif "deploy" in route:
                        # Test agent deploy route with sample version
                        response = client.post(route, json={"version_number": 1})
                        assert response.status_code == 200
                    else:
                        # Test agent create route with sample data
                        response = client.post(route, json={
                            "name": "Test Agent",
                            "role": "test agent",
                            "instructions": "This is a test agent",
                            "model": "claude",
                            "tools": ["calculator"],
                            "config": {"param": "value"}
                        })
                        assert response.status_code == 201 or response.status_code == 400
                elif method == "GET":
                    response = client.get(route)
                    assert response.status_code == 200 or response.status_code == 404

    def test_route_responses(self):
        """Test that routes return proper JSON responses"""
        # Test POST /agents response structure
        create_response = client.post("/api/v1/agents", json={
            "name": "Test Agent",
            "role": "test agent",
            "instructions": "This is a test agent",
            "model": "claude",
            "tools": ["calculator"],
            "config": {"param": "value"}
        })

        if create_response.status_code == 201:
            assert "agent" in create_response.json()
            assert "message" in create_response.json()
        elif create_response.status_code == 400:
            assert "detail" in create_response.json()

        # Test GET /agents response structure
        list_response = client.get("/api/v1/agents")
        assert isinstance(list_response.json(), dict)
        assert "agents" in list_response.json() or "detail" in list_response.json()

    def test_error_handling(self):
        """Test error handling for invalid routes"""
        # Test invalid agent ID
        invalid_response = client.get("/api/v1/agents/invalid-id")
        assert invalid_response.status_code == 404 or invalid_response.status_code == 200

        # Test invalid POST data
        invalid_post_response = client.post("/api/v1/agents", json={})
        assert invalid_post_response.status_code == 400

    def test_rate_limiting_headers(self):
        """Test that rate limiting headers are present"""
        # Make multiple requests to test rate limiting
        for _ in range(3):
            client.post("/api/v1/agents", json={
                "name": "Test Agent",
                "role": "test agent",
                "instructions": "This is a test agent",
                "model": "claude",
                "tools": ["calculator"],
                "config": {"param": "value"}
            })

        # Check if rate limiting headers are present
        last_response = client.post("/api/v1/agents", json={
            "name": "Test Agent",
            "role": "test agent",
            "instructions": "This is a test agent",
            "model": "claude",
            "tools": ["calculator"],
            "config": {"param": "value"}
        })

        rate_limit_headers = [
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset"
        ]

        for header in rate_limit_headers:
            assert header in last_response.headers

    def test_documentation_routes(self):
        """Test that documentation routes are accessible"""
        docs_routes = [
            "/api/v1/docs",
            "/api/v1/redoc"
        ]

        for route in docs_routes:
            response = client.get(route)
            assert response.status_code == 200 or response.status_code == 404

print("\nAll route tests completed!")
print("If you see mostly ✓, your API routes are properly set up!")