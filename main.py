"""Quotebot AI Proxy - Main Application"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi.errors import RateLimitExceeded
import time

from app.core.config import settings
from app.utils.logger import setup_logging, get_logger
from app.api.v1 import api_router
from app.middleware.rate_limit import limiter, rate_limit_handler
from app.middleware.error_handler import global_exception_handler
from app import __version__

# Setup logging
setup_logging()
logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Quotebot AI Proxy",
    description="Production-ready FastAPI backend for Dify integration with Quotebot",
    version=__version__,
    debug=settings.APP_DEBUG,
    docs_url=f"/api/{settings.API_VERSION}/docs",
    redoc_url=f"/api/{settings.API_VERSION}/redoc",
    openapi_url=f"/api/{settings.API_VERSION}/openapi.json"
)

# Add rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trusted host middleware (security)
if not settings.APP_DEBUG:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]  # Configure in production
    )

# Add global exception handler
app.add_exception_handler(Exception, global_exception_handler)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests"""
    start_time = time.time()

    logger.info(f"→ {request.method} {request.url.path}")

    response = await call_next(request)

    duration = time.time() - start_time
    logger.info(
        f"✓ {request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Duration: {duration:.3f}s"
    )

    return response


# Include API routes
app.include_router(api_router, prefix=f"/api/{settings.API_VERSION}")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Quotebot AI Proxy",
        "version": __version__,
        "status": "running",
        "docs": f"/api/{settings.API_VERSION}/docs"
    }


# Startup event
@app.on_event("startup")
async def startup_event():
    """Application startup"""
    logger.info("="*70)
    logger.info("🚀 Starting Quotebot AI Proxy")
    logger.info(f"Version: {__version__}")
    logger.info(f"Environment: {'DEBUG' if settings.APP_DEBUG else 'PRODUCTION'}")
    logger.info(f"Dify API: {settings.DIFY_API_BASE_URL}")
    logger.info(f"Redis: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
    logger.info("="*70)


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown"""
    logger.info("👋 Shutting down Quotebot AI Proxy")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.APP_DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
