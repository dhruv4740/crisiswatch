"""
CrisisWatch FastAPI Application
RESTful API for real-time misinformation detection and fact-checking.
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from config import get_settings
from models.schemas import (
    Claim,
    FactCheckResult,
    Evidence,
    VerdictType,
    SeverityLevel,
)
from graph.nodes import (
    extract_claim,
    generate_search_queries,
    search_sources,
    search_sources_streaming,
    synthesize_evidence,
    generate_explanation,
)
from services.claim_store import get_claim_store
from services.reliability import get_reliability_score


# ============================================
# REQUEST/RESPONSE MODELS
# ============================================

class ClaimCheckRequest(BaseModel):
    """Request to check a single claim."""
    claim: str = Field(..., min_length=5, max_length=2000, description="The claim text to verify")
    language: str = Field(default="en", pattern="^(en|hi)$", description="Language code (en or hi)")
    skip_cache: bool = Field(default=False, description="Skip cache lookup and force fresh check")


class BatchCheckRequest(BaseModel):
    """Request to check multiple claims."""
    claims: list[str] = Field(..., min_items=1, max_items=20, description="List of claims to verify")
    language: str = Field(default="en", pattern="^(en|hi)$", description="Language code")
    skip_cache: bool = Field(default=False, description="Skip cache lookup")


class EvidenceItem(BaseModel):
    """Evidence item with reliability scoring."""
    source: str
    type: str
    snippet: str
    stance: str
    reliability: float = Field(description="Source reliability score 0-1")
    url: Optional[str] = None
    published_date: Optional[str] = None


class ClaimCheckResponse(BaseModel):
    """Response for a claim check."""
    claim_id: str
    claim_text: str
    verdict: str
    confidence: float
    severity: str
    explanation: str
    explanation_hindi: Optional[str] = None
    correction: Optional[str] = None
    sources_checked: int
    evidence: list[EvidenceItem]
    # New reliability and diversity fields
    overall_reliability: float = Field(default=0.0, description="Average reliability of evidence sources")
    source_diversity: float = Field(default=0.0, description="Diversity of sources 0-1")
    processing_time_seconds: float
    cached: bool = False


class BatchCheckResponse(BaseModel):
    """Response for batch claim check."""
    total_claims: int
    processed: int
    cached: int
    results: list[ClaimCheckResponse]
    total_processing_time_seconds: float


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: str
    version: str
    llm_available: bool
    search_tools: dict[str, bool]


class StatsResponse(BaseModel):
    """Statistics response."""
    total_claims_checked: int
    by_verdict: dict[str, int]
    by_severity: dict[str, int]
    cache_size: int


# ============================================
# PIPELINE RUNNER
# ============================================

async def run_factcheck_pipeline(
    raw_input: str,
    language: str = "en",
) -> tuple[FactCheckResult, float]:
    """
    Run the full fact-checking pipeline.
    
    Returns:
        Tuple of (FactCheckResult, processing_time_seconds)
    """
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
    state.update(res)
    
    if state.get("error") or not state.get("claim"):
        # Return early with error
        end_time = time.time()
        return FactCheckResult(
            claim=Claim(text=raw_input, language=language),
            verdict=VerdictType.UNVERIFIABLE,
            confidence=0.0,
            severity=SeverityLevel.LOW,
            explanation=state.get("error", "Unable to process claim"),
            sources_checked=0,
            processing_time_seconds=end_time - start_time,
        ), end_time - start_time
    
    # 2) Generate search queries
    res = await generate_search_queries(state)
    state.update(res)
    
    # 3) Search sources
    res = await search_sources(state)
    state.update(res)
    
    # 4) Synthesize evidence
    res = await synthesize_evidence(state)
    state.update(res)
    
    # 5) Generate explanation
    res = await generate_explanation(state)
    state.update(res)
    
    end_time = time.time()
    processing_time = end_time - start_time
    
    # Build result
    result = FactCheckResult(
        claim=state["claim"],
        verdict=state.get("verdict", VerdictType.UNVERIFIABLE),
        confidence=state.get("confidence", 0.0),
        severity=state.get("severity", SeverityLevel.MEDIUM),
        explanation=state.get("explanation", ""),
        explanation_hindi=state.get("explanation_hindi"),
        correction=state.get("correction"),
        evidence=state.get("evidence", []),
        sources_checked=state.get("sources_checked", 0),
        overall_reliability=state.get("overall_reliability", 0.0),
        source_diversity=state.get("source_diversity", 0.0),
        processing_time_seconds=processing_time,
    )
    
    return result, processing_time


# ============================================
# FASTAPI APP
# ============================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    print("🚀 CrisisWatch API starting up...")
    yield
    # Shutdown
    print("👋 CrisisWatch API shutting down...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    settings = get_settings()
    
    app = FastAPI(
        title="CrisisWatch API",
        description="Real-time misinformation detection and fact-checking for crisis events",
        version="1.0.0",
        lifespan=lifespan,
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    return app


app = create_app()


# ============================================
# ENDPOINTS
# ============================================

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {
        "name": "CrisisWatch API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/api/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Check API health and service availability."""
    from agents.llm_providers import LLMManager
    from tools import TavilySearchTool, GoogleFactCheckTool, NewsAPITool, WikipediaTool
    
    llm = LLMManager()
    
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="1.0.0",
        llm_available=llm.gemini.is_available,
        search_tools={
            "tavily": TavilySearchTool().is_available,
            "google_factcheck": GoogleFactCheckTool().is_available,
            "newsapi": NewsAPITool().is_available,
            "wikipedia": True,
        },
    )


@app.get("/api/stats", response_model=StatsResponse, tags=["Stats"])
async def get_stats():
    """Get fact-checking statistics."""
    store = get_claim_store()
    stats = store.get_stats()
    
    return StatsResponse(
        total_claims_checked=stats["total_claims"],
        by_verdict=stats["by_verdict"],
        by_severity=stats["by_severity"],
        cache_size=stats["total_claims"],
    )


@app.post("/api/check", response_model=ClaimCheckResponse, tags=["Fact-Check"])
async def check_claim(request: ClaimCheckRequest):
    """
    Check a single claim for misinformation.
    
    Returns verdict, confidence, severity, and explanation.
    """
    store = get_claim_store()
    
    # Check cache first
    if not request.skip_cache:
        cached = store.get(request.claim)
        if cached:
            return ClaimCheckResponse(
                claim_id=cached["claim_hash"],
                claim_text=request.claim,
                verdict=cached["verdict"],
                confidence=cached["confidence"],
                severity=cached["severity"],
                explanation=cached["explanation"],
                explanation_hindi=cached.get("explanation_hindi"),
                correction=cached.get("correction"),
                sources_checked=cached.get("sources_checked", 0),
                evidence=[],  # Cached results don't store full evidence
                overall_reliability=cached.get("overall_reliability", 0.0),
                source_diversity=cached.get("source_diversity", 0.0),
                processing_time_seconds=0.0,
                cached=True,
            )
    
    # Run fact-check pipeline
    try:
        result, processing_time = await run_factcheck_pipeline(
            raw_input=request.claim,
            language=request.language,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fact-check failed: {str(e)}")
    
    # Store result
    claim_id = store.store(request.claim, result)
    
    # Build response
    evidence_list = [
        {
            "source": e.source_name,
            "type": e.source_type,
            "snippet": e.snippet,
            "stance": e.stance,
            "reliability": e.reliability_score,
            "url": e.source_url,
            "published_date": e.published_date,
        }
        for e in result.evidence
    ]
    
    return ClaimCheckResponse(
        claim_id=claim_id,
        claim_text=request.claim,
        verdict=result.verdict.value,
        confidence=result.confidence,
        severity=result.severity.value,
        explanation=result.explanation,
        explanation_hindi=result.explanation_hindi,
        correction=result.correction,
        sources_checked=result.sources_checked,
        evidence=evidence_list,
        overall_reliability=result.overall_reliability,
        source_diversity=result.source_diversity,
        processing_time_seconds=processing_time,
        cached=False,
    )


@app.get("/api/check/stream", tags=["Fact-Check"])
async def check_claim_stream(
    claim: str = Query(..., min_length=5, max_length=2000, description="The claim text to verify"),
    language: str = Query(default="en", pattern="^(en|hi)$", description="Language code (en or hi)"),
):
    """
    Check a claim with real-time progress streaming via Server-Sent Events (SSE).
    
    Returns a stream of progress events followed by the final result.
    
    Event types:
    - step: Pipeline stage progress (extracting, generating_queries, searching, synthesizing, explaining, complete)
    - source: Individual source search status (searching, found, error)
    - complete: Final result with full data
    - error: Error occurred
    """
    
    # Queue to collect events from the streaming search
    event_queue: asyncio.Queue = asyncio.Queue()
    
    async def generate_events() -> AsyncGenerator[str, None]:
        start_time = time.time()
        store = get_claim_store()
        total_sources_found = 0
        
        def send_event(event_type: str, data: dict) -> str:
            return f"data: {json.dumps({'type': event_type, **data})}\n\n"
        
        def emit_source_event(source_name: str, status: str, count: int):
            """Callback for streaming search to emit source events."""
            nonlocal total_sources_found
            if status == "found":
                total_sources_found += count
            event_queue.put_nowait({
                "source": source_name,
                "status": status,
                "count": count,
                "total": total_sources_found,
            })
        
        try:
            # Step 1: Extract claim
            yield send_event("step", {"step": "extracting", "progress": 10, "message": "Analyzing claim..."})
            claim_obj = await extract_claim({"raw_input": claim})
            extracted_claim = claim_obj.get("claim")
            if not extracted_claim:
                yield send_event("error", {"message": "Failed to extract claim from input"})
                return
            
            # Step 2: Generate search queries
            yield send_event("step", {"step": "generating_queries", "progress": 20, "message": "Preparing search queries..."})
            queries_state = await generate_search_queries({"claim": extracted_claim})
            queries = queries_state.get("_search_queries", [extracted_claim.text])
            
            # Step 3: Search sources with streaming events
            yield send_event("step", {"step": "searching", "progress": 25, "message": "Starting source search..."})
            
            # Use streaming search that emits events
            search_task = asyncio.create_task(search_sources_streaming(
                {
                    "claim": extracted_claim,
                    "_search_queries": queries,
                    "language": language,
                },
                emit_source_event,
            ))
            
            # Process source events as they come in
            while not search_task.done():
                try:
                    # Wait for events with a short timeout
                    source_event = await asyncio.wait_for(event_queue.get(), timeout=0.1)
                    progress = 25 + min(35, source_event["total"] * 2)  # Scale progress 25-60
                    yield send_event("source", {
                        "source": source_event["source"],
                        "status": source_event["status"],
                        "count": source_event["count"],
                        "total": source_event["total"],
                        "progress": progress,
                    })
                except asyncio.TimeoutError:
                    continue
            
            # Get final search results
            search_state = await search_task
            results = search_state.get("search_results", [])
            
            # Drain any remaining events
            while not event_queue.empty():
                source_event = event_queue.get_nowait()
                yield send_event("source", {
                    "source": source_event["source"],
                    "status": source_event["status"],
                    "count": source_event["count"],
                    "total": source_event["total"],
                    "progress": 60,
                })
            
            yield send_event("step", {"step": "searching", "progress": 60, "message": f"Found {len(results)} sources"})
            
            # Step 4: Synthesize evidence
            yield send_event("step", {"step": "synthesizing", "progress": 70, "message": "Analyzing evidence..."})
            synthesis_state = await synthesize_evidence({
                "claim": extracted_claim,
                "search_results": results,
            })
            evidence = synthesis_state.get("evidence", [])
            verdict = synthesis_state.get("verdict")
            confidence = synthesis_state.get("confidence", 0.0)
            severity = synthesis_state.get("severity")
            overall_reliability = synthesis_state.get("overall_reliability", 0.0)
            source_diversity = synthesis_state.get("source_diversity", 0.0)
            
            # Step 5: Generate explanation
            yield send_event("step", {"step": "explaining", "progress": 85, "message": "Generating explanation..."})
            explanation_state = await generate_explanation({
                "claim": extracted_claim,
                "evidence": evidence,
                "verdict": verdict,
                "confidence": confidence,
                "severity": severity,
                "language": language,
            })
            explanation = explanation_state.get("explanation", "")
            explanation_hindi = explanation_state.get("explanation_hindi")
            correction = explanation_state.get("correction")
            
            # Build final result
            from models.schemas import FactCheckResult, VerdictType, SeverityLevel
            result = FactCheckResult(
                claim=extracted_claim,
                verdict=verdict if isinstance(verdict, VerdictType) else VerdictType(verdict),
                confidence=confidence,
                severity=severity if isinstance(severity, SeverityLevel) else SeverityLevel(severity),
                evidence=evidence,
                explanation=explanation,
                explanation_hindi=explanation_hindi,
                correction=correction,
                sources_checked=len(results),
                overall_reliability=overall_reliability,
                source_diversity=source_diversity,
            )
            
            # Store result
            claim_id = store.store(claim, result)
            processing_time = time.time() - start_time
            
            # Build response
            evidence_list = [
                {
                    "source": e.source_name,
                    "type": e.source_type,
                    "snippet": e.snippet,
                    "stance": e.stance,
                    "reliability": e.reliability_score,
                    "url": e.source_url,
                    "published_date": e.published_date,
                }
                for e in result.evidence
            ]
            
            final_result = {
                "claim_id": claim_id,
                "claim_text": claim,
                "verdict": result.verdict.value,
                "confidence": result.confidence,
                "severity": result.severity.value,
                "explanation": result.explanation,
                "explanation_hindi": result.explanation_hindi,
                "correction": result.correction,
                "sources_checked": result.sources_checked,
                "evidence": evidence_list,
                "overall_reliability": result.overall_reliability,
                "source_diversity": result.source_diversity,
                "processing_time_seconds": processing_time,
                "cached": False,
            }
            
            yield send_event("complete", {"progress": 100, "message": "Fact-check complete", "result": final_result})
            
        except Exception as e:
            yield send_event("error", {"message": f"Error during fact-check: {str(e)}"})
    
    return StreamingResponse(
        generate_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/check-batch", response_model=BatchCheckResponse, tags=["Fact-Check"])
async def check_claims_batch(request: BatchCheckRequest):
    """
    Check multiple claims for misinformation.
    
    Processes claims in parallel for efficiency.
    Limited to 20 claims per request.
    """
    store = get_claim_store()
    start_time = time.time()
    
    results: list[ClaimCheckResponse] = []
    cached_count = 0
    
    # Separate cached and new claims
    claims_to_process = []
    
    for claim_text in request.claims:
        if not request.skip_cache:
            cached = store.get(claim_text)
            if cached:
                results.append(ClaimCheckResponse(
                    claim_id=cached["claim_hash"],
                    claim_text=claim_text,
                    verdict=cached["verdict"],
                    confidence=cached["confidence"],
                    severity=cached["severity"],
                    explanation=cached["explanation"],
                    explanation_hindi=cached.get("explanation_hindi"),
                    correction=cached.get("correction"),
                    sources_checked=cached.get("sources_checked", 0),
                    evidence=[],
                    overall_reliability=cached.get("overall_reliability", 0.0),
                    source_diversity=cached.get("source_diversity", 0.0),
                    processing_time_seconds=0.0,
                    cached=True,
                ))
                cached_count += 1
                continue
        
        claims_to_process.append(claim_text)
    
    # Process remaining claims in parallel (limit concurrency)
    async def process_claim(claim_text: str) -> ClaimCheckResponse:
        try:
            result, proc_time = await run_factcheck_pipeline(
                raw_input=claim_text,
                language=request.language,
            )
            claim_id = store.store(claim_text, result)
            
            evidence_list = [
                {
                    "source": e.source_name,
                    "type": e.source_type,
                    "snippet": e.snippet,
                    "stance": e.stance,
                    "reliability": e.reliability_score,
                    "url": e.source_url,
            "published_date": e.published_date,
        }
                for e in result.evidence
            ]
            
            return ClaimCheckResponse(
                claim_id=claim_id,
                claim_text=claim_text,
                verdict=result.verdict.value,
                confidence=result.confidence,
                severity=result.severity.value,
                explanation=result.explanation,
                explanation_hindi=result.explanation_hindi,
                correction=result.correction,
                sources_checked=result.sources_checked,
                evidence=evidence_list,
                overall_reliability=result.overall_reliability,
                source_diversity=result.source_diversity,
                processing_time_seconds=proc_time,
                cached=False,
            )
        except Exception as e:
            # Return error result for failed claims
            return ClaimCheckResponse(
                claim_id="error",
                claim_text=claim_text,
                verdict="unverifiable",
                confidence=0.0,
                severity="low",
                explanation=f"Error processing claim: {str(e)}",
                sources_checked=0,
                evidence=[],
                overall_reliability=0.0,
                source_diversity=0.0,
                processing_time_seconds=0.0,
                cached=False,
            )
    
    # Process in batches to avoid overwhelming the system
    if claims_to_process:
        batch_size = 5
        for i in range(0, len(claims_to_process), batch_size):
            batch = claims_to_process[i:i + batch_size]
            batch_results = await asyncio.gather(*[process_claim(c) for c in batch])
            results.extend(batch_results)
    
    end_time = time.time()
    
    return BatchCheckResponse(
        total_claims=len(request.claims),
        processed=len(request.claims) - cached_count,
        cached=cached_count,
        results=results,
        total_processing_time_seconds=end_time - start_time,
    )


@app.get("/api/history", tags=["History"])
async def get_history(limit: int = 50):
    """Get recent fact-check history."""
    store = get_claim_store()
    
    # Get all cached claims
    with store._lock:
        items = list(store._cache.values())
    
    # Sort by checked_at descending
    items.sort(key=lambda x: x.get("checked_at", ""), reverse=True)
    
    return {
        "total": len(items),
        "items": items[:limit],
    }


@app.get("/api/similar", tags=["Search"])
async def find_similar_claims(claim: str, threshold: float = 0.6):
    """Find similar claims that have already been checked."""
    store = get_claim_store()
    similar = store.find_similar(claim, threshold=threshold)
    
    return {
        "query": claim,
        "threshold": threshold,
        "matches": similar,
    }


# ============================================
# NOTIFICATION ENDPOINTS
# ============================================

class NotifyRequest(BaseModel):
    """Request to send notification."""
    claim_id: str
    channels: list[str] = Field(default=["webhook"], description="Notification channels: sms, email, webhook, slack")
    recipients: dict[str, list[str]] = Field(
        description="Channel-specific recipients, e.g., {'email': ['user@example.com'], 'webhook': ['https://...']}"
    )


@app.post("/api/notify", tags=["Notifications"])
async def send_notification(request: NotifyRequest):
    """
    Send notification for a fact-check result.
    
    Sends alerts via specified channels (SMS, Email, Webhook, Slack).
    """
    from services.notifications import get_notification_service, NotificationChannel, NotificationPayload
    
    store = get_claim_store()
    
    # Find the claim result
    with store._lock:
        claim_data = store._cache.get(request.claim_id)
    
    if not claim_data:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    # Create payload
    payload = NotificationPayload(
        claim_id=request.claim_id,
        claim_text=claim_data["claim_text"],
        verdict=claim_data["verdict"],
        severity=claim_data["severity"],
        correction=claim_data.get("correction"),
        explanation_short=claim_data["explanation"][:500] if claim_data.get("explanation") else "",
    )
    
    notification_service = get_notification_service()
    results = []
    
    for channel_name, recipients in request.recipients.items():
        try:
            channel = NotificationChannel(channel_name)
            for recipient in recipients:
                result = await notification_service.send(channel, payload, recipient)
                results.append({
                    "channel": channel_name,
                    "recipient": recipient,
                    "success": result.success,
                    "message": result.message,
                })
        except ValueError:
            results.append({
                "channel": channel_name,
                "recipient": None,
                "success": False,
                "message": f"Unknown channel: {channel_name}",
            })
    
    return {
        "claim_id": request.claim_id,
        "notifications_sent": len([r for r in results if r["success"]]),
        "notifications_failed": len([r for r in results if not r["success"]]),
        "results": results,
    }


@app.get("/api/notification-channels", tags=["Notifications"])
async def get_notification_channels():
    """Get available and configured notification channels."""
    from services.notifications import get_notification_service
    
    service = get_notification_service()
    configured = service.get_configured_channels()
    
    return {
        "available": ["sms", "email", "webhook", "slack", "telegram"],
        "configured": [c.value for c in configured],
    }


# ============================================
# INGESTION ENDPOINTS (Demo)
# ============================================

@app.get("/api/ingest/twitter", tags=["Ingestion"])
async def get_twitter_feed(crisis_type: str = "earthquake", limit: int = 10):
    """
    Get crisis-related tweets for monitoring.
    
    Uses mock data for demo. In production, connects to Twitter API.
    """
    from tools import TwitterIngestTool
    
    tool = TwitterIngestTool()
    tweets = await tool.get_crisis_feed(crisis_type=crisis_type, hours_back=24)
    
    return {
        "crisis_type": crisis_type,
        "count": len(tweets[:limit]),
        "tweets": [
            {
                "id": t.id,
                "text": t.text,
                "author": t.author_username,
                "engagement_score": t.engagement_score,
                "language": t.language,
                "url": t.source_url,
            }
            for t in tweets[:limit]
        ],
    }


@app.get("/api/ingest/whatsapp", tags=["Ingestion"])
async def get_whatsapp_messages(limit: int = 10):
    """
    Get pending WhatsApp messages for fact-checking.
    
    Uses mock data for demo. In production, receives via webhook.
    """
    from tools import WhatsAppGatewayTool
    
    tool = WhatsAppGatewayTool()
    messages = tool.get_mock_messages()
    prioritized = tool.prioritize_messages(messages)
    
    return {
        "count": len(prioritized[:limit]),
        "messages": [
            {
                "id": m.id,
                "text": m.text,
                "is_forwarded": m.is_forwarded,
                "virality": m.virality_indicator,
                "group": m.group_name,
                "language": m.language,
            }
            for m in prioritized[:limit]
        ],
    }


@app.get("/api/ingest/youtube", tags=["Ingestion"])
async def get_youtube_videos(crisis_type: str = "earthquake", limit: int = 10):
    """
    Get crisis-related YouTube videos for monitoring.
    
    Uses mock data for demo. In production, connects to YouTube API.
    """
    from tools import YouTubeCommentsTool
    
    tool = YouTubeCommentsTool()
    videos = await tool.get_crisis_videos(crisis_type=crisis_type, hours_back=24)
    
    return {
        "crisis_type": crisis_type,
        "count": len(videos[:limit]),
        "videos": [
            {
                "id": v.id,
                "title": v.title,
                "channel": v.channel_title,
                "views": v.view_count,
                "comments": v.comment_count,
                "url": v.url,
            }
            for v in videos[:limit]
        ],
    }


# ============================================
# RUN SERVER
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)



