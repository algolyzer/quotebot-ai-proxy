"""
Middleware Configuration
All middleware setup in one place
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import time
import uuid

from app.config import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


def setup_middleware(app: FastAPI) -> None:
    """
    Configure all middleware for the application

    Args:
        app: FastAPI application instance
    """

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Process-Time"],
    )

    # Compression Middleware
    app.add_middleware(
        GZipMiddleware,
        minimum_size=1000
    )

    # Request ID and Timing Middleware
    @app.middleware("http")
    async def request_id_and_timing_middleware(request: Request, call_next):
        """
        Add unique request ID and measure response time
        """
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Measure time
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate duration
        process_time = time.time() - start_time

        # Add headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{process_time:.3f}"

        # Log slow requests
        if process_time > 2.0:
            logger.warning(
                f"⚠️  Slow request [{request_id}]: "
                f"{request.method} {request.url.path} took {process_time:.2f}s"
            )

        return response
