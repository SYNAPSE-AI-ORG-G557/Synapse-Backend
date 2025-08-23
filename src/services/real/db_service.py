# In src/services/real/db_service.py

import uuid
from datetime import datetime
from typing import List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func # ## FIX: Make sure func is imported for server timestamps

from src.schemas.job import JobCreate, JobStatus, JobStateEnum
from src.db.models import ProcessingJob, User


class RealDatabaseService:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def _get_or_create_test_user(self) -> User:
        # This helper function is fine as is
        stmt = select(User).where(User.email == "test@example.com")
        result = await self._session.execute(stmt)
        user = result.scalars().first()

        if not user:
            user = User(username="testuser", email="test@example.com", password_hash="dummy")
            self._session.add(user)
            await self._session.commit()
            await self._session.refresh(user)
        return user


    async def create_job(self, job_id: uuid.UUID, job_data: JobCreate) -> JobStatus:
        """Creates a new job record in the 'processing_jobs' table."""
        test_user = await self._get_or_create_test_user()
        
        new_job = ProcessingJob(
            uuid=job_id,
            # ## IMPROVEMENT: Assuming you've added user_id to your ProcessingJob model
            user_id=test_user.uuid, 
            job_type=job_data.input_type,
            status=JobStateEnum.PENDING.value,
            # ## FIX: Store input_data directly, not nested in another dict
            input_data=job_data.input_data,
        )
        self._session.add(new_job)
        await self._session.commit()
        await self._session.refresh(new_job)

        return JobStatus(
            id=new_job.uuid,
            status=JobStateEnum(new_job.status),
            created_at=new_job.created_at,
            updated_at=new_job.created_at,
            history=["Job created"],
            result=None,
        )

    # ## FIX: Completed the return type hint
    async def get_job_by_id(self, job_id: uuid.UUID) -> Optional[JobStatus]:
        """Retrieves a job from the 'processing_jobs' table."""
        job = await self._session.get(ProcessingJob, job_id)
        if not job:
            return None

        last_update_time = job.completed_at or job.started_at or job.created_at

        return JobStatus(
            id=job.uuid,
            status=JobStateEnum(job.status),
            created_at=job.created_at,
            updated_at=last_update_time,
            history=["Job retrieved"],
            result=job.result_data,
        )

    async def update_job_status(
        self, job_id: uuid.UUID, status: JobStateEnum, result: Optional[Any] = None
    ) -> JobStatus:
        """Updates the status of a job in the 'processing_jobs' table."""
        job = await self._session.get(ProcessingJob, job_id)
        if not job:
            raise ValueError(f"Job with ID {job_id} not found in processing_jobs table.")

        # Update status
        job.status = status.value

        # Use DB now() for consistent timestamps
        if status == JobStateEnum.PROCESSING and not job.started_at:
            job.started_at = func.now()

        if status in [JobStateEnum.COMPLETED, JobStateEnum.FAILED]:
            job.completed_at = func.now()

        # Store result or error
        if result is not None:
            if status == JobStateEnum.FAILED:
                job.error_message = str(result)
                job.result_data = None
            else:
                job.result_data = result
                job.error_message = None

        self._session.add(job)
        await self._session.commit()

        # --- IMPORTANT FIX ---
        # Explicitly refresh object so no lazy-loading happens
        await self._session.refresh(job)

        # Compute last updated time
        last_update_time = job.completed_at or job.started_at or job.created_at

        # Return safe response
        return JobStatus(
            id=job.uuid,
            status=JobStateEnum(job.status),
            created_at=job.created_at,
            updated_at=last_update_time,
            history=["Job status updated"],
            result=job.result_data,
        )

    async def add_job_history_event(
        self, job_id: uuid.UUID, event_description: str
    ) -> List[str]:
        # This placeholder function is fine as is
        print(f"HISTORY for {job_id}: {event_description}")
        return [event_description]