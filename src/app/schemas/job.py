import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class EmploymentType(StrEnum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"


class JobCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    department: str | None = Field(None, max_length=100)
    description: str | None = None
    requirements: str | None = None
    location: str | None = Field(None, max_length=200)
    employment_type: EmploymentType = EmploymentType.FULL_TIME
    is_active: bool = True


class JobUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    department: str | None = Field(None, max_length=100)
    description: str | None = None
    requirements: str | None = None
    location: str | None = Field(None, max_length=200)
    employment_type: EmploymentType | None = None
    is_active: bool | None = None


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    department: str | None
    description: str | None
    requirements: str | None
    location: str | None
    employment_type: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
