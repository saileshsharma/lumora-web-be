"""
Authentication Utilities
Helper functions for extracting user info from tokens
"""

import logging
from flask import request
from typing import Optional, Dict
import jwt

logger = logging.getLogger(__name__)


def get_user_from_token() -> Optional[Dict[str, str]]:
    """
    Extract user information from Keycloak JWT token

    Returns:
        Dict with user_id, username, email or None if not authenticated
    """
    try:
        # Get Authorization header
        auth_header = request.headers.get('Authorization')

        if not auth_header or not auth_header.startswith('Bearer '):
            logger.debug("No valid Authorization header found")
            return None

        # Extract token
        token = auth_header.replace('Bearer ', '')

        # Decode token without verification (Keycloak already verified it)
        # We're just extracting the claims
        decoded = jwt.decode(token, options={"verify_signature": False})

        user_info = {
            'user_id': decoded.get('sub', ''),  # 'sub' is the user ID
            'username': decoded.get('preferred_username', ''),
            'email': decoded.get('email', '')
        }

        logger.debug(f"Extracted user info: {user_info.get('username')} ({user_info.get('user_id')})")
        return user_info

    except jwt.DecodeError as e:
        logger.error(f"Failed to decode JWT token: {e}")
        return None
    except Exception as e:
        logger.error(f"Error extracting user from token: {e}")
        return None
