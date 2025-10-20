"""
Conversation Service
Manages conversation lifecycle and coordinates between Redis, PostgreSQL, and Dify
Updated to handle new schema fields
"""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List

from app.models.schemas import (
    InitialContext, ConversationStatus, MessageRole,
    ConversationRecord, MessageRecord
)
from app.services.database import redis_client, db_service
from app.services.dify_service import dify_service
from app.utils.logger import setup_logger
from app.utils.response_parser import parse_buttons_from_answer

logger = setup_logger(__name__)


class ConversationService:
    """High-level service for managing conversations"""

    async def start_conversation(
            self,
            context: InitialContext
    ) -> Dict[str, Any]:
        """
        Start a new conversation

        1. Generate conversation ID
        2. Create conversation in Dify with full context
        3. Store in Redis (fast access)
        4. Store in PostgreSQL (persistence)

        Args:
            context: Initial context from tablazat.hu

        Returns:
            Dict with conversation_id and initial AI response
        """
        # Generate unique conversation ID
        conversation_id = f"conv-{uuid.uuid4()}"

        logger.info(
            f"Starting conversation {conversation_id} "
            f"for session {context.session_id}"
        )

        # Prepare comprehensive inputs for Dify
        dify_inputs = {
            # Date context
            "current_date": context.current_date,

            # User information
            "is_identified_user": context.user_data.is_identified_user,
            "user_name": context.user_data.name or "Guest",
            "user_id": context.user_data.user_id if context.user_data.user_id is not None else "",
            "user_email": context.user_data.email or "",

            # Traffic and source
            "traffic_source": context.traffic_data.traffic_source or "direct",
            "landing_page": context.traffic_data.landing_page,
            "conversation_start_page": context.traffic_data.conversation_start_page,

            # Interaction metadata
            "device_type": context.interaction_data.device_type,
            "initiation_method": context.interaction_data.initiation_method,

            # Compliance
            "privacy_accepted": context.compliance_data.privacy_policy_accepted,
        }

        # Create a natural first message that includes context
        first_message_parts = [
            f"Date: {context.current_date}",
        ]

        if context.user_data.is_identified_user and context.user_data.name:
            first_message_parts.append(f"User: {context.user_data.name}")

        first_message_parts.extend([
            f"Device: {context.interaction_data.device_type}",
            f"Started from: {context.traffic_data.conversation_start_page}",
        ])

        if context.traffic_data.traffic_source:
            first_message_parts.append(f"Source: {context.traffic_data.traffic_source}")

        first_message = "\n".join(first_message_parts)

        # Create conversation in Dify
        try:
            dify_response = await dify_service.create_conversation(
                user_id=context.session_id,
                initial_inputs=dify_inputs,
                first_message=first_message
            )
        except Exception as e:
            logger.error(f"Failed to create Dify conversation: {e}")
            raise

        dify_conversation_id = dify_response.get("conversation_id")
        initial_answer = dify_response.get("answer", "")

        # Prepare conversation record
        conversation_data = {
            "conversation_id": conversation_id,
            "session_id": context.session_id,
            "dify_conversation_id": dify_conversation_id,
            "status": ConversationStatus.ACTIVE.value,
            "initial_context": context.dict(),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "message_count": 1
        }

        # Store in Redis (fast access)
        await redis_client.save_conversation(
            conversation_id,
            conversation_data
        )

        # Store in PostgreSQL (persistence)
        try:
            await db_service.save_conversation(conversation_data)
        except Exception as e:
            logger.error(f"Failed to save conversation to database: {e}")
            # Continue even if DB save fails - Redis is our primary store

        # Store initial AI message
        await self._save_message(
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content=initial_answer,
            dify_message_id=dify_response.get("message_id")
        )

        logger.info(
            f"Conversation {conversation_id} started successfully. "
            f"Dify conversation: {dify_conversation_id}"
        )

        return {
            "conversation_id": conversation_id,
            "dify_conversation_id": dify_conversation_id,
            "initial_answer": initial_answer,
            "status": "started",
            "timestamp": datetime.utcnow().isoformat()
        }

    async def send_message(
            self,
            conversation_id: str,
            message: str
    ) -> Dict[str, Any]:
        """
        Send a message in an existing conversation

        1. Retrieve conversation from Redis
        2. Send message to Dify
        3. Check if conversation is complete
        4. Update storage
        5. Trigger callback if complete

        Args:
            conversation_id: Conversation ID
            message: User's message

        Returns:
            Dict with AI answer and completion status
        """
        # Get conversation from Redis
        conversation = await redis_client.get_conversation(conversation_id)

        if not conversation:
            # Try database as fallback
            conversation = await db_service.get_conversation(conversation_id)

            if not conversation:
                logger.error(f"Conversation {conversation_id} not found")
                raise ValueError(f"Conversation {conversation_id} not found")

            # Restore to Redis
            await redis_client.save_conversation(conversation_id, conversation)

        session_id = conversation["session_id"]
        dify_conversation_id = conversation["dify_conversation_id"]

        logger.debug(
            f"Sending message to conversation {conversation_id}: "
            f"{message[:50]}..."
        )

        # Save user message
        await self._save_message(
            conversation_id=conversation_id,
            role=MessageRole.USER,
            content=message
        )

        # Send to Dify
        try:
            dify_response = await dify_service.send_message(
                conversation_id=dify_conversation_id,
                user_id=session_id,
                message=message
            )
        except Exception as e:
            logger.error(f"Failed to send message to Dify: {e}")
            raise

        answer = dify_response.get("answer", "")

        # Parse buttons from answer

        cleaned_answer, buttons = parse_buttons_from_answer(answer)

        # Save the original answer (with buttons) to database for history
        await self._save_message(
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content=answer,  # Store original with buttons
            dify_message_id=dify_response.get("message_id")
        )

        # Update message count
        message_count = conversation.get("message_count", 0) + 2
        await redis_client.update_conversation(
            conversation_id,
            {"message_count": message_count, "updated_at": datetime.utcnow().isoformat()}
        )

        # Check if conversation is complete
        variables = await dify_service.get_conversation_variables(
            dify_conversation_id,
            session_id
        )

        is_complete = dify_service.is_conversation_complete(
            dify_response,
            variables
        )

        # Build result with parsed buttons
        result = {
            "answer": cleaned_answer,  # Return cleaned answer without button tags
            "conversation_complete": is_complete,
            "buttons": buttons  # Return parsed buttons array
        }

        # If complete, trigger finalization
        if is_complete:
            logger.info(f"Conversation {conversation_id} is complete")

            # Import here to avoid circular dependency
            from app.services.callback_service import callback_service

            # Trigger callback in background
            import asyncio
            asyncio.create_task(
                self._finalize_conversation(
                    conversation_id,
                    dify_response,
                    variables
                )
            )

        return result

    async def get_history(
            self,
            conversation_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get conversation history

        First tries Redis, falls back to PostgreSQL

        Args:
            conversation_id: Conversation ID

        Returns:
            List of messages
        """
        # Try Redis first
        messages = await redis_client.get_messages(conversation_id)

        if not messages:
            # Fall back to database
            messages = await db_service.get_messages(conversation_id)

        # Format for frontend
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                "role": msg.get("role"),
                "content": msg.get("content"),
                "timestamp": msg.get("created_at")
            })

        return formatted_messages

    async def _save_message(
            self,
            conversation_id: str,
            role: MessageRole,
            content: str,
            dify_message_id: Optional[str] = None
    ):
        """Save message to both Redis and PostgreSQL"""
        message_id = f"msg-{uuid.uuid4()}"

        message_data = {
            "message_id": message_id,
            "conversation_id": conversation_id,
            "role": role.value,
            "content": content,
            "dify_message_id": dify_message_id,
            "created_at": datetime.utcnow().isoformat()
        }

        # Save to Redis
        await redis_client.add_message(conversation_id, message_data)

        # Save to PostgreSQL
        try:
            await db_service.save_message({
                **message_data,
                "created_at": datetime.utcnow()
            })
        except Exception as e:
            logger.error(f"Failed to save message to database: {e}")

    async def _finalize_conversation(
            self,
            conversation_id: str,
            dify_response: Dict[str, Any],
            variables: Dict[str, Any]
    ):
        """
        Finalize conversation and send callback to tablazat.hu

        1. Extract structured data
        2. Update conversation status
        3. Send callback to tablazat.hu
        """
        logger.info(f"Finalizing conversation {conversation_id}")

        # Get conversation data
        conversation = await redis_client.get_conversation(conversation_id)

        if not conversation:
            logger.error(f"Cannot finalize - conversation {conversation_id} not found")
            return

        # Extract structured data from variables
        structured_data = dify_service.extract_structured_data(
            dify_response,
            variables
        )

        # Build final output
        from app.services.callback_service import callback_service

        try:
            await callback_service.send_final_output(
                conversation_id=conversation_id,
                conversation_data=conversation,
                structured_data=structured_data or {}
            )

            # Update status
            await redis_client.update_conversation(
                conversation_id,
                {
                    "status": ConversationStatus.COMPLETED.value,
                    "completed_at": datetime.utcnow().isoformat()
                }
            )

            await db_service.update_conversation(
                conversation_id,
                {
                    "status": ConversationStatus.COMPLETED.value,
                    "completed_at": datetime.utcnow()
                }
            )

            logger.info(f"Conversation {conversation_id} finalized successfully")

        except Exception as e:
            logger.error(f"Failed to finalize conversation {conversation_id}: {e}")

            # Mark as failed
            await redis_client.update_conversation(
                conversation_id,
                {"status": ConversationStatus.FAILED.value}
            )


# Create singleton instance
conversation_service = ConversationService()
