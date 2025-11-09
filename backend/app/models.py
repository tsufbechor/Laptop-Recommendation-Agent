"""Pydantic models shared across the backend."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, validator


class Product(BaseModel):
    """Product entry as stored in the catalogue."""

    sku: str = Field(alias="SKU")
    vendor: str = Field(alias="Vendor")
    family: str = Field(alias="Family")
    name: str = Field(alias="Name")
    description: str = Field(alias="Description")
    cpu: str = Field(alias="CPU")
    gpu: str = Field(alias="GPU")
    storage: str = Field(alias="Storage")
    ram: str = Field(alias="RAM")
    price: float = Field(alias="Price")
    image_url: Optional[str] = Field(default=None, alias="ImageUrl")

    model_config = {"populate_by_name": True}

    @validator("price", pre=True)
    def _coerce_price(cls, value: Any) -> float:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            cleaned = value.replace("$", "").replace(",", "").strip()
            if not cleaned:
                return 0.0
            return float(cleaned)
        raise ValueError("Unsupported price format")


class ProductKnowledge(BaseModel):
    """Extended product information from web scraping."""

    sku: str
    summary: str  # 1-2 paragraphs
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    use_cases: List[str] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class RetrievedProduct(Product):
    """Product returned from the semantic search with similarity metadata."""

    similarity: float = Field(default=0.0)
    matched_keywords: Optional[List[str]] = None
    explanation: Optional[str] = None
    knowledge: Optional[ProductKnowledge] = None


class EnhancedProduct(Product):
    """Product with additional knowledge base information."""

    knowledge: Optional[ProductKnowledge] = None


class ProductComparison(BaseModel):
    """Comparison details between two products."""

    better_at: List[str] = Field(default_factory=list)
    worse_at: List[str] = Field(default_factory=list)
    price_difference: float = 0.0
    value_assessment: str = ""


class ComparedProduct(RetrievedProduct):
    """Product with comparison context."""

    comparison: Optional[ProductComparison] = None
    is_primary_recommendation: bool = False


class ComparisonResponse(BaseModel):
    """Response containing product comparison."""

    primary_product: ComparedProduct
    alternative_product: ComparedProduct
    comparison_summary: str
    recommendation_reasoning: str


class ChatMessage(BaseModel):
    """Single message within a session."""

    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    id: Optional[str] = None


class ChatRequest(BaseModel):
    """Request body for the chat REST endpoint."""

    session_id: str
    message: str
    user_preferences: Optional[Dict[str, Any]] = None


class ChatResponseMetadata(BaseModel):
    """Diagnostic metadata returned with chat responses."""

    retrieval_latency_ms: Optional[float] = None
    llm_latency_ms: Optional[float] = None
    top_k: int
    applied_filters: Dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    """Response body returned to the frontend."""

    reply: str
    products_shown: List[RetrievedProduct] = Field(default_factory=list)
    reasoning: Optional[str] = None
    metadata: ChatResponseMetadata
    comparison: Optional[ComparisonResponse] = None


class FeedbackRequest(BaseModel):
    """User feedback on a single message."""

    session_id: str
    message_id: str
    feedback: Literal["positive", "negative"]


class SessionHistoryResponse(BaseModel):
    """Stored conversation history for a session."""

    session_id: str
    messages: List[ChatMessage]


class SessionMetrics(BaseModel):
    """Metrics tracked per conversation session."""

    session_id: str
    turn_count: int
    retrieval_latency_ms: float
    llm_latency_ms: float
    recommended_products: List[str]
    user_feedback: Dict[str, Literal["positive", "negative"]] = Field(default_factory=dict)
    started_at: datetime
    updated_at: datetime


class AggregateMetrics(BaseModel):
    """Aggregated analytics over all sessions."""

    total_sessions: int
    average_turns: float
    average_retrieval_latency_ms: float
    average_llm_latency_ms: float
    most_recommended_products: List[str]
    positive_feedback_ratio: Optional[float]


class ConversationFeedback(BaseModel):
    """User feedback for a complete conversation."""

    session_id: str
    rating: int = Field(ge=1, le=5)  # 1-5 stars
    comment: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    feedback_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    products_recommended: List[str] = Field(default_factory=list)


class FeedbackSubmitRequest(BaseModel):
    """Request body for submitting conversation feedback."""

    session_id: str
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = None


class ConversationSummary(BaseModel):
    """Summary of a past conversation with feedback."""

    session_id: str
    started_at: datetime
    updated_at: datetime
    message_count: int
    products_recommended: List[str]
    feedback: Optional[ConversationFeedback] = None
    first_user_message: Optional[str] = None
