"""
CrisisWatch Fact-Checking Workflow
Main LangGraph workflow definition.
"""

from langgraph.graph import StateGraph, START, END
from graph.state import FactCheckState
from graph.nodes import (
    extract_claim,
    generate_search_queries,
    search_sources,
    synthesize_evidence,
    generate_explanation,
)


def should_continue_after_extraction(state: FactCheckState) -> str:
    """Determine if we should continue after claim extraction."""
    if state.get("error") or not state.get("claim"):
        return "end"
    return "continue"


def create_fact_check_workflow() -> StateGraph:
    """
    Create the fact-checking workflow graph.
    
    Workflow:
    1. extract_claim: Parse and validate the input claim
    2. generate_search_queries: Create optimized search queries
    3. search_sources: Search multiple sources in parallel
    4. synthesize_evidence: Analyze evidence and determine verdict
    5. generate_explanation: Create human-readable output
    
    Returns:
        Compiled LangGraph workflow
    """
    
    # Create the graph
    workflow = StateGraph(FactCheckState)
    
    # Add nodes
    workflow.add_node("extract_claim", extract_claim)
    workflow.add_node("generate_queries", generate_search_queries)
    workflow.add_node("search_sources", search_sources)
    workflow.add_node("synthesize_evidence", synthesize_evidence)
    workflow.add_node("generate_explanation", generate_explanation)
    
    # Add edges
    workflow.add_edge(START, "extract_claim")
    
    # Conditional edge after extraction
    workflow.add_conditional_edges(
        "extract_claim",
        should_continue_after_extraction,
        {
            "continue": "generate_queries",
            "end": END,
        }
    )
    
    workflow.add_edge("generate_queries", "search_sources")
    workflow.add_edge("search_sources", "synthesize_evidence")
    workflow.add_edge("synthesize_evidence", "generate_explanation")
    workflow.add_edge("generate_explanation", END)
    
    return workflow.compile()


# Create the compiled workflow
fact_check_agent = create_fact_check_workflow()
