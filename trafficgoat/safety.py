"""Safety helpers - target allowlist and config-time guardrails.

Default-deny anything outside RFC1918, loopback, link-local and ULA. Public
targets require an explicit opt-in (`allow_public=True`, surfaced as
`--allow-public` on the CLI or `allow_public` on the API).

Hostnames are resolved (A + AAAA) and *every* returned address must pass the
check. A hostname that resolves to a mix of public and private addresses is
rejected even in `allow_public=False` mode, so a single misconfigured DNS
record can't trick the tool into hitting a public IP.
"""

from __future__ import annotations

import ipaddress
import socket
from typing import Iterable


SAFE_NETWORKS: tuple[ipaddress._BaseNetwork, ...] = (
    ipaddress.ip_network("127.0.0.0/8"),       # loopback
    ipaddress.ip_network("10.0.0.0/8"),        # RFC1918
    ipaddress.ip_network("172.16.0.0/12"),     # RFC1918
    ipaddress.ip_network("192.168.0.0/16"),    # RFC1918
    ipaddress.ip_network("169.254.0.0/16"),    # link-local
    ipaddress.ip_network("::1/128"),           # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),          # IPv6 unique-local
    ipaddress.ip_network("fe80::/10"),         # IPv6 link-local
)


class UnsafeTargetError(ValueError):
    """Raised when a target is rejected by the allowlist."""


def is_private_address(addr: str) -> bool:
    """Return True if `addr` is a literal IP in one of the SAFE_NETWORKS."""
    try:
        ip = ipaddress.ip_address(addr)
    except ValueError:
        return False
    return any(ip in net for net in SAFE_NETWORKS)


def resolve_target(target: str) -> list[str]:
    """Resolve `target` to a list of IP literals via getaddrinfo.

    If `target` is already a literal IP, returns [target]. Raises socket.gaierror
    on resolution failure.
    """
    try:
        ipaddress.ip_address(target)
        return [target]
    except ValueError:
        pass
    infos = socket.getaddrinfo(target, None, type=socket.SOCK_STREAM)
    addrs = sorted({info[4][0] for info in infos})
    return addrs


def check_target(target: str, allow_public: bool = False) -> list[str]:
    """Validate a target hostname or IP.

    Returns the list of resolved addresses on success. Raises
    `UnsafeTargetError` if any resolved address is public and `allow_public`
    is False.

    The empty string and `0.0.0.0` are allowed as no-op sentinels used by
    `auto` mode (which targets a pool of public domains itself; its own gating
    is handled separately).
    """
    if not target or target in ("0.0.0.0", "::"):
        return [target] if target else []
    try:
        addrs = resolve_target(target)
    except socket.gaierror as e:
        raise UnsafeTargetError(f"Cannot resolve target {target!r}: {e}") from e

    if allow_public:
        return addrs

    unsafe = [a for a in addrs if not is_private_address(a)]
    if unsafe:
        raise UnsafeTargetError(
            f"Target {target!r} resolves to public address(es) {unsafe}. "
            f"Pass --allow-public (CLI) or allow_public=true (API) to permit, "
            f"or pick a private/loopback target."
        )
    return addrs


def check_targets(targets: Iterable[str], allow_public: bool = False) -> None:
    """Validate a batch of targets. Raises UnsafeTargetError on the first miss."""
    for t in targets:
        check_target(t, allow_public=allow_public)
