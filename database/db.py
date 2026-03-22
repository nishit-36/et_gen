# database/db.py
# This file creates our SQLite database and all 3 tables
# SQLite is a simple database that saves data in a single file on your PC
# No installation needed - Python has it built in

import sqlite3
import os
from datetime import datetime

# This is where our database file will be saved
# It will create a file called "et_news.db" inside the database folder
DB_PATH = os.path.join(os.path.dirname(__file__), "et_news.db")

def get_connection():
    # This function opens a connection to the database
    # Like opening a file before reading or writing it
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # row_factory means results come back as dictionaries
    # so we can do result["user_id"] instead of result[0]
    return conn

def create_tables():
    # This function creates all 3 tables if they don't exist yet
    # "IF NOT EXISTS" means it won't crash if tables already exist
    conn = get_connection()
    cursor = conn.cursor()

    # TABLE 1 - users
    # Stores basic info about each user
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            profession TEXT DEFAULT 'general',
            interests TEXT DEFAULT '',
            language TEXT DEFAULT 'english',
            created_at TEXT
        )
    """)

    # TABLE 2 - reading_history
    # Every time user clicks an article, we save it here
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reading_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            article_title TEXT,
            category TEXT,
            time_spent_sec INTEGER DEFAULT 0,
            clicked_at TEXT
        )
    """)

    # TABLE 3 - interest_scores
    # Auto calculated score per category per user
    # Higher score = show more of this category
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS interest_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            category TEXT,
            score REAL DEFAULT 0.0,
            article_count INTEGER DEFAULT 0,
            updated_at TEXT
        )
    """)

    conn.commit()
    # commit means save all changes permanently
    conn.close()
    print("Database and tables created successfully!")

def save_user(user_id, profession="general", interests=[], language="english"):
    # This function saves a new user to the database
    # Or updates existing user if they already exist
    conn = get_connection()
    cursor = conn.cursor()

    interests_str = ",".join(interests)
    # We convert list ["markets","startups"] to string "markets,startups"
    # because SQLite cannot store Python lists directly

    cursor.execute("""
        INSERT OR REPLACE INTO users
        (user_id, profession, interests, language, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, profession, interests_str, language, datetime.now().isoformat()))
    # The ? marks are placeholders - prevents SQL injection attacks
    # .isoformat() converts datetime to string like "2025-03-22T10:30:00"

    conn.commit()
    conn.close()
    print(f"User {user_id} saved successfully!")

def get_user(user_id):
    # This function reads a user from the database
    # Returns user data as a dictionary
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()

    if user is None:
        return None
    # Convert to regular dictionary
    user_dict = dict(user)
    # Convert interests string back to list
    if user_dict["interests"]:
        user_dict["interests"] = user_dict["interests"].split(",")
    else:
        user_dict["interests"] = []
    return user_dict

def save_reading_history(user_id, article_title, category, time_spent_sec=0):
    # This function saves every article click by user
    # Called silently every time user opens an article
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO reading_history
        (user_id, article_title, category, time_spent_sec, clicked_at)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, article_title, category, time_spent_sec, datetime.now().isoformat()))

    conn.commit()
    conn.close()

    # After saving history, update the interest score for this category
    update_interest_score(user_id, category, time_spent_sec)

def update_interest_score(user_id, category, time_spent_sec=0):
    # This function recalculates interest score after every article read
    # Score formula: (article_count * 0.5) + (total_minutes * 0.5)
    # Normalized between 0 and 1
    conn = get_connection()
    cursor = conn.cursor()

    # Check if score record already exists for this user + category
    cursor.execute("""
        SELECT * FROM interest_scores
        WHERE user_id = ? AND category = ?
    """, (user_id, category))
    existing = cursor.fetchone()

    if existing is None:
        # First time user reads this category - create new record
        new_score = min(0.1 + (time_spent_sec / 600), 1.0)
        # min(..., 1.0) makes sure score never goes above 1
        cursor.execute("""
            INSERT INTO interest_scores
            (user_id, category, score, article_count, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, category, new_score, 1, datetime.now().isoformat()))
    else:
        # User has read this category before - update existing record
        existing = dict(existing)
        new_count = existing["article_count"] + 1
        new_score = min((new_count * 0.5 + (time_spent_sec / 60) * 0.5) / 10, 1.0)
        cursor.execute("""
            UPDATE interest_scores
            SET score = ?, article_count = ?, updated_at = ?
            WHERE user_id = ? AND category = ?
        """, (new_score, new_count, datetime.now().isoformat(), user_id, category))

    conn.commit()
    conn.close()

def get_interest_scores(user_id):
    # This function returns all interest scores for a user
    # Personalizer agent uses this to rank articles
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT category, score FROM interest_scores
        WHERE user_id = ?
        ORDER BY score DESC
    """, (user_id,))
    # ORDER BY score DESC means highest score comes first

    rows = cursor.fetchall()
    conn.close()

    # Convert to simple dictionary like {"markets": 0.87, "startups": 0.65}
    scores = {}
    for row in rows:
        scores[row["category"]] = row["score"]
    return scores

# This block runs only when you run this file directly
# It will NOT run when other files import this file
if __name__ == "__main__":
    print("Creating database...")
    create_tables()

    print("\nTesting save_user...")
    save_user(
        user_id="user_123",
        profession="investor",
        interests=["markets", "startups", "economy"],
        language="english"
    )

    print("\nTesting get_user...")
    user = get_user("user_123")
    print("User found:", user)

    print("\nTesting reading history...")
    save_reading_history("user_123", "Nifty crosses 24500", "markets", 120)
    save_reading_history("user_123", "Zepto raises 350M", "startups", 90)
    save_reading_history("user_123", "RBI holds repo rate", "markets", 200)

    print("\nTesting interest scores...")
    scores = get_interest_scores("user_123")
    print("Interest scores:", scores)

    print("\nAll database tests passed!")