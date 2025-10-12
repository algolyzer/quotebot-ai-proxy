"""
Pydantic Models for Request/Response validation
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class ConversationStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    ABANDONED = "abandoned"


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


# ============================================================================
# INITIAL CONTEXT (FROM TABLAZAT.HU)
# ============================================================================

class UserData(BaseModel):
    is_identified_user: bool
    name: Optional[str] = None
    email: Optional[EmailStr] = None


class TrafficData(BaseModel):
    traffic_source: str
    landing_page: str


class InitialContext(BaseModel):
    session_id: str = Field(..., description="Unique session ID from tablazat.hu")
    user_data: UserData
    traffic_data: TrafficData


# ============================================================================
# CONVERSATION ENDPOINTS
# ============================================================================

class StartConversationRequest(InitialContext):
    """Request to start a new conversation"""
    pass


class StartConversationResponse(BaseModel):
    """Response after starting a conversation"""
    conversation_id: str
    status: str = "started"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChatMessageRequest(BaseModel):
    """Request to send a chat message"""
    conversation_id: str = Field(..., description="Conversation ID from start_conversation")
    message: str = Field(..., min_length=1, max_length=4000, description="User's message")


class ChatMessageResponse(BaseModel):
    """Response from chat endpoint"""
    answer: str
    conversation_complete: bool = False
    metadata: Optional[Dict[str, Any]] = None


class MessageHistory(BaseModel):
    """Single message in conversation history"""
    role: MessageRole
    content: str
    timestamp: Optional[datetime] = None


class ConversationHistoryResponse(BaseModel):
    """Response containing conversation history"""
    conversation_id: str
    messages: List[MessageHistory]
    status: ConversationStatus


# ============================================================================
# FINAL OUTPUT (TO TABLAZAT.HU)
# ============================================================================

class CompanyDetails(BaseModel):
    duns_number: Optional[str] = None
    company_name: Optional[str] = None
    tax_number: Optional[str] = None


class CustomerInfo(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    company_details: Optional[CompanyDetails] = None


class ProductRequest(BaseModel):
    category_guess: str
    original_user_query: str
    specifications: Dict[str, Any] = Field(default_factory=dict)


class FinalOutputMetadata(BaseModel):
    traffic_source: str
    landing_page: str
    flow_path: str = "STANDARD"
    conversation_duration_seconds: Optional[int] = None
    total_messages: Optional[int] = None


class FinalOutput(BaseModel):
    """Final structured data sent to tablazat.hu"""
    conversation_id: str
    session_id: str
    customer_info: CustomerInfo
    product_request: ProductRequest
    metadata: FinalOutputMetadata


# ============================================================================
# DIFY API MODELS
# ============================================================================

class DifyChatRequest(BaseModel):
    """Request to Dify chat API"""
    inputs: Dict[str, Any] = Field(default_factory=dict)
    query: str
    response_mode: str = "blocking"
    conversation_id: Optional[str] = None
    user: str


class DifyMessageResponse(BaseModel):
    """Response from Dify (blocking mode)"""
    event: str
    task_id: str
    id: str
    message_id: str
    conversation_id: str
    mode: str
    answer: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: int


# ============================================================================
# INTERNAL STORAGE MODELS
# ============================================================================

class ConversationRecord(BaseModel):
    """Internal conversation record"""
    conversation_id: str
    session_id: str
    dify_conversation_id: Optional[str] = None
    initial_context: InitialContext
    status: ConversationStatus = ConversationStatus.ACTIVE
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    message_count: int = 0

    class Config:
        use_enum_values = True


class MessageRecord(BaseModel):
    """Individual message record"""
    message_id: str
    conversation_id: str
    role: MessageRole
    content: str
    dify_message_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True


# ============================================================================
# ERROR RESPONSES
# ============================================================================

class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    message: str
    request_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
