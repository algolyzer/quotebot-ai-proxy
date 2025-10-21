"""
Callback Service
Sends final structured data to tablazat.hu with retry logic
Updated to include new metadata fields
"""

import httpx
from typing import Dict, Any
from datetime import datetime
import asyncio

from app.config import settings
from app.models.schemas import (
    FinalOutput, CustomerInfo, ProductRequest,
    FinalOutputMetadata, CompanyDetails
)
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class CallbackService:
    """Service for sending callbacks to tablazat.hu"""

    def __init__(self):
        self.callback_url = settings.TABLAZAT_CALLBACK_URL
        self.timeout = settings.TABLAZAT_CALLBACK_TIMEOUT
        self.max_retries = settings.TABLAZAT_CALLBACK_MAX_RETRIES

        # Create HTTP client
        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            limits=httpx.Limits(max_keepalive_connections=10)
        )

    async def send_final_output(
            self,
            conversation_id: str,
            conversation_data: Dict[str, Any],
            structured_data: Dict[str, Any]
    ):
        """
        Send final structured data to tablazat.hu

        This is called when the conversation is complete and all
        required information has been collected.

        Args:
            conversation_id: Our conversation ID
            conversation_data: Conversation record from storage
            structured_data: Extracted structured data from Dify
        """
        logger.info(
            f"Preparing final output for conversation {conversation_id}"
        )

        # Extract initial context
        initial_context = conversation_data.get("initial_context", {})
        session_id = conversation_data.get("session_id")

        # Build customer info
        customer_info = self._build_customer_info(structured_data)

        # Build product request
        product_request = self._build_product_request(structured_data)

        # Build metadata with new fields
        created_at = conversation_data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))

        duration_seconds = None
        if created_at:
            duration_seconds = int((datetime.utcnow() - created_at).total_seconds())

        # Extract metadata from initial context
        traffic_data = initial_context.get("traffic_data", {})
        interaction_data = initial_context.get("interaction_data", {})
        compliance_data = initial_context.get("compliance_data", {})

        metadata = FinalOutputMetadata(
            traffic_source=traffic_data.get("traffic_source"),
            conversation_start_page=traffic_data.get("conversation_start_page", "/"),
            device_type=interaction_data.get("device_type", "unknown"),
            initiation_method=interaction_data.get("initiation_method", "unknown"),
            flow_path=structured_data.get("flow_path", "STANDARD"),
            conversation_duration_seconds=duration_seconds,
            total_messages=conversation_data.get("message_count", 0),
            privacy_policy_accepted=compliance_data.get("privacy_policy_accepted", True)
        )

        # Create final output
        final_output = FinalOutput(
            conversation_id=conversation_id,
            session_id=session_id,
            customer_info=customer_info,
            product_request=product_request,
            metadata=metadata
        )

        # Send to tablazat.hu with retry logic
        await self._send_with_retry(final_output)

    def _build_customer_info(self, data: Dict[str, Any]) -> CustomerInfo:
        """Build customer info from structured data"""
        company_details = None

        if any(key in data for key in ["company_name", "duns_number", "tax_number"]):
            company_details = CompanyDetails(
                company_name=data.get("company_name"),
                duns_number=data.get("duns_number"),
                tax_number=data.get("tax_number")
            )

        return CustomerInfo(
            name=data.get("customer_name", "Unknown"),
            email=data.get("customer_email", "noemail@example.com"),
            phone=data.get("customer_phone"),
            company_details=company_details
        )

    def _build_product_request(self, data: Dict[str, Any]) -> ProductRequest:
        """Build product request from structured data"""
        # Extract product specifications
        specs = {}

        # Common fields
        spec_fields = [
            "product_type", "quantity", "lifting_height",
            "load_capacity", "fuel_type", "delivery_date",
            "budget_range", "special_requirements"
        ]

        for field in spec_fields:
            if field in data:
                specs[field] = data[field]

        # Add any other fields that aren't already captured
        for key, value in data.items():
            if key not in ["customer_name", "customer_email", "customer_phone",
                           "company_name", "duns_number", "tax_number",
                           "category", "original_query", "flow_path"] and value:
                specs[key] = value

        return ProductRequest(
            category_guess=data.get("category", "unknown"),
            original_user_query=data.get("original_query", ""),
            specifications=specs
        )

    async def _send_with_retry(self, final_output: FinalOutput):
        """Send callback with exponential backoff retry"""
        last_exception = None

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(
                    f"Sending callback to tablazat.hu (attempt {attempt}/{self.max_retries}) "
                    f"for conversation {final_output.conversation_id}"
                )

                response = await self.client.post(
                    self.callback_url,
                    json=final_output.dict(),
                    headers={"Content-Type": "application/json"}
                )

                response.raise_for_status()

                logger.info(
                    f"✅ Successfully sent callback for conversation "
                    f"{final_output.conversation_id}"
                )

                return

            except httpx.HTTPError as e:
                last_exception = e
                logger.warning(
                    f"Callback attempt {attempt} failed for "
                    f"conversation {final_output.conversation_id}: {str(e)}"
                )

                # Exponential backoff: 1s, 2s, 4s, ...
                if attempt < self.max_retries:
                    wait_time = 2 ** (attempt - 1)
                    logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)

            except Exception as e:
                last_exception = e
                logger.error(
                    f"Unexpected error sending callback for "
                    f"conversation {final_output.conversation_id}: {str(e)}"
                )

                if attempt < self.max_retries:
                    wait_time = 2 ** (attempt - 1)
                    await asyncio.sleep(wait_time)

        # All retries failed
        logger.error(
            f"❌ Failed to send callback after {self.max_retries} attempts "
            f"for conversation {final_output.conversation_id}: {str(last_exception)}"
        )

        # In production, you might want to:
        # 1. Store failed callbacks in a dead letter queue
        # 2. Send alert to monitoring system
        # 3. Log to a separate failed callbacks table

        raise Exception(
            f"Failed to send callback after {self.max_retries} attempts: "
            f"{str(last_exception)}"
        )

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


# Create singleton instance
callback_service = CallbackService()
