# agents/profiler.py
# This agent reads user data from SQLite database
# It builds a complete user profile object
# No LLM needed - just database reads
# Every other agent uses this profile to personalize results

import sys
import os

# This line tells Python where to find our other files
# Without this, Python cannot find database/db.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import get_user, get_interest_scores, save_user

def run_profiler(user_id: str) -> dict:
    # This is the main function of this agent
    # Input: user_id (just a string like "user_123")
    # Output: complete profile dictionary

    print(f"Profiler Agent: Reading profile for {user_id}")

    # STEP 1 - Try to get user from database
    user = get_user(user_id)

    if user is None:
        # User not found in database
        # This means it's a brand new user - first time opening app
        # We create a default profile for them
        print(f"Profiler Agent: New user detected - creating default profile")
        save_user(
            user_id=user_id,
            profession="general",
            interests=[],
            language="english"
        )
        # Read it back after saving
        user = get_user(user_id)

    # STEP 2 - Get their interest scores
    # These scores are auto-calculated from reading history
    interest_scores = get_interest_scores(user_id)

    if not interest_scores:
        # Brand new user has no reading history yet
        # Give equal score to all categories
        # So all news shows equally until they start reading
        interest_scores = {
            "markets": 0.5,
            "startups": 0.5,
            "economy": 0.5,
            "tech": 0.5,
            "budget": 0.5
        }
        print("Profiler Agent: No reading history yet - using default equal scores")

    # STEP 3 - Build the complete profile object
    # This is what gets passed to other agents
    profile = {
        "user_id": user["user_id"],
        "profession": user["profession"],
        "interests": user["interests"],
        # interests from manual setup (optional)
        "language": user["language"],
        "interest_scores": interest_scores,
        # auto-calculated scores from reading history
        "is_new_user": len(interest_scores) == 0 or all(
            v == 0.5 for v in interest_scores.values()
        )
        # is_new_user = True means no personalization data yet
        # Personalizer will show all news equally for new users
    }

    print(f"Profiler Agent: Profile built successfully")
    print(f"  Profession: {profile['profession']}")
    print(f"  Interests: {profile['interests']}")
    print(f"  Language: {profile['language']}")
    print(f"  Top interest score: {max(interest_scores, key=interest_scores.get)} = {max(interest_scores.values()):.2f}")

    return profile


# Test this agent directly
if __name__ == "__main__":
    print("=" * 40)
    print("Testing Profiler Agent")
    print("=" * 40)

    # Test 1 - New user (never seen before)
    print("\nTest 1: Brand new user")
    profile = run_profiler("new_user_999")
    print("Result:", profile)

    # Test 2 - Existing user from database test
    print("\nTest 2: Existing user (user_123 from db test)")
    profile = run_profiler("user_123")
    print("Result:", profile)

    print("\nProfiler Agent working correctly!")