"""Health check endpoint"""
from fastapi import APIRouter
from datetime import datetime
from app.models.schemas import HealthResponse
from app.core.redis_client import redis_client
from app.services.dify_service import dify_service
from app import __version__

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint

    Returns the health status of the application and its dependencies
    """
    # Check Redis
    redis_ok = redis_client.exists("health_check")
    redis_client.set("health_check", "ok", ttl=60)

    # Check Dify
    dify_ok = await dify_service.health_check()

    status = "healthy" if (redis_ok and dify_ok) else "degraded"

    return HealthResponse(
        status=status,
        timestamp=datetime.utcnow(),
        version=__version__,
        redis_connected=redis_ok,
        dify_accessible=dify_ok
    )
