"""Flask application factory and Socket.IO setup."""

from flask import Flask
from flask_socketio import SocketIO

socketio = SocketIO()

# Global engine reference for the web app
_engine = None
_stats = None


def get_engine():
    return _engine


def get_stats():
    return _stats


def set_engine(engine):
    global _engine
    _engine = engine


def set_stats(stats):
    global _stats
    _stats = stats


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )
    app.config["SECRET_KEY"] = "trafficgoat-secret"

    from trafficgoat.web.routes import bp
    app.register_blueprint(bp)

    socketio.init_app(app, cors_allowed_origins="*", async_mode="eventlet")

    # Setup stats collector for web
    from trafficgoat.stats import StatsCollector
    stats = StatsCollector()
    set_stats(stats)

    # Wire up Socket.IO broadcasting
    stats.on_stats(lambda s: socketio.emit("stats_update", s, namespace="/"))
    stats.on_log(lambda msg: socketio.emit("log_message", {"message": msg}, namespace="/"))

    return app
