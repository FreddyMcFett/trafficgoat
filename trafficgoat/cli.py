"""CLI interface for TrafficGoat."""

import argparse
import os
import sys
import time

from trafficgoat import __version__
from trafficgoat.config import TrafficConfig
from trafficgoat.engine import TrafficEngine
from trafficgoat.stats import StatsCollector
from trafficgoat.modes import MODES


BANNER = r"""
  _____ _____  ___  _____ _____ _____ _____  _____ _____  ___  _____
 |_   _| ___ \/ _ \|  ___|  ___|_   _/  __ \|  __ \  _  |/ _ \|_   _|
   | | | |_/ / /_\ \ |_  | |_    | | | /  \/| |  \/ | | / /_\ \ | |
   | | |    /|  _  |  _| |  _|   | | | |    | | __| | | |  _  | | |
   | | | |\ \| | | | |   | |    _| |_| \__/\| |_\ \ \_/ / | | | | |
   \_/ \_| \_\_| |_\_|   \_|    \___/ \____/ \____/\___/\_| |_/ \_/
"""


def format_bytes(n: int) -> str:
    """Format bytes into human-readable string."""
    for unit in ("B", "KB", "MB", "GB"):
        if abs(n) < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def print_stats(stats_data: dict, quiet: bool = False):
    """Print live stats to terminal."""
    if quiet:
        return
    sys.stdout.write("\r\033[K")
    sys.stdout.write(
        f"  Packets: {stats_data['total_packets']:>8,}  |  "
        f"Rate: {stats_data['total_pps']:>8,.1f} pps  |  "
        f"Data: {format_bytes(stats_data['total_bytes']):>10}  |  "
        f"Errors: {stats_data['total_errors']:>6}  |  "
        f"Time: {stats_data['elapsed']:>6.1f}s"
    )
    sys.stdout.flush()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trafficgoat",
        description="TrafficGoat - Advanced network traffic generator for firewall testing and log generation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  sudo trafficgoat stress -t 192.168.1.1 -d 60 -r 500
  sudo trafficgoat scan -t 10.0.0.1 -p 1-1024
  sudo trafficgoat protocol -t 192.168.1.1 --protocol icmp -d 30
  sudo trafficgoat mixed -t 192.168.1.1 -r 200 -d 120
  sudo trafficgoat stealth -t 192.168.1.1 -d 300
  sudo trafficgoat custom -t 192.168.1.1 -c config.yaml
  sudo trafficgoat web --web-port 8080
        """,
    )

    parser.add_argument("--version", action="version", version=f"trafficgoat {__version__}")

    subparsers = parser.add_subparsers(dest="mode", help="Traffic generation mode")

    # Common arguments for all modes
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("-t", "--target", required=True, help="Target IP address or hostname")
    common.add_argument("-p", "--ports", default="80", help="Ports: single, range (1-1024), or comma-separated (default: 80)")
    common.add_argument("-d", "--duration", type=int, default=60, help="Duration in seconds (default: 60)")
    common.add_argument("-r", "--rate", type=int, default=100, help="Packets per second (default: 100)")
    common.add_argument("--threads", type=int, default=4, help="Worker threads (default: 4)")
    common.add_argument("-i", "--interface", help="Network interface to use")
    common.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    common.add_argument("-q", "--quiet", action="store_true", help="Minimal output")
    common.add_argument("--dry-run", action="store_true", help="Show what would be generated without sending")

    # Mode subcommands
    subparsers.add_parser("stress", parents=[common], help="High-volume stress test")
    subparsers.add_parser("scan", parents=[common], help="Port scanning simulation")
    subparsers.add_parser("mixed", parents=[common], help="Realistic mixed traffic")

    proto_parser = subparsers.add_parser("protocol", parents=[common], help="Single protocol test")
    proto_parser.add_argument(
        "--protocol", default="tcp",
        choices=["tcp", "tcp_syn", "tcp_connect", "udp", "icmp", "http", "dns", "ftp", "ssh", "smtp"],
        help="Protocol to test (default: tcp)",
    )

    subparsers.add_parser("stealth", parents=[common], help="Low-and-slow attack simulation")

    custom_parser = subparsers.add_parser("custom", parents=[common], help="Custom config from YAML")
    custom_parser.add_argument("-c", "--config", required=True, help="YAML configuration file")

    # Web UI mode
    web_parser = subparsers.add_parser("web", help="Start the Web UI")
    web_parser.add_argument("--host", default="0.0.0.0", help="Bind address (default: 0.0.0.0)")
    web_parser.add_argument("--web-port", type=int, default=8080, help="Web UI port (default: 8080)")
    web_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    return parser


def run_cli(args):
    """Run traffic generation in CLI mode."""
    config = TrafficConfig.from_args(args)
    stats = StatsCollector()

    # Setup live stats printing
    if not config.quiet:
        stats.on_stats(lambda s: print_stats(s, config.quiet))
    if config.verbose:
        stats.on_log(lambda msg: print(f"\n  {msg}"))

    mode_class = MODES.get(config.mode)
    if not mode_class:
        print(f"[!] Unknown mode: {config.mode}")
        sys.exit(1)

    engine = TrafficEngine(config, stats)
    mode_class.configure(config, engine, stats)

    if not config.quiet:
        print(f"\n  Mode: {mode_class.name} - {mode_class.description}")
        print(f"  Target: {config.target}")
        print(f"  Duration: {config.duration}s | Rate: {config.rate} pps | Dry-run: {config.dry_run}")
        print(f"  {'=' * 70}")
        print()

    engine.start()
    engine.wait()

    # Final stats
    final = stats.get_stats()
    if not config.quiet:
        print("\n")
        print(f"  {'=' * 70}")
        print(f"  Final Results:")
        print(f"  Packets sent:  {final['total_packets']:>12,}")
        print(f"  Data sent:     {format_bytes(final['total_bytes']):>12}")
        print(f"  Errors:        {final['total_errors']:>12,}")
        print(f"  Duration:      {final['elapsed']:>11.1f}s")
        print(f"  Avg rate:      {final['total_pps']:>11.1f} pps")
        print(f"  {'=' * 70}")


def run_web(args):
    """Start the Web UI."""
    from trafficgoat.web.app import create_app, socketio

    host = args.host
    port = args.web_port

    if not args.verbose:
        print(BANNER)
    print(f"  Starting TrafficGoat Web UI on http://{host}:{port}")
    print(f"  Press Ctrl+C to stop\n")

    app = create_app()
    socketio.run(app, host=host, port=port, debug=args.verbose, allow_unsafe_werkzeug=True)


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.mode:
        print(BANNER)
        parser.print_help()
        sys.exit(0)

    # Check root for non-web modes (raw sockets need root)
    if args.mode != "web" and os.geteuid() != 0:
        print("[!] TrafficGoat requires root privileges for raw socket access.")
        print("[!] Run with: sudo trafficgoat ...")
        sys.exit(1)

    if args.mode == "web":
        run_web(args)
    else:
        if not getattr(args, "quiet", False):
            print(BANNER)
        run_cli(args)


if __name__ == "__main__":
    main()
