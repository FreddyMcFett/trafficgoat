from trafficgoat.generators.tcp import TCPGenerator
from trafficgoat.generators.udp import UDPGenerator
from trafficgoat.generators.icmp import ICMPGenerator
from trafficgoat.generators.http import HTTPGenerator
from trafficgoat.generators.dns import DNSGenerator
from trafficgoat.generators.application import ApplicationGenerator
from trafficgoat.generators.malicious import MaliciousGenerator

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
}

__all__ = [
    "TCPGenerator",
    "UDPGenerator",
    "ICMPGenerator",
    "HTTPGenerator",
    "DNSGenerator",
    "ApplicationGenerator",
    "MaliciousGenerator",
    "GENERATORS",
]
