"""
API Routes
All HTTP endpoints for the Quotebot AI Proxy
"""

from fastapi import APIRouter, HTTPException, Request, status
from typing import List

from app.models.schemas import (
    StartConversationRequest, StartConversationResponse,
    ChatMessageRequest, ChatMessageResponse,
    MessageHistory, ErrorResponse
)
from app.services.conversation_service import conversation_service
from app.services.database import redis_client
from app.config import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter()


# ============================================================================
# ENDPOINT 1: START CONVERSATION
# ============================================================================

@router.post(
    "/start_conversation",
    response_model=StartConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a new conversation",
    description="Initialize a new conversation with context from tablazat.hu"
)
async def start_conversation(
        request: Request,
        context: StartConversationRequest
):
    """
    Start a new conversation (The Handshake)

    This endpoint receives initial context from tablazat.hu and creates
    a new conversation in Dify.

    **Input:** Initial context with session_id, user_data, traffic_data
    **Output:** conversation_id to track this session
    """
    request_id = getattr(request.state, "request_id", "unknown")

    logger.info(
        f"[{request_id}] Starting conversation for session {context.session_id}"
    )

    # Rate limiting
    if settings.RATE_LIMIT_ENABLED:
        rate_limit_ok = await redis_client.check_rate_limit(
            f"session:{context.session_id}"
        )

        if not rate_limit_ok:
            logger.warning(
                f"[{request_id}] Rate limit exceeded for session {context.session_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later."
            )

    try:
        result = await conversation_service.start_conversation(context)

        logger.info(
            f"[{request_id}] Conversation started: {result['conversation_id']}"
        )

        return StartConversationResponse(
            conversation_id=result["conversation_id"],
            status="started"
        )

    except Exception as e:
        logger.error(
            f"[{request_id}] Error starting conversation: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start conversation: {str(e)}"
        )


# ============================================================================
# ENDPOINT 2: SEND MESSAGE (CHAT)
# ============================================================================

@router.post(
    "/chat",
    response_model=ChatMessageResponse,
    summary="Send a chat message",
    description="Send a message in an existing conversation"
)
async def send_message(
        request: Request,
        chat_msg: ChatMessageRequest
):
    """
    Send a message in an ongoing conversation

    This endpoint forwards the user's message to Dify and returns
    the AI's response.

    **Input:** conversation_id + user message
    **Output:** AI assistant's answer + completion status
    """
    request_id = getattr(request.state, "request_id", "unknown")

    logger.debug(
        f"[{request_id}] Received message for conversation "
        f"{chat_msg.conversation_id}"
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

        return ChatMessageResponse(
            answer=result["answer"],
            conversation_complete=result["conversation_complete"]
        )

    except ValueError as e:
        # Conversation not found
        logger.warning(
            f"[{request_id}] Conversation not found: {chat_msg.conversation_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

    except Exception as e:
        logger.error(
            f"[{request_id}] Error sending message: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send message: {str(e)}"
        )


# ============================================================================
# ENDPOINT 3: GET CONVERSATION HISTORY
# ============================================================================

@router.get(
    "/history/{conversation_id}",
    response_model=List[MessageHistory],
    summary="Get conversation history",
    description="Retrieve message history for a conversation (for page refresh)"
)
async def get_history(
        request: Request,
        conversation_id: str
):
    """
    Get conversation history

    This endpoint returns all messages in a conversation, used when
    the user refreshes the page.

    **Input:** conversation_id (in URL)
    **Output:** Array of message objects with role and content
    """
    request_id = getattr(request.state, "request_id", "unknown")

    logger.debug(
        f"[{request_id}] Fetching history for conversation {conversation_id}"
    )

    try:
        messages = await conversation_service.get_history(conversation_id)

        # Convert to response format
        history = [
            MessageHistory(
                role=msg["role"],
                content=msg["content"],
                timestamp=msg.get("timestamp")
            )
            for msg in messages
        ]

        return history

    except Exception as e:
        logger.error(
            f"[{request_id}] Error fetching history: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch history: {str(e)}"
        )


# ============================================================================
# ADMIN/DEBUG ENDPOINTS (Optional)
# ============================================================================

@router.get(
    "/conversation/{conversation_id}/status",
    summary="Get conversation status",
    description="Get detailed status of a conversation (for debugging)"
)
async def get_conversation_status(conversation_id: str):
    """Get conversation status (admin/debug endpoint)"""

    # Only enable in non-production
    if settings.ENVIRONMENT == "production":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endpoint not available in production"
        )

    try:
        # Try Redis first
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
