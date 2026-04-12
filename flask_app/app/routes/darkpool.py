import re
from app.utils import error_details
import logging
from flask import Blueprint, jsonify, current_app
from app.utils.auth import log_request, require_api_key

logger = logging.getLogger(__name__)

darkpool_bp = Blueprint('darkpool', __name__)

CACHE_TTL = 300

TICKER_PATTERN = re.compile(r'^[A-Z]{1,5}(-[A-Z])?$')


def _get_cached(key, compute_fn, ttl=CACHE_TTL):
    from app import cache
    data = cache.get(key)
    if data is not None:
        return data
    data = compute_fn()
    cache.set(key, data, timeout=ttl)
    return data


def _get_db_manager():
    try:
        from app.utils.database import db_manager
        return db_manager
    except Exception:
        return None


def _validate_ticker(ticker):
    ticker = ticker.strip().upper()
    if not ticker or len(ticker) > 10:
        raise ValueError(f"Invalid ticker: {ticker}")
    if not TICKER_PATTERN.match(ticker):
        raise ValueError(f"Invalid ticker format: {ticker}")
    return ticker


@darkpool_bp.route('/darkpool/<ticker>', methods=['GET'])
@log_request
@require_api_key
def darkpool_ticker(ticker):
    try:
        ticker = _validate_ticker(ticker)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    try:
        db = _get_db_manager()
        if not db:
            return jsonify({'error': 'Database unavailable'}), 503

        cache_key = f'darkpool_{ticker}'
        result = _get_cached(
            cache_key,
            lambda: _fetch_darkpool(ticker, db),
            ttl=CACHE_TTL,
        )
        return jsonify(result)

    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        current_app.logger.error(f"Dark pool error for {ticker}: {e}")
        return jsonify({
            'error': f'Failed to fetch dark pool data for {ticker}',
            'details': error_details(e),
        }), 500


@darkpool_bp.route('/darkpool/<ticker>/venues', methods=['GET'])
@log_request
@require_api_key
def darkpool_venues(ticker):
    try:
        ticker = _validate_ticker(ticker)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    try:
        db = _get_db_manager()
        if not db:
            return jsonify({'error': 'Database unavailable'}), 503

        cache_key = f'darkpool_venues_{ticker}'
        result = _get_cached(
            cache_key,
            lambda: _fetch_venues(ticker, db),
            ttl=CACHE_TTL,
        )
        return jsonify(result)

    except Exception as e:
        current_app.logger.error(f"Dark pool venues error for {ticker}: {e}")
        return jsonify({
            'error': f'Failed to fetch dark pool venues for {ticker}',
            'details': error_details(e),
        }), 500


def _fetch_darkpool(ticker, db):
    with db.get_cursor() as cur:
        cur.execute("""
            SELECT week_start_date, total_darkpool_shares, total_darkpool_trades,
                   num_ats_venues, top_ats_mpid, top_ats_shares, concentration_ratio
            FROM darkpool_ticker_aggregates
            WHERE ticker = %s
            ORDER BY week_start_date DESC
            LIMIT 12
        """, (ticker,))
        rows = cur.fetchall()

    if not rows:
        raise ValueError(f"No dark pool data found for {ticker}")

    weeks = []
    for row in rows:
        weeks.append({
            'week_start_date': row[0].isoformat() if row[0] else None,
            'total_shares': int(row[1]) if row[1] else 0,
            'total_trades': int(row[2]) if row[2] else 0,
            'num_ats_venues': int(row[3]) if row[3] else 0,
            'top_ats_mpid': row[4],
            'top_ats_shares': int(row[5]) if row[5] else 0,
            'concentration_ratio': float(row[6]) if row[6] else 0,
        })

    wow_change = None
    if len(weeks) >= 2 and weeks[1]['total_shares'] > 0:
        wow_change = (weeks[0]['total_shares'] - weeks[1]['total_shares']) / weeks[1]['total_shares']

    with db.get_cursor() as cur:
        cur.execute("""
            SELECT ats_name, ats_mpid, SUM(total_shares) as vol
            FROM darkpool_weekly_volume
            WHERE ticker = %s
              AND week_start_date = (
                  SELECT MAX(week_start_date) FROM darkpool_weekly_volume WHERE ticker = %s
              )
            GROUP BY ats_name, ats_mpid
            ORDER BY vol DESC
            LIMIT 3
        """, (ticker, ticker))
        top_venues = []
        for row in cur.fetchall():
            top_venues.append({
                'ats_name': row[0],
                'ats_mpid': row[1],
                'shares': int(row[2]) if row[2] else 0,
            })

    return {
        'ticker': ticker,
        'latest': weeks[0] if weeks else None,
        'wow_change': round(wow_change, 4) if wow_change is not None else None,
        'weeks': weeks,
        'top_venues': top_venues,
    }


def _fetch_venues(ticker, db):
    with db.get_cursor() as cur:
        cur.execute("""
            SELECT ats_name, ats_mpid, SUM(total_shares) as vol, SUM(total_trades) as trades
            FROM darkpool_weekly_volume
            WHERE ticker = %s
              AND week_start_date >= (
                  SELECT MAX(week_start_date) - INTERVAL '12 weeks'
                  FROM darkpool_weekly_volume WHERE ticker = %s
              )
            GROUP BY ats_name, ats_mpid
            ORDER BY vol DESC
            LIMIT 10
        """, (ticker, ticker))
        venues = []
        for row in cur.fetchall():
            venues.append({
                'ats_name': row[0],
                'ats_mpid': row[1],
                'total_shares': int(row[2]) if row[2] else 0,
                'total_trades': int(row[3]) if row[3] else 0,
            })

    return {
        'ticker': ticker,
        'venues': venues,
    }
