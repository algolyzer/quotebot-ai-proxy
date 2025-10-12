"""
Exception Handlers
Centralized error handling
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.utils.logger import setup_logger

logger = setup_logger(__name__)


def setup_exception_handlers(app: FastAPI) -> None:
    """
    Configure exception handlers for the application

    Args:
        app: FastAPI application instance
    """

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Handle all uncaught exceptions"""
        request_id = getattr(request.state, "request_id", "unknown")

        logger.error(
            f"❌ Unhandled exception [Request ID: {request_id}]: {str(exc)}",
            exc_info=True
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "internal_server_error",
                "message": "An unexpected error occurred",
                "request_id": request_id
            }
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle validation errors"""
        request_id = getattr(request.state, "request_id", "unknown")

        logger.warning(
            f"⚠️  Validation error [Request ID: {request_id}]: {exc.errors()}"
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "validation_error",
                "message": "Invalid request data",
                "details": exc.errors(),
                "request_id": request_id
            }
        )
