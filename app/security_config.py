"""
Security configuration for the AI Outfit Assistant API.
Includes rate limiting, security headers, and input validation schemas.
"""

import os
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from marshmallow import Schema, fields, validate, ValidationError

# ============================================================================
# RATE LIMITING CONFIGURATION
# ============================================================================

def get_limiter_storage():
    """Get storage backend for rate limiter (in-memory by default)."""
    # For production, consider using Redis:
    # return "redis://localhost:6379"
    return "memory://"

def configure_rate_limiter(app):
    """Configure Flask-Limiter with appropriate rate limits."""
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["500 per day", "100 per hour"],
        storage_uri=get_limiter_storage(),
        storage_options={},
        strategy="fixed-window"
    )

    return limiter

# Rate limit configurations for different endpoint types
RATE_LIMITS = {
    # Expensive AI endpoints - strict limits
    "ai_generation": "5 per hour",  # Image generation with FAL AI
    "ai_rating": "20 per hour",      # OpenAI GPT-4 calls
    "ai_tryon": "10 per hour",       # Virtual try-on

    # User actions - moderate limits
    "user_action": "30 per minute",  # Submit outfit, vote, etc.
    "api_read": "60 per minute",     # Get requests

    # Auth endpoints - strict limits to prevent brute force
    "auth": "10 per hour",

    # Admin endpoints - very strict
    "admin": "5 per hour"
}

# ============================================================================
# SECURITY HEADERS CONFIGURATION
# ============================================================================

def configure_security_headers(app):
    """Configure Flask-Talisman for security headers."""

    # Determine if we're in production
    is_production = os.getenv('FLASK_ENV') == 'production'

    # Content Security Policy
    csp = {
        'default-src': ["'self'"],
        'script-src': [
            "'self'",
            "'unsafe-inline'",  # Required for some React features
            'https://cdn.jsdelivr.net',
        ],
        'style-src': [
            "'self'",
            "'unsafe-inline'",  # Required for inline styles
        ],
        'img-src': [
            "'self'",
            'data:',  # For base64 images
            'https:',  # Allow all HTTPS images (from AI APIs)
            'blob:',
        ],
        'font-src': ["'self'", 'data:'],
        'connect-src': [
            "'self'",
            'https://api.openai.com',
            'https://fal.run',
            'https://api.nanobanana.net',
        ],
        'frame-ancestors': ["'none'"],  # Prevent clickjacking
        'base-uri': ["'self'"],
        'form-action': ["'self'"],
    }

    # Configure Talisman
    talisman = Talisman(
        app,
        force_https=is_production,  # Only enforce HTTPS in production
        strict_transport_security=is_production,
        strict_transport_security_max_age=31536000,  # 1 year
        content_security_policy=csp,
        content_security_policy_nonce_in=['script-src'],
        referrer_policy='strict-origin-when-cross-origin',
        feature_policy={
            'geolocation': "'none'",
            'microphone': "'none'",
            'camera': "'none'",
        },
        x_content_type_options=True,
        x_xss_protection=True,
    )

    return talisman

# ============================================================================
# INPUT VALIDATION SCHEMAS
# ============================================================================

class OutfitRatingSchema(Schema):
    """Validation schema for outfit rating requests."""
    photo = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=10_000_000),  # ~10MB max
        error_messages={'required': 'Photo data is required'}
    )
    occasion = fields.Str(
        required=True,
        validate=validate.OneOf([
            'casual', 'formal', 'business', 'party', 'wedding',
            'date', 'interview', 'gym', 'beach', 'other'
        ]),
        error_messages={'required': 'Occasion is required'}
    )

class OutfitGenerationSchema(Schema):
    """Validation schema for outfit generation requests."""
    occasion = fields.Str(
        required=True,
        validate=validate.OneOf([
            'casual', 'formal', 'business', 'party', 'wedding',
            'date', 'interview', 'gym', 'beach', 'other'
        ])
    )
    style = fields.Str(
        required=False,
        validate=validate.Length(max=200)
    )
    preferences = fields.Str(
        required=False,
        validate=validate.Length(max=500)
    )

class VirtualTryOnSchema(Schema):
    """Validation schema for virtual try-on requests."""
    personImage = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=10_000_000)
    )
    garmentImage = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=10_000_000)
    )
    category = fields.Str(
        required=True,
        validate=validate.OneOf(['upper_body', 'lower_body', 'dresses'])
    )

class ArenaSubmissionSchema(Schema):
    """Validation schema for Fashion Arena submissions."""
    userId = fields.Str(
        required=True,
        validate=validate.Regexp(r'^[a-zA-Z0-9_-]{1,50}$')
    )
    userName = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=50)
    )
    photo = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=10_000_000)
    )
    occasion = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=100)
    )

class ArenaVoteSchema(Schema):
    """Validation schema for arena voting."""
    userId = fields.Str(
        required=True,
        validate=validate.Regexp(r'^[a-zA-Z0-9_-]{1,50}$')
    )
    userName = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=50)
    )
    outfitId = fields.Str(
        required=True,
        validate=validate.Regexp(r'^[a-zA-Z0-9_-]{1,50}$')
    )

class SquadCreateSchema(Schema):
    """Validation schema for squad creation."""
    name = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=50)
    )
    description = fields.Str(
        required=False,
        validate=validate.Length(max=200)
    )
    userId = fields.Str(
        required=True,
        validate=validate.Regexp(r'^[a-zA-Z0-9_-]{1,50}$')
    )
    userName = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=50)
    )
    maxMembers = fields.Int(
        required=False,
        validate=validate.Range(min=2, max=50)
    )

class SquadJoinSchema(Schema):
    """Validation schema for joining a squad."""
    inviteCode = fields.Str(
        required=True,
        validate=[
            validate.Length(equal=6),
            validate.Regexp(r'^[A-Z0-9]{6}$')
        ]
    )
    userId = fields.Str(
        required=True,
        validate=validate.Regexp(r'^[a-zA-Z0-9_-]{1,50}$')
    )
    userName = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=50)
    )

class SquadOutfitSchema(Schema):
    """Validation schema for sharing outfit to squad."""
    squadId = fields.Str(
        required=True,
        validate=validate.Regexp(r'^[a-zA-Z0-9_-]{1,50}$')
    )
    userId = fields.Str(
        required=True,
        validate=validate.Regexp(r'^[a-zA-Z0-9_-]{1,50}$')
    )
    userName = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=50)
    )
    photo = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=10_000_000)
    )
    occasion = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=100)
    )
    question = fields.Str(
        required=False,
        validate=validate.Length(max=200)
    )

class SquadVoteSchema(Schema):
    """Validation schema for voting on squad outfit."""
    outfitId = fields.Str(
        required=True,
        validate=validate.Regexp(r'^[a-zA-Z0-9_-]{1,50}$')
    )
    userId = fields.Str(
        required=True,
        validate=validate.Regexp(r'^[a-zA-Z0-9_-]{1,50}$')
    )
    userName = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=50)
    )
    voteType = fields.Str(
        required=True,
        validate=validate.OneOf(['thumbs_up', 'thumbs_down', 'fire'])
    )
    comment = fields.Str(
        required=False,
        validate=validate.Length(max=300)
    )

class SquadMessageSchema(Schema):
    """Validation schema for squad chat messages."""
    outfitId = fields.Str(
        required=True,
        validate=validate.Regexp(r'^[a-zA-Z0-9_-]{1,50}$')
    )
    userId = fields.Str(
        required=True,
        validate=validate.Regexp(r'^[a-zA-Z0-9_-]{1,50}$')
    )
    userName = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=50)
    )
    message = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=300)
    )

# ============================================================================
# ADMIN AUTHENTICATION
# ============================================================================

def validate_admin_password(password: str) -> bool:
    """
    Validate admin password against environment variable.

    Args:
        password: Password to validate

    Returns:
        bool: True if password is valid
    """
    admin_password = os.getenv('ADMIN_PASSWORD')

    if not admin_password:
        raise ValueError("ADMIN_PASSWORD environment variable not set")

    # Use constant-time comparison to prevent timing attacks
    import hmac
    return hmac.compare_digest(password, admin_password)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def validate_request_data(schema_class, data):
    """
    Validate request data against a Marshmallow schema.

    Args:
        schema_class: Marshmallow schema class
        data: Data to validate

    Returns:
        Validated data

    Raises:
        ValidationError: If validation fails
    """
    schema = schema_class()
    return schema.load(data)

def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal attacks.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    import re
    # Remove path separators and dangerous characters
    safe_name = re.sub(r'[^\w\s.-]', '', filename)
    safe_name = safe_name.replace('..', '')
    safe_name = safe_name.replace('/', '')
    safe_name = safe_name.replace('\\', '')
    return safe_name[:255]  # Limit length

def validate_image_data(data: str) -> bool:
    """
    Validate that data is a proper base64 image.

    Args:
        data: Base64 image data

    Returns:
        bool: True if valid
    """
    # Check for local file paths
    if any(prefix in data.lower() for prefix in ['file://', 'file:\\', '../', '..\\']):
        return False

    # Check if it's a data URL
    if data.startswith('data:image/'):
        return True

    # Check if it's a valid HTTP(S) URL
    if data.startswith(('http://', 'https://')):
        return True

    return False
