import redis.asyncio as redis
from src.core.config import settings

# Create a connection pool for the Redis client.
# This is a best practice as it allows for efficient reuse of connections
# without the overhead of establishing a new connection for every request.
redis_pool = redis.ConnectionPool.from_url(
    str(settings.REDIS_URL),
    max_connections=10,
    decode_responses=True  # Decode responses from bytes to UTF-8 strings automatically
)

def get_redis_client() -> redis.Redis:
    """
    Returns a Redis client instance from the connection pool.
    This function can be used as a dependency in FastAPI.
    """
    return redis.Redis(connection_pool=redis_pool)

# A single client instance can also be created for use in non-request scopes,
# like the background Pub/Sub listener we will create later.
redis_client = get_redis_client()
