"""
Error Handling Middleware
Centralized error handling for all API endpoints
"""

from flask import jsonify
import logging

from app.utils.exceptions import APIException, ValidationError, OpenAIServiceError

logger = logging.getLogger(__name__)


def register_error_handlers(app):
    """
    Register error handlers with Flask app

    Args:
        app: Flask application instance
    """

    @app.errorhandler(ValidationError)
    def handle_validation_error(error):
        """Handle validation errors"""
        logger.warning(f"Validation error: {error.message}")
        return jsonify({
            "success": False,
            "error": error.message,
            "details": error.details
        }), error.status_code

    @app.errorhandler(OpenAIServiceError)
    def handle_openai_error(error):
        """Handle OpenAI service errors"""
        logger.error(f"OpenAI error: {error.message}")
        return jsonify({
            "success": False,
            "error": error.message,
            "details": error.details
        }), error.status_code

    @app.errorhandler(APIException)
    def handle_api_exception(error):
        """Handle all API exceptions"""
        logger.error(f"API error: {error.message}")
        return jsonify({
            "success": False,
            "error": error.message,
            "details": error.details
        }), error.status_code

    @app.errorhandler(404)
    def handle_not_found(error):
        """Handle 404 errors"""
        logger.warning(f"404 Not Found: {error}")
        return jsonify({
            "success": False,
            "error": "Endpoint not found",
            "details": {"error": str(error)}
        }), 404

    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        """Handle 405 errors"""
        logger.warning(f"405 Method Not Allowed: {error}")
        return jsonify({
            "success": False,
            "error": "Method not allowed",
            "details": {"error": str(error)}
        }), 405

    @app.errorhandler(500)
    def handle_internal_error(error):
        """Handle 500 errors"""
        logger.error(f"500 Internal Server Error: {error}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "details": {"error": str(error)}
        }), 500

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        """Handle all unexpected errors"""
        logger.critical(f"Unexpected error: {error}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "An unexpected error occurred",
            "details": {"error": str(error)}
        }), 500

    logger.info("Error handlers registered successfully")
