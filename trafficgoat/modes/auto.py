"""Auto mode - zero-configuration multi-destination traffic generation.

Generates varied traffic to thousands of destinations using many protocols.
Choose between light, medium, and heavy load presets. No target IP needed.
"""

from trafficgoat.config import TrafficConfig, GeneratorConfig
from trafficgoat.engine import TrafficEngine
from trafficgoat.stats import StatsCollector
from trafficgoat.generators.auto import (
    AutoRawGenerator,
    AutoHTTPGenerator,
    AutoTCPConnectGenerator,
    AutoBulkGenerator,
    build_destination_pool,
    POPULAR_DOMAINS,
)


LOAD_PRESETS = {
    "light": {
        "description": "Light load - ~2000 pps to 500 destinations",
        "dest_count": 500,
        "raw_generators": 2,
        "raw_rate": 500,
        "raw_batch": 50,
        "bulk_generators": 4,
        "bulk_rate": 10000,
        "bulk_batch": 500,
        "http_generators": 1,
        "http_rate": 20,
        "tcp_generators": 1,
        "tcp_rate": 20,
    },
    "medium": {
        "description": "Medium load - ~10000 pps to 1500 destinations",
        "dest_count": 1500,
        "raw_generators": 4,
        "raw_rate": 1000,
        "raw_batch": 100,
        "bulk_generators": 8,
        "bulk_rate": 50000,
        "bulk_batch": 1000,
        "http_generators": 2,
        "http_rate": 50,
        "tcp_generators": 2,
        "tcp_rate": 50,
    },
    "heavy": {
        "description": "Heavy load - ~50000 pps to 3000 destinations",
        "dest_count": 3000,
        "raw_generators": 8,
        "raw_rate": 2000,
        "raw_batch": 200,
        "bulk_generators": 16,
        "bulk_rate": 100000,
        "bulk_batch": 2000,
        "http_generators": 4,
        "http_rate": 125,
        "tcp_generators": 4,
        "tcp_rate": 125,
    },
}


class AutoMode:
    """Zero-configuration multi-destination traffic generation.

    Generates varied traffic to thousands of destinations using
    multiple protocols (TCP, UDP, ICMP, DNS, NTP, HTTP).
    No target IP configuration required.
    """

    name = "auto"
    description = "Zero-config multi-destination traffic to 1000s of targets with varied protocols"

    @staticmethod
    def configure(config: TrafficConfig, engine: TrafficEngine, stats: StatsCollector):
        """Configure engine for auto mode with the specified load level."""
        load = getattr(config, "auto_load", "medium")
        preset = LOAD_PRESETS.get(load, LOAD_PRESETS["medium"])

        stats.log(f"Auto mode: {preset['description']}")

        destinations = build_destination_pool(preset["dest_count"])

        # Raw packet generators (TCP SYN, UDP, ICMP, DNS, NTP via scapy)
        for i in range(preset["raw_generators"]):
            gen_config = GeneratorConfig(
                type="auto_raw",
                target="0.0.0.0",
                rate=preset["raw_rate"],
                duration=config.duration,
            )
            engine.add_generator(AutoRawGenerator(
                gen_config, stats, config.dry_run,
                destinations=destinations,
                batch_size=preset["raw_batch"],
                label=str(i + 1),
            ))

        # Bulk bandwidth generators (large UDP packets for high throughput)
        for i in range(preset["bulk_generators"]):
            gen_config = GeneratorConfig(
                type="auto_bulk",
                target="0.0.0.0",
                rate=preset["bulk_rate"],
                duration=config.duration,
            )
            engine.add_generator(AutoBulkGenerator(
                gen_config, stats, config.dry_run,
                destinations=destinations,
                batch_size=preset["bulk_batch"],
                label=str(i + 1),
            ))

        # HTTP generators (real HTTP/HTTPS requests to many websites)
        for i in range(preset["http_generators"]):
            gen_config = GeneratorConfig(
                type="auto_http",
                target="0.0.0.0",
                rate=preset["http_rate"],
                duration=config.duration,
            )
            engine.add_generator(AutoHTTPGenerator(
                gen_config, stats, config.dry_run,
                domains=POPULAR_DOMAINS,
                label=str(i + 1),
            ))

        # TCP connect generators (full TCP handshake to many destinations)
        for i in range(preset["tcp_generators"]):
            gen_config = GeneratorConfig(
                type="auto_tcp",
                target="0.0.0.0",
                rate=preset["tcp_rate"],
                duration=config.duration,
            )
            engine.add_generator(AutoTCPConnectGenerator(
                gen_config, stats, config.dry_run,
                destinations=destinations,
                label=str(i + 1),
            ))
