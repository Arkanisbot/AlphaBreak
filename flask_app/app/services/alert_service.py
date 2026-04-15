"""
Smart Alerts Service
====================
Rule storage + the evaluation engine. Rules are single-ticker, up to 3
AND-chained threshold conditions over price, volume, and a curated set of
indicators. Indicator math is reused from dashboard_service where possible.
"""

import json
import logging
import re
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from app.services.dashboard_service import (
    _calculate_rsi,
    _calculate_sma,
    _calculate_stochastic,
    _calculate_cci,
    _calculate_adx,
)

logger = logging.getLogger(__name__)

MAX_RULES_PER_USER = 10
MAX_CONDITIONS_PER_RULE = 3

TICKER_RE = re.compile(r'^[A-Z][A-Z0-9.\-]{0,11}$')

ALLOWED_FIELDS = {
    'price', 'volume',
    'rsi_14',
    'sma_20', 'sma_50', 'sma_200',
    'ema_20', 'ema_50',
    'macd_hist',
    'stoch_k',
    'cci_20',
    'adx_14',
}

ALLOWED_OPS = {'>', '<', '>=', '<=', '=='}

ALLOWED_COOLDOWNS = {3600, 14400, 86400, 0}  # 1h / 4h / 1d / reset-only

FIELD_LABELS = {
    'price': 'Price', 'volume': 'Volume',
    'rsi_14': 'RSI(14)',
    'sma_20': 'SMA(20)', 'sma_50': 'SMA(50)', 'sma_200': 'SMA(200)',
    'ema_20': 'EMA(20)', 'ema_50': 'EMA(50)',
    'macd_hist': 'MACD Histogram',
    'stoch_k': 'Stochastic %K',
    'cci_20': 'CCI(20)',
    'adx_14': 'ADX(14)',
}


# ──────────────────────────────────────────────────────────────────────────────
# Validation
# ──────────────────────────────────────────────────────────────────────────────

def validate_payload(payload):
    """Return (cleaned_dict, None) or (None, error_message)."""
    if not isinstance(payload, dict):
        return None, 'Invalid payload'

    name = (payload.get('name') or '').strip()
    if not name or len(name) > 120:
        return None, 'Name required (1–120 chars)'

    ticker = (payload.get('ticker') or '').strip().upper()
    if not TICKER_RE.match(ticker):
        return None, 'Invalid ticker'

    raw_conditions = payload.get('conditions')
    if not isinstance(raw_conditions, list) or not raw_conditions:
        return None, 'At least one condition required'
    if len(raw_conditions) > MAX_CONDITIONS_PER_RULE:
        return None, f'At most {MAX_CONDITIONS_PER_RULE} conditions allowed'

    clean_conditions = []
    for cond in raw_conditions:
        if not isinstance(cond, dict):
            return None, 'Condition must be an object'
        field = cond.get('field')
        op = cond.get('op')
        value = cond.get('value')
        if field not in ALLOWED_FIELDS:
            return None, f'Unsupported field: {field}'
        if op not in ALLOWED_OPS:
            return None, f'Unsupported operator: {op}'
        try:
            value = float(value)
        except (TypeError, ValueError):
            return None, 'Condition value must be numeric'
        clean_conditions.append({'field': field, 'op': op, 'value': value})

    cooldown = payload.get('cooldown_seconds', 86400)
    try:
        cooldown = int(cooldown)
    except (TypeError, ValueError):
        return None, 'Invalid cooldown'
    if cooldown not in ALLOWED_COOLDOWNS:
        return None, 'Invalid cooldown'

    return {
        'name': name,
        'ticker': ticker,
        'conditions': clean_conditions,
        'cooldown_seconds': cooldown,
        'email_enabled': bool(payload.get('email_enabled', True)),
        'in_app_enabled': bool(payload.get('in_app_enabled', True)),
        'is_active': bool(payload.get('is_active', True)),
    }, None


# ──────────────────────────────────────────────────────────────────────────────
# CRUD
# ──────────────────────────────────────────────────────────────────────────────

def _row_to_dict(row):
    return {
        'id': row[0],
        'user_id': row[1],
        'name': row[2],
        'ticker': row[3],
        'conditions': row[4],
        'cooldown_seconds': row[5],
        'email_enabled': row[6],
        'in_app_enabled': row[7],
        'is_active': row[8],
        'last_triggered_at': row[9].isoformat() if row[9] else None,
        'created_at': row[10].isoformat() if row[10] else None,
        'updated_at': row[11].isoformat() if row[11] else None,
    }


_SELECT_COLS = """
    id, user_id, name, ticker, conditions, cooldown_seconds,
    email_enabled, in_app_enabled, is_active, last_triggered_at,
    created_at, updated_at
"""


def list_rules(db_manager, user_id):
    rows = db_manager.execute_query(
        f"SELECT {_SELECT_COLS} FROM user_alert_rules WHERE user_id = %s ORDER BY created_at DESC",
        (user_id,),
    )
    return [_row_to_dict(r) for r in (rows or [])]


def count_rules(db_manager, user_id):
    rows = db_manager.execute_query(
        "SELECT COUNT(*) FROM user_alert_rules WHERE user_id = %s",
        (user_id,),
    )
    return rows[0][0] if rows else 0


def get_rule(db_manager, rule_id, user_id):
    rows = db_manager.execute_query(
        f"SELECT {_SELECT_COLS} FROM user_alert_rules WHERE id = %s AND user_id = %s",
        (rule_id, user_id),
    )
    return _row_to_dict(rows[0]) if rows else None


def create_rule(db_manager, user_id, payload):
    clean, err = validate_payload(payload)
    if err:
        return None, err
    if count_rules(db_manager, user_id) >= MAX_RULES_PER_USER:
        return None, f'Rule limit reached ({MAX_RULES_PER_USER}). Delete an existing rule first.'

    query = f"""
        INSERT INTO user_alert_rules
            (user_id, name, ticker, conditions, cooldown_seconds,
             email_enabled, in_app_enabled, is_active)
        VALUES (%s, %s, %s, %s::jsonb, %s, %s, %s, %s)
        RETURNING {_SELECT_COLS}
    """
    with db_manager.get_cursor(commit=True) as cur:
        cur.execute(query, (
            user_id, clean['name'], clean['ticker'],
            json.dumps(clean['conditions']), clean['cooldown_seconds'],
            clean['email_enabled'], clean['in_app_enabled'], clean['is_active'],
        ))
        return _row_to_dict(cur.fetchone()), None


def update_rule(db_manager, rule_id, user_id, payload):
    clean, err = validate_payload(payload)
    if err:
        return None, err

    query = f"""
        UPDATE user_alert_rules SET
            name = %s, ticker = %s, conditions = %s::jsonb,
            cooldown_seconds = %s, email_enabled = %s, in_app_enabled = %s,
            is_active = %s, updated_at = NOW()
        WHERE id = %s AND user_id = %s
        RETURNING {_SELECT_COLS}
    """
    with db_manager.get_cursor(commit=True) as cur:
        cur.execute(query, (
            clean['name'], clean['ticker'], json.dumps(clean['conditions']),
            clean['cooldown_seconds'], clean['email_enabled'], clean['in_app_enabled'],
            clean['is_active'], rule_id, user_id,
        ))
        row = cur.fetchone()
        if not row:
            return None, 'Rule not found'
        return _row_to_dict(row), None


def delete_rule(db_manager, rule_id, user_id):
    with db_manager.get_cursor(commit=True) as cur:
        cur.execute(
            "DELETE FROM user_alert_rules WHERE id = %s AND user_id = %s",
            (rule_id, user_id),
        )
        return cur.rowcount > 0


def toggle_rule(db_manager, rule_id, user_id, is_active):
    with db_manager.get_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE user_alert_rules SET is_active = %s, updated_at = NOW() "
            "WHERE id = %s AND user_id = %s",
            (bool(is_active), rule_id, user_id),
        )
        return cur.rowcount > 0


def list_firings(db_manager, user_id, rule_id=None, limit=50):
    base = """
        SELECT f.id, f.rule_id, r.name, r.ticker, f.fired_at, f.matched_values
        FROM alert_rule_firings f
        JOIN user_alert_rules r ON r.id = f.rule_id
        WHERE r.user_id = %s
    """
    params = [user_id]
    if rule_id:
        base += " AND f.rule_id = %s"
        params.append(rule_id)
    base += " ORDER BY f.fired_at DESC LIMIT %s"
    params.append(min(int(limit), 200))

    rows = db_manager.execute_query(base, tuple(params))
    return [
        {
            'id': r[0],
            'rule_id': r[1],
            'rule_name': r[2],
            'ticker': r[3],
            'fired_at': r[4].isoformat() if r[4] else None,
            'matched_values': r[5],
        }
        for r in (rows or [])
    ]


# ──────────────────────────────────────────────────────────────────────────────
# Evaluation engine
# ──────────────────────────────────────────────────────────────────────────────

def _ema(series, length):
    return series.ewm(span=length, adjust=False).mean()


def compute_indicator_snapshot(df):
    """
    Given a DataFrame with Open/High/Low/Close/Volume (chronological),
    return a dict of the latest value for each field in ALLOWED_FIELDS.
    NaN → None.
    """
    if df is None or df.empty or 'Close' not in df.columns:
        return {}

    close = df['Close']

    snap = {
        'price': close.iloc[-1],
        'volume': df['Volume'].iloc[-1] if 'Volume' in df.columns else np.nan,
        'rsi_14': _calculate_rsi(df, 14).iloc[-1],
        'sma_20': _calculate_sma(close, 20).iloc[-1],
        'sma_50': _calculate_sma(close, 50).iloc[-1],
        'sma_200': _calculate_sma(close, 200).iloc[-1] if len(close) >= 200 else np.nan,
        'ema_20': _ema(close, 20).iloc[-1],
        'ema_50': _ema(close, 50).iloc[-1],
        'cci_20': _calculate_cci(df, 20).iloc[-1],
    }

    # MACD histogram: 12/26 EMA diff, minus 9-EMA of that diff
    macd_line = _ema(close, 12) - _ema(close, 26)
    macd_signal = _ema(macd_line, 9)
    snap['macd_hist'] = (macd_line - macd_signal).iloc[-1]

    # Stochastic %K
    stoch_k, _ = _calculate_stochastic(df, 14, 3)
    snap['stoch_k'] = stoch_k.iloc[-1]

    # ADX
    adx, _, _ = _calculate_adx(df, 14)
    snap['adx_14'] = adx.iloc[-1]

    # Coerce NaN → None and numpy scalars → float
    cleaned = {}
    for k, v in snap.items():
        try:
            fv = float(v)
            if np.isnan(fv) or np.isinf(fv):
                cleaned[k] = None
            else:
                cleaned[k] = fv
        except (TypeError, ValueError):
            cleaned[k] = None
    return cleaned


def _eval_op(left, op, right):
    if left is None:
        return False
    if op == '>':  return left > right
    if op == '<':  return left < right
    if op == '>=': return left >= right
    if op == '<=': return left <= right
    if op == '==': return left == right
    return False


def evaluate_rule(rule, snapshot):
    """Return (fired: bool, matched_values: dict). Parses JSONB if string."""
    conditions = rule.get('conditions')
    if isinstance(conditions, str):
        try:
            conditions = json.loads(conditions)
        except (json.JSONDecodeError, TypeError):
            return False, {}
    if not conditions:
        return False, {}

    matched = {}
    for cond in conditions:
        field = cond.get('field')
        val = snapshot.get(field)
        matched[field] = val
        if not _eval_op(val, cond.get('op'), cond.get('value')):
            return False, matched
    return True, matched


def is_in_cooldown(rule, now=None):
    cooldown = rule.get('cooldown_seconds') or 0
    if cooldown <= 0:
        # 0 = reset-only (no automatic cooldown, but we still gate one-shot via last_triggered_at)
        return False
    last = rule.get('last_triggered_at')
    if not last:
        return False
    if isinstance(last, str):
        try:
            last = datetime.fromisoformat(last.replace('Z', '+00:00'))
        except ValueError:
            return False
    now = now or datetime.now(timezone.utc)
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    return (now - last).total_seconds() < cooldown


def format_rule_message(rule, matched_values):
    """Short human-readable summary for notification body."""
    parts = []
    conds = rule.get('conditions')
    if isinstance(conds, str):
        try:
            conds = json.loads(conds)
        except (json.JSONDecodeError, TypeError):
            conds = []
    for cond in conds or []:
        label = FIELD_LABELS.get(cond['field'], cond['field'])
        actual = matched_values.get(cond['field'])
        actual_str = f'{actual:.2f}' if isinstance(actual, (int, float)) else '—'
        parts.append(f"{label} {cond['op']} {cond['value']} (now {actual_str})")
    return '; '.join(parts)
