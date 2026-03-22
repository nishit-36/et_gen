# agents/orchestrator.py
# This is the boss agent that connects all other agents
# Every user request comes here first
# It decides which agents to call and in what order
# Uses LangGraph StateGraph to manage the flow

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
# STEP 1 — Define each agent as a node
# A node is just a function that receives
# the shared state and returns updated state
# ─────────────────────────────────────────

def profiler_node(state: NewsState) -> NewsState:
    # Reads user profile from database
    print("\n[Orchestrator] Running Profiler Node...")
    profile = run_profiler(state["user_id"])
    # Update state with profile data
    state["profession"]      = profile["profession"]
    state["interests"]       = profile["interests"]
    state["language"]        = profile["language"]
    # Store full profile in state for other agents
    state["user_profile"]    = profile
    return state

def fetcher_node(state: NewsState) -> NewsState:
    # Fetches live news based on action type
    print("\n[Orchestrator] Running Fetcher Node...")
    action   = state.get("action", "fetch_all")
    category = state.get("category", "all")
    query    = state.get("query", None)

    result = run_fetcher(
        action=action if action in ["fetch_all","fetch_category","fetch_search"] else "fetch_all",
        category=category,
        query=query,
        count=5
    )
    state["raw_articles"] = result["articles"]
    return state

def personalizer_node(state: NewsState) -> NewsState:
    # Ranks articles for this specific user
    print("\n[Orchestrator] Running Personalizer Node...")
    profile      = state.get("user_profile", {})
    raw_articles = state.get("raw_articles", [])

    result = run_personalizer(profile, raw_articles)
    state["personalized_feed"] = result["ranked_articles"]
    return state

def story_arc_node(state: NewsState) -> NewsState:
    # Builds story arc for a topic
    print("\n[Orchestrator] Running Story Arc Node...")
    query        = state.get("query", "latest news")
    raw_articles = state.get("raw_articles", [])

    result = run_story_arc(query, raw_articles)
    state["story_arc"] = result
    return state

def vernacular_node(state: NewsState) -> NewsState:
    # Translates content to user's language
    print("\n[Orchestrator] Running Vernacular Node...")
    language = state.get("language", "english")
    feed     = state.get("personalized_feed", [])

    if language != "english" and feed:
        # Translate only top 3 articles to save time
        translated = []
        for article in feed[:3]:
            t = run_vernacular(article.copy(), language)
            translated.append(t)
        # Replace top 3 with translated versions
        state["personalized_feed"] = translated + feed[3:]

    return state

# ─────────────────────────────────────────
# STEP 2 — Define routing logic
# This function decides which node to go to
# based on what the user wants to do
# ─────────────────────────────────────────

def route_action(state: NewsState) -> str:
    # This is the router - reads action from state
    # Returns name of next node to run
    action = state.get("action", "load_feed")
    print(f"\n[Orchestrator] Routing action: {action}")

    if action == "load_feed":
        return "fetch_news"
    elif action == "fetch_category":
        return "fetch_news"
    elif action == "fetch_search":
        return "fetch_news"
    elif action == "story_arc":
        return "fetch_for_arc"
    elif action == "translate":
        return "translate_only"
    else:
        return "fetch_news"

def route_after_fetch(state: NewsState) -> str:
    # After fetching news decide what to do next
    action = state.get("action", "load_feed")

    if action == "story_arc":
        return "build_arc"
    else:
        return "personalize"

# ─────────────────────────────────────────
# STEP 3 — Build the graph
# Graph = all nodes connected with edges
# Edges = arrows showing what runs after what
# ─────────────────────────────────────────

def build_graph():
    # Create the StateGraph with our NewsState schema
    graph = StateGraph(NewsState)

    # Add all agent nodes to graph
    graph.add_node("profile_user",  profiler_node)
    graph.add_node("fetch_news",    fetcher_node)
    graph.add_node("personalize",   personalizer_node)
    graph.add_node("build_arc",     story_arc_node)
    graph.add_node("translate",     vernacular_node)

    # Set entry point - always start with profiler
    graph.set_entry_point("profile_user")

    # After profiling - route based on action
    graph.add_conditional_edges(
        "profile_user",
        route_action,
        {
            "fetch_news":     "fetch_news",
            "fetch_for_arc":  "fetch_news",
            "translate_only": "translate",
        }
    )

    # After fetching - route based on action
    graph.add_conditional_edges(
        "fetch_news",
        route_after_fetch,
        {
            "build_arc":   "build_arc",
            "personalize": "personalize",
        }
    )

    # After personalizing - always translate
    graph.add_edge("personalize", "translate")

    # After translate - done
    graph.add_edge("translate", END)

    # After arc - done
    graph.add_edge("build_arc", END)

    # Compile the graph into a runnable app
    app = graph.compile()
    return app

# ─────────────────────────────────────────
# STEP 4 — Main run function
# This is what FastAPI will call
# ─────────────────────────────────────────

def run_orchestrator(
    user_id:  str,
    action:   str = "load_feed",
    category: str = "all",
    query:    str = None,
    language: str = "english"
) -> dict:
    # This is the single entry point for all requests
    # FastAPI calls this function for every user action

    print(f"\n{'='*40}")
    print(f"Orchestrator started")
    print(f"  user_id:  {user_id}")
    print(f"  action:   {action}")
    print(f"  category: {category}")
    print(f"  query:    {query}")
    print(f"{'='*40}")

    # Build initial state
    initial_state: NewsState = {
        "user_id":          user_id,
        "profession":       "general",
        "interests":        [],
        "language":         language,
        "action":           action,
        "category":         category,
        "query":            query,
        "raw_articles":     [],
        "personalized_feed":[],
        "briefing":         None,
        "story_arc":        None,
        "translated_content": None,
        "error":            None,
        "retry_count":      0,
        "user_profile":     {}
    }

    try:
        # Build and run the graph
        app    = build_graph()
        result = app.invoke(initial_state)

        print(f"\n[Orchestrator] Completed successfully!")

        # Return clean result based on action
        if action == "story_arc":
            return {
                "status":    "success",
                "action":    action,
                "story_arc": result.get("story_arc", {})
            }
        else:
            return {
                "status":   "success",
                "action":   action,
                "feed":     result.get("personalized_feed", []),
                "total":    len(result.get("personalized_feed", []))
            }

    except Exception as e:
        print(f"\n[Orchestrator] Error: {str(e)}")
        return {
            "status": "error",
            "error":  str(e),
            "feed":   []
        }


# Test orchestrator directly
if __name__ == "__main__":
    print("=" * 40)
    print("Testing Orchestrator")
    print("=" * 40)

    # Test 1 - Load feed for investor
    print("\nTest 1: Load personalized feed")
    result = run_orchestrator(
        user_id  = "user_123",
        action   = "load_feed",
        language = "english"
    )
    print(f"Status: {result['status']}")
    print(f"Total articles: {result['total']}")
    if result["feed"]:
        print("Top 3 articles:")
        for a in result["feed"][:3]:
            print(f"  [{a.get('relevance_score',0)}] {a['title'][:55]}")

    # Test 2 - Story arc
    print("\nTest 2: Story arc for RBI")
    result2 = run_orchestrator(
        user_id = "user_123",
        action  = "story_arc",
        query   = "RBI repo rate decision"
    )
    print(f"Status: {result2['status']}")
    if result2.get("story_arc"):
        arc = result2["story_arc"]
        print(f"Summary: {arc.get('summary','')[:100]}...")
        print(f"Timeline events: {len(arc.get('timeline',[]))}")

    print("\nOrchestrator working correctly!")