"""
CrisisWatch Fact-Check Workflow State
Defines the state schema for the LangGraph workflow.
"""

from typing import TypedDict, Optional, Annotated
from operator import add
from models.schemas import (
    Claim, Evidence, VerdictType, SeverityLevel, SearchResult,
    SideBySideComparison, MisinformationAnalysis
)


class FactCheckState(TypedDict):
    """State for the fact-checking workflow."""
    
    # Input
    raw_input: str  # Original user input
    language: str  # Detected or specified language ("en" or "hi")
    
    # Claim extraction
    claim: Optional[Claim]  # Parsed claim object
    
    # Search results (accumulated from all tools)
    search_results: Annotated[list[SearchResult], add]
    
    # Evidence synthesis
    evidence: list[Evidence]  # Synthesized evidence
    
    # Verdict
    verdict: Optional[VerdictType]
    confidence: float
    severity: Optional[SeverityLevel]
    
    # Output
    explanation: str
    explanation_hindi: Optional[str]
    correction: Optional[str]
    
    # New: Side-by-side comparison and misinformation analysis
    side_by_side: Optional[SideBySideComparison]
    misinformation_analysis: Optional[MisinformationAnalysis]
    
    # Metadata
    sources_checked: int
    error: Optional[str]
