# agents/vernacular.py
# This agent translates news articles into Indian languages
# Uses Groq Gemma2 9B - lighter and faster than LLaMA for translation
# Supported languages: Hindi, Gujarati, Tamil, Telugu, Bengali

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Language configuration
# display_name = what we show in UI
# instruction  = what we tell the model
SUPPORTED_LANGUAGES = {
    "hindi": {
        "display_name": "हिंदी",
        "instruction": "Translate to Hindi. Use simple conversational Hindi. Add cultural context where needed."
    },
    "gujarati": {
        "display_name": "ગુજરાતી",
        "instruction": "Translate to Gujarati. Use simple conversational Gujarati. Add cultural context where needed."
    },
    "tamil": {
        "display_name": "தமிழ்",
        "instruction": "Translate to Tamil. Use simple conversational Tamil. Add cultural context where needed."
    },
    "telugu": {
        "display_name": "తెలుగు",
        "instruction": "Translate to Telugu. Use simple conversational Telugu. Add cultural context where needed."
    },
    "bengali": {
        "display_name": "বাংলা",
        "instruction": "Translate to Bengali. Use simple conversational Bengali. Add cultural context where needed."
    }
}

def translate_text(text: str, target_language: str) -> str:
    # This function translates any text to target language
    # Uses Gemma2 9B - faster than LLaMA for translation tasks
    # Input:
    #   text            = English text to translate
    #   target_language = "hindi" / "gujarati" / "tamil" etc
    # Output: translated text as string

    if target_language not in SUPPORTED_LANGUAGES:
        print(f"Vernacular: Language '{target_language}' not supported")
        return text
        # Return original text if language not supported

    lang_config   = SUPPORTED_LANGUAGES[target_language]
    instruction   = lang_config["instruction"]
    display_name  = lang_config["display_name"]

    prompt = f"""
{instruction}

Important rules:
- Do NOT translate proper nouns like company names (RBI, NSE, BSE, Zepto, etc.)
- Do NOT translate numbers, percentages, or currency amounts
- Keep financial terms recognizable (repo rate, GDP, IPO etc.)
- Make it sound natural, not robotic word-by-word translation
- Add brief cultural explanation in brackets if a concept needs context

Text to translate:
{text}

Provide only the translated text. No explanations, no English text.
"""

    try:
        print(f"Vernacular: Translating to {display_name}...")
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            # gemma2-9b-it is faster and cheaper for translation
            # "it" means instruction tuned version
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            # low temperature for consistent translation
            max_tokens=1000
        )

        translated = response.choices[0].message.content.strip()
        print(f"Vernacular: Translation to {display_name} complete")
        return translated

    except Exception as e:
        print(f"Vernacular: Translation failed - {str(e)}")
        return text
        # Return original English if translation fails

def run_vernacular(article: dict, target_language: str) -> dict:
    # This is the main function of Vernacular Agent
    # Input:
    #   article         = full article dictionary with title and summary
    #   target_language = language code like "hindi"
    # Output: same article with translated title and summary added

    print(f"\nVernacular Agent started")
    print(f"  Target language: {target_language}")
    print(f"  Article: {article.get('title','')[:50]}...")

    if target_language == "english" or target_language not in SUPPORTED_LANGUAGES:
        # No translation needed or language not supported
        print("Vernacular: Already in English or language not supported - no translation needed")
        return article

    # Translate title
    translated_title = translate_text(
        article.get("title", ""),
        target_language
    )

    # Translate summary
    translated_summary = translate_text(
        article.get("summary", ""),
        target_language
    )

    # Add translated fields to article
    # We keep original English too so user can switch back
    article["translated_title"]   = translated_title
    article["translated_summary"] = translated_summary
    article["translated_language"] = target_language
    article["language_display"]    = SUPPORTED_LANGUAGES[target_language]["display_name"]

    print(f"Vernacular Agent done!")
    return article

def run_vernacular_feed(articles: list, target_language: str) -> list:
    # Translate an entire list of articles
    # Used when user sets Hindi as default language on profile
    # Input:  list of articles + target language
    # Output: list of articles with translations added

    print(f"\nVernacular: Translating {len(articles)} articles to {target_language}")

    translated_articles = []
    for article in articles:
        translated = run_vernacular(article, target_language)
        translated_articles.append(translated)

    return translated_articles


# Test this agent directly
if __name__ == "__main__":
    print("=" * 40)
    print("Testing Vernacular Agent")
    print("=" * 40)

    # Sample article to translate
    test_article = {
        "title":    "RBI keeps repo rate unchanged at 6.5%, signals possible cut in June",
        "summary":  "The Reserve Bank of India kept its benchmark lending rate unchanged for the sixth consecutive meeting. Governor Shaktikanta Das said inflation is trending toward the 4% target. Markets reacted positively as bond yields fell 8 basis points.",
        "category": "economy",
        "source":   "ET Economy"
    }

    # Test 1 - Hindi translation
    print("\nTest 1: Translate to Hindi")
    result = run_vernacular(test_article.copy(), "hindi")
    print(f"Original title:    {test_article['title']}")
    print(f"Hindi title:       {result['translated_title']}")
    print(f"Original summary:  {test_article['summary'][:80]}...")
    print(f"Hindi summary:     {result['translated_summary'][:80]}...")

    # Test 2 - Gujarati translation
    print("\nTest 2: Translate to Gujarati")
    result2 = run_vernacular(test_article.copy(), "gujarati")
    print(f"Gujarati title:    {result2['translated_title']}")

    # Test 3 - Unsupported language
    print("\nTest 3: Unsupported language (returns original)")
    result3 = run_vernacular(test_article.copy(), "french")
    print(f"Result: {result3['title']}")

    print("\nVernacular Agent working correctly!")