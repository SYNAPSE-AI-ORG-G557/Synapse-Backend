import uuid
from fastapi import APIRouter, status, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.schemas.job import JobCreate, JobCreated, JobStatus
from src.services.real.db_service import RealDatabaseService
from src.db.session import get_db_session
from src.core.celery_app import app as celery_app

router = APIRouter()


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

    # Step 1: create initial job record
    await db_service.create_job(job_id=job_id, job_data=job_in)

    # Step 2: prepare payload and dispatch Celery task
    job_dict = job_in.model_dump(exclude={"user_id"})
    user_id = str(job_in.user_id)

    celery_app.send_task(
        "route_input_task",
        args=[str(job_id), user_id, job_dict],
    )

    # Step 3: return status URL
    status_url = str(request.url_for("get_job_status", job_id=job_id))
    return JobCreated(job_id=job_id, status_url=status_url)


@router.get(
    "/jobs/status/{job_id}",
    response_model=JobStatus,
    summary="Get the status of a processing job",
)
async def get_job_status(
    job_id: uuid.UUID,
    db_service: RealDatabaseService = Depends(get_database_service),
):
    """Retrieve the current status of a job."""
    job = await db_service.get_job_by_id(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found.",
        )
    return job
