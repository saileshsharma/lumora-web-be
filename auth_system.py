"""
Authentication System for AI Outfit Assistant
Handles user registration, login, JWT tokens, and password management
"""

import json
import os
import uuid
from datetime import datetime, timedelta
import bcrypt
from typing import Optional, Dict, Any

# User database file
USERS_DB_FILE = 'users_db.json'
TOKEN_BLACKLIST_FILE = 'token_blacklist.json'

# ============================================================================
# USER DATABASE FUNCTIONS
# ============================================================================

def load_users() -> Dict[str, Any]:
    """Load users from JSON database"""
    if os.path.exists(USERS_DB_FILE):
        try:
            with open(USERS_DB_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {"users": []}
    return {"users": []}

def save_users(users_data: Dict[str, Any]) -> None:
    """Save users to JSON database"""
    with open(USERS_DB_FILE, 'w') as f:
        json.dump(users_data, f, indent=2)

def load_blacklist() -> Dict[str, Any]:
    """Load token blacklist"""
    if os.path.exists(TOKEN_BLACKLIST_FILE):
        try:
            with open(TOKEN_BLACKLIST_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {"tokens": []}
    return {"tokens": []}

def save_blacklist(blacklist_data: Dict[str, Any]) -> None:
    """Save token blacklist"""
    with open(TOKEN_BLACKLIST_FILE, 'w') as f:
        json.dump(blacklist_data, f, indent=2)

# ============================================================================
# PASSWORD HASHING
# ============================================================================

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt

    Args:
        password: Plain text password

    Returns:
        Hashed password as string
    """
    # Generate salt and hash password
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash

    Args:
        password: Plain text password
        hashed_password: Hashed password from database

    Returns:
        True if password matches, False otherwise
    """
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

# ============================================================================
# USER MANAGEMENT
# ============================================================================

def create_user(email: str, password: str, name: str) -> Dict[str, Any]:
    """
    Create a new user account

    Args:
        email: User's email address
        password: Plain text password (will be hashed)
        name: User's display name

    Returns:
        User object

    Raises:
        ValueError: If user already exists or validation fails
    """
    # Load existing users
    users_data = load_users()

    # Check if user already exists
    if any(user['email'].lower() == email.lower() for user in users_data['users']):
        raise ValueError("User with this email already exists")

    # Validate inputs
    if not email or '@' not in email:
        raise ValueError("Invalid email address")

    if not password or len(password) < 6:
        raise ValueError("Password must be at least 6 characters")

    if not name or len(name.strip()) < 2:
        raise ValueError("Name must be at least 2 characters")

    # Create user object
    user = {
        'id': str(uuid.uuid4()),
        'email': email.lower(),
        'password_hash': hash_password(password),
        'name': name.strip(),
        'created_at': datetime.utcnow().isoformat(),
        'updated_at': datetime.utcnow().isoformat(),
        'is_active': True,
        'email_verified': False,  # For future email verification
    }

    # Add to database
    users_data['users'].append(user)
    save_users(users_data)

    # Return user without password hash
    return {
        'id': user['id'],
        'email': user['email'],
        'name': user['name'],
        'created_at': user['created_at'],
    }

def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Authenticate a user with email and password

    Args:
        email: User's email address
        password: Plain text password

    Returns:
        User object if authentication successful, None otherwise
    """
    users_data = load_users()

    # Find user by email
    user = next(
        (u for u in users_data['users'] if u['email'].lower() == email.lower()),
        None
    )

    if not user:
        return None

    # Check if account is active
    if not user.get('is_active', True):
        return None

    # Verify password
    if not verify_password(password, user['password_hash']):
        return None

    # Return user without password hash
    return {
        'id': user['id'],
        'email': user['email'],
        'name': user['name'],
        'created_at': user['created_at'],
    }

def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get user by ID

    Args:
        user_id: User's ID

    Returns:
        User object if found, None otherwise
    """
    users_data = load_users()

    user = next(
        (u for u in users_data['users'] if u['id'] == user_id),
        None
    )

    if not user:
        return None

    # Return user without password hash
    return {
        'id': user['id'],
        'email': user['email'],
        'name': user['name'],
        'created_at': user['created_at'],
    }

def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """
    Get user by email

    Args:
        email: User's email address

    Returns:
        User object if found, None otherwise
    """
    users_data = load_users()

    user = next(
        (u for u in users_data['users'] if u['email'].lower() == email.lower()),
        None
    )

    if not user:
        return None

    # Return user without password hash
    return {
        'id': user['id'],
        'email': user['email'],
        'name': user['name'],
        'created_at': user['created_at'],
    }

def update_user(user_id: str, **kwargs) -> Optional[Dict[str, Any]]:
    """
    Update user information

    Args:
        user_id: User's ID
        **kwargs: Fields to update (name, password, etc.)

    Returns:
        Updated user object if successful, None otherwise
    """
    users_data = load_users()

    user = next(
        (u for u in users_data['users'] if u['id'] == user_id),
        None
    )

    if not user:
        return None

    # Update allowed fields
    if 'name' in kwargs and kwargs['name']:
        user['name'] = kwargs['name'].strip()

    if 'password' in kwargs and kwargs['password']:
        if len(kwargs['password']) < 6:
            raise ValueError("Password must be at least 6 characters")
        user['password_hash'] = hash_password(kwargs['password'])

    if 'email_verified' in kwargs:
        user['email_verified'] = kwargs['email_verified']

    user['updated_at'] = datetime.utcnow().isoformat()

    # Save changes
    save_users(users_data)

    # Return user without password hash
    return {
        'id': user['id'],
        'email': user['email'],
        'name': user['name'],
        'created_at': user['created_at'],
        'updated_at': user['updated_at'],
    }

# ============================================================================
# TOKEN BLACKLIST (for logout)
# ============================================================================

def is_token_blacklisted(jti: str) -> bool:
    """
    Check if a token is blacklisted

    Args:
        jti: JWT ID (jti claim from token)

    Returns:
        True if token is blacklisted, False otherwise
    """
    blacklist = load_blacklist()
    return any(token['jti'] == jti for token in blacklist['tokens'])

def blacklist_token(jti: str, expires_at: str) -> None:
    """
    Add a token to the blacklist

    Args:
        jti: JWT ID (jti claim from token)
        expires_at: Token expiration time (ISO format)
    """
    blacklist = load_blacklist()

    # Add token to blacklist
    blacklist['tokens'].append({
        'jti': jti,
        'blacklisted_at': datetime.utcnow().isoformat(),
        'expires_at': expires_at
    })

    save_blacklist(blacklist)

def cleanup_expired_tokens() -> int:
    """
    Remove expired tokens from blacklist

    Returns:
        Number of tokens removed
    """
    blacklist = load_blacklist()
    now = datetime.utcnow()

    # Filter out expired tokens
    original_count = len(blacklist['tokens'])
    blacklist['tokens'] = [
        token for token in blacklist['tokens']
        if datetime.fromisoformat(token['expires_at']) > now
    ]

    removed_count = original_count - len(blacklist['tokens'])

    if removed_count > 0:
        save_blacklist(blacklist)

    return removed_count

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_user_count() -> int:
    """Get total number of registered users"""
    users_data = load_users()
    return len(users_data['users'])

def search_users(query: str, limit: int = 10) -> list:
    """
    Search users by name or email

    Args:
        query: Search query
        limit: Maximum number of results

    Returns:
        List of matching users
    """
    users_data = load_users()
    query = query.lower()

    matches = [
        {
            'id': user['id'],
            'email': user['email'],
            'name': user['name'],
        }
        for user in users_data['users']
        if query in user['email'].lower() or query in user['name'].lower()
    ]

    return matches[:limit]
