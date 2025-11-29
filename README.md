# 🔍 CrisisWatch - Real-Time Misinformation Detection Agent

An AI-powered agent that detects and debunks misinformation during crisis events (earthquakes, floods, disease outbreaks, civil unrest). Built for the **Misinformation Track**.

## Features

- ✅ **Claim Extraction** - Identifies verifiable claims from text
- ✅ **Multi-Source Search** - Wikipedia, news APIs, fact-check databases
- ✅ **Evidence Synthesis** - Cross-references sources to determine truth
- ✅ **Severity Ranking** - Prioritizes life-threatening misinformation
- ✅ **Bilingual Output** - Explanations in English AND Hindi
- ✅ **Shareable Corrections** - Ready-to-post social media corrections

## Quick Start

### 1. Setup Environment

```powershell
cd C:\Projects\crisiswatch
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Configure API Keys

Copy `.env.example` to `.env` and add your API keys:

```powershell
Copy-Item .env.example .env
```

**Required:**
- `GEMINI_API_KEY` - Get free from [aistudio.google.com](https://aistudio.google.com)

**Optional (improves accuracy):**
- `TAVILY_API_KEY` - Web search ([tavily.com](https://tavily.com))
- `NEWSAPI_KEY` - News articles ([newsapi.org](https://newsapi.org))
- `GOOGLE_FACTCHECK_API_KEY` - Existing fact-checks ([Google Cloud Console](https://console.cloud.google.com))

### 3. Run the Agent

```powershell
# Check a single claim
python cli.py check "Drinking hot water with lemon cures COVID-19"

# Interactive mode
python cli.py interactive
```

## Example Output

```json
{
  "claim": {
    "text": "Drinking hot water with lemon cures COVID-19",
    "crisis_type": "health"
  },
  "verdict": "false",
  "confidence": 1.0,
  "severity": "high",
  "explanation": "This is simply not true. There is no scientific evidence...",
  "explanation_hindi": "यह बिल्कुल सच नहीं है...",
  "correction": "Drinking hot water with lemon DOES NOT cure COVID-19. Rely on proven treatments."
}
```

## Project Structure

```
crisiswatch/
├── agents/           # LLM providers (Gemini, Grok)
├── tools/            # Search tools (Wikipedia, Tavily, NewsAPI, Fact Check)
├── graph/            # LangGraph workflow (nodes, state, prompts)
├── models/           # Pydantic schemas
├── config/           # Settings and environment config
├── cli.py            # Command-line interface
├── requirements.txt  # Python dependencies
└── .env              # API keys (not committed)
```

## How It Works

```
User Input → Extract Claim → Generate Search Queries → Search Sources (parallel)
                                                              ↓
           ← Generate Explanation ← Synthesize Evidence ← Rank Severity
```

1. **Extract Claim**: Uses Gemini to parse claims and identify crisis type
2. **Search Sources**: Queries Wikipedia, news, and fact-check databases in parallel
3. **Synthesize Evidence**: Analyzes evidence to determine verdict
4. **Generate Explanation**: Creates human-readable explanations in English/Hindi

## Verdict Types

| Verdict | Description |
|---------|-------------|
| `false` | Claim is definitively false |
| `mostly_false` | Claim is mostly false with minor truth |
| `mixed` | Claim contains both true and false elements |
| `mostly_true` | Claim is mostly true with minor errors |
| `true` | Claim is verified as true |
| `unverifiable` | Cannot be verified with available sources |

## Severity Levels

| Level | Description | Example |
|-------|-------------|---------|
| `critical` | Life-threatening | Fake evacuation routes |
| `high` | Causes panic or undermines response | False hospital closures |
| `medium` | Misleading but not immediately dangerous | Exaggerated damage claims |
| `low` | Minor inaccuracies | Wrong dates or minor details |

## Next Steps (Roadmap)

- [ ] Add Tavily/NewsAPI integration for broader search
- [ ] Add Twitter/X monitoring for real-time claims
- [ ] Build Streamlit dashboard for agencies
- [ ] Add SMS notification system
- [ ] Fine-tune claim detection for regional languages

## Tech Stack

- **LLM**: Google Gemini 2.0 Flash
- **Framework**: LangGraph (agentic workflow)
- **Search**: Wikipedia API, Tavily, NewsAPI, Google Fact Check
- **Language**: Python 3.11+

## License

MIT

---

Built for the **CrisisWatch** project - Misinformation Track
