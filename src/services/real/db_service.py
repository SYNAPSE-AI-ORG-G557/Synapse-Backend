import uuid
from typing import List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime

from src.schemas.job import JobCreate, JobStatus, JobStateEnum
from src.db.models import Task, TaskResult, User


class RealDatabaseService:
    """A real implementation of the database service using SQLAlchemy."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def _get_or_create_test_user(self) -> User:
        stmt = select(User).where(User.email == "test@example.com")
        result = await self._session.execute(stmt)
        user = result.scalars().first()

        if not user:
            print("Creating a dummy test user for the job...")
            user = User(
                username="testuser",
                email="test@example.com",
                password_hash="dummy_hash",
                # No need to set created_at/updated_at - handled by DB
            )
            self._session.add(user)
            await self._session.commit()
            await self._session.refresh(user)
        return user

    async def create_job(self, job_id: uuid.UUID, job_data: JobCreate) -> JobStatus:
        test_user = await self._get_or_create_test_user()
        
        new_task = Task(
            uuid=job_id,
            user_id=test_user.uuid,
            title=f"Job for input type {job_data.input_type}",
            task_type=job_data.input_type,
            status=JobStateEnum.PENDING.value,
            payload={"input_data": job_data.input_data},
            # Don't set created_at/updated_at - handled by DB server
        )
        self._session.add(new_task)
        await self._session.commit()
        await self._session.refresh(new_task)

        return JobStatus(
            id=new_task.uuid,
            status=JobStateEnum(new_task.status),
            created_at=new_task.created_at,
            updated_at=new_task.updated_at,  # Use the DB-generated value
            history=["Job created"],
            result=None,
        )

    async def get_job_by_id(self, job_id: uuid.UUID) -> Optional[JobStatus]:
        task = await self._session.get(Task, job_id)
        if not task:
            return None

        result_stmt = (
            select(TaskResult)
           .where(TaskResult.task_id == job_id)
           .order_by(TaskResult.created_at.desc())
        )
        task_res = (await self._session.execute(result_stmt)).scalars().first()

        return JobStatus(
            id=task.uuid,
            status=JobStateEnum(task.status),
            created_at=task.created_at,
            updated_at=task.updated_at,  # Use the actual updated_at field
            history=["Job retrieved from database"],
            result=task_res.result if task_res else None,
        )

    async def update_job_status(
        self, job_id: uuid.UUID, status: JobStateEnum, result: Optional[Any] = None
    ) -> JobStatus:
        task = await self._session.get(Task, job_id)
        if not task:
            raise ValueError(f"Job with ID {job_id} not found.")

        # Only update the status - updated_at will be auto-updated by DB
        task.status = status.value
        self._session.add(task)

        if result is not None:
            new_result = TaskResult(
                task_id=job_id,
                result=result,
                success=(status != JobStateEnum.FAILED),
                # created_at handled by DB
            )
            self._session.add(new_result)

        await self._session.commit()
        await self._session.refresh(task)  # Refresh to get updated timestamps
        return await self.get_job_by_id(job_id)

    async def add_job_history_event(
        self, job_id: uuid.UUID, event_description: str
    ) -> List[str]:
        # For now, just log - could implement actual history storage later
        print(f"HISTORY for {job_id}: {event_description}")
        return [event_description]