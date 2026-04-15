"""
Authentication Routes
=====================
Handles user registration, login, logout, and token refresh.
"""

import hashlib
import logging
import os
import re
import secrets
from datetime import datetime, timedelta, timezone

from flask import Blueprint, current_app, g, jsonify, request

from app import limiter
from app.utils.auth import log_request
from app.utils.database import (
    consume_password_reset_token,
    create_user,
    db_manager,
    get_refresh_token,
    get_user_by_email,
    get_user_by_public_id,
    invalidate_user_password_reset_tokens,
    revoke_all_user_tokens,
    revoke_refresh_token,
    store_password_reset_token,
    store_refresh_token,
    update_user_last_login,
    update_user_password,
)
from app.utils.jwt_auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_token_hash,
    hash_password,
    require_jwt,
    verify_password,
)

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)


# ──────────────────────────────────────────────────────────────────────────────
# Helper Functions
# ──────────────────────────────────────────────────────────────────────────────

def _validate_email(email):
    """Basic email format validation."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def _validate_password(password):
    """Validate password meets minimum requirements."""
    min_length = current_app.config.get('PASSWORD_MIN_LENGTH', 8)
    return len(password) >= min_length


def _user_to_response(user):
    """Convert user dict to safe response (no password hash)."""
    return {
        'public_id': user.get('public_id'),
        'email': user.get('email'),
        'display_name': user.get('display_name'),
        'is_premium': user.get('is_premium', False),
    }


def _get_client_ip():
    """Get client IP address, handling proxies."""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/auth/register
# ──────────────────────────────────────────────────────────────────────────────

@auth_bp.route('/auth/register', methods=['POST'])
@limiter.limit("5/hour")
@log_request
def register():
    """
    Register a new user account.

    Request body:
        {
            "email": "user@example.com",
            "password": "securepassword",
            "display_name": "John Doe"  (optional)
        }

    Returns:
        201: User created with tokens
        400: Invalid input
        409: Email already exists
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body required'}), 400

    email = data.get('email', '').strip()
    password = data.get('password', '')
    display_name = data.get('display_name', '').strip() or None

    # Validate email
    if not email or not _validate_email(email):
        return jsonify({'error': 'Valid email address required'}), 400

    # Validate password
    if not _validate_password(password):
        min_len = current_app.config.get('PASSWORD_MIN_LENGTH', 8)
        return jsonify({'error': f'Password must be at least {min_len} characters'}), 400

    # Check if email already exists
    existing = get_user_by_email(email)
    if existing:
        return jsonify({'error': 'Email already registered'}), 409

    # Hash password and create user
    password_hash = hash_password(password)
    user = create_user(email, password_hash, display_name)

    if not user:
        return jsonify({'error': 'Failed to create account'}), 500

    # Generate tokens
    access_token = create_access_token(user['public_id'], user['email'])
    refresh_token, token_hash = create_refresh_token(user['public_id'])

    # Store refresh token
    expires_seconds = current_app.config.get('JWT_REFRESH_EXPIRES', 604800)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_seconds)
    store_refresh_token(
        user['id'],
        token_hash,
        expires_at,
        device_info=request.headers.get('User-Agent'),
        ip_address=_get_client_ip()
    )

    logger.info(f"New user registered: {user['email']}")

    # Seed default notification preferences
    try:
        from app.routes.notifications import _seed_default_preferences, DEFAULT_EVENT_TYPES
        from app.utils.database import db_manager
        _seed_default_preferences(user['id'], db_manager)
    except Exception as e:
        logger.debug(f"Failed to seed notification prefs: {e}")

    return jsonify({
        'user': _user_to_response(user),
        'access_token': access_token,
        'refresh_token': refresh_token,
        'token_type': 'Bearer',
        'expires_in': current_app.config.get('JWT_ACCESS_EXPIRES', 900),
    }), 201


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/auth/login
# ──────────────────────────────────────────────────────────────────────────────

@auth_bp.route('/auth/login', methods=['POST'])
@limiter.limit("10/minute")
@log_request
def login():
    """
    Authenticate user and return tokens.

    Request body:
        {
            "email": "user@example.com",
            "password": "securepassword"
        }

    Returns:
        200: Login successful with tokens
        400: Invalid input
        401: Invalid credentials
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body required'}), 400

    email = data.get('email', '').strip()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400

    # Get user by email
    user = get_user_by_email(email)

    if not user:
        # Use same error for security (don't reveal if email exists)
        return jsonify({'error': 'Invalid email or password'}), 401

    # Verify password
    if not verify_password(password, user['password_hash']):
        return jsonify({'error': 'Invalid email or password'}), 401

    # Generate tokens
    access_token = create_access_token(user['public_id'], user['email'])
    refresh_token, token_hash = create_refresh_token(user['public_id'])

    # Store refresh token
    expires_seconds = current_app.config.get('JWT_REFRESH_EXPIRES', 604800)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_seconds)
    store_refresh_token(
        user['id'],
        token_hash,
        expires_at,
        device_info=request.headers.get('User-Agent'),
        ip_address=_get_client_ip()
    )

    # Update last login
    update_user_last_login(user['id'])

    logger.info(f"User logged in: {user['email']}")

    return jsonify({
        'user': _user_to_response(user),
        'access_token': access_token,
        'refresh_token': refresh_token,
        'token_type': 'Bearer',
        'expires_in': current_app.config.get('JWT_ACCESS_EXPIRES', 900),
    })


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/auth/refresh
# ──────────────────────────────────────────────────────────────────────────────

@auth_bp.route('/auth/refresh', methods=['POST'])
@log_request
def refresh():
    """
    Refresh access token using refresh token.

    Request body:
        {
            "refresh_token": "eyJ..."
        }

    Returns:
        200: New access token
        401: Invalid or expired refresh token
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body required'}), 400

    refresh_token = data.get('refresh_token', '')

    if not refresh_token:
        return jsonify({'error': 'Refresh token required'}), 400

    # Decode and validate refresh token
    payload = decode_token(refresh_token)

    if not payload or payload.get('type') != 'refresh':
        return jsonify({'error': 'Invalid refresh token'}), 401

    # Check if token exists in database and not revoked
    token_hash = get_token_hash(refresh_token)
    token_record = get_refresh_token(token_hash)

    if not token_record:
        return jsonify({'error': 'Refresh token not found or expired'}), 401

    # Generate new access token
    access_token = create_access_token(token_record['public_id'], token_record['email'])

    return jsonify({
        'access_token': access_token,
        'token_type': 'Bearer',
        'expires_in': current_app.config.get('JWT_ACCESS_EXPIRES', 900),
    })


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/auth/logout
# ──────────────────────────────────────────────────────────────────────────────

@auth_bp.route('/auth/logout', methods=['POST'])
@log_request
@require_jwt
def logout():
    """
    Logout user by revoking refresh token.

    Request body:
        {
            "refresh_token": "eyJ..."
        }

    Returns:
        200: Logout successful
        400: Missing refresh token
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body required'}), 400

    refresh_token = data.get('refresh_token', '')

    if refresh_token:
        token_hash = get_token_hash(refresh_token)
        revoke_refresh_token(token_hash)

    logger.info(f"User logged out: {g.user_email}")

    return jsonify({'message': 'Logged out successfully'})


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/auth/me
# ──────────────────────────────────────────────────────────────────────────────

# ──────────────────────────────────────────────────────────────────────────────
# POST /api/auth/forgot-password
# ──────────────────────────────────────────────────────────────────────────────

PASSWORD_RESET_TTL_SECONDS = 3600  # 1 hour
FRONTEND_BASE_URL = os.getenv('FRONTEND_BASE_URL', 'https://alphabreak.vip')


def _hash_reset_token(raw_token):
    return hashlib.sha256(raw_token.encode('utf-8')).hexdigest()


def _send_password_reset_email(user_email, user_name, reset_url):
    """
    Dispatch a password reset email. Bypasses per-user notification preferences
    because this is security-critical. Falls back to logging in SES sandbox mode.
    """
    subject = '[AlphaBreak] Reset your password'
    display = user_name or user_email
    text_body = (
        f"Hi {display},\n\n"
        f"Someone requested a password reset for your AlphaBreak account. "
        f"Click the link below to choose a new password. This link expires in 1 hour.\n\n"
        f"{reset_url}\n\n"
        f"If you did not request this, you can safely ignore this email — your password will not change.\n\n"
        f"— AlphaBreak"
    )
    html_body = f"""
    <div style="background:#1a1a2e;padding:20px;font-family:Arial,sans-serif;">
      <div style="max-width:600px;margin:0 auto;background:#16213e;border-radius:8px;overflow:hidden;">
        <div style="background:#0f3460;padding:15px 20px;">
          <h1 style="color:#00d4aa;margin:0;font-size:20px;">AlphaBreak</h1>
        </div>
        <div style="padding:24px;color:#e0e0e0;line-height:1.6;">
          <h2 style="color:#fff;margin-top:0;">Reset your password</h2>
          <p>Hi {display}, someone requested a password reset for your AlphaBreak account.</p>
          <p style="margin:24px 0;">
            <a href="{reset_url}" style="background:#00d4aa;color:#0f3460;padding:12px 24px;
               border-radius:6px;text-decoration:none;font-weight:bold;">Choose a new password</a>
          </p>
          <p style="color:#888;font-size:13px;">This link expires in 1 hour. If you did not request
             this, you can ignore the email — your password will not change.</p>
          <hr style="border-color:#2a2a4a;margin:20px 0;">
          <p style="font-size:12px;color:#888;">
            If the button doesn't work, paste this URL into your browser:<br>
            <span style="color:#4fc3f7;">{reset_url}</span>
          </p>
        </div>
      </div>
    </div>
    """

    from app.services.notification_service import SES_SANDBOX_MODE, SES_FROM_EMAIL, SES_REGION
    if SES_SANDBOX_MODE:
        logger.info(f"[SES sandbox] password reset link for {user_email}: {reset_url}")
        return True
    try:
        import boto3
        client = boto3.client('ses', region_name=SES_REGION)
        client.send_email(
            Source=SES_FROM_EMAIL,
            Destination={'ToAddresses': [user_email]},
            Message={
                'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                'Body': {
                    'Html': {'Data': html_body, 'Charset': 'UTF-8'},
                    'Text': {'Data': text_body, 'Charset': 'UTF-8'},
                },
            },
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send password reset email to {user_email}: {e}")
        return False


@auth_bp.route('/auth/forgot-password', methods=['POST'])
@limiter.limit("5/hour")
@log_request
def forgot_password():
    """
    Start a password reset. Always returns 200 with a generic message to avoid
    leaking whether an email is registered.
    """
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()

    generic = jsonify({
        'message': 'If an account exists for that email, a reset link has been sent.'
    })

    if not email or not _validate_email(email):
        return generic, 200

    user = get_user_by_email(email)
    if not user:
        return generic, 200

    # Invalidate any outstanding tokens, then issue a fresh one
    invalidate_user_password_reset_tokens(user['id'])

    raw_token = secrets.token_urlsafe(32)
    token_hash = _hash_reset_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=PASSWORD_RESET_TTL_SECONDS)

    try:
        store_password_reset_token(
            user['id'], token_hash, expires_at, ip_address=_get_client_ip()
        )
    except Exception as e:
        logger.error(f"Failed to issue password reset: {e}")
        return generic, 200  # still don't leak

    reset_url = f"{FRONTEND_BASE_URL}/#reset-password?token={raw_token}"
    _send_password_reset_email(user['email'], user.get('display_name'), reset_url)

    logger.info(f"Password reset requested for user_id={user['id']}")
    return generic, 200


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/auth/reset-password
# ──────────────────────────────────────────────────────────────────────────────

@auth_bp.route('/auth/reset-password', methods=['POST'])
@limiter.limit("10/hour")
@log_request
def reset_password():
    """
    Complete a password reset using the token from the email link.
    Consumes the token atomically, updates the password, and revokes all
    existing refresh tokens so the user must log in again everywhere.
    """
    data = request.get_json(silent=True) or {}
    raw_token = (data.get('token') or '').strip()
    new_password = data.get('password') or ''

    if not raw_token:
        return jsonify({'error': 'Reset token required'}), 400
    if not _validate_password(new_password):
        min_len = current_app.config.get('PASSWORD_MIN_LENGTH', 8)
        return jsonify({'error': f'Password must be at least {min_len} characters'}), 400

    user = consume_password_reset_token(_hash_reset_token(raw_token))
    if not user:
        return jsonify({'error': 'Invalid or expired reset link'}), 400

    new_hash = hash_password(new_password)
    if not update_user_password(user['id'], new_hash):
        return jsonify({'error': 'Failed to update password'}), 500

    # Security: force re-login on all devices
    revoke_all_user_tokens(user['id'])

    logger.info(f"Password reset completed for user_id={user['id']}")
    return jsonify({'message': 'Password updated. Please log in with your new password.'})


@auth_bp.route('/auth/me', methods=['GET'])
@log_request
@require_jwt
def get_current_user():
    """
    Get current authenticated user's profile.

    Returns:
        200: User profile
        401: Not authenticated
    """
    user = get_user_by_public_id(g.user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({
        'user': _user_to_response(user),
    })
