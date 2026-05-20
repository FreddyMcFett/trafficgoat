"""/metrics endpoint tests (F10)."""

import pytest

from trafficgoat.web.app import create_app, get_stats


@pytest.fixture
def app():
    # Empty auth token disables auth so we can test the metrics shape without
    # carrying a token around.
    return create_app(host="127.0.0.1", port=8080, auth_token="")


@pytest.fixture
def client(app):
    return app.test_client()


def test_metrics_endpoint_shape(client):
    stats = get_stats()
    stats.register_generator("test:tcp")
    stats.start()
    stats.update("test:tcp", packets=42, bytes_sent=4242, errors=2, connections=7)

    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert resp.mimetype == "text/plain"
    body = resp.get_data(as_text=True)

    # Exposition format basics
    assert "# HELP trafficgoat_running" in body
    assert "# TYPE trafficgoat_running gauge" in body
    assert "trafficgoat_running 1" in body

    # Per-generator counters
    assert 'trafficgoat_packets_total{generator="test:tcp"} 42' in body
    assert 'trafficgoat_bytes_total{generator="test:tcp"} 4242' in body
    assert 'trafficgoat_errors_total{generator="test:tcp"} 2' in body
    assert 'trafficgoat_connections_total{generator="test:tcp"} 7' in body

    # Aggregate counters
    assert "trafficgoat_total_packets 42" in body


def test_metrics_requires_auth_when_token_set():
    app = create_app(host="127.0.0.1", port=8080, auth_token="s3cret")
    client = app.test_client()
    assert client.get("/metrics").status_code == 401
    assert client.get("/metrics", headers={"X-Auth-Token": "wrong"}).status_code == 401
    assert client.get("/metrics", headers={"X-Auth-Token": "s3cret"}).status_code == 200
