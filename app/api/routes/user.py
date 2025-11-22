"""
User Routes
Endpoints for user profile and statistics
"""

from flask import Blueprint, request, jsonify
import logging

from app.services import UserStatsService
from app.utils.auth_utils import get_user_from_token
from app.utils.exceptions import APIException

logger = logging.getLogger(__name__)

user_bp = Blueprint('user', __name__)


@user_bp.route('/user/stats', methods=['GET'])
def get_user_stats():
    """
    Get statistics for the authenticated user

    Returns:
        JSON response with user statistics:
        {
            "success": true,
            "stats": {
                "outfits_generated": 0,
                "outfits_rated": 0,
                "arena_submissions": 0,
                "favorite_outfits": 0
            }
        }
    """
    try:
        logger.info("Get user stats request received")

        # Extract user from token
        user_info = get_user_from_token()

        if not user_info:
            logger.warning("No user token found in request")
            return jsonify({
                "success": False,
                "error": "Authentication required"
            }), 401

        user_id = user_info['user_id']
        logger.info(f"Fetching stats for user: {user_info['username']} ({user_id})")

        # Get statistics
        stats = UserStatsService.get_user_statistics(user_id)

        logger.info(f"Stats retrieved successfully: {stats}")

        return jsonify({
            "success": True,
            "stats": stats
        })

    except APIException as e:
        logger.error(f"API error: {e.message}")
        return jsonify({
            "success": False,
            "error": e.message,
            "details": e.details
        }), e.status_code

    except Exception as e:
        logger.error(f"Unexpected error in get_user_stats: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "details": {"error": str(e)}
        }), 500
