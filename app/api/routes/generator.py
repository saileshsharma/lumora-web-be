"""
Outfit Generator Routes
Endpoints for generating outfit suggestions with AI
"""

from flask import Blueprint, request, jsonify
import logging
import json

from app.services import (
    OpenAIService,
    ImageService,
    FALService,
    NanoBananaService
)
from app.config.constants import BACKGROUND_MAP, DEFAULT_BACKGROUND
from app.utils.exceptions import (
    ValidationError,
    OpenAIServiceError,
    APIException,
    ConfigurationError
)

logger = logging.getLogger(__name__)

generator_bp = Blueprint('generator', __name__)


@generator_bp.route('/generate-outfit', methods=['POST'])
def generate_outfit():
    """
    Generate outfit suggestions based on user preferences with realistic person image

    Request JSON:
        {
            "user_image": "data:image/...;base64,...",
            "occasion": "Casual Outing",
            "wow_factor": 5,
            "brands": ["Nike", "Adidas"],  # optional
            "budget": "Under $50",  # optional
            "conditions": "Prefer sustainable fashion"  # optional
        }

    Returns:
        JSON response with outfit description and generated image
    """
    try:
        logger.info("="*60)
        logger.info("GENERATE OUTFIT REQUEST RECEIVED")
        logger.info("="*60)

        # Log raw request data
        logger.debug(f"Request method: {request.method}")
        logger.debug(f"Request headers: {dict(request.headers)}")
        logger.debug(f"Request content-type: {request.content_type}")

        data = request.json
        logger.debug(f"Request data keys: {list(data.keys()) if data else 'None'}")

        # Extract parameters
        user_image = data.get('user_image', None)
        wow_factor = data.get('wow_factor', 5)
        brands = data.get('brands', [])
        budget = data.get('budget', '')
        occasion = data.get('occasion', 'Casual Outing')
        conditions = data.get('conditions', '')

        logger.info(f"Parameters:")
        logger.info(f"  - Occasion: {occasion}")
        logger.info(f"  - Wow Factor: {wow_factor}")
        logger.info(f"  - Brands: {brands}")
        logger.info(f"  - Budget: {budget or 'None'}")
        logger.info(f"  - Conditions: {conditions or 'None'}")
        logger.info(f"  - User image provided: {user_image is not None}")

        # Validate required fields
        if not user_image:
            raise ValidationError(
                "No user image provided. Image generation requires a user photo.",
                details={"field": "user_image"}
            )

        # Validate image
        image_service = ImageService()
        image_service.validate_image_data(user_image)

        # Step 1: Generate outfit description using OpenAI
        logger.info("Step 1: Generating outfit description with OpenAI...")

        openai_service = OpenAIService()
        outfit_data = openai_service.generate_outfit_description(
            occasion=occasion,
            wow_factor=wow_factor,
            brands=brands if brands else None,
            budget=budget if budget else None,
            conditions=conditions if conditions else None,
            user_image=user_image
        )

        outfit_description_json = json.dumps(outfit_data)
        logger.info(f"Outfit description generated: {outfit_description_json[:500]}...")

        # Build detailed outfit description for image generation
        outfit_details = " ".join([
            f"{item['description']} in {item['color']}"
            for item in outfit_data.get('items', [])
        ])

        # Step 2: Determine appropriate background
        background = BACKGROUND_MAP.get(occasion, DEFAULT_BACKGROUND)
        logger.info(f"Background selected: {background}")
        logger.info(f"Outfit details for image: {outfit_details}")

        # Step 3: Upload user image to FAL CDN
        logger.info("Step 3: Uploading user image to FAL CDN...")

        temp_file_path = image_service.save_base64_to_temp_file(user_image)
        fal_service = FALService()
        fal_upload_url = fal_service.upload_file(temp_file_path)

        logger.info(f"User image uploaded: {fal_upload_url}")

        # Step 4: Generate outfit image using NanoBanana
        logger.info("Step 4: Generating outfit image with NanoBanana...")

        nanobanana_service = NanoBananaService()
        generated_image_base64 = nanobanana_service.generate_outfit_image(
            person_image_base64=user_image,
            outfit_description=outfit_details,
            occasion=occasion,
            background_description=background,
            fal_upload_url=fal_upload_url
        )

        logger.info("Outfit image generated successfully")

        # Format response to match frontend expectations
        result_data = json.dumps({
            "success": True,
            "outfit_description": outfit_description_json,
            "outfit_image_url": generated_image_base64
        })

        logger.info("="*60)
        logger.info("GENERATE OUTFIT COMPLETED SUCCESSFULLY")
        logger.info("="*60)

        return jsonify({
            "success": True,
            "data": result_data
        })

    except ValidationError as e:
        logger.warning(f"Validation error: {e.message}")
        return jsonify({
            "success": False,
            "error": e.message,
            "details": e.details
        }), e.status_code

    except ConfigurationError as e:
        logger.error(f"Configuration error: {e.message}")
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
        logger.error(f"Unexpected error in generate_outfit: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "details": {"error": str(e)}
        }), 500
