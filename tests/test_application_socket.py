"""Socket-leak regression test for ApplicationGenerator._tcp_connect_send (B1)."""

import socket
from unittest import mock

from trafficgoat.config import GeneratorConfig
from trafficgoat.generators.application import ApplicationGenerator
from trafficgoat.stats import StatsCollector


def _make_app_gen():
    cfg = GeneratorConfig(type="application", subtype="ftp", target="127.0.0.1", rate=1000)
    return ApplicationGenerator(cfg, StatsCollector(), dry_run=False)


class _FakeSocket:
    """Records close() calls and raises a chosen exception on a chosen method."""

    def __init__(self, raise_on: str | None = None, exc: Exception | None = None):
        self.raise_on = raise_on
        self.exc = exc or ConnectionRefusedError()
        self.closed = False

    def settimeout(self, _t):
        pass

    def connect(self, _addr):
        if self.raise_on == "connect":
            raise self.exc

    def sendall(self, _data):
        if self.raise_on == "sendall":
            raise self.exc

    def recv(self, _n):
        if self.raise_on == "recv":
            raise self.exc
        return b""

    def close(self):
        self.closed = True


def test_socket_closed_on_connect_refused():
    gen = _make_app_gen()
    fake = _FakeSocket(raise_on="connect", exc=ConnectionRefusedError())
    with mock.patch("trafficgoat.generators.application.socket.socket", return_value=fake):
        gen._tcp_connect_send(21, b"USER test\r\n")
    assert fake.closed, "socket must be closed even when connect() raises"


def test_socket_closed_on_timeout():
    gen = _make_app_gen()
    fake = _FakeSocket(raise_on="connect", exc=socket.timeout())
    with mock.patch("trafficgoat.generators.application.socket.socket", return_value=fake):
        gen._tcp_connect_send(22, b"banner\r\n")
    assert fake.closed


def test_socket_closed_on_gaierror():
    gen = _make_app_gen()
    fake = _FakeSocket(raise_on="connect", exc=socket.gaierror("no such host"))
    with mock.patch("trafficgoat.generators.application.socket.socket", return_value=fake):
        gen._tcp_connect_send(25, b"EHLO\r\n")
    assert fake.closed


def test_socket_closed_on_sendall_error():
    gen = _make_app_gen()
    fake = _FakeSocket(raise_on="sendall", exc=OSError("broken pipe"))
    with mock.patch("trafficgoat.generators.application.socket.socket", return_value=fake):
        gen._tcp_connect_send(21, b"USER test\r\n", recv=False)
    assert fake.closed


def test_socket_closed_on_success():
    gen = _make_app_gen()
    fake = _FakeSocket()
    with mock.patch("trafficgoat.generators.application.socket.socket", return_value=fake):
        gen._tcp_connect_send(22, b"hi\r\n", recv=False)
    assert fake.closed
