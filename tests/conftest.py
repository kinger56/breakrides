"""Shared test setup. Every test gets a brand-new app with its own empty
in-memory database, so tests can't affect each other."""

import os

# Set before app.main is imported, so importing it never creates a real
# database file.
os.environ["DATABASE_URL"] = "sqlite://"

from datetime import datetime, timedelta, timezone  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402

PASSWORD = "correct-horse-battery"


@pytest.fixture
def app():
    return create_app(Settings("sqlite://", "scu.edu", 30, False))


@pytest.fixture
def client(app):
    return TestClient(app)


def signup(client, email="ben@scu.edu", first_name="Ben", password=PASSWORD):
    return client.post(
        "/api/auth/signup", json={"email": email, "first_name": first_name, "password": password}
    )


def flight_in(days: float, hours: float = 0) -> str:
    """An ISO flight time `days` from now, with a timezone, as the API expects."""
    return (datetime.now(timezone.utc) + timedelta(days=days, hours=hours)).isoformat()
