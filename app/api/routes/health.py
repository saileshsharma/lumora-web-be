"""
Health Check Routes
System health and status endpoints
"""

from flask import Blueprint, jsonify
import logging

logger = logging.getLogger(__name__)

health_bp = Blueprint('health', __name__)


@health_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint

    Returns:
        JSON response with health status
    """
    logger.debug("Health check requested")

    return jsonify({
        "status": "healthy",
        "message": "Outfit Assistant API is running"
    })
