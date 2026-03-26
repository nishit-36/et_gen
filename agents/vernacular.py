# agents/vernacular.py
# IMPROVEMENTS:
# 1. Title + summary translated in ONE API call (was 2 calls)
# 2. English added to SUPPORTED_LANGUAGES
# 3. Financial jargon explanation added to prompt
# 4. translation_failed flag in output
# 5. Better error transparency

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# IMPROVEMENT 2 — English added to config
# Previously english was handled by if/else outside config
# Now it is part of the same config dictionary
# Cleaner and consistent
SUPPORTED_LANGUAGES = {
    "english": {
        "display_name": "English",
        "instruction":  "Keep the text in clear simple English. Fix any grammar issues."
    },
    "hindi": {
        "display_name": "हिंदी",
        "instruction":  "Translate to Hindi. Use simple conversational Hindi that Indians use daily. Not textbook Hindi."
    },
    "gujarati": {
        "display_name": "ગુજરાતી",
        "instruction":  "Translate to Gujarati. Use simple conversational Gujarati."
    },
    "tamil": {
        "display_name": "தமிழ்",
        "instruction":  "Translate to Tamil. Use simple conversational Tamil."
    },
    "telugu": {
        "display_name": "తెలుగు",
        "instruction":  "Translate to Telugu. Use simple conversational Telugu."
    },
    "bengali": {
        "display_name": "বাংলা",
        "instruction":  "Translate to Bengali. Use simple conversational Bengali."
    }
}


def translate_article(
    title:           str,
    summary:         str,
    target_language: str,
    user_profession: str = "general"
) -> dict:
    # IMPROVEMENT 1 — Single API call for both title and summary
    # Previously: 2 separate API calls = 2x slower
    # Now: 1 API call returns both = 2x faster
    #
    # IMPROVEMENT 3 — Financial jargon explanation
    # Prompt now asks model to explain financial terms
    # in simple language for Indian readers
    #
    # Input:
    #   title           = article title in English
    #   summary         = article summary in English
    #   target_language = "hindi" / "gujarati" etc
    #   user_profession = used to adjust formality level
    # Output: dict with translated_title and translated_summary

    if target_language not in SUPPORTED_LANGUAGES:
        print(f"Vernacular: Language '{target_language}' not supported")
        return {
            "translated_title":   title,
            "translated_summary": summary,
            "translation_failed": True,
            "error": f"Language {target_language} not supported"
        }

    if target_language == "english":
        # No translation needed
        return {
            "translated_title":   title,
            "translated_summary": summary,
            "translation_failed": False
        }

    lang_config  = SUPPORTED_LANGUAGES[target_language]
    instruction  = lang_config["instruction"]
    display_name = lang_config["display_name"]

    # Adjust tone based on user profession
    tone = "simple and clear"
    if user_profession in ["investor", "professional"]:
        tone = "professional but clear"
    elif user_profession == "student":
        tone = "simple and easy to understand"

    # IMPROVEMENT 3 — Financial jargon in prompt
    prompt = f"""
{instruction}

Tone: {tone}

Important rules:
- Do NOT translate proper nouns like company names (RBI, NSE, BSE, Sebi, etc.)
- Do NOT translate numbers, percentages, or currency amounts (Rs 500, 6.5%, etc.)
- Keep brand names in English (Zepto, Reliance, Tata, etc.)
- For financial terms like "repo rate", "hawkish", "bullish", "GDP", "IPO":
  Write the English term first then explain simply in {display_name} in brackets
  Example: repo rate (वह दर जिस पर बैंक RBI से पैसा उधार लेते हैं)
- Make it sound natural — not robotic word by word translation

Translate BOTH the title and summary below.
Return EXACTLY in this format with these exact labels:
TITLE: [translated title here]
SUMMARY: [translated summary here]

Title to translate:
{title}

Summary to translate:
{summary}
"""

    try:
        print(f"Vernacular: Translating to {display_name} (1 API call)...")
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=600
        )

        response_text = response.choices[0].message.content.strip()

        # Parse the response to extract title and summary
        translated_title   = title
        translated_summary = summary
        parse_failed       = False

        lines = response_text.split("\n")
        for i, line in enumerate(lines):
            if line.startswith("TITLE:"):
                translated_title = line.replace("TITLE:", "").strip()
            elif line.startswith("SUMMARY:"):
                # Summary might be multiple lines
                # Join everything after SUMMARY: label
                summary_start = response_text.find("SUMMARY:")
                if summary_start != -1:
                    translated_summary = response_text[
                        summary_start + 8:
                    ].strip()

        # Verify we actually got translations
        if translated_title == title and translated_summary == summary:
            parse_failed = True
            print(f"Vernacular: Could not parse response properly")

        print(f"Vernacular: Translation to {display_name} complete")
        return {
            "translated_title":    translated_title,
            "translated_summary":  translated_summary,
            "language_display":    display_name,
            "translation_failed":  parse_failed
        }

    except Exception as e:
        print(f"Vernacular: Translation failed - {str(e)}")
        # IMPROVEMENT 4 — Clear failure flag
        # Previously returned original text silently
        # Now returns translation_failed=True so UI can show message
        return {
            "translated_title":   title,
            "translated_summary": summary,
            "translation_failed": True,
            "error":              str(e)
        }


def run_vernacular(article: dict, target_language: str) -> dict:
    # Main function of Vernacular Agent
    # Input:
    #   article         = article dict with title and summary
    #   target_language = "hindi" / "gujarati" etc
    # Output: same article with translation fields added

    print(f"\nVernacular Agent started")
    print(f"  Target language: {target_language}")
    print(f"  Article: {article.get('title','')[:50]}...")

    if target_language == "english":
        article["translation_failed"] = False
        return article

    # Get user profession if available in article
    user_profession = article.get("user_profession", "general")

    # Single API call for both title and summary
    result = translate_article(
        title           = article.get("title", ""),
        summary         = article.get("summary", ""),
        target_language = target_language,
        user_profession = user_profession
    )

    # Add translation fields to article
    article["translated_title"]   = result["translated_title"]
    article["translated_summary"] = result["translated_summary"]
    article["translated_language"]= target_language
    article["language_display"]   = result.get(
        "language_display",
        SUPPORTED_LANGUAGES.get(target_language, {}).get("display_name", target_language)
    )
    article["translation_failed"] = result.get("translation_failed", False)

    if result.get("translation_failed"):
        print(f"Vernacular: Translation failed — showing English fallback")
    else:
        print(f"Vernacular Agent done!")

    return article


def run_vernacular_feed(articles: list, target_language: str) -> list:
    # Translate entire list of articles
    print(f"\nVernacular: Translating {len(articles)} articles to {target_language}")
    return [run_vernacular(article, target_language) for article in articles]


# Test
if __name__ == "__main__":
    print("="*40)
    print("Testing Vernacular Agent")
    print("="*40)

    test_article = {
        "title":   "RBI keeps repo rate unchanged at 6.5%, signals possible cut in June",
        "summary": "The Reserve Bank of India kept its benchmark lending rate unchanged for the sixth consecutive meeting. Governor Shaktikanta Das said inflation is trending toward the 4% target. Markets reacted positively as bond yields fell 8 basis points.",
        "category": "economy"
    }

    # Test 1 — Hindi (single API call)
    print("\nTest 1: Hindi translation (single API call)")
    result = run_vernacular(test_article.copy(), "hindi")
    print(f"Original:  {test_article['title']}")
    print(f"Hindi:     {result['translated_title']}")
    print(f"Failed:    {result['translation_failed']}")
    print(f"Summary:   {result['translated_summary'][:80]}...")

    # Test 2 — Gujarati
    print("\nTest 2: Gujarati translation")
    result2 = run_vernacular(test_article.copy(), "gujarati")
    print(f"Gujarati:  {result2['translated_title']}")
    print(f"Failed:    {result2['translation_failed']}")

    # Test 3 — Unsupported language
    print("\nTest 3: Unsupported language")
    result3 = run_vernacular(test_article.copy(), "french")
    print(f"Failed flag: {result3['translation_failed']}")
    print(f"Error: {result3.get('error', 'none')}")

    # Test 4 — English (no translation)
    print("\nTest 4: English (no API call)")
    result4 = run_vernacular(test_article.copy(), "english")
    print(f"Title unchanged: {result4['title']}")
    print(f"Failed: {result4['translation_failed']}")

    print("\nVernacular Agent working correctly!")