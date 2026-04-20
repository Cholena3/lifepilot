"""Health check endpoints."""

from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def health_check() -> dict[str, str]:
    """Basic health check endpoint."""
    return {"status": "healthy"}


@router.get("/ready")
async def readiness_check() -> dict[str, str]:
    """Readiness check - verifies dependencies are available."""
    # TODO: Add database and Redis connectivity checks
    return {"status": "ready"}
