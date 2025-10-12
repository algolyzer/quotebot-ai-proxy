"""Rate limiting middleware"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[
        f"{settings.RATE_LIMIT_PER_MINUTE}/minute",
        f"{settings.RATE_LIMIT_PER_HOUR}/hour"
    ]
)


async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """Handle rate limit exceeded"""
    logger.warning(f"Rate limit exceeded for {get_remote_address(request)}")
    return Response(
        content="Rate limit exceeded. Please try again later.",
        status_code=429
    )
