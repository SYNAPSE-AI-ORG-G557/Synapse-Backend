# In: Synapse-Backend/src/services/interfaces/_db.py

import uuid
from abc import ABC, abstractmethod
from src.schemas.job import JobCreate, JobStatus, JobStateEnum

class IDatabaseService(ABC):
    """
    An abstract interface defining the contract for database operations.
    Any class that handles database logic MUST implement these methods.
    """

    @abstractmethod
    async def create_job(self, job_id: uuid.UUID, job_data: JobCreate) -> JobStatus:
        """Creates a new job record in the database."""
        raise NotImplementedError

    @abstractmethod
    async def get_job_by_id(self, job_id: uuid.UUID) -> JobStatus | None:
        """Retrieves a job record by its ID."""
        raise NotImplementedError

    @abstractmethod
    async def update_job_status(self, job_id: uuid.UUID, status: JobStateEnum) -> JobStatus:
        """Updates the status of an existing job."""
        raise NotImplementedError