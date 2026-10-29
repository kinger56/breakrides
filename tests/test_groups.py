from tests.conftest import flight_in, signup


def add_trip(client, airport="SFO", direction="to_airport", flight_time=None):
    return client.post(
        "/api/trips",
        json={"airport": airport, "direction": direction, "flight_time": flight_time or flight_in(7)},
    ).json()


def as_user(client, email, first_name):
    client.cookies.clear()
    signup(client, email=email, first_name=first_name)


def test_alone_until_someone_else_books_a_nearby_flight(client):
    as_user(client, "ben@scu.edu", "Ben")
    trip = add_trip(client, flight_time=flight_in(7))
    alone = client.get(f"/api/trips/{trip['id']}/group").json()
    assert alone["matched"] is False
    assert alone["cost_per_person"] == 70  # the whole SFO fare

    as_user(client, "ana@scu.edu", "Ana")
    add_trip(client, flight_time=flight_in(7, hours=0.5))
    as_user(client, "cy@scu.edu", "Cy")
    add_trip(client, airport="SJC", flight_time=flight_in(7))  # different airport

    client.cookies.clear()
    client.post("/api/auth/login", json={"email": "ben@scu.edu", "password": "correct-horse-battery"})
    group = client.get(f"/api/trips/{trip['id']}/group").json()
    assert group["matched"] is True
    assert group["riders"] == [
        {"first_name": "Ben", "is_you": True},
        {"first_name": "Ana", "is_you": False},
    ]
    assert group["cost_per_person"] == 35.0
    assert group["savings_per_person"] == 35.0


def test_group_shows_no_emails(client):
    as_user(client, "ana@scu.edu", "Ana")
    add_trip(client)
    as_user(client, "ben@scu.edu", "Ben")
    trip = add_trip(client)
    assert "@" not in str(client.get(f"/api/trips/{trip['id']}/group").json())


def test_cannot_see_group_for_someone_elses_trip(client):
    as_user(client, "ana@scu.edu", "Ana")
    anas = add_trip(client)
    as_user(client, "ben@scu.edu", "Ben")
    assert client.get(f"/api/trips/{anas['id']}/group").status_code == 404


def test_group_requires_login(client):
    assert client.get("/api/trips/1/group").status_code == 401
