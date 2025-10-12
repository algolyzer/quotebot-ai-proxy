"""
Dify API Service
Handles all communication with the Dify platform
"""

import httpx
from typing import Dict, Any, Optional
from app.config import settings
from app.models.schemas import DifyChatRequest, DifyMessageResponse
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class DifyService:
    """Service for interacting with Dify API"""

    def __init__(self):
        self.api_url = settings.DIFY_API_URL
        self.api_key = settings.DIFY_API_KEY
        self.timeout = settings.DIFY_TIMEOUT

        # Create a persistent HTTP client with connection pooling
        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            limits=httpx.Limits(
                max_keepalive_connections=20,
                max_connections=100,
                keepalive_expiry=30.0
            )
        )

    def _get_headers(self) -> Dict[str, str]:
        """Get authorization headers for Dify API"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def create_conversation(
            self,
            user_id: str,
            initial_inputs: Dict[str, Any],
            first_message: str = "Hello, I'm interested in your products"
    ) -> Dict[str, Any]:
        """
        Create a new conversation in Dify

        Args:
            user_id: Session ID from tablazat.hu
            initial_inputs: Context data to pass to AI
            first_message: Initial message to start conversation

        Returns:
            Dify response with conversation_id and first AI response
        """
        payload = {
            "inputs": initial_inputs,
            "query": first_message,
            "response_mode": "blocking",
            "user": user_id
        }

        logger.info(f"Creating Dify conversation for user {user_id}")

        try:
            response = await self.client.post(
                f"{self.api_url}/chat-messages",
                headers=self._get_headers(),
                json=payload
            )

            response.raise_for_status()
            data = response.json()

            logger.info(
                f"Dify conversation created: {data.get('conversation_id')} "
                f"for user {user_id}"
            )

            return data

        except httpx.HTTPError as e:
            logger.error(f"Dify API error during conversation creation: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating Dify conversation: {str(e)}")
            raise

    async def send_message(
            self,
            conversation_id: str,
            user_id: str,
            message: str,
            additional_inputs: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send a message in an existing Dify conversation

        Args:
            conversation_id: Dify conversation ID
            user_id: Session ID
            message: User's message
            additional_inputs: Optional additional context

        Returns:
            Dify response with AI's answer
        """
        payload = {
            "inputs": additional_inputs or {},
            "query": message,
            "response_mode": "blocking",
            "conversation_id": conversation_id,
            "user": user_id
        }

        logger.debug(
            f"Sending message to Dify conversation {conversation_id}: "
            f"{message[:50]}..."
        )

        try:
            response = await self.client.post(
                f"{self.api_url}/chat-messages",
                headers=self._get_headers(),
                json=payload
            )

            response.raise_for_status()
            data = response.json()

            logger.debug(
                f"Received Dify response for conversation {conversation_id}"
            )

            return data

        except httpx.HTTPError as e:
            logger.error(
                f"Dify API error sending message to {conversation_id}: {str(e)}"
            )
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error sending message to Dify: {str(e)}"
            )
            raise

    async def get_conversation_history(
            self,
            conversation_id: str,
            user_id: str,
            limit: int = 20
    ) -> Dict[str, Any]:
        """
        Get conversation history from Dify

        Args:
            conversation_id: Dify conversation ID
            user_id: Session ID
            limit: Number of messages to retrieve

        Returns:
            Conversation history from Dify
        """
        try:
            response = await self.client.get(
                f"{self.api_url}/messages",
                headers=self._get_headers(),
                params={
                    "conversation_id": conversation_id,
                    "user": user_id,
                    "limit": limit
                }
            )

            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(
                f"Dify API error getting history for {conversation_id}: {str(e)}"
            )
            raise

    async def get_conversation_variables(
            self,
            conversation_id: str,
            user_id: str
    ) -> Dict[str, Any]:
        """
        Get conversation variables from Dify
        These contain structured data collected during the conversation

        Args:
            conversation_id: Dify conversation ID
            user_id: Session ID

        Returns:
            Conversation variables
        """
        try:
            response = await self.client.get(
                f"{self.api_url}/conversations/{conversation_id}/variables",
                headers=self._get_headers(),
                params={"user": user_id}
            )

            response.raise_for_status()
            data = response.json()

            logger.info(
                f"Retrieved {len(data.get('data', []))} variables "
                f"for conversation {conversation_id}"
            )

            return data

        except httpx.HTTPError as e:
            logger.error(
                f"Dify API error getting variables for {conversation_id}: {str(e)}"
            )
            # Return empty if variables endpoint fails
            return {"data": [], "has_more": False}

    def extract_structured_data(
            self,
            dify_response: Dict[str, Any],
            variables: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Extract structured data from Dify response

        This can come from:
        1. metadata field in the response
        2. conversation variables
        3. parsing the answer text (if formatted as JSON)

        Args:
            dify_response: Response from Dify
            variables: Optional conversation variables

        Returns:
            Extracted structured data or None
        """
        # Method 1: Check metadata
        metadata = dify_response.get("metadata", {})
        if metadata.get("structured_output"):
            logger.info("Found structured data in response metadata")
            return metadata["structured_output"]

        # Method 2: Check conversation variables
        if variables and variables.get("data"):
            structured = {}
            for var in variables["data"]:
                structured[var["name"]] = var["value"]

            if structured:
                logger.info(f"Extracted {len(structured)} variables from conversation")
                return structured

        # Method 3: Parse JSON from answer (if Dify outputs JSON in the response)
        answer = dify_response.get("answer", "")
        if "```json" in answer:
            import json
            try:
                json_start = answer.find("```json") + 7
                json_end = answer.find("```", json_start)
                json_str = answer[json_start:json_end].strip()
                data = json.loads(json_str)
                logger.info("Parsed structured data from JSON block in answer")
                return data
            except Exception as e:
                logger.warning(f"Failed to parse JSON from answer: {e}")

        return None

    def is_conversation_complete(
            self,
            dify_response: Dict[str, Any],
            variables: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Check if the conversation has reached completion

        Completion indicators:
        1. Specific flag in metadata
        2. All required fields collected in variables
        3. Completion keywords in the AI response

        Args:
            dify_response: Response from Dify
            variables: Optional conversation variables

        Returns:
            True if conversation is complete
        """
        # Method 1: Check metadata flag
        metadata = dify_response.get("metadata", {})
        if metadata.get("conversation_complete"):
            logger.info("Conversation marked complete by Dify metadata")
            return True

        # Method 2: Check for completion keywords in answer
        answer = dify_response.get("answer", "").lower()
        for keyword in settings.COMPLETION_KEYWORDS:
            if keyword.lower() in answer:
                logger.info(f"Completion keyword found: '{keyword}'")
                return True

        # Method 3: Check if all required variables are collected
        if variables and variables.get("data"):
            collected_vars = {var["name"] for var in variables["data"]}
            required_vars = set(settings.REQUIRED_FIELDS)

            if required_vars.issubset(collected_vars):
                # Check that they all have values
                all_have_values = all(
                    var["value"] for var in variables["data"]
                    if var["name"] in settings.REQUIRED_FIELDS
                )

                if all_have_values:
                    logger.info("All required variables collected")
                    return True

        return False

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


# Create singleton instance
dify_service = DifyService()
