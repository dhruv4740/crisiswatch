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
    # Side-by-side comparison
    side_by_side: Optional["SideBySideComparison"] = Field(
        default=None, description="Side-by-side comparison of claim vs facts"
    )
    # Why False explanation
    misinformation_analysis: Optional["MisinformationAnalysis"] = Field(
        default=None, description="Analysis of misinformation tactics used"
    )
    checked_at: datetime = Field(default_factory=datetime.now)
    processing_time_seconds: float = Field(
        default=0.0, description="Time taken to process the claim"
    )


class SideBySideComparison(BaseModel):
    """Side-by-side comparison of claim vs verified facts."""
    claim_points: list[str] = Field(description="Key points from the claim")
    fact_points: list[str] = Field(description="Corresponding verified facts")
    discrepancies: list[str] = Field(description="Specific discrepancies identified")


class MisinformationTactic(BaseModel):
    """A misinformation tactic detected in the claim."""
    name: str = Field(description="Name of the tactic")
    description: str = Field(description="What this tactic means")
    detected_example: str = Field(description="Example from the claim")


class MisinformationAnalysis(BaseModel):
    """Analysis of why a claim is false/misleading."""
    primary_issue: str = Field(description="The main reason the claim is false")
    tactics_detected: list[MisinformationTactic] = Field(
        default_factory=list, description="Misinformation tactics identified"
    )
    context_missing: list[str] = Field(
        default_factory=list, description="Important context that was omitted"
    )
    manipulation_techniques: list[str] = Field(
        default_factory=list, description="Emotional/psychological manipulation techniques"
    )


# Common misinformation tactics database
MISINFORMATION_TACTICS = {
    "gish_gallop": {
        "name": "Gish Gallop",
        "description": "Overwhelming with numerous weak arguments that are time-consuming to refute"
    },
    "cherry_picking": {
        "name": "Cherry Picking",
        "description": "Selecting only evidence that supports the claim while ignoring contradicting evidence"
    },
    "appeal_to_emotion": {
        "name": "Appeal to Emotion",
        "description": "Using emotional language to override rational thinking"
    },
    "false_authority": {
        "name": "False Authority",
        "description": "Citing unqualified sources as experts"
    },
    "strawman": {
        "name": "Strawman Argument",
        "description": "Misrepresenting an opposing view to make it easier to attack"
    },
    "out_of_context": {
        "name": "Out of Context",
        "description": "Quotes or statistics taken out of their original context"
    },
    "outdated_info": {
        "name": "Outdated Information",
        "description": "Using old information as if it's current"
    },
    "exaggeration": {
        "name": "Exaggeration",
        "description": "Overstating facts or statistics to make them more alarming"
    },
    "false_causation": {
        "name": "False Causation",
        "description": "Claiming one event caused another without evidence (correlation ≠ causation)"
    },
    "missing_context": {
        "name": "Missing Context",
        "description": "Omitting crucial details that would change the interpretation"
    }
}


class SearchResult(BaseModel):
    """Result from a search tool."""
    title: str = Field(description="Title of the result")
    url: str = Field(description="URL of the result")
    snippet: str = Field(description="Text snippet from the result")
    source: str = Field(description="Source of the result (e.g., 'tavily', 'newsapi')")
    published_date: Optional[str] = Field(default=None, description="Publication date if available")

