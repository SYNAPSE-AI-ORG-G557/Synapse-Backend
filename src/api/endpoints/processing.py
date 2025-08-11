import uuid
from fastapi import APIRouter, status, Request, Depends
from src.schemas.job import JobCreate, JobCreated
from src.core.celery_app import celery_app
from src.services.dependencies import get_db_service
from src.services.interfaces._db import IDatabaseService

router = APIRouter()

@router.post(
    "/process",
    response_model=JobCreated,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_processing_job(
    request: Request,
    job_in: JobCreate,
    db_service: IDatabaseService = Depends(get_db_service)
):
    job_id = uuid.uuid4()

    # Create job record in DB
    await db_service.create_job(job_id=job_id, job_data=job_in)

    # Dispatch Celery task
    celery_app.send_task(
        "src.tasks.cpu_light_tasks.route_input_task",
        args=[str(job_id), job_in.model_dump()],
    )

    status_url = str(request.url_for("get_job_status", job_id=job_id))
    return JobCreated(job_id=job_id, status_url=status_url)

@router.get("/status/{job_id}")
async def get_job_status(
    job_id: uuid.UUID,
    db_service: IDatabaseService = Depends(get_db_service)
):
    job = await db_service.get_job_by_id(job_id)
    if not job:
        return {"error": "Job not found"}
    return job
