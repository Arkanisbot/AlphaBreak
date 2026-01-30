"""
JWT Authentication Utilities
============================
Handles JWT token generation, verification, and password hashing for user authentication.
"""

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from functools import wraps

import bcrypt
import jwt
from flask import current_app, g, jsonify, request

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Password Hashing
# ──────────────────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt with configurable rounds.

    Args:
        password: Plain text password

    Returns:
        Bcrypt hash string
    """
    rounds = current_app.config.get('BCRYPT_ROUNDS', 12)
    salt = bcrypt.gensalt(rounds=rounds)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        password: Plain text password to verify
        password_hash: Stored bcrypt hash

    Returns:
        True if password matches, False otherwise
    """
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except Exception as e:
        logger.warning(f"Password verification error: {e}")
        return False


# ──────────────────────────────────────────────────────────────────────────────
# JWT Token Generation
# ──────────────────────────────────────────────────────────────────────────────

def create_access_token(user_id: str, email: str) -> str:
    """
    Create a short-lived JWT access token.

    Args:
        user_id: User's public UUID
        email: User's email address

    Returns:
        JWT access token string
    """
    expires_seconds = current_app.config.get('JWT_ACCESS_EXPIRES', 900)  # 15 min default
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_seconds)

    payload = {
        'sub': user_id,
        'email': email,
        'type': 'access',
        'exp': expires_at,
        'iat': datetime.now(timezone.utc),
    }

    secret = current_app.config.get('JWT_SECRET_KEY')
    algorithm = current_app.config.get('JWT_ALGORITHM', 'HS256')

    return jwt.encode(payload, secret, algorithm=algorithm)


def create_refresh_token(user_id: str) -> tuple[str, str]:
    """
    Create a long-lived refresh token.

    Args:
        user_id: User's public UUID

    Returns:
        Tuple of (token_string, token_hash_for_db)
    """
    expires_seconds = current_app.config.get('JWT_REFRESH_EXPIRES', 604800)  # 7 days default
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_seconds)

    # Include random jti (JWT ID) for uniqueness
    jti = secrets.token_hex(16)

    payload = {
        'sub': user_id,
        'type': 'refresh',
        'jti': jti,
        'exp': expires_at,
        'iat': datetime.now(timezone.utc),
    }

    secret = current_app.config.get('JWT_SECRET_KEY')
    algorithm = current_app.config.get('JWT_ALGORITHM', 'HS256')

    token = jwt.encode(payload, secret, algorithm=algorithm)

    # Hash the token for storage in DB (for revocation checking)
    token_hash = hashlib.sha256(token.encode('utf-8')).hexdigest()

    return token, token_hash


def decode_token(token: str) -> dict | None:
    """
    Decode and verify a JWT token.

    Args:
        token: JWT token string

    Returns:
        Decoded payload dict, or None if invalid/expired
    """
    try:
        secret = current_app.config.get('JWT_SECRET_KEY')
        algorithm = current_app.config.get('JWT_ALGORITHM', 'HS256')

        payload = jwt.decode(token, secret, algorithms=[algorithm])
        return payload
    except jwt.ExpiredSignatureError:
        logger.debug("Token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.debug(f"Invalid token: {e}")
        return None


def get_token_hash(token: str) -> str:
    """
    Get SHA-256 hash of a token for database storage/lookup.

    Args:
        token: JWT token string

    Returns:
        SHA-256 hash hex string
    """
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


# ──────────────────────────────────────────────────────────────────────────────
# Authentication Decorators
# ──────────────────────────────────────────────────────────────────────────────

def require_jwt(f):
    """
    Decorator that requires a valid JWT access token.

    Sets g.user_id and g.user_email on success.
    Returns 401 on missing/invalid token.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = _extract_bearer_token()

        if not token:
            return jsonify({'error': 'Missing authorization token'}), 401

        payload = decode_token(token)

        if not payload:
            return jsonify({'error': 'Invalid or expired token'}), 401

        if payload.get('type') != 'access':
            return jsonify({'error': 'Invalid token type'}), 401

        # Set user info in Flask's g object
        g.user_id = payload.get('sub')
        g.user_email = payload.get('email')
        g.auth_type = 'jwt'

        return f(*args, **kwargs)

    return decorated


def require_auth(allow_anonymous=False):
    """
    Decorator that accepts either JWT token OR API key authentication.

    This maintains backward compatibility with existing API key auth
    while also supporting the new JWT-based user auth.

    Args:
        allow_anonymous: If True, allow unauthenticated requests

    Priority:
        1. JWT Bearer token in Authorization header
        2. API key in X-API-Key header or api_key query param
        3. Anonymous (if allow_anonymous=True)
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            # Try JWT auth first
            token = _extract_bearer_token()
            if token:
                payload = decode_token(token)
                if payload and payload.get('type') == 'access':
                    g.user_id = payload.get('sub')
                    g.user_email = payload.get('email')
                    g.auth_type = 'jwt'
                    return f(*args, **kwargs)

            # Try API key auth
            api_key = _extract_api_key()
            if api_key:
                valid_keys = current_app.config.get('API_KEYS', [])
                if api_key in valid_keys:
                    g.api_key_id = hashlib.sha256(api_key.encode()).hexdigest()[:8]
                    g.auth_type = 'api_key'
                    g.user_id = None
                    g.user_email = None
                    return f(*args, **kwargs)

            # Allow anonymous if configured
            if allow_anonymous:
                g.user_id = None
                g.user_email = None
                g.auth_type = 'anonymous'
                return f(*args, **kwargs)

            # No valid auth found
            return jsonify({'error': 'Authentication required'}), 401

        return decorated
    return decorator


# ──────────────────────────────────────────────────────────────────────────────
# Helper Functions
# ──────────────────────────────────────────────────────────────────────────────

def _extract_bearer_token() -> str | None:
    """
    Extract Bearer token from Authorization header.

    Returns:
        Token string, or None if not present/invalid format
    """
    auth_header = request.headers.get('Authorization', '')

    if auth_header.startswith('Bearer '):
        return auth_header[7:]

    return None


def _extract_api_key() -> str | None:
    """
    Extract API key from header or query param.

    Returns:
        API key string, or None if not present
    """
    # Check header first
    api_key = request.headers.get('X-API-Key')

    # Fall back to query param
    if not api_key:
        api_key = request.args.get('api_key')

    return api_key


def get_current_user_id() -> str | None:
    """
    Get the current authenticated user's ID from Flask's g object.

    Returns:
        User's public UUID, or None if not authenticated via JWT
    """
    return getattr(g, 'user_id', None)


def is_authenticated() -> bool:
    """
    Check if the current request is authenticated via JWT.

    Returns:
        True if user is authenticated via JWT, False otherwise
    """
    return getattr(g, 'auth_type', None) == 'jwt' and getattr(g, 'user_id', None) is not None
