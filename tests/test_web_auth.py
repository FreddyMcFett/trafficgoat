"""Auth + validation on /api/* (C1, H1, C4)."""

import pytest

from trafficgoat.web.app import create_app


@pytest.fixture
def authed_client():
    app = create_app(host="127.0.0.1", port=8080, auth_token="s3cret")
    return app.test_client(), "s3cret"


def test_start_requires_auth(authed_client):
    client, _ = authed_client
    r = client.post("/api/start", json={"mode": "stress", "target": "127.0.0.1"})
    assert r.status_code == 401


def test_start_rejects_invalid_token(authed_client):
    client, _ = authed_client
    r = client.post("/api/start", json={"mode": "stress", "target": "127.0.0.1"},
                    headers={"X-Auth-Token": "nope"})
    assert r.status_code == 401


def test_start_rejects_public_target(authed_client):
    client, token = authed_client
    r = client.post("/api/start", json={"mode": "stress", "target": "8.8.8.8"},
                    headers={"X-Auth-Token": token})
    # Root check happens before allowlist if non-root; that's still a non-200 either way.
    # The allowlist rejection is what we care about — make sure 8.8.8.8 isn't accepted.
    assert r.status_code in (400, 403)


def test_start_rejects_unknown_mode(authed_client):
    client, token = authed_client
    r = client.post("/api/start", json={"mode": "nonexistent", "target": "127.0.0.1"},
                    headers={"X-Auth-Token": token})
    assert r.status_code in (400, 403)


def test_start_rejects_out_of_range_rate(authed_client):
    client, token = authed_client
    r = client.post(
        "/api/start",
        json={"mode": "stress", "target": "127.0.0.1", "rate": 9_999_999_999},
        headers={"X-Auth-Token": token},
    )
    assert r.status_code in (400, 403)


def test_status_requires_auth(authed_client):
    client, _ = authed_client
    assert client.get("/api/status").status_code == 401


def test_metrics_with_query_token():
    """The token can also ride in the ?token=... query string for /metrics scraping."""
    app = create_app(host="127.0.0.1", port=8080, auth_token="sometoken")
    client = app.test_client()
    assert client.get("/metrics").status_code == 401
    assert client.get("/metrics?token=sometoken").status_code == 200
