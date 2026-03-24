"""Web UI routes and API endpoints."""

import os
import time
from flask import Blueprint, render_template, request, jsonify, redirect
from flask_socketio import emit

from trafficgoat.web.app import (
    socketio, get_engine, get_stats, set_engine,
    get_session_history, start_session, end_session, get_current_session,
)
from trafficgoat.config import TrafficConfig
from trafficgoat.engine import TrafficEngine
from trafficgoat.modes import MODES

bp = Blueprint("main", __name__)


@bp.route("/")
def dashboard():
    return render_template("dashboard.html")


@bp.route("/generate")
def generate_page():
    return render_template("generate.html")


@bp.route("/modes")
def modes_page():
    """Redirect old modes page to generate."""
    return redirect("/generate")


@bp.route("/logs")
def logs_page():
    return render_template("logs.html")


# ---- API Endpoints ----

@bp.route("/api/start", methods=["POST"])
def api_start():
    """Start traffic generation."""
    data = request.get_json() or {}
    stats = get_stats()
    engine = get_engine()

    if engine and engine.is_running():
        return jsonify({"error": "Engine already running. Stop it first."}), 400

    # Check root
    if os.geteuid() != 0:
        return jsonify({"error": "TrafficGoat requires root privileges for raw socket access."}), 403

    mode_name = data.get("mode", "stress")

    config = TrafficConfig(
        target=data.get("target", "127.0.0.1"),
        ports=data.get("ports", "80"),
        duration=int(data.get("duration", 60)),
        rate=int(data.get("rate", 100)),
        threads=int(data.get("threads", 4)),
        mode=mode_name,
        protocol=data.get("protocol", ""),
        dry_run=data.get("dry_run", False),
    )

    # For auto mode, attach load level
    load_level = None
    if mode_name == "auto":
        load_level = data.get("load", "medium")
        config.auto_load = load_level

    stats.reset()
    new_engine = TrafficEngine(config, stats)
    set_engine(new_engine)

    mode_class = MODES.get(config.mode)
    if not mode_class:
        return jsonify({"error": f"Unknown mode: {config.mode}"}), 400

    mode_class.configure(config, new_engine, stats)

    # Record session
    start_session(
        mode=config.mode,
        target=config.target,
        load_level=load_level,
        dry_run=config.dry_run,
        duration=config.duration,
    )

    new_engine.start()

    return jsonify({"status": "started", "mode": config.mode, "target": config.target})


@bp.route("/api/stop", methods=["POST"])
def api_stop():
    """Stop traffic generation."""
    engine = get_engine()
    if engine and engine.is_running():
        # Capture final stats before stopping
        stats_data = engine.get_status()
        engine.stop()
        end_session(stats_data)
        return jsonify({"status": "stopped"})
    return jsonify({"status": "not_running"})


@bp.route("/api/status", methods=["GET"])
def api_status():
    """Get current engine status and stats."""
    engine = get_engine()
    stats = get_stats()
    if engine:
        status = engine.get_status()
        # If engine finished on its own, record the session
        if not status.get("running") and get_current_session():
            end_session(status)
        return jsonify(status)
    return jsonify({
        "running": False,
        "elapsed": 0,
        "total_packets": 0,
        "total_bytes": 0,
        "total_errors": 0,
        "total_pps": 0,
        "total_bps": 0,
        "generators": {},
        "mode": "",
        "target": "",
        "generator_count": 0,
    })


@bp.route("/api/modes", methods=["GET"])
def api_modes():
    """Get available modes."""
    modes_info = {}
    for name, cls in MODES.items():
        modes_info[name] = {
            "name": cls.name,
            "description": cls.description,
        }
    return jsonify(modes_info)


@bp.route("/api/logs", methods=["GET"])
def api_logs():
    """Get recent log messages."""
    stats = get_stats()
    n = request.args.get("n", 100, type=int)
    return jsonify({"logs": stats.get_logs(n)})


@bp.route("/api/history", methods=["GET"])
def api_history():
    """Get session history."""
    history = get_session_history()
    n = request.args.get("n", 20, type=int)
    return jsonify({"sessions": history[:n]})


@bp.route("/api/version", methods=["GET"])
def api_version():
    """Get application version info."""
    from trafficgoat import __version__
    return jsonify({"version": __version__})


# ---- Socket.IO Events ----

@socketio.on("connect")
def on_connect():
    stats = get_stats()
    if stats:
        emit("stats_update", stats.get_stats())
        for line in stats.get_logs(50):
            emit("log_message", {"message": line})


@socketio.on("request_stats")
def on_request_stats():
    stats = get_stats()
    if stats:
        emit("stats_update", stats.get_stats())
