"""
Pydantic models for the SHL Assessment Recommender API.
Defines request/response schemas and internal data structures.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime


# ============== Request/Response Models ==============

class Message(BaseModel):
    """Single message in conversation history."""
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    """Request body for POST /chat endpoint."""
    messages: List[Message] = Field(
        ...,
        description="Full conversation history (stateless, no server memory)"
    )


class Recommendation(BaseModel):
    """Single assessment recommendation."""
    name: str = Field(..., description="Assessment name from catalog")
    url: str = Field(..., description="Full URL to assessment in SHL catalog")
    test_type: str = Field(..., description="Test type: K (Knowledge), P (Personality), A (Ability)")


class ChatResponse(BaseModel):
    """Response body for POST /chat endpoint."""
    reply: str = Field(..., description="Agent's conversational response")
    recommendations: List[Recommendation] = Field(
        default_factory=list,
        description="1-10 recommendations when agent commits to shortlist; empty while clarifying"
    )
    end_of_conversation: bool = Field(
        default=False,
        description="True when agent considers task complete"
    )


# ============== Internal Data Models ==============

class Assessment(BaseModel):
    """Internal representation of an SHL assessment."""
    name: str
    url: str
    test_type: str  # K, P, A, or combined
    description: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    competencies: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    industries: List[str] = Field(default_factory=list)
    duration_minutes: Optional[int] = None


class QueryContext(BaseModel):
    """Extracted context from conversation for retrieval."""
    roles: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    seniority: Optional[str] = None  # junior, mid, senior, lead, executive
    assessment_types: List[str] = Field(default_factory=list)  # cognitive, personality, technical, skills
    stakeholder_interaction: Optional[bool] = None
    coding_required: Optional[bool] = None
    leadership: Optional[bool] = None
    communication: Optional[bool] = None
    job_description: Optional[str] = None


class RetrievalResult(BaseModel):
    """Result from retrieval pipeline."""
    assessment: Assessment
    semantic_score: float = 0.0
    keyword_score: float = 0.0
    combined_score: float = 0.0
    match_reasons: List[str] = Field(default_factory=list)


# ============== Agent State ==============

class AgentIntent(BaseModel):
    """Detected intent from user message."""
    intent_type: Literal[
        "recommend", "clarify", "refine", "compare", "greet", "off_topic", "unsafe"
    ]
    confidence: float = 1.0
    details: dict = Field(default_factory=dict)


class ConversationState(BaseModel):
    """State tracking for current conversation."""
    has_recommended: bool = False
    clarification_questions_asked: int = 0
    last_recommendations: List[Assessment] = Field(default_factory=list)
    context: QueryContext = Field(default_factory=QueryContext)