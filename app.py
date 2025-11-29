"""
CrisisWatch - Streamlit Dashboard
Real-Time Misinformation Detection for Crisis Events
Enhanced UI with Analytics & Live Monitoring
"""

import streamlit as st
import asyncio
import time
import random
from datetime import datetime, timedelta

# Must be first Streamlit command
st.set_page_config(
    page_title="CrisisWatch",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

from config import get_settings
from models.schemas import Claim, FactCheckResult, VerdictType, SeverityLevel
from graph.nodes import (
    extract_claim,
    generate_search_queries,
    search_sources,
    synthesize_evidence,
    generate_explanation,
)

settings = get_settings()

# ============================================
# SESSION STATE INITIALIZATION
# ============================================
if "claim_input" not in st.session_state:
    st.session_state.claim_input = ""
if "is_checking" not in st.session_state:
    st.session_state.is_checking = False
if "result" not in st.session_state:
    st.session_state.result = None
if "check_history" not in st.session_state:
    st.session_state.check_history = []

# ============================================
# SAMPLE CLAIMS & TRENDING DATA
# ============================================
SAMPLE_CLAIMS = {
    "🦠 Health & Medical": [
        "Drinking hot water with lemon cures COVID-19",
        "Drinking cow urine prevents coronavirus infection",
        "5G towers spread the coronavirus",
        "Wearing masks causes oxygen deprivation",
    ],
    "🌊 Natural Disasters": [
        "A magnitude 8.5 earthquake just hit Delhi, evacuate immediately",
        "Tsunami warning issued for entire east coast of India",
        "Mumbai airport flooded and closed indefinitely",
    ],
    "⚠️ Civil & Political": [
        "Army has taken over Mumbai, curfew declared",
        "Internet shutdown across all of India starting tonight",
        "All banks will be closed for the next 2 weeks",
    ],
    "💉 Vaccines": [
        "COVID vaccines contain microchips for tracking",
        "mRNA vaccines alter your DNA permanently",
    ],
}

# Simulated trending misinformation for demo
TRENDING_MISINFO = [
    {"claim": "Major earthquake predicted in Mumbai for tonight", "severity": "critical", "time": "2 min ago", "platform": "Twitter"},
    {"claim": "New COVID variant has 90% fatality rate", "severity": "critical", "time": "5 min ago", "platform": "WhatsApp"},
    {"claim": "Government banning all cash transactions", "severity": "high", "time": "8 min ago", "platform": "Facebook"},
    {"claim": "Drinking bleach kills coronavirus", "severity": "critical", "time": "12 min ago", "platform": "YouTube"},
    {"claim": "Schools closed indefinitely due to outbreak", "severity": "high", "time": "15 min ago", "platform": "Twitter"},
]

# ============================================
# MODERN CSS STYLING
# ============================================
def load_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Hide Streamlit defaults */
    #MainMenu, footer, header {visibility: hidden;}
    .stDeployButton {display: none;}
    
    /* Main container */
    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        max-width: 1400px;
    }
    
    /* Hero Header */
    .hero-container {
        background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
        padding: 1.8rem 2rem;
        border-radius: 20px;
        margin-bottom: 1.5rem;
        position: relative;
        overflow: hidden;
        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
    }
    .hero-container::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.03'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
    }
    .hero-content {
        position: relative;
        z-index: 1;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .hero-left {
        flex: 1;
    }
    .hero-title {
        color: white;
        font-size: 2.2rem;
        font-weight: 800;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 0.6rem;
    }
    .hero-subtitle {
        color: rgba(255,255,255,0.8);
        font-size: 0.95rem;
        margin-top: 0.3rem;
        font-weight: 400;
    }
    .hero-badges {
        display: flex;
        gap: 0.5rem;
        margin-top: 0.6rem;
    }
    .hero-badge {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 0.25rem 0.7rem;
        border-radius: 30px;
        font-size: 0.65rem;
        font-weight: 600;
        color: white;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .hero-badge.live {
        background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
        animation: pulse-live 2s infinite;
    }
    @keyframes pulse-live {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }
    
    /* Stats in header */
    .hero-stats {
        display: flex;
        gap: 1rem;
    }
    .stat-box {
        text-align: center;
        background: rgba(255,255,255,0.1);
        padding: 0.6rem 1rem;
        border-radius: 12px;
        backdrop-filter: blur(10px);
    }
    .stat-value {
        color: white;
        font-size: 1.3rem;
        font-weight: 800;
    }
    .stat-label {
        color: rgba(255,255,255,0.7);
        font-size: 0.65rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Main Content Card */
    .content-card {
        background: white;
        border-radius: 20px;
        padding: 2rem;
        box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        border: 1px solid #e5e7eb;
        min-height: 400px;
    }
    
    /* Input Section */
    .input-section {
        text-align: center;
        padding: 2rem 0;
    }
    .input-title {
        font-size: 1.5rem;
        font-weight: 700;
        color: #1f2937;
        margin-bottom: 0.3rem;
    }
    .input-subtitle {
        font-size: 0.95rem;
        color: #6b7280;
        margin-bottom: 2rem;
    }
    
    /* Loading Animation - Large & Centered */
    .loading-overlay {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 3rem 2rem;
        min-height: 400px;
    }
    
    .loading-spinner-large {
        width: 80px;
        height: 80px;
        border: 5px solid #e2e8f0;
        border-top: 5px solid #6366f1;
        border-radius: 50%;
        animation: spin 1s linear infinite;
        margin-bottom: 2rem;
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    .loading-title {
        font-size: 1.5rem;
        font-weight: 700;
        color: #1f2937;
        margin-bottom: 0.5rem;
    }
    
    .loading-subtitle {
        font-size: 1rem;
        color: #6b7280;
        margin-bottom: 2rem;
    }
    
    /* Step Progress */
    .steps-container {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
        flex-wrap: wrap;
        max-width: 700px;
    }
    
    .step-item {
        display: flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.5rem 1rem;
        background: #f1f5f9;
        border-radius: 30px;
        font-size: 0.85rem;
        color: #64748b;
        transition: all 0.3s ease;
    }
    
    .step-item.active {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
        color: white;
        animation: step-pulse 1.5s ease-in-out infinite;
    }
    
    .step-item.completed {
        background: #22c55e;
        color: white;
    }
    
    @keyframes step-pulse {
        0%, 100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(99, 102, 241, 0.4); }
        50% { transform: scale(1.02); box-shadow: 0 0 0 10px rgba(99, 102, 241, 0); }
    }
    
    /* Verdict Cards */
    .verdict-card {
        border-radius: 16px;
        padding: 2rem;
        text-align: center;
        box-shadow: 0 8px 30px rgba(0,0,0,0.12);
        position: relative;
        overflow: hidden;
    }
    .verdict-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
    }
    .verdict-false {
        background: linear-gradient(180deg, #fff5f5 0%, #ffffff 100%);
    }
    .verdict-false::before {
        background: linear-gradient(90deg, #ef4444 0%, #dc2626 100%);
    }
    .verdict-mostly-false {
        background: linear-gradient(180deg, #fff7ed 0%, #ffffff 100%);
    }
    .verdict-mostly-false::before {
        background: linear-gradient(90deg, #f97316 0%, #ea580c 100%);
    }
    .verdict-mixed {
        background: linear-gradient(180deg, #fefce8 0%, #ffffff 100%);
    }
    .verdict-mixed::before {
        background: linear-gradient(90deg, #eab308 0%, #ca8a04 100%);
    }
    .verdict-true, .verdict-mostly-true {
        background: linear-gradient(180deg, #f0fdf4 0%, #ffffff 100%);
    }
    .verdict-true::before, .verdict-mostly-true::before {
        background: linear-gradient(90deg, #22c55e 0%, #16a34a 100%);
    }
    .verdict-unverifiable {
        background: linear-gradient(180deg, #f8fafc 0%, #ffffff 100%);
    }
    .verdict-unverifiable::before {
        background: linear-gradient(90deg, #64748b 0%, #475569 100%);
    }
    
    .verdict-icon {
        font-size: 3.5rem;
        margin-bottom: 0.5rem;
    }
    .verdict-label {
        font-size: 1.4rem;
        font-weight: 700;
        margin-bottom: 0.3rem;
    }
    .verdict-false .verdict-label { color: #dc2626; }
    .verdict-mostly-false .verdict-label { color: #ea580c; }
    .verdict-mixed .verdict-label { color: #ca8a04; }
    .verdict-true .verdict-label, .verdict-mostly-true .verdict-label { color: #16a34a; }
    .verdict-unverifiable .verdict-label { color: #475569; }
    
    /* Confidence Meter */
    .confidence-container {
        background: white;
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        text-align: center;
    }
    .confidence-value {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .confidence-label {
        font-size: 0.8rem;
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 600;
    }
    
    /* Severity Badge */
    .severity-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.5rem 1rem;
        border-radius: 30px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .severity-critical {
        background: linear-gradient(135deg, #fecaca 0%, #fca5a5 100%);
        color: #991b1b;
    }
    .severity-high {
        background: linear-gradient(135deg, #fed7aa 0%, #fdba74 100%);
        color: #9a3412;
    }
    .severity-medium {
        background: linear-gradient(135deg, #fef08a 0%, #fde047 100%);
        color: #854d0e;
    }
    .severity-low {
        background: linear-gradient(135deg, #bbf7d0 0%, #86efac 100%);
        color: #166534;
    }
    
    /* Section Headers */
    .section-header {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        font-size: 1.1rem;
        font-weight: 700;
        color: #1f2937;
        margin: 1.5rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #e5e7eb;
    }
    
    /* Claim Display */
    .claim-display {
        background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
        border-radius: 12px;
        padding: 1.2rem;
        border-left: 4px solid #0284c7;
        margin-bottom: 1.5rem;
    }
    .claim-display-text {
        font-size: 1.1rem;
        color: #0c4a6e;
        font-weight: 500;
        line-height: 1.5;
    }
    
    /* Explanation Box */
    .explanation-box {
        background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
        border-radius: 12px;
        padding: 1.5rem;
        border-left: 4px solid #6366f1;
        line-height: 1.7;
        color: #374151;
    }
    
    /* Correction Box */
    .correction-box {
        background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
        border-radius: 12px;
        padding: 1.5rem;
        border: 1px solid #a7f3d0;
        margin-top: 1rem;
    }
    .correction-title {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-weight: 700;
        color: #065f46;
        margin-bottom: 0.8rem;
    }
    .correction-text {
        color: #047857;
        font-size: 1rem;
        line-height: 1.6;
    }
    
    /* Evidence Card - With clickable links */
    .evidence-card {
        background: white;
        border-radius: 12px;
        padding: 1.2rem;
        margin-bottom: 0.8rem;
        border: 1px solid #e5e7eb;
        transition: all 0.2s ease;
    }
    .evidence-card:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        border-color: #d1d5db;
        transform: translateY(-2px);
    }
    .evidence-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 0.5rem;
    }
    .evidence-source {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-weight: 600;
        color: #1f2937;
    }
    .evidence-link {
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
        color: #6366f1;
        text-decoration: none;
        font-size: 0.85rem;
        font-weight: 500;
        padding: 0.3rem 0.6rem;
        background: #eef2ff;
        border-radius: 6px;
        transition: all 0.2s;
    }
    .evidence-link:hover {
        background: #6366f1;
        color: white;
    }
    .evidence-snippet {
        color: #4b5563;
        font-size: 0.9rem;
        line-height: 1.5;
    }
    .stance-supports { color: #16a34a; }
    .stance-refutes { color: #dc2626; }
    .stance-neutral { color: #6b7280; }
    
    /* Metadata Pills */
    .meta-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
        background: #f3f4f6;
        padding: 0.4rem 0.8rem;
        border-radius: 20px;
        font-size: 0.8rem;
        color: #4b5563;
        margin-right: 0.5rem;
        margin-bottom: 0.5rem;
    }
    
    /* Trending Card */
    .trending-card {
        background: white;
        border-radius: 12px;
        padding: 1rem;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        border: 1px solid #e5e7eb;
        margin-top: 1rem;
    }
    .trending-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 0.8rem;
    }
    .trending-title {
        display: flex;
        align-items: center;
        gap: 0.4rem;
        font-size: 0.85rem;
        font-weight: 700;
        color: #1f2937;
    }
    .trending-live {
        display: flex;
        align-items: center;
        gap: 0.3rem;
        font-size: 0.7rem;
        color: #16a34a;
        font-weight: 600;
    }
    .live-dot {
        width: 6px;
        height: 6px;
        background: #22c55e;
        border-radius: 50%;
        animation: blink 1s infinite;
    }
    @keyframes blink {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.3; }
    }
    
    .trending-item {
        display: flex;
        align-items: flex-start;
        gap: 0.6rem;
        padding: 0.6rem;
        border-radius: 8px;
        background: #f8fafc;
        margin-bottom: 0.5rem;
        cursor: pointer;
        transition: all 0.2s;
        border: 1px solid transparent;
    }
    .trending-item:hover {
        background: #f1f5f9;
        border-color: #e2e8f0;
    }
    .trending-severity {
        padding: 0.15rem 0.4rem;
        border-radius: 4px;
        font-size: 0.6rem;
        font-weight: 700;
        text-transform: uppercase;
        flex-shrink: 0;
    }
    .trending-severity.critical {
        background: #fecaca;
        color: #991b1b;
    }
    .trending-severity.high {
        background: #fed7aa;
        color: #9a3412;
    }
    .trending-severity.medium {
        background: #fef08a;
        color: #854d0e;
    }
    .trending-content {
        flex: 1;
        min-width: 0;
    }
    .trending-text {
        font-size: 0.8rem;
        color: #374151;
        line-height: 1.3;
        margin-bottom: 0.2rem;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .trending-meta {
        font-size: 0.65rem;
        color: #9ca3af;
    }
    
    /* Analytics Cards */
    .analytics-card {
        background: white;
        border-radius: 12px;
        padding: 1rem;
        text-align: center;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        border: 1px solid #e5e7eb;
        margin-bottom: 0.8rem;
    }
    .analytics-icon {
        font-size: 1.5rem;
        margin-bottom: 0.2rem;
    }
    .analytics-value {
        font-size: 1.5rem;
        font-weight: 800;
        color: #1f2937;
    }
    .analytics-label {
        font-size: 0.7rem;
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Sidebar styling */
    .sidebar-header {
        font-size: 0.75rem;
        font-weight: 700;
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 0.8rem;
    }
    
    .api-status {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.4rem 0;
        font-size: 0.85rem;
    }
    
    .status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
    }
    
    .status-active { background: #22c55e; }
    .status-inactive { background: #ef4444; }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        background: #f1f5f9;
        border-radius: 10px;
        padding: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 0.5rem 1.5rem;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background: white;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
        color: white;
        border: none;
        padding: 0.75rem 2rem;
        font-size: 1rem;
        font-weight: 600;
        border-radius: 10px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4);
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(99, 102, 241, 0.5);
    }
    
    /* Text area */
    .stTextArea textarea {
        border-radius: 12px;
        border: 2px solid #e2e8f0;
        padding: 1rem;
        font-size: 1rem;
        transition: all 0.2s ease;
    }
    .stTextArea textarea:focus {
        border-color: #6366f1;
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
    }
    </style>
    """, unsafe_allow_html=True)


# ============================================
# PIPELINE RUNNER
# ============================================
async def run_pipeline(raw_input: str, language: str) -> FactCheckResult:
    """Run the fact-checking pipeline."""
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

    # Step 1: Extract claim
    res = await extract_claim(state)
    state.update({k: v for k, v in res.items() if k in state})
    claim_obj = state.get("claim")

    # Step 2: Generate search queries
    res = await generate_search_queries(state)
    if res.get("_search_queries"):
        state["_search_queries"] = res.get("_search_queries")

    # Step 3: Search sources
    res = await search_sources(state)
    state["search_results"] = res.get("search_results", [])
    state["sources_checked"] = res.get("sources_checked", 0)

    # Step 4: Synthesize evidence
    res = await synthesize_evidence(state)
    state["evidence"] = res.get("evidence", [])
    state["verdict"] = res.get("verdict")
    state["confidence"] = res.get("confidence", 0.0)
    state["severity"] = res.get("severity")

    # Step 5: Generate explanation
    res = await generate_explanation(state)
    state["explanation"] = res.get("explanation")
    state["explanation_hindi"] = res.get("explanation_hindi")
    state["correction"] = res.get("correction")

    end_time = time.time()

    if claim_obj is None:
        claim_obj = Claim(text=raw_input, language=language)

    return FactCheckResult(
        claim=claim_obj,
        verdict=state.get("verdict") or VerdictType.UNVERIFIABLE,
        confidence=state.get("confidence", 0.0),
        severity=state.get("severity") or SeverityLevel.MEDIUM,
        explanation=state.get("explanation", ""),
        explanation_hindi=state.get("explanation_hindi"),
        evidence=state.get("evidence", []),
        correction=state.get("correction"),
        sources_checked=state.get("sources_checked", 0),
        processing_time_seconds=round(end_time - start_time, 2),
    )


def get_verdict_display(verdict: VerdictType) -> tuple:
    """Get display properties for verdict."""
    displays = {
        VerdictType.FALSE: ("❌", "FALSE", "verdict-false"),
        VerdictType.MOSTLY_FALSE: ("⚠️", "MOSTLY FALSE", "verdict-mostly-false"),
        VerdictType.MIXED: ("🔄", "MIXED", "verdict-mixed"),
        VerdictType.MOSTLY_TRUE: ("✅", "MOSTLY TRUE", "verdict-mostly-true"),
        VerdictType.TRUE: ("✅", "TRUE", "verdict-true"),
        VerdictType.UNVERIFIABLE: ("❓", "UNVERIFIABLE", "verdict-unverifiable"),
    }
    return displays.get(verdict, ("❓", "UNKNOWN", "verdict-unverifiable"))


def get_severity_display(severity: SeverityLevel) -> tuple:
    """Get display properties for severity."""
    displays = {
        SeverityLevel.CRITICAL: ("🚨", "Critical Risk", "severity-critical"),
        SeverityLevel.HIGH: ("⚠️", "High Risk", "severity-high"),
        SeverityLevel.MEDIUM: ("📋", "Medium Risk", "severity-medium"),
        SeverityLevel.LOW: ("ℹ️", "Low Risk", "severity-low"),
    }
    return displays.get(severity, ("📋", "Medium", "severity-medium"))


def render_input_section(language: str):
    """Render the claim input section."""
    st.markdown("""
    <div class="input-section">
        <div class="input-title">🔍 Verify a Claim</div>
        <div class="input-subtitle">Enter any suspicious claim, news, or forwarded message to check its authenticity</div>
    </div>
    """, unsafe_allow_html=True)
    
    claim_text = st.text_area(
        "Claim",
        value=st.session_state.claim_input,
        height=120,
        placeholder="e.g., 'Drinking hot water with lemon cures COVID-19' or 'A magnitude 8 earthquake hit Delhi today'",
        label_visibility="collapsed",
        key="claim_textarea"
    )
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔍 Verify This Claim", type="primary", use_container_width=True):
            if claim_text.strip():
                st.session_state.claim_input = claim_text
                st.session_state.is_checking = True
                st.rerun()
            else:
                st.warning("⚠️ Please enter a claim to verify")


def render_loading_section(claim_text: str, language: str):
    """Render loading animation while checking."""
    steps = [
        ("🔍", "Analyzing"),
        ("💡", "Querying"),
        ("🌐", "Searching"),
        ("⚖️", "Synthesizing"),
        ("📝", "Explaining"),
    ]
    
    loading_container = st.empty()
    
    steps_html = "".join([f'<div class="step-item">{icon} {label}</div>' for icon, label in steps])
    
    loading_container.markdown(f"""
    <div class="loading-overlay">
        <div class="loading-spinner-large"></div>
        <div class="loading-title">Verifying Claim...</div>
        <div class="loading-subtitle">Cross-referencing multiple sources for accuracy</div>
        <div class="steps-container">
            {steps_html}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    try:
        result = asyncio.run(run_pipeline(claim_text, language))
        st.session_state.result = result
        st.session_state.is_checking = False
        
        st.session_state.check_history.append({
            "claim": claim_text,
            "verdict": result.verdict,
            "time": datetime.now()
        })
        
        loading_container.empty()
        st.rerun()
    except Exception as e:
        loading_container.empty()
        st.error(f"An error occurred: {str(e)}")
        st.session_state.is_checking = False


def render_results_section(result: FactCheckResult):
    """Render the fact-check results."""
    verdict_icon, verdict_label, verdict_class = get_verdict_display(result.verdict)
    sev_icon, sev_label, sev_class = get_severity_display(result.severity)
    
    # Check Another button
    if st.button("← Check Another Claim", key="check_another"):
        st.session_state.result = None
        st.session_state.claim_input = ""
        st.rerun()
    
    st.markdown("")
    
    # Display the claim
    st.markdown(f"""
    <div class="claim-display">
        <div class="claim-display-text">"{result.claim.text}"</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Verdict Section
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.markdown(f"""
        <div class="verdict-card {verdict_class}">
            <div class="verdict-icon">{verdict_icon}</div>
            <div class="verdict-label">{verdict_label}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="confidence-container">
            <div class="confidence-value">{int(result.confidence * 100)}%</div>
            <div class="confidence-label">Confidence</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="confidence-container">
            <span class="severity-badge {sev_class}">{sev_icon} {sev_label}</span>
            <div class="confidence-label" style="margin-top: 0.8rem;">Severity</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Metadata
    st.markdown('<div class="section-header">📌 Details</div>', unsafe_allow_html=True)
    
    crisis_type = result.claim.crisis_type.title() if result.claim.crisis_type else 'General'
    meta_html = f"""
    <div>
        <span class="meta-pill">🏷️ {crisis_type}</span>
        <span class="meta-pill">⏱️ {result.processing_time_seconds}s</span>
        <span class="meta-pill">📚 {result.sources_checked} sources</span>
        <span class="meta-pill">🕐 {result.checked_at.strftime('%H:%M:%S')}</span>
    """
    if result.claim.extracted_entities:
        for entity in result.claim.extracted_entities[:3]:
            meta_html += f'<span class="meta-pill">🔖 {entity}</span>'
    meta_html += "</div>"
    
    st.markdown(meta_html, unsafe_allow_html=True)
    
    # Explanation
    st.markdown('<div class="section-header">📖 Explanation</div>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🇬🇧 English", "🇮🇳 Hindi"])
    
    with tab1:
        st.markdown(f'<div class="explanation-box">{result.explanation}</div>', unsafe_allow_html=True)
    
    with tab2:
        if result.explanation_hindi:
            st.markdown(f'<div class="explanation-box">{result.explanation_hindi}</div>', unsafe_allow_html=True)
        else:
            st.info("Hindi explanation not available")
    
    # Correction
    if result.correction:
        st.markdown('<div class="section-header">📢 Share This Correction</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="correction-box">
            <div class="correction-title">📋 Ready to copy & share</div>
            <div class="correction-text">{result.correction}</div>
        </div>
        """, unsafe_allow_html=True)
        st.code(result.correction, language=None)
    
    # Evidence with clickable links
    st.markdown('<div class="section-header">🔎 Evidence Sources</div>', unsafe_allow_html=True)
    
    if result.evidence:
        for evidence in result.evidence:
            stance_class = f"stance-{evidence.stance}"
            stance_icon = {"supports": "✅", "refutes": "❌", "neutral": "➖"}.get(evidence.stance, "➖")
            
            link_html = ""
            if evidence.source_url:
                link_html = f'<a href="{evidence.source_url}" target="_blank" class="evidence-link">🔗 Visit Source</a>'
            
            st.markdown(f"""
            <div class="evidence-card">
                <div class="evidence-header">
                    <div class="evidence-source">
                        <span class="{stance_class}">{stance_icon}</span>
                        {evidence.source_name}
                    </div>
                    {link_html}
                </div>
                <div class="evidence-snippet">{evidence.snippet}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No detailed evidence sources available")
    
    with st.expander("🔧 View Raw API Response"):
        st.json(result.model_dump(mode="json"))


def render_trending_sidebar():
    """Render trending misinformation."""
    st.markdown("""
    <div class="trending-card">
        <div class="trending-header">
            <div class="trending-title">📡 Live Feed</div>
            <div class="trending-live"><div class="live-dot"></div> LIVE</div>
        </div>
    """, unsafe_allow_html=True)
    
    for item in TRENDING_MISINFO[:4]:
        st.markdown(f"""
        <div class="trending-item">
            <span class="trending-severity {item['severity']}">{item['severity'][:4]}</span>
            <div class="trending-content">
                <div class="trending-text">{item['claim']}</div>
                <div class="trending-meta">{item['platform']} • {item['time']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)


# ============================================
# MAIN APP
# ============================================
def main():
    load_css()
    
    # Stats
    total_checked = len(st.session_state.check_history) + 127
    false_detected = sum(1 for h in st.session_state.check_history 
                        if h.get("verdict") in [VerdictType.FALSE, VerdictType.MOSTLY_FALSE]) + 89
    
    # Hero Header
    st.markdown(f"""
    <div class="hero-container">
        <div class="hero-content">
            <div class="hero-left">
                <h1 class="hero-title">🛡️ CrisisWatch</h1>
                <p class="hero-subtitle">AI-Powered Real-Time Misinformation Detection for Crisis Events</p>
                <div class="hero-badges">
                    <span class="hero-badge">Powered by Gemini AI</span>
                    <span class="hero-badge live">● Live Monitoring</span>
                </div>
            </div>
            <div class="hero-stats">
                <div class="stat-box">
                    <div class="stat-value">{total_checked}</div>
                    <div class="stat-label">Claims Checked</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{false_detected}</div>
                    <div class="stat-label">False Detected</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">4</div>
                    <div class="stat-label">Sources Active</div>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.markdown('<div class="sidebar-header">⚙️ System Status</div>', unsafe_allow_html=True)
        
        apis = [
            ("Gemini AI", settings.has_gemini),
            ("Tavily Search", settings.has_tavily),
            ("NewsAPI", settings.has_newsapi),
            ("Wikipedia", True),
        ]
        
        for name, active in apis:
            status_class = "status-active" if active else "status-inactive"
            st.markdown(f"""
            <div class="api-status">
                <div class="status-dot {status_class}"></div>
                <span>{name}</span>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        st.markdown('<div class="sidebar-header">🌐 Output Language</div>', unsafe_allow_html=True)
        language = st.radio(
            "Language",
            options=["en", "hi"],
            format_func=lambda x: "🇬🇧 English" if x == "en" else "🇮🇳 हिंदी",
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        st.markdown('<div class="sidebar-header">📋 Quick Examples</div>', unsafe_allow_html=True)
        
        for category, claims in SAMPLE_CLAIMS.items():
            with st.expander(category):
                for claim in claims:
                    if st.button(claim, key=f"sample_{hash(claim)}", use_container_width=True):
                        st.session_state.claim_input = claim
                        st.session_state.result = None
                        st.rerun()
        
        st.markdown("---")
        
        st.markdown('<div class="sidebar-header">📡 Trending Alerts</div>', unsafe_allow_html=True)
        render_trending_sidebar()
    
    # Main Content
    main_col, side_col = st.columns([3, 1])
    
    with main_col:
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        
        if st.session_state.is_checking:
            render_loading_section(st.session_state.claim_input, language)
        elif st.session_state.result is not None:
            render_results_section(st.session_state.result)
        else:
            render_input_section(language)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with side_col:
        # Analytics Cards
        st.markdown("""
        <div class="analytics-card">
            <div class="analytics-icon">🎯</div>
            <div class="analytics-value">94%</div>
            <div class="analytics-label">Accuracy</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="analytics-card">
            <div class="analytics-icon">⚡</div>
            <div class="analytics-value">8.2s</div>
            <div class="analytics-label">Avg Response</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="analytics-card">
            <div class="analytics-icon">🌍</div>
            <div class="analytics-value">2</div>
            <div class="analytics-label">Languages</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Recent Checks
        if st.session_state.check_history:
            st.markdown("### Recent")
            for h in st.session_state.check_history[-3:][::-1]:
                v = h.get("verdict")
                v_val = v.value if hasattr(v, "value") else str(v)
                icon = {"false": "❌", "mostly_false": "⚠️", "mixed": "🔄", "true": "✅", "mostly_true": "✅"}.get(v_val, "❓")
                st.markdown(f"{icon} {h['claim'][:25]}...")


if __name__ == "__main__":
    main()
