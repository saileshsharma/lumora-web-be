"""
NanoBanana Service Layer
Handles image generation using NanoBanana API with face preservation
"""

import logging
import time
from typing import Optional
import requests
from io import BytesIO
from PIL import Image

from app.config.settings import Config
from app.config.constants import ERROR_MESSAGES
from app.utils.exceptions import (
    APIException,
    ConfigurationError,
    ImageProcessingError
)
from app.services.image_service import ImageService

logger = logging.getLogger(__name__)


class NanoBananaServiceError(APIException):
    """NanoBanana API Error"""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, status_code=503, details=details)


class NanoBananaService:
    """Service for generating outfit images using NanoBanana API"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize NanoBanana service

        Args:
            api_key: NanoBanana API key (uses Config.NANOBANANA_API_KEY if not provided)
        """
        self.api_key = api_key or Config.NANOBANANA_API_KEY

        if not self.api_key:
            raise ConfigurationError(
                "NanoBanana API key not configured",
                details={"missing_config": "NANOBANANA_API_KEY"}
            )

        self.base_url = "https://api.nanobananaapi.ai/api/v1/nanobanana"
        self.image_service = ImageService()
        self.max_poll_attempts = 60  # 60 attempts * 2 seconds = 2 minutes max
        self.poll_interval = 2  # seconds

    def _submit_task(
        self,
        prompt: str,
        image_url: str
    ) -> str:
        """
        Submit image generation task to NanoBanana API

        Args:
            prompt: Generation prompt
            image_url: URL of source image

        Returns:
            Task ID

        Raises:
            NanoBananaServiceError: If submission fails
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "prompt": prompt,
            "type": "IMAGETOIAMGE",  # Image to Image editing
            "imageUrls": [image_url],
            "numImages": 1,
            "image_size": "3:4",  # Portrait format for fashion
            "callBackUrl": "https://webhook.site/dummy"  # Dummy callback, we'll poll instead
        }

        logger.info(f"Submitting task to NanoBanana API...")
        logger.info(f"Payload: {payload}")

        try:
            response = requests.post(
                f"{self.base_url}/generate",
                headers=headers,
                json=payload,
                timeout=30
            )

            if response.status_code != 200:
                logger.error(f"NanoBanana API request failed: {response.status_code} - {response.text}")
                raise NanoBananaServiceError(
                    f"API request failed with status {response.status_code}",
                    details={"response": response.text}
                )

            task_data = response.json()
            logger.info(f"Task response: {task_data}")

            if task_data.get('code') != 200:
                error_msg = task_data.get('msg', 'Unknown error')
                raise NanoBananaServiceError(
                    f"Task submission failed: {error_msg}",
                    details={"response": task_data}
                )

            task_id = task_data['data']['taskId']
            logger.info(f"Task submitted successfully: {task_id}")

            return task_id

        except requests.RequestException as e:
            logger.error(f"Network error submitting task: {e}", exc_info=True)
            raise NanoBananaServiceError(
                "Network error communicating with NanoBanana API",
                details={"error": str(e)}
            )

    def _poll_task_status(self, task_id: str) -> str:
        """
        Poll task status until completion or timeout

        Args:
            task_id: Task ID to poll

        Returns:
            URL of generated image

        Raises:
            NanoBananaServiceError: If polling fails or times out
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        logger.info(f"Polling task status: {task_id}")
        logger.info(f"Max attempts: {self.max_poll_attempts}, Interval: {self.poll_interval}s")

        for attempt in range(self.max_poll_attempts):
            time.sleep(self.poll_interval)

            try:
                status_response = requests.get(
                    f"{self.base_url}/record-info?taskId={task_id}",
                    headers=headers,
                    timeout=10
                )

                if status_response.status_code != 200:
                    logger.warning(f"Status check failed: {status_response.status_code}")
                    continue

                status_data = status_response.json()
                logger.info(f"Attempt {attempt + 1}/{self.max_poll_attempts}: {status_data}")

                if status_data.get('code') == 200:
                    task_info = status_data.get('data', {})
                    success_flag = task_info.get('successFlag')

                    if success_flag == 1:
                        # Task completed successfully
                        response_data = task_info.get('response', {})
                        generated_image_url = response_data.get('resultImageUrl')

                        if generated_image_url:
                            logger.info(f"Image generated successfully: {generated_image_url}")
                            return generated_image_url
                        else:
                            logger.warning("Success flag is 1 but no resultImageUrl found")

                    elif success_flag is not None and success_flag != 0:
                        # Task failed
                        error_msg = task_info.get('errorMessage', 'Unknown error')
                        raise NanoBananaServiceError(
                            f"Image generation failed: {error_msg}",
                            details={"task_info": task_info}
                        )
                    # If success_flag is 0, task is still processing, continue polling

            except requests.RequestException as e:
                logger.warning(f"Network error checking status (attempt {attempt + 1}): {e}")
                continue

        # Timeout reached
        raise NanoBananaServiceError(
            "Image generation timeout - task took too long",
            details={"task_id": task_id, "attempts": self.max_poll_attempts}
        )

    def generate_outfit_image(
        self,
        person_image_base64: str,
        outfit_description: str,
        occasion: str,
        background_description: str,
        fal_upload_url: str
    ) -> str:
        """
        Generate outfit image with face preservation

        Args:
            person_image_base64: Base64-encoded person image
            outfit_description: Description of outfit to generate
            occasion: Occasion for the outfit
            background_description: Background setting description
            fal_upload_url: URL where person image has been uploaded (via FAL CDN)

        Returns:
            Base64-encoded generated image

        Raises:
            NanoBananaServiceError: If generation fails
            ImageProcessingError: If image processing fails
        """
        logger.info("="*60)
        logger.info("NANOBANANA IMAGE GENERATION STARTED")
        logger.info("="*60)
        logger.info(f"Occasion: {occasion}")
        logger.info(f"Outfit: {outfit_description[:200]}...")
        logger.info(f"Background: {background_description}")

        # Build prompt
        prompt = f"""Transform this person wearing {outfit_description}.
Setting: {background_description}.
Occasion: {occasion}.
Keep the same person's face and features exactly as in the original image. Natural pose appropriate for {occasion}, facial expression matching the formality.
Photorealistic, professional fashion photography, magazine quality, 3/4 body shot with professional studio lighting."""

        logger.info("-" * 60)
        logger.info("PROMPT:")
        logger.info(prompt)
        logger.info("-" * 60)

        try:
            # Submit task
            task_id = self._submit_task(prompt, fal_upload_url)

            # Poll for completion
            generated_image_url = self._poll_task_status(task_id)

            # Download generated image
            logger.info(f"Downloading generated image...")
            response = requests.get(generated_image_url, timeout=30)

            if response.status_code != 200:
                raise NanoBananaServiceError(
                    "Failed to download generated image",
                    details={"status_code": response.status_code}
                )

            # Open and optimize image
            img = Image.open(BytesIO(response.content))
            logger.info(f"Downloaded image: {len(response.content)} bytes, size: {img.size}")

            # Optimize image
            img = self.image_service.optimize_image(img, max_size=1024)

            # Convert to base64
            base64_image = self.image_service.image_to_base64(img, format="PNG")

            logger.info("Image generation completed successfully")
            logger.info("="*60)

            return base64_image

        except NanoBananaServiceError:
            # Re-raise NanoBanana errors
            raise
        except ImageProcessingError:
            # Re-raise image processing errors
            raise
        except Exception as e:
            logger.error(f"Unexpected error in generate_outfit_image: {e}", exc_info=True)
            raise NanoBananaServiceError(
                "Failed to generate outfit image",
                details={"error": str(e)}
            )
