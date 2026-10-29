from datetime import timedelta

from sqlalchemy import select, update

from app.models import LoginSession, User, utcnow
from tests.conftest import PASSWORD, signup


def test_signup_logs_you_in(client):
    response = signup(client)
    assert response.status_code == 201
    assert response.json()["first_name"] == "Ben"
    assert client.get("/api/me").json()["email"] == "ben@scu.edu"


def test_session_cookie_is_httponly_and_samesite(client):
    cookie = signup(client).headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=lax" in cookie


def test_only_school_emails_can_sign_up(client):
    response = signup(client, email="ben@gmail.com")
    assert response.status_code == 422
    assert "@scu.edu" in response.json()["detail"]


def test_lookalike_domain_is_rejected(client):
    assert signup(client, email="ben@notscu.edu").status_code == 422


def test_duplicate_email_is_rejected_ignoring_case(client):
    signup(client)
    assert signup(client, email="BEN@scu.edu").status_code == 409


def test_short_password_is_rejected(client):
    assert signup(client, password="short").status_code == 422


def test_password_is_never_stored(client, app):
    signup(client)
    with app.state.session_factory() as db:
        user = db.scalar(select(User))
    assert PASSWORD not in user.password_hash


def test_login_and_wrong_password(client):
    signup(client)
    client.cookies.clear()
    wrong = client.post("/api/auth/login", json={"email": "ben@scu.edu", "password": "nope-nope-nope"})
    unknown = client.post("/api/auth/login", json={"email": "who@scu.edu", "password": PASSWORD})
    # Same error either way: the form doesn't reveal who has an account.
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()

    ok = client.post("/api/auth/login", json={"email": "Ben@SCU.edu", "password": PASSWORD})
    assert ok.status_code == 200


def test_me_requires_login(client):
    assert client.get("/api/me").status_code == 401


def test_logout_kills_the_session(client):
    signup(client)
    token = client.cookies.get("session")
    assert client.post("/api/auth/logout").status_code == 204
    # Even if someone kept a copy of the old cookie, it no longer works.
    client.cookies.set("session", token)
    assert client.get("/api/me").status_code == 401


def test_expired_session_is_rejected(client, app):
    signup(client)
    with app.state.session_factory() as db:
        db.execute(update(LoginSession).values(expires_at=utcnow() - timedelta(seconds=1)))
        db.commit()
    assert client.get("/api/me").status_code == 401


def test_raw_token_is_not_in_the_database(client, app):
    signup(client)
    token = client.cookies.get("session")
    with app.state.session_factory() as db:
        stored = db.scalar(select(LoginSession.token_hash))
    assert stored != token


def test_serves_built_frontend_without_hiding_the_api(tmp_path):
    from fastapi.testclient import TestClient

    from app.config import Settings
    from app.main import create_app

    (tmp_path / "index.html").write_text("<title>BreakRides</title>")
    client = TestClient(create_app(Settings("sqlite://", "scu.edu", 30, False), frontend_dist=tmp_path))
    assert "BreakRides" in client.get("/").text
    assert client.get("/api/health").json() == {"status": "ok"}
