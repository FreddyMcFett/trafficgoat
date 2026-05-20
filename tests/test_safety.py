"""Target allowlist tests."""

import socket
from unittest import mock

import pytest

from trafficgoat.safety import (
    UnsafeTargetError,
    check_target,
    is_private_address,
    resolve_target,
)


class TestIsPrivateAddress:
    def test_loopback_ipv4(self):
        assert is_private_address("127.0.0.1")
        assert is_private_address("127.255.255.255")

    def test_rfc1918(self):
        assert is_private_address("10.0.0.1")
        assert is_private_address("172.16.5.5")
        assert is_private_address("172.31.255.255")
        assert is_private_address("192.168.1.1")

    def test_link_local(self):
        assert is_private_address("169.254.1.1")

    def test_ipv6_local(self):
        assert is_private_address("::1")
        assert is_private_address("fc00::1")
        assert is_private_address("fe80::1")

    def test_public_addresses(self):
        assert not is_private_address("8.8.8.8")
        assert not is_private_address("1.1.1.1")
        assert not is_private_address("172.32.0.1")  # just outside RFC1918
        assert not is_private_address("2001:4860:4860::8888")

    def test_invalid(self):
        assert not is_private_address("not-an-ip")
        assert not is_private_address("")


class TestCheckTarget:
    def test_private_target_allowed_by_default(self):
        assert check_target("127.0.0.1") == ["127.0.0.1"]
        assert check_target("10.5.5.5") == ["10.5.5.5"]
        assert check_target("192.168.0.1") == ["192.168.0.1"]

    def test_public_target_rejected(self):
        with pytest.raises(UnsafeTargetError):
            check_target("8.8.8.8")
        with pytest.raises(UnsafeTargetError):
            check_target("1.1.1.1")

    def test_public_target_allowed_with_flag(self):
        assert check_target("8.8.8.8", allow_public=True) == ["8.8.8.8"]

    def test_empty_target_passthrough(self):
        # Used by auto mode which manages its own destinations.
        assert check_target("") == []
        assert check_target("0.0.0.0") == ["0.0.0.0"]

    def test_hostname_resolving_to_private(self):
        with mock.patch("trafficgoat.safety.socket.getaddrinfo") as m:
            m.return_value = [(0, 0, 0, "", ("10.0.0.5", 0))]
            assert check_target("internal.example") == ["10.0.0.5"]

    def test_hostname_resolving_to_public_rejected(self):
        with mock.patch("trafficgoat.safety.socket.getaddrinfo") as m:
            m.return_value = [(0, 0, 0, "", ("8.8.8.8", 0))]
            with pytest.raises(UnsafeTargetError):
                check_target("dns.google")

    def test_hostname_with_mixed_addresses_rejected(self):
        # A single public-resolution disqualifies the host even if there are
        # private ones in the same response.
        with mock.patch("trafficgoat.safety.socket.getaddrinfo") as m:
            m.return_value = [
                (0, 0, 0, "", ("10.0.0.5", 0)),
                (0, 0, 0, "", ("8.8.8.8", 0)),
            ]
            with pytest.raises(UnsafeTargetError):
                check_target("mixed.example")

    def test_resolution_failure(self):
        with mock.patch("trafficgoat.safety.socket.getaddrinfo") as m:
            m.side_effect = socket.gaierror("no such host")
            with pytest.raises(UnsafeTargetError):
                check_target("definitely-not-a-real-host.example.invalid")


class TestResolveTarget:
    def test_literal_ip(self):
        assert resolve_target("127.0.0.1") == ["127.0.0.1"]
        assert resolve_target("::1") == ["::1"]

    def test_hostname(self):
        # localhost is the most portable resolvable name.
        addrs = resolve_target("localhost")
        # Could be 127.0.0.1 / ::1 / both depending on system config
        assert addrs, "localhost must resolve to at least one address"
