"""
OpenAI Service Layer
Handles all OpenAI API interactions with error handling, retry logic, and validation
"""

import json
import logging
from typing import Dict, Any, Optional, List
import openai
from openai import OpenAI
import time

from app.config.settings import Config
from app.utils.exceptions import (
    OpenAIServiceError,
    ValidationError,
    ConfigurationError
)

logger = logging.getLogger(__name__)


class OpenAIService:
    """Service for interacting with OpenAI GPT-4 Vision API"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize OpenAI service

        Args:
            api_key: OpenAI API key (uses Config.OPENAI_API_KEY if not provided)
        """
        self.api_key = api_key or Config.OPENAI_API_KEY

        if not self.api_key:
            raise ConfigurationError(
                "OpenAI API key not configured",
                details={"missing_config": "OPENAI_API_KEY"}
            )

        self.client = OpenAI(api_key=self.api_key)
        self.model = Config.OPENAI_MODEL
        self.max_tokens = Config.OPENAI_MAX_TOKENS
        self.timeout = Config.OPENAI_TIMEOUT
        self.max_retries = 3
        self.retry_delay = 1  # seconds

    def _make_api_call_with_retry(
        self,
        messages: List[Dict[str, Any]],
        response_format: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Make OpenAI API call with retry logic

        Args:
            messages: List of message objects for the API
            response_format: Optional response format specification

        Returns:
            Response content as string

        Raises:
            OpenAIServiceError: If API call fails after retries
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                logger.info(f"OpenAI API call attempt {attempt + 1}/{self.max_retries}")

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=self.max_tokens,
                    response_format=response_format or {"type": "json_object"},
                    timeout=self.timeout
                )

                content = response.choices[0].message.content
                logger.info("OpenAI API call successful")

                return content

            except openai.RateLimitError as e:
                last_error = e
                logger.warning(f"Rate limit hit, attempt {attempt + 1}/{self.max_retries}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff

            except openai.APITimeoutError as e:
                last_error = e
                logger.warning(f"Timeout error, attempt {attempt + 1}/{self.max_retries}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)

            except openai.APIConnectionError as e:
                last_error = e
                logger.warning(f"Connection error, attempt {attempt + 1}/{self.max_retries}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)

            except openai.AuthenticationError as e:
                # Don't retry authentication errors
                logger.error(f"Authentication error: {e}")
                raise OpenAIServiceError(
                    "OpenAI authentication failed",
                    details={"error": str(e)}
                )

            except openai.APIError as e:
                last_error = e
                logger.error(f"OpenAI API error: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)

        # If we get here, all retries failed
        error_msg = f"OpenAI API call failed after {self.max_retries} attempts"
        logger.error(f"{error_msg}: {last_error}")
        raise OpenAIServiceError(
            error_msg,
            details={"last_error": str(last_error)}
        )

    def rate_outfit(
        self,
        image_base64: str,
        occasion: str,
        budget: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Rate an outfit using GPT-4 Vision

        Args:
            image_base64: Base64-encoded image data with data URL prefix
            occasion: Occasion for the outfit
            budget: Optional budget constraint

        Returns:
            Dictionary with rating data including scores, explanations, and suggestions

        Raises:
            ValidationError: If input validation fails
            OpenAIServiceError: If API call fails
        """
        logger.info("="*60)
        logger.info("RATING OUTFIT WITH OPENAI")
        logger.info(f"Occasion: {occasion}, Budget: {budget or 'None'}")
        logger.info("="*60)

        # Validate inputs
        if not image_base64:
            raise ValidationError("No image provided")

        if not image_base64.startswith('data:image'):
            raise ValidationError(
                "Invalid image format",
                details={"expected": "data:image/...;base64,..."}
            )

        if not occasion:
            raise ValidationError("Occasion is required")

        # Build prompt
        budget_text = f" with a budget of {budget}" if budget else ""

        prompt = f"""Analyze this outfit for a {occasion}{budget_text}.

Please provide:
1. Wow Factor Score (1-10): Rate the overall visual impact and style
2. Occasion Fitness Score (1-10): How appropriate is this for {occasion}?
3. Overall Rating (1-10): Combined assessment

Then provide detailed feedback including:
- Strengths of the outfit
- Areas for improvement
- Specific suggestions for colors, fit, accessories
- 3-5 shopping recommendations with descriptions
- A humorous "roast" - brutally honest, witty, and playful criticism about the outfit (2-3 sentences, make it funny but not mean-spirited)

Format your response as JSON with this structure:
{{
  "wow_factor": <number>,
  "occasion_fitness": <number>,
  "overall_rating": <number>,
  "wow_factor_explanation": "<brief explanation>",
  "occasion_fitness_explanation": "<brief explanation>",
  "overall_explanation": "<brief explanation>",
  "strengths": ["<strength1>", "<strength2>", ...],
  "improvements": ["<improvement1>", "<improvement2>", ...],
  "suggestions": ["<suggestion1>", "<suggestion2>", ...],
  "roast": "<humorous witty roast of the outfit>",
  "shopping_recommendations": [
    {{
      "item": "<item name>",
      "description": "<description>",
      "price": "<estimated price>",
      "reason": "<why this would enhance the outfit>"
    }}
  ]
}}"""

        # Build messages
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_base64
                        }
                    }
                ]
            }
        ]

        try:
            # Make API call with retry logic
            result = self._make_api_call_with_retry(messages)

            # Validate JSON response
            try:
                parsed_result = json.loads(result)
                logger.info(f"Successfully parsed rating response")
                return parsed_result
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse OpenAI response as JSON: {e}")
                logger.error(f"Response content: {result[:500]}...")
                raise OpenAIServiceError(
                    "Invalid JSON response from OpenAI",
                    details={"parse_error": str(e)}
                )

        except OpenAIServiceError:
            # Re-raise OpenAI service errors
            raise
        except Exception as e:
            logger.error(f"Unexpected error in rate_outfit: {e}", exc_info=True)
            raise OpenAIServiceError(
                "Failed to rate outfit",
                details={"error": str(e)}
            )

    def generate_outfit_description(
        self,
        occasion: str,
        wow_factor: int,
        brands: Optional[List[str]] = None,
        budget: Optional[str] = None,
        conditions: Optional[str] = None,
        user_image: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate outfit description and recommendations using GPT-4

        Args:
            occasion: Occasion for the outfit
            wow_factor: Style intensity (1-10)
            brands: Optional list of preferred brands
            budget: Optional budget constraint
            conditions: Optional additional requirements
            user_image: Optional user image for personalization

        Returns:
            Dictionary with outfit description and recommendations

        Raises:
            ValidationError: If input validation fails
            OpenAIServiceError: If API call fails
        """
        logger.info("="*60)
        logger.info("GENERATING OUTFIT DESCRIPTION WITH OPENAI")
        logger.info(f"Occasion: {occasion}, Wow Factor: {wow_factor}")
        logger.info("="*60)

        # Validate inputs
        if not occasion:
            raise ValidationError("Occasion is required")

        if not isinstance(wow_factor, (int, float)) or not (1 <= wow_factor <= 10):
            raise ValidationError(
                "Wow factor must be between 1 and 10",
                details={"provided": wow_factor}
            )

        # Build style description
        if wow_factor <= 3:
            style_desc = "classic, safe, and timeless"
        elif wow_factor <= 6:
            style_desc = "balanced, stylish, and modern"
        else:
            style_desc = "bold, creative, and fashion-forward"

        # Build preference text
        brand_text = f" from brands like {', '.join(brands)}" if brands else ""
        budget_text = f" within a budget of {budget}" if budget else ""
        conditions_text = f" Additional requirements: {conditions}." if conditions else ""

        # Build prompt
        prompt = f"""Create a detailed outfit recommendation for {occasion}.

Style level: {wow_factor}/10 ({style_desc})
Preferences:{brand_text}{budget_text}
{conditions_text}

Provide:
1. Complete outfit description (top, bottom, shoes, accessories)
2. Color palette and why it works
3. Style notes and occasion appropriateness
4. 5-8 specific product recommendations with:
   - Item name and type
   - Color and material
   - Why it works for this outfit
   - Estimated price range

Format as JSON:
{{
  "outfit_summary": "<brief 2-3 sentence overview>",
  "items": [
    {{
      "category": "<top/bottom/shoes/accessories>",
      "name": "<item name>",
      "description": "<detailed description>",
      "color": "<color>",
      "material": "<material>",
      "why": "<why it works>"
    }}
  ],
  "color_palette": {{
    "primary": "<color>",
    "secondary": "<color>",
    "accent": "<color>",
    "reasoning": "<why this palette works>"
  }},
  "style_notes": "<styling tips and notes>",
  "shopping_list": [
    {{
      "item": "<item name>",
      "description": "<description>",
      "price_range": "<price range>",
      "priority": "<must-have/recommended/optional>"
    }}
  ]
}}"""

        # Build messages
        messages = []

        if user_image:
            # Include user image for personalized recommendations
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": user_image
                        }
                    }
                ]
            })
        else:
            # Text-only prompt
            messages.append({
                "role": "user",
                "content": prompt
            })

        try:
            # Make API call with retry logic
            result = self._make_api_call_with_retry(messages)

            # Validate JSON response
            try:
                parsed_result = json.loads(result)
                logger.info(f"Successfully generated outfit description")
                return parsed_result
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse OpenAI response as JSON: {e}")
                logger.error(f"Response content: {result[:500]}...")
                raise OpenAIServiceError(
                    "Invalid JSON response from OpenAI",
                    details={"parse_error": str(e)}
                )

        except OpenAIServiceError:
            # Re-raise OpenAI service errors
            raise
        except Exception as e:
            logger.error(f"Unexpected error in generate_outfit_description: {e}", exc_info=True)
            raise OpenAIServiceError(
                "Failed to generate outfit description",
                details={"error": str(e)}
            )
