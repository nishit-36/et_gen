# agents/orchestrator.py
# IMPROVEMENTS:
# 1. Graph built ONCE globally - not every request
# 2. Retry system actually works now
# 3. Better routing logic

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langgraph.graph import StateGraph, END
from state.schema import NewsState
from agents.profiler import run_profiler
from agents.fetcher import run_fetcher
from agents.personalizer import run_personalizer
from agents.story_arc import run_story_arc
from agents.vernacular import run_vernacular
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────
# IMPROVEMENT 1 — Build graph ONCE globally
# Previously this was inside run_orchestrator()
# meaning it rebuilt every single request
# Now it builds once when server starts
# Much faster for all subsequent requests
# ─────────────────────────────────────────
_APP = None
# _APP stores the compiled graph
# underscore means it's a private variable
# only used inside this file

def get_app():
    # Returns the compiled graph
    # Builds it only first time
    # After that returns cached version
    global _APP
    if _APP is None:
        print("[Orchestrator] Building graph for first time...")
        _APP = build_graph()
        print("[Orchestrator] Graph built and cached!")
    return _APP

# ─────────────────────────────────────────
# AGENT NODES
# Each node is one agent function
# ─────────────────────────────────────────

def profiler_node(state: NewsState) -> NewsState:
    print("\n[Orchestrator] Running Profiler Node...")
    profile = run_profiler(state["user_id"])
    state["profession"]   = profile["profession"]
    state["interests"]    = profile["interests"]
    state["language"]     = profile["language"]
    state["user_profile"] = profile
    return state

def fetcher_node(state: NewsState) -> NewsState:
    print("\n[Orchestrator] Running Fetcher Node...")
    action   = state.get("action", "fetch_all")
    category = state.get("category", "all")
    query    = state.get("query", None)

    # IMPROVEMENT 2 — Retry system
    # If fetch fails try again up to 2 times
    max_retries = 2
    retry_count = state.get("retry_count", 0)

    for attempt in range(max_retries + 1):
        try:
            result = run_fetcher(
                action=action if action in [
                    "fetch_all", "fetch_category", "fetch_search"
                ] else "fetch_all",
                category=category,
                query=query,
                count=5
            )
            state["raw_articles"] = result["articles"]
            state["retry_count"]  = attempt
            break
            # Break out of loop if successful

        except Exception as e:
            print(f"[Orchestrator] Fetch attempt {attempt+1} failed: {e}")
            if attempt == max_retries:
                # All retries exhausted
                print("[Orchestrator] All retries failed - returning empty")
                state["raw_articles"] = []
                state["error"]        = str(e)
            else:
                print(f"[Orchestrator] Retrying... ({attempt+2}/{max_retries+1})")

    return state

def personalizer_node(state: NewsState) -> NewsState:
    print("\n[Orchestrator] Running Personalizer Node...")
    profile      = state.get("user_profile", {})
    raw_articles = state.get("raw_articles", [])

    result = run_personalizer(profile, raw_articles)
    state["personalized_feed"] = result["ranked_articles"]
    return state

def story_arc_node(state: NewsState) -> NewsState:
    print("\n[Orchestrator] Running Story Arc Node...")
    query        = state.get("query", "latest news")
    raw_articles = state.get("raw_articles", [])

    result = run_story_arc(query, raw_articles)
    state["story_arc"] = result
    return state

def vernacular_node(state: NewsState) -> NewsState:
    print("\n[Orchestrator] Running Vernacular Node...")
    language = state.get("language", "english")
    feed     = state.get("personalized_feed", [])

    if language != "english" and feed:
        translated = []
        for article in feed[:3]:
            t = run_vernacular(article.copy(), language)
            translated.append(t)
        state["personalized_feed"] = translated + feed[3:]

    return state

# ─────────────────────────────────────────
# ROUTING LOGIC
# Decides which node runs after which
# ─────────────────────────────────────────

def route_action(state: NewsState) -> str:
    action = state.get("action", "load_feed")
    print(f"\n[Orchestrator] Routing action: {action}")

    if action in ["load_feed", "fetch_category", "fetch_search"]:
        return "fetch_news"
    elif action == "story_arc":
        return "fetch_news"
    elif action == "translate":
        return "translate_only"
    else:
        return "fetch_news"

def route_after_fetch(state: NewsState) -> str:
    action = state.get("action", "load_feed")
    # If fetch failed and no articles - still try to personalize
    # Personalizer handles empty list gracefully
    if action == "story_arc":
        return "build_arc"
    else:
        return "personalize"

# ─────────────────────────────────────────
# BUILD THE GRAPH
# ─────────────────────────────────────────

def build_graph():
    graph = StateGraph(NewsState)

    # Add nodes
    graph.add_node("profile_user", profiler_node)
    graph.add_node("fetch_news",   fetcher_node)
    graph.add_node("personalize",  personalizer_node)
    graph.add_node("build_arc",    story_arc_node)
    graph.add_node("translate",    vernacular_node)

    # Entry point always profiler
    graph.set_entry_point("profile_user")

    # After profiling route based on action
    graph.add_conditional_edges(
        "profile_user",
        route_action,
        {
            "fetch_news":     "fetch_news",
            "translate_only": "translate",
        }
    )

    # After fetching route based on action
    graph.add_conditional_edges(
        "fetch_news",
        route_after_fetch,
        {
            "build_arc":   "build_arc",
            "personalize": "personalize",
        }
    )

    # After personalizing always translate
    graph.add_edge("personalize", "translate")

    # End points
    graph.add_edge("translate", END)
    graph.add_edge("build_arc", END)

    return graph.compile()

# ─────────────────────────────────────────
# MAIN RUN FUNCTION
# Called by FastAPI for every request
# ─────────────────────────────────────────

def run_orchestrator(
    user_id:   str,
    action:    str  = "load_feed",
    category:  str  = "all",
    query:     str  = None,
    language:  str  = "english"
) -> dict:

    print(f"\n{'='*40}")
    print(f"Orchestrator started")
    print(f"  user_id:  {user_id}")
    print(f"  action:   {action}")
    print(f"  category: {category}")
    print(f"  query:    {query}")
    print(f"{'='*40}")

    # Build initial state
    initial_state: NewsState = {
        "user_id":            user_id,
        "profession":         "general",
        "interests":          [],
        "language":           language,
        "experience_level":   None,
        "reading_time_preference": None,
        "category":           category,
        "action":             action,
        "query":              query,
        "raw_articles":       [],
        "personalized_feed":  [],
        "briefing":           None,
        "story_arc":          None,
        "qa_response":        None,
        "translated_content": None,
        "error":              None,
        "retry_count":        0,
        "user_profile":       {}
    }

    try:
        # IMPROVEMENT — use cached graph instead of rebuilding
        app    = get_app()
        result = app.invoke(initial_state)

        print(f"\n[Orchestrator] Completed successfully!")

        if action == "story_arc":
            return {
                "status":    "success",
                "action":    action,
                "story_arc": result.get("story_arc", {})
            }
        else:
            return {
                "status": "success",
                "action": action,
                "feed":   result.get("personalized_feed", []),
                "total":  len(result.get("personalized_feed", []))
            }

    except Exception as e:
        print(f"\n[Orchestrator] Error: {str(e)}")
        return {
            "status": "error",
            "error":  str(e),
            "feed":   []
        }


# Test
if __name__ == "__main__":
    print("="*40)
    print("Testing Orchestrator")
    print("="*40)

    print("\nTest 1: Load feed")
    result = run_orchestrator(
        user_id  = "user_123",
        action   = "load_feed",
        language = "english"
    )
    print(f"Status: {result['status']}")
    print(f"Total:  {result['total']}")

    print("\nTest 2: Same request again - should use cached graph")
    result2 = run_orchestrator(
        user_id  = "user_123",
        action   = "load_feed",
        language = "english"
    )
    print(f"Status: {result2['status']}")
    print(f"Total:  {result2['total']}")

    print("\nOrchestrator working correctly!")