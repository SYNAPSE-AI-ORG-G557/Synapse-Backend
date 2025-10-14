# src/db/session.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from src.core.config import settings

# --- Asynchronous Setup (for your main FastAPI app) ---
# This part should remain as it is for your async endpoints.
async_engine = create_async_engine(
    str(settings.DATABASE_DSN),
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=settings.DB_POOL_PRE_PING,
    echo=False
)

AsyncSessionFactory = async_sessionmaker(
    async_engine,
    autoflush=False,
    expire_on_commit=False,
    class_=AsyncSession,
)

async def get_db_session() -> AsyncSession:
    """
    Dependency that yields a SQLAlchemy async session.
    Ensures the session is properly closed after use.
    """
    async with AsyncSessionFactory() as session:
        yield session

# --- Synchronous Setup (for Celery Beat endpoint) ---
# Add this entire block to the file.
sync_engine = create_engine(
    str(settings.DATABASE_DSN_SYNC),
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=settings.DB_POOL_PRE_PING
)

SyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine
)

def get_sync_db_session():
    """
    Dependency that yields a SQLAlchemy synchronous session.
    Required for the sqlalchemy-celery-beat endpoint.
    """
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()