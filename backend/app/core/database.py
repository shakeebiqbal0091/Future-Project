from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, declarative_base as sa_declarative_base
from sqlalchemy.pool import QueuePool
from app.core.config import settings
from app.models.models import Base as ModelsBase

# Create the database engine with connection pooling
engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql", "postgresql+asyncpg"),
    echo=True,  # Set to False in production
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
    pool_pre_ping=True
)

# Create a configured "Session" class
SessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Base for all models
Base = sa_declarative_base(cls=ModelsBase)