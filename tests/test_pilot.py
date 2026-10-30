"""Pilot features: public stats and deleting your account."""

from sqlalchemy import func, select

from app.models import EmailCode, LoginSession, RideGroup, Trip, User
from tests.conftest import PASSWORD, flight_in, signup


def as_user(client, email):
    client.cookies.clear()
    if client.post("/api/auth/login", json={"email": email, "password": PASSWORD}).status_code != 200:
        signup(client, email=email, first_name=email.split("@")[0].title())


def add_trip(client, hours=0.0):
    return client.post(
        "/api/trips",
        json={"airport": "SFO", "direction": "to_airport", "flight_time": flight_in(7, hours=hours)},
    ).json()["id"]


def locked_pair(client):
    as_user(client, "ana@scu.edu")
    ana = add_trip(client)
    as_user(client, "ben@scu.edu")
    ben = add_trip(client, 0.5)
    client.post(f"/api/trips/{ben}/confirm")
    as_user(client, "ana@scu.edu")
    client.post(f"/api/trips/{ana}/confirm")
    return ana, ben


def count(app, model):
    with app.state.session_factory() as db:
        return db.scalar(select(func.count()).select_from(model))


# ---- stats -----------------------------------------------------------------------


def test_stats_start_at_zero_and_need_no_login(client):
    assert client.get("/api/stats").json() == {
        "students": 0, "rides_confirmed": 0, "riders_matched": 0,
        "estimated_savings": 0, "feedback_email": None,
    }


def test_stats_count_confirmed_rides_and_savings(client):
    locked_pair(client)
    signup(client, email="unverified@scu.edu", verify=False)  # not counted
    stats = client.get("/api/stats").json()
    assert stats["students"] == 2
    assert stats["rides_confirmed"] == 1 and stats["riders_matched"] == 2
    assert stats["estimated_savings"] == 70  # one SFO fare saved by sharing


def test_stats_contain_no_personal_data(client):
    locked_pair(client)
    text = client.get("/api/stats").text
    assert "@" not in text and "Ana" not in text and "Ben" not in text


# ---- delete account -----------------------------------------------------------------


def test_delete_account_needs_the_password(client):
    signup(client)
    assert client.request("DELETE", "/api/me", json={"password": "wrong-password!"}).status_code == 403
    assert client.get("/api/me").status_code == 200


def test_delete_account_removes_everything(client, app):
    signup(client)
    add_trip(client)
    assert client.request("DELETE", "/api/me", json={"password": PASSWORD}).status_code == 204
    assert client.get("/api/me").status_code == 401
    for model in (User, Trip, LoginSession, EmailCode):
        assert count(app, model) == 0, model.__name__
    # The email can be used to sign up again.
    assert signup(client).status_code == 201


def test_deleting_an_account_unlocks_the_group_for_the_others(client, app):
    ana, ben = locked_pair(client)
    as_user(client, "ben@scu.edu")
    client.request("DELETE", "/api/me", json={"password": PASSWORD})
    assert count(app, RideGroup) == 0
    as_user(client, "ana@scu.edu")
    group = client.get(f"/api/trips/{ana}/group").json()
    assert group["locked"] is False and group["matched"] is False
