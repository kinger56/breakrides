from datetime import timedelta

from sqlalchemy import select, update

from app.models import EmailCode, utcnow
from tests.conftest import flight_in, signup


def new_account(client):
    signup(client, verify=False)


def add_trip(client):
    return client.post(
        "/api/trips", json={"airport": "SJC", "direction": "to_airport", "flight_time": flight_in(5)}
    )


def test_signup_emails_a_six_digit_code(client, mailer):
    response = client.post(
        "/api/auth/signup", json={"email": "Ben@SCU.edu", "first_name": "Ben", "password": "x" * 12}
    )
    assert response.json()["email_verified"] is False
    assert mailer.sent[-1]["to"] == "ben@scu.edu"
    assert len(mailer.last_code("ben@scu.edu")) == 6


def test_unverified_students_cannot_add_trips(client):
    new_account(client)
    assert add_trip(client).status_code == 403


def test_right_code_verifies(client, mailer):
    new_account(client)
    code = mailer.last_code("ben@scu.edu")
    assert client.post("/api/auth/verify", json={"code": code}).json()["email_verified"] is True
    assert client.get("/api/me").json()["email_verified"] is True
    assert add_trip(client).status_code == 201


def wrong_code(mailer):
    real = mailer.last_code("ben@scu.edu")
    return "000000" if real != "000000" else "111111"


def test_wrong_code_is_rejected_and_limited_to_five_tries(client, mailer):
    new_account(client)
    bad = wrong_code(mailer)
    for _ in range(5):
        assert client.post("/api/auth/verify", json={"code": bad}).status_code == 400
    # Even the right code is refused now: 5 tries out of a million can't be
    # stretched into a brute-force attack.
    right = mailer.last_code("ben@scu.edu")
    assert client.post("/api/auth/verify", json={"code": right}).status_code == 429


def test_expired_code_is_rejected(client, mailer, app):
    new_account(client)
    with app.state.session_factory() as db:
        db.execute(update(EmailCode).values(expires_at=utcnow() - timedelta(seconds=1)))
        db.commit()
    code = mailer.last_code("ben@scu.edu")
    response = client.post("/api/auth/verify", json={"code": code})
    assert response.status_code == 400 and "expired" in response.json()["detail"]


def test_code_is_stored_hashed(client, mailer, app):
    new_account(client)
    with app.state.session_factory() as db:
        stored = db.scalar(select(EmailCode.code_hash))
    assert mailer.last_code("ben@scu.edu") not in stored


def test_resend_replaces_the_old_code_and_is_rate_limited(client, mailer):
    new_account(client)
    first = mailer.last_code("ben@scu.edu")
    client.app.state.resend_throttle._clock = lambda: 10**9  # signup's code was "long ago"
    assert client.post("/api/auth/resend").status_code == 204
    second = mailer.last_code("ben@scu.edu")
    too_soon = client.post("/api/auth/resend")
    assert too_soon.status_code == 429 and "retry-after" in too_soon.headers
    if first != second:  # (1 in a million they match)
        assert client.post("/api/auth/verify", json={"code": first}).status_code == 400
    assert client.post("/api/auth/verify", json={"code": second}).status_code == 200


def test_code_must_be_six_digits(client):
    new_account(client)
    assert client.post("/api/auth/verify", json={"code": "12ab56"}).status_code == 422


def test_email_failure_does_not_lose_the_account(client, app):
    class BrokenMailer:
        def send(self, *args):
            from app.mailer import MailError
            raise MailError("down")

    app.state.mailer = BrokenMailer()
    response = client.post(
        "/api/auth/signup", json={"email": "ben@scu.edu", "first_name": "Ben", "password": "x" * 12}
    )
    assert response.status_code == 201
    client.app.state.resend_throttle._clock = lambda: 10**9
    assert client.post("/api/auth/resend").status_code == 502
