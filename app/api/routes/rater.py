"""
Outfit Rater Routes
Endpoints for rating and analyzing outfits
"""

from flask import Blueprint, request, jsonify
import logging
import json

from app.services import OpenAIService, ImageService, UserStatsService
from app.utils.exceptions import ValidationError, OpenAIServiceError, APIException
from app.utils.auth_utils import get_user_from_token

logger = logging.getLogger(__name__)

rater_bp = Blueprint('rater', __name__)


@rater_bp.route('/rate-outfit', methods=['POST'])
def rate_outfit():
    """
    Rate an outfit based on uploaded photo, occasion, and budget

    Request JSON:
        {
            "image": "data:image/...;base64,...",
            "occasion": "Casual Outing",
            "budget": "Under $50"  # optional
        }

    Returns:
        JSON response with rating data
    """
    try:
        logger.info("="*60)
        logger.info("RATE OUTFIT REQUEST RECEIVED")
        logger.info("="*60)

        data = request.json

        # Extract parameters
        image_base64 = data.get('image')
        occasion = data.get('occasion', 'Casual Outing')
        budget = data.get('budget', '')

        logger.info(f"Parameters - Occasion: {occasion}, Budget: {budget or 'None'}")

        # Validate image
        image_service = ImageService()
        image_service.validate_image_data(image_base64)

        # Rate outfit using OpenAI service
        openai_service = OpenAIService()
        result = openai_service.rate_outfit(
            image_base64=image_base64,
            occasion=occasion,
            budget=budget
        )

        logger.info("Outfit rated successfully")

        # Track user statistics
        user_info = get_user_from_token()
        if user_info:
            UserStatsService.increment_outfit_rated(
                user_id=user_info['user_id'],
                username=user_info['username'],
                email=user_info['email']
            )
            logger.info(f"Tracked outfit rating for user: {user_info['username']}")

        logger.info("="*60)

        # Frontend expects data as JSON string
        return jsonify({
            "success": True,
            "data": json.dumps(result)
        })

    except ValidationError as e:
        logger.warning(f"Validation error: {e.message}")
        return jsonify({
            "success": False,
            "error": e.message,
            "details": e.details
        }), e.status_code

    except OpenAIServiceError as e:
        logger.error(f"OpenAI service error: {e.message}")
        return jsonify({
            "success": False,
            "error": e.message,
            "details": e.details
        }), e.status_code

    except APIException as e:
        logger.error(f"API error: {e.message}")
        return jsonify({
            "success": False,
            "error": e.message,
            "details": e.details
        }), e.status_code

    except Exception as e:
        logger.error(f"Unexpected error in rate_outfit: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "details": {"error": str(e)}
        }), 500
