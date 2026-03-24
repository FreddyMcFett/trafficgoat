"""Scan mode - port scanning simulation."""

from trafficgoat.config import TrafficConfig, GeneratorConfig
from trafficgoat.engine import TrafficEngine
from trafficgoat.stats import StatsCollector
from trafficgoat.generators.tcp import TCPGenerator
from trafficgoat.generators.malicious import MaliciousGenerator


class ScanMode:
    """Port scanning simulation using various scan techniques."""

    name = "scan"
    description = "Port scanning simulation (SYN, connect, FIN, XMAS, NULL scans)"

    @staticmethod
    def configure(config: TrafficConfig, engine: TrafficEngine, stats: StatsCollector):
        """Configure engine with scanning generators."""
        # Default to common ports if not specified
        ports = config.ports if config.ports != "80" else "1-1024"
        rate_per_gen = max(config.rate // 3, 10)

        # SYN scan
        syn_conf = GeneratorConfig(
            type="tcp_syn", subtype="syn",
            target=config.target, ports=ports,
            rate=rate_per_gen, duration=config.duration,
        )
        engine.add_generator(TCPGenerator(syn_conf, stats, config.dry_run))

        # FIN scan
        fin_conf = GeneratorConfig(
            type="tcp", subtype="fin",
            target=config.target, ports=ports,
            rate=rate_per_gen, duration=config.duration,
        )
        engine.add_generator(TCPGenerator(fin_conf, stats, config.dry_run))

        # Full port scan pattern
        scan_conf = GeneratorConfig(
            type="portscan", subtype="portscan",
            target=config.target, ports=ports,
            rate=rate_per_gen, duration=config.duration,
        )
        engine.add_generator(MaliciousGenerator(scan_conf, stats, config.dry_run))
