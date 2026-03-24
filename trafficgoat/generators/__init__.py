from trafficgoat.generators.tcp import TCPGenerator
from trafficgoat.generators.udp import UDPGenerator
from trafficgoat.generators.icmp import ICMPGenerator
from trafficgoat.generators.http import HTTPGenerator
from trafficgoat.generators.dns import DNSGenerator
from trafficgoat.generators.application import ApplicationGenerator
from trafficgoat.generators.malicious import MaliciousGenerator
from trafficgoat.generators.auto import (
    AutoRawGenerator, AutoHTTPGenerator, AutoTCPConnectGenerator,
    AutoBulkGenerator, AutoCurlGenerator, AutoSaaSGenerator,
)

GENERATORS = {
    "tcp": TCPGenerator,
    "tcp_syn": TCPGenerator,
    "tcp_connect": TCPGenerator,
    "udp": UDPGenerator,
    "icmp": ICMPGenerator,
    "http": HTTPGenerator,
    "dns": DNSGenerator,
    "ftp": ApplicationGenerator,
    "ssh": ApplicationGenerator,
    "smtp": ApplicationGenerator,
    "application": ApplicationGenerator,
    "malicious": MaliciousGenerator,
    "portscan": MaliciousGenerator,
    "bruteforce": MaliciousGenerator,
    "auto_raw": AutoRawGenerator,
    "auto_http": AutoHTTPGenerator,
    "auto_tcp": AutoTCPConnectGenerator,
    "auto_bulk": AutoBulkGenerator,
    "auto_curl": AutoCurlGenerator,
    "auto_saas": AutoSaaSGenerator,
}

__all__ = [
    "TCPGenerator",
    "UDPGenerator",
    "ICMPGenerator",
    "HTTPGenerator",
    "DNSGenerator",
    "ApplicationGenerator",
    "MaliciousGenerator",
    "AutoRawGenerator",
    "AutoHTTPGenerator",
    "AutoTCPConnectGenerator",
    "AutoBulkGenerator",
    "AutoCurlGenerator",
    "AutoSaaSGenerator",
    "GENERATORS",
]
