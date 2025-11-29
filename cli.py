"""
Simple CLI runner for CrisisWatch workflow.
Run locally to test claim verification pipeline.
"""

import asyncio
import time
import json
from typing import Optional

import typer
from config import get_settings
from models.schemas import Claim, FactCheckResult, Evidence, VerdictType
from graph.nodes import (
    extract_claim,
    generate_search_queries,
    search_sources,
    synthesize_evidence,
    generate_explanation,
)

app = typer.Typer(add_completion=False)
settings = get_settings()


async def run_pipeline(raw_input: str, language: str = "en") -> FactCheckResult:
    state = {
        "raw_input": raw_input,
        "language": language,
        "claim": None,
        "search_results": [],
        "evidence": [],
        "verdict": None,
        "confidence": 0.0,
        "severity": None,
        "explanation": "",
        "explanation_hindi": None,
        "correction": None,
        "sources_checked": 0,
        "error": None,
    }

    start_time = time.time()

    # 1) Extract claim
    res = await extract_claim(state)
    state.update({k: v for k, v in res.items() if k in res})
    if res.get("error"):
        state["error"] = res.get("error")

    # Use the extracted claim
    claim_obj = state.get("claim")

    # 2) Generate search queries
    res = await generate_search_queries(state)
    if res.get("_search_queries"):
        state["_search_queries"] = res.get("_search_queries")

    # 3) Search sources
    res = await search_sources(state)
    state["search_results"] = res.get("search_results", [])
    state["sources_checked"] = res.get("sources_checked", 0)

    # 4) Synthesize evidence
    res = await synthesize_evidence(state)
    state["evidence"] = res.get("evidence", [])
    state["verdict"] = res.get("verdict")
    state["confidence"] = res.get("confidence", 0.0)
    state["severity"] = res.get("severity")
    state["_reasoning"] = res.get("_reasoning", "")

    # 5) Generate explanation
    res = await generate_explanation(state)
    state["explanation"] = res.get("explanation")
    state["explanation_hindi"] = res.get("explanation_hindi")
    state["correction"] = res.get("correction")

    end_time = time.time()

    # Build FactCheckResult
    # If claim_obj is None, create simple Claim wrapper
    if claim_obj is None:
        claim_obj = Claim(text=raw_input, language=language)

    factcheck = FactCheckResult(
        claim=claim_obj,
        verdict=state.get("verdict") or VerdictType.UNVERIFIABLE,
        confidence=state.get("confidence", 0.0),
        severity=state.get("severity") or "medium",
        explanation=state.get("explanation", ""),
        explanation_hindi=state.get("explanation_hindi"),
        evidence=state.get("evidence", []),
        correction=state.get("correction"),
        sources_checked=state.get("sources_checked", 0),
        processing_time_seconds=round(end_time - start_time, 2),
    )

    return factcheck


@app.command("check")
def check_claim(
    claim: str = typer.Argument(..., help="Claim text to check"),
    language: str = typer.Option("en", "-l", "--language", help="Language code (en | hi)"),
):
    """Run the CrisisWatch pipeline on a claim."""
    print("=" * 60)
    print("🔍 CrisisWatch - Misinformation Detection Agent")
    print("=" * 60)
    print(f"Primary LLM: {settings.primary_llm}")
    print(f"Gemini configured: {settings.has_gemini}")
    print(f"Claim: {claim}")
    print("-" * 60)

    result = asyncio.run(run_pipeline(claim, language=language))

    # Pretty-print JSON
    print("\n📋 RESULT:")
    print(json.dumps(result.model_dump(), indent=2, default=str, ensure_ascii=False))


@app.command("interactive")
def interactive_mode():
    """Run CrisisWatch in interactive mode - enter claims one by one."""
    print("=" * 60)
    print("🔍 CrisisWatch - Interactive Mode")
    print("=" * 60)
    print(f"Primary LLM: {settings.primary_llm}")
    print("Type 'quit' or 'exit' to stop.\n")

    while True:
        claim = typer.prompt("Enter claim to check")
        if claim.lower() in ("quit", "exit"):
            print("Goodbye!")
            break

        result = asyncio.run(run_pipeline(claim))
        print("\n📋 RESULT:")
        print(json.dumps(result.model_dump(), indent=2, default=str, ensure_ascii=False))
        print("-" * 60)


if __name__ == "__main__":
    app()
