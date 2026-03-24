"""Stress mode - high volume traffic to stress test firewalls."""

from trafficgoat.config import TrafficConfig, GeneratorConfig
from trafficgoat.engine import TrafficEngine
from trafficgoat.stats import StatsCollector
from trafficgoat.generators.tcp import TCPGenerator
from trafficgoat.generators.udp import UDPGenerator
from trafficgoat.generators.icmp import ICMPGenerator
from trafficgoat.generators.http import HTTPGenerator


class StressMode:
    """High-volume stress test using multiple generators at maximum rate."""

    name = "stress"
    description = "High-volume stress test with TCP SYN, UDP, ICMP, and HTTP traffic"

    @staticmethod
    def configure(config: TrafficConfig, engine: TrafficEngine, stats: StatsCollector):
        """Configure engine with stress-test generators."""
        rate_per_gen = max(config.rate // 4, 10)

        # TCP SYN flood
        tcp_conf = GeneratorConfig(
            type="tcp_syn", subtype="syn",
            target=config.target, ports=config.ports,
            rate=rate_per_gen, duration=config.duration,
        )
        engine.add_generator(TCPGenerator(tcp_conf, stats, config.dry_run))

        # UDP flood
        udp_conf = GeneratorConfig(
            type="udp", subtype="random",
            target=config.target, ports=config.ports,
            rate=rate_per_gen, duration=config.duration,
        )
        engine.add_generator(UDPGenerator(udp_conf, stats, config.dry_run))

        # ICMP flood
        icmp_conf = GeneratorConfig(
            type="icmp", subtype="echo",
            target=config.target,
            rate=rate_per_gen, duration=config.duration,
        )
        engine.add_generator(ICMPGenerator(icmp_conf, stats, config.dry_run))

        # HTTP flood
        http_conf = GeneratorConfig(
            type="http",
            target=config.target, ports=config.ports,
            rate=rate_per_gen, duration=config.duration,
            methods=["GET", "POST"],
        )
        engine.add_generator(HTTPGenerator(http_conf, stats, config.dry_run))
