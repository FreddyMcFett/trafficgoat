"""HTTP/HTTPS traffic generator."""

import random
import time

import requests
from urllib3.exceptions import InsecureRequestWarning

from trafficgoat.generators.base import BaseGenerator
from trafficgoat.config import GeneratorConfig, parse_ports
from trafficgoat.stats import StatsCollector

# Suppress SSL warnings for testing
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Edge/120.0.0.0",
    "curl/8.4.0",
    "python-requests/2.31.0",
    "Googlebot/2.1 (+http://www.google.com/bot.html)",
    "Mozilla/5.0 (compatible; Bingbot/2.0; +http://www.bing.com/bingbot.htm)",
]

PATHS = [
    "/", "/index.html", "/login", "/admin", "/api/v1/users", "/api/v1/status",
    "/wp-admin", "/wp-login.php", "/.env", "/robots.txt", "/sitemap.xml",
    "/api/health", "/dashboard", "/search?q=test", "/static/js/app.js",
    "/favicon.ico", "/api/v1/data", "/config", "/backup", "/test",
    "/.git/config", "/phpmyadmin", "/shell", "/cmd", "/debug",
]


class HTTPGenerator(BaseGenerator):
    """Generate HTTP/HTTPS traffic with various methods and paths."""

    name = "http"

    def __init__(self, config: GeneratorConfig, stats: StatsCollector, dry_run: bool = False):
        super().__init__(config, stats, dry_run)
        self.urls = config.urls or []
        self.methods = config.methods or ["GET"]
        self.port_list = parse_ports(self.ports)

        # Build URL list if not provided
        if not self.urls:
            for port in self.port_list:
                scheme = "https" if port == 443 else "http"
                port_suffix = "" if port in (80, 443) else f":{port}"
                for path in PATHS:
                    self.urls.append(f"{scheme}://{self.target}{port_suffix}{path}")

    def generate(self):
        self.stats.log(f"{self.name}: HTTP requests to {self.target} ({len(self.urls)} URLs, methods={self.methods})")
        session = requests.Session()
        session.verify = False
        start = time.time()

        while not self.should_stop():
            if self.duration > 0 and time.time() - start >= self.duration:
                break

            url = random.choice(self.urls)
            method = random.choice(self.methods)
            headers = {
                "User-Agent": random.choice(USER_AGENTS),
                "Accept": "text/html,application/json,*/*",
                "Accept-Language": random.choice(["en-US,en;q=0.9", "de-DE,de;q=0.9", "fr-FR,fr;q=0.9"]),
                "Connection": random.choice(["keep-alive", "close"]),
            }

            body = None
            if method in ("POST", "PUT"):
                body = f'{{"user":"test{random.randint(1,9999)}","action":"login","timestamp":{int(time.time())}}}'
                headers["Content-Type"] = "application/json"

            try:
                if not self.dry_run:
                    resp = session.request(
                        method, url, headers=headers, data=body,
                        timeout=5, allow_redirects=False,
                    )
                    size = len(resp.content) + len(str(resp.headers))
                    self.stats.update(self.name, packets=1, bytes_sent=size, connections=1)
                else:
                    self.stats.update(self.name, packets=1, bytes_sent=256)
            except requests.RequestException:
                self.stats.update(self.name, packets=1, errors=1)

            self.throttle()
