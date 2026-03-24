# CLAUDE.md - TrafficGoat Development Guide

## Project Overview

TrafficGoat is an advanced network traffic generator for Linux designed for authorized firewall testing, IDS/IPS validation, and log generation. It generates realistic multi-protocol traffic via CLI or a real-time web dashboard.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt
pip install -e .

# Run web UI (requires root for raw sockets)
sudo trafficgoat web --web-port 8080

# Run CLI auto mode
sudo trafficgoat auto -l heavy -d 120

# Dry run (no packets sent, good for testing)
sudo trafficgoat stress -t 127.0.0.1 --dry-run
```

## Project Structure

```
trafficgoat/
├── trafficgoat/              # Main package
│   ├── __init__.py           # Version (1.0.0)
│   ├── __main__.py           # Entry point
│   ├── cli.py                # CLI argument parsing and execution
│   ├── config.py             # TrafficConfig / GeneratorConfig dataclasses
│   ├── engine.py             # TrafficEngine - orchestrates generators
│   ├── stats.py              # StatsCollector - thread-safe stats aggregation
│   ├── generators/           # Traffic generator implementations
│   │   ├── base.py           # BaseGenerator ABC (threading, throttling)
│   │   ├── tcp.py            # TCP SYN, connect, flag scans
│   │   ├── udp.py            # UDP random, DNS, NTP
│   │   ├── icmp.py           # ICMP echo, mixed types
│   │   ├── http.py           # HTTP/HTTPS requests
│   │   ├── dns.py            # DNS queries (A, AAAA, MX, etc.)
│   │   ├── application.py    # FTP, SSH, SMTP simulation
│   │   ├── malicious.py      # Port scans, brute force, DDoS patterns
│   │   └── auto.py           # Auto-mode: raw, bulk, HTTP, TCP connect
│   ├── modes/                # Traffic generation modes
│   │   ├── stress.py         # High-volume stress test
│   │   ├── scan.py           # Port scanning simulation
│   │   ├── mixed.py          # Realistic mixed traffic
│   │   ├── protocol.py       # Single protocol test
│   │   ├── stealth.py        # Low-and-slow evasion
│   │   ├── custom.py         # YAML-configured
│   │   └── auto.py           # Zero-config multi-destination
│   └── web/                  # Flask + Socket.IO web UI
│       ├── app.py            # Flask factory, Socket.IO setup
│       ├── routes.py         # REST API + Socket.IO events
│       ├── templates/        # Jinja2 HTML templates
│       └── static/           # CSS + JavaScript
├── configs/
│   └── example.yaml          # Example YAML configuration
├── tests/                    # Test suite
├── setup.py                  # Package setup
├── requirements.txt          # Python dependencies
└── install.sh                # Installation script
```

## Architecture

The system follows a layered architecture:

1. **CLI/Web Layer** - User interfaces (argparse CLI or Flask web dashboard)
2. **Engine Layer** - `TrafficEngine` orchestrates generators in background threads
3. **Mode Layer** - Mode classes configure which generators to use and at what rates
4. **Generator Layer** - `BaseGenerator` subclasses produce packets using Scapy/requests/sockets
5. **Stats Layer** - `StatsCollector` aggregates metrics thread-safely, broadcasts via Socket.IO

### Key Data Flow
```
User Input (CLI/Web) -> Mode.configure() -> Engine.add_generator() -> Generator threads
Generator.generate() -> stats.update() -> StatsCollector -> Socket.IO -> Dashboard
```

## Key Files to Understand

- **`engine.py`** - Central orchestrator. Starts/stops generators, runs stats loop.
- **`stats.py`** - Thread-safe statistics. Uses locks, supports callbacks for real-time broadcasting.
- **`generators/base.py`** - Abstract base with `generate()`, `throttle()`, `should_stop()`.
- **`generators/auto.py`** - High-bandwidth generators: `AutoRawGenerator`, `AutoBulkGenerator`, `AutoHTTPGenerator`, `AutoTCPConnectGenerator`.
- **`modes/auto.py`** - Load presets (light/medium/heavy) with tuned rates and batch sizes.
- **`web/app.py`** - Flask factory with Socket.IO for real-time dashboard updates.
- **`web/routes.py`** - REST API (`/api/start`, `/api/stop`, `/api/status`) + Socket.IO events.
- **`web/static/js/app.js`** - Dashboard JS with Socket.IO client + HTTP polling fallback.

## Development Notes

### Adding a New Generator
1. Create a class extending `BaseGenerator` in `generators/`
2. Implement `generate()` method with a loop that checks `self.should_stop()`
3. Call `self.stats.update(self.name, packets=N, bytes_sent=N)` for each batch
4. Call `self.throttle()` for rate limiting
5. Register in `generators/__init__.py` GENERATORS dict

### Adding a New Mode
1. Create a class in `modes/` with `name`, `description`, and `configure()` static method
2. `configure()` creates `GeneratorConfig` instances and adds generators to the engine
3. Register in `modes/__init__.py` MODES dict

### Dashboard Real-Time Updates
- Engine emits stats every ~1 second via `StatsCollector.emit_stats()`
- Socket.IO broadcasts `stats_update` events to all connected clients
- JavaScript also polls `/api/status` every second as a fallback
- Dashboard updates smoothly without manual page refresh

### Bandwidth Optimization
- `AutoBulkGenerator` sends large UDP packets (1400 bytes, near MTU) in batches
- Pre-generated payloads avoid per-packet `os.urandom()` overhead
- Batch sending via `send(packets, verbose=0, inter=0)` maximizes throughput
- Heavy preset: 16 bulk generators x 100000 pps x 2000 batch for massive throughput

### Testing
```bash
# Dry run - tests generation logic without sending packets
sudo trafficgoat auto -l medium --dry-run -d 10

# Web UI dry run - check via browser
sudo trafficgoat web --web-port 8080
# Then start with "Dry Run" checkbox enabled in the dashboard

# Python import test
python -c "from trafficgoat.generators.auto import AutoBulkGenerator; print('OK')"
```

## Dependencies

- **scapy** (>=2.5.0) - Raw packet crafting and sending
- **flask** (>=3.0) - Web framework
- **flask-socketio** (>=5.3) - Real-time WebSocket support
- **eventlet** (>=0.35) - Async I/O backend for Socket.IO
- **requests** (>=2.31) - HTTP client for application-layer traffic
- **pyyaml** (>=6.0) - YAML config parsing

## Important Constraints

- Requires **root privileges** for raw socket access (Scapy)
- Requires **Linux** (raw sockets, Scapy layer 3 sending)
- Python **3.10+** required (type hint syntax)
- Web UI uses **eventlet** async mode for Socket.IO
- This tool is for **authorized security testing only**
