"""Chat endpoints"""
from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
import httpx
from app.models.schemas import (
    ChatMessageRequest,
    ChatMessageResponse,
    ConversationHistoryResponse,
    HistoryMessage
)
from app.services.dify_service import dify_service
from app.core.redis_client import redis_client
from app.api.dependencies import verify_api_key
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post("/chat", response_model=ChatMessageResponse)
async def send_chat_message(
    request: ChatMessageRequest,
    api_key: str = Depends(verify_api_key)
) -> ChatMessageResponse:
    """
    Send a chat message to Dify

    - **query**: User message content
    - **conversation_id**: Optional conversation ID to continue
    - **user**: User identifier
    - **inputs**: Optional additional inputs
    - **response_mode**: blocking or streaming
    """
    try:
        logger.info(f"→ Chat request from user: {request.user}")

        # Send to Dify
        dify_response = await dify_service.send_message(
            query=request.query,
            user=request.user,
            conversation_id=request.conversation_id,
            inputs=request.inputs,
            response_mode=request.response_mode
        )

        # Extract response data
        answer = dify_response.get("answer", "")
        conversation_id = dify_response.get("conversation_id", "")
        message_id = dify_response.get("message_id", "")
        created_at = dify_response.get("created_at", 0)

        # Store conversation mapping in Redis
        if conversation_id:
            redis_client.set_conversation(request.user, {
                "conversation_id": conversation_id,
                "last_message_id": message_id,
                "last_activity": created_at
            })

        logger.info(f"✓ Chat response sent to user: {request.user}")

        return ChatMessageResponse(
            answer=answer,
            conversation_id=conversation_id,
            message_id=message_id,
            created_at=created_at
        )

    except httpx.HTTPError as e:
        logger.error(f"✗ Dify API error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Dify service unavailable"
        )
    except Exception as e:
        logger.error(f"✗ Error processing chat: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/history/{conversation_id}", response_model=ConversationHistoryResponse)
async def get_conversation_history(
    conversation_id: str,
    user: str,
    limit: int = 20,
    api_key: str = Depends(verify_api_key)
) -> ConversationHistoryResponse:
    """
    Get conversation history

    - **conversation_id**: Conversation ID
    - **user**: User identifier
    - **limit**: Number of messages to retrieve (max 100)
    """
    try:
        logger.info(f"→ History request for conversation: {conversation_id}")

        # Validate limit
        if limit < 1 or limit > 100:
            limit = 20

        # Get history from Dify
        history_data = await dify_service.get_history(
            conversation_id=conversation_id,
            user=user,
            limit=limit
        )

        # Transform to response format
        messages = []
        data = history_data.get("data", [])

        # Dify returns newest first, reverse for chronological order
        for item in reversed(data):
            # Add user message
            if item.get("query"):
                messages.append(
                    HistoryMessage(
                        role="user",
                        content=item["query"],
                        created_at=item.get("created_at", 0),
                        message_id=item.get("id")
                    )
                )

            # Add assistant message
            if item.get("answer"):
                messages.append(
                    HistoryMessage(
                        role="assistant",
                        content=item["answer"],
                        created_at=item.get("created_at", 0),
                        message_id=item.get("id")
                    )
                )

        logger.info(f"✓ Retrieved {len(messages)} messages")

        return ConversationHistoryResponse(
            messages=messages,
            has_more=history_data.get("has_more", False),
            total=len(messages)
        )

    except httpx.HTTPError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Dify service unavailable"
        )
    except Exception as e:
        logger.error(f"✗ Error fetching history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.delete("/conversation/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    user: str,
    api_key: str = Depends(verify_api_key)
):
    """
    Delete a conversation

    - **conversation_id**: Conversation ID to delete
    - **user**: User identifier
    """
    try:
        logger.info(f"→ Delete request for conversation: {conversation_id}")

        # Delete from Dify
        deleted = await dify_service.delete_conversation(
            conversation_id=conversation_id,
            user=user
        )

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )

        # Delete from Redis
        redis_client.delete_conversation(user)

        logger.info(f"✓ Deleted conversation: {conversation_id}")

        return {"status": "deleted", "conversation_id": conversation_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"✗ Error deleting conversation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
