"""
Flask Application Factory

Creates and configures the Flask application with all necessary extensions,
blueprints, and error handlers.
"""

from flask import Flask, jsonify, request, g
from flask.json.provider import DefaultJSONProvider
from flask_cors import CORS
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
try:
    from flask_socketio import SocketIO
except ImportError:
    SocketIO = None
try:
    from prometheus_flask_instrumentator import Instrumentator
    from prometheus_client import Gauge
except ImportError:
    Instrumentator = None
    Gauge = None
import jwt as pyjwt
import logging
from logging.handlers import RotatingFileHandler
try:
    from pythonjsonlogger import jsonlogger
except ImportError:
    jsonlogger = None
import math
import os
import time
import uuid


class SafeJSONProvider(DefaultJSONProvider):
    """JSON provider that converts NaN/Infinity to null instead of invalid JSON."""

    def dumps(self, obj, **kwargs):
        import json

        def clean(o):
            if isinstance(o, float):
                if math.isnan(o) or math.isinf(o):
                    return None
            if isinstance(o, dict):
                return {k: clean(v) for k, v in o.items()}
            if isinstance(o, (list, tuple)):
                return [clean(v) for v in o]
            return o

        return super().dumps(clean(obj), **kwargs)


cache = Cache()
limiter = Limiter(key_func=get_remote_address)
socketio = SocketIO() if SocketIO else None

# Prometheus custom metrics
if Gauge:
    ACTIVE_DB_CONNECTIONS = Gauge(
        'alphabreak_active_db_connections',
        'Number of active database connections in the pool'
    )
    CACHE_HIT_RATE = Gauge(
        'alphabreak_cache_hit_rate',
        'Cache hit rate (hits / total lookups)'
    )
else:
    ACTIVE_DB_CONNECTIONS = None
    CACHE_HIT_RATE = None


def _get_rate_limit_key():
    """
    Per-user rate-limit key: use the JWT subject (user ID) when an
    Authorization Bearer token is present and valid; fall back to the
    client IP address for anonymous requests.
    """
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]
        try:
            from flask import current_app
            secret = current_app.config.get('JWT_SECRET_KEY')
            algorithm = current_app.config.get('JWT_ALGORITHM', 'HS256')
            payload = pyjwt.decode(token, secret, algorithms=[algorithm])
            user_id = payload.get('sub')
            if user_id:
                return f"user:{user_id}"
        except Exception:
            pass
    return get_remote_address()


def create_app(config_name='development'):
    """
    Flask application factory.

    Args:
        config_name: Configuration environment (development, production, testing)

    Returns:
        Flask app instance
    """
    app = Flask(__name__)
    app.json_provider_class = SafeJSONProvider
    app.json = SafeJSONProvider(app)

    # Load configuration
    config_module = f'app.config.{config_name.capitalize()}Config'
    app.config.from_object(config_module)

    # Enable CORS for frontend access
    CORS(app, resources={r"/api/*": {"origins": app.config.get('CORS_ORIGINS', ['https://alphabreak.vip', 'https://www.alphabreak.vip'])}})

    # Initialize Flask-Caching
    cache.init_app(app)

    # Rate limiting to prevent abuse (per-user when authenticated, per-IP otherwise)
    app.config['RATELIMIT_KEY_FUNC'] = _get_rate_limit_key
    app.config['RATELIMIT_DEFAULT'] = "5000 per day;500 per hour"
    app.config['RATELIMIT_STORAGE_URI'] = app.config.get('RATELIMIT_STORAGE_URL', 'memory://')
    limiter.init_app(app)

    # Exempt health/ready/live endpoints from rate limiting (for K8s probes)
    @limiter.request_filter
    def exempt_health_endpoints():
        from flask import request
        exempt_paths = ['/api/health', '/api/ready', '/api/live']
        return any(request.path.startswith(path) for path in exempt_paths)

    # Initialize Flask-SocketIO for real-time WebSocket support (if installed)
    if socketio:
        socketio.init_app(
            app,
            cors_allowed_origins=app.config.get('CORS_ORIGINS', '*'),
            message_queue=app.config.get('REDIS_URL', None),
            async_mode='eventlet',
        )
        from app.routes import websocket  # noqa: F401 — registers SocketIO events on import

    # Setup structured JSON logging
    if not app.debug:
        if not os.path.exists('logs'):
            os.mkdir('logs')

        file_handler = RotatingFileHandler(
            'logs/trading_api.log',
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        if jsonlogger:
            json_formatter = jsonlogger.JsonFormatter(
                fmt='%(asctime)s %(levelname)s %(name)s %(module)s %(funcName)s %(lineno)d %(message)s',
                rename_fields={
                    'asctime': 'timestamp',
                    'levelname': 'level',
                    'funcName': 'function',
                    'lineno': 'line',
                },
                datefmt='%Y-%m-%dT%H:%M:%S%z',
            )
            file_handler.setFormatter(json_formatter)
        else:
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
            ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Trading API startup')

    # Request-ID middleware and request timing
    @app.before_request
    def _before_request():
        g.request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))
        g.start_time = time.time()

    @app.after_request
    def _after_request(response):
        duration_ms = (time.time() - getattr(g, 'start_time', time.time())) * 1000
        request_id = getattr(g, 'request_id', '-')
        response.headers['X-Request-ID'] = request_id
        app.logger.info(
            'request completed',
            extra={
                'request_id': request_id,
                'method': request.method,
                'path': request.path,
                'status': response.status_code,
                'duration_ms': round(duration_ms, 2),
            },
        )
        # Update custom Prometheus metrics
        if ACTIVE_DB_CONNECTIONS:
            _update_custom_metrics()
        return response

    # Prometheus metrics instrumentation
    if Instrumentator:
        Instrumentator(
            should_group_status_codes=False,
            excluded_handlers=['/metrics'],
        ).instrument(app).expose(app, endpoint='/metrics')

    def _update_custom_metrics():
        """Collect custom metrics from DB pool and cache."""
        try:
            from app.utils.database import db_manager
            status = db_manager.pool_status()
            if status and not status.get('closed'):
                pool = db_manager.connection_pool
                # _used tracks connections currently checked out
                used = len(getattr(pool, '_used', {}))
                ACTIVE_DB_CONNECTIONS.set(used)
        except Exception:
            pass
        try:
            backend = cache.cache
            hits = getattr(backend, '_cache_hits', 0)
            misses = getattr(backend, '_cache_misses', 0)
            total = hits + misses
            CACHE_HIT_RATE.set(hits / total if total > 0 else 0.0)
        except Exception:
            pass

    # Register blueprints
    from app.routes.health import health_bp
    from app.routes.predictions import predictions_bp
    from app.routes.options import options_bp
    from app.routes.frontend_compat import frontend_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.reports import reports_bp
    from app.routes.watchlist import watchlist_bp
    from app.routes.earnings import earnings_bp
    from app.routes.longterm import longterm_bp
    from app.routes.portfolio import portfolio_bp
    from app.routes.forex import forex_bp
    from app.routes.auth import auth_bp
    from app.routes.user import user_bp
    from app.routes.notifications import notifications_bp
    from app.routes.profile import profile_bp
    from app.routes.journal import journal_bp
    from app.routes.analyze import analyze_bp
    from app.routes.darkpool import darkpool_bp

    app.register_blueprint(health_bp, url_prefix='/api')
    app.register_blueprint(predictions_bp, url_prefix='/api')
    app.register_blueprint(options_bp, url_prefix='/api')
    app.register_blueprint(frontend_bp, url_prefix='/api')
    app.register_blueprint(dashboard_bp, url_prefix='/api')
    app.register_blueprint(reports_bp, url_prefix='/api')
    app.register_blueprint(watchlist_bp, url_prefix='/api')
    app.register_blueprint(earnings_bp, url_prefix='/api')
    app.register_blueprint(longterm_bp, url_prefix='/api')
    app.register_blueprint(portfolio_bp, url_prefix='/api')
    app.register_blueprint(forex_bp, url_prefix='/api')
    app.register_blueprint(auth_bp, url_prefix='/api')
    app.register_blueprint(user_bp, url_prefix='/api')
    app.register_blueprint(notifications_bp, url_prefix='/api')
    app.register_blueprint(profile_bp, url_prefix='/api')
    app.register_blueprint(journal_bp, url_prefix='/api')
    app.register_blueprint(analyze_bp, url_prefix='/api')
    app.register_blueprint(darkpool_bp, url_prefix='/api')

    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Endpoint not found'}), 404

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f'Server Error: {error}')
        return jsonify({'error': 'Internal server error'}), 500

    @app.errorhandler(Exception)
    def handle_exception(error):
        app.logger.error(f'Unhandled Exception: {error}')
        return jsonify({'error': 'An unexpected error occurred'}), 500

    # Initialize model manager on startup
    # Note: before_first_request is deprecated in Flask 2.3+
    # Using with app.app_context() instead
    with app.app_context():
        from app.models import model_manager
        try:
            model_manager.load_models()
            app.logger.info('Models loaded successfully')
        except Exception as e:
            app.logger.warning(f'Models not loaded (this is OK if models not trained yet): {e}')

    return app
