"""
Authentication Utilities
"""
import secrets

from app.config import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class APIKeyService:
    """Service for handling API key authentication"""

    def __init__(self):
        self.api_key = settings.API_KEY

    def verify_api_key(self, api_key: str) -> bool:
        """
        Verify an API key

        Args:
            api_key: The API key to verify

        Returns:
            True if valid, False otherwise
        """
        if not self.api_key:
            logger.warning("No API key configured in settings")
            return False

        # Simple string comparison - in production, you might want to hash these
        is_valid = secrets.compare_digest(api_key, self.api_key)

        if not is_valid:
            logger.warning("Invalid API key attempt")

        return is_valid


# Create singleton instances
api_key_service = APIKeyService()
