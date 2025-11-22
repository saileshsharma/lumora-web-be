"""
Keycloak Authentication Integration
Handles token validation, user info, and role-based authorization
"""

import os
import logging
from functools import wraps
from flask import request, jsonify
from keycloak import KeycloakOpenID, KeycloakAuthenticationError
import jwt
from jwt.exceptions import DecodeError, ExpiredSignatureError, InvalidTokenError

# Logger
logger = logging.getLogger('auth')

# Keycloak Configuration
KEYCLOAK_SERVER_URL = os.getenv('KEYCLOAK_SERVER_URL', 'http://localhost:8080')
KEYCLOAK_REALM = os.getenv('KEYCLOAK_REALM', 'lumora')
KEYCLOAK_CLIENT_ID = os.getenv('KEYCLOAK_CLIENT_ID', 'lumora-backend')
KEYCLOAK_CLIENT_SECRET = os.getenv('KEYCLOAK_CLIENT_SECRET', '')

# Initialize Keycloak OpenID client
keycloak_openid = None

def init_keycloak():
    """Initialize Keycloak OpenID client"""
    global keycloak_openid

    try:
        keycloak_openid = KeycloakOpenID(
            server_url=KEYCLOAK_SERVER_URL,
            client_id=KEYCLOAK_CLIENT_ID,
            realm_name=KEYCLOAK_REALM,
            client_secret_key=KEYCLOAK_CLIENT_SECRET
        )
        logger.info(f"✓ Keycloak initialized: {KEYCLOAK_SERVER_URL}/realms/{KEYCLOAK_REALM}")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Keycloak: {str(e)}")
        return False

def get_keycloak_public_key():
    """Get Keycloak public key for token validation"""
    try:
        return (
            "-----BEGIN PUBLIC KEY-----\n"
            + keycloak_openid.public_key()
            + "\n-----END PUBLIC KEY-----"
        )
    except Exception as e:
        logger.error(f"Failed to get Keycloak public key: {str(e)}")
        return None

def validate_token(token):
    """
    Validate Keycloak JWT token

    Args:
        token: JWT access token string

    Returns:
        dict: Decoded token payload if valid
        None: If token is invalid
    """
    if not keycloak_openid:
        logger.error("Keycloak not initialized")
        return None

    try:
        # Get Keycloak public key
        public_key = get_keycloak_public_key()
        if not public_key:
            return None

        # Decode and validate token
        options = {
            "verify_signature": True,
            "verify_aud": False,  # Audience verification optional
            "verify_exp": True
        }

        decoded_token = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            options=options
        )

        logger.info(f"Token validated for user: {decoded_token.get('preferred_username')}")
        return decoded_token

    except ExpiredSignatureError:
        logger.warning("Token has expired")
        return None
    except DecodeError:
        logger.warning("Token decode error")
        return None
    except InvalidTokenError as e:
        logger.warning(f"Invalid token: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Token validation error: {str(e)}")
        return None

def get_user_info(token):
    """
    Get user information from Keycloak using access token

    Args:
        token: JWT access token string

    Returns:
        dict: User information
        None: If failed
    """
    if not keycloak_openid:
        logger.error("Keycloak not initialized")
        return None

    try:
        user_info = keycloak_openid.userinfo(token)
        return user_info
    except KeycloakAuthenticationError as e:
        logger.warning(f"Authentication error: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Failed to get user info: {str(e)}")
        return None

def extract_token_from_header():
    """
    Extract Bearer token from Authorization header

    Returns:
        str: Token string or None
    """
    auth_header = request.headers.get('Authorization', '')

    if not auth_header:
        return None

    parts = auth_header.split()

    if len(parts) != 2 or parts[0].lower() != 'bearer':
        return None

    return parts[1]

def get_user_roles(decoded_token):
    """
    Extract user roles from decoded token

    Args:
        decoded_token: Decoded JWT token

    Returns:
        list: List of role names
    """
    roles = []

    # Get realm roles
    realm_access = decoded_token.get('realm_access', {})
    roles.extend(realm_access.get('roles', []))

    # Get client roles (optional)
    resource_access = decoded_token.get('resource_access', {})
    client_access = resource_access.get(KEYCLOAK_CLIENT_ID, {})
    roles.extend(client_access.get('roles', []))

    return roles

def has_role(decoded_token, role_name):
    """
    Check if user has a specific role

    Args:
        decoded_token: Decoded JWT token
        role_name: Role name to check

    Returns:
        bool: True if user has role
    """
    roles = get_user_roles(decoded_token)
    return role_name in roles

# ============================================================================
# DECORATORS
# ============================================================================

def keycloak_required(f):
    """
    Decorator to require valid Keycloak authentication

    Usage:
        @app.route('/protected')
        @keycloak_required
        def protected_route():
            # Access token data via request.keycloak_token
            return jsonify({"message": "Protected resource"})
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Extract token
        token = extract_token_from_header()

        if not token:
            return jsonify({"error": "Missing authorization token"}), 401

        # Validate token
        decoded_token = validate_token(token)

        if not decoded_token:
            return jsonify({"error": "Invalid or expired token"}), 401

        # Attach decoded token to request
        request.keycloak_token = decoded_token

        # Get user info and attach to request
        user_info = get_user_info(token)
        request.keycloak_user = user_info

        return f(*args, **kwargs)

    return decorated_function

def keycloak_optional(f):
    """
    Decorator for optional Keycloak authentication
    Allows both authenticated and unauthenticated access

    Usage:
        @app.route('/optional')
        @keycloak_optional
        def optional_route():
            if hasattr(request, 'keycloak_token'):
                # User is authenticated
                return jsonify({"user": request.keycloak_user})
            else:
                # User is not authenticated
                return jsonify({"message": "Public access"})
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Extract token
        token = extract_token_from_header()

        if token:
            # Validate token
            decoded_token = validate_token(token)

            if decoded_token:
                # Attach decoded token to request
                request.keycloak_token = decoded_token

                # Get user info and attach to request
                user_info = get_user_info(token)
                request.keycloak_user = user_info

        return f(*args, **kwargs)

    return decorated_function

def require_role(role_name):
    """
    Decorator to require a specific role

    Usage:
        @app.route('/admin')
        @keycloak_required
        @require_role('admin')
        def admin_route():
            return jsonify({"message": "Admin access"})

    Args:
        role_name: Required role name
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(request, 'keycloak_token'):
                return jsonify({"error": "Authentication required"}), 401

            if not has_role(request.keycloak_token, role_name):
                return jsonify({"error": f"Requires '{role_name}' role"}), 403

            return f(*args, **kwargs)

        return decorated_function
    return decorator

def require_any_role(*role_names):
    """
    Decorator to require any of the specified roles

    Usage:
        @app.route('/privileged')
        @keycloak_required
        @require_any_role('admin', 'premium')
        def privileged_route():
            return jsonify({"message": "Privileged access"})

    Args:
        *role_names: Variable number of role names
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(request, 'keycloak_token'):
                return jsonify({"error": "Authentication required"}), 401

            user_roles = get_user_roles(request.keycloak_token)
            has_required_role = any(role in user_roles for role in role_names)

            if not has_required_role:
                return jsonify({
                    "error": f"Requires one of: {', '.join(role_names)}"
                }), 403

            return f(*args, **kwargs)

        return decorated_function
    return decorator

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_current_user():
    """
    Get current authenticated user from request

    Returns:
        dict: User info or None
    """
    if hasattr(request, 'keycloak_user'):
        return request.keycloak_user
    return None

def get_current_user_id():
    """
    Get current authenticated user ID from request

    Returns:
        str: User ID or None
    """
    if hasattr(request, 'keycloak_token'):
        return request.keycloak_token.get('sub')
    return None

def get_current_username():
    """
    Get current authenticated username from request

    Returns:
        str: Username or None
    """
    if hasattr(request, 'keycloak_token'):
        return request.keycloak_token.get('preferred_username')
    return None

def is_authenticated():
    """
    Check if current request is authenticated

    Returns:
        bool: True if authenticated
    """
    return hasattr(request, 'keycloak_token')
