"""Protocol mode - single protocol testing."""

from trafficgoat.config import TrafficConfig, GeneratorConfig
from trafficgoat.engine import TrafficEngine
from trafficgoat.stats import StatsCollector
from trafficgoat.generators.tcp import TCPGenerator
from trafficgoat.generators.udp import UDPGenerator
from trafficgoat.generators.icmp import ICMPGenerator
from trafficgoat.generators.http import HTTPGenerator
from trafficgoat.generators.dns import DNSGenerator
from trafficgoat.generators.application import ApplicationGenerator


PROTOCOL_MAP = {
    "tcp": (TCPGenerator, {"subtype": "syn"}),
    "tcp_syn": (TCPGenerator, {"subtype": "syn"}),
    "tcp_connect": (TCPGenerator, {"subtype": "connect"}),
    "udp": (UDPGenerator, {"subtype": "random"}),
    "icmp": (ICMPGenerator, {"subtype": "echo"}),
    "http": (HTTPGenerator, {"methods": ["GET", "POST"]}),
    "dns": (DNSGenerator, {"subtype": "mixed"}),
    "ftp": (ApplicationGenerator, {"subtype": "ftp"}),
    "ssh": (ApplicationGenerator, {"subtype": "ssh"}),
    "smtp": (ApplicationGenerator, {"subtype": "smtp"}),
}


class ProtocolMode:
    """Single protocol testing with full control over parameters."""

    name = "protocol"
    description = "Test a specific protocol (tcp, udp, icmp, http, dns, ftp, ssh, smtp)"

    @staticmethod
    def configure(config: TrafficConfig, engine: TrafficEngine, stats: StatsCollector):
        """Configure engine with a single protocol generator."""
        proto = config.protocol or "tcp"

        if proto not in PROTOCOL_MAP:
            available = ", ".join(sorted(PROTOCOL_MAP.keys()))
            stats.log(f"Unknown protocol '{proto}'. Available: {available}")
            stats.log(f"Falling back to TCP SYN")
            proto = "tcp"

        gen_class, defaults = PROTOCOL_MAP[proto]

        gen_conf = GeneratorConfig(
            type=proto,
            target=config.target,
            ports=config.ports,
            rate=config.rate,
            duration=config.duration,
            **defaults,
        )
        engine.add_generator(gen_class(gen_conf, stats, config.dry_run))
