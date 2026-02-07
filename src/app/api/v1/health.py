from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    settings = get_settings()
    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    healthy = db_status == "connected"
    return {
        "status": "healthy" if healthy else "unhealthy",
        "database": db_status,
        "version": settings.app_version,
    }


@router.get("/status")
async def liveness() -> dict[str, str]:
    return {"status": "ok"}
