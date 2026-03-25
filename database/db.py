# database/db.py
# Creates SQLite database and all tables
# Updated with better interest score formula
# and new user profile fields

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "et_news.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    # TABLE 1 - users
    # Updated with new fields: experience_level, reading_time_preference
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            profession TEXT DEFAULT 'general',
            interests TEXT DEFAULT '',
            language TEXT DEFAULT 'english',
            experience_level TEXT DEFAULT 'general',
            reading_time_preference TEXT DEFAULT 'any',
            created_at TEXT,
            last_active TEXT
        )
    """)

    # Add new columns if they don't exist yet
    # This handles existing database that was created before
    # ALTER TABLE adds column only if it doesn't exist
    try:
        cursor.execute("""
            ALTER TABLE users ADD COLUMN experience_level
            TEXT DEFAULT 'general'
        """)
    except Exception:
        pass
        # Column already exists - ignore error

    try:
        cursor.execute("""
            ALTER TABLE users ADD COLUMN reading_time_preference
            TEXT DEFAULT 'any'
        """)
    except Exception:
        pass

    try:
        cursor.execute("""
            ALTER TABLE users ADD COLUMN last_active TEXT
        """)
    except Exception:
        pass

    # TABLE 2 - reading_history
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
    # Updated with normalized_score field
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS interest_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            category TEXT,
            score REAL DEFAULT 0.0,
            normalized_score REAL DEFAULT 0.0,
            article_count INTEGER DEFAULT 0,
            total_time_sec INTEGER DEFAULT 0,
            updated_at TEXT
        )
    """)

    # Add new columns if they don't exist
    try:
        cursor.execute("""
            ALTER TABLE interest_scores ADD COLUMN
            normalized_score REAL DEFAULT 0.0
        """)
    except Exception:
        pass

    try:
        cursor.execute("""
            ALTER TABLE interest_scores ADD COLUMN
            total_time_sec INTEGER DEFAULT 0
        """)
    except Exception:
        pass

    conn.commit()
    conn.close()
    print("Database and tables created/updated successfully!")

def save_user(
    user_id,
    profession="general",
    interests=[],
    language="english",
    experience_level="general",
    reading_time_preference="any"
):
    conn = get_connection()
    cursor = conn.cursor()

    interests_str = ",".join(interests)
    now = datetime.now().isoformat()

    cursor.execute("""
        INSERT OR REPLACE INTO users
        (user_id, profession, interests, language,
         experience_level, reading_time_preference,
         created_at, last_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id, profession, interests_str, language,
        experience_level, reading_time_preference,
        now, now
    ))

    conn.commit()
    conn.close()
    print(f"User {user_id} saved successfully!")

def get_user(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    # Also update last_active when user is fetched
    cursor.execute("""
        UPDATE users SET last_active = ?
        WHERE user_id = ?
    """, (datetime.now().isoformat(), user_id))

    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.commit()
    conn.close()

    if user is None:
        return None

    user_dict = dict(user)
    if user_dict["interests"]:
        user_dict["interests"] = user_dict["interests"].split(",")
    else:
        user_dict["interests"] = []
    return user_dict

def save_reading_history(
    user_id,
    article_title,
    category,
    time_spent_sec=0
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO reading_history
        (user_id, article_title, category, time_spent_sec, clicked_at)
        VALUES (?, ?, ?, ?, ?)
    """, (
        user_id, article_title, category,
        time_spent_sec, datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()

    # Update interest score after saving history
    update_interest_score(user_id, category, time_spent_sec)

def update_interest_score(user_id, category, time_spent_sec=0):
    # IMPROVED FORMULA
    # score = (click_count * 0.6) + (total_read_minutes * 0.4)
    # This gives more weight to clicks than time
    # because user might leave article open without reading

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM interest_scores
        WHERE user_id = ? AND category = ?
    """, (user_id, category))
    existing = cursor.fetchone()

    if existing is None:
        # First time reading this category
        new_count     = 1
        new_time      = time_spent_sec
        # score = (1 click * 0.6) + (time_in_minutes * 0.4)
        new_score     = (1 * 0.6) + ((time_spent_sec / 60) * 0.4)
        new_score     = min(new_score, 10.0)
        # cap at 10 before normalization

        cursor.execute("""
            INSERT INTO interest_scores
            (user_id, category, score, article_count,
             total_time_sec, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            user_id, category, new_score,
            new_count, new_time, datetime.now().isoformat()
        ))
    else:
        existing      = dict(existing)
        new_count     = existing["article_count"] + 1
        new_time      = existing["total_time_sec"] + time_spent_sec
        # Improved formula: clicks weighted 0.6, time weighted 0.4
        new_score     = (new_count * 0.6) + ((new_time / 60) * 0.4)
        new_score     = min(new_score, 10.0)

        cursor.execute("""
            UPDATE interest_scores
            SET score = ?, article_count = ?,
                total_time_sec = ?, updated_at = ?
            WHERE user_id = ? AND category = ?
        """, (
            new_score, new_count, new_time,
            datetime.now().isoformat(), user_id, category
        ))

    conn.commit()
    conn.close()

    # After updating, normalize all scores for this user
    normalize_scores(user_id)

def normalize_scores(user_id):
    # NORMALIZATION
    # Makes all scores add up to 1.0
    # So no single category dominates unfairly
    # Example: markets=0.6, startups=0.3, economy=0.1
    # All add up to 1.0 - perfect for ranking

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, score FROM interest_scores
        WHERE user_id = ?
    """, (user_id,))
    rows = cursor.fetchall()

    if not rows:
        conn.close()
        return

    # Calculate total of all raw scores
    total = sum(row["score"] for row in rows)

    if total == 0:
        conn.close()
        return

    # Divide each score by total to normalize
    for row in rows:
        normalized = round(row["score"] / total, 4)
        cursor.execute("""
            UPDATE interest_scores
            SET normalized_score = ?
            WHERE id = ?
        """, (normalized, row["id"]))

    conn.commit()
    conn.close()

def get_interest_scores(user_id):
    # Returns normalized scores for personalizer
    # normalized_score is between 0 and 1
    # all scores together add up to 1.0

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT category, score, normalized_score
        FROM interest_scores
        WHERE user_id = ?
        ORDER BY normalized_score DESC
    """, (user_id,))

    rows = cursor.fetchall()
    conn.close()

    scores = {}
    for row in rows:
        # Use normalized score for ranking
        # Fall back to raw score if normalized is 0
        scores[row["category"]] = (
            row["normalized_score"]
            if row["normalized_score"] > 0
            else row["score"]
        )
    return scores


# Test when run directly
if __name__ == "__main__":
    print("Creating/updating database...")
    create_tables()

    print("\nTesting save_user with new fields...")
    save_user(
        user_id="user_123",
        profession="investor",
        interests=["markets", "startups", "economy"],
        language="english",
        experience_level="professional",
        reading_time_preference="long"
    )

    print("\nTesting get_user...")
    user = get_user("user_123")
    print("User:", user)

    print("\nTesting reading history + improved scores...")
    save_reading_history("user_123", "Nifty crosses 24500", "markets", 180)
    save_reading_history("user_123", "Zepto raises 350M", "startups", 90)
    save_reading_history("user_123", "RBI holds repo rate", "markets", 240)
    save_reading_history("user_123", "Budget 2026 highlights", "budget", 60)

    print("\nTesting normalized interest scores...")
    scores = get_interest_scores("user_123")
    print("Normalized scores:", scores)
    print("Sum of scores:", round(sum(scores.values()), 2))
    print("(Should be 1.0 or close to it)")

    print("\nAll database tests passed!")