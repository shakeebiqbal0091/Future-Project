import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app, get_db, engine, SessionLocal, Base

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Override get_db for testing
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# Test client
client = TestClient(app)

# Test setup
@pytest.fixture(autouse=True)
async def setup_database():
    # Create all tables
    Base.metadata.create_all(bind=test_engine)

    # Create test data
    yield

    # Clean up after tests
    Base.metadata.drop_all(bind=test_engine)

# Test cases
class TestRootEndpoint:
    def test_root_endpoint(self):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "AI Agent Orchestration Platform API"
        assert "endpoints" in data

    def test_health_check(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"
        assert data["database"] == "connected"

class TestAuthEndpoint:
    def test_register_user(self):
        user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "full_name": "Test User",
            "password": "testpassword"
        }
        response = client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert "token" in data
        assert data["user"]["email"] == "test@example.com"

    def test_login_user(self):
        # First register a user
        register_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "testpassword"
        }
        client.post("/api/v1/auth/register", json=register_data)

        # Then login
        login_data = {
            "email": "test@example.com",
            "password": "testpassword"
        }
        response = client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert "token" in data

class TestOrganizationEndpoint:
    def test_create_organization(self, setup_database):
        # First create a user and get token
        register_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "testpassword"
        }
        response = client.post("/api/v1/auth/register", json=register_data)
        token = response.json()["token"]["access_token"]

        # Create organization
        headers = {"Authorization": f"Bearer {token}"}
        org_data = {
            "name": "Test Organization",
            "slug": "test-org",
            "description": "Test organization description"
        }
        response = client.post("/api/v1/organizations/", json=org_data, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Organization"

class TestAgentEndpoint:
    def test_create_agent(self, setup_database):
        # Setup: create user and organization
        register_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "testpassword"
        }
        response = client.post("/api/v1/auth/register", json=register_data)
        token = response.json()["token"]["access_token"]

        headers = {"Authorization": f"Bearer {token}"}

        # Create organization
        org_data = {
            "name": "Test Organization",
            "slug": "test-org",
            "description": "Test organization description"
        }
        org_response = client.post("/api/v1/organizations/", json=org_data, headers=headers)
        organization_id = org_response.json()["id"]

        # Create agent
        agent_data = {
            "name": "Test Agent",
            "description": "Test agent description",
            "type": "openai",
            "model": "gpt-3.5-turbo",
            "api_key": "test-api-key",
            "config": {"max_tokens": 1000},
            "organization_id": organization_id
        }
        response = client.post("/api/v1/agents/", json=agent_data, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Agent"

class TestWorkflowEndpoint:
    def test_create_workflow(self, setup_database):
        # Setup: create user, organization, and agent
        register_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "testpassword"
        }
        response = client.post("/api/v1/auth/register", json=register_data)
        token = response.json()["token"]["access_token"]

        headers = {"Authorization": f"Bearer {token}"}

        # Create organization
        org_data = {
            "name": "Test Organization",
            "slug": "test-org",
            "description": "Test organization description"
        }
        org_response = client.post("/api/v1/organizations/", json=org_data, headers=headers)
        organization_id = org_response.json()["id"]

        # Create agent
        agent_data = {
            "name": "Test Agent",
            "description": "Test agent description",
            "type": "openai",
            "model": "gpt-3.5-turbo",
            "api_key": "test-api-key",
            "config": {"max_tokens": 1000},
            "organization_id": organization_id
        }
        agent_response = client.post("/api/v1/agents/", json=agent_data, headers=headers)
        agent_id = agent_response.json()["id"]

        # Create workflow
        workflow_data = {
            "name": "Test Workflow",
            "description": "Test workflow description",
            "definition": {"steps": ["step1", "step2"]},
            "status": "draft",
            "organization_id": organization_id,
            "agent_id": agent_id
        }
        response = client.post("/api/v1/workflows/", json=workflow_data, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Workflow"

class TestTaskEndpoint:
    def test_create_task(self, setup_database):
        # Setup: create user, organization, agent, and workflow
        register_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "testpassword"
        }
        response = client.post("/api/v1/auth/register", json=register_data)
        token = response.json()["token"]["access_token"]

        headers = {"Authorization": f"Bearer {token}"}

        # Create organization
        org_data = {
            "name": "Test Organization",
            "slug": "test-org",
            "description": "Test organization description"
        }
        org_response = client.post("/api/v1/organizations/", json=org_data, headers=headers)
        organization_id = org_response.json()["id"]

        # Create agent
        agent_data = {
            "name": "Test Agent",
            "description": "Test agent description",
            "type": "openai",
            "model": "gpt-3.5-turbo",
            "api_key": "test-api-key",
            "config": {"max_tokens": 1000},
            "organization_id": organization_id
        }
        agent_response = client.post("/api/v1/agents/", json=agent_data, headers=headers)
        agent_id = agent_response.json()["id"]

        # Create workflow
        workflow_data = {
            "name": "Test Workflow",
            "description": "Test workflow description",
            "definition": {"steps": ["step1", "step2"]},
            "status": "draft",
            "organization_id": organization_id,
            "agent_id": agent_id
        }
        workflow_response = client.post("/api/v1/workflows/", json=workflow_data, headers=headers)
        workflow_id = workflow_response.json()["id"]

        # Create task
        task_data = {
            "name": "Test Task",
            "description": "Test task description",
            "input_data": {"prompt": "test prompt"},
            "organization_id": organization_id,
            "workflow_id": workflow_id
        }
        response = client.post("/api/v1/tasks/", json=task_data, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Task"

class TestIntegrationEndpoint:
    def test_create_integration(self, setup_database):
        # Setup: create user and organization
        register_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "testpassword"
        }
        response = client.post("/api/v1/auth/register", json=register_data)
        token = response.json()["token"]["access_token"]

        headers = {"Authorization": f"Bearer {token}"}

        # Create organization
        org_data = {
            "name": "Test Organization",
            "slug": "test-org",
            "description": "Test organization description"
        }
        org_response = client.post("/api/v1/organizations/", json=org_data, headers=headers)
        organization_id = org_response.json()["id"]

        # Create integration
        integration_data = {
            "name": "Test Slack Integration",
            "type": "slack",
            "config": {
                "webhook_url": "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX",
                "channel": "#general",
                "bot_name": "AI Agent"
            },
            "organization_id": organization_id
        }
        response = client.post("/api/v1/integrations/", json=integration_data, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Slack Integration"

class TestAnalyticsEndpoint:
    def test_get_usage_metrics(self, setup_database):
        # Setup: create user and organization
        register_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "testpassword"
        }
        response = client.post("/api/v1/auth/register", json=register_data)
        token = response.json()["token"]["access_token"]

        headers = {"Authorization": f"Bearer {token}"}

        # Create organization
        org_data = {
            "name": "Test Organization",
            "slug": "test-org",
            "description": "Test organization description"
        }
        org_response = client.post("/api/v1/organizations/", json=org_data, headers=headers)
        organization_id = org_response.json()["id"]

        # Test analytics endpoint
        query_data = {
            "metric": "token_usage",
            "group_by": "day",
            "time_range": "last_7d",
            "organization_id": organization_id
        }
        response = client.get("/api/v1/analytics/usage", params=query_data, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "summary" in data

class TestBillingEndpoint:
    def test_get_available_plans(self):
        response = client.get("/api/v1/billing/plans")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3  # free, pro, enterprise
        assert any(plan["id"] == "pro" for plan in data)

    def test_get_subscription_limits(self, setup_database):
        # Setup: create user and organization
        register_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "testpassword"
        }
        response = client.post("/api/v1/auth/register", json=register_data)
        token = response.json()["token"]["access_token"]

        headers = {"Authorization": f"Bearer {token}"}

        # Create organization
        org_data = {
            "name": "Test Organization",
            "slug": "test-org",
            "description": "Test organization description"
        }
        org_response = client.post("/api/v1/organizations/", json=org_data, headers=headers)

        # Test limits endpoint
        response = client.get("/api/v1/billing/limits", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "organizations" in data
        assert len(data["organizations"]) == 1