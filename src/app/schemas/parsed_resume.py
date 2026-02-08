from pydantic import BaseModel


class WorkExperience(BaseModel):
    company: str
    title: str
    start_date: str | None = None
    end_date: str | None = None
    description: str | None = None


class Education(BaseModel):
    institution: str
    degree: str | None = None
    field: str | None = None
    year: str | None = None


class ParsedResumeData(BaseModel):
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    summary: str | None = None
    skills: list[str] = []
    experience: list[WorkExperience] = []
    education: list[Education] = []
    languages: list[str] = []
    certifications: list[str] = []
