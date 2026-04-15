"""
Airflow DAG: Smart Alerts Evaluator
====================================
Every 10 minutes during US market hours, evaluates user-defined alert rules
against fresh OHLCV data and fires notifications via the existing
notification_service pipeline.

Pattern mirrors trend_break_10min_report_dag.py for DB + scheduling, and
portfolio_update_dag.py for batch per-row iteration.
"""

import json
import logging
import os
import sys
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

sys.path.insert(0, '/app')

logger = logging.getLogger(__name__)

default_args = {
    'owner': 'trading-system',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
    'execution_timeout': timedelta(minutes=8),
}

dag = DAG(
    'smart_alerts_evaluator',
    default_args=default_args,
    description='Evaluate user-defined smart alert rules every 10 minutes',
    schedule_interval='*/10 * * * *',
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
    tags=['alerts', '10min'],
)

DB_CONFIG = {
    'host': os.getenv('TIMESERIES_DB_HOST', 'postgres-timeseries-service'),
    'port': int(os.getenv('TIMESERIES_DB_PORT', 5432)),
    'database': os.getenv('TIMESERIES_DB_NAME', 'trading_data'),
    'user': os.getenv('TIMESERIES_DB_USER', 'trading'),
    'password': os.getenv('TIMESERIES_DB_PASSWORD', 'trading_password'),
}


def _is_market_hours():
    now_utc = datetime.utcnow()
    weekday = now_utc.weekday()
    if weekday >= 5:
        return False
    et_hour = (now_utc.hour - 5) % 24
    if et_hour < 9 or et_hour >= 16:
        return False
    if et_hour == 9 and now_utc.minute < 30:
        return False
    return True


def _fetch_ohlcv(ticker, period_days=400):
    """Fetch a ~400-day daily OHLCV DataFrame via yfinance."""
    import yfinance as yf
    try:
        df = yf.Ticker(ticker).history(period=f'{period_days}d', interval='1d', auto_adjust=False)
        if df is None or df.empty:
            return None
        # Normalize columns to Title-Case expected by alert_service
        df = df.rename(columns={c: c.title() for c in df.columns})
        return df
    except Exception as e:
        logger.warning(f"yfinance fetch failed for {ticker}: {e}")
        return None


def evaluate_alerts(**context):
    """Main task: load active rules, compute indicators, fire notifications."""
    if not _is_market_hours():
        logger.info("Outside US market hours, skipping evaluation")
        return 0

    import psycopg2
    from psycopg2.extras import RealDictCursor

    # Import after sys.path fix so /app resolves
    from app.services import alert_service
    from app.services.notification_service import (
        create_notification,
        should_send_email,
        _send_email_ses,
    )

    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False

    try:
        # 1) Pull all active rules joined with user email
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT r.id, r.user_id, r.name, r.ticker, r.conditions,
                       r.cooldown_seconds, r.email_enabled, r.in_app_enabled,
                       r.last_triggered_at, u.email, u.display_name
                FROM user_alert_rules r
                JOIN users u ON u.id = r.user_id
                WHERE r.is_active = TRUE AND u.is_active = TRUE
            """)
            rules = list(cur.fetchall())

        if not rules:
            logger.info("No active alert rules")
            return 0

        # 2) Group by ticker to fetch each ticker's OHLCV only once
        rules_by_ticker = {}
        for r in rules:
            rules_by_ticker.setdefault(r['ticker'], []).append(r)

        logger.info(f"Evaluating {len(rules)} rules across {len(rules_by_ticker)} tickers")

        fired_count = 0
        for ticker, ticker_rules in rules_by_ticker.items():
            df = _fetch_ohlcv(ticker)
            if df is None or df.empty:
                continue

            snapshot = alert_service.compute_indicator_snapshot(df)
            if not snapshot:
                continue

            for rule in ticker_rules:
                try:
                    if alert_service.is_in_cooldown(rule):
                        continue

                    fired, matched = alert_service.evaluate_rule(rule, snapshot)
                    if not fired:
                        continue

                    body = alert_service.format_rule_message(rule, matched)
                    title = f"Alert: {rule['name']} ({ticker})"
                    metadata = {
                        'ticker': ticker,
                        'rule_id': rule['id'],
                        'rule_name': rule['name'],
                        'matched_values': matched,
                    }

                    notif_id = None
                    if rule['in_app_enabled']:
                        notif_id = create_notification(
                            conn, rule['user_id'], 'smart_alert', title, body, metadata
                        )

                    if rule['email_enabled'] and should_send_email(conn, rule['user_id'], 'smart_alert'):
                        sent = _send_email_ses(
                            conn, notif_id, rule['email'],
                            f"[AlphaBreak] {title}", body, metadata
                        )
                        if sent and notif_id:
                            with conn.cursor() as cur:
                                cur.execute(
                                    "UPDATE notifications SET email_sent = TRUE, email_sent_at = NOW() WHERE id = %s",
                                    (notif_id,),
                                )
                                conn.commit()

                    with conn.cursor() as cur:
                        cur.execute(
                            "UPDATE user_alert_rules SET last_triggered_at = NOW() WHERE id = %s",
                            (rule['id'],),
                        )
                        cur.execute(
                            "INSERT INTO alert_rule_firings (rule_id, matched_values, notification_id) "
                            "VALUES (%s, %s::jsonb, %s)",
                            (rule['id'], json.dumps(matched), notif_id),
                        )
                        conn.commit()

                    fired_count += 1
                    logger.info(f"Fired rule {rule['id']} ({rule['name']}) for user {rule['user_id']}")
                except Exception as e:
                    logger.exception(f"Failed to evaluate rule {rule.get('id')}: {e}")
                    conn.rollback()

        logger.info(f"Smart alerts evaluator: fired {fired_count} alerts")
        return fired_count
    finally:
        conn.close()


evaluate_task = PythonOperator(
    task_id='evaluate_alerts',
    python_callable=evaluate_alerts,
    dag=dag,
)
