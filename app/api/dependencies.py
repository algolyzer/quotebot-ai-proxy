"""
Authentication Dependencies
FastAPI dependencies for API key validation
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.utils.auth import api_key_service
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

# Security schemes
api_key_scheme = HTTPBearer(
    scheme_name="API Key",
    description="API Key for starting conversations"
)


async def verify_api_key(
        credentials: HTTPAuthorizationCredentials = Depends(api_key_scheme)
) -> str:
    """
    Verify API key from Authorization header

    Args:
        credentials: Bearer token from header

    Returns:
        The API key if valid

    Raises:
        HTTPException: If API key is invalid
    """
    api_key = credentials.credentials

    if not api_key_service.verify_api_key(api_key):
        logger.warning("Invalid API key attempt")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return api_key
