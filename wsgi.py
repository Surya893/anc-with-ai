"""
WSGI Entry Point for Production Deployment
Uses Gunicorn with Gevent workers for async support
"""

import os
from server import app, socketio

# Set production environment
os.environ.setdefault('FLASK_ENV', 'production')

# Initialize application
application = app

# For running with gunicorn + socketio
if __name__ == "__main__":
    socketio.run(application)
