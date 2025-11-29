"""
Pydantic models for CrisisWatch data structures.
"""

from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import datetime
from enum import Enum


class SeverityLevel(str, Enum):
    """Severity level of misinformation."""
    CRITICAL = "critical"  # Life-threatening (fake evacuation routes, dangerous remedies)
    HIGH = "high"  # Causes panic or undermines emergency response
    MEDIUM = "medium"  # Misleading but not immediately dangerous
    LOW = "low"  # Minor inaccuracies


class VerdictType(str, Enum):
    """Verdict classification for a claim."""
    FALSE = "false"
    MOSTLY_FALSE = "mostly_false"
    MIXED = "mixed"
    MOSTLY_TRUE = "mostly_true"
    TRUE = "true"
    UNVERIFIABLE = "unverifiable"


class Evidence(BaseModel):
    """A piece of evidence found during fact-checking."""
    source_name: str = Field(description="Name of the source (e.g., 'WHO', 'Reuters')")
    source_url: Optional[str] = Field(default=None, description="URL of the source")
    source_type: Literal["fact_check", "news", "official", "wikipedia", "web"] = Field(
        description="Type of source"
    )
    snippet: str = Field(description="Relevant text snippet from the source")
    stance: Literal["supports", "refutes", "neutral"] = Field(
        description="Whether this evidence supports or refutes the claim"
    )
    reliability_score: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Reliability score of the source (0-1)"
    )
    published_date: Optional[str] = Field(default=None, description="Publication date of the source")
    retrieved_at: datetime = Field(default_factory=datetime.now)


class Claim(BaseModel):
    """A claim to be fact-checked."""
    text: str = Field(description="The claim text to verify")
    source: Optional[str] = Field(default=None, description="Where the claim originated")
    language: Literal["en", "hi"] = Field(default="en", description="Language of the claim")
    crisis_type: Optional[str] = Field(
        default=None, description="Type of crisis (earthquake, flood, health, etc.)"
    )
    extracted_entities: list[str] = Field(
        default_factory=list, description="Named entities extracted from the claim"
    )


class FactCheckResult(BaseModel):
    """Result of fact-checking a claim."""
    claim: Claim = Field(description="The original claim")
    verdict: VerdictType = Field(description="Final verdict on the claim")
    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence score for the verdict (0-1)"
    )
    severity: SeverityLevel = Field(description="Severity level of the misinformation")
    explanation: str = Field(description="Human-readable explanation of the verdict")
    explanation_hindi: Optional[str] = Field(
        default=None, description="Hindi translation of the explanation"
    )
    evidence: list[Evidence] = Field(
        default_factory=list, description="Evidence collected during fact-checking"
    )
    correction: Optional[str] = Field(
        default=None, description="Suggested correction to share"
    )
    sources_checked: int = Field(default=0, description="Number of sources checked")
    # New reliability and diversity fields
    overall_reliability: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Average reliability score of evidence sources"
    )
    source_diversity: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Source diversity score"
    )
    checked_at: datetime = Field(default_factory=datetime.now)
    processing_time_seconds: float = Field(
        default=0.0, description="Time taken to process the claim"
    )


class SearchResult(BaseModel):
    """Result from a search tool."""
    title: str = Field(description="Title of the result")
    url: str = Field(description="URL of the result")
    snippet: str = Field(description="Text snippet from the result")
    source: str = Field(description="Source of the result (e.g., 'tavily', 'newsapi')")
    published_date: Optional[str] = Field(default=None, description="Publication date if available")

