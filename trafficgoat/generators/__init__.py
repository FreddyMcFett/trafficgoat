from trafficgoat.generators.tcp import TCPGenerator
from trafficgoat.generators.udp import UDPGenerator
from trafficgoat.generators.icmp import ICMPGenerator
from trafficgoat.generators.http import HTTPGenerator
from trafficgoat.generators.dns import DNSGenerator
from trafficgoat.generators.application import ApplicationGenerator
from trafficgoat.generators.malicious import MaliciousGenerator
from trafficgoat.generators.auto import AutoRawGenerator, AutoHTTPGenerator, AutoTCPConnectGenerator

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
    "GENERATORS",
]
