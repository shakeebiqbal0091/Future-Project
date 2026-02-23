from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from typing import Generator
from contextlib import contextmanager
from app.core.config import settings
import redis
from redis import Redis

# Database setup
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30
)

# Redis setup
redis_client = Redis.from_url(settings.REDIS_URL)

# SQLAlchemy session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False
)

# Base class for models
Base = declarative_base()

@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def create_all_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)

def drop_all_tables():
    """Drop all database tables"""
    Base.metadata.drop_all(bind=engine)