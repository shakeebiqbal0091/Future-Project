import pytest
from app.main import app
from app.core.database import engine
from app.models.models import Base

@pytest.fixture(scope="session")
def test_app():
    """Create a test FastAPI app instance."""
    return app

@pytest.fixture(scope="session")
def test_client(test_app):
    """Create a test client for the FastAPI app."""
    from fastapi.testclient import TestClient
    return TestClient(test_app)

@pytest.fixture(scope="session")
def test_db():
    """Create a test database engine."""
    from sqlalchemy import create_engine
    test_engine = create_engine("sqlite:///:memory:")

    # Create all tables
    Base.metadata.create_all(bind=test_engine)

    yield test_engine

    # Drop all tables
    Base.metadata.drop_all(bind=test_engine)

@pytest.fixture
async def db_session(test_db):
    """Create a database session for testing."""
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

    # Create async engine
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    # Create all tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    SessionLocal = sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False
    )

    async with SessionLocal() as session:
        yield session

        # Rollback any changes
        await session.rollback()

@pytest.fixture
def auth_token():
    """Generate a test authentication token."""
    from app.core.security.auth_handler import AuthHandler
    from app.models.models import User

    # Create a test user
    test_user = User(
        id="test-user-id",
        username="testuser",
        email="test@example.com",
        hashed_password="test-password-hash",
        is_active=True
    )

    # Create token
    token = AuthHandler.create_access_token(test_user.username)

    return token

@pytest.fixture
def test_user():
    """Create a test user."""
    from app.models.models import User

    return User(
        id="test-user-id",
        username="testuser",
        email="test@example.com",
        hashed_password="test-password-hash",
        is_active=True
    )

@pytest.fixture
async def test_user_in_db(db_session, test_user):
    """Add test user to database."""
    await db_session.add(test_user)
    await db_session.commit()
    await db_session.refresh(test_user)
    return test_user

@pytest.fixture
def test_agent_data():
    """Test agent data for creating agents."""
    return {
        "name": "Test Agent",
        "role": "test agent",
        "instructions": "This is a test agent",
        "model": "claude",
        "tools": ["calculator"],
        "config": {"param": "value"}
    }

@pytest.fixture
async def test_agent(db_session, test_user, test_agent_data):
    """Create a test agent."""
    from app.models.models import Agent
    from app.models.models import StatusEnum

    test_agent = Agent(
        organization_id=test_user.id,
        name=test_agent_data["name"],
        role=test_agent_data["role"],
        instructions=test_agent_data["instructions"],
        model=test_agent_data["model"],
        tools=test_agent_data["tools"],
        config=test_agent_data["config"],
        status=StatusEnum.active,
        version=1,
        created_by=test_user.id
    )

    await db_session.add(test_agent)
    await db_session.commit()
    await db_session.refresh(test_agent)

    return test_agent

@pytest.fixture
async def test_agent_version(db_session, test_agent):
    """Create a test agent version."""
    from app.models.models import AgentVersion

    test_version = AgentVersion(
        agent_id=test_agent.id,
        version=2,
        config=test_agent.config,
        deployed_by=test_agent.created_by
    )

    await db_session.add(test_version)
    await db_session.commit()
    await db_session.refresh(test_version)

    return test_version