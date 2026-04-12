"""
WSGI Entry Point
=================
Entry point for Gunicorn and other WSGI servers.

Usage:
    # Development (uses socketio.run for WebSocket support)
    python wsgi.py

    # Production with Gunicorn (eventlet worker class)
    gunicorn -c gunicorn_config.py wsgi:app
"""

import os
import sys

# Add parent directory to path for src imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, socketio

# Get environment from ENV variable, default to production
config_name = os.environ.get('FLASK_ENV', 'production')

# Create the application instance
app = create_app(config_name)


if __name__ == '__main__':
    # Development server — use socketio.run() for WebSocket support
    debug = config_name == 'development'
    port = int(os.environ.get('PORT', 5000))

    print(f"Starting Flask development server with SocketIO...")
    print(f"Environment: {config_name}")
    print(f"Debug mode: {debug}")
    print(f"Port: {port}")

    socketio.run(
        app,
        host='0.0.0.0',
        port=port,
        debug=debug,
    )
