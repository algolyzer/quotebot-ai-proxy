"""
Quotebot AI Proxy - Main Application Entry Point
Clean, minimal, and organized
"""

from app.core.app_factory import create_app

# Create the FastAPI application
app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
