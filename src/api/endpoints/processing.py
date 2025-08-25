# Synapse-Backend/src/api/endpoints/processing.py

import uuid
from fastapi import APIRouter, status, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

# Import the schemas we created earlier
from src.schemas.job import JobCreate, JobCreated, JobStatus
# Import the real database service and the session dependency
from src.services.real.db_service import RealDatabaseService
from src.db.session import get_db_session
# Import the celery app for dispatching tasks
from src.core.celery_app import app as celery_app
router = APIRouter()

# --- Dependency Provider ---
# This function provides an instance of our database service to the endpoints.
def get_database_service(session: AsyncSession = Depends(get_db_session)) -> RealDatabaseService:
    """Dependency provider for the RealDatabaseService."""
    return RealDatabaseService(session)


@router.post(
    "/process",
    response_model=JobCreated,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit a new processing job",
)
async def create_processing_job(
    request: Request,
    job_in: JobCreate,
    db_service: RealDatabaseService = Depends(get_database_service),
):
    """
    Accepts a new processing job, creates an initial record in the database,
    and dispatches the first task to the worker queue.
    """
    job_id = uuid.uuid4()

    # Step 1: Use the injected database service to create the initial job record.
    await db_service.create_job(job_id=job_id, job_data=job_in)

    # Step 2: Dispatch the first task in the processing chain to the Celery worker.
    celery_app.send_task(
        "route_input_task",
        args=[str(job_id), job_in.model_dump()],
    )

    # Step 3: Return a 202 Accepted response with the job ID and a URL to check the status.
    status_url = str(request.url_for("get_job_status", job_id=job_id))
    return JobCreated(job_id=job_id, status_url=status_url)


@router.get(
    "/jobs/status/{job_id}",  # Using a more standard RESTful path
    response_model=JobStatus,
    summary="Get the status of a processing job",
)
async def get_job_status(
    job_id: uuid.UUID,
    db_service: RealDatabaseService = Depends(get_database_service),
):
    """
    Retrieves and returns the current status of a job by its ID.
    """
    job = await db_service.get_job_by_id(job_id)
    if not job:
        # Raise a proper HTTP 404 error if the job is not found.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found.",
        )
    return job