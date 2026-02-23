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
class TestAgentAPI:

    @classmethod
    def setup_class(cls):
        create_test_tables()

    @classmethod
    def teardown_class(cls):
        drop_test_tables()

    def test_create_agent(self):
        # Test creating an agent
        response = client.post("/api/v1/agents", json={
            "name": "Test Agent",
            "role": "test agent",
            "instructions": "This is a test agent",
            "model": "claude",
            "tools": ["calculator"],
            "config": {"param": "value"}
        })

        assert response.status_code == 201
        assert "agent" in response.json()
        assert "id" in response.json()["agent"]

    def test_list_agents(self):
        # Test listing agents
        response = client.get("/api/v1/agents")

        assert response.status_code == 200
        assert "agents" in response.json()
        assert "total" in response.json()

    def test_get_agent(self):
        # First create an agent to get its ID
        create_response = client.post("/api/v1/agents", json={
            "name": "Test Agent",
            "role": "test agent",
            "instructions": "This is a test agent",
            "model": "claude",
            "tools": ["calculator"],
            "config": {"param": "value"}
        })

        agent_id = create_response.json()["agent"]["id"]

        # Test getting agent details
        response = client.get(f"/api/v1/agents/{agent_id}")

        assert response.status_code == 200
        assert "id" in response.json()
        assert response.json()["id"] == agent_id

    def test_update_agent(self):
        # First create an agent to get its ID
        create_response = client.post("/api/v1/agents", json={
            "name": "Test Agent",
            "role": "test agent",
            "instructions": "This is a test agent",
            "model": "claude",
            "tools": ["calculator"],
            "config": {"param": "value"}
        })

        agent_id = create_response.json()["agent"]["id"]

        # Test updating agent
        response = client.put("/api/v1/agents/{agent_id}", json={
            "name": "Updated Test Agent",
            "role": "updated test agent",
            "instructions": "Updated instructions",
            "model": "claude",
            "tools": ["calculator", "web_search"],
            "config": {"param": "updated value"}
        })

        assert response.status_code == 200
        assert "agent" in response.json()
        assert response.json()["agent"]["name"] == "Updated Test Agent"

    def test_delete_agent(self):
        # First create an agent to get its ID
        create_response = client.post("/api/v1/agents", json={
            "name": "Test Agent",
            "role": "test agent",
            "instructions": "This is a test agent",
            "model": "claude",
            "tools": ["calculator"],
            "config": {"param": "value"}
        })

        agent_id = create_response.json()["agent"]["id"]

        # Test deleting agent
        response = client.delete(f"/api/v1/agents/{agent_id}")

        assert response.status_code == 200
        assert "message" in response.json()
        assert response.json()["message"] == "Agent deleted successfully"

    def test_test_agent(self):
        # First create an agent to get its ID
        create_response = client.post("/api/v1/agents", json={
            "name": "Test Agent",
            "role": "test agent",
            "instructions": "This is a test agent",
            "model": "claude",
            "tools": ["calculator"],
            "config": {"param": "value"}
        })

        agent_id = create_response.json()["agent"]["id"]

        # Test agent testing endpoint
        response = client.post(f"/api/v1/agents/{agent_id}/test", json={
            "input": {"question": "What is 2 + 2?"}
        })

        assert response.status_code == 200
        assert "success" in response.json()
        assert response.json()["success"] is True

    def test_list_agent_versions(self):
        # First create an agent to get its ID
        create_response = client.post("/api/v1/agents", json={
            "name": "Test Agent",
            "role": "test agent",
            "instructions": "This is a test agent",
            "model": "claude",
            "tools": ["calculator"],
            "config": {"param": "value"}
        })

        agent_id = create_response.json()["agent"]["id"]

        # Test listing agent versions
        response = client.get(f"/api/v1/agents/{agent_id}/versions")

        assert response.status_code == 200
        assert "versions" in response.json()
        assert "total" in response.json()

    def test_deploy_agent_version(self):
        # First create an agent to get its ID
        create_response = client.post("/api/v1/agents", json={
            "name": "Test Agent",
            "role": "test agent",
            "instructions": "This is a test agent",
            "model": "claude",
            "tools": ["calculator"],
            "config": {"param": "value"}
        })

        agent_id = create_response.json()["agent"]["id"]

        # Test deploying agent version
        response = client.post(f"/api/v1/agents/{agent_id}/deploy", json={
            "version_number": 1
        })

        assert response.status_code == 200
        assert "version" in response.json()
        assert "message" in response.json()
        assert response.json()["message"] == "Agent version deployed successfully"

    def test_get_agent_metrics(self):
        # First create an agent to get its ID
        create_response = client.post("/api/v1/agents", json={
            "name": "Test Agent",
            "role": "test agent",
            "instructions": "This is a test agent",
            "model": "claude",
            "tools": ["calculator"],
            "config": {"param": "value"}
        })

        agent_id = create_response.json()["agent"]["id"]

        # Test getting agent metrics
        response = client.get(f"/api/v1/agents/{agent_id}/metrics")

        assert response.status_code == 200
        assert "metrics" in response.json()
        assert "total_tasks" in response.json()["metrics"]
        assert "success_rate" in response.json()["metrics"]