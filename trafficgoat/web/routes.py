"""Web UI routes and API endpoints."""

import functools
import hmac
import logging
import os
from flask import Blueprint, Response, render_template, request, jsonify, redirect
from flask_socketio import emit, disconnect

from trafficgoat.web.app import (
    socketio, get_engine, get_stats, set_engine,
    get_session_history, start_session, end_session, get_current_session,
    get_engine_lock, get_auth_token, get_settings,
)
from trafficgoat.config import TrafficConfig, ConfigError
from trafficgoat.engine import TrafficEngine
from trafficgoat.modes import MODES
from trafficgoat.safety import check_target, UnsafeTargetError


logger = logging.getLogger(__name__)

bp = Blueprint("main", __name__)


def _extract_token() -> str:
    """Pull the bearer/auth token from the request, in priority order."""
    header = request.headers.get("X-Auth-Token", "")
    if header:
        return header
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return request.args.get("token", "")


def require_auth(fn):
    """Reject requests missing the configured token. No-op if auth disabled."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        expected = get_auth_token()
        if not expected:
            return fn(*args, **kwargs)
        provided = _extract_token()
        if not provided or not hmac.compare_digest(provided, expected):
            return jsonify({"error": "Unauthorized"}), 401
        return fn(*args, **kwargs)
    return wrapper


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
@require_auth
def api_start():
    """Start traffic generation."""
    data = request.get_json(silent=True) or {}
    stats = get_stats()
    settings = get_settings()

    # Single-engine invariant guarded by lock.
    with get_engine_lock():
        engine = get_engine()
        if engine and engine.is_running():
            return jsonify({"error": "Engine already running. Stop it first."}), 400

        if os.geteuid() != 0:
            return jsonify({"error": "TrafficGoat requires root privileges for raw socket access."}), 403

        mode_name = data.get("mode", "stress")
        mode_class = MODES.get(mode_name)
        if not mode_class:
            return jsonify({"error": "Unknown mode"}), 400

        # Build + validate config. Range errors and unsafe targets surface as 400.
        try:
            config = TrafficConfig(
                target=data.get("target", "127.0.0.1"),
                ports=data.get("ports", "80"),
                duration=int(data.get("duration", 60)),
                rate=int(data.get("rate", 100)),
                threads=int(data.get("threads", 4)),
                mode=mode_name,
                protocol=data.get("protocol", ""),
                dry_run=bool(data.get("dry_run", False)),
                allow_public=settings["allow_public"] or bool(data.get("allow_public", False)),
                enable_malicious=settings["enable_malicious"] or bool(data.get("enable_malicious", False)),
            )
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid request parameters"}), 400

        load_level = None
        if mode_name == "auto":
            load_level = data.get("load", "medium")
            if load_level not in ("light", "medium", "heavy"):
                return jsonify({"error": "Invalid load level"}), 400
            config.auto_load = load_level
        elif mode_name == "scan":
            # Scan mode legitimately uses the portscan subtype of MaliciousGenerator.
            # That subtype is not gated, but we still want the generator to
            # see enable_malicious=True so it skips the gate check entirely
            # if its subtype is ever upgraded.
            config.enable_malicious = True

        try:
            config.validate()
        except ConfigError as e:
            return jsonify({"error": str(e)}), 400

        # Target allowlist enforcement.
        try:
            check_target(config.target, allow_public=config.allow_public)
        except UnsafeTargetError as e:
            return jsonify({"error": str(e)}), 400

        stats.reset()
        new_engine = TrafficEngine(config, stats)
        set_engine(new_engine)

        mode_class.configure(config, new_engine, stats)

        # Propagate enable_malicious to any generator configs the mode created.
        for gen in new_engine._generators:
            if hasattr(gen, "config"):
                gen.config.enable_malicious = config.enable_malicious
                if hasattr(gen, "enable_malicious"):
                    gen.enable_malicious = config.enable_malicious

        start_session(
            mode=config.mode,
            target=config.target,
            load_level=load_level,
            dry_run=config.dry_run,
            duration=config.duration,
        )

        try:
            new_engine.start()
        except Exception:
            logger.exception("engine start failed")
            return jsonify({"error": "Engine failed to start"}), 500

    return jsonify({"status": "started", "mode": config.mode, "target": config.target})


@bp.route("/api/stop", methods=["POST"])
@require_auth
def api_stop():
    """Stop traffic generation."""
    with get_engine_lock():
        engine = get_engine()
        if engine and engine.is_running():
            stats_data = engine.get_status()
            engine.stop()
            end_session(stats_data)
            return jsonify({"status": "stopped"})
    return jsonify({"status": "not_running"})


@bp.route("/api/status", methods=["GET"])
@require_auth
def api_status():
    """Get current engine status and stats."""
    engine = get_engine()
    if engine:
        status = engine.get_status()
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
@require_auth
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
@require_auth
def api_logs():
    """Get recent log messages."""
    stats = get_stats()
    n = request.args.get("n", 100, type=int)
    n = max(1, min(n, 1000))
    return jsonify({"logs": stats.get_logs(n)})


@bp.route("/api/history", methods=["GET"])
@require_auth
def api_history():
    """Get session history."""
    history = get_session_history()
    n = request.args.get("n", 20, type=int)
    n = max(1, min(n, 200))
    return jsonify({"sessions": history[:n]})


@bp.route("/api/version", methods=["GET"])
@require_auth
def api_version():
    """Get application version info."""
    from trafficgoat import __version__
    return jsonify({"version": __version__})


def _prometheus_escape(label_value: str) -> str:
    """Escape a label value per Prometheus exposition rules."""
    return label_value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


@bp.route("/metrics", methods=["GET"])
@require_auth
def metrics():
    """Prometheus exposition format. Hand-rolled to avoid a new dependency.

    Counters use monotonic totals (packets, bytes, errors); the engine running
    flag is exposed as a gauge.
    """
    stats = get_stats()
    if stats is None:
        return Response("# stats not initialized\n", mimetype="text/plain; version=0.0.4")
    data = stats.get_stats()

    lines: list[str] = []
    lines.append("# HELP trafficgoat_running 1 if traffic generation is active.")
    lines.append("# TYPE trafficgoat_running gauge")
    lines.append(f"trafficgoat_running {1 if data.get('running') else 0}")

    lines.append("# HELP trafficgoat_packets_total Packets sent per generator.")
    lines.append("# TYPE trafficgoat_packets_total counter")
    lines.append("# HELP trafficgoat_bytes_total Bytes sent per generator.")
    lines.append("# TYPE trafficgoat_bytes_total counter")
    lines.append("# HELP trafficgoat_errors_total Errors per generator.")
    lines.append("# TYPE trafficgoat_errors_total counter")
    lines.append("# HELP trafficgoat_connections_total Successful connections per generator.")
    lines.append("# TYPE trafficgoat_connections_total counter")
    lines.append("# HELP trafficgoat_pps Recent packets-per-second per generator.")
    lines.append("# TYPE trafficgoat_pps gauge")
    lines.append("# HELP trafficgoat_bps Recent bytes-per-second per generator.")
    lines.append("# TYPE trafficgoat_bps gauge")

    for name, gen in (data.get("generators") or {}).items():
        label = f'generator="{_prometheus_escape(name)}"'
        lines.append(f"trafficgoat_packets_total{{{label}}} {gen.get('packets_sent', 0)}")
        lines.append(f"trafficgoat_bytes_total{{{label}}} {gen.get('bytes_sent', 0)}")
        lines.append(f"trafficgoat_errors_total{{{label}}} {gen.get('errors', 0)}")
        lines.append(f"trafficgoat_connections_total{{{label}}} {gen.get('connections', 0)}")
        lines.append(f"trafficgoat_pps{{{label}}} {gen.get('pps', 0)}")
        lines.append(f"trafficgoat_bps{{{label}}} {gen.get('bps', 0)}")

    lines.append("# HELP trafficgoat_total_packets Total packets across all generators.")
    lines.append("# TYPE trafficgoat_total_packets counter")
    lines.append(f"trafficgoat_total_packets {data.get('total_packets', 0)}")
    lines.append("# HELP trafficgoat_total_bytes Total bytes across all generators.")
    lines.append("# TYPE trafficgoat_total_bytes counter")
    lines.append(f"trafficgoat_total_bytes {data.get('total_bytes', 0)}")
    lines.append("# HELP trafficgoat_total_errors Total errors across all generators.")
    lines.append("# TYPE trafficgoat_total_errors counter")
    lines.append(f"trafficgoat_total_errors {data.get('total_errors', 0)}")

    body = "\n".join(lines) + "\n"
    return Response(body, mimetype="text/plain; version=0.0.4")


# ---- Socket.IO Events ----

def _socket_authed() -> bool:
    expected = get_auth_token()
    if not expected:
        return True
    # Token can ride in the connect query (?token=...) or in the Authorization
    # header set by socket.io-client `extraHeaders`.
    provided = request.args.get("token", "") or request.headers.get("X-Auth-Token", "")
    if not provided:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            provided = auth_header[7:]
    return bool(provided) and hmac.compare_digest(provided, expected)


@socketio.on("connect")
def on_connect():
    if not _socket_authed():
        disconnect()
        return False
    stats = get_stats()
    if stats:
        emit("stats_update", stats.get_stats())
        for line in stats.get_logs(50):
            emit("log_message", {"message": line})
    return None


@socketio.on("request_stats")
def on_request_stats():
    if not _socket_authed():
        return
    stats = get_stats()
    if stats:
        emit("stats_update", stats.get_stats())
