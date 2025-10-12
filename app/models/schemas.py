"""Pydantic models for request/response validation"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List
from datetime import datetime


# Request Models
class ChatMessageRequest(BaseModel):
    """Chat message request"""
    query: str = Field(..., min_length=1, max_length=10000, description="User message")
    conversation_id: Optional[str] = Field(None, description="Conversation ID to continue")
    user: str = Field(..., min_length=1, max_length=255, description="User identifier")
    inputs: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional inputs")
    response_mode: str = Field(default="blocking", description="Response mode: blocking or streaming")

    @field_validator('response_mode')
    def validate_response_mode(cls, v):
        if v not in ['blocking', 'streaming']:
            raise ValueError('response_mode must be either blocking or streaming')
        return v


# Response Models
class ChatMessageResponse(BaseModel):
    """Chat message response"""
    answer: str
    conversation_id: str
    message_id: str
    created_at: int


class HistoryMessage(BaseModel):
    """Single message in conversation history"""
    role: str
    content: str
    created_at: int
    message_id: Optional[str] = None


class ConversationHistoryResponse(BaseModel):
    """Conversation history response"""
    messages: List[HistoryMessage]
    has_more: bool
    total: int


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: datetime
    version: str
    redis_connected: bool
    dify_accessible: bool


class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
