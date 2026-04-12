"""
WebSocket Event Handlers
========================
Flask-SocketIO event handlers for real-time data streaming.

Events:
    connect        — authenticate (optional) and log connection
    disconnect     — log disconnection
    subscribe_ticker   — join a ticker room for price updates
    unsubscribe_ticker — leave a ticker room
    subscribe_alerts   — join the trade-signal alerts room
"""

import logging
from flask import request
from flask_socketio import emit, join_room, leave_room
import jwt as pyjwt

from app import socketio

logger = logging.getLogger(__name__)


@socketio.on('connect')
def handle_connect():
    """Handle new WebSocket connection. Optionally authenticate via JWT in query params."""
    token = request.args.get('token')
    user_id = None

    if token:
        try:
            from flask import current_app
            secret = current_app.config.get('JWT_SECRET_KEY')
            algorithm = current_app.config.get('JWT_ALGORITHM', 'HS256')
            payload = pyjwt.decode(token, secret, algorithms=[algorithm])
            user_id = payload.get('sub')
        except pyjwt.ExpiredSignatureError:
            logger.warning('WebSocket connect: expired JWT token from %s', request.sid)
        except pyjwt.InvalidTokenError:
            logger.warning('WebSocket connect: invalid JWT token from %s', request.sid)

    logger.info('WebSocket connected: sid=%s user=%s', request.sid, user_id or 'anonymous')
    emit('connected', {'status': 'ok', 'sid': request.sid})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection."""
    logger.info('WebSocket disconnected: sid=%s', request.sid)


@socketio.on('subscribe_ticker')
def handle_subscribe_ticker(data):
    """
    Subscribe to real-time price updates for a ticker.

    Expects: { "ticker": "AAPL" }
    Joins the client to a room named 'ticker:<SYMBOL>'.
    """
    ticker = (data.get('ticker') or '').upper().strip()
    if not ticker:
        emit('error', {'message': 'ticker is required'})
        return

    room = f'ticker:{ticker}'
    join_room(room)
    logger.info('sid=%s subscribed to %s', request.sid, room)
    emit('subscribed', {'ticker': ticker, 'room': room})


@socketio.on('unsubscribe_ticker')
def handle_unsubscribe_ticker(data):
    """
    Unsubscribe from a ticker room.

    Expects: { "ticker": "AAPL" }
    """
    ticker = (data.get('ticker') or '').upper().strip()
    if not ticker:
        emit('error', {'message': 'ticker is required'})
        return

    room = f'ticker:{ticker}'
    leave_room(room)
    logger.info('sid=%s unsubscribed from %s', request.sid, room)
    emit('unsubscribed', {'ticker': ticker, 'room': room})


@socketio.on('subscribe_alerts')
def handle_subscribe_alerts(data=None):
    """Subscribe to trade-signal alerts room."""
    join_room('alerts')
    logger.info('sid=%s subscribed to alerts', request.sid)
    emit('subscribed', {'room': 'alerts'})
