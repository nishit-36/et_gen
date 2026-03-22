# api/main.py
# This is the FastAPI server
# It receives requests from the frontend
# Calls the orchestrator and sends results back
# Think of it as the waiter between frontend and backend

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
from agents.orchestrator import run_orchestrator
from database.db import create_tables, save_user, save_reading_history, get_user
from dotenv import load_dotenv

load_dotenv()

# Create FastAPI app
app = FastAPI(
    title="ET News AI",
    description="AI powered personalized news for Economic Times",
    version="1.0.0"
)

# CORS middleware
# This allows your HTML frontend to talk to this Python server
# Without this browser will block all requests from frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create database tables when server starts
create_tables()

# ─────────────────────────────────────────
# REQUEST MODELS
# These define what data frontend must send
# Pydantic validates the data automatically
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
    user_id:    str
    profession: Optional[str] = "general"
    interests:  Optional[list] = []
    language:   Optional[str] = "english"

class TrackReadRequest(BaseModel):
    user_id:       str
    article_title: str
    category:      str
    time_spent:    Optional[int] = 0

# ─────────────────────────────────────────
# API ENDPOINTS
# Each endpoint is a URL the frontend calls
# ─────────────────────────────────────────

@app.get("/")
def home():
    # Simple health check endpoint
    # Open http://localhost:8000 in browser to verify server is running
    return {"status": "ET News AI backend is running!"}

@app.post("/api/feed")
def get_feed(request: FeedRequest):
    # Called when user opens app or refreshes feed
    # Returns personalized ranked news feed
    print(f"\nAPI: /feed called for user {request.user_id}")
    result = run_orchestrator(
        user_id  = request.user_id,
        action   = "load_feed",
        language = request.language
    )
    return result

@app.post("/api/category")
def get_category(request: CategoryRequest):
    # Called when user clicks a category tab
    # Returns news for that specific category
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
    # Called when user types in search bar
    # Returns articles matching the search query
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
    # Called when user clicks Story Arc button
    # Returns complete story with timeline and sentiment
    print(f"\nAPI: /story-arc called - '{request.topic}'")
    result = run_orchestrator(
        user_id = request.user_id,
        action  = "story_arc",
        query   = request.topic
    )
    return result

@app.post("/api/translate")
def translate_article(request: TranslateRequest):
    # Called when user clicks translate button
    # Returns article translated to selected language
    print(f"\nAPI: /translate called - language: {request.language}")
    from agents.vernacular import run_vernacular
    article = {
        "title":   request.title,
        "summary": request.summary
    }
    result = run_vernacular(article, request.language)
    return {
        "status":              "success",
        "translated_title":    result.get("translated_title", request.title),
        "translated_summary":  result.get("translated_summary", request.summary),
        "language":            request.language
    }

@app.post("/api/save-user")
def save_user_profile(request: SaveUserRequest):
    # Called when user completes optional profile setup
    # Saves profession, interests and language to database
    print(f"\nAPI: /save-user called for {request.user_id}")
    save_user(
        user_id    = request.user_id,
        profession = request.profession,
        interests  = request.interests,
        language   = request.language
    )
    return {"status": "success", "message": "Profile saved"}

@app.post("/api/track-read")
def track_reading(request: TrackReadRequest):
    # Called silently every time user opens an article
    # Saves reading history to improve personalization
    print(f"\nAPI: /track-read - {request.article_title[:40]}")
    save_reading_history(
        user_id       = request.user_id,
        article_title = request.article_title,
        category      = request.category,
        time_spent_sec= request.time_spent
    )
    return {"status": "success"}

@app.get("/api/user/{user_id}")
def get_user_profile(user_id: str):
    # Called when frontend needs to check if user exists
    # Returns user profile or null if new user
    user = get_user(user_id)
    if user:
        return {"status": "found", "user": user}
    else:
        return {"status": "new_user", "user": None}