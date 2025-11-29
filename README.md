# 🧢 Fact or Cap - AI-Powered Fact Checker (Backend)

> **Real-time misinformation detection. No cap.**

[![Live Demo](https://img.shields.io/badge/Live%20Demo-crisiswatch--web.vercel.app-blue?style=for-the-badge)](https://crisiswatch-web.vercel.app)
[![Backend API](https://img.shields.io/badge/API-crisiswatch--uoj4.onrender.com-green?style=for-the-badge)](https://crisiswatch-uoj4.onrender.com/docs)

## 🔗 Quick Links

| Resource | URL |
|----------|-----|
| **Live Website** | https://crisiswatch-web.vercel.app |
| **Backend API** | https://crisiswatch-uoj4.onrender.com |
| **API Docs (Swagger)** | https://crisiswatch-uoj4.onrender.com/docs |
| **Frontend Repo** | https://github.com/dhruv4740/crisiswatch-web |
| **Backend Repo** | https://github.com/dhruv4740/crisiswatch |

---

## 🎯 What It Does

**Fact or Cap** is an AI-powered fact-checking tool that:

1. **Takes any claim** - Paste a viral tweet, news headline, or any statement
2. **Searches 10+ sources** - Wikipedia, news APIs, fact-check databases, and more
3. **Returns a verdict** - TRUE, FALSE, MOSTLY TRUE, MIXED, or UNVERIFIABLE
4. **Explains in detail** - With evidence, sources, and confidence scores
5. **Supports Hindi** - Bilingual explanations for Indian users

---

## 🚀 Try It Now

### Option 1: Use the Live Website
👉 **https://crisiswatch-web.vercel.app**

### Option 2: Use the API Directly
```bash
# Streaming API (recommended)
curl "https://crisiswatch-uoj4.onrender.com/api/check/stream?claim=Elon%20Musk%20bought%20Twitter"

# Simple API
curl -X POST "https://crisiswatch-uoj4.onrender.com/api/check" \
  -H "Content-Type: application/json" \
  -d '{"claim": "Elon Musk bought Twitter"}'
```

### Option 3: Run Backend Locally
```powershell
# Clone and setup
git clone https://github.com/dhruv4740/crisiswatch.git
cd crisiswatch
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Add your API key
copy .env.example .env
# Edit .env and add GEMINI_API_KEY

# Run the API server
python -m uvicorn api.main:app --reload --port 8000

# API available at http://localhost:8000
# Docs at http://localhost:8000/docs
```

---

## 🧩 Browser Extension

Located in the `crisiswatch-extension/` folder of the frontend repo.

### Installation (Chrome - Developer Mode)
1. Clone/download the frontend repo
2. Open Chrome → `chrome://extensions/`
3. Enable **"Developer mode"** (top right toggle)
4. Click **"Load unpacked"**
5. Select the `crisiswatch-extension` folder

### Usage
- Select any text on a webpage
- Click the Fact or Cap extension icon
- Get instant fact-check results!

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| **Language** | Python 3.11+ |
| **Framework** | FastAPI |
| **LLM** | Google Gemini 2.0 Flash |
| **Workflow** | LangGraph (agentic) |
| **Search APIs** | Tavily, NewsAPI, Wikipedia, Google Fact Check |
| **Hosting** | Render.com |

---

## 📊 Features

- ✅ **Real-time Streaming** - Server-Sent Events for live progress
- ✅ **10+ Data Sources** - Wikipedia, news, fact-checkers
- ✅ **Confidence Scores** - 0-100% with each verdict
- ✅ **Bilingual Support** - English + Hindi
- ✅ **Claim Caching** - Faster repeat lookups
- ✅ **Trending Claims** - Community fact-checks

---

## 🔑 API Keys Required

Create a `.env` file with:

```env
# Required
GEMINI_API_KEY=your_gemini_key_here

# Optional (improves accuracy)
TAVILY_API_KEY=your_tavily_key
NEWSAPI_KEY=your_newsapi_key
GOOGLE_FACTCHECK_API_KEY=your_google_key
```

| Key | Required | Get It From |
|-----|----------|-------------|
| `GEMINI_API_KEY` | ✅ Yes | [aistudio.google.com](https://aistudio.google.com) |
| `TAVILY_API_KEY` | Optional | [tavily.com](https://tavily.com) |
| `NEWSAPI_KEY` | Optional | [newsapi.org](https://newsapi.org) |

---

## 📁 Project Structure

```
crisiswatch/
├── api/              # FastAPI endpoints (/api/check, /api/check/stream)
├── agents/           # LLM providers (Gemini)
├── tools/            # Search tools (Wikipedia, Tavily, NewsAPI, etc.)
├── graph/            # LangGraph workflow
│   ├── nodes.py      # Pipeline stages
│   ├── prompts.py    # LLM prompts
│   └── state.py      # State schema
├── models/           # Pydantic schemas
├── config/           # Settings and environment
├── services/         # Caching, notifications
├── cli.py            # Command-line interface
└── requirements.txt  # Dependencies
```

---

## 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/check` | POST | Check a claim (returns full result) |
| `/api/check/stream` | GET | Check with real-time streaming (SSE) |
| `/api/trending` | GET | Get trending/recent claims |
| `/health` | GET | Health check |
| `/docs` | GET | Swagger API documentation |

---

## 📈 Verdict Types

| Verdict | Meaning |
|---------|---------|
| `TRUE` | Verified as accurate |
| `MOSTLY_TRUE` | Mostly accurate with minor issues |
| `MIXED` | Contains both true and false elements |
| `MOSTLY_FALSE` | Mostly inaccurate |
| `FALSE` | Definitively false/misinformation |
| `UNVERIFIABLE` | Cannot be verified |

---

## 🏆 Hackathon

Built for the **CrisisWatch Hackathon 2025** - Misinformation Track

---

## 📄 License

MIT

---

**No cap. Just facts.** 🧢
