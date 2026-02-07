import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class ExtractionStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class ResumeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_id: uuid.UUID
    original_filename: str
    stored_filename: str
    file_path: str
    content_type: str
    file_size_bytes: int
    extracted_text: str | None
    extraction_status: str
    extraction_error: str | None
    created_at: datetime
    updated_at: datetime


class ResumeTextResponse(BaseModel):
    id: uuid.UUID
    extracted_text: str | None
    extraction_status: str
