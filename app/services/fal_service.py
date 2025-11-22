"""
FAL Service Layer
Handles FAL AI CDN uploads for image hosting
"""

import logging
import os
from typing import Optional
import fal_client

from app.config.settings import Config
from app.utils.exceptions import (
    APIException,
    ConfigurationError,
    ImageProcessingError
)

logger = logging.getLogger(__name__)


class FALServiceError(APIException):
    """FAL Service Error"""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, status_code=503, details=details)


class FALService:
    """Service for uploading images to FAL CDN"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize FAL service

        Args:
            api_key: FAL API key (uses Config.FAL_API_KEY if not provided)
        """
        self.api_key = api_key or Config.FAL_API_KEY

        if not self.api_key:
            raise ConfigurationError(
                "FAL API key not configured",
                details={"missing_config": "FAL_API_KEY"}
            )

        # Set FAL_KEY environment variable for fal_client
        os.environ['FAL_KEY'] = self.api_key

    def upload_file(self, file_path: str) -> str:
        """
        Upload file to FAL CDN

        Args:
            file_path: Path to local file to upload

        Returns:
            Public URL of uploaded file

        Raises:
            FALServiceError: If upload fails
            ImageProcessingError: If file doesn't exist or can't be read
        """
        logger.info(f"Uploading file to FAL CDN: {file_path}")

        try:
            # Check if file exists
            if not os.path.exists(file_path):
                raise ImageProcessingError(
                    "File not found",
                    details={"file_path": file_path}
                )

            # Upload to FAL CDN
            file_url = fal_client.upload_file(file_path)

            logger.info(f"File uploaded successfully: {file_url}")
            return file_url

        except ImageProcessingError:
            # Re-raise image processing errors
            raise
        except Exception as e:
            logger.error(f"Failed to upload file to FAL CDN: {e}", exc_info=True)
            raise FALServiceError(
                "Failed to upload file to FAL CDN",
                details={"error": str(e), "file_path": file_path}
            )

    def upload_base64_image(self, base64_data: str, temp_file_path: str) -> str:
        """
        Upload base64 image to FAL CDN
        (Requires image to be saved to temp file first)

        Args:
            base64_data: Base64-encoded image (not used directly, but for context)
            temp_file_path: Path to temporary file containing the image

        Returns:
            Public URL of uploaded image

        Raises:
            FALServiceError: If upload fails
        """
        logger.info(f"Uploading base64 image via temp file: {temp_file_path}")

        try:
            return self.upload_file(temp_file_path)

        except FALServiceError:
            # Re-raise FAL errors
            raise
        except Exception as e:
            logger.error(f"Failed to upload base64 image: {e}", exc_info=True)
            raise FALServiceError(
                "Failed to upload base64 image to FAL CDN",
                details={"error": str(e)}
            )
