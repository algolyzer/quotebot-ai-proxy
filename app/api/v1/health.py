"""
Health & Monitoring Endpoints
System health checks and metrics
"""

from fastapi import APIRouter
import time

from app.services.database import database, redis_client
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter()


@router.get(
    "/health",
    summary="Health check",
    description="Check service health and dependencies"
)
async def health_check():
    """
    **Health Check**

    Checks the health of:
    - Redis connection
    - PostgreSQL connection
    - Overall application status

    Used by load balancers and monitoring systems.
    """
    redis_status = "unknown"
    db_status = "unknown"

    # Check Redis
    try:
        await redis_client.ping()
        redis_status = "healthy"
    except Exception as e:
        redis_status = "unhealthy"
        logger.error(f"Redis health check failed: {e}")

    # Check Database
    try:
        await database.fetch_one("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        db_status = "unhealthy"
        logger.error(f"Database health check failed: {e}")

    # Overall status
    overall_status = (
        "healthy" if redis_status == "healthy" and db_status == "healthy"
        else "degraded"
    )

    return {
        "status": overall_status,
        "timestamp": time.time(),
        "services": {
            "redis": redis_status,
            "database": db_status,
            "dify": "unknown"  # We don't check Dify to avoid unnecessary API calls
        },
        "version": "1.0.0"
    }


@router.get(
    "/ready",
    summary="Readiness probe",
    description="Check if service is ready to accept traffic"
)
async def readiness_check():
    """
    **Readiness Probe**

    Indicates whether the service is ready to handle requests.
    Used by Kubernetes and other orchestration systems.
    """
    return {
        "ready": True,
        "timestamp": time.time()
    }


@router.get(
    "/metrics",
    summary="Basic metrics",
    description="Get basic application metrics"
)
async def get_metrics():
    """
    **Metrics Endpoint**

    Returns basic application metrics.
    In production, use Prometheus client for detailed metrics.
    """
    return {
        "service": "quotebot-ai-proxy",
        "version": "0.0.1",
        "uptime_seconds": time.time(),
        "timestamp": time.time()
    }
