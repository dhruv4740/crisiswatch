"""
Node functions for the CrisisWatch fact-checking workflow.
"""

import json
import asyncio
from typing import Any, AsyncGenerator, Callable, Optional
from urllib.parse import urlparse
from graph.state import FactCheckState
from graph.prompts import (
    CLAIM_EXTRACTION_PROMPT,
    EVIDENCE_SYNTHESIS_PROMPT,
    EXPLANATION_GENERATION_PROMPT_EN,
    EXPLANATION_GENERATION_PROMPT_HI,
    SEARCH_QUERY_GENERATION_PROMPT,
    MISINFO_PATTERNS,
)
from models.schemas import Claim, Evidence, SearchResult, VerdictType, SeverityLevel
from agents.llm_providers import LLMManager
from tools import TavilySearchTool, GoogleFactCheckTool, NewsAPITool, WikipediaTool
from tools import AggregatedFactCheckTool  # New: Snopes, PolitiFact, etc.
from services.reliability import get_reliability_score, calculate_source_diversity
from services.confidence import calibrate_confidence, calibrate_verdict


# Source display names for SSE events
SOURCE_DISPLAY_NAMES = {
    "tavily": "Web Search",
    "tavily_secondary": "Extended Web Search", 
    "factcheck": "Google Fact Check",
    "news": "NewsAPI",
    "wikipedia": "Wikipedia",
    "factcheck_aggregator": "Fact-Checkers",
    "snopes": "Snopes",
    "politifact": "PolitiFact",
    "fullfact": "Full Fact",
    "afp_factcheck": "AFP Fact Check",
    "reuters_factcheck": "Reuters",
}


# Initialize shared resources
llm_manager = LLMManager()
tavily_tool = TavilySearchTool()
factcheck_tool = GoogleFactCheckTool()
news_tool = NewsAPITool()
wikipedia_tool = WikipediaTool()
aggregated_factcheck_tool = AggregatedFactCheckTool()  # New!


def _extract_domain(url: str) -> str:
    """Extract domain from URL for deduplication."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        # Remove www prefix
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except:
        return ""


def _deduplicate_results(results: list[SearchResult], max_per_domain: int = 2) -> list[SearchResult]:
    """
    Deduplicate search results by domain and content similarity.
    
    Args:
        results: List of SearchResult objects
        max_per_domain: Maximum results to keep per domain
        
    Returns:
        Deduplicated list of SearchResult objects
    """
    domain_counts: dict[str, int] = {}
    seen_snippets: set[str] = set()
    deduplicated = []
    
    for result in results:
        domain = _extract_domain(result.url)
        
        # Skip if we've seen too many from this domain
        if domain and domain_counts.get(domain, 0) >= max_per_domain:
            continue
        
        # Skip if snippet is too similar to one we've seen
        snippet_key = result.snippet[:100].lower().strip()
        if snippet_key in seen_snippets:
            continue
        
        deduplicated.append(result)
        domain_counts[domain] = domain_counts.get(domain, 0) + 1
        seen_snippets.add(snippet_key)
    
    return deduplicated


def _rank_by_reliability(results: list[SearchResult]) -> list[SearchResult]:
    """
    Rank search results by source reliability score.
    
    Args:
        results: List of SearchResult objects
        
    Returns:
        Sorted list with highest reliability first
    """
    def get_score(result: SearchResult) -> float:
        tool_source = result.source.split(":")[0] if ":" in result.source else result.source
        score, _ = get_reliability_score(
            url=result.url,
            source_name=result.title,
            tool_source=tool_source,
        )
        return score
    
    return sorted(results, key=get_score, reverse=True)


def _parse_json_response(text: str) -> dict:
    """Parse JSON from LLM response, handling common issues."""
    if not text:
        return {}
        
    # Try to find JSON in the response
    text = text.strip()
    
    # Handle markdown code blocks
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        parts = text.split("```")
        if len(parts) >= 2:
            text = parts[1]
            # If it starts with a language identifier, skip to next line
            if text.startswith(("json", "JSON")):
                text = text[4:].strip()
    
    text = text.strip()
    
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object in text
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
        return {}


async def extract_claim(state: FactCheckState) -> dict[str, Any]:
    """Extract and parse the claim from raw input."""
    raw_input = state["raw_input"]
    language = state.get("language", "en")
    
    # Quick validation - if input is too short, just use it directly
    if len(raw_input.strip()) < 10:
        return {
            "claim": Claim(text=raw_input.strip(), language=language),
            "error": None,
        }
    
    try:
        prompt = CLAIM_EXTRACTION_PROMPT.format(text=raw_input)
        response = await llm_manager.generate(
            prompt=prompt,
            system_prompt="You are a fact-checking assistant. Always respond with valid JSON. Be generous - most claims can be fact-checked.",
            temperature=0.3,
        )
        
        parsed = _parse_json_response(response)
        
        # Only reject if explicitly marked as not checkworthy AND we have a good reason
        if parsed.get("is_checkworthy") == False and "opinion" in parsed.get("reason", "").lower():
            return {
                "claim": None,
                "error": f"Claim not checkworthy: {parsed.get('reason', 'Not a verifiable factual claim')}",
            }
        
        # Use extracted claim or fall back to raw input
        main_claim = parsed.get("main_claim") or raw_input
        
        claim = Claim(
            text=main_claim,
            language=language,
            crisis_type=parsed.get("crisis_type"),
            extracted_entities=parsed.get("entities", []),
        )
        
        return {"claim": claim, "error": None}
        
    except Exception as e:
        import traceback
        print(f"[extract_claim] Error: {e}")
        print(traceback.format_exc())
        # Fallback: use raw input as claim
        return {
            "claim": Claim(text=raw_input, language=language),
            "error": None,
        }


async def generate_search_queries(state: FactCheckState) -> dict[str, Any]:
    """
    Generate optimized search queries for the claim.
    
    Optimization: Skip LLM call for simple claims (short, few entities)
    to save ~3s of processing time.
    """
    claim = state["claim"]
    if not claim:
        return {"_search_queries": []}
    
    # Optimization: Skip LLM for simple claims
    # Simple = short text (<100 chars) or few entities (<3)
    entities = getattr(claim, 'extracted_entities', []) or []
    is_simple = len(claim.text) < 100 or len(entities) < 3
    
    if is_simple:
        # Generate basic queries without LLM
        base_query = claim.text
        queries = [
            base_query,
            f"{base_query} fact check",
            f"{base_query} true or false",
        ]
        # Add entity-based query if we have entities
        if entities:
            queries.append(f"{' '.join(entities[:3])} news")
        return {"_search_queries": queries}
    
    try:
        prompt = SEARCH_QUERY_GENERATION_PROMPT.format(claim=claim.text)
        response = await llm_manager.generate(
            prompt=prompt,
            system_prompt="You are a research assistant. Always respond with valid JSON.",
            temperature=0.5,
        )
        
        parsed = _parse_json_response(response)
        queries = [q["query"] for q in parsed.get("queries", [])]
        
        if not queries:
            # Fallback to using the claim text directly
            queries = [claim.text]
        
        return {"_search_queries": queries}
        
    except Exception:
        return {"_search_queries": [claim.text]}


async def search_sources(state: FactCheckState) -> dict[str, Any]:
    """
    Search multiple sources for evidence in parallel.
    
    Optimizations:
    - Parallel execution with asyncio.gather()
    - Multiple queries for broader coverage
    - Deduplication by domain and content
    - Reliability-based ranking
    """
    claim = state["claim"]
    if not claim:
        return {"search_results": [], "sources_checked": 0, "source_diversity": 0.0}
    
    # Get search queries (generated in previous step or use claim text)
    queries = state.get("_search_queries", [claim.text])
    primary_query = queries[0] if queries else claim.text
    secondary_query = queries[1] if len(queries) > 1 else None
    language = state.get("language", "en")
    
    all_results: list[SearchResult] = []
    sources_checked = 0
    
    # Build parallel task list with increased search depth
    tasks = []
    
    # Tavily web search - primary query with 5 results
    if tavily_tool.is_available:
        tasks.append(("tavily", tavily_tool.search(primary_query, max_results=5, search_depth="advanced")))
        sources_checked += 1
        # Also search secondary query if available
        if secondary_query:
            tasks.append(("tavily_secondary", tavily_tool.search(secondary_query, max_results=3)))
    
    # Google Fact Check - critical for existing fact-checks
    if factcheck_tool.is_available:
        tasks.append(("factcheck", factcheck_tool.search(primary_query, language_code=language, max_results=10)))
        sources_checked += 1
    
    # NEW: Aggregated fact-checkers (Snopes, PolitiFact, Full Fact, AFP, Reuters)
    tasks.append(("factcheck_aggregator", aggregated_factcheck_tool.search(primary_query, max_results_per_source=2)))
    sources_checked += 5  # Count all 5 fact-checkers
    
    # NewsAPI - increased to 5 articles
    if news_tool.is_available:
        tasks.append(("news", news_tool.search(primary_query, language=language, max_results=5, sort_by="relevancy")))
        sources_checked += 1
    
    # Wikipedia - primary search with 5 results
    tasks.append(("wikipedia", wikipedia_tool.search(primary_query, language=language, max_results=5)))
    sources_checked += 1
    
    # Execute ALL searches in parallel for maximum speed
    if tasks:
        results = await asyncio.gather(*[t[1] for t in tasks], return_exceptions=True)
        
        for (source_name, _), result in zip(tasks, results):
            if isinstance(result, Exception):
                print(f"Search error ({source_name}): {result}")
            elif result:
                all_results.extend(result)
    
    # Post-processing: deduplicate and rank
    deduplicated = _deduplicate_results(all_results, max_per_domain=3)
    ranked = _rank_by_reliability(deduplicated)
    
    # Calculate source diversity score
    diversity_score = calculate_source_diversity(ranked)
    
    return {
        "search_results": ranked,
        "sources_checked": len(ranked),  # Fixed: count actual results, not tool availability
        "source_diversity": diversity_score,
        "_raw_results_count": len(all_results),
        "_deduplicated_count": len(deduplicated),
    }


async def search_sources_streaming(
    state: FactCheckState,
    emit_event: Callable[[str, str, int], None],
) -> dict[str, Any]:
    """
    Search multiple sources with SSE event emission for live progress display.
    
    Args:
        state: The fact-check state
        emit_event: Callback to emit SSE events (source_name, status, count)
    
    Emits events like:
        ("Web Search", "searching", 0)
        ("Web Search", "found", 5)
    """
    claim = state["claim"]
    if not claim:
        return {"search_results": [], "sources_checked": 0, "source_diversity": 0.0}
    
    queries = state.get("_search_queries", [claim.text])
    primary_query = queries[0] if queries else claim.text
    secondary_query = queries[1] if len(queries) > 1 else None
    language = state.get("language", "en")
    
    all_results: list[SearchResult] = []
    
    # Define sources with their search functions
    sources = []
    
    if tavily_tool.is_available:
        sources.append(("tavily", lambda: tavily_tool.search(primary_query, max_results=5, search_depth="advanced")))
        if secondary_query:
            sources.append(("tavily_secondary", lambda q=secondary_query: tavily_tool.search(q, max_results=3)))
    
    if factcheck_tool.is_available:
        sources.append(("factcheck", lambda: factcheck_tool.search(primary_query, language_code=language, max_results=10)))
    
    # NEW: Aggregated fact-checkers
    sources.append(("factcheck_aggregator", lambda: aggregated_factcheck_tool.search(primary_query, max_results_per_source=2)))
    
    if news_tool.is_available:
        sources.append(("news", lambda: news_tool.search(primary_query, language=language, max_results=5, sort_by="relevancy")))
    
    sources.append(("wikipedia", lambda: wikipedia_tool.search(primary_query, language=language, max_results=5)))
    
    # Search each source sequentially to emit events (still fast enough)
    for source_key, search_fn in sources:
        display_name = SOURCE_DISPLAY_NAMES.get(source_key, source_key)
        
        # Emit "searching" event
        emit_event(display_name, "searching", 0)
        
        try:
            results = await search_fn()
            count = len(results) if results else 0
            if results:
                all_results.extend(results)
            # Emit "found" event
            emit_event(display_name, "found", count)
        except Exception as e:
            print(f"Search error ({source_key}): {e}")
            emit_event(display_name, "error", 0)
    
    # Post-processing
    deduplicated = _deduplicate_results(all_results, max_per_domain=3)
    ranked = _rank_by_reliability(deduplicated)
    diversity_score = calculate_source_diversity(ranked)
    
    return {
        "search_results": ranked,
        "sources_checked": len(ranked),
        "source_diversity": diversity_score,
        "_raw_results_count": len(all_results),
        "_deduplicated_count": len(deduplicated),
    }


async def synthesize_evidence(state: FactCheckState) -> dict[str, Any]:
    """
    Synthesize search results into evidence and determine verdict.
    
    Optimizations:
    - Limit to top 10 most reliable sources for faster LLM processing
    - Include reliability scores in evidence formatting
    - Track source diversity in reasoning
    """
    claim = state["claim"]
    search_results = state.get("search_results", [])
    source_diversity = state.get("source_diversity", 0.0)
    
    if not claim:
        return {
            "evidence": [],
            "verdict": VerdictType.UNVERIFIABLE,
            "confidence": 0.0,
            "severity": SeverityLevel.LOW,
            "source_diversity": 0.0,
        }
    
    if not search_results:
        return {
            "evidence": [],
            "verdict": VerdictType.UNVERIFIABLE,
            "confidence": 0.3,
            "severity": SeverityLevel.MEDIUM,
            "source_diversity": 0.0,
        }
    
    # Limit to top 10 most reliable sources for faster LLM processing
    # (already ranked by reliability in search_sources)
    top_results = search_results[:10]
    
    # Format evidence with reliability scores for the prompt
    evidence_text = ""
    for i, result in enumerate(top_results, 1):
        tool_source = result.source.split(":")[0] if ":" in result.source else result.source
        reliability, source_type = get_reliability_score(
            url=result.url,
            source_name=result.title,
            tool_source=tool_source,
        )
        evidence_text += f"\n{i}. [{result.source}] {result.title} (Reliability: {reliability:.0%}, Type: {source_type})\n"
        evidence_text += f"   URL: {result.url}\n"
        evidence_text += f"   Content: {result.snippet[:350]}...\n"
    
    try:
        prompt = EVIDENCE_SYNTHESIS_PROMPT.format(
            claim=claim.text,
            evidence=evidence_text,
            source_count=len(top_results),
            diversity_score=source_diversity,
            misinfo_patterns=MISINFO_PATTERNS,
        )
        
        response = await llm_manager.generate(
            prompt=prompt,
            system_prompt="You are an expert fact-checker. Analyze evidence objectively and respond with valid JSON. Consider source reliability scores when weighing evidence.",
            temperature=0.3,
        )
        
        parsed = _parse_json_response(response)
        
        # Parse verdict
        verdict_str = parsed.get("verdict", "unverifiable").lower()
        verdict_map = {
            "false": VerdictType.FALSE,
            "mostly_false": VerdictType.MOSTLY_FALSE,
            "mixed": VerdictType.MIXED,
            "mostly_true": VerdictType.MOSTLY_TRUE,
            "true": VerdictType.TRUE,
            "unverifiable": VerdictType.UNVERIFIABLE,
        }
        verdict = verdict_map.get(verdict_str, VerdictType.UNVERIFIABLE)
        
        # Parse severity
        severity_str = parsed.get("severity", "medium").lower()
        severity_map = {
            "critical": SeverityLevel.CRITICAL,
            "high": SeverityLevel.HIGH,
            "medium": SeverityLevel.MEDIUM,
            "low": SeverityLevel.LOW,
        }
        severity = severity_map.get(severity_str, SeverityLevel.MEDIUM)
        
        # Build evidence list with reliability scoring
        evidence_list = []
        key_findings = parsed.get("key_findings", [])
        
        if key_findings and len(key_findings) > 0:
            for finding in key_findings:
                source_name = finding.get("source", "Unknown")
                # Try to find matching search result for URL and published_date
                source_url = None
                published_date = None
                for sr in search_results:
                    if source_name.lower() in sr.title.lower() or source_name.lower() in sr.source.lower():
                        source_url = sr.url
                        published_date = sr.published_date
                        break
                
                # Get reliability score
                reliability, source_type = get_reliability_score(
                    url=source_url or "",
                    source_name=source_name,
                    tool_source="web",
                )
                
                evidence_list.append(Evidence(
                    source_name=source_name,
                    source_type=source_type,
                    source_url=source_url,
                    snippet=finding.get("finding", ""),
                    stance=finding.get("stance", "neutral"),
                    reliability_score=reliability,
                    published_date=published_date,
                ))
        else:
            # Fallback: Create evidence directly from search results if LLM didn't provide key_findings
            for sr in search_results[:5]:  # Limit to top 5
                tool_source = sr.source.split(":")[0] if ":" in sr.source else sr.source
                reliability, source_type = get_reliability_score(
                    url=sr.url,
                    source_name=sr.title,
                    tool_source=tool_source,
                )
                evidence_list.append(Evidence(
                    source_name=sr.title[:50] if sr.title else sr.source,
                    source_type=source_type,
                    source_url=sr.url,
                    snippet=sr.snippet[:300] if sr.snippet else "",
                    stance="neutral",  # We don't know stance without LLM analysis
                    reliability_score=reliability,
                    published_date=sr.published_date,
                ))
        
        # Calibrate confidence based on evidence patterns
        base_confidence = float(parsed.get("confidence", 0.5))
        calibrated_confidence, calibration_reason = calibrate_confidence(
            base_confidence=base_confidence,
            verdict=verdict,
            evidence=evidence_list,
            claim_text=claim.text,  # Pass claim text (string) for pseudoscience pattern detection
        )
        
        # Calibrate verdict based on confidence (upgrade mostly_X to X if confidence is high)
        calibrated_verdict, verdict_reason = calibrate_verdict(verdict, calibrated_confidence)
        
        # Calculate overall reliability score (average of evidence)
        overall_reliability = 0.0
        if evidence_list:
            overall_reliability = sum(e.reliability_score for e in evidence_list) / len(evidence_list)
        
        return {
            "evidence": evidence_list,
            "verdict": calibrated_verdict,
            "confidence": calibrated_confidence,
            "severity": severity,
            "source_diversity": source_diversity,
            "overall_reliability": overall_reliability,
            "_reasoning": parsed.get("reasoning", "") + f" [Calibration: {calibration_reason}] [Verdict: {verdict_reason}]",
        }
        
    except Exception as e:
        print(f"Evidence synthesis error: {e}")
        
        # Fallback: Create evidence directly from search results even on error
        evidence_list = []
        for sr in search_results[:5]:
            tool_source = sr.source.split(":")[0] if ":" in sr.source else sr.source
            reliability, source_type = get_reliability_score(
                url=sr.url,
                source_name=sr.title,
                tool_source=tool_source,
            )
            evidence_list.append(Evidence(
                source_name=sr.title[:50] if sr.title else sr.source,
                source_type=source_type,
                source_url=sr.url,
                snippet=sr.snippet[:300] if sr.snippet else "",
                stance="neutral",
                reliability_score=reliability,
                published_date=sr.published_date,
            ))
        
        overall_reliability = 0.0
        if evidence_list:
            overall_reliability = sum(e.reliability_score for e in evidence_list) / len(evidence_list)
        
        return {
            "evidence": evidence_list,
            "verdict": VerdictType.UNVERIFIABLE,
            "confidence": 0.3,
            "severity": SeverityLevel.MEDIUM,
            "overall_reliability": overall_reliability,
            "source_diversity": source_diversity,
            "_reasoning": f"Error during analysis: {str(e)}",
        }


async def generate_explanation(state: FactCheckState) -> dict[str, Any]:
    """
    Generate human-readable explanation and correction.
    
    Optimization: Runs English and Hindi explanation generation in parallel
    to reduce total latency by ~50% for bilingual output.
    """
    claim = state["claim"]
    verdict = state.get("verdict", VerdictType.UNVERIFIABLE)
    confidence = state.get("confidence", 0.5)
    severity = state.get("severity", SeverityLevel.MEDIUM)
    evidence = state.get("evidence", [])
    reasoning = state.get("_reasoning", "")
    language = state.get("language", "en")
    
    if not claim:
        return {
            "explanation": "Unable to process the claim.",
            "explanation_hindi": "दावे को संसाधित करने में असमर्थ।",
            "correction": None,
        }
    
    # Format evidence for prompt
    evidence_text = ""
    for e in evidence[:5]:
        evidence_text += f"- {e.source_name}: {e.snippet} (Stance: {e.stance})\n"
    
    if not evidence_text:
        evidence_text = "Limited evidence found."
    
    # Build prompt parameters
    prompt_params = {
        "claim": claim.text,
        "verdict": verdict.value,
        "confidence": int(confidence * 100),
        "severity": severity.value,
        "evidence": evidence_text,
        "reasoning": reasoning,
    }
    
    async def generate_english() -> dict:
        """Generate English explanation."""
        try:
            prompt = EXPLANATION_GENERATION_PROMPT_EN.format(**prompt_params)
            response = await llm_manager.generate(
                prompt=prompt,
                system_prompt="You are a crisis communication expert. Generate clear, helpful explanations. Respond with valid JSON.",
                temperature=0.5,
            )
            return _parse_json_response(response)
        except Exception as e:
            print(f"English explanation error: {e}")
            return {}
    
    async def generate_hindi() -> dict:
        """Generate Hindi explanation."""
        try:
            prompt = EXPLANATION_GENERATION_PROMPT_HI.format(**prompt_params)
            response = await llm_manager.generate(
                prompt=prompt,
                system_prompt="आप एक संकट संचार विशेषज्ञ हैं। हिंदी में स्पष्ट, सहायक व्याख्याएं उत्पन्न करें। JSON में जवाब दें।",
                temperature=0.5,
            )
            return _parse_json_response(response)
        except Exception as e:
            print(f"Hindi explanation error: {e}")
            return {}
    
    try:
        # Run English and Hindi generation in parallel
        english_result, hindi_result = await asyncio.gather(
            generate_english(),
            generate_hindi(),
        )
        
        explanation = english_result.get("explanation", f"This claim has been rated as {verdict.value}.")
        correction = english_result.get("correction")
        explanation_hindi = hindi_result.get("explanation_hindi")
        
        return {
            "explanation": explanation,
            "explanation_hindi": explanation_hindi,
            "correction": correction,
        }
        
    except Exception as e:
        print(f"Explanation generation error: {e}")
        return {
            "explanation": f"This claim has been rated as {verdict.value} with {int(confidence * 100)}% confidence.",
            "explanation_hindi": None,
            "correction": None,
        }





