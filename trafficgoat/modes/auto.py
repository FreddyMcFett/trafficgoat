"""Auto mode - zero-configuration multi-destination traffic generation.

Generates varied traffic to thousands of destinations using many protocols.
Choose between light, medium, and heavy load presets. No target IP needed.

Protocols covered:
- Raw packets: TCP SYN, UDP, ICMP, DNS, NTP, SNMP, SIP, LDAP, RADIUS,
  MQTT, Syslog, Memcached, Modbus, BGP, QUIC, STUN, Kerberos, NetFlow
- Bulk bandwidth: Large UDP payloads near MTU
- HTTP/HTTPS: Requests to popular websites
- Curl: Heavy parallel HTTP/2 load via curl subprocesses
- SaaS: API traffic to top SaaS platforms
- TCP connect: Full handshakes to varied destinations
"""

from trafficgoat.config import TrafficConfig, GeneratorConfig
from trafficgoat.engine import TrafficEngine
from trafficgoat.stats import StatsCollector
from trafficgoat.generators.auto import (
    AutoRawGenerator,
    AutoHTTPGenerator,
    AutoTCPConnectGenerator,
    AutoBulkGenerator,
    AutoCurlGenerator,
    AutoSaaSGenerator,
    build_destination_pool,
    POPULAR_DOMAINS,
    SAAS_DOMAINS,
)


LOAD_PRESETS = {
    "light": {
        "description": "Light load - ~2000 pps to 500 destinations (18+ protocols)",
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
        "curl_generators": 0,
        "curl_rate": 10,
        "curl_parallel": 4,
        "saas_generators": 1,
        "saas_rate": 10,
    },
    "medium": {
        "description": "Medium load - ~10000 pps to 1500 destinations (18+ protocols)",
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
        "curl_generators": 1,
        "curl_rate": 30,
        "curl_parallel": 8,
        "saas_generators": 2,
        "saas_rate": 25,
    },
    "heavy": {
        "description": "Heavy load - ~50000 pps to 3000 destinations (18+ protocols)",
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
        "curl_generators": 4,
        "curl_rate": 50,
        "curl_parallel": 16,
        "saas_generators": 4,
        "saas_rate": 50,
    },
}


class AutoMode:
    """Zero-configuration multi-destination traffic generation.

    Generates varied traffic to thousands of destinations using 18+ protocols
    including TCP, UDP, ICMP, DNS, NTP, SNMP, SIP, LDAP, RADIUS, MQTT,
    Syslog, Modbus, BGP, QUIC, STUN, Kerberos, NetFlow, HTTP/HTTPS,
    plus SaaS API traffic and curl-based heavy HTTP load.
    No target IP configuration required.
    """

    name = "auto"
    description = "Zero-config multi-destination traffic to 1000s of targets with 18+ protocols including SaaS APIs"

    @staticmethod
    def configure(config: TrafficConfig, engine: TrafficEngine, stats: StatsCollector):
        """Configure engine for auto mode with the specified load level."""
        load = getattr(config, "auto_load", "medium")
        preset = LOAD_PRESETS.get(load, LOAD_PRESETS["medium"])

        stats.log(f"Auto mode: {preset['description']}")

        destinations = build_destination_pool(preset["dest_count"])

        # Raw packet generators (TCP SYN, UDP, ICMP, DNS, NTP + exotic protocols via scapy)
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

        # Curl-based heavy HTTP generators (parallel subprocess curl for max throughput)
        for i in range(preset["curl_generators"]):
            gen_config = GeneratorConfig(
                type="auto_curl",
                target="0.0.0.0",
                rate=preset["curl_rate"],
                duration=config.duration,
            )
            engine.add_generator(AutoCurlGenerator(
                gen_config, stats, config.dry_run,
                domains=POPULAR_DOMAINS + SAAS_DOMAINS,
                parallel=preset["curl_parallel"],
                label=str(i + 1),
            ))

        # SaaS API traffic generators (realistic SaaS application traffic)
        for i in range(preset["saas_generators"]):
            gen_config = GeneratorConfig(
                type="auto_saas",
                target="0.0.0.0",
                rate=preset["saas_rate"],
                duration=config.duration,
            )
            engine.add_generator(AutoSaaSGenerator(
                gen_config, stats, config.dry_run,
                domains=SAAS_DOMAINS,
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
