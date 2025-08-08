# Synapse-Backend/src/api/endpoints/processing.py

import uuid
from fastapi import APIRouter, status, Request
from src.schemas.job import JobCreate, JobCreated
from src.core.celery_app import celery_app  # Import the celery client

router = APIRouter()

@router.post(
    "/process",
    response_model=JobCreated,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_processing_job(
    request: Request,
    job_in: JobCreate,
):
    """
    Accepts a new processing job, creates an initial record,
    and dispatches it to the worker queue.
    """
    job_id = uuid.uuid4()

    print(f"Received job {job_id} of type {job_in.input_type}")

    # Dispatch the task to the worker via Celery
    celery_app.send_task(
        "src.tasks.cpu_light_tasks.route_input_task",
        args=[str(job_id), job_in.model_dump()],
    )
    
    status_url = str(request.url_for("get_job_status", job_id=job_id))
    return JobCreated(job_id=job_id, status_url=status_url)


@router.get("/status/{job_id}")
async def get_job_status(job_id: uuid.UUID):
    return {"job_id": job_id, "status": "PENDING"}
