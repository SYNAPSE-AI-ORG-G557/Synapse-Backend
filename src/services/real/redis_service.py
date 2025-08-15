import uuid
import json
from typing import Optional

import redis.asyncio as redis
from src.services.interfaces._redis import IRedisService, IRedisLock
from src.schemas.websocket import WSClarificationRequest


class RedisLockWrapper(IRedisLock):
    """Wraps a redis.asyncio.Lock to implement the IRedisLock interface."""

    def __init__(self, lock: redis.lock.Lock):
        self._lock = lock

    async def __aenter__(self) -> "IRedisLock":
        await self._lock.acquire()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional["TracebackType"],
    ) -> None:
        await self._lock.release()


class RealRedisService(IRedisService):
    """
    A real implementation of the Redis service for state management,
    locking, and pub/sub notifications.
    """

    def __init__(self, client: redis.Redis):
        self._client = client

    async def set_job_state(self, job_id: uuid.UUID, state_data: dict):
        """Stores the volatile state of a job in a Redis HASH."""
        stringified_data = {k: json.dumps(v) for k, v in state_data.items()}
        key = f"job:{job_id}:state"
        await self._client.hset(key, mapping=stringified_data)

    async def get_job_state(self, job_id: uuid.UUID) -> Optional[dict]:
        """Retrieves the state of a job from Redis."""
        key = f"job:{job_id}:state"
        data = await self._client.hgetall(key)
        if data:
            # Deserialize JSON strings back to original types
            return {k: json.loads(v) for k, v in data.items()}
        return None

    def acquire_job_lock(self, job_id: uuid.UUID, timeout: int = 60) -> IRedisLock:
        """Acquires a distributed lock for a specific job_id."""
        lock_key = f"job:{job_id}:lock"
        lock = self._client.lock(lock_key, timeout=timeout, blocking_timeout=5)
        return RedisLockWrapper(lock)

    async def publish_job_update(self, job_id: uuid.UUID, message: dict):
        """Publishes a job update message to the 'job-updates' channel."""
        channel = "job-updates"
        payload = {"job_id": str(job_id), **message}
        await self._client.publish(channel, json.dumps(payload))

    async def store_clarification_request(
        self, job_id: uuid.UUID, request: WSClarificationRequest
    ):
        """Persists the clarification question being asked to the user."""
        key = f"job:{job_id}:clarification"
        await self._client.set(key, request.model_dump_json(), ex=3600 * 24)

    async def get_clarification_request(
        self, job_id: uuid.UUID
    ) -> Optional[WSClarificationRequest]:
        """Retrieves a pending clarification request."""
        key = f"job:{job_id}:clarification"
        data = await self._client.get(key)
        if data:
            return WSClarificationRequest.model_validate_json(data)
        return None
