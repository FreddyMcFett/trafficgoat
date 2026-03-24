"""Flask application factory and Socket.IO setup."""

import time
from flask import Flask
from flask_socketio import SocketIO

socketio = SocketIO()

# Global engine reference for the web app
_engine = None
_stats = None

# Session history - stores completed traffic generation sessions
_session_history = []
_current_session = None


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


def get_session_history():
    return _session_history


def start_session(mode, target, load_level=None, dry_run=False, duration=0):
    global _current_session
    _current_session = {
        "id": len(_session_history) + 1,
        "start_time": time.time(),
        "end_time": None,
        "mode": mode,
        "target": target,
        "load_level": load_level,
        "dry_run": dry_run,
        "duration_config": duration,
        "total_packets": 0,
        "total_bytes": 0,
        "total_errors": 0,
        "peak_pps": 0,
        "status": "running",
    }
    return _current_session


def end_session(stats_data=None):
    global _current_session
    if _current_session is None:
        return
    _current_session["end_time"] = time.time()
    _current_session["status"] = "completed"
    if stats_data:
        _current_session["total_packets"] = stats_data.get("total_packets", 0)
        _current_session["total_bytes"] = stats_data.get("total_bytes", 0)
        _current_session["total_errors"] = stats_data.get("total_errors", 0)
    _session_history.insert(0, _current_session)
    # Keep last 50 sessions
    if len(_session_history) > 50:
        _session_history[:] = _session_history[:50]
    _current_session = None


def get_current_session():
    return _current_session


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )
    app.config["SECRET_KEY"] = "trafficgoat-secret"

    from trafficgoat import __version__

    @app.context_processor
    def inject_version():
        return {"app_version": __version__}

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
