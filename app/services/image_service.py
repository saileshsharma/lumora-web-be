"""
Image Service Layer
Handles image processing, validation, and transformations
"""

import base64
import logging
import tempfile
from io import BytesIO
from typing import Optional, Tuple
from PIL import Image

from app.config.settings import Config
from app.utils.exceptions import ImageProcessingError, ValidationError

logger = logging.getLogger(__name__)


class ImageService:
    """Service for image processing and validation"""

    @staticmethod
    def validate_image_data(image_data: str) -> bool:
        """
        Validate base64 image data

        Args:
            image_data: Base64-encoded image with data URL prefix

        Returns:
            True if valid

        Raises:
            ValidationError: If validation fails
        """
        if not image_data:
            raise ValidationError("No image data provided")

        if not isinstance(image_data, str):
            raise ValidationError(
                "Invalid image data type",
                details={"expected": "string", "got": type(image_data).__name__}
            )

        if not image_data.startswith('data:image'):
            raise ValidationError(
                "Invalid image format - must be data URL",
                details={"expected": "data:image/...;base64,..."}
            )

        # Check size (approximate, since it's base64)
        # Base64 adds ~33% overhead, so divide by 1.33 to get original size
        estimated_size = len(image_data) * 0.75
        if estimated_size > Config.MAX_IMAGE_SIZE:
            raise ValidationError(
                "Image size exceeds maximum allowed",
                details={
                    "max_size": Config.MAX_IMAGE_SIZE,
                    "estimated_size": int(estimated_size)
                }
            )

        return True

    @staticmethod
    def encode_to_base64(image_data: bytes) -> str:
        """
        Convert image bytes to base64 string with data URL prefix

        Args:
            image_data: Raw image bytes

        Returns:
            Base64-encoded image with data URL prefix

        Raises:
            ImageProcessingError: If encoding fails
        """
        try:
            # If already base64 with data URL, return as is
            if isinstance(image_data, str) and image_data.startswith('data:image'):
                return image_data

            # Otherwise, encode it
            image = Image.open(BytesIO(image_data))
            buffered = BytesIO()
            image.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()

            return f"data:image/png;base64,{img_str}"

        except Exception as e:
            logger.error(f"Failed to encode image to base64: {e}", exc_info=True)
            raise ImageProcessingError(
                "Failed to encode image",
                details={"error": str(e)}
            )

    @staticmethod
    def save_base64_to_temp_file(base64_data: str) -> str:
        """
        Save base64 image data to a temporary file

        Args:
            base64_data: Base64-encoded image (with or without data URL prefix)

        Returns:
            Path to temporary file

        Raises:
            ImageProcessingError: If saving fails
        """
        try:
            # Remove data URL prefix if present
            if ',' in base64_data:
                base64_data = base64_data.split(',')[1]

            # Decode base64
            image_data = base64.b64decode(base64_data)

            # Create temp file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            temp_file.write(image_data)
            temp_file.close()

            logger.info(f"Saved image to temp file: {temp_file.name}")
            return temp_file.name

        except Exception as e:
            logger.error(f"Failed to save base64 to temp file: {e}", exc_info=True)
            raise ImageProcessingError(
                "Failed to save image to temp file",
                details={"error": str(e)}
            )

    @staticmethod
    def optimize_image(image: Image.Image, max_size: int = 1024) -> Image.Image:
        """
        Optimize image by resizing if needed

        Args:
            image: PIL Image object
            max_size: Maximum dimension (width or height)

        Returns:
            Optimized PIL Image object
        """
        try:
            if image.width > max_size or image.height > max_size:
                image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                logger.info(f"Image resized to: {image.size}")

            return image

        except Exception as e:
            logger.error(f"Failed to optimize image: {e}", exc_info=True)
            raise ImageProcessingError(
                "Failed to optimize image",
                details={"error": str(e)}
            )

    @staticmethod
    def image_to_base64(image: Image.Image, format: str = "PNG") -> str:
        """
        Convert PIL Image to base64 string

        Args:
            image: PIL Image object
            format: Image format (PNG, JPEG, etc.)

        Returns:
            Base64-encoded image with data URL prefix

        Raises:
            ImageProcessingError: If conversion fails
        """
        try:
            buffered = BytesIO()
            image.save(buffered, format=format)
            img_str = base64.b64encode(buffered.getvalue()).decode()

            mime_type = f"image/{format.lower()}"
            return f"data:{mime_type};base64,{img_str}"

        except Exception as e:
            logger.error(f"Failed to convert image to base64: {e}", exc_info=True)
            raise ImageProcessingError(
                "Failed to convert image to base64",
                details={"error": str(e)}
            )

    @staticmethod
    def get_image_dimensions(image_data: str) -> Tuple[int, int]:
        """
        Get dimensions of base64-encoded image

        Args:
            image_data: Base64-encoded image

        Returns:
            Tuple of (width, height)

        Raises:
            ImageProcessingError: If unable to read image
        """
        try:
            # Remove data URL prefix if present
            if ',' in image_data:
                image_data = image_data.split(',')[1]

            # Decode and open image
            img_bytes = base64.b64decode(image_data)
            image = Image.open(BytesIO(img_bytes))

            return (image.width, image.height)

        except Exception as e:
            logger.error(f"Failed to get image dimensions: {e}", exc_info=True)
            raise ImageProcessingError(
                "Failed to read image dimensions",
                details={"error": str(e)}
            )
