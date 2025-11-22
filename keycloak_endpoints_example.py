"""
Example Keycloak-Protected Endpoints
Demonstrates how to use Keycloak authentication decorators
"""

from flask import Blueprint, jsonify, request
from keycloak_auth import (
    keycloak_required,
    keycloak_optional,
    require_role,
    require_any_role,
    get_current_user,
    get_current_user_id,
    get_current_username,
    is_authenticated,
    get_user_roles
)

# Create blueprint
keycloak_example_bp = Blueprint('keycloak_examples', __name__, url_prefix='/api/examples')

# ============================================================================
# EXAMPLE 1: Public Endpoint (No Authentication)
# ============================================================================

@keycloak_example_bp.route('/public', methods=['GET'])
def public_endpoint():
    """
    Public endpoint - No authentication required
    Anyone can access this endpoint
    """
    return jsonify({
        "message": "This is a public endpoint",
        "authenticated": False
    }), 200

# ============================================================================
# EXAMPLE 2: Optional Authentication
# ============================================================================

@keycloak_example_bp.route('/optional', methods=['GET'])
@keycloak_optional
def optional_auth_endpoint():
    """
    Optional authentication endpoint
    Works with or without authentication
    Provides different responses based on auth status
    """
    if is_authenticated():
        user = get_current_user()
        return jsonify({
            "message": "Welcome back, authenticated user!",
            "authenticated": True,
            "user": {
                "id": get_current_user_id(),
                "username": get_current_username(),
                "email": user.get('email'),
                "name": user.get('name')
            },
            "roles": get_user_roles(request.keycloak_token)
        }), 200
    else:
        return jsonify({
            "message": "Welcome, guest user!",
            "authenticated": False,
            "hint": "Login to access personalized features"
        }), 200

# ============================================================================
# EXAMPLE 3: Required Authentication
# ============================================================================

@keycloak_example_bp.route('/protected', methods=['GET'])
@keycloak_required
def protected_endpoint():
    """
    Protected endpoint - Requires authentication
    Returns 401 if not authenticated
    """
    user = get_current_user()

    return jsonify({
        "message": "Access granted to protected resource",
        "user": {
            "id": get_current_user_id(),
            "username": get_current_username(),
            "email": user.get('email'),
            "name": user.get('name'),
            "email_verified": user.get('email_verified'),
        },
        "token_info": {
            "issued_at": request.keycloak_token.get('iat'),
            "expires_at": request.keycloak_token.get('exp'),
            "issuer": request.keycloak_token.get('iss')
        }
    }), 200

# ============================================================================
# EXAMPLE 4: Role-Based Access - Admin Only
# ============================================================================

@keycloak_example_bp.route('/admin', methods=['GET'])
@keycloak_required
@require_role('admin')
def admin_only_endpoint():
    """
    Admin-only endpoint
    Requires 'admin' role
    Returns 403 if user doesn't have admin role
    """
    return jsonify({
        "message": "Admin access granted",
        "user": get_current_username(),
        "roles": get_user_roles(request.keycloak_token),
        "admin_features": [
            "User management",
            "System settings",
            "Analytics dashboard",
            "Content moderation"
        ]
    }), 200

# ============================================================================
# EXAMPLE 5: Role-Based Access - Premium Only
# ============================================================================

@keycloak_example_bp.route('/premium', methods=['GET'])
@keycloak_required
@require_role('premium')
def premium_only_endpoint():
    """
    Premium-only endpoint
    Requires 'premium' role
    Returns 403 if user doesn't have premium role
    """
    return jsonify({
        "message": "Premium access granted",
        "user": get_current_username(),
        "roles": get_user_roles(request.keycloak_token),
        "premium_features": [
            "Advanced AI analysis",
            "Unlimited outfit generation",
            "Priority support",
            "Ad-free experience"
        ]
    }), 200

# ============================================================================
# EXAMPLE 6: Multiple Roles Allowed
# ============================================================================

@keycloak_example_bp.route('/privileged', methods=['GET'])
@keycloak_required
@require_any_role('admin', 'premium')
def privileged_endpoint():
    """
    Privileged endpoint
    Requires either 'admin' OR 'premium' role
    Returns 403 if user has neither role
    """
    user_roles = get_user_roles(request.keycloak_token)
    is_admin = 'admin' in user_roles
    is_premium = 'premium' in user_roles

    return jsonify({
        "message": "Privileged access granted",
        "user": get_current_username(),
        "access_level": "admin" if is_admin else "premium",
        "roles": user_roles,
        "features": {
            "advanced_analytics": True,
            "priority_support": True,
            "beta_features": is_admin
        }
    }), 200

# ============================================================================
# EXAMPLE 7: User Profile Endpoint
# ============================================================================

@keycloak_example_bp.route('/profile', methods=['GET'])
@keycloak_required
def get_user_profile():
    """
    Get current user's profile
    Requires authentication
    """
    user = get_current_user()
    token = request.keycloak_token

    return jsonify({
        "profile": {
            "id": get_current_user_id(),
            "username": get_current_username(),
            "email": user.get('email'),
            "email_verified": user.get('email_verified'),
            "name": user.get('name'),
            "given_name": user.get('given_name'),
            "family_name": user.get('family_name'),
        },
        "roles": get_user_roles(token),
        "account_type": "premium" if 'premium' in get_user_roles(token) else "free",
        "is_admin": 'admin' in get_user_roles(token)
    }), 200

# ============================================================================
# EXAMPLE 8: POST Request with Authentication
# ============================================================================

@keycloak_example_bp.route('/create-outfit', methods=['POST'])
@keycloak_required
def create_outfit():
    """
    Create outfit with user association
    Requires authentication
    Associates outfit with authenticated user
    """
    data = request.get_json()
    user_id = get_current_user_id()
    username = get_current_username()

    # Example: Create outfit and associate with user
    outfit = {
        "id": "outfit-123",
        "name": data.get('name', 'Untitled Outfit'),
        "description": data.get('description'),
        "occasion": data.get('occasion'),
        "created_by": {
            "user_id": user_id,
            "username": username
        },
        "created_at": "2025-01-15T10:30:00Z"
    }

    return jsonify({
        "message": "Outfit created successfully",
        "outfit": outfit
    }), 201

# ============================================================================
# EXAMPLE 9: Admin Action - Delete Resource
# ============================================================================

@keycloak_example_bp.route('/delete-user/<user_id>', methods=['DELETE'])
@keycloak_required
@require_role('admin')
def delete_user(user_id):
    """
    Delete user (admin only)
    Requires 'admin' role
    """
    admin_username = get_current_username()

    # Example: Delete user logic
    return jsonify({
        "message": f"User {user_id} deleted successfully",
        "deleted_by": admin_username,
        "action": "user_deletion",
        "timestamp": "2025-01-15T10:30:00Z"
    }), 200

# ============================================================================
# EXAMPLE 10: Check User Permissions
# ============================================================================

@keycloak_example_bp.route('/permissions', methods=['GET'])
@keycloak_required
def get_user_permissions():
    """
    Get current user's permissions
    Returns what actions the user can perform
    """
    roles = get_user_roles(request.keycloak_token)

    permissions = {
        "can_create_outfit": True,  # All authenticated users
        "can_rate_outfit": True,  # All authenticated users
        "can_use_arena": True,  # All authenticated users
        "can_join_squad": True,  # All authenticated users
        "can_delete_own_content": True,  # All authenticated users
        "can_access_premium_features": 'premium' in roles or 'admin' in roles,
        "can_moderate_content": 'admin' in roles,
        "can_manage_users": 'admin' in roles,
        "can_view_analytics": 'admin' in roles,
        "can_configure_system": 'admin' in roles,
    }

    return jsonify({
        "user": get_current_username(),
        "roles": roles,
        "permissions": permissions
    }), 200

# ============================================================================
# EXAMPLE 11: Rate Limiting with Authentication
# ============================================================================

@keycloak_example_bp.route('/limited', methods=['GET'])
@keycloak_optional
def rate_limited_endpoint():
    """
    Rate-limited endpoint
    Different limits for authenticated vs unauthenticated users
    """
    if is_authenticated():
        # Authenticated users get higher limits
        limit = 100
        message = "Authenticated users: 100 requests per hour"
    else:
        # Anonymous users get lower limits
        limit = 10
        message = "Anonymous users: 10 requests per hour"

    return jsonify({
        "message": message,
        "rate_limit": limit,
        "authenticated": is_authenticated(),
        "user": get_current_username() if is_authenticated() else "anonymous"
    }), 200

# ============================================================================
# EXAMPLE 12: User Activity Logging
# ============================================================================

@keycloak_example_bp.route('/log-activity', methods=['POST'])
@keycloak_required
def log_activity():
    """
    Log user activity
    Associates actions with authenticated user
    """
    data = request.get_json()
    user_id = get_current_user_id()
    username = get_current_username()

    activity_log = {
        "user_id": user_id,
        "username": username,
        "action": data.get('action'),
        "resource": data.get('resource'),
        "timestamp": "2025-01-15T10:30:00Z",
        "ip_address": request.remote_addr,
        "user_agent": request.headers.get('User-Agent')
    }

    # Example: Save to database
    return jsonify({
        "message": "Activity logged successfully",
        "log": activity_log
    }), 201
