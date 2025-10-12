"""API dependencies"""
from fastapi import Header, HTTPException, status
from typing import Optional
from app.core.config import settings


async def verify_api_key(
    x_api_key: Optional[str] = Header(None, alias=settings.API_KEY_HEADER)
) -> str:
    """Verify API key from header"""
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is missing"
        )

    # Add your API key verification logic here
    # For now, accepting any non-empty key
    # In production, validate against stored keys

    return x_api_key
