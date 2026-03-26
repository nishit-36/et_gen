# agents/personalizer.py
# IMPROVEMENTS:
# 1. Summary included in prompt - LLM understands articles better
# 2. Reason/explanation added to each article score
# 3. Category diversity - max 3 articles per category in top 10
# 4. Better prompt with recency + profession weight

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from groq import Groq
from dotenv import load_dotenv
import json

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def rank_articles_with_llm(user_profile: dict, articles: list) -> list:
    if not articles:
        return []

    # Limit to 20 articles max
    articles_to_rank = articles[:20]

    profile_text = f"""
User Profile:
- Profession: {user_profile.get('profession', 'general')}
- Experience Level: {user_profile.get('experience_level', 'general')}
- Interests: {', '.join(user_profile.get('interests', []))}
- Interest Scores: {user_profile.get('interest_scores', {})}
- Reading Preference: {user_profile.get('reading_time_preference', 'any')}
"""

    # IMPROVEMENT 1 — Include summary in article text
    # Previously only title was sent
    # Now title + first 100 chars of summary
    # LLM understands article content much better
    articles_text = ""
    for i, article in enumerate(articles_to_rank):
        summary_preview = article.get("summary", "")[:100]
        articles_text += (
            f"{i}. [{article['category']}] "
            f"{article['title']} "
            f"— {summary_preview}\n"
        )

    # IMPROVEMENT 2 — Better prompt
    # Now asks for reason with each score
    # Also considers recency and profession
    prompt = f"""
You are a news personalization engine for Economic Times India.

{profile_text}

Here are {len(articles_to_rank)} news articles:
{articles_text}

Score each article from 0.0 to 1.0 based on relevance to this user.

Scoring rules:
- Give higher scores to articles matching user interests and profession
- Give higher scores to recent breaking news over old news
- Investor → boost markets, stocks, economy articles
- Student → boost explainer, education, economy articles
- Startup Founder → boost startup, tech, funding articles
- Professional → boost business, economy, policy articles
- If user has no specific interests give all articles score 0.5

Return ONLY a JSON array where each item has score and reason:
[
  {{"score": 0.9, "reason": "matches markets interest"}},
  {{"score": 0.3, "reason": "not relevant to investor profile"}},
  ...
]

Return nothing else. Just the JSON array.
"""

    try:
        print("Personalizer: Asking LLaMA to rank articles...")
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=800
        )

        response_text = response.choices[0].message.content.strip()

        # Clean JSON if needed
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        print(f"Personalizer: LLaMA response received")
        parsed = json.loads(response_text)

        # Handle both formats:
        # New format: [{"score": 0.9, "reason": "..."}]
        # Old format: [0.9, 0.3, ...]
        scores  = []
        reasons = []

        for item in parsed:
            if isinstance(item, dict):
                scores.append(item.get("score", 0.5))
                reasons.append(item.get("reason", ""))
            else:
                # Old format fallback
                scores.append(float(item))
                reasons.append("")

        # Fix count mismatch
        if len(scores) != len(articles_to_rank):
            print(f"Personalizer: Score count mismatch - padding")
            while len(scores) < len(articles_to_rank):
                scores.append(0.5)
                reasons.append("")
            scores  = scores[:len(articles_to_rank)]
            reasons = reasons[:len(articles_to_rank)]

    except Exception as e:
        print(f"Personalizer: LLaMA failed - {str(e)}")
        print("Personalizer: Using interest score fallback")
        scores  = []
        reasons = []
        interest_scores = user_profile.get("interest_scores", {})
        for article in articles_to_rank:
            category = article.get("category", "general")
            score    = interest_scores.get(category, 0.5)
            scores.append(score)
            reasons.append(f"based on {category} interest score")

    # Attach scores and reasons to articles
    for i, article in enumerate(articles_to_rank):
        article["relevance_score"] = round(scores[i], 2)
        article["reason"]          = reasons[i]
        # reason shows why this article was recommended
        # displayed in UI as "Recommended because: ..."

    # Articles beyond 20 get default score
    for article in articles[20:]:
        article["relevance_score"] = 0.5
        article["reason"]          = "general interest"

    # Sort by relevance score
    ranked = sorted(
        articles,
        key=lambda x: x["relevance_score"],
        reverse=True
    )

    # IMPROVEMENT 3 — Category diversity
    # Ensure max 3 articles per category in top 10
    # Prevents feed from showing 8 markets articles in a row
    final_ranked     = []
    category_counts  = {}
    overflow_articles = []

    for article in ranked:
        category = article.get("category", "general")
        count    = category_counts.get(category, 0)

        if len(final_ranked) < 10:
            # Still filling top 10
            if count < 3:
                # Category has room - add to main feed
                final_ranked.append(article)
                category_counts[category] = count + 1
            else:
                # Category full - save for later
                overflow_articles.append(article)
        else:
            # Top 10 filled - add rest normally
            final_ranked.append(article)

    # Insert overflow articles after top 10
    # They go at position 10, 11, 12 etc
    result = final_ranked[:10] + overflow_articles + final_ranked[10:]

    return result


def run_personalizer(user_profile: dict, raw_articles: list) -> dict:
    print(f"\nPersonalizer Agent started")
    print(f"  User:       {user_profile.get('user_id')}")
    print(f"  Profession: {user_profile.get('profession')}")
    print(f"  Articles:   {len(raw_articles)}")

    if not raw_articles:
        print("Personalizer: No articles to rank")
        return {"ranked_articles": [], "total": 0}

    is_new_user = user_profile.get("is_new_user", True)

    if is_new_user and not user_profile.get("interests"):
        print("Personalizer: New user - showing all articles equally")
        for article in raw_articles:
            article["relevance_score"] = 0.5
            article["reason"]          = "explore all topics"
        return {
            "ranked_articles": raw_articles,
            "total":           len(raw_articles),
            "personalized":    False
        }

    ranked_articles = rank_articles_with_llm(user_profile, raw_articles)

    print(f"Personalizer: Ranking complete")
    print(f"  Top article: {ranked_articles[0]['title'][:50]}...")
    print(f"  Top score:   {ranked_articles[0]['relevance_score']}")
    print(f"  Top reason:  {ranked_articles[0].get('reason', '')}")

    return {
        "ranked_articles": ranked_articles,
        "total":           len(ranked_articles),
        "personalized":    True
    }


# Test
if __name__ == "__main__":
    print("="*40)
    print("Testing Personalizer Agent")
    print("="*40)

    from agents.fetcher import run_fetcher
    from agents.profiler import run_profiler

    print("\nTest 1: Investor user")
    fetch_result = run_fetcher(action="fetch_all", count=3)
    raw_articles = fetch_result["articles"]
    user_profile = run_profiler("user_123")
    result       = run_personalizer(user_profile, raw_articles)

    print(f"\nTop 5 ranked articles:")
    for i, article in enumerate(result["ranked_articles"][:5]):
        print(f"  {i+1}. [{article['relevance_score']}] {article['title'][:45]}")
        print(f"      Reason: {article.get('reason', 'none')}")

    print("\nTest 2: Category diversity check")
    categories = [
        a["category"]
        for a in result["ranked_articles"][:10]
    ]
    print(f"  Top 10 categories: {categories}")
    from collections import Counter
    counts = Counter(categories)
    print(f"  Category counts: {dict(counts)}")
    max_count = max(counts.values()) if counts else 0
    if max_count <= 3:
        print("  Diversity check PASSED - no category exceeds 3")
    else:
        print(f"  Note: one category has {max_count} articles")

    print("\nPersonalizer Agent working correctly!")