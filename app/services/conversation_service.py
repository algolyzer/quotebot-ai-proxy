"""
Conversation Service - SIMPLIFIED
Just passes raw context to Dify without complex parsing
"""

import uuid
import json
from datetime import datetime
from typing import Dict, Any, Optional, List

from app.models.schemas import (
    ConversationStatus, MessageRole,
    ConversationRecord, MessageRecord, StartConversationRequest
)
from app.services.database import redis_client, db_service
from app.services.dify_service import dify_service
from app.utils.logger import setup_logger
from app.utils.response_parser import parse_buttons_from_answer, parse_stage_from_answer

logger = setup_logger(__name__)


class ConversationService:
    """High-level service for managing conversations"""

    async def start_conversation(
            self,
            request: StartConversationRequest
    ) -> Dict[str, Any]:
        """
        Start a new conversation - SIMPLIFIED VERSION

        Just takes the raw context and sends it to Dify as-is.
        No complex validation or parsing.

        Args:
            request: Simple request with session_id and context dict

        Returns:
            Dict with conversation_id and initial AI response
        """
        # Generate unique conversation ID
        conversation_id = f"conv-{uuid.uuid4()}"

        logger.info(
            f"Starting conversation {conversation_id} "
            f"for session {request.session_id}"
        )
        context_dict = {
            "current_date": request.current_date,
            "session_id": request.session_id,
            "user_data": request.user_data,
            "traffic_data": request.traffic_data,
            "context_data": request.context_data,
            "interaction_data": request.interaction_data,
            "compliance_data": request.compliance_data,
        }

        # Convert the entire context to a JSON string for Dify
        context_string = json.dumps(context_dict, ensure_ascii=False, indent=2)

        logger.info(f"Context being sent to Dify:\n{context_string}")

        # Create conversation in Dify with the raw context as a string
        try:
            dify_response = await dify_service.create_conversation(
                user_id=request.session_id,
                context_string=context_string
            )
        except Exception as e:
            logger.error(f"Failed to create Dify conversation: {e}")
            raise

        dify_conversation_id = dify_response.get("conversation_id")
        initial_answer = dify_response.get("answer", "")

        # Prepare conversation record
        conversation_data = {
            "conversation_id": conversation_id,
            "session_id": request.session_id,
            "dify_conversation_id": dify_conversation_id,
            "status": ConversationStatus.ACTIVE.value,
            "initial_context": context_dict,  # Store raw context
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
        5. Parse buttons and stage from response

        Args:
            conversation_id: Conversation ID
            message: User's message

        Returns:
            Dict with AI answer, buttons, stage, and completion status
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

        # Parse stage from answer first
        cleaned_answer_stage, stage = parse_stage_from_answer(answer)

        # Then parse buttons from the cleaned answer
        cleaned_answer, buttons = parse_buttons_from_answer(cleaned_answer_stage)

        # Save the original answer (with buttons and stage) to database for history
        await self._save_message(
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content=answer,  # Store original with buttons and stage
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

        # Build result with parsed buttons and stage
        result = {
            "answer": cleaned_answer,  # Return cleaned answer without button/stage tags
            "conversation_complete": is_complete,
            "buttons": buttons,  # Return parsed buttons array
            "stage": stage  # Return parsed stage (empty string if not found)
        }

        # If complete, just mark as complete - no callback needed
        if is_complete:
            logger.info(f"Conversation {conversation_id} is complete")

            await redis_client.update_conversation(
                conversation_id,
                {
                    "status": ConversationStatus.COMPLETED.value,
                    "completed_at": datetime.utcnow().isoformat()
                }
            )

            try:
                await db_service.update_conversation(
                    conversation_id,
                    {
                        "status": ConversationStatus.COMPLETED.value,
                        "completed_at": datetime.utcnow()
                    }
                )
            except Exception as e:
                logger.error(f"Failed to update conversation status in database: {e}")

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


# Create singleton instance
conversation_service = ConversationService()
