# agents/personalizer.py
# This agent ranks articles based on user's interest profile
# Uses Groq LLaMA 3.3 70B to understand and rank articles
# Input: user profile + raw articles
# Output: same articles but sorted by relevance for this user

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from groq import Groq
from dotenv import load_dotenv
import json

load_dotenv()

# Initialize Groq client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def rank_articles_with_llm(user_profile: dict, articles: list) -> list:
    # This function sends user profile + articles to LLaMA
    # LLaMA scores each article 0.0 to 1.0 based on relevance
    # Higher score = more relevant for this user

    if not articles:
        return []

    # Build a simple text summary of user profile
    # We send this to LLaMA so it understands who the user is
    profile_text = f"""
User Profile:
- Profession: {user_profile.get('profession', 'general')}
- Interests: {', '.join(user_profile.get('interests', []))}
- Interest Scores: {user_profile.get('interest_scores', {})}
"""

    # Build article list text to send to LLaMA
    # We only send title and category - summary is too long
    articles_text = ""
    for i, article in enumerate(articles):
        articles_text += f"{i}. [{article['category']}] {article['title']}\n"

    # This is the prompt we send to LLaMA
    # We ask it to return JSON so we can parse it easily
    prompt = f"""
You are a news personalization engine.

{profile_text}

Here are {len(articles)} news articles:
{articles_text}

Score each article from 0.0 to 1.0 based on relevance to this user.
1.0 = perfectly matches user interests
0.0 = completely irrelevant to user

Rules:
- Investor interested in markets should get high scores for market news
- Student should get higher scores for explainer and economy articles
- If user has no specific interests, give all articles score 0.5

Return ONLY a JSON array of scores in this exact format:
[0.9, 0.3, 0.8, 0.5, ...]

Return nothing else. Just the JSON array.
"""

    try:
        print("Personalizer: Asking LLaMA to rank articles...")
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            # temperature 0.1 means very consistent results
            # lower = more predictable, higher = more creative
            max_tokens=200
        )

        response_text = response.choices[0].message.content.strip()
        print(f"Personalizer: LLaMA response: {response_text[:100]}...")

        # Parse the JSON array from LLaMA response
        # LLaMA should return something like [0.9, 0.3, 0.8, ...]
        scores = json.loads(response_text)

        # Make sure we got same number of scores as articles
        if len(scores) != len(articles):
            print(f"Personalizer: Score count mismatch - using equal scores")
            scores = [0.5] * len(articles)

    except Exception as e:
        # If LLaMA fails for any reason
        # Fall back to interest score based ranking
        print(f"Personalizer: LLaMA ranking failed - {str(e)}")
        print("Personalizer: Using interest score fallback ranking")
        scores = []
        interest_scores = user_profile.get("interest_scores", {})
        for article in articles:
            category = article.get("category", "general")
            score = interest_scores.get(category, 0.5)
            scores.append(score)

    # Attach scores to articles
    for i, article in enumerate(articles):
        article["relevance_score"] = round(scores[i], 2)

    # Sort articles by relevance score - highest first
    ranked = sorted(articles, key=lambda x: x["relevance_score"], reverse=True)

    return ranked

def run_personalizer(user_profile: dict, raw_articles: list) -> dict:
    # This is the main function of Personalizer Agent
    # Input:
    #   user_profile  = output from Profiler Agent
    #   raw_articles  = output from Fetcher Agent
    # Output: ranked articles dictionary

    print(f"\nPersonalizer Agent started")
    print(f"  User: {user_profile.get('user_id')}")
    print(f"  Profession: {user_profile.get('profession')}")
    print(f"  Articles to rank: {len(raw_articles)}")

    if not raw_articles:
        print("Personalizer: No articles to rank")
        return {"ranked_articles": [], "total": 0}

    # Check if new user with no reading history
    is_new_user = user_profile.get("is_new_user", True)

    if is_new_user and not user_profile.get("interests"):
        # Brand new user - no personalization data yet
        # Just return articles as-is with equal scores
        print("Personalizer: New user - showing all articles equally")
        for article in raw_articles:
            article["relevance_score"] = 0.5
        return {
            "ranked_articles": raw_articles,
            "total": len(raw_articles),
            "personalized": False
        }

    # Existing user - rank using LLaMA
    ranked_articles = rank_articles_with_llm(user_profile, raw_articles)

    print(f"Personalizer: Ranking complete")
    print(f"  Top article: {ranked_articles[0]['title'][:50]}...")
    print(f"  Top score:   {ranked_articles[0]['relevance_score']}")

    return {
        "ranked_articles": ranked_articles,
        "total": len(ranked_articles),
        "personalized": True
    }


# Test this agent directly
if __name__ == "__main__":
    print("=" * 40)
    print("Testing Personalizer Agent")
    print("=" * 40)

    # First get some real articles using fetcher
    from agents.fetcher import run_fetcher
    from agents.profiler import run_profiler

    # Test 1 - Investor user
    print("\nTest 1: Investor interested in markets")
    fetch_result = run_fetcher(action="fetch_all", count=2)
    raw_articles  = fetch_result["articles"]

    # Use existing user_123 from our database test
    user_profile = run_profiler("user_123")

    result = run_personalizer(user_profile, raw_articles)

    print(f"\nTop 3 ranked articles for investor:")
    for i, article in enumerate(result["ranked_articles"][:3]):
        print(f"  {i+1}. [{article['relevance_score']}] {article['title'][:60]}")

    # Test 2 - New user
    print("\nTest 2: Brand new user (no history)")
    new_profile = run_profiler("brand_new_user_456")
    result2     = run_personalizer(new_profile, raw_articles)
    print(f"New user articles (all equal score 0.5):")
    for article in result2["ranked_articles"][:3]:
        print(f"  [{article['relevance_score']}] {article['title'][:60]}")

    print("\nPersonalizer Agent working correctly!")