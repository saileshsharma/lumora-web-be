"""
Fashion Arena Module - Handles photo submissions, voting, and leaderboard
"""
import json
import os
from datetime import datetime
import uuid

# Database path configuration
# Railway: Uses /app/data volume for persistence
# Development: Uses outfit-assistant directory (one level up from backend/)
if os.path.exists('/app/data'):
    # Railway production environment
    DATA_DIR = '/app/data'
else:
    # Local development - DB is in outfit-assistant directory
    backend_dir = os.path.dirname(os.path.abspath(__file__))  # .../backend
    DATA_DIR = os.path.dirname(backend_dir)  # .../outfit-assistant

os.makedirs(DATA_DIR, exist_ok=True)
FASHION_ARENA_DB = os.path.join(DATA_DIR, "fashion_arena_db.json")
print(f"Fashion Arena DB path: {FASHION_ARENA_DB}")

def initialize_db():
    """Initialize the fashion arena database if it doesn't exist"""
    if not os.path.exists(FASHION_ARENA_DB):
        with open(FASHION_ARENA_DB, 'w') as f:
            json.dump({
                "submissions": [],
                "votes": {}
            }, f)

def load_db():
    """Load the fashion arena database"""
    initialize_db()
    with open(FASHION_ARENA_DB, 'r') as f:
        return json.load(f)

def save_db(data):
    """Save the fashion arena database"""
    with open(FASHION_ARENA_DB, 'w') as f:
        json.dump(data, f, indent=2)

def submit_to_arena(photo_data, title, description, occasion, source_mode, user_id=None):
    """
    Submit a photo to Fashion Arena
    
    Args:
        photo_data: Base64 encoded image data
        title: Title of the submission
        description: Description of the outfit
        occasion: Occasion for the outfit
        source_mode: 'rater' or 'generator'
        user_id: Optional user identifier
    
    Returns:
        dict: Submission details including submission_id
    """
    db = load_db()
    
    submission_id = str(uuid.uuid4())
    submission = {
        "id": submission_id,
        "photo": photo_data,
        "title": title,
        "description": description,
        "occasion": occasion,
        "source_mode": source_mode,
        "user_id": user_id or "anonymous",
        "created_at": datetime.now().isoformat(),
        "total_votes": 0,
        "total_rating": 0,
        "vote_count": 0,
        "average_rating": 0
    }
    
    db["submissions"].append(submission)
    save_db(db)
    
    return submission

def get_all_submissions(sort_by="recent"):
    """
    Get all Fashion Arena submissions
    
    Args:
        sort_by: 'recent', 'top_voted', or 'top_rated'
    
    Returns:
        list: List of submissions
    """
    db = load_db()
    submissions = db["submissions"]
    
    if sort_by == "top_voted":
        submissions = sorted(submissions, key=lambda x: x["total_votes"], reverse=True)
    elif sort_by == "top_rated":
        submissions = sorted(submissions, key=lambda x: x["average_rating"], reverse=True)
    else:  # recent
        submissions = sorted(submissions, key=lambda x: x["created_at"], reverse=True)
    
    return submissions

def get_leaderboard(limit=10):
    """
    Get top submissions for the leaderboard
    
    Args:
        limit: Number of top submissions to return (default 10)
    
    Returns:
        list: Top submissions sorted by average rating
    """
    db = load_db()
    submissions = db["submissions"]
    
    # Sort by average rating, then by total votes as tiebreaker
    sorted_submissions = sorted(
        submissions,
        key=lambda x: (x["average_rating"], x["total_votes"]),
        reverse=True
    )
    
    return sorted_submissions[:limit]

def vote_submission(submission_id, vote_type, rating, voter_id=None):
    """
    Vote on a submission
    
    Args:
        submission_id: ID of the submission to vote on
        vote_type: 'upvote' or 'downvote'
        rating: Rating value (1-10)
        voter_id: Optional voter identifier
    
    Returns:
        dict: Updated submission or None if not found
    """
    db = load_db()
    voter_id = voter_id or "anonymous"
    
    # Find the submission
    submission = None
    for sub in db["submissions"]:
        if sub["id"] == submission_id:
            submission = sub
            break
    
    if not submission:
        return None
    
    # Check if user already voted
    vote_key = f"{submission_id}_{voter_id}"
    if vote_key in db["votes"]:
        # User already voted, update their vote
        old_vote = db["votes"][vote_key]
        
        # Update vote count
        if old_vote["vote_type"] == "upvote" and vote_type == "downvote":
            submission["total_votes"] -= 1
        elif old_vote["vote_type"] == "downvote" and vote_type == "upvote":
            submission["total_votes"] += 1
        
        # Update rating
        submission["total_rating"] = submission["total_rating"] - old_vote["rating"] + rating
        
    else:
        # New vote
        if vote_type == "upvote":
            submission["total_votes"] += 1
        
        submission["vote_count"] += 1
        submission["total_rating"] += rating
    
    # Calculate average rating
    if submission["vote_count"] > 0:
        submission["average_rating"] = round(submission["total_rating"] / submission["vote_count"], 2)
    
    # Save the vote
    db["votes"][vote_key] = {
        "submission_id": submission_id,
        "voter_id": voter_id,
        "vote_type": vote_type,
        "rating": rating,
        "voted_at": datetime.now().isoformat()
    }
    
    save_db(db)
    
    return submission

def get_submission_by_id(submission_id):
    """Get a single submission by ID"""
    db = load_db()
    for sub in db["submissions"]:
        if sub["id"] == submission_id:
            return sub
    return None

def check_user_vote(submission_id, voter_id=None):
    """Check if a user has already voted on a submission"""
    db = load_db()
    voter_id = voter_id or "anonymous"
    vote_key = f"{submission_id}_{voter_id}"
    return db["votes"].get(vote_key)

def get_stats():
    """Get Fashion Arena statistics"""
    db = load_db()
    return {
        "total_submissions": len(db["submissions"]),
        "total_votes": len(db["votes"]),
        "avg_rating_overall": round(
            sum(s["average_rating"] for s in db["submissions"]) / len(db["submissions"]), 2
        ) if db["submissions"] else 0
    }

def restore_data(backup_data):
    """
    Restore Fashion Arena data from backup

    Args:
        backup_data: dict with 'submissions' and 'votes' keys

    Returns:
        int: Number of submissions restored
    """
    try:
        # Validate backup data structure
        if isinstance(backup_data, list):
            # Handle list format (old backup)
            backup_data = {"submissions": backup_data, "votes": {}}

        if not isinstance(backup_data, dict) or "submissions" not in backup_data:
            raise ValueError("Invalid backup format")

        # Save the backup data directly
        save_db(backup_data)

        return len(backup_data.get("submissions", []))
    except Exception as e:
        raise Exception(f"Restore failed: {str(e)}")

def like_submission(submission_id):
    """
    Simple like functionality - increments total_votes by 1

    Args:
        submission_id: ID of the submission to like

    Returns:
        dict: Updated submission or None if not found
    """
    db = load_db()

    # Find the submission
    submission = None
    for sub in db["submissions"]:
        if sub["id"] == submission_id:
            submission = sub
            break

    if not submission:
        return None

    # Increment the like count
    submission["total_votes"] = submission.get("total_votes", 0) + 1

    save_db(db)

    return submission

def cleanup_invalid_submissions():
    """
    Remove submissions with invalid photo data (local file paths)

    Returns:
        dict: Cleanup results with count of removed submissions
    """
    db = load_db()
    original_count = len(db["submissions"])

    # Filter out submissions with file:// paths
    valid_submissions = [
        sub for sub in db["submissions"]
        if not (sub.get("photo", "").startswith("file://"))
    ]

    removed_count = original_count - len(valid_submissions)

    if removed_count > 0:
        db["submissions"] = valid_submissions
        save_db(db)

    return {
        "original_count": original_count,
        "removed_count": removed_count,
        "remaining_count": len(valid_submissions)
    }

def delete_submission(submission_id):
    """
    Delete a submission by ID

    Args:
        submission_id (str): The submission ID to delete

    Returns:
        bool: True if deleted successfully, False if not found
    """
    db = load_db()

    # Find and remove the submission
    original_length = len(db["submissions"])
    db["submissions"] = [sub for sub in db["submissions"] if sub["id"] != submission_id]

    if len(db["submissions"]) < original_length:
        save_db(db)
        print(f"Deleted submission: {submission_id}")
        return True
    else:
        print(f"Submission not found: {submission_id}")
        return False
