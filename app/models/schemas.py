"""
Pydantic Models for Request/Response validation
Updated to match new tablazat.hu schema requirements
"""

from pydantic import BaseModel, EmailStr, Field, field_validator
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
# INITIAL CONTEXT (FROM TABLAZAT.HU) - UPDATED SCHEMA
# ============================================================================

class UserData(BaseModel):
    """User information from tablazat.hu"""
    is_identified_user: bool = Field(
        ...,
        description="Whether the user is identified/logged in"
    )
    name: Optional[str] = Field(
        None,
        description="User's name (required when is_identified_user=true)"
    )
    user_id: Optional[int] = Field(
        None,
        description="User's ID in tablazat.hu system (required when is_identified_user=true)"
    )
    email: Optional[EmailStr] = Field(
        None,
        description="User's email address"
    )

    @field_validator('name', 'user_id')
    @classmethod
    def validate_identified_user_fields(cls, v, info):
        """Validate that identified users have required fields"""
        # This will be called for each field, but we need to check after all fields are set
        # So we'll do a final check in model_post_init
        return v

    def model_post_init(self, __context):
        """Validate conditional requirements after model initialization"""
        if self.is_identified_user:
            if not self.name:
                raise ValueError("user_data.name is required when is_identified_user=true")
            if self.user_id is None:
                raise ValueError("user_data.user_id is required when is_identified_user=true")


class TrafficData(BaseModel):
    """Traffic and source information"""
    traffic_source: Optional[str] = Field(
        None,
        description="Marketing campaign or traffic source identifier"
    )
    conversation_start_page: str = Field(
        ...,
        description="Page where the conversation was initiated"
    )


class InteractionData(BaseModel):
    """User interaction metadata"""
    device_type: str = Field(
        ...,
        description="Device type: desktop, mobile, tablet",
        pattern="^(desktop|mobile|tablet)$"
    )
    initiation_method: str = Field(
        ...,
        description="How conversation started: user_clicked, auto_popup, chat_icon, etc."
    )


class ComplianceData(BaseModel):
    """Compliance and privacy information"""
    privacy_policy_accepted: bool = Field(
        ...,
        description="Whether user has accepted the privacy policy"
    )


class InitialContext(BaseModel):
    """Complete initial context from tablazat.hu"""
    current_date: str = Field(
        ...,
        description="Current date in YYYY-MM-DD format",
        pattern=r"^\d{4}-\d{2}-\d{2}$"
    )
    session_id: str = Field(
        ...,
        description="Unique session ID from tablazat.hu"
    )
    user_data: UserData
    traffic_data: TrafficData
    interaction_data: InteractionData
    compliance_data: ComplianceData


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
    traffic_source: Optional[str] = None
    conversation_start_page: str
    device_type: str
    initiation_method: str
    flow_path: str = "STANDARD"
    conversation_duration_seconds: Optional[int] = None
    total_messages: Optional[int] = None
    privacy_policy_accepted: bool = True


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
