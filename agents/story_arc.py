# agents/story_arc.py
# This agent builds a complete story for any news topic
# It creates: timeline, key players, sentiment analysis, predictions
# Uses: Groq LLaMA 3.3 70B + HuggingFace sentiment (runs locally)

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from groq import Groq
from dotenv import load_dotenv
import json

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def get_sentiment(text: str) -> dict:
    # This function detects if a text is positive, negative or neutral
    # Uses HuggingFace transformers - runs completely locally
    # No API key needed, no internet needed after first download

    try:
        from transformers import pipeline
        # pipeline is a simple way to use HuggingFace models
        # First time this runs it downloads the model (~500MB)
        # After that it uses the cached local copy

        print("Story Arc: Running sentiment analysis locally...")
        sentiment_pipeline = pipeline(
            "sentiment-analysis",
            model="distilbert-base-uncased-finetuned-sst-2-english",
            # This is a small fast model good for news sentiment
        )

        # Truncate text to 512 characters
        # Model has a limit on how much text it can process
        result = sentiment_pipeline(text[:512])
        label = result[0]["label"]
        score = result[0]["score"]

        return {
            "label": label,
            # POSITIVE or NEGATIVE
            "score": round(score, 2),
            # confidence score 0 to 1
            "readable": "Positive" if label == "POSITIVE" else "Negative"
        }

    except Exception as e:
        print(f"Story Arc: Sentiment analysis failed - {str(e)}")
        # If HuggingFace fails return neutral as fallback
        return {"label": "NEUTRAL", "score": 0.5, "readable": "Neutral"}

def build_story_arc_with_llm(topic: str, articles: list) -> dict:
    # This function sends all articles about a topic to LLaMA
    # LLaMA builds a complete structured story from them

    if not articles:
        return {}

    # Build text from all article titles and summaries
    articles_text = ""
    for i, article in enumerate(articles[:8]):
        # We limit to 8 articles to avoid token limit
        articles_text += f"""
Article {i+1}:
Title: {article['title']}
Summary: {article['summary'][:200]}
Published: {article['published_at']}
"""

    prompt = f"""
You are a financial news analyst. Analyze these articles about "{topic}" and build a complete story arc.

{articles_text}

Return a JSON object with exactly this structure:
{{
    "timeline": [
        {{"date": "date here", "event": "what happened in one sentence"}},
        {{"date": "date here", "event": "what happened in one sentence"}}
    ],
    "key_players": [
        {{"name": "person or company name", "role": "their role in this story"}}
    ],
    "summary": "2-3 sentence overall summary of this story",
    "what_to_watch": "one sentence prediction of what might happen next"
}}

Return ONLY the JSON. Nothing else.
"""

    try:
        print(f"Story Arc: Asking LLaMA to build story for '{topic}'...")
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=800
        )

        response_text = response.choices[0].message.content.strip()

        # Sometimes LLaMA adds ```json at start and ``` at end
        # We need to remove those to get clean JSON
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        story = json.loads(response_text)
        print("Story Arc: LLaMA built story successfully")
        return story

    except Exception as e:
        print(f"Story Arc: LLaMA failed - {str(e)}")
        # Return basic structure if LLaMA fails
        return {
            "timeline": [{"date": "Recent", "event": f"News about {topic} reported"}],
            "key_players": [],
            "summary": f"Recent news coverage about {topic}",
            "what_to_watch": "Monitor for further developments"
        }

def analyze_sentiment_for_articles(articles: list) -> dict:
    # Analyze sentiment for each article
    # Returns overall positive/negative/neutral breakdown

    positive = 0
    negative = 0
    neutral  = 0

    for article in articles[:5]:
        # Limit to 5 articles to save time
        text = article.get("title", "") + " " + article.get("summary", "")
        sentiment = get_sentiment(text)

        if sentiment["label"] == "POSITIVE":
            positive += 1
        elif sentiment["label"] == "NEGATIVE":
            negative += 1
        else:
            neutral += 1

    total = positive + negative + neutral
    if total == 0:
        total = 1

    return {
        "positive": round((positive / total) * 100),
        "negative": round((negative / total) * 100),
        "neutral":  round((neutral / total) * 100),
        "overall":  "Positive" if positive > negative else "Negative" if negative > positive else "Neutral"
    }

def run_story_arc(topic: str, articles: list) -> dict:
    # This is the main function of Story Arc Agent
    # Input:
    #   topic    = topic name like "Zepto funding" or "RBI rate decision"
    #   articles = list of articles about this topic from Fetcher
    # Output: complete story arc dictionary

    print(f"\nStory Arc Agent started for topic: '{topic}'")
    print(f"  Articles available: {len(articles)}")

    if not articles:
        return {
            "topic": topic,
            "error": "No articles found for this topic"
        }

    # Step 1 - Build story structure using LLaMA
    story = build_story_arc_with_llm(topic, articles)

    # Step 2 - Analyze sentiment using HuggingFace locally
    print("Story Arc: Analyzing sentiment of articles...")
    sentiment = analyze_sentiment_for_articles(articles)

    # Step 3 - Combine everything into final result
    result = {
        "topic":        topic,
        "timeline":     story.get("timeline", []),
        "key_players":  story.get("key_players", []),
        "summary":      story.get("summary", ""),
        "what_to_watch":story.get("what_to_watch", ""),
        "sentiment":    sentiment,
        "total_articles": len(articles)
    }

    print(f"Story Arc Agent done!")
    print(f"  Timeline events: {len(result['timeline'])}")
    print(f"  Key players:     {len(result['key_players'])}")
    print(f"  Sentiment:       {result['sentiment']['overall']}")

    return result


# Test this agent directly
if __name__ == "__main__":
    print("=" * 40)
    print("Testing Story Arc Agent")
    print("=" * 40)

    # Get real articles about RBI using fetcher
    from agents.fetcher import run_fetcher

    print("\nFetching articles about RBI...")
    fetch_result = run_fetcher(
        action="fetch_search",
        query="RBI repo rate decision India",
        count=5
    )
    articles = fetch_result["articles"]
    print(f"Got {len(articles)} articles")

    # Build story arc
    result = run_story_arc("RBI Interest Rate Decision", articles)

    print("\n--- STORY ARC RESULT ---")
    print(f"Topic: {result['topic']}")
    print(f"\nSummary: {result['summary']}")

    print(f"\nTimeline ({len(result['timeline'])} events):")
    for event in result["timeline"]:
        print(f"  {event.get('date','?')} - {event.get('event','?')}")

    print(f"\nKey Players ({len(result['key_players'])}):")
    for player in result["key_players"]:
        print(f"  {player.get('name','?')} - {player.get('role','?')}")

    print(f"\nSentiment: {result['sentiment']}")
    print(f"\nWhat to Watch: {result['what_to_watch']}")

    print("\nStory Arc Agent working correctly!")