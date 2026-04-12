"""
Streaming Service
=================
Emits real-time price updates and alerts over WebSocket (Flask-SocketIO).

MVP approach: polls yfinance every N seconds for subscribed tickers.
The Polygon.io live feed will replace the poller in a future iteration.

Public helpers
--------------
    stream_price_update(ticker, price_data) — push a price update to a ticker room
    stream_alert(alert_data)               — push a trade-signal alert
    start_price_poller(tickers, interval)  — background thread that polls yfinance
"""

import logging
import time
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def stream_price_update(ticker, price_data):
    """
    Emit a price update event to everyone in the ticker room.

    Args:
        ticker:     Symbol string (e.g. 'AAPL').
        price_data: dict with at least 'price', 'change', 'change_pct', 'volume'.
    """
    from app import socketio

    room = f'ticker:{ticker.upper()}'
    payload = {
        'ticker': ticker.upper(),
        'timestamp': datetime.now(timezone.utc).isoformat(),
        **price_data,
    }
    socketio.emit('price_update', payload, room=room)
    logger.debug('Emitted price_update for %s to room %s', ticker, room)


def stream_alert(alert_data):
    """
    Emit a trade-signal alert to the alerts room.

    Args:
        alert_data: dict — should contain 'ticker', 'signal', 'message', etc.
    """
    from app import socketio

    payload = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        **alert_data,
    }
    socketio.emit('alert', payload, room='alerts')
    logger.info('Emitted alert: %s', alert_data.get('signal', 'unknown'))


def start_price_poller(tickers, interval=60):
    """
    Launch a background thread that polls yfinance for the given tickers
    every *interval* seconds and pushes price_update events.

    This is the MVP approach. It will be replaced by a Polygon.io streaming
    feed in a future iteration.

    Args:
        tickers:  list of ticker symbols to poll.
        interval: seconds between poll cycles (default 60).
    """
    from app import socketio

    def _poll_loop():
        logger.info(
            'Price poller started: tickers=%s interval=%ds',
            tickers, interval,
        )
        while True:
            for ticker in tickers:
                try:
                    data = _fetch_latest_price(ticker)
                    if data:
                        stream_price_update(ticker, data)
                except Exception:
                    logger.exception('Price poller error for %s', ticker)
            time.sleep(interval)

    # socketio.start_background_task is eventlet-safe
    socketio.start_background_task(_poll_loop)
    logger.info('Price poller background task launched')


def _fetch_latest_price(ticker):
    """
    Fetch the latest price snapshot from yfinance for a single ticker.

    Returns a dict with price, change, change_pct, volume, or None on failure.
    """
    try:
        import yfinance as yf

        tk = yf.Ticker(ticker)
        info = tk.fast_info

        price = getattr(info, 'last_price', None)
        prev_close = getattr(info, 'previous_close', None)

        if price is None:
            return None

        change = (price - prev_close) if prev_close else 0.0
        change_pct = (change / prev_close * 100) if prev_close else 0.0

        return {
            'price': round(price, 2),
            'change': round(change, 2),
            'change_pct': round(change_pct, 2),
            'volume': getattr(info, 'last_volume', 0),
        }
    except Exception:
        logger.exception('yfinance fetch failed for %s', ticker)
        return None
