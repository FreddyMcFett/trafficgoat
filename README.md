# TrafficGoat

Advanced network traffic generator for Linux - designed for firewall testing and log generation.

## Features

- **7 Traffic Generators**: TCP (SYN/connect/flags), UDP, ICMP, HTTP/HTTPS, DNS, Application (FTP/SSH/SMTP), Malicious patterns
- **6 Operating Modes**: stress, scan, mixed, protocol, stealth, custom
- **Dual Interface**: Full CLI + Web UI with real-time dashboard
- **Live Statistics**: Packets/s, bytes/s, per-generator breakdowns via Socket.IO
- **Highly Configurable**: YAML configs, per-generator rate control, port ranges

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
| `stress` | High-volume: TCP SYN + UDP + ICMP + HTTP at max rate |
| `scan` | Port scanning: SYN, FIN, and connect scans |
| `mixed` | Realistic: weighted distribution across all protocols |
| `protocol` | Single protocol with full parameter control |
| `stealth` | Low-and-slow with randomized timing |
| `custom` | User-defined via YAML config file |

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
