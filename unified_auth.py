"""
Unified Authentication Module
Supports both legacy JWT and Keycloak authentication
"""

import os
import logging
from functools import wraps
from flask import request, jsonify

# Logger
logger = logging.getLogger('auth')

# Check if Keycloak is enabled
USE_KEYCLOAK = os.getenv('USE_KEYCLOAK', 'false').lower() == 'true'

# Import appropriate auth module
if USE_KEYCLOAK:
    try:
        import keycloak_auth
        KEYCLOAK_AVAILABLE = True
    except ImportError:
        KEYCLOAK_AVAILABLE = False
        USE_KEYCLOAK = False
        logger.warning("Keycloak not available, falling back to JWT")

if not USE_KEYCLOAK:
    from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt


def get_current_user():
    """
    Get current user information from token
    Works with both JWT and Keycloak
    """
    if USE_KEYCLOAK and KEYCLOAK_AVAILABLE:
        return keycloak_auth.get_current_user()
    else:
        try:
            verify_jwt_in_request(optional=True)
            user_id = get_jwt_identity()
            if user_id:
                claims = get_jwt()
                return {
                    'user_id': user_id,
                    'email': claims.get('email'),
                    'roles': claims.get('roles', [])
                }
            return None
        except:
            return None


def auth_required(optional=False):
    """
    Decorator for routes that require authentication
    Works with both JWT and Keycloak

    Args:
        optional: If True, authentication is optional (allows anonymous access)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if USE_KEYCLOAK and KEYCLOAK_AVAILABLE:
                # Use Keycloak authentication
                if optional:
                    # For optional auth, just continue
                    return f(*args, **kwargs)
                else:
                    # For required auth, use Keycloak decorator
                    return keycloak_auth.keycloak_required(f)(*args, **kwargs)
            else:
                # Use legacy JWT authentication
                try:
                    verify_jwt_in_request(optional=optional)
                    return f(*args, **kwargs)
                except Exception as e:
                    if not optional:
                        return jsonify({"error": "Authentication required"}), 401
                    return f(*args, **kwargs)

        return decorated_function
    return decorator


def require_role(role):
    """
    Decorator for routes that require specific role
    Works with both JWT and Keycloak
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if USE_KEYCLOAK and KEYCLOAK_AVAILABLE:
                # Use Keycloak role check
                return keycloak_auth.require_role(role)(f)(*args, **kwargs)
            else:
                # Use JWT role check
                try:
                    verify_jwt_in_request()
                    claims = get_jwt()
                    user_roles = claims.get('roles', [])

                    if role not in user_roles:
                        return jsonify({"error": f"Role '{role}' required"}), 403

                    return f(*args, **kwargs)
                except Exception as e:
                    return jsonify({"error": "Authentication required"}), 401

        return decorated_function
    return decorator


def require_any_role(*roles):
    """
    Decorator for routes that require any of the specified roles
    Works with both JWT and Keycloak
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if USE_KEYCLOAK and KEYCLOAK_AVAILABLE:
                # Use Keycloak role check
                return keycloak_auth.require_any_role(*roles)(f)(*args, **kwargs)
            else:
                # Use JWT role check
                try:
                    verify_jwt_in_request()
                    claims = get_jwt()
                    user_roles = claims.get('roles', [])

                    if not any(role in user_roles for role in roles):
                        return jsonify({"error": f"One of these roles required: {', '.join(roles)}"}), 403

                    return f(*args, **kwargs)
                except Exception as e:
                    return jsonify({"error": "Authentication required"}), 401

        return decorated_function
    return decorator


# Backward compatibility aliases
keycloak_required = auth_required(optional=False)
optional_auth = auth_required(optional=True)
