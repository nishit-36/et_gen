# api/main.py
# IMPROVEMENTS:
# 1. New /api/qa endpoint for article Q&A
# 2. Updated /api/save-user with new profile fields
# 3. New /api/categories endpoint - sends all categories to frontend

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from agents.orchestrator import run_orchestrator
from agents.qa_agent import run_qa_agent
from agents.vernacular import run_vernacular
from agents.fetcher import ALL_CATEGORIES
from database.db import (
    create_tables, save_user,
    save_reading_history, get_user
)
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="ET News AI",
    description="AI powered personalized news for Economic Times",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create tables on startup
create_tables()

# ─────────────────────────────────────────
# REQUEST MODELS
# ─────────────────────────────────────────

class FeedRequest(BaseModel):
    user_id:  str
    language: Optional[str] = "english"

class CategoryRequest(BaseModel):
    user_id:  str
    category: str
    language: Optional[str] = "english"

class SearchRequest(BaseModel):
    user_id:  str
    query:    str
    language: Optional[str] = "english"

class StoryArcRequest(BaseModel):
    user_id: str
    topic:   str

class TranslateRequest(BaseModel):
    user_id:  str
    title:    str
    summary:  str
    language: str

class SaveUserRequest(BaseModel):
    user_id:                  str
    profession:               Optional[str]  = "general"
    interests:                Optional[list] = []
    language:                 Optional[str]  = "english"
    experience_level:         Optional[str]  = "general"
    reading_time_preference:  Optional[str]  = "any"

class TrackReadRequest(BaseModel):
    user_id:       str
    article_title: str
    category:      str
    time_spent:    Optional[int] = 0

# NEW — Q&A request model
class QARequest(BaseModel):
    user_id:         str
    question:        str
    article_title:   str
    article_summary: str
    language:        Optional[str] = "english"

# ─────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────

@app.get("/")
def home():
    return {
        "status":  "ET News AI backend is running!",
        "version": "2.0.0",
        "features": [
            "personalized feed",
            "story arc",
            "vernacular translation",
            "article Q&A"
        ]
    }

# NEW — Returns all available categories
# Frontend uses this to build category tabs dynamically
@app.get("/api/categories")
def get_categories():
    return {
        "status":     "success",
        "categories": ALL_CATEGORIES,
        "total":      len(ALL_CATEGORIES)
    }

@app.post("/api/feed")
def get_feed(request: FeedRequest):
    print(f"\nAPI: /feed called for {request.user_id}")
    result = run_orchestrator(
        user_id  = request.user_id,
        action   = "load_feed",
        language = request.language
    )
    return result

@app.post("/api/category")
def get_category(request: CategoryRequest):
    print(f"\nAPI: /category called - {request.category}")
    result = run_orchestrator(
        user_id  = request.user_id,
        action   = "fetch_category",
        category = request.category,
        language = request.language
    )
    return result

@app.post("/api/search")
def search_news(request: SearchRequest):
    print(f"\nAPI: /search called - '{request.query}'")
    result = run_orchestrator(
        user_id  = request.user_id,
        action   = "fetch_search",
        query    = request.query,
        language = request.language
    )
    return result

@app.post("/api/story-arc")
def get_story_arc(request: StoryArcRequest):
    print(f"\nAPI: /story-arc called - '{request.topic}'")
    result = run_orchestrator(
        user_id = request.user_id,
        action  = "story_arc",
        query   = request.topic
    )
    return result

@app.post("/api/translate")
def translate_article(request: TranslateRequest):
    print(f"\nAPI: /translate - {request.language}")
    article = {
        "title":   request.title,
        "summary": request.summary
    }
    result = run_vernacular(article, request.language)
    return {
        "status":             "success",
        "translated_title":   result.get("translated_title",   request.title),
        "translated_summary": result.get("translated_summary", request.summary),
        "language":           request.language,
        "translation_failed": result.get("translation_failed", False)
    }

# NEW — Q&A endpoint
# Called when user asks a question about an article
@app.post("/api/qa")
def ask_question(request: QARequest):
    print(f"\nAPI: /qa called")
    print(f"  Question: {request.question[:50]}...")

    # Get user profile for profession info
    user = get_user(request.user_id)
    profession = user["profession"] if user else "general"

    result = run_qa_agent(
        question        = request.question,
        article_title   = request.article_title,
        article_summary = request.article_summary,
        user_profession = profession,
        language        = request.language
    )

    return {
        "status":              "success" if not result["error"] else "error",
        "answer":              result["answer"],
        "follow_up_questions": result["follow_up_questions"],
        "error":               result["error"]
    }

@app.post("/api/save-user")
def save_user_profile(request: SaveUserRequest):
    print(f"\nAPI: /save-user - {request.user_id}")
    save_user(
        user_id                 = request.user_id,
        profession              = request.profession,
        interests               = request.interests,
        language                = request.language,
        experience_level        = request.experience_level,
        reading_time_preference = request.reading_time_preference
    )
    return {"status": "success", "message": "Profile saved"}

@app.post("/api/track-read")
def track_reading(request: TrackReadRequest):
    print(f"\nAPI: /track-read - {request.article_title[:40]}")
    save_reading_history(
        user_id        = request.user_id,
        article_title  = request.article_title,
        category       = request.category,
        time_spent_sec = request.time_spent
    )
    return {"status": "success"}

@app.get("/api/user/{user_id}")
def get_user_profile(user_id: str):
    user = get_user(user_id)
    if user:
        return {"status": "found",    "user": user}
    else:
        return {"status": "new_user", "user": None}