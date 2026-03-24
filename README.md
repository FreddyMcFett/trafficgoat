# TrafficGoat

Advanced network traffic generator for Linux - designed for firewall testing and log generation.

## Features

- **10 Traffic Generators**: TCP (SYN/connect/flags), UDP, ICMP, HTTP/HTTPS, DNS, Application (FTP/SSH/SMTP), Malicious patterns, Bulk bandwidth
- **7 Operating Modes**: auto, stress, scan, mixed, protocol, stealth, custom
- **Dual Interface**: Full CLI + Web UI with real-time dashboard
- **Live Statistics**: Packets/s, bytes/s, per-generator breakdowns via Socket.IO (auto-updates every second)
- **High Bandwidth**: Bulk data generators produce gigabytes of traffic using large UDP payloads
- **Highly Configurable**: YAML configs, per-generator rate control, port ranges

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           TrafficGoat                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────┐    ┌──────────────────────────────────────────┐   │
│  │   CLI Interface  │    │           Web UI (Flask)                 │   │
│  │   (argparse)     │    │  ┌──────────┐  ┌──────────────────┐    │   │
│  │                  │    │  │ REST API  │  │   Socket.IO      │    │   │
│  │  trafficgoat     │    │  │ /api/*    │  │   (real-time)    │    │   │
│  │  auto/stress/..  │    │  └────┬─────┘  └────────┬─────────┘    │   │
│  └────────┬─────────┘    └───────┼─────────────────┼──────────────┘   │
│           │                      │                 │                    │
│           ▼                      ▼                 ▲                    │
│  ┌────────────────────────────────────┐   ┌───────┴──────────────┐    │
│  │         TrafficEngine              │   │   StatsCollector     │    │
│  │  ┌─────────────────────────────┐   │   │                      │    │
│  │  │    Mode Layer               │   │   │  - Thread-safe locks │    │
│  │  │  auto│stress│scan│mixed│... │   │   │  - Per-generator     │    │
│  │  │  configure(config, engine)  │   │   │    aggregation       │    │
│  │  └─────────────┬───────────────┘   │   │  - 1s emit loop     │    │
│  │                │                    │   │  - Log broadcasting  │    │
│  │                ▼                    │   └───────▲──────────────┘    │
│  │  ┌─────────────────────────────┐   │           │                    │
│  │  │  Generator Threads          │   │           │                    │
│  │  │                             │   │           │                    │
│  │  │  ┌───────┐ ┌───────┐       │   │    stats.update()             │
│  │  │  │TCP/SYN│ │  UDP  │       │───┼───────────┘                    │
│  │  │  └───────┘ └───────┘       │   │                                │
│  │  │  ┌───────┐ ┌───────┐       │   │                                │
│  │  │  │ ICMP  │ │ HTTP  │       │   │                                │
│  │  │  └───────┘ └───────┘       │   │                                │
│  │  │  ┌───────┐ ┌───────┐       │   │                                │
│  │  │  │  DNS  │ │ Bulk  │       │   │                                │
│  │  │  └───────┘ └───────┘       │   │                                │
│  │  │  ┌───────┐ ┌───────┐       │   │                                │
│  │  │  │App/FTP│ │Malici.│       │   │                                │
│  │  │  └───────┘ └───────┘       │   │                                │
│  │  └─────────────────────────────┘   │                                │
│  └────────────────────────────────────┘                                │
│                    │                                                     │
│                    ▼                                                     │
│  ┌─────────────────────────────────────┐                               │
│  │          Network (Scapy/Sockets)     │                               │
│  │  Raw packets │ HTTP requests │ TCP   │                               │
│  └─────────────────────────────────────┘                               │
└─────────────────────────────────────────────────────────────────────────┘

Data Flow:
  User Input → Mode.configure() → Engine.add_generator() → Generator threads
  Generator.generate() → stats.update() → StatsCollector → Socket.IO → Dashboard
```

## Requirements

- Linux (Debian/Ubuntu)
- Python 3.10+
- Root privileges (raw sockets)

## Installation

```bash
git clone <repo-url> && cd trafficgoat
sudo ./install.sh
```

Or manually:

```bash
pip install -r requirements.txt
pip install -e .
```

## CLI Usage

```bash
# Auto mode - zero-config, high bandwidth to thousands of destinations
sudo trafficgoat auto -l heavy -d 300
sudo trafficgoat auto -l medium -d 120
sudo trafficgoat auto -l light -d 60

# Stress test - all traffic types at high rate
sudo trafficgoat stress -t 192.168.1.1 -d 60 -r 500

# Port scan simulation
sudo trafficgoat scan -t 10.0.0.1 -p 1-1024

# Realistic mixed traffic
sudo trafficgoat mixed -t 192.168.1.1 -r 200 -d 120

# Single protocol test
sudo trafficgoat protocol -t 192.168.1.1 --protocol icmp -d 30

# Low-and-slow stealth test
sudo trafficgoat stealth -t 192.168.1.1 -d 300

# Custom config
sudo trafficgoat custom -t 192.168.1.1 -c configs/example.yaml

# Dry run (no packets sent)
sudo trafficgoat stress -t 192.168.1.1 --dry-run
```

## Web UI

```bash
sudo trafficgoat web --web-port 8080
```

Then open `http://localhost:8080` in your browser. The Web UI provides:

- **Dashboard**: Real-time statistics, start/stop controls, per-generator breakdown
- **Modes**: Visual overview of all available modes
- **Logs**: Live log streaming with auto-scroll

## Modes

| Mode | Description |
|------|-------------|
| `auto` | Zero-config: multi-destination traffic to 1000s of targets with bulk bandwidth |
| `stress` | High-volume: TCP SYN + UDP + ICMP + HTTP at max rate |
| `scan` | Port scanning: SYN, FIN, and connect scans |
| `mixed` | Realistic: weighted distribution across all protocols |
| `protocol` | Single protocol with full parameter control |
| `stealth` | Low-and-slow with randomized timing |
| `custom` | User-defined via YAML config file |

### Auto Mode Load Presets

| Level | PPS | Destinations | Bulk Generators | Batch Size |
|-------|-----|-------------|-----------------|------------|
| `light` | ~2,000 | 500 | 4 | 500 |
| `medium` | ~10,000 | 1,500 | 8 | 1,000 |
| `heavy` | ~50,000 | 3,000 | 16 | 2,000 |

Each bulk generator sends 1,400-byte UDP packets in large batches for maximum bandwidth. A 5-minute heavy run generates multiple gigabytes of traffic.

## Custom Configuration

See `configs/example.yaml` for a full example:

```yaml
target: "192.168.1.1"
duration: 120
generators:
  - type: tcp_syn
    ports: "80,443"
    rate: 200
    weight: 0.4
  - type: http
    ports: "80"
    rate: 100
    methods: [GET, POST]
    weight: 0.3
  - type: dns
    subtype: mixed
    rate: 50
    weight: 0.3
```

## CLI Options

```
Global Options:
  -t, --target       Target IP/hostname (required)
  -p, --ports        Port(s): single, range, comma-separated (default: 80)
  -d, --duration     Duration in seconds (default: 60)
  -r, --rate         Packets per second (default: 100)
  --threads          Worker threads (default: 4)
  -i, --interface    Network interface
  -v, --verbose      Verbose output
  -q, --quiet        Minimal output
  --dry-run          Simulate without sending packets
```

## Disclaimer

This tool is intended for **authorized security testing, firewall validation, and log generation** only. Only use against systems you own or have explicit permission to test. Unauthorized use against third-party systems is illegal.
