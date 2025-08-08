# In: Synapse-Backend/src/schemas/job.py

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, List, Literal
from pydantic import BaseModel, Field

class JobStateEnum(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    AWAITING_CLARIFICATION = "AWAITING_CLARIFICATION"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

# Schema for creating a new job (from frontend)
class JobCreate(BaseModel):
    input_type: Literal["text", "image", "audio"]
    input_data: str  # For files, this will be base64 encoded

# Schema for the response after creating a job
class JobCreated(BaseModel):
    job_id: uuid.UUID
    status_url: str

# Schema for checking the status of a job
class JobStatus(BaseModel):
    id: uuid.UUID
    status: JobStateEnum
    created_at: datetime
    updated_at: datetime
    history: List[str] = Field(default_factory=list)
    result: Any | None = None
