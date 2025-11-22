"""
AI Outfit Assistant - Refactored Application Entry Point
Clean architecture with proper separation of concerns
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from app import create_app
from app.config.settings import get_config

# Get configuration based on environment
config = get_config()

# Validate configuration
try:
    config.validate()
except ValueError as e:
    print(f"Configuration error: {e}")
    print("Please ensure all required API keys are set in .env file")
    exit(1)

# Create Flask application
app = create_app(config)

if __name__ == '__main__':
    # Run the application
    app.run(
        host=config.HOST,
        port=config.PORT,
        debug=config.DEBUG
    )
