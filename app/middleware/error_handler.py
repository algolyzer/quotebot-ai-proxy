"""Global error handler"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "detail": str(exc) if request.app.debug else "An unexpected error occurred"
        }
    )
