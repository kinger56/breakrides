"""Security hardening: real client IPs, sign-up limits, headers, timing."""

import pathlib

import pytest
from fastapi.testclient import TestClient

from app import security
from app.client_ip import real_client_ip
from app.config import Settings
from app.main import create_app

ROOT = pathlib.Path(__file__).parent.parent
RENDER_PROXY = "10.12.0.5"  # Render's internal network (private address)
CLOUDFLARE = "162.158.1.20"  # inside Cloudflare's published ranges


# ---- working out the real visitor IP -------------------------------------------


@pytest.mark.parametrize("xff, peer, expected", [
    # Normal visit: Cloudflare and Render add the visitor's IP.
    ("73.15.20.9", RENDER_PROXY, "73.15.20.9"),
    (f"73.15.20.9, {CLOUDFLARE}", RENDER_PROXY, "73.15.20.9"),
    # Attack: the visitor writes a fake IP first. It's ignored.
    ("45.33.32.77, 73.15.20.9", RENDER_PROXY, "73.15.20.9"),
    (f"1.1.1.1, 8.8.8.8, 73.15.20.9, {CLOUDFLARE}", RENDER_PROXY, "73.15.20.9"),
    # Junk in the header can't break it.
    ("not-an-ip, 73.15.20.9", RENDER_PROXY, "73.15.20.9"),
    # IPv6 visitors.
    ("2601:600:8080::1, 2606:4700::1", RENDER_PROXY, "2601:600:8080::1"),
    # Local development: no header, connected directly.
    (None, "127.0.0.1", "127.0.0.1"),
    # Someone connecting directly (not through our proxies) can't use the header.
    ("45.33.32.77", "73.15.99.50", "73.15.99.50"),
])
def test_real_client_ip(xff, peer, expected):
    assert real_client_ip(xff, peer) == expected


def test_render_does_not_let_uvicorn_trust_the_header():
    # uvicorn's --proxy-headers would replace the connecting address with the
    # (fakeable) leftmost header entry before our code sees it.
    assert "--proxy-headers" not in (ROOT / "render.yaml").read_text()


# ---- rate limits use the real IP --------------------------------------------------


@pytest.fixture
def proxied_client(app):
    """Requests arrive the way they do on Render: from the internal proxy."""
    return TestClient(app, client=(RENDER_PROXY, 12345))


def login(client, email, real_ip, fake_ip):
    return client.post(
        "/api/auth/login",
        json={"email": email, "password": "wrong-password-1"},
        headers={"X-Forwarded-For": f"{fake_ip}, {real_ip}"},
    )


def test_faking_a_new_ip_each_time_does_not_dodge_the_ip_limit(proxied_client):
    # The attack from the live site: 20 failures, each claiming a new IP.
    for i in range(20):
        login(proxied_client, f"student{i}@scu.edu", "73.15.20.9", f"45.33.32.{i}")
    assert login(proxied_client, "new@scu.edu", "73.15.20.9", "45.33.32.200").status_code == 429
    # A different real visitor is unaffected.
    assert login(proxied_client, "new@scu.edu", "73.15.20.10", "45.33.32.200").status_code == 401


def signup(client, i, real_ip="73.15.20.9"):
    return client.post(
        "/api/auth/signup",
        json={"email": f"s{i}@scu.edu", "first_name": "S", "password": "long-enough-pass"},
        headers={"X-Forwarded-For": f"45.33.32.{i}, {real_ip}"},
    )


def test_signups_are_limited_per_ip(proxied_client, mailer):
    for i in range(5):
        assert signup(proxied_client, i).status_code == 201
    blocked = signup(proxied_client, 99)
    assert blocked.status_code == 429 and "retry-after" in blocked.headers
    assert len(mailer.sent) == 5  # the blocked attempt sent no email
    assert signup(proxied_client, 100, real_ip="73.15.20.10").status_code == 201


# ---- headers --------------------------------------------------------------------


def test_security_headers(client):
    headers = client.get("/api/health").headers
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert "default-src 'self'" in headers["content-security-policy"]
    assert "frame-ancestors 'none'" in headers["content-security-policy"]
    assert "strict-transport-security" not in headers  # local http


def test_production_adds_hsts_and_hides_api_docs(mailer):
    prod = Settings("sqlite://", "scu.edu", 30, True, api_docs=False)
    client = TestClient(create_app(prod, mailer=mailer))
    assert "max-age=31536000" in client.get("/api/health").headers["strict-transport-security"]
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404


# ---- timing ---------------------------------------------------------------------


def test_unknown_email_still_runs_a_password_check(client, monkeypatch):
    checks = []
    real_verify = security.verify_password
    monkeypatch.setattr(security, "verify_password", lambda p, h: checks.append(h) or real_verify(p, h))
    response = client.post("/api/auth/login", json={"email": "nobody@scu.edu", "password": "whatever-123"})
    assert response.status_code == 401
    assert checks == [security.DUMMY_HASH]  # same slow work as a real wrong password
