"""
Application Configuration
Centralized configuration management
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Base configuration"""

    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    ENV = os.getenv('FLASK_ENV', 'production')

    # Server
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 5001))

    # API Keys
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    FAL_API_KEY = os.getenv('FAL_API_KEY')
    NANOBANANA_API_KEY = os.getenv('NANOBANANA_API_KEY')

    # CORS Origins
    CORS_ORIGINS = [
        "https://ai-outfit-assistant.vercel.app",
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:5001",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5001",
        "https://lumora-web-production.up.railway.app",
        "https://web-production-c70ba.up.railway.app",
    ]

    # API Configuration
    OPENAI_MODEL = "gpt-4o"
    OPENAI_MAX_TOKENS = 1500
    OPENAI_TIMEOUT = 30

    # Image Configuration
    MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
    ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp']

    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_DIR = 'logs'

    # Fashion Arena
    ARENA_DB_PATH = './fashion_arena_db.json'

    @classmethod
    def validate(cls):
        """Validate required configuration"""
        required_keys = ['OPENAI_API_KEY', 'FAL_API_KEY', 'NANOBANANA_API_KEY']
        missing = [key for key in required_keys if not getattr(cls, key)]

        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")

        return True


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    ENV = 'development'


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    ENV = 'production'


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    ENV = 'testing'


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config():
    """Get configuration based on environment"""
    env = os.getenv('FLASK_ENV', 'development')
    return config.get(env, config['default'])
