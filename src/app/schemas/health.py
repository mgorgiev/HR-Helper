from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    database: str
    version: str


class StatusResponse(BaseModel):
    status: str
