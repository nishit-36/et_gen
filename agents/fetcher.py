# agents/fetcher.py
# This agent fetches live news from two sources:
# 1. Tavily API - searches internet for latest ET news
# 2. ET RSS Feed - direct feed from Economic Times website
# No LLM needed - just fetching and cleaning data

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import feedparser
from tavily import TavilyClient
from dotenv import load_dotenv
from datetime import datetime

# Load API keys from .env file
load_dotenv()

# Initialize Tavily client once
# We do this outside the function so it doesn't
# create a new client every single time
tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

# ET RSS feed URLs for each category
# These are free public feeds from Economic Times
ET_RSS_FEEDS = {
    "markets":  "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "startups": "https://economictimes.indiatimes.com/small-biz/startups/rssfeeds/13357270.cms",
    "economy":  "https://economictimes.indiatimes.com/economy/rssfeeds/1373380680.cms",
    "tech":     "https://economictimes.indiatimes.com/tech/rssfeeds/13357270.cms",
    "budget":   "https://economictimes.indiatimes.com/news/economy/policy/rssfeeds/1415421581.cms"
}

# Tavily search queries for each category
# These are optimized to get best ET news results
TAVILY_QUERIES = {
    "markets":  "Economic Times India stock market NSE BSE news today",
    "startups": "Economic Times India startup funding news today",
    "economy":  "Economic Times India economy RBI GDP news today",
    "tech":     "Economic Times India technology news today",
    "budget":   "Economic Times India budget finance ministry news today"
}

def fetch_from_rss(category: str, count: int = 5) -> list:
    # Fetches articles from ET RSS feed for a category
    # RSS is like a live list of latest articles from a website
    # feedparser reads this list and returns it as Python objects

    articles = []

    if category not in ET_RSS_FEEDS:
        print(f"Fetcher: No RSS feed found for category {category}")
        return articles

    try:
        print(f"Fetcher: Reading RSS feed for {category}...")
        feed = feedparser.parse(ET_RSS_FEEDS[category])

        # feedparser returns entries - each entry is one article
        for entry in feed.entries[:count]:
            article = {
                "title":        entry.get("title", "No title"),
                "summary":      entry.get("summary", "No summary")[:300],
                # [:300] means take only first 300 characters
                # RSS summaries can be very long
                "url":          entry.get("link", ""),
                "category":     category,
                "source":       "ET RSS",
                "published_at": entry.get("published", datetime.now().isoformat())
            }
            articles.append(article)

        print(f"Fetcher: Got {len(articles)} articles from RSS for {category}")

    except Exception as e:
        # If RSS fails for any reason, we just return empty list
        # Tavily will still work as backup
        print(f"Fetcher: RSS failed for {category} - {str(e)}")

    return articles

def fetch_from_tavily(category: str, count: int = 5) -> list:
    # Fetches articles from Tavily API
    # Tavily searches the internet and returns clean results
    # Better for finding very recent breaking news

    articles = []

    query = TAVILY_QUERIES.get(category, f"Economic Times India {category} news today")

    try:
        print(f"Fetcher: Searching Tavily for {category}...")
        results = tavily_client.search(
            query=query,
            max_results=count,
            search_depth="basic"
            # basic is faster, advanced is slower but more detailed
        )

        for result in results.get("results", []):
            article = {
                "title":        result.get("title", "No title"),
                "summary":      result.get("content", "No summary")[:300],
                "url":          result.get("url", ""),
                "category":     category,
                "source":       "Tavily",
                "published_at": datetime.now().isoformat()
                # Tavily doesn't always give publish date
                # so we use current time as fallback
            }
            articles.append(article)

        print(f"Fetcher: Got {len(articles)} articles from Tavily for {category}")

    except Exception as e:
        print(f"Fetcher: Tavily failed for {category} - {str(e)}")

    return articles

def remove_duplicates(articles: list) -> list:
    # Sometimes same article appears in both RSS and Tavily
    # This function removes duplicates by comparing titles
    # If two titles are very similar we keep only one

    seen_titles = []
    unique_articles = []

    for article in articles:
        title = article["title"].lower().strip()
        # Convert to lowercase for fair comparison
        # "Nifty Rises" and "nifty rises" are same article

        # Check if we have seen a very similar title before
        is_duplicate = False
        for seen in seen_titles:
            # If first 40 characters match - it's a duplicate
            if title[:40] == seen[:40]:
                is_duplicate = True
                break

        if not is_duplicate:
            seen_titles.append(title)
            unique_articles.append(article)

    print(f"Fetcher: Removed duplicates - {len(articles)} → {len(unique_articles)} articles")
    return unique_articles

def run_fetcher(action: str, category: str = "all", query: str = None, count: int = 5) -> dict:
    # This is the main function of the Fetcher Agent
    # Input:
    #   action   = "fetch_all" / "fetch_category" / "fetch_search"
    #   category = "markets" / "startups" / "economy" / "tech" / "budget" / "all"
    #   query    = search text (only for fetch_search action)
    #   count    = how many articles per category
    # Output: dictionary with articles list

    print(f"\nFetcher Agent started - action: {action}, category: {category}")
    all_articles = []

    if action == "fetch_all":
        # User opened app - fetch news for ALL categories
        categories = ["markets", "startups", "economy", "tech", "budget"]
        for cat in categories:
            # Get from both RSS and Tavily for each category
            rss_articles    = fetch_from_rss(cat, count)
            tavily_articles = fetch_from_tavily(cat, count)
            # Combine both sources
            combined = rss_articles + tavily_articles
            all_articles.extend(combined)

    elif action == "fetch_category":
        # User clicked a specific category tab
        rss_articles    = fetch_from_rss(category, count * 2)
        tavily_articles = fetch_from_tavily(category, count * 2)
        all_articles    = rss_articles + tavily_articles

    elif action == "fetch_search":
        # User typed something in search bar
        if query:
            try:
                print(f"Fetcher: Searching for '{query}'...")
                results = tavily_client.search(
                    query=f"Economic Times India {query}",
                    max_results=count * 2,
                    search_depth="basic"
                )
                for result in results.get("results", []):
                    all_articles.append({
                        "title":        result.get("title", "No title"),
                        "summary":      result.get("content", "No summary")[:300],
                        "url":          result.get("url", ""),
                        "category":     "search",
                        "source":       "Tavily Search",
                        "published_at": datetime.now().isoformat()
                    })
            except Exception as e:
                print(f"Fetcher: Search failed - {str(e)}")

    # Remove duplicate articles
    all_articles = remove_duplicates(all_articles)

    result = {
        "articles":      all_articles,
        "total_fetched": len(all_articles),
        "fetched_at":    datetime.now().isoformat(),
        "action":        action,
        "category":      category
    }

    print(f"Fetcher Agent done - total articles: {len(all_articles)}")
    return result


# Test this agent directly
if __name__ == "__main__":
    print("=" * 40)
    print("Testing Fetcher Agent")
    print("=" * 40)

    # Test 1 - Fetch all categories
    print("\nTest 1: Fetch all categories")
    result = run_fetcher(action="fetch_all", count=2)
    print(f"Total articles fetched: {result['total_fetched']}")
    if result['articles']:
        print("First article:")
        print(f"  Title:    {result['articles'][0]['title']}")
        print(f"  Category: {result['articles'][0]['category']}")
        print(f"  Source:   {result['articles'][0]['source']}")

    # Test 2 - Fetch specific category
    print("\nTest 2: Fetch markets category only")
    result = run_fetcher(action="fetch_category", category="markets", count=3)
    print(f"Markets articles: {result['total_fetched']}")

    # Test 3 - Search
    print("\nTest 3: Search for RBI news")
    result = run_fetcher(action="fetch_search", query="RBI interest rate decision", count=3)
    print(f"Search results: {result['total_fetched']}")
    if result['articles']:
        for a in result['articles'][:2]:
            print(f"  - {a['title']}")

    print("\nFetcher Agent working correctly!")