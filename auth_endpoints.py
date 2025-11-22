"""
Authentication API Endpoints
Handles /api/auth/* routes for registration, login, token refresh, and logout
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    get_jwt
)
from datetime import timedelta
import logging
from marshmallow import Schema, fields, validate, ValidationError

import auth_system

# Create blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# Logger
logger = logging.getLogger('auth')

# ============================================================================
# VALIDATION SCHEMAS
# ============================================================================

class RegisterSchema(Schema):
    """Validation schema for user registration"""
    email = fields.Email(required=True, error_messages={'required': 'Email is required'})
    password = fields.Str(
        required=True,
        validate=validate.Length(min=6, max=100),
        error_messages={'required': 'Password is required'}
    )
    name = fields.Str(
        required=True,
        validate=validate.Length(min=2, max=50),
        error_messages={'required': 'Name is required'}
    )

class LoginSchema(Schema):
    """Validation schema for user login"""
    email = fields.Email(required=True, error_messages={'required': 'Email is required'})
    password = fields.Str(required=True, error_messages={'required': 'Password is required'})

class UpdateProfileSchema(Schema):
    """Validation schema for profile update"""
    name = fields.Str(validate=validate.Length(min=2, max=50))
    password = fields.Str(validate=validate.Length(min=6, max=100))

# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user account

    Request Body:
        {
            "email": "user@example.com",
            "password": "securePassword123",
            "name": "John Doe"
        }

    Returns:
        201: User created successfully with access and refresh tokens
        400: Validation error or user already exists
        500: Server error
    """
    try:
        data = request.get_json()

        # Validate input
        try:
            schema = RegisterSchema()
            validated_data = schema.load(data)
        except ValidationError as e:
            return jsonify({'error': 'Validation failed', 'details': e.messages}), 400

        # Create user
        try:
            user = auth_system.create_user(
                email=validated_data['email'],
                password=validated_data['password'],
                name=validated_data['name']
            )
        except ValueError as e:
            return jsonify({'error': str(e)}), 400

        # Generate JWT tokens
        access_token = create_access_token(
            identity=user['id'],
            additional_claims={'email': user['email'], 'name': user['name']},
            expires_delta=timedelta(minutes=15)
        )
        refresh_token = create_refresh_token(
            identity=user['id'],
            expires_delta=timedelta(days=7)
        )

        logger.info(f"New user registered: {user['email']}")

        return jsonify({
            'message': 'User registered successfully',
            'user': user,
            'access_token': access_token,
            'refresh_token': refresh_token
        }), 201

    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return jsonify({'error': 'Registration failed', 'message': str(e)}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Login with email and password

    Request Body:
        {
            "email": "user@example.com",
            "password": "securePassword123"
        }

    Returns:
        200: Login successful with access and refresh tokens
        400: Validation error
        401: Invalid credentials
        500: Server error
    """
    try:
        data = request.get_json()

        # Validate input
        try:
            schema = LoginSchema()
            validated_data = schema.load(data)
        except ValidationError as e:
            return jsonify({'error': 'Validation failed', 'details': e.messages}), 400

        # Authenticate user
        user = auth_system.authenticate_user(
            email=validated_data['email'],
            password=validated_data['password']
        )

        if not user:
            logger.warning(f"Failed login attempt for: {validated_data['email']}")
            return jsonify({'error': 'Invalid email or password'}), 401

        # Generate JWT tokens
        access_token = create_access_token(
            identity=user['id'],
            additional_claims={'email': user['email'], 'name': user['name']},
            expires_delta=timedelta(minutes=15)
        )
        refresh_token = create_refresh_token(
            identity=user['id'],
            expires_delta=timedelta(days=7)
        )

        logger.info(f"User logged in: {user['email']}")

        return jsonify({
            'message': 'Login successful',
            'user': user,
            'access_token': access_token,
            'refresh_token': refresh_token
        }), 200

    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({'error': 'Login failed', 'message': str(e)}), 500

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """
    Refresh access token using refresh token

    Headers:
        Authorization: Bearer <refresh_token>

    Returns:
        200: New access token
        401: Invalid or expired refresh token
        500: Server error
    """
    try:
        # Get user ID from refresh token
        user_id = get_jwt_identity()

        # Get user details
        user = auth_system.get_user_by_id(user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Generate new access token
        access_token = create_access_token(
            identity=user['id'],
            additional_claims={'email': user['email'], 'name': user['name']},
            expires_delta=timedelta(minutes=15)
        )

        return jsonify({
            'access_token': access_token
        }), 200

    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        return jsonify({'error': 'Token refresh failed', 'message': str(e)}), 500

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """
    Logout user and blacklist current token

    Headers:
        Authorization: Bearer <access_token>

    Returns:
        200: Logout successful
        401: Invalid token
        500: Server error
    """
    try:
        # Get token JTI (JWT ID) and expiration
        jwt_data = get_jwt()
        jti = jwt_data['jti']
        exp = jwt_data['exp']

        # Add token to blacklist
        from datetime import datetime
        expires_at = datetime.utcfromtimestamp(exp).isoformat()
        auth_system.blacklist_token(jti, expires_at)

        logger.info(f"User logged out: {get_jwt_identity()}")

        return jsonify({'message': 'Logout successful'}), 200

    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        return jsonify({'error': 'Logout failed', 'message': str(e)}), 500

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """
    Get current user information

    Headers:
        Authorization: Bearer <access_token>

    Returns:
        200: User information
        401: Invalid token
        404: User not found
        500: Server error
    """
    try:
        user_id = get_jwt_identity()

        user = auth_system.get_user_by_id(user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        return jsonify({
            'user': user
        }), 200

    except Exception as e:
        logger.error(f"Get user error: {str(e)}")
        return jsonify({'error': 'Failed to get user', 'message': str(e)}), 500

@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """
    Update user profile

    Headers:
        Authorization: Bearer <access_token>

    Request Body:
        {
            "name": "New Name",
            "password": "newPassword123"  // optional
        }

    Returns:
        200: Profile updated successfully
        400: Validation error
        401: Invalid token
        404: User not found
        500: Server error
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json()

        # Validate input
        try:
            schema = UpdateProfileSchema()
            validated_data = schema.load(data)
        except ValidationError as e:
            return jsonify({'error': 'Validation failed', 'details': e.messages}), 400

        # Update user
        try:
            updated_user = auth_system.update_user(user_id, **validated_data)
        except ValueError as e:
            return jsonify({'error': str(e)}), 400

        if not updated_user:
            return jsonify({'error': 'User not found'}), 404

        logger.info(f"Profile updated: {updated_user['email']}")

        return jsonify({
            'message': 'Profile updated successfully',
            'user': updated_user
        }), 200

    except Exception as e:
        logger.error(f"Profile update error: {str(e)}")
        return jsonify({'error': 'Profile update failed', 'message': str(e)}), 500

# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================

@auth_bp.route('/check-email', methods=['POST'])
def check_email():
    """
    Check if email is already registered

    Request Body:
        {
            "email": "user@example.com"
        }

    Returns:
        200: Email availability status
        400: Validation error
    """
    try:
        data = request.get_json()
        email = data.get('email')

        if not email:
            return jsonify({'error': 'Email is required'}), 400

        user = auth_system.get_user_by_email(email)

        return jsonify({
            'available': user is None,
            'message': 'Email available' if user is None else 'Email already registered'
        }), 200

    except Exception as e:
        logger.error(f"Email check error: {str(e)}")
        return jsonify({'error': 'Email check failed', 'message': str(e)}), 500

@auth_bp.route('/stats', methods=['GET'])
def get_stats():
    """
    Get authentication statistics (for debugging)

    Returns:
        200: Statistics
    """
    try:
        return jsonify({
            'total_users': auth_system.get_user_count(),
            'message': 'Authentication system is running'
        }), 200

    except Exception as e:
        logger.error(f"Stats error: {str(e)}")
        return jsonify({'error': 'Failed to get stats', 'message': str(e)}), 500
