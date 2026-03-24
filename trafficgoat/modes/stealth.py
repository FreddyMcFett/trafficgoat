"""Stealth mode - low-and-slow attack simulation."""

from trafficgoat.config import TrafficConfig, GeneratorConfig
from trafficgoat.engine import TrafficEngine
from trafficgoat.stats import StatsCollector
from trafficgoat.generators.tcp import TCPGenerator
from trafficgoat.generators.http import HTTPGenerator
from trafficgoat.generators.dns import DNSGenerator


class StealthMode:
    """Low-and-slow attack simulation with randomized delays."""

    name = "stealth"
    description = "Low-and-slow attack simulation with randomized timing and subtle patterns"

    @staticmethod
    def configure(config: TrafficConfig, engine: TrafficEngine, stats: StatsCollector):
        """Configure engine with slow, stealthy generators."""
        # Force low rates for stealth
        stealth_rate = min(config.rate, 5)  # Max 5 pps for stealth

        # Slow SYN scan (1-2 pps)
        tcp_conf = GeneratorConfig(
            type="tcp", subtype="syn",
            target=config.target, ports=config.ports,
            rate=max(stealth_rate // 2, 1), duration=config.duration,
        )
        engine.add_generator(TCPGenerator(tcp_conf, stats, config.dry_run))

        # Slow HTTP requests with varied timing
        http_conf = GeneratorConfig(
            type="http",
            target=config.target, ports=config.ports,
            rate=max(stealth_rate // 3, 1), duration=config.duration,
            methods=["GET"],
        )
        engine.add_generator(HTTPGenerator(http_conf, stats, config.dry_run))

        # Occasional DNS queries
        dns_conf = GeneratorConfig(
            type="dns", subtype="valid",
            target=config.target,
            rate=1, duration=config.duration,
        )
        engine.add_generator(DNSGenerator(dns_conf, stats, config.dry_run))
