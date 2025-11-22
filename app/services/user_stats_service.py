"""
User Statistics Service
Tracks and retrieves user activity statistics
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
from threading import Lock

logger = logging.getLogger(__name__)

# File lock for thread-safe JSON operations
_file_lock = Lock()

# Path to stats database
STATS_DB_PATH = Path(__file__).parent.parent.parent / "user_stats_db.json"


class UserStatsService:
    """Service for tracking and retrieving user statistics"""

    @staticmethod
    def _load_stats() -> Dict:
        """Load stats database from JSON file"""
        try:
            if not STATS_DB_PATH.exists():
                return {"user_stats": []}

            with open(STATS_DB_PATH, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading stats database: {e}")
            return {"user_stats": []}

    @staticmethod
    def _save_stats(data: Dict) -> None:
        """Save stats database to JSON file"""
        try:
            with _file_lock:
                with open(STATS_DB_PATH, 'w') as f:
                    json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving stats database: {e}")

    @staticmethod
    def _get_user_stats(user_id: str) -> Optional[Dict]:
        """Get existing stats for a user"""
        data = UserStatsService._load_stats()
        for user_stat in data.get("user_stats", []):
            if user_stat.get("user_id") == user_id:
                return user_stat
        return None

    @staticmethod
    def _initialize_user_stats(user_id: str, username: str = "", email: str = "") -> Dict:
        """Initialize stats for a new user"""
        return {
            "user_id": user_id,
            "username": username,
            "email": email,
            "outfits_generated": 0,
            "outfits_rated": 0,
            "arena_submissions": 0,
            "favorite_outfits": 0,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

    @staticmethod
    def increment_outfit_generated(user_id: str, username: str = "", email: str = "") -> None:
        """Increment outfit generated count for user"""
        try:
            data = UserStatsService._load_stats()
            user_stats = UserStatsService._get_user_stats(user_id)

            if user_stats is None:
                # Create new user stats
                user_stats = UserStatsService._initialize_user_stats(user_id, username, email)
                data["user_stats"].append(user_stats)

            # Update count
            for stats in data["user_stats"]:
                if stats["user_id"] == user_id:
                    stats["outfits_generated"] += 1
                    stats["updated_at"] = datetime.utcnow().isoformat()
                    # Update username/email if provided
                    if username:
                        stats["username"] = username
                    if email:
                        stats["email"] = email
                    break

            UserStatsService._save_stats(data)
            logger.info(f"Incremented outfit_generated for user {user_id}")
        except Exception as e:
            logger.error(f"Error incrementing outfit_generated: {e}")

    @staticmethod
    def increment_outfit_rated(user_id: str, username: str = "", email: str = "") -> None:
        """Increment outfit rated count for user"""
        try:
            data = UserStatsService._load_stats()
            user_stats = UserStatsService._get_user_stats(user_id)

            if user_stats is None:
                # Create new user stats
                user_stats = UserStatsService._initialize_user_stats(user_id, username, email)
                data["user_stats"].append(user_stats)

            # Update count
            for stats in data["user_stats"]:
                if stats["user_id"] == user_id:
                    stats["outfits_rated"] += 1
                    stats["updated_at"] = datetime.utcnow().isoformat()
                    # Update username/email if provided
                    if username:
                        stats["username"] = username
                    if email:
                        stats["email"] = email
                    break

            UserStatsService._save_stats(data)
            logger.info(f"Incremented outfit_rated for user {user_id}")
        except Exception as e:
            logger.error(f"Error incrementing outfit_rated: {e}")

    @staticmethod
    def increment_arena_submission(user_id: str, username: str = "", email: str = "") -> None:
        """Increment arena submission count for user"""
        try:
            data = UserStatsService._load_stats()
            user_stats = UserStatsService._get_user_stats(user_id)

            if user_stats is None:
                # Create new user stats
                user_stats = UserStatsService._initialize_user_stats(user_id, username, email)
                data["user_stats"].append(user_stats)

            # Update count
            for stats in data["user_stats"]:
                if stats["user_id"] == user_id:
                    stats["arena_submissions"] += 1
                    stats["updated_at"] = datetime.utcnow().isoformat()
                    # Update username/email if provided
                    if username:
                        stats["username"] = username
                    if email:
                        stats["email"] = email
                    break

            UserStatsService._save_stats(data)
            logger.info(f"Incremented arena_submission for user {user_id}")
        except Exception as e:
            logger.error(f"Error incrementing arena_submission: {e}")

    @staticmethod
    def get_user_statistics(user_id: str) -> Dict:
        """Get statistics for a specific user"""
        try:
            user_stats = UserStatsService._get_user_stats(user_id)

            if user_stats is None:
                # Return zeros for new user
                return {
                    "outfits_generated": 0,
                    "outfits_rated": 0,
                    "arena_submissions": 0,
                    "favorite_outfits": 0
                }

            return {
                "outfits_generated": user_stats.get("outfits_generated", 0),
                "outfits_rated": user_stats.get("outfits_rated", 0),
                "arena_submissions": user_stats.get("arena_submissions", 0),
                "favorite_outfits": user_stats.get("favorite_outfits", 0)
            }
        except Exception as e:
            logger.error(f"Error getting user statistics: {e}")
            return {
                "outfits_generated": 0,
                "outfits_rated": 0,
                "arena_submissions": 0,
                "favorite_outfits": 0
            }
