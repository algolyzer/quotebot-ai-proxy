"""Dify API service"""
import httpx
from typing import Dict, Any, Optional
from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DifyService:
    """Service for Dify API communication"""

    def __init__(self):
        self.base_url = settings.DIFY_API_BASE_URL
        self.api_key = settings.DIFY_API_KEY
        self.timeout = settings.DIFY_REQUEST_TIMEOUT

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for Dify API"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def send_message(
        self,
        query: str,
        user: str,
        conversation_id: Optional[str] = None,
        inputs: Optional[Dict[str, Any]] = None,
        response_mode: str = "blocking"
    ) -> Dict[str, Any]:
        """Send message to Dify"""
        try:
            url = f"{self.base_url}/chat-messages"

            payload = {
                "query": query,
                "user": user,
                "response_mode": response_mode,
                "inputs": inputs or {}
            }

            if conversation_id:
                payload["conversation_id"] = conversation_id

            logger.info(f"→ Sending message to Dify for user: {user}")

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    headers=self._get_headers(),
                    json=payload
                )
                response.raise_for_status()

                result = response.json()
                logger.info(f"✓ Received response from Dify")

                return result

        except httpx.TimeoutException as e:
            logger.error(f"✗ Dify timeout: {str(e)}")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"✗ Dify HTTP error {e.response.status_code}: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"✗ Dify error: {str(e)}")
            raise

    async def get_history(
        self,
        conversation_id: str,
        user: str,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Get conversation history from Dify"""
        try:
            url = f"{self.base_url}/messages"
            params = {
                "conversation_id": conversation_id,
                "user": user,
                "limit": limit
            }

            logger.info(f"→ Fetching history for conversation: {conversation_id}")

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    url,
                    headers=self._get_headers(),
                    params=params
                )
                response.raise_for_status()

                result = response.json()
                logger.info(f"✓ Retrieved {len(result.get('data', []))} messages")

                return result

        except Exception as e:
            logger.error(f"✗ Error fetching history: {str(e)}")
            raise

    async def delete_conversation(
        self,
        conversation_id: str,
        user: str
    ) -> bool:
        """Delete conversation from Dify"""
        try:
            url = f"{self.base_url}/conversations/{conversation_id}"

            logger.info(f"→ Deleting conversation: {conversation_id}")

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.delete(
                    url,
                    headers=self._get_headers(),
                    json={"user": user}
                )
                response.raise_for_status()

                logger.info(f"✓ Deleted conversation: {conversation_id}")
                return True

        except Exception as e:
            logger.error(f"✗ Error deleting conversation: {str(e)}")
            return False

    async def health_check(self) -> bool:
        """Check if Dify API is accessible"""
        try:
            url = f"{self.base_url}/parameters"

            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(
                    url,
                    headers=self._get_headers()
                )
                return response.status_code == 200

        except:
            return False


# Singleton instance
dify_service = DifyService()
