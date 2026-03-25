# state/schema.py
# Shared data structure that flows between all agents
# Every agent reads from and writes to this state

from typing import TypedDict, List, Optional

class NewsState(TypedDict):

    # --- WHO IS THE USER ---
    user_id: str
    # example: "user_123"

    profession: str
    # example: "investor" / "student" / "startup_founder"

    interests: List[str]
    # example: ["markets", "startups", "economy"]

    language: str
    # example: "english" / "hindi" / "gujarati"

    # NEW - experience level and reading preference
    experience_level: Optional[str]
    # example: "student" / "professional" / "expert"

    reading_time_preference: Optional[str]
    # example: "short" / "long" / "any"

    category: Optional[str]
    # example: "markets" / "all" / "politics" / "jobs"

    user_profile: Optional[dict]
    # full profile object stored here so all nodes can access it

    # --- WHAT USER WANTS RIGHT NOW ---
    action: str
    # example: "load_feed" / "search" / "story_arc" / "translate" / "qa"

    query: Optional[str]
    # example: "Union Budget 2025"
    # only filled when user searches or asks a question

    # --- RAW NEWS FROM FETCHER AGENT ---
    raw_articles: List[dict]
    # example: [{"title": "...", "summary": "...", "url": "...", "category": "markets"}]
    # filled by News Fetcher Agent
    # empty list [] at start

    # --- PERSONALIZED FEED FROM PERSONALIZER AGENT ---
    personalized_feed: List[dict]
    # same articles but ranked by relevance for this specific user
    # each article now also has:
    #   "relevance_score": 0.9
    #   "reason": "matches your markets interest"  <-- NEW
    # filled by Personalizer Agent

    # --- DEEP BRIEFING ---
    briefing: Optional[str]
    # full deep briefing text on a topic
    # only filled when user clicks Deep Briefing button

    # --- STORY ARC FROM STORY ARC AGENT ---
    story_arc: Optional[dict]
    # example: {
    #   "timeline": [...],
    #   "key_players": [...],
    #   "sentiment": {...},
    #   "predictions": "...",
    #   "sources_used": [...]   <-- NEW
    # }
    # only filled when user clicks Story Arc button

    # --- Q&A RESPONSE FROM QA AGENT ---  <-- NEW
    qa_response: Optional[str]
    # answer to user's question about an article
    # example: "RBI kept rates unchanged because inflation..."
    # only filled when user asks a question about an article

    # --- TRANSLATED CONTENT FROM VERNACULAR AGENT ---
    translated_content: Optional[str]
    # translated version of article text
    # only filled when user clicks Translate button

    # --- ERROR TRACKING ---
    error: Optional[str]
    # if anything goes wrong error message stored here
    # None means everything working fine

    # --- RETRY COUNT ---
    retry_count: int
    # how many times we tried if something failed
    # starts at 0, max 2 retries