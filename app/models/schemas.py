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
# INITIAL CONTEXT (FROM TABLAZAT.HU) - SIMPLIFIED
# ============================================================================

class StartConversationRequest(BaseModel):
    """
    Request to start a new conversation
    Matches the documentation schema (no 'context' wrapper)
    """
    current_date: str = Field(..., description="Current date (Required)")
    session_id: str = Field(..., description="Unique session ID (Required)")

    user_data: Dict[str, Any] = Field(..., description="User data section")
    traffic_data: Dict[str, Any] = Field(..., description="Traffic data section")
    context_data: Dict[str, Any] = Field(..., description="Context data section")
    interaction_data: Dict[str, Any] = Field(..., description="Interaction data section")
    compliance_data: Dict[str, Any] = Field(..., description="Compliance data section")

    class Config:
        json_schema_extra = {
            "example": {
                "current_date": "2025-10-20",
                "session_id": "xyz-abc-123",
                "user_data": {
                    "is_identified_user": False,
                    "name": "Teszt Elek",
                    "user_id": 1485
                },
                "traffic_data": {
                    "traffic_source": "google_ads_targonca_kampany",
                    "conversation_start_page": "/targonca"
                },
                "context_data": {
                    "breadcrumbs": "Targonca > Elektromos targonca",
                    "category": "Elektromos targonca"
                },
                "interaction_data": {
                    "device_type": "desktop",
                    "initiation_method": "user_clicked"
                },
                "compliance_data": {
                    "privacy_policy_accepted": True
                }
            }
        }


# ============================================================================
# CONVERSATION ENDPOINTS
# ============================================================================

class StartConversationResponse(BaseModel):
    """Response after starting a conversation"""
    conversation_id: str
    status: str = "started"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    answer: str = Field(
        ...,
        description="Initial AI response to start the conversation"
    )


class ChatMessageRequest(BaseModel):
    """Request to send a chat message"""
    conversation_id: str = Field(
        ...,
        description="Conversation ID from start_conversation"
    )
    message: str = Field(
        ...,
        description="User's message"
    )


class ChatMessageResponse(BaseModel):
    """Response from chat endpoint"""
    answer: str
    conversation_complete: bool = False
    buttons: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Parsed buttons from AI response"
    )
    stage: str = Field(
        default="",
        description="Current conversation stage (empty string if not specified)"
    )
    metadata: Optional[Dict[str, Any]] = None


class MessageHistory(BaseModel):
    """Single message in conversation history"""
    role: MessageRole
    content: str
    timestamp: Optional[datetime] = None
    buttons: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Parsed buttons from AI response (only for assistant messages)"
    )


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
    traffic_source: Optional[str] = None
    conversation_start_page: str
    device_type: str
    initiation_method: str
    flow_path: str = "STANDARD"
    conversation_duration_seconds: Optional[int] = None
    total_messages: Optional[int] = None
    privacy_policy_accepted: bool = True
    initial_breadcrumbs: Optional[str] = None
    initial_category: Optional[str] = None


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
    initial_context: Dict[str, Any]
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
