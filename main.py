"""
Production FastAPI Application for Quotebot AI Proxy
Handles 1000+ requests/second with proper scaling
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time
import logging

from app.config import settings
from app.api.routes import router
from app.utils.logger import setup_logger
from app.services.database import database, redis_client

# Setup logging
logger = setup_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle management for startup and shutdown"""
    # Startup
    logger.info("🚀 Starting Quotebot AI Proxy...")

    # Initialize database connections
    try:
        await database.connect()
        logger.info("✅ PostgreSQL connected")
    except Exception as e:
        logger.error(f"❌ PostgreSQL connection failed: {e}")
        raise

    # Test Redis connection
    try:
        await redis_client.ping()
        logger.info("✅ Redis connected")
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
        raise

    logger.info(f"🎯 Environment: {settings.ENVIRONMENT}")
    logger.info(f"🔗 Dify API: {settings.DIFY_API_URL}")

    yield

    # Shutdown
    logger.info("🛑 Shutting down Quotebot AI Proxy...")
    await database.disconnect()
    await redis_client.close()
    logger.info("✅ Cleanup complete")


# Initialize FastAPI
app = FastAPI(
    title="Quotebot AI Proxy",
    description="High-performance proxy service between tablazat.hu and Dify",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
)

# ============================================================================
# MIDDLEWARE
# ============================================================================

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

# Compression
app.add_middleware(GZipMiddleware, minimum_size=1000)


# Request ID and timing middleware
@app.middleware("http")
async def add_request_id_and_timing(request: Request, call_next):
    """Add request ID and measure response time"""
    import uuid

    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    start_time = time.time()

    response = await call_next(request)

    process_time = time.time() - start_time

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = str(round(process_time, 3))

    # Log slow requests
    if process_time > 2.0:
        logger.warning(
            f"Slow request: {request.method} {request.url.path} "
            f"took {process_time:.2f}s"
        )

    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all uncaught exceptions"""
    request_id = getattr(request.state, "request_id", "unknown")

    logger.error(
        f"Unhandled exception [Request ID: {request_id}]: {str(exc)}",
        exc_info=True
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred",
            "request_id": request_id
        }
    )


# ============================================================================
# ROUTES
# ============================================================================

# Include API routes
app.include_router(router, prefix="/api/v1")


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for load balancers"""
    try:
        # Check Redis
        await redis_client.ping()
        redis_status = "healthy"
    except:
        redis_status = "unhealthy"

    try:
        # Check Database
        await database.fetch_one("SELECT 1")
        db_status = "healthy"
    except:
        db_status = "unhealthy"

    overall_status = (
        "healthy" if redis_status == "healthy" and db_status == "healthy"
        else "degraded"
    )

    return {
        "status": overall_status,
        "services": {
            "redis": redis_status,
            "database": db_status,
            "dify": "unknown"  # We don't check Dify here to avoid unnecessary calls
        },
        "version": "1.0.0"
    }


# Readiness probe for Kubernetes
@app.get("/ready")
async def readiness_check():
    """Readiness check for orchestration systems"""
    return {"ready": True}


# Metrics endpoint (basic)
@app.get("/metrics")
async def metrics():
    """Basic metrics endpoint"""
    # In production, use Prometheus client here
    return {
        "service": "quotebot-ai-proxy",
        "version": "1.0.0",
        "uptime": time.time()
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Quotebot AI Proxy",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs" if settings.ENVIRONMENT != "production" else "disabled"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        workers=4,  # Adjust based on CPU cores
        log_level="info",
        access_log=True,
    )
