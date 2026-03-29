# ET News AI — AI-Native News Experience

> Built for **ET Gen AI Hackathon 2026** · Problem Statement 8 · Team Holy Trinity

India's first AI-powered personalized business news experience — built on Economic Times intelligence. A multi-agent system that transforms how Indians consume business news.

---

## What is ET News AI?

Business news in 2026 is still delivered like it's 2005 — same homepage for everyone, static articles, English only, no depth. ET News AI changes that completely.

Instead of one feed for everyone, ET News AI builds a different experience for every user. A mutual fund investor gets market-relevant stories ranked by AI. A startup founder gets funding news first. A student gets explainer content. And anyone can ask questions about any article and get instant AI answers.

---

## Features

### Personalized Feed
AI ranks 40+ live ET articles by relevance to your profession and reading history. Every card shows an AI relevance score and the reason it was recommended. Feed learns automatically from what you read — no manual setup required.

### Ask AI
Click Ask AI on any article and chat with an AI that has read it. Ask "How does this affect my investments?" or "Explain this simply" and get answers tailored to your profile. Follow-up questions suggested automatically.

### Deep Briefing
One click gives you the full picture — main article plus all related ET coverage synthesized together. No need to read 5 separate articles.

### Story Arc
Pick any ongoing news story and get a complete visual narrative — full timeline with real dates, key players identified, sentiment analysis (positive/negative/neutral), conflicting viewpoints highlighted, and AI prediction of what happens next. All sources cited.

### Vernacular Translation
Translate any article to Hindi, Gujarati, Tamil, Telugu, or Bengali. Not word-by-word translation — cultural context and financial term explanations included.

### 11 ET Categories
Markets · Startups · Economy · Technology · Budget · Politics · International · Jobs · Real Estate · Auto · Education

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Agent Framework | LangGraph | Multi-agent state management and orchestration |
| LLM | Groq + LLaMA 3.3 70B | Personalization, story arc, Q&A, orchestrator |
| LLM | Groq + LLaMA 3.3 70B | Vernacular translation |
| Sentiment | HuggingFace DistilBERT | Runs locally — no API key needed |
| News Search | Tavily API | Live news fetching from internet |
| News Feed | ET RSS Feeds | Direct Economic Times article feed |
| Backend | FastAPI + Uvicorn | REST API server — 8 endpoints |
| Database | SQLite | User profiles and interest scores |
| Frontend | HTML + CSS + JavaScript | Complete UI — no frameworks needed |
| Monitoring | LangSmith | Agent trace logging and debugging |

**Cost: Zero.** Every tool and API used is free tier or open source.

---

## System Architecture

```
User Request
     ↓
Orchestrator Agent  (LangGraph + LLaMA 3.3 70B)
     ↓
┌────────────────────────────────────────────┐
│                                            │
User Profiler → News Fetcher → Personalizer  │
     ↓               ↓              ↓        │
  SQLite         Tavily + RSS    LLaMA Rank  │
│                                            │
└──────────── Story Arc ── Vernacular ───────┘
                  ↓              ↓
           LLaMA + HF        LLaMA Trans
                  ↓
          Quality Guard Agent
                  ↓
         FastAPI → Frontend
```

### Agents

| Agent | LLM Used | Job |
|---|---|---|
| Orchestrator | LLaMA 3.3 70B | Receives every request, routes to correct agents |
| User Profiler | None | Reads user profile and interest scores from SQLite |
| News Fetcher | None | Fetches live articles from Tavily + ET RSS |
| Personalizer | LLaMA 3.3 70B | Ranks articles with score and reason for each user |
| Story Arc | LLaMA 3.3 70B + HuggingFace | Builds timeline, sentiment, key players, predictions |
| Vernacular | LLaMA 3.3 70B | Translates with cultural context to Indian languages |
| Q&A Agent | LLaMA 3.3 70B | Answers user questions about any article |
| Quality Guard | LLaMA 3.3 70B | Checks for hallucinations and missing citations |

---

## Project Structure

```
et_gen/
├── agents/
│   ├── orchestrator.py      # Boss agent — routes all requests
│   ├── profiler.py          # Reads user data from SQLite
│   ├── fetcher.py           # Fetches live news from Tavily + RSS
│   ├── personalizer.py      # Ranks articles using LLaMA
│   ├── story_arc.py         # Builds story timeline and sentiment
│   ├── vernacular.py        # Translates to Indian languages
│   └── qa_agent.py          # Answers questions about articles
├── api/
│   └── main.py              # FastAPI server — all endpoints
├── database/
│   └── db.py                # SQLite setup and queries
├── state/
│   └── schema.py            # Shared data structure between agents
├── frontend/
│   ├── index.html           # Main UI
│   ├── style.css            # All styling
│   └── app.js               # Frontend logic and API calls
├── .env                     # API keys (not committed to GitHub)
├── requirements.txt         # Python dependencies
└── README.md
```

---

## Setup Instructions

### Prerequisites
- Python 3.11 or higher
- Git

### Step 1 — Clone the repository

```bash
git clone https://github.com/nishit-36/et_gen.git
cd et_gen
```

### Step 2 — Create virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate
```

### Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

### Step 4 — Get free API keys

| Service | URL | Key format |
|---|---|---|
| Groq | console.groq.com | `gsk_...` |
| Tavily | app.tavily.com | `tvly-...` |
| LangSmith | smith.langchain.com | `lsv2_...` |

### Step 5 — Create .env file

Create a file named `.env` in the root folder and add:

```
GROQ_API_KEY=your_groq_key_here
TAVILY_API_KEY=your_tavily_key_here
LANGCHAIN_API_KEY=your_langsmith_key_here
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=et-news-ai
```

### Step 6 — Run the backend server

```bash
uvicorn api.main:app --reload
```

Backend runs at `http://localhost:8000`
API documentation at `http://localhost:8000/docs`

### Step 7 — Run the frontend server

Open a second terminal window:

```bash
cd frontend
python -m http.server 3000
```

### Step 8 — Open the app

Open your browser and go to:

```
http://localhost:3000
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Health check |
| GET | `/api/categories` | Get all news categories |
| POST | `/api/feed` | Get personalized news feed |
| POST | `/api/category` | Get news for specific category |
| POST | `/api/search` | Search for any topic |
| POST | `/api/story-arc` | Build story arc for a topic |
| POST | `/api/qa` | Ask AI a question about an article |
| POST | `/api/translate` | Translate article to Indian language |
| POST | `/api/save-user` | Save user profile |
| POST | `/api/track-read` | Track article reading for personalization |

---

## Team

**Team Holy Trinity** — ET Gen AI Hackathon 2026

- Vedika Tomar
- Ayushmaan Singh
- Nishit Parmar

---

## Hackathon Details

- **Event:** ET Gen AI Hackathon 2026
- **Problem Statement:** PS 8 — AI-Native News Experience
- **Partners:** Avataar.ai · Unstop
- **Category:** Multi-agent AI system with personalization and vernacular support

---

## License

This project was built for the ET Gen AI Hackathon 2026. All code is original and open source.
