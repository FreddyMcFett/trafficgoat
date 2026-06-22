"""Hardening regressions: token-on-disk, rate limiting, CORS pinning, body cap."""

import os

import pytest

from trafficgoat.web import app as app_module
from trafficgoat.web.app import create_app
from trafficgoat.web.routes import _rate_hits


@pytest.fixture(autouse=True)
def _reset_rate_buckets():
    _rate_hits.clear()
    yield
    _rate_hits.clear()


def test_generated_token_is_written_to_file_not_stdout(capsys, tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    monkeypatch.delenv("TRAFFICGOAT_TOKEN", raising=False)
    create_app(host="127.0.0.1", port=8080, auth_token=None)
    out = capsys.readouterr().out

    token = app_module.get_auth_token()
    assert token  # a token was generated
    assert token not in out, "full token should not be printed to stdout"
    assert "Saved to:" in out

    # File exists, has 0600, and contains the token.
    saved_files = list(tmp_path.glob("trafficgoat-token-*.txt"))
    assert len(saved_files) == 1
    path = saved_files[0]
    assert path.read_text().strip() == token
    mode = os.stat(path).st_mode & 0o777
    assert mode == 0o600, f"expected mode 0600, got {oct(mode)}"


def test_rate_limit_on_api_logs():
    app = create_app(host="127.0.0.1", port=8080, auth_token="t")
    client = app.test_client()
    headers = {"X-Auth-Token": "t"}
    # 30/5s is the limit; 30 should pass, 31st should 429.
    for _ in range(30):
        r = client.get("/api/logs", headers=headers)
        assert r.status_code == 200
    r = client.get("/api/logs", headers=headers)
    assert r.status_code == 429
    assert r.headers.get("Retry-After")
    assert r.get_json()["error"] == "Too Many Requests"


def test_rate_limit_buckets_separately_per_token():
    app = create_app(host="127.0.0.1", port=8080, auth_token="t")
    client = app.test_client()
    # Use up the budget for /api/logs with token "t".
    for _ in range(30):
        client.get("/api/logs", headers={"X-Auth-Token": "t"})
    # /api/history has its own bucket — should still work.
    r = client.get("/api/history", headers={"X-Auth-Token": "t"})
    assert r.status_code == 200


def test_rate_limit_on_api_start():
    app = create_app(host="127.0.0.1", port=8080, auth_token="t")
    client = app.test_client()
    headers = {"X-Auth-Token": "t"}
    payload = {"mode": "stress", "target": "8.8.8.8"}  # 400 from allowlist
    # 3/10s is the limit. After 3 attempts the 4th must be 429.
    for _ in range(3):
        r = client.post("/api/start", json=payload, headers=headers)
        assert r.status_code in (400, 403)
    r = client.post("/api/start", json=payload, headers=headers)
    assert r.status_code == 429


def test_cors_does_not_widen_when_allow_public(monkeypatch):
    monkeypatch.delenv("TRAFFICGOAT_CORS_ORIGINS", raising=False)
    create_app(host="127.0.0.1", port=8080, auth_token="t", allow_public=True)
    origins = app_module.socketio.server_options.get("cors_allowed_origins")
    assert origins != "*", "allow_public must not open CORS to the world"
    assert isinstance(origins, list)
    assert any("127.0.0.1" in o for o in origins)


def test_cors_env_var_overrides(monkeypatch):
    monkeypatch.setenv("TRAFFICGOAT_CORS_ORIGINS",
                       "http://dash.example.com, http://other.example.com")
    create_app(host="127.0.0.1", port=8080, auth_token="t")
    origins = app_module.socketio.server_options.get("cors_allowed_origins")
    assert "http://dash.example.com" in origins
    assert "http://other.example.com" in origins


def test_oversized_body_rejected():
    app = create_app(host="127.0.0.1", port=8080, auth_token="t")
    client = app.test_client()
    # 2 MiB body, MAX_CONTENT_LENGTH is 1 MiB.
    big = b"x" * (2 * 1024 * 1024)
    r = client.post("/api/start", data=big,
                    headers={"X-Auth-Token": "t",
                             "Content-Type": "application/json"})
    assert r.status_code == 413
