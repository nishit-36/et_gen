# state/schema.py
# This file defines what data flows between all agents
# Think of it like a shared notebook every agent can read and write

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
    
    category: Optional[str]
    # example: "markets" / "all" -- which tab user clicked

    user_profile: Optional[dict]
    # full profile object stored here so all nodes can access it

    # --- WHAT USER WANTS RIGHT NOW ---
    action: str
    # example: "load_feed" / "search" / "story_arc" / "translate"

    query: Optional[str]
    # example: "Union Budget 2025" -- only filled when user searches
    # Optional means it can be empty (None) if not needed

    # --- RAW NEWS FROM FETCHER AGENT ---
    raw_articles: List[dict]
    # example: [{"title": "Nifty crosses 24500", "summary": "...", "url": "...", "category": "markets"}]
    # This is filled by News Fetcher Agent
    # Empty list [] at start

    # --- PERSONALIZED FEED FROM PERSONALIZER AGENT ---
    personalized_feed: List[dict]
    # Same articles but now ranked by relevance for this specific user
    # Filled by Personalizer Agent after it receives raw_articles

    # --- DEEP BRIEFING FROM BRIEFING WRITER ---
    briefing: Optional[str]
    # Full deep briefing text on a topic
    # Only filled when user clicks Deep Briefing button

    # --- STORY ARC FROM STORY ARC AGENT ---
    story_arc: Optional[dict]
    # example: {"timeline": [...], "key_players": [...], "sentiment": {...}, "predictions": "..."}
    # Only filled when user clicks Story Arc button

    # --- TRANSLATED CONTENT FROM VERNACULAR AGENT ---
    translated_content: Optional[str]
    # Translated version of article text
    # Only filled when user clicks Translate button

    # --- ERROR TRACKING ---
    error: Optional[str]
    # If anything goes wrong, error message is stored here
    # None means everything is working fine

    # --- RETRY COUNT ---
    retry_count: int
    # How many times we tried if something failed
    # Starts at 0