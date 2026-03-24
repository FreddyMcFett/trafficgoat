"""Auto traffic generators - multi-destination, multi-protocol for load generation.

These generators send varied traffic to thousands of destinations across many
protocols without requiring any target configuration. Designed for high
performance using batch packet sending via scapy.
"""

import os
import random
import socket
import time

from scapy.all import IP, TCP, UDP, ICMP, DNS, DNSQR, NTP, send

from trafficgoat.generators.base import BaseGenerator
from trafficgoat.config import GeneratorConfig
from trafficgoat.stats import StatsCollector


# ---------------------------------------------------------------------------
# Destination pools
# ---------------------------------------------------------------------------

POPULAR_DOMAINS = [
    # Top websites
    "google.com", "youtube.com", "facebook.com", "amazon.com", "wikipedia.org",
    "twitter.com", "instagram.com", "linkedin.com", "reddit.com", "netflix.com",
    "microsoft.com", "apple.com", "github.com", "stackoverflow.com", "yahoo.com",
    "bing.com", "twitch.tv", "cnn.com", "bbc.com", "nytimes.com",
    "cloudflare.com", "dropbox.com", "spotify.com", "zoom.us", "slack.com",
    "discord.com", "medium.com", "quora.com", "ebay.com", "paypal.com",
    "stripe.com", "shopify.com", "wordpress.com", "tumblr.com", "pinterest.com",
    # Developer / infra
    "docker.com", "npmjs.com", "pypi.org", "rubygems.org", "kernel.org",
    "debian.org", "ubuntu.com", "fedoraproject.org", "archlinux.org",
    "mozilla.org", "apache.org", "nginx.org", "php.net", "python.org",
    "golang.org", "rust-lang.org", "nodejs.org", "vuejs.org", "angular.io",
    "jquery.com", "gitlab.com", "bitbucket.org", "heroku.com",
    "digitalocean.com", "linode.com", "vultr.com", "ovh.com", "hetzner.com",
    "akamai.com", "fastly.com",
    # Productivity / SaaS
    "office.com", "live.com", "outlook.com", "icloud.com", "protonmail.com",
    "duckduckgo.com", "brave.com", "opera.com", "whatsapp.com", "telegram.org",
    "signal.org", "skype.com", "trello.com", "asana.com", "notion.so",
    "figma.com", "canva.com", "adobe.com", "salesforce.com", "hubspot.com",
    "zendesk.com", "datadog.com", "newrelic.com", "splunk.com", "grafana.com",
    "elastic.co", "mongodb.com", "redis.io", "postgresql.org", "mysql.com",
    "terraform.io", "kubernetes.io", "prometheus.io", "envoyproxy.io",
    # Media / entertainment
    "hulu.com", "disneyplus.com", "hbomax.com", "peacocktv.com",
    "soundcloud.com", "bandcamp.com", "vimeo.com", "dailymotion.com",
    "flickr.com", "deviantart.com", "behance.net", "dribbble.com",
    # E-commerce / finance
    "alibaba.com", "aliexpress.com", "wish.com", "etsy.com", "walmart.com",
    "target.com", "bestbuy.com", "newegg.com", "costco.com",
    "chase.com", "bankofamerica.com", "wellsfargo.com", "citigroup.com",
    "coinbase.com", "binance.com", "kraken.com",
    # News / information
    "washingtonpost.com", "theguardian.com", "reuters.com", "apnews.com",
    "bloomberg.com", "forbes.com", "wired.com", "techcrunch.com",
    "arstechnica.com", "theverge.com", "engadget.com", "mashable.com",
    # Education / reference
    "khanacademy.org", "coursera.org", "edx.org", "udemy.com",
    "w3schools.com", "mdn.dev", "docs.python.org", "docs.oracle.com",
    # Government / org
    "nasa.gov", "nih.gov", "cdc.gov", "who.int", "un.org",
    "europa.eu", "gov.uk", "canada.ca",
    # Misc
    "craigslist.org", "yelp.com", "tripadvisor.com", "booking.com",
    "airbnb.com", "uber.com", "lyft.com", "doordash.com", "grubhub.com",
    "zillow.com", "realtor.com", "weather.com", "accuweather.com",
]

PUBLIC_DNS_SERVERS = [
    "8.8.8.8", "8.8.4.4",                          # Google
    "1.1.1.1", "1.0.0.1",                          # Cloudflare
    "9.9.9.9", "149.112.112.112",                  # Quad9
    "208.67.222.222", "208.67.220.220",             # OpenDNS
    "64.6.64.6", "64.6.65.6",                      # Verisign
    "76.76.2.0", "76.76.10.0",                     # Control D
    "94.140.14.14", "94.140.15.15",                # AdGuard
    "185.228.168.9", "185.228.169.9",              # CleanBrowsing
    "77.88.8.8", "77.88.8.1",                      # Yandex
    "156.154.70.1", "156.154.71.1",                # Neustar
]

PUBLIC_NTP_SERVERS = [
    "129.6.15.28", "129.6.15.29",                  # NIST
    "132.163.97.1", "132.163.97.2",                # NIST
    "132.163.96.1", "132.163.96.2",                # NIST
    "128.138.141.172",                              # University of Colorado
    "198.60.22.240",                                # Utah
    "64.113.32.5",                                  # Midwest
]

WELL_KNOWN_IPS = [
    # Google
    "142.250.80.46", "142.250.80.47", "142.250.185.206", "172.217.14.206",
    "216.58.214.206", "142.251.33.174", "142.251.40.46",
    # Cloudflare
    "104.16.132.229", "104.16.133.229", "104.18.32.7", "104.18.33.7",
    "172.67.182.31", "104.21.234.56",
    # Amazon
    "52.94.236.248", "54.239.28.85", "176.32.103.205",
    "205.251.242.103", "52.46.139.168",
    # Microsoft
    "20.70.246.20", "13.107.42.14", "204.79.197.200",
    "20.189.173.1", "52.168.112.66",
    # Facebook/Meta
    "157.240.1.35", "157.240.3.35", "31.13.65.36",
    "31.13.66.35", "157.240.12.35",
    # Others
    "151.101.1.140", "151.101.65.140",              # Reddit
    "104.244.42.65", "104.244.42.193",              # Twitter
    "140.82.121.4", "140.82.121.3",                 # GitHub
    "199.232.69.194", "185.199.108.133",            # GitHub Pages
    "93.184.216.34",                                 # example.com
    "208.80.154.224",                                # Wikipedia
    "198.35.26.96",                                  # Wikipedia
    "103.102.166.224",                               # Cloudflare
    "151.101.0.176", "151.101.128.176",             # Various CDN
]

# Ports
TCP_PORTS = [
    21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443, 445,
    465, 587, 636, 993, 995, 1433, 1521, 2049, 3306, 3389,
    5432, 5900, 5985, 6379, 8080, 8443, 8888, 9090, 9200, 9300,
    27017, 6443, 2379, 10250, 11211, 15672, 5672, 4369,
]

UDP_PORTS = [
    53, 67, 68, 69, 123, 137, 138, 161, 162, 500, 514,
    520, 1194, 1900, 4500, 5353, 5060, 5061, 33434,
]

DNS_QUERY_TYPES = ["A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA", "PTR", "SRV"]

HTTP_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Edge/120.0.0.0",
    "curl/8.4.0",
    "python-requests/2.31.0",
    "Googlebot/2.1 (+http://www.google.com/bot.html)",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
    "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (compatible; Bingbot/2.0; +http://www.bing.com/bingbot.htm)",
    "Mozilla/5.0 (compatible; YandexBot/3.0; +http://yandex.com/bots)",
]

HTTP_PATHS = [
    "/", "/index.html", "/login", "/api/v1/status", "/api/health",
    "/robots.txt", "/sitemap.xml", "/favicon.ico", "/.well-known/security.txt",
    "/about", "/contact", "/search?q=test", "/api/v1/users",
    "/wp-admin", "/wp-login.php", "/.env", "/config", "/admin",
    "/api/v1/data", "/dashboard", "/static/js/app.js", "/assets/main.css",
    "/graphql", "/api/v2/query", "/health", "/metrics", "/status",
]


def _generate_random_public_ip():
    """Generate a random routable public IP address."""
    while True:
        a = random.randint(1, 223)
        b = random.randint(0, 255)
        c = random.randint(0, 255)
        d = random.randint(1, 254)
        if a == 10:
            continue
        if a == 127:
            continue
        if a == 172 and 16 <= b <= 31:
            continue
        if a == 192 and b == 168:
            continue
        if a == 169 and b == 254:
            continue
        if a == 0 or a >= 224:
            continue
        if a == 100 and 64 <= b <= 127:
            continue  # CGNAT
        return f"{a}.{b}.{c}.{d}"


def build_destination_pool(count=1000):
    """Build a large pool of destination IPs combining known and random IPs."""
    pool = list(set(PUBLIC_DNS_SERVERS + PUBLIC_NTP_SERVERS + WELL_KNOWN_IPS))
    seen = set(pool)
    while len(pool) < count:
        ip = _generate_random_public_ip()
        if ip not in seen:
            seen.add(ip)
            pool.append(ip)
    random.shuffle(pool)
    return pool


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------

class AutoRawGenerator(BaseGenerator):
    """High-performance multi-destination raw packet generator.

    Sends TCP SYN, UDP, ICMP, DNS, and NTP packets in batches to a large pool
    of destinations with high protocol and port variation. Uses large payloads
    to maximize bandwidth throughput.
    """

    name = "auto:raw"

    def __init__(self, config: GeneratorConfig, stats: StatsCollector,
                 dry_run: bool = False, destinations: list[str] | None = None,
                 batch_size: int = 10, label: str = ""):
        super().__init__(config, stats, dry_run)
        self.destinations = destinations or build_destination_pool()
        self.batch_size = batch_size
        # Adjust delay for batch sending: send batch_size packets per cycle
        self._delay = self.batch_size / max(self.rate, 1)
        if label:
            self.name = f"auto:raw:{label}"

    def generate(self):
        self.stats.log(
            f"{self.name}: Multi-target raw traffic to "
            f"{len(self.destinations)} destinations at {self.rate} pps"
        )
        start = time.time()

        protocols = ['tcp_syn', 'udp', 'icmp', 'dns', 'ntp']
        weights = [0.25, 0.35, 0.15, 0.15, 0.10]

        while not self.should_stop():
            if self.duration > 0 and time.time() - start >= self.duration:
                break

            packets = []
            for _ in range(self.batch_size):
                proto = random.choices(protocols, weights=weights, k=1)[0]
                dst = random.choice(self.destinations)
                pkt = self._build_packet(dst, proto)
                if pkt is not None:
                    packets.append(pkt)

            if packets:
                if not self.dry_run:
                    try:
                        send(packets, verbose=0, inter=0)
                    except Exception:
                        self.stats.update(self.name, errors=1)
                total_bytes = sum(len(p) for p in packets)
                self.stats.update(self.name, packets=len(packets), bytes_sent=total_bytes)

            self.throttle()

    def _build_packet(self, dst, proto):
        """Build a single packet for the given destination and protocol.

        Uses large payloads (up to MTU ~1400 bytes) to maximize bandwidth.
        """
        try:
            if proto == 'tcp_syn':
                # TCP SYN with options padding for larger packets
                return IP(dst=dst) / TCP(
                    sport=random.randint(1024, 65535),
                    dport=random.choice(TCP_PORTS),
                    flags="S",
                    seq=random.randint(0, 2**32 - 1),
                    options=[('MSS', 1460), ('NOP', None), ('WScale', 7)],
                )
            elif proto == 'udp':
                # Large UDP payloads - near MTU for maximum bandwidth
                payload = os.urandom(random.randint(512, 1400))
                return IP(dst=dst) / UDP(
                    sport=random.randint(1024, 65535),
                    dport=random.choice(UDP_PORTS),
                ) / payload
            elif proto == 'icmp':
                # Large ICMP payloads
                payload = os.urandom(random.randint(256, 1400))
                return IP(dst=dst) / ICMP(
                    type=8, code=0,
                    id=random.randint(1, 65535),
                    seq=random.randint(0, 65535),
                ) / payload
            elif proto == 'dns':
                domain = random.choice(POPULAR_DOMAINS)
                qtype = random.choice(DNS_QUERY_TYPES[:5])
                return IP(dst=random.choice(PUBLIC_DNS_SERVERS)) / UDP(
                    dport=53, sport=random.randint(1024, 65535),
                ) / DNS(
                    id=random.randint(0, 65535), rd=1,
                    qd=DNSQR(qname=domain, qtype=qtype),
                )
            elif proto == 'ntp':
                return IP(dst=random.choice(PUBLIC_NTP_SERVERS)) / UDP(
                    dport=123
                ) / NTP(version=3)
        except Exception:
            return None
        return None


class AutoBulkGenerator(BaseGenerator):
    """High-bandwidth bulk data generator using large UDP packets.

    Sends maximum-size UDP packets (1400 bytes payload, near MTU) in large
    batches to generate gigabytes of traffic quickly. Designed for bandwidth
    testing rather than protocol variety.
    """

    name = "auto:bulk"

    def __init__(self, config: GeneratorConfig, stats: StatsCollector,
                 dry_run: bool = False, destinations: list[str] | None = None,
                 batch_size: int = 50, label: str = ""):
        super().__init__(config, stats, dry_run)
        self.destinations = destinations or build_destination_pool()
        self.batch_size = batch_size
        self._delay = self.batch_size / max(self.rate, 1)
        if label:
            self.name = f"auto:bulk:{label}"
        # Pre-generate payloads for speed (avoid per-packet urandom overhead)
        self._payloads = [os.urandom(1400) for _ in range(64)]

    def generate(self):
        self.stats.log(
            f"{self.name}: Bulk bandwidth to "
            f"{len(self.destinations)} destinations at {self.rate} pps "
            f"(batch={self.batch_size}, ~{self.batch_size * 1400} bytes/batch)"
        )
        start = time.time()

        while not self.should_stop():
            if self.duration > 0 and time.time() - start >= self.duration:
                break

            packets = []
            for _ in range(self.batch_size):
                dst = random.choice(self.destinations)
                port = random.choice(UDP_PORTS)
                payload = random.choice(self._payloads)
                pkt = IP(dst=dst) / UDP(
                    sport=random.randint(1024, 65535),
                    dport=port,
                ) / payload
                packets.append(pkt)

            if not self.dry_run:
                try:
                    send(packets, verbose=0, inter=0)
                except Exception:
                    self.stats.update(self.name, errors=1)
            total_bytes = sum(len(p) for p in packets)
            self.stats.update(self.name, packets=len(packets), bytes_sent=total_bytes)

            self.throttle()


class AutoHTTPGenerator(BaseGenerator):
    """Multi-destination HTTP generator for auto mode.

    Makes HTTP/HTTPS requests to a large pool of real websites with varied
    methods, user agents, and paths.
    """

    name = "auto:http"

    def __init__(self, config: GeneratorConfig, stats: StatsCollector,
                 dry_run: bool = False, domains: list[str] | None = None,
                 label: str = ""):
        super().__init__(config, stats, dry_run)
        self.domains = domains or POPULAR_DOMAINS
        if label:
            self.name = f"auto:http:{label}"

    def generate(self):
        import requests as req_lib
        from urllib3.exceptions import InsecureRequestWarning
        req_lib.packages.urllib3.disable_warnings(InsecureRequestWarning)

        self.stats.log(
            f"{self.name}: HTTP traffic to {len(self.domains)} domains at {self.rate} pps"
        )
        session = req_lib.Session()
        session.verify = False

        methods = ["GET", "HEAD", "POST"]
        start = time.time()

        while not self.should_stop():
            if self.duration > 0 and time.time() - start >= self.duration:
                break

            domain = random.choice(self.domains)
            scheme = random.choice(["http", "https"])
            path = random.choice(HTTP_PATHS)
            method = random.choice(methods)
            url = f"{scheme}://{domain}{path}"

            headers = {
                "User-Agent": random.choice(HTTP_USER_AGENTS),
                "Accept": "text/html,application/json,*/*",
                "Accept-Language": random.choice([
                    "en-US,en;q=0.9", "de-DE,de;q=0.9", "fr-FR,fr;q=0.9",
                    "es-ES,es;q=0.9", "ja-JP,ja;q=0.9", "zh-CN,zh;q=0.9",
                ]),
                "Connection": random.choice(["keep-alive", "close"]),
            }

            body = None
            if method == "POST":
                body = f'{{"user":"test{random.randint(1,9999)}","ts":{int(time.time())}}}'
                headers["Content-Type"] = "application/json"

            try:
                if not self.dry_run:
                    resp = session.request(
                        method, url, headers=headers, data=body,
                        timeout=3, allow_redirects=False,
                    )
                    size = len(resp.content) + len(str(resp.headers))
                    self.stats.update(self.name, packets=1, bytes_sent=size, connections=1)
                else:
                    self.stats.update(self.name, packets=1, bytes_sent=512)
            except Exception:
                self.stats.update(self.name, packets=1, errors=1)

            self.throttle()


class AutoTCPConnectGenerator(BaseGenerator):
    """Multi-destination TCP connect generator for auto mode.

    Makes full TCP connections to many destinations on varied ports,
    simulating real application traffic.
    """

    name = "auto:tcp"

    def __init__(self, config: GeneratorConfig, stats: StatsCollector,
                 dry_run: bool = False, destinations: list[str] | None = None,
                 label: str = ""):
        super().__init__(config, stats, dry_run)
        self.destinations = destinations or build_destination_pool(500)
        if label:
            self.name = f"auto:tcp:{label}"

    def generate(self):
        self.stats.log(
            f"{self.name}: TCP connect to {len(self.destinations)} destinations at {self.rate} pps"
        )
        start = time.time()

        while not self.should_stop():
            if self.duration > 0 and time.time() - start >= self.duration:
                break

            dst = random.choice(self.destinations)
            port = random.choice(TCP_PORTS)
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                if not self.dry_run:
                    sock.connect((dst, port))
                    self.stats.update(self.name, packets=1, bytes_sent=64, connections=1)
                else:
                    self.stats.update(self.name, packets=1, bytes_sent=64)
                sock.close()
            except (ConnectionRefusedError, socket.timeout, OSError):
                self.stats.update(self.name, packets=1, errors=1)

            self.throttle()
