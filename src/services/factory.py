# Synapse-Worker/src/services/factory.py

from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession

# Import the session factory and redis client from the worker's own core/db modules
from src.db.session import AsyncSessionFactory
from src.core.redis_client import get_redis_client

# Import the real service implementations
from src.services.real.db_service import RealDatabaseService
from src.services.real.redis_service import RealRedisService


@asynccontextmanager
async def db_service_provider():
    """A context manager to provide a database service to a Celery task."""
    session: AsyncSession = AsyncSessionFactory()
    try:
        yield RealDatabaseService(session)
    finally:
        await session.close()

@asynccontextmanager
async def redis_service_provider():
    """A context manager to provide a Redis service to a Celery task."""
    # The redis client's lifecycle is managed by its connection pool,
    # so we don't need to manually close it here.
    yield RealRedisService(get_redis_client())