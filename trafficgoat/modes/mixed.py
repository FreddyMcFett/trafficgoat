"""Mixed mode - realistic mixed traffic generation."""

from trafficgoat.config import TrafficConfig, GeneratorConfig
from trafficgoat.engine import TrafficEngine
from trafficgoat.stats import StatsCollector
from trafficgoat.generators.tcp import TCPGenerator
from trafficgoat.generators.udp import UDPGenerator
from trafficgoat.generators.icmp import ICMPGenerator
from trafficgoat.generators.http import HTTPGenerator
from trafficgoat.generators.dns import DNSGenerator
from trafficgoat.generators.application import ApplicationGenerator


class MixedMode:
    """Realistic mixed traffic profile simulating real-world network patterns."""

    name = "mixed"
    description = "Realistic mixed traffic with weighted distribution across all protocols"

    @staticmethod
    def configure(config: TrafficConfig, engine: TrafficEngine, stats: StatsCollector):
        """Configure engine with a realistic mix of traffic generators."""
        total_rate = config.rate

        # HTTP (40% of traffic - dominant in real networks)
        http_conf = GeneratorConfig(
            type="http",
            target=config.target, ports="80,443,8080,8443",
            rate=max(int(total_rate * 0.4), 5), duration=config.duration,
            methods=["GET", "POST", "PUT"],
        )
        engine.add_generator(HTTPGenerator(http_conf, stats, config.dry_run))

        # DNS (20% of traffic)
        dns_conf = GeneratorConfig(
            type="dns", subtype="mixed",
            target=config.target,
            rate=max(int(total_rate * 0.2), 5), duration=config.duration,
        )
        engine.add_generator(DNSGenerator(dns_conf, stats, config.dry_run))

        # TCP connections (15%)
        tcp_conf = GeneratorConfig(
            type="tcp", subtype="connect",
            target=config.target, ports=config.ports,
            rate=max(int(total_rate * 0.15), 5), duration=config.duration,
        )
        engine.add_generator(TCPGenerator(tcp_conf, stats, config.dry_run))

        # ICMP (10%)
        icmp_conf = GeneratorConfig(
            type="icmp", subtype="mixed",
            target=config.target,
            rate=max(int(total_rate * 0.1), 5), duration=config.duration,
        )
        engine.add_generator(ICMPGenerator(icmp_conf, stats, config.dry_run))

        # UDP (10%)
        udp_conf = GeneratorConfig(
            type="udp", subtype="random",
            target=config.target, ports="53,123,161,500",
            rate=max(int(total_rate * 0.1), 5), duration=config.duration,
        )
        engine.add_generator(UDPGenerator(udp_conf, stats, config.dry_run))

        # Application layer (5%)
        app_conf = GeneratorConfig(
            type="application", subtype="mixed",
            target=config.target,
            rate=max(int(total_rate * 0.05), 2), duration=config.duration,
        )
        engine.add_generator(ApplicationGenerator(app_conf, stats, config.dry_run))
