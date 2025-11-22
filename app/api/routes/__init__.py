"""
API Routes Module
All API endpoint blueprints
"""

from app.api.routes.health import health_bp
from app.api.routes.rater import rater_bp
from app.api.routes.generator import generator_bp

__all__ = [
    'health_bp',
    'rater_bp',
    'generator_bp'
]
