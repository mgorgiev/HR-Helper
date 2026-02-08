from fastapi import APIRouter

from app.api.v1 import candidates, health, jobs, matching, resumes

api_v1_router = APIRouter()
api_v1_router.include_router(health.router)
api_v1_router.include_router(candidates.router)
api_v1_router.include_router(jobs.router)
api_v1_router.include_router(resumes.router)
api_v1_router.include_router(matching.router)
