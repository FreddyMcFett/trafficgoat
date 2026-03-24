"""Configuration loading and validation for TrafficGoat."""

import yaml
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class GeneratorConfig:
    """Configuration for a single traffic generator."""
    type: str
    target: str = ""
    ports: str = "80"
    rate: int = 100
    weight: float = 1.0
    duration: int = 60
    count: int = 0  # 0 = unlimited (use duration)
    # HTTP-specific
    urls: list = field(default_factory=list)
    methods: list = field(default_factory=lambda: ["GET"])
    # Application-specific
    subtype: str = ""  # ftp, ssh, smtp, portscan, bruteforce
    # Extra kwargs
    options: dict = field(default_factory=dict)


@dataclass
class TrafficConfig:
    """Main traffic configuration."""
    target: str = "127.0.0.1"
    ports: str = "80"
    duration: int = 60
    rate: int = 100
    threads: int = 4
    interface: Optional[str] = None
    verbose: bool = False
    quiet: bool = False
    dry_run: bool = False
    mode: str = "stress"
    protocol: str = ""
    generators: list = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "TrafficConfig":
        """Create config from dictionary."""
        generators = []
        for gen_data in data.pop("generators", []):
            generators.append(GeneratorConfig(**gen_data))
        config = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        config.generators = generators
        return config

    @classmethod
    def from_yaml(cls, path: str) -> "TrafficConfig":
        """Load config from YAML file."""
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)

    @classmethod
    def from_args(cls, args) -> "TrafficConfig":
        """Create config from argparse namespace."""
        config = cls(
            target=getattr(args, "target", "127.0.0.1"),
            ports=getattr(args, "ports", "80"),
            duration=getattr(args, "duration", 60),
            rate=getattr(args, "rate", 100),
            threads=getattr(args, "threads", 4),
            interface=getattr(args, "interface", None),
            verbose=getattr(args, "verbose", False),
            quiet=getattr(args, "quiet", False),
            dry_run=getattr(args, "dry_run", False),
            mode=getattr(args, "mode", "stress"),
            protocol=getattr(args, "protocol", ""),
        )
        # Load from config file if specified
        config_file = getattr(args, "config", None)
        if config_file:
            file_config = cls.from_yaml(config_file)
            # CLI args override file config for explicitly set values
            if not args.target and file_config.target:
                config.target = file_config.target
            config.generators = file_config.generators
        return config


def parse_ports(port_str: str) -> list[int]:
    """Parse port string like '80', '1-1024', '80,443,8080' into list of ints."""
    ports = []
    for part in port_str.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            ports.extend(range(int(start), int(end) + 1))
        else:
            ports.append(int(part))
    return ports
