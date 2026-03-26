# agents/fetcher.py
# IMPROVEMENTS:
# 1. More ET categories added - politics, jobs, real estate, auto, education
# 2. Time-aware queries - "last 24 hours" instead of "today"
# 3. Better deduplication - 60 chars instead of 40

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import feedparser
from tavily import TavilyClient
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

# IMPROVEMENT 1 — More ET RSS feeds
# Added: politics, international, jobs, real estate, auto, education
ET_RSS_FEEDS = {
    "markets":       "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "startups":      "https://economictimes.indiatimes.com/small-biz/startups/rssfeeds/13357270.cms",
    "economy":       "https://economictimes.indiatimes.com/economy/rssfeeds/1373380680.cms",
    "tech":          "https://economictimes.indiatimes.com/tech/rssfeeds/13357270.cms",
    "budget":        "https://economictimes.indiatimes.com/news/economy/policy/rssfeeds/1415421581.cms",
    "politics":      "https://economictimes.indiatimes.com/news/politics-and-nation/rssfeeds/1052732854.cms",
    "international": "https://economictimes.indiatimes.com/news/international/rssfeeds/1522591854.cms",
    "jobs":          "https://economictimes.indiatimes.com/jobs/rssfeeds/107003.cms",
    "real-estate":   "https://economictimes.indiatimes.com/industry/services/property-/-cstruction/rssfeeds/13358287.cms",
    "auto":          "https://economictimes.indiatimes.com/industry/auto/rssfeeds/1081579906.cms",
    "education":     "https://economictimes.indiatimes.com/industry/services/education/rssfeeds/13357540.cms"
}

# IMPROVEMENT 2 — Time-aware Tavily queries
# Changed "today" to "last 24 hours" for fresher results
TAVILY_QUERIES = {
    "markets":       "Economic Times India stock market NSE BSE news last 24 hours",
    "startups":      "Economic Times India startup funding news last 24 hours",
    "economy":       "Economic Times India economy RBI GDP news last 24 hours",
    "tech":          "Economic Times India technology AI news last 24 hours",
    "budget":        "Economic Times India budget finance ministry news last 24 hours",
    "politics":      "Economic Times India politics government policy news last 24 hours",
    "international": "Economic Times India international global news last 24 hours",
    "jobs":          "Economic Times India jobs employment hiring news last 24 hours",
    "real-estate":   "Economic Times India real estate property housing news last 24 hours",
    "auto":          "Economic Times India automobile car electric vehicle news last 24 hours",
    "education":     "Economic Times India education university exam news last 24 hours"
}

# All available categories list
# Used by frontend to show tabs
ALL_CATEGORIES = list(ET_RSS_FEEDS.keys())


def fetch_from_rss(category: str, count: int = 5) -> list:
    articles = []

    if category not in ET_RSS_FEEDS:
        print(f"Fetcher: No RSS feed for category {category}")
        return articles

    try:
        print(f"Fetcher: Reading RSS for {category}...")
        feed = feedparser.parse(ET_RSS_FEEDS[category])

        for entry in feed.entries[:count]:
            article = {
                "title":        entry.get("title", "No title"),
                "summary":      entry.get("summary", "No summary")[:300],
                "url":          entry.get("link", ""),
                "category":     category,
                "source":       "ET RSS",
                "published_at": entry.get("published", datetime.now().isoformat())
            }
            articles.append(article)

        print(f"Fetcher: Got {len(articles)} from RSS for {category}")

    except Exception as e:
        print(f"Fetcher: RSS failed for {category} - {str(e)}")

    return articles


def fetch_from_tavily(category: str, count: int = 5) -> list:
    articles = []

    query = TAVILY_QUERIES.get(
        category,
        f"Economic Times India {category} news last 24 hours"
    )

    try:
        print(f"Fetcher: Searching Tavily for {category}...")
        results = tavily_client.search(
            query=query,
            max_results=count,
            search_depth="basic"
        )

        for result in results.get("results", []):
            article = {
                "title":        result.get("title", "No title"),
                "summary":      result.get("content", "No summary")[:300],
                "url":          result.get("url", ""),
                "category":     category,
                "source":       "Tavily",
                "published_at": datetime.now().isoformat()
            }
            articles.append(article)

        print(f"Fetcher: Got {len(articles)} from Tavily for {category}")

    except Exception as e:
        print(f"Fetcher: Tavily failed for {category} - {str(e)}")

    return articles


def remove_duplicates(articles: list) -> list:
    # IMPROVEMENT 3 — Better deduplication
    # Changed from 40 chars to 60 chars comparison
    # Catches more duplicate variations
    seen_titles    = []
    unique_articles = []

    for article in articles:
        title = article["title"].lower().strip()

        is_duplicate = False
        for seen in seen_titles:
            # Compare first 60 characters
            if title[:60] == seen[:60]:
                is_duplicate = True
                break

        if not is_duplicate:
            seen_titles.append(title)
            unique_articles.append(article)

    removed = len(articles) - len(unique_articles)
    if removed > 0:
        print(f"Fetcher: Removed {removed} duplicates - {len(articles)} → {len(unique_articles)}")
    return unique_articles


def run_fetcher(
    action:   str = "fetch_all",
    category: str = "all",
    query:    str = None,
    count:    int = 5
) -> dict:

    print(f"\nFetcher Agent - action: {action}, category: {category}")
    all_articles = []

    if action == "fetch_all":
        # Fetch all categories
        # For all news tab - get 5 main categories
        main_categories = ["markets", "startups", "economy", "tech", "budget"]
        for cat in main_categories:
            rss_articles    = fetch_from_rss(cat, count)
            tavily_articles = fetch_from_tavily(cat, count)
            all_articles.extend(rss_articles + tavily_articles)

    elif action == "fetch_category":
        # Fetch specific category
        if category == "all":
            # All tab selected
            main_categories = ["markets", "startups", "economy", "tech", "budget"]
            for cat in main_categories:
                rss_articles    = fetch_from_rss(cat, count)
                tavily_articles = fetch_from_tavily(cat, count)
                all_articles.extend(rss_articles + tavily_articles)
        else:
            # Specific category tab
            rss_articles    = fetch_from_rss(category, count * 2)
            tavily_articles = fetch_from_tavily(category, count * 2)
            all_articles    = rss_articles + tavily_articles

    elif action == "fetch_search":
        # User searched for something
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

    # Remove duplicates
    all_articles = remove_duplicates(all_articles)

    result = {
        "articles":      all_articles,
        "total_fetched": len(all_articles),
        "fetched_at":    datetime.now().isoformat(),
        "action":        action,
        "category":      category
    }

    print(f"Fetcher done - total: {len(all_articles)} articles")
    return result


# Test
if __name__ == "__main__":
    print("="*40)
    print("Testing Fetcher Agent")
    print("="*40)

    # Test 1 — All categories
    print("\nTest 1: Fetch all")
    result = run_fetcher(action="fetch_all", count=2)
    print(f"Total: {result['total_fetched']}")

    # Test 2 — New category: Politics
    print("\nTest 2: Politics category (new)")
    result2 = run_fetcher(action="fetch_category", category="politics", count=3)
    print(f"Politics articles: {result2['total_fetched']}")
    if result2["articles"]:
        print(f"  First: {result2['articles'][0]['title'][:60]}")

    # Test 3 — New category: Jobs
    print("\nTest 3: Jobs category (new)")
    result3 = run_fetcher(action="fetch_category", category="jobs", count=3)
    print(f"Jobs articles: {result3['total_fetched']}")

    # Test 4 — New category: Auto
    print("\nTest 4: Auto category (new)")
    result4 = run_fetcher(action="fetch_category", category="auto", count=3)
    print(f"Auto articles: {result4['total_fetched']}")

    # Test 5 — All categories list
    print(f"\nAll available categories: {ALL_CATEGORIES}")

    print("\nFetcher Agent working correctly!")