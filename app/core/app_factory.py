"""
Application Factory
Creates and configures the FastAPI application
"""

from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.config import settings
from app.core.middleware import setup_middleware
from app.core.exception_handlers import setup_exception_handlers
from app.api.v1 import conversations, health
from app.services.database import database, redis_client
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle manager
    Handles startup and shutdown events
    """
    # 🚀 Startup
    logger.info("🚀 Starting Quotebot AI Proxy...")

    # Connect to PostgreSQL
    try:
        await database.connect()
        logger.info("✅ PostgreSQL connected")
    except Exception as e:
        logger.error(f"❌ PostgreSQL connection failed: {e}")
        raise

    # Connect to Redis
    try:
        await redis_client.connect()
        await redis_client.ping()
        logger.info("✅ Redis connected")
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
        raise

    logger.info(f"🎯 Environment: {settings.ENVIRONMENT}")
    logger.info(f"🔗 Dify API: {settings.DIFY_API_URL}")
    logger.info("✨ Application ready!")

    yield

    # 🛑 Shutdown
    logger.info("🛑 Shutting down gracefully...")
    await database.disconnect()
    await redis_client.close()
    logger.info("✅ Cleanup complete")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application

    Returns:
        FastAPI: Configured application instance
    """

    # Create FastAPI app
    app = FastAPI(
        title="Quotebot AI Proxy",
        description="High-performance proxy service between tablazat.hu and Dify AI",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    )

    # Setup middleware (CORS, compression, logging, etc.)
    setup_middleware(app)

    # Setup exception handlers
    setup_exception_handlers(app)

    # Register API routes
    app.include_router(
        conversations.router,
        prefix="/api/v1/conversations",
        tags=["Conversations"]
    )

    app.include_router(
        health.router,
        tags=["Health & Monitoring"]
    )

    # Root endpoint
    @app.get("/", tags=["Root"])
    async def root():
        """Root endpoint - API information"""
        return {
            "service": "Quotebot AI Proxy",
            "version": "1.0.0",
            "status": "running",
            "docs": f"/docs" if settings.ENVIRONMENT != "production" else None,
            "health": "/health"
        }

    return app
