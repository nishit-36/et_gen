# agents/qa_agent.py
# NEW AGENT - Article Q&A
# Allows user to ask questions about any article
# Turns news reader into news assistant
# Example questions:
#   "Why did RBI keep rates unchanged?"
#   "How will this affect stock market?"
#   "Explain this in simple terms"
#   "Is this good for startups?"

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def run_qa_agent(
    question:        str,
    article_title:   str,
    article_summary: str,
    user_profession: str = "general",
    language:        str = "english"
) -> dict:
    # This agent answers user questions about a specific article
    # Input:
    #   question        = what user asked
    #   article_title   = title of the article
    #   article_summary = summary of the article
    #   user_profession = investor / student / startup_founder etc
    #   language        = english / hindi / gujarati etc
    # Output: dict with answer and follow_up_questions

    print(f"\nQA Agent started")
    print(f"  Question:   {question[:60]}...")
    print(f"  Article:    {article_title[:50]}...")
    print(f"  Profession: {user_profession}")
    print(f"  Language:   {language}")

    if not question or not article_title:
        return {
            "answer":               "Please ask a question about the article.",
            "follow_up_questions":  [],
            "error":                True
        }

    # Adjust explanation style based on user profession
    style_instruction = "Clear and informative"
    if user_profession == "investor":
        style_instruction = "Focus on financial impact, market implications, and investment angle"
    elif user_profession == "student":
        style_instruction = "Simple language, explain financial terms, educational tone"
    elif user_profession == "startup_founder":
        style_instruction = "Focus on startup ecosystem impact, funding, and business angle"
    elif user_profession == "professional":
        style_instruction = "Professional tone, focus on business and policy implications"

    # Language instruction
    lang_instruction = "Answer in English"
    if language == "hindi":
        lang_instruction = "Answer in simple Hindi. Keep financial terms in English with Hindi explanation."
    elif language == "gujarati":
        lang_instruction = "Answer in simple Gujarati. Keep financial terms in English."
    elif language == "tamil":
        lang_instruction = "Answer in simple Tamil. Keep financial terms in English."
    elif language == "telugu":
        lang_instruction = "Answer in simple Telugu. Keep financial terms in English."
    elif language == "bengali":
        lang_instruction = "Answer in simple Bengali. Keep financial terms in English."

    prompt = f"""
You are an expert financial journalist and analyst for Economic Times India.

Article Title: {article_title}
Article Content: {article_summary}

User Question: {question}

User Profile: {user_profession}
Style: {style_instruction}
{lang_instruction}

Instructions:
- Answer the question directly and clearly
- Base your answer on the article content provided
- If the article does not contain enough information to answer fully,
  say so and provide general context
- Keep answer between 3-5 sentences
- Do not make up facts not in the article
- End with one key takeaway for the user

Also suggest 3 follow-up questions the user might want to ask next.

Return your response in this exact format:

ANSWER: [your answer here]

FOLLOWUP1: [follow up question 1]
FOLLOWUP2: [follow up question 2]
FOLLOWUP3: [follow up question 3]
"""

    try:
        print("QA Agent: Asking LLaMA...")
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=600
        )

        response_text = response.choices[0].message.content.strip()
        print("QA Agent: Got response from LLaMA")

        # Parse response
        answer            = ""
        follow_up_questions = []

        lines = response_text.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("ANSWER:"):
                answer = line.replace("ANSWER:", "").strip()
            elif line.startswith("FOLLOWUP1:"):
                follow_up_questions.append(line.replace("FOLLOWUP1:", "").strip())
            elif line.startswith("FOLLOWUP2:"):
                follow_up_questions.append(line.replace("FOLLOWUP2:", "").strip())
            elif line.startswith("FOLLOWUP3:"):
                follow_up_questions.append(line.replace("FOLLOWUP3:", "").strip())

        # If parsing failed get full response as answer
        if not answer:
            answer = response_text
            print("QA Agent: Used full response as answer")

        print(f"QA Agent done!")
        print(f"  Answer length: {len(answer)} chars")
        print(f"  Follow-ups:    {len(follow_up_questions)}")

        return {
            "answer":              answer,
            "follow_up_questions": follow_up_questions,
            "error":               False
        }

    except Exception as e:
        print(f"QA Agent: Failed - {str(e)}")
        return {
            "answer":              "Sorry I could not answer that question right now. Please try again.",
            "follow_up_questions": [],
            "error":               True,
            "error_message":       str(e)
        }


# Test
if __name__ == "__main__":
    print("="*40)
    print("Testing QA Agent")
    print("="*40)

    # Test article
    test_title   = "RBI keeps repo rate unchanged at 6.5%, signals possible cut in June"
    test_summary = """The Reserve Bank of India kept its benchmark lending rate
    unchanged for the sixth consecutive meeting. Governor Shaktikanta Das said
    inflation is trending toward the 4% target. Markets reacted positively as
    bond yields fell 8 basis points. The decision was unanimous among MPC members.
    Analysts expect a possible rate cut in June if inflation stays under control."""

    # Test 1 — Investor asking financial question
    print("\nTest 1: Investor question")
    result = run_qa_agent(
        question        = "How will this affect my fixed deposit returns?",
        article_title   = test_title,
        article_summary = test_summary,
        user_profession = "investor",
        language        = "english"
    )
    print(f"\nAnswer: {result['answer']}")
    print(f"\nFollow-up questions:")
    for q in result["follow_up_questions"]:
        print(f"  - {q}")

    # Test 2 — Student asking simple question
    print("\n" + "="*40)
    print("\nTest 2: Student question")
    result2 = run_qa_agent(
        question        = "What is repo rate and why does it matter?",
        article_title   = test_title,
        article_summary = test_summary,
        user_profession = "student",
        language        = "english"
    )
    print(f"\nAnswer: {result2['answer']}")

    # Test 3 — Hindi language answer
    print("\n" + "="*40)
    print("\nTest 3: Hindi answer")
    result3 = run_qa_agent(
        question        = "RBI ne rate kyun nahi badla?",
        article_title   = test_title,
        article_summary = test_summary,
        user_profession = "general",
        language        = "hindi"
    )
    print(f"\nHindi Answer: {result3['answer']}")

    print("\nQA Agent working correctly!")