"""
Forex Routes
============
Endpoints for forex correlation model and data:

1. GET /api/forex/pairs           -- List all forex pairs
2. GET /api/forex/data/<pair>     -- Historical data for a pair
3. GET /api/forex/correlations    -- Correlation matrix
4. GET /api/forex/trend-breaks    -- Trend breaks for all pairs
5. GET /api/forex/summary         -- Summary statistics
"""

import logging
from flask import Blueprint, jsonify, request, current_app
from app.utils.auth import log_request, require_api_key

logger = logging.getLogger(__name__)

forex_bp = Blueprint('forex', __name__)


def _get_db_manager():
    """Get database manager."""
    try:
        from app.utils.database import db_manager
        return db_manager
    except Exception:
        return None


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/forex/pairs
# ──────────────────────────────────────────────────────────────────────────────

@forex_bp.route('/forex/pairs', methods=['GET'])
@log_request
@require_api_key
def get_forex_pairs():
    """Get list of all forex pairs with metadata."""
    try:
        db = _get_db_manager()
        if db is None:
            return jsonify({'error': 'Database not available'}), 503

        rows = db.execute_query("""
            SELECT pair, base_currency, quote_currency,
                   data_start_date, data_end_date, total_records,
                   model_trained, model_trained_at, model_version,
                   avg_daily_range, volatility_30d
            FROM forex_pairs
            ORDER BY pair
        """)

        pairs = []
        for row in (rows or []):
            pairs.append({
                'pair': row[0],
                'base_currency': row[1],
                'quote_currency': row[2],
                'data_start_date': row[3].isoformat() if row[3] else None,
                'data_end_date': row[4].isoformat() if row[4] else None,
                'total_records': row[5],
                'model_trained': row[6],
                'model_trained_at': row[7].isoformat() if row[7] else None,
                'model_version': row[8],
                'avg_daily_range': float(row[9]) if row[9] else None,
                'volatility_30d': float(row[10]) if row[10] else None,
            })

        return jsonify({'pairs': pairs, 'count': len(pairs)})

    except Exception as e:
        logger.error(f"Forex pairs error: {e}")
        return jsonify({'error': str(e)}), 500


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/forex/data/<pair>
# ──────────────────────────────────────────────────────────────────────────────

@forex_bp.route('/forex/data/<pair>', methods=['GET'])
@log_request
@require_api_key
def get_forex_data(pair):
    """Get historical data for a forex pair."""
    # Normalize pair format
    pair = pair.upper().replace('_', '/')
    if '/' not in pair and len(pair) == 6:
        pair = pair[:3] + '/' + pair[3:]

    days = request.args.get('days', 365, type=int)
    days = min(max(days, 1), 10000)

    try:
        db = _get_db_manager()
        if db is None:
            return jsonify({'error': 'Database not available'}), 503

        rows = db.execute_query("""
            SELECT date, open, high, low, close, volume, source
            FROM forex_daily_data
            WHERE pair = %s
              AND date >= NOW() - INTERVAL '%s days'
            ORDER BY date DESC
        """, (pair, days))

        data = []
        for row in (rows or []):
            data.append({
                'date': row[0].isoformat() if row[0] else None,
                'open': float(row[1]) if row[1] else None,
                'high': float(row[2]) if row[2] else None,
                'low': float(row[3]) if row[3] else None,
                'close': float(row[4]) if row[4] else None,
                'volume': int(row[5]) if row[5] else 0,
                'source': row[6],
            })

        return jsonify({
            'pair': pair,
            'data': data,
            'count': len(data),
        })

    except Exception as e:
        logger.error(f"Forex data error for {pair}: {e}")
        return jsonify({'error': str(e)}), 500


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/forex/correlations
# ──────────────────────────────────────────────────────────────────────────────

@forex_bp.route('/forex/correlations', methods=['GET'])
@log_request
@require_api_key
def get_forex_correlations():
    """Get correlation matrix between forex pairs."""
    strength_filter = request.args.get('strength')  # 'strong', 'mid', 'weak'

    try:
        db = _get_db_manager()
        if db is None:
            return jsonify({'error': 'Database not available'}), 503

        # Get latest correlations
        query = """
            SELECT pair_a, pair_b, correlation_30d, correlation_90d,
                   correlation_1y, correlation_all, pattern_strength,
                   lead_lag_days, lead_lag_correlation, data_points
            FROM forex_correlations
            WHERE calculation_date = (
                SELECT MAX(calculation_date) FROM forex_correlations
            )
        """

        if strength_filter and strength_filter in ('strong', 'mid', 'weak'):
            query += f" AND pattern_strength = '{strength_filter}'"

        query += " ORDER BY ABS(correlation_all) DESC"

        rows = db.execute_query(query)

        correlations = []
        for row in (rows or []):
            correlations.append({
                'pair_a': row[0],
                'pair_b': row[1],
                'correlation_30d': float(row[2]) if row[2] else None,
                'correlation_90d': float(row[3]) if row[3] else None,
                'correlation_1y': float(row[4]) if row[4] else None,
                'correlation_all': float(row[5]) if row[5] else None,
                'pattern_strength': row[6],
                'lead_lag_days': row[7],
                'lead_lag_correlation': float(row[8]) if row[8] else None,
                'data_points': row[9],
            })

        # Get thresholds
        thresh_rows = db.execute_query("""
            SELECT strong_min, mid_min, weak_max, max_correlation,
                   min_correlation, avg_correlation
            FROM forex_correlation_thresholds
            ORDER BY calculation_date DESC
            LIMIT 1
        """)

        thresholds = None
        if thresh_rows:
            t = thresh_rows[0]
            thresholds = {
                'strong_min': float(t[0]) if t[0] else None,
                'mid_min': float(t[1]) if t[1] else None,
                'weak_max': float(t[2]) if t[2] else None,
                'max_correlation': float(t[3]) if t[3] else None,
                'min_correlation': float(t[4]) if t[4] else None,
                'avg_correlation': float(t[5]) if t[5] else None,
            }

        return jsonify({
            'correlations': correlations,
            'count': len(correlations),
            'thresholds': thresholds,
        })

    except Exception as e:
        logger.error(f"Forex correlations error: {e}")
        return jsonify({'error': str(e)}), 500


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/forex/trend-breaks
# ──────────────────────────────────────────────────────────────────────────────

@forex_bp.route('/forex/trend-breaks', methods=['GET'])
@log_request
@require_api_key
def get_forex_trend_breaks():
    """Get trend breaks across all forex pairs."""
    pair = request.args.get('pair')
    direction = request.args.get('direction')
    days = request.args.get('days', 30, type=int)
    limit = request.args.get('limit', 100, type=int)

    try:
        db = _get_db_manager()
        if db is None:
            return jsonify({'error': 'Database not available'}), 503

        conditions = ["break_date >= NOW() - INTERVAL '%s days'"]
        params = [days]

        if pair:
            pair = pair.upper().replace('_', '/')
            if '/' not in pair and len(pair) == 6:
                pair = pair[:3] + '/' + pair[3:]
            conditions.append("pair = %s")
            params.append(pair)

        if direction and direction in ('bullish', 'bearish'):
            conditions.append("break_direction = %s")
            params.append(direction)

        where_clause = " AND ".join(conditions)
        params.append(limit)

        rows = db.execute_query(f"""
            SELECT pair, break_date, break_direction, break_probability, confidence,
                   price_at_break, price_before_5d, movement_pct,
                   rsi_value, cci_value, macd_histogram,
                   stochastic_k, stochastic_d, adx_value, bb_position,
                   outcome_5d_pct, outcome_10d_pct, was_correct
            FROM forex_trend_breaks
            WHERE {where_clause}
            ORDER BY break_date DESC
            LIMIT %s
        """, tuple(params))

        breaks = []
        for row in (rows or []):
            breaks.append({
                'pair': row[0],
                'break_date': row[1].isoformat() if row[1] else None,
                'break_direction': row[2],
                'break_probability': float(row[3]) if row[3] else None,
                'confidence': float(row[4]) if row[4] else None,
                'price_at_break': float(row[5]) if row[5] else None,
                'price_before_5d': float(row[6]) if row[6] else None,
                'movement_pct': float(row[7]) if row[7] else None,
                'indicators': {
                    'rsi': float(row[8]) if row[8] else None,
                    'cci': float(row[9]) if row[9] else None,
                    'macd_histogram': float(row[10]) if row[10] else None,
                    'stochastic_k': float(row[11]) if row[11] else None,
                    'stochastic_d': float(row[12]) if row[12] else None,
                    'adx': float(row[13]) if row[13] else None,
                    'bb_position': row[14],
                },
                'outcome': {
                    'pct_5d': float(row[15]) if row[15] else None,
                    'pct_10d': float(row[16]) if row[16] else None,
                    'was_correct': row[17],
                },
            })

        return jsonify({
            'trend_breaks': breaks,
            'count': len(breaks),
        })

    except Exception as e:
        logger.error(f"Forex trend breaks error: {e}")
        return jsonify({'error': str(e)}), 500


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/forex/summary
# ──────────────────────────────────────────────────────────────────────────────

@forex_bp.route('/forex/summary', methods=['GET'])
@log_request
@require_api_key
def get_forex_summary():
    """Get summary statistics for forex models."""
    try:
        db = _get_db_manager()
        if db is None:
            return jsonify({'error': 'Database not available'}), 503

        # Pairs count
        pairs_result = db.execute_query("SELECT COUNT(*) FROM forex_pairs")
        pairs_count = pairs_result[0][0] if pairs_result else 0

        # Total data points
        data_result = db.execute_query("SELECT COUNT(*) FROM forex_daily_data")
        data_count = data_result[0][0] if data_result else 0

        # Correlation counts by strength
        corr_result = db.execute_query("""
            SELECT pattern_strength, COUNT(*)
            FROM forex_correlations
            WHERE calculation_date = (SELECT MAX(calculation_date) FROM forex_correlations)
            GROUP BY pattern_strength
        """)

        pattern_counts = {'strong': 0, 'mid': 0, 'weak': 0}
        for row in (corr_result or []):
            if row[0] in pattern_counts:
                pattern_counts[row[0]] = row[1]

        # Trend breaks count by pair
        breaks_result = db.execute_query("""
            SELECT pair, COUNT(*) as break_count
            FROM forex_trend_breaks
            GROUP BY pair
            ORDER BY break_count DESC
        """)

        breaks_by_pair = {}
        total_breaks = 0
        for row in (breaks_result or []):
            breaks_by_pair[row[0]] = row[1]
            total_breaks += row[1]

        # Recent breaks (last 7 days)
        recent_result = db.execute_query("""
            SELECT COUNT(*)
            FROM forex_trend_breaks
            WHERE break_date >= NOW() - INTERVAL '7 days'
        """)
        recent_breaks = recent_result[0][0] if recent_result else 0

        return jsonify({
            'pairs_count': pairs_count,
            'data_points': data_count,
            'pattern_counts': pattern_counts,
            'total_pattern_correlations': sum(pattern_counts.values()),
            'total_trend_breaks': total_breaks,
            'trend_breaks_by_pair': breaks_by_pair,
            'recent_breaks_7d': recent_breaks,
        })

    except Exception as e:
        logger.error(f"Forex summary error: {e}")
        return jsonify({'error': str(e)}), 500
