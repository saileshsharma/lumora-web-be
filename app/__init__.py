"""
AI Outfit Assistant Application
Main application factory and initialization
"""

from flask import Flask
from flask_cors import CORS
import logging
import os
from datetime import datetime

from app.config.settings import Config
from app.api.middlewares.error_handler import register_error_handlers
from app.api.routes import health_bp, rater_bp, generator_bp


def create_app(config=None):
    """
    Application factory pattern

    Args:
        config: Configuration class (uses Config if not provided)

    Returns:
        Configured Flask application
    """
    # Create Flask app
    app = Flask(__name__)

    # Load configuration
    if config is None:
        config = Config

    app.config.from_object(config)

    # Configure logging
    setup_logging(config)

    # Configure CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": config.CORS_ORIGINS,
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True
        }
    })

    # Register blueprints
    app.register_blueprint(health_bp, url_prefix='/api')
    app.register_blueprint(rater_bp, url_prefix='/api')
    app.register_blueprint(generator_bp, url_prefix='/api')

    # Register error handlers
    register_error_handlers(app)

    # Log startup
    logger = logging.getLogger(__name__)
    logger.info("="*60)
    logger.info("OUTFIT ASSISTANT APPLICATION STARTED")
    logger.info(f"Environment: {config.ENV}")
    logger.info(f"Debug: {config.DEBUG}")
    logger.info("="*60)

    return app


def setup_logging(config):
    """
    Configure application logging

    Args:
        config: Configuration object
    """
    # Create log directory
    os.makedirs(config.LOG_DIR, exist_ok=True)

    # Create log filename with timestamp
    log_filename = os.path.join(
        config.LOG_DIR,
        f"outfit_assistant_{datetime.now().strftime('%Y%m%d')}.log"
    )

    # Configure logging format with more details
    logging.basicConfig(
        level=logging.DEBUG,  # Set to DEBUG for full logging
        format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler()  # Also output to console
        ],
        force=True  # Force reconfiguration
    )

    # Set werkzeug to INFO to avoid too many logs
    logging.getLogger('werkzeug').setLevel(logging.INFO)

    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured: {log_filename}")
    logger.info(f"Log level: DEBUG (full logging enabled)")
