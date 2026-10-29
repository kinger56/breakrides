"""Shared test setup. Every test gets a brand-new app with its own empty
in-memory database, so tests can't affect each other."""

import os

# Set before app.main is imported, so importing it never creates a real
# database file.
os.environ["DATABASE_URL"] = "sqlite://"

from datetime import datetime, timedelta, timezone  # noqa: E402

import re  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402

PASSWORD = "correct-horse-battery"


class FakeMailer:
    """Records emails instead of sending them."""

    def __init__(self):
        self.sent = []

    def send(self, to, subject, text):
        self.sent.append({"to": to, "subject": subject, "text": text})

    def last_code(self, to):
        mail = [m for m in self.sent if m["to"] == to][-1]
        return re.search(r"\b(\d{6})\b", mail["text"]).group(1)


@pytest.fixture
def mailer():
    return FakeMailer()


@pytest.fixture
def app(mailer):
    return create_app(Settings("sqlite://", "scu.edu", 30, False), mailer=mailer)


@pytest.fixture
def client(app):
    return TestClient(app)


def signup(client, email="ben@scu.edu", first_name="Ben", password=PASSWORD, verify=True):
    """Sign up (and log in). By default also enters the emailed code, since
    most tests are about what verified students can do."""
    response = client.post(
        "/api/auth/signup", json={"email": email, "first_name": first_name, "password": password}
    )
    if verify and response.status_code == 201:
        code = client.app.state.mailer.last_code(email.lower())
        assert client.post("/api/auth/verify", json={"code": code}).status_code == 200
    return response


def flight_in(days: float, hours: float = 0) -> str:
    """An ISO flight time `days` from now, with a timezone, as the API expects."""
    return (datetime.now(timezone.utc) + timedelta(days=days, hours=hours)).isoformat()
