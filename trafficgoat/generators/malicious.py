"""Malicious traffic pattern generator - port scans, brute force, DDoS patterns."""

import os
import random
import socket
import time

from scapy.all import IP, TCP, UDP, ICMP, send, RandShort

from trafficgoat.generators.base import BaseGenerator
from trafficgoat.config import GeneratorConfig, parse_ports
from trafficgoat.stats import StatsCollector


class MaliciousGenerator(BaseGenerator):
    """Generate malicious traffic patterns for firewall testing."""

    name = "malicious"

    def __init__(self, config: GeneratorConfig, stats: StatsCollector, dry_run: bool = False):
        super().__init__(config, stats, dry_run)
        self.subtype = config.subtype or config.type
        if self.subtype in ("portscan", "bruteforce", "ddos", "amplification"):
            pass
        else:
            self.subtype = "mixed"
        self.name = f"mal:{self.subtype}"
        self.port_list = parse_ports(self.ports)

    def generate(self):
        if self.subtype == "portscan":
            self._port_scan()
        elif self.subtype == "bruteforce":
            self._brute_force()
        elif self.subtype == "ddos":
            self._ddos_patterns()
        elif self.subtype == "amplification":
            self._amplification()
        else:
            self._mixed_malicious()

    def _port_scan(self):
        """Sequential and random port scanning."""
        self.stats.log(f"{self.name}: Port scan on {self.target}")
        scan_types = ["syn", "connect", "fin", "xmas", "null"]
        start = time.time()

        # Sequential scan
        for port in self.port_list:
            if self.should_stop():
                break
            if self.duration > 0 and time.time() - start >= self.duration:
                break
            scan_type = random.choice(scan_types)
            if scan_type == "syn":
                pkt = IP(dst=self.target) / TCP(sport=int(RandShort()), dport=port, flags="S")
                if not self.dry_run:
                    send(pkt, verbose=0)
                self.stats.update(self.name, packets=1, bytes_sent=len(pkt))
            elif scan_type == "connect":
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(1)
                    if not self.dry_run:
                        result = sock.connect_ex((self.target, port))
                    sock.close()
                    self.stats.update(self.name, packets=1, bytes_sent=64, connections=1)
                except (socket.timeout, OSError):
                    self.stats.update(self.name, packets=1, errors=1)
            elif scan_type == "fin":
                pkt = IP(dst=self.target) / TCP(sport=int(RandShort()), dport=port, flags="F")
                if not self.dry_run:
                    send(pkt, verbose=0)
                self.stats.update(self.name, packets=1, bytes_sent=len(pkt))
            elif scan_type == "xmas":
                pkt = IP(dst=self.target) / TCP(sport=int(RandShort()), dport=port, flags="FPU")
                if not self.dry_run:
                    send(pkt, verbose=0)
                self.stats.update(self.name, packets=1, bytes_sent=len(pkt))
            else:  # null
                pkt = IP(dst=self.target) / TCP(sport=int(RandShort()), dport=port, flags="")
                if not self.dry_run:
                    send(pkt, verbose=0)
                self.stats.update(self.name, packets=1, bytes_sent=len(pkt))
            self.throttle()

    def _brute_force(self):
        """Simulate brute force login attempts on common services."""
        self.stats.log(f"{self.name}: Brute force simulation on {self.target}")
        services = [
            (22, "SSH-2.0-OpenSSH_9.0\r\n"),
            (21, "USER admin\r\nPASS {pwd}\r\nQUIT\r\n"),
            (23, "{user}\r\n{pwd}\r\n"),
            (3306, "\x00"),  # MySQL connect attempt
            (5432, "\x00"),  # PostgreSQL connect attempt
        ]
        passwords = [
            "admin", "password", "123456", "root", "letmein",
            "master", "qwerty", "abc123", "monkey", "dragon",
            "111111", "baseball", "shadow", "1234567890", "password1",
        ]
        users = ["admin", "root", "user", "test", "guest", "operator"]
        start = time.time()

        while not self.should_stop():
            if self.duration > 0 and time.time() - start >= self.duration:
                break
            port, template = random.choice(services)
            pwd = random.choice(passwords)
            user = random.choice(users)
            data = template.format(pwd=pwd, user=user).encode()
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                if not self.dry_run:
                    sock.connect((self.target, port))
                    try:
                        sock.recv(1024)  # banner
                    except socket.timeout:
                        pass
                    sock.sendall(data)
                sock.close()
                self.stats.update(self.name, packets=1, bytes_sent=len(data), connections=1)
            except (ConnectionRefusedError, socket.timeout, OSError):
                self.stats.update(self.name, packets=1, errors=1)
            self.throttle()

    def _ddos_patterns(self):
        """Simulate various DDoS patterns."""
        self.stats.log(f"{self.name}: DDoS patterns to {self.target}")
        start = time.time()
        while not self.should_stop():
            if self.duration > 0 and time.time() - start >= self.duration:
                break
            pattern = random.choice(["syn_flood", "udp_flood", "icmp_flood", "mixed"])
            port = random.choice(self.port_list)

            if pattern == "syn_flood":
                for _ in range(10):
                    if self.should_stop():
                        break
                    pkt = IP(dst=self.target) / TCP(
                        sport=int(RandShort()), dport=port, flags="S",
                        seq=random.randint(0, 2**32 - 1)
                    )
                    if not self.dry_run:
                        send(pkt, verbose=0)
                    self.stats.update(self.name, packets=1, bytes_sent=len(pkt))
            elif pattern == "udp_flood":
                for _ in range(10):
                    if self.should_stop():
                        break
                    payload = os.urandom(random.randint(128, 1400))
                    pkt = IP(dst=self.target) / UDP(sport=int(RandShort()), dport=port) / payload
                    if not self.dry_run:
                        send(pkt, verbose=0)
                    self.stats.update(self.name, packets=1, bytes_sent=len(pkt))
            elif pattern == "icmp_flood":
                for _ in range(10):
                    if self.should_stop():
                        break
                    pkt = IP(dst=self.target) / ICMP(type=8) / os.urandom(1024)
                    if not self.dry_run:
                        send(pkt, verbose=0)
                    self.stats.update(self.name, packets=1, bytes_sent=len(pkt))
            else:
                # Mixed burst
                pkts = [
                    IP(dst=self.target) / TCP(sport=int(RandShort()), dport=port, flags="S"),
                    IP(dst=self.target) / UDP(sport=int(RandShort()), dport=port) / os.urandom(256),
                    IP(dst=self.target) / ICMP(type=8) / os.urandom(128),
                ]
                for pkt in pkts:
                    if self.should_stop():
                        break
                    if not self.dry_run:
                        send(pkt, verbose=0)
                    self.stats.update(self.name, packets=1, bytes_sent=len(pkt))
            self.throttle()

    def _amplification(self):
        """Simulate DNS/NTP amplification patterns."""
        self.stats.log(f"{self.name}: Amplification patterns to {self.target}")
        start = time.time()
        while not self.should_stop():
            if self.duration > 0 and time.time() - start >= self.duration:
                break
            # Large DNS queries (ANY type)
            from scapy.all import DNS, DNSQR
            pkt = IP(dst=self.target) / UDP(dport=53) / DNS(
                rd=1, qd=DNSQR(qname=".", qtype="ANY")
            )
            if not self.dry_run:
                send(pkt, verbose=0)
            self.stats.update(self.name, packets=1, bytes_sent=len(pkt))
            self.throttle()

    def _mixed_malicious(self):
        """Alternate between different malicious patterns."""
        self.stats.log(f"{self.name}: Mixed malicious traffic to {self.target}")
        methods = [self._port_scan, self._brute_force, self._ddos_patterns]
        for method in methods:
            if self.should_stop():
                break
            # Run each pattern for a portion of the duration
            original_duration = self.duration
            self.duration = max(original_duration // len(methods), 10)
            method()
            self.duration = original_duration
