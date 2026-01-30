"""
User Routes
===========
Handles user-specific data like watchlists.
"""

import logging

from flask import Blueprint, g, jsonify, request

from app.utils.auth import log_request
from app.utils.database import (
    add_to_user_watchlist,
    get_user_by_public_id,
    get_user_watchlist,
    merge_watchlist,
    remove_from_user_watchlist,
)
from app.utils.jwt_auth import require_jwt

logger = logging.getLogger(__name__)

user_bp = Blueprint('user', __name__)


def _get_user_internal_id():
    """Get the internal user ID from public_id in g.user_id."""
    user = get_user_by_public_id(g.user_id)
    return user['id'] if user else None


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/user/watchlist
# ──────────────────────────────────────────────────────────────────────────────

@user_bp.route('/user/watchlist', methods=['GET'])
@log_request
@require_jwt
def get_watchlist():
    """
    Get the authenticated user's watchlist.

    Returns:
        200: List of tickers in watchlist
        401: Not authenticated
    """
    user_id = _get_user_internal_id()

    if not user_id:
        return jsonify({'error': 'User not found'}), 404

    watchlist = get_user_watchlist(user_id)
    tickers = [item['ticker'] for item in watchlist]

    return jsonify({
        'tickers': tickers,
        'items': watchlist,
        'count': len(watchlist),
    })


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/user/watchlist
# ──────────────────────────────────────────────────────────────────────────────

@user_bp.route('/user/watchlist', methods=['POST'])
@log_request
@require_jwt
def add_to_watchlist():
    """
    Add ticker(s) to the user's watchlist.

    Request body:
        {
            "ticker": "AAPL"  (single ticker)
        }
        OR
        {
            "tickers": ["AAPL", "GOOGL", "MSFT"]  (multiple tickers)
        }

    Returns:
        200: Ticker(s) added
        400: Invalid input
    """
    user_id = _get_user_internal_id()

    if not user_id:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body required'}), 400

    # Handle single ticker
    ticker = data.get('ticker')
    if ticker:
        ticker = ticker.strip().upper()
        if not ticker or len(ticker) > 10:
            return jsonify({'error': 'Invalid ticker symbol'}), 400

        added = add_to_user_watchlist(user_id, ticker)

        return jsonify({
            'ticker': ticker,
            'added': added,
            'message': 'Ticker added to watchlist' if added else 'Ticker already in watchlist',
        })

    # Handle multiple tickers
    tickers = data.get('tickers', [])
    if not isinstance(tickers, list):
        return jsonify({'error': 'tickers must be a list'}), 400

    added_count = 0
    for t in tickers:
        if isinstance(t, str) and t.strip():
            t = t.strip().upper()
            if len(t) <= 10 and add_to_user_watchlist(user_id, t):
                added_count += 1

    return jsonify({
        'added_count': added_count,
        'total_submitted': len(tickers),
        'message': f'{added_count} ticker(s) added to watchlist',
    })


# ──────────────────────────────────────────────────────────────────────────────
# DELETE /api/user/watchlist/<ticker>
# ──────────────────────────────────────────────────────────────────────────────

@user_bp.route('/user/watchlist/<ticker>', methods=['DELETE'])
@log_request
@require_jwt
def remove_from_watchlist(ticker):
    """
    Remove a ticker from the user's watchlist.

    Returns:
        200: Ticker removed
        404: Ticker not in watchlist
    """
    user_id = _get_user_internal_id()

    if not user_id:
        return jsonify({'error': 'User not found'}), 404

    ticker = ticker.strip().upper()
    removed = remove_from_user_watchlist(user_id, ticker)

    if removed:
        return jsonify({
            'ticker': ticker,
            'removed': True,
            'message': 'Ticker removed from watchlist',
        })
    else:
        return jsonify({
            'ticker': ticker,
            'removed': False,
            'error': 'Ticker not found in watchlist',
        }), 404


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/user/watchlist/migrate
# ──────────────────────────────────────────────────────────────────────────────

@user_bp.route('/user/watchlist/migrate', methods=['POST'])
@log_request
@require_jwt
def migrate_watchlist():
    """
    Migrate localStorage watchlist to server.

    Merges the provided tickers with any existing server watchlist.
    This is called after login to sync localStorage data.

    Request body:
        {
            "tickers": ["AAPL", "GOOGL", "MSFT"]
        }

    Returns:
        200: Migration complete with merged count
    """
    user_id = _get_user_internal_id()

    if not user_id:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body required'}), 400

    tickers = data.get('tickers', [])
    if not isinstance(tickers, list):
        return jsonify({'error': 'tickers must be a list'}), 400

    # Clean and validate tickers
    clean_tickers = []
    for t in tickers:
        if isinstance(t, str) and t.strip():
            t = t.strip().upper()
            if len(t) <= 10:
                clean_tickers.append(t)

    # Merge into user's watchlist
    added_count = merge_watchlist(user_id, clean_tickers)

    # Get updated watchlist
    watchlist = get_user_watchlist(user_id)
    final_tickers = [item['ticker'] for item in watchlist]

    logger.info(f"Watchlist migration for {g.user_email}: {added_count} new tickers added")

    return jsonify({
        'migrated_count': added_count,
        'submitted_count': len(clean_tickers),
        'tickers': final_tickers,
        'total_count': len(final_tickers),
        'message': f'Migration complete. {added_count} new ticker(s) added.',
    })
