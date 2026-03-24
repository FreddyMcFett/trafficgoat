"""Web UI routes and API endpoints."""

import os
from flask import Blueprint, render_template, request, jsonify
from flask_socketio import emit

from trafficgoat.web.app import socketio, get_engine, get_stats, set_engine
from trafficgoat.config import TrafficConfig
from trafficgoat.engine import TrafficEngine
from trafficgoat.modes import MODES

bp = Blueprint("main", __name__)


@bp.route("/")
def dashboard():
    return render_template("dashboard.html")


@bp.route("/modes")
def modes_page():
    modes_info = {name: cls.description for name, cls in MODES.items()}
    return render_template("modes.html", modes=modes_info)


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

    config = TrafficConfig(
        target=data.get("target", "127.0.0.1"),
        ports=data.get("ports", "80"),
        duration=int(data.get("duration", 60)),
        rate=int(data.get("rate", 100)),
        threads=int(data.get("threads", 4)),
        mode=data.get("mode", "stress"),
        protocol=data.get("protocol", ""),
        dry_run=data.get("dry_run", False),
    )

    stats.reset()
    new_engine = TrafficEngine(config, stats)
    set_engine(new_engine)

    mode_class = MODES.get(config.mode)
    if not mode_class:
        return jsonify({"error": f"Unknown mode: {config.mode}"}), 400

    mode_class.configure(config, new_engine, stats)
    new_engine.start()

    return jsonify({"status": "started", "mode": config.mode, "target": config.target})


@bp.route("/api/stop", methods=["POST"])
def api_stop():
    """Stop traffic generation."""
    engine = get_engine()
    if engine and engine.is_running():
        engine.stop()
        return jsonify({"status": "stopped"})
    return jsonify({"status": "not_running"})


@bp.route("/api/status", methods=["GET"])
def api_status():
    """Get current engine status and stats."""
    engine = get_engine()
    stats = get_stats()
    if engine:
        return jsonify(engine.get_status())
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
