"""
Custom Exceptions
"""


class APIException(Exception):
    """Base API Exception"""

    def __init__(self, message: str, status_code: int = 500, details: dict = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(APIException):
    """Validation Error"""

    def __init__(self, message: str, details: dict = None):
        super().__init__(message, status_code=400, details=details)


class OpenAIServiceError(APIException):
    """OpenAI Service Error"""

    def __init__(self, message: str, details: dict = None):
        super().__init__(message, status_code=503, details=details)


class FALServiceError(APIException):
    """FAL Service Error"""

    def __init__(self, message: str, details: dict = None):
        super().__init__(message, status_code=503, details=details)


class ImageProcessingError(APIException):
    """Image Processing Error"""

    def __init__(self, message: str, details: dict = None):
        super().__init__(message, status_code=400, details=details)


class ConfigurationError(APIException):
    """Configuration Error"""

    def __init__(self, message: str, details: dict = None):
        super().__init__(message, status_code=500, details=details)
