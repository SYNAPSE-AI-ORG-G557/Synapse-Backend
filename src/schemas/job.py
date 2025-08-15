
# Synapse-Backend/src/schemas/job.py

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, List, Literal
from pydantic import BaseModel, Field

class JobStateEnum(str, Enum):
    """Enumeration for the possible states of a job."""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    AWAITING_CLARIFICATION = "AWAITING_CLARIFICATION"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class JobCreate(BaseModel):
    """Schema for creating a new job. This is the input to the API."""
    input_type: Literal["text", "image", "audio"]
    input_data: str  # For files, this will be a base64 encoded string

class JobCreated(BaseModel):
    """Schema for the response after a job is successfully created."""
    job_id: uuid.UUID
    status_url: str

class JobStatus(BaseModel):
    """Schema for representing the full status of a job."""
    id: uuid.UUID
    status: JobStateEnum
    created_at: datetime
    updated_at: datetime
    history: List[str] = Field(default_factory=list)
    result: Any | None = None