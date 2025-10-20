"""
Conversation API Endpoints
Clean, RESTful endpoint design
"""

from fastapi import APIRouter, HTTPException, Request, status
from typing import List

from app.models.schemas import (
    StartConversationRequest, StartConversationResponse,
    ChatMessageRequest, ChatMessageResponse,
    MessageHistory
)
from app.services.conversation_service import conversation_service
from app.services.database import redis_client
from app.config import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter()


@router.post(
    "/start_conversation",
    response_model=StartConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a new conversation",
    description="Initialize a conversation with context from tablazat.hu"
)
async def start_conversation(
        request: Request,
        context: StartConversationRequest
):
    """
    **Start a new conversation**

    This is the "handshake" endpoint that receives initial context
    from tablazat.hu and creates a new Dify conversation.

    **Flow:**
    1. Receives session info, user data, and traffic source
    2. Creates conversation in Dify
    3. Returns conversation_id to track the session
    """
    request_id = getattr(request.state, "request_id", "unknown")

    logger.info(
        f"[{request_id}] 🆕 Starting conversation for session {context.session_id}"
    )

    # Rate limiting
    if settings.RATE_LIMIT_ENABLED:
        rate_limit_ok = await redis_client.check_rate_limit(
            f"session:{context.session_id}"
        )

        if not rate_limit_ok:
            logger.warning(
                f"[{request_id}] 🚫 Rate limit exceeded for {context.session_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later."
            )

    try:
        result = await conversation_service.start_conversation(context)

        logger.info(
            f"[{request_id}] ✅ Conversation started: {result['conversation_id']}"
        )

        return StartConversationResponse(
            conversation_id=result["conversation_id"],
            status="started"
        )

    except Exception as e:
        logger.error(
            f"[{request_id}] ❌ Error starting conversation: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start conversation: {str(e)}"
        )


@router.post(
    "/chat",
    response_model=ChatMessageResponse,
    summary="Send a message",
    description="Send a message in an active conversation"
)
async def send_message(
        request: Request,
        chat_msg: ChatMessageRequest
):
    """
    **Send a message in an active conversation**

    This endpoint forwards messages to Dify and returns AI responses.
    It also automatically detects when a conversation is complete.

    **Flow:**
    1. Receives user message with conversation_id
    2. Forwards to Dify AI
    3. Returns AI response
    4. Checks if conversation is complete
    5. If complete, triggers callback to tablazat.hu
    """
    request_id = getattr(request.state, "request_id", "unknown")

    logger.debug(
        f"[{request_id}] 💬 Message for {chat_msg.conversation_id}"
    )

    # Validate message length
    if len(chat_msg.message) > 4000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message too long (max 4000 characters)"
        )

    try:
        result = await conversation_service.send_message(
            conversation_id=chat_msg.conversation_id,
            message=chat_msg.message
        )

        if result.get("conversation_complete"):
            logger.info(
                f"[{request_id}] 🎉 Conversation {chat_msg.conversation_id} complete!"
            )

        return ChatMessageResponse(
            answer=result["answer"],
            buttons=result["buttons"],
            conversation_complete=result["conversation_complete"]
        )

    except ValueError as e:
        logger.warning(
            f"[{request_id}] ⚠️  Conversation not found: {chat_msg.conversation_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

    except Exception as e:
        logger.error(
            f"[{request_id}] ❌ Error sending message: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send message: {str(e)}"
        )


@router.get(
    "/history/{conversation_id}",
    response_model=List[MessageHistory],
    summary="Get conversation history",
    description="Retrieve all messages for a conversation (used on page refresh)"
)
async def get_history(
        request: Request,
        conversation_id: str
):
    """
    **Get conversation history**

    Returns all messages in a conversation. This is used when
    a user refreshes the page to restore the conversation state.

    **Response:**
    Array of messages with role (user/assistant) and content
    """
    request_id = getattr(request.state, "request_id", "unknown")

    logger.debug(
        f"[{request_id}] 📜 Fetching history for {conversation_id}"
    )

    try:
        messages = await conversation_service.get_history(conversation_id)

        history = [
            MessageHistory(
                role=msg["role"],
                content=msg["content"],
                timestamp=msg.get("timestamp")
            )
            for msg in messages
        ]

        logger.debug(
            f"[{request_id}] ✅ Retrieved {len(history)} messages"
        )

        return history

    except Exception as e:
        logger.error(
            f"[{request_id}] ❌ Error fetching history: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch history: {str(e)}"
        )


@router.get(
    "/{conversation_id}",
    summary="Get conversation details",
    description="Get detailed status of a conversation (debug endpoint)"
)
async def get_conversation_status(
        request: Request,
        conversation_id: str
):
    """
    **Get conversation status** (Debug endpoint)

    Returns detailed information about a conversation.
    Only available in development mode.
    """
    # Only enable in non-production
    if settings.ENVIRONMENT == "production":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endpoint not available in production"
        )

    try:
        conversation = await redis_client.get_conversation(conversation_id)

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )

        return conversation

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
