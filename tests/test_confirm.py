"""Confirming a group, locking it, and sharing contact info."""

from tests.conftest import PASSWORD, flight_in, signup

FLIGHT = flight_in(7)


def as_user(client, email):
    """Switch the test client to this student (signing up the first time)."""
    client.cookies.clear()
    if client.post("/api/auth/login", json={"email": email, "password": PASSWORD}).status_code != 200:
        signup(client, email=email, first_name=email.split("@")[0].title())


def add_trip(client, flight_time=FLIGHT, airport="SFO"):
    return client.post(
        "/api/trips", json={"airport": airport, "direction": "to_airport", "flight_time": flight_time}
    ).json()["id"]


def group(client, trip_id):
    return client.get(f"/api/trips/{trip_id}/group").json()


def confirm(client, trip_id):
    return client.post(f"/api/trips/{trip_id}/confirm")


def two_riders(client):
    as_user(client, "ana@scu.edu")
    ana = add_trip(client)
    as_user(client, "ben@scu.edu")
    ben = add_trip(client, flight_in(7, hours=0.5))
    return ana, ben


def test_no_contact_info_until_everyone_confirms(client):
    ana, ben = two_riders(client)
    confirm(client, ben)  # Ben says yes
    g = group(client, ben)
    assert g["you_confirmed"] and not g["locked"]
    assert {r["first_name"]: r["confirmed"] for r in g["riders"]} == {"Ben": True, "Ana": False}
    assert all(r["email"] is None for r in g["riders"])


def test_group_locks_when_everyone_confirms_and_shares_emails(client, mailer):
    ana, ben = two_riders(client)
    confirm(client, ben)
    as_user(client, "ana@scu.edu")
    locked = confirm(client, ana).json()
    assert locked["locked"] is True
    assert sorted(r["email"] for r in locked["riders"]) == ["ana@scu.edu", "ben@scu.edu"]
    # Both riders get an email with each other's contact info.
    confirmations = [m for m in mailer.sent if "is confirmed" in m["subject"]]
    assert sorted(m["to"] for m in confirmations) == ["ana@scu.edu", "ben@scu.edu"]
    assert all("ana@scu.edu" in m["text"] and "ben@scu.edu" in m["text"] for m in confirmations)


def test_locked_group_does_not_change_when_someone_new_arrives(client):
    ana, ben = two_riders(client)
    confirm(client, ben)
    as_user(client, "ana@scu.edu")
    confirm(client, ana)
    as_user(client, "cy@scu.edu")
    cy = add_trip(client, flight_in(7, hours=0.25))  # would have matched them
    assert group(client, cy)["matched"] is False
    as_user(client, "ana@scu.edu")
    assert len(group(client, ana)["riders"]) == 2


def test_new_rider_joining_resets_earlier_confirmations(client):
    ana, ben = two_riders(client)
    confirm(client, ben)
    as_user(client, "cy@scu.edu")
    add_trip(client, flight_in(7, hours=0.25))  # joins the suggested group
    as_user(client, "ben@scu.edu")
    g = group(client, ben)
    # Ben said yes to a group of 2, not to riding with Cy: he must confirm again.
    assert len(g["riders"]) == 3 and g["you_confirmed"] is False


def test_cannot_confirm_alone(client):
    as_user(client, "ben@scu.edu")
    solo = add_trip(client)
    assert confirm(client, solo).status_code == 400


def test_leaving_a_locked_group_unlocks_it_for_everyone(client):
    ana, ben = two_riders(client)
    confirm(client, ben)
    as_user(client, "ana@scu.edu")
    confirm(client, ana)
    as_user(client, "ben@scu.edu")
    after = client.post(f"/api/trips/{ben}/leave").json()
    assert after["locked"] is False and after["you_confirmed"] is False
    assert all(r["email"] is None for r in after["riders"])
    as_user(client, "ana@scu.edu")
    assert group(client, ana)["locked"] is False


def test_deleting_a_trip_in_a_locked_group_unlocks_the_others(client):
    ana, ben = two_riders(client)
    confirm(client, ben)
    as_user(client, "ana@scu.edu")
    confirm(client, ana)
    as_user(client, "ben@scu.edu")
    assert client.delete(f"/api/trips/{ben}").status_code == 204
    as_user(client, "ana@scu.edu")
    g = group(client, ana)
    assert g["locked"] is False and g["matched"] is False


def test_cannot_confirm_someone_elses_trip(client):
    ana, ben = two_riders(client)
    assert confirm(client, ana).status_code == 404  # logged in as Ben


def test_unverified_students_cannot_confirm(client):
    ana, ben = two_riders(client)
    client.cookies.clear()
    signup(client, email="new@scu.edu", verify=False)
    assert confirm(client, ana).status_code == 403
