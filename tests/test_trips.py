from tests.conftest import flight_in, signup


def add_trip(client, airport="SJC", direction="to_airport", flight_time=None):
    return client.post(
        "/api/trips",
        json={"airport": airport, "direction": direction, "flight_time": flight_time or flight_in(7)},
    )


def test_trips_require_login(client):
    assert add_trip(client).status_code == 401
    assert client.get("/api/trips").status_code == 401


def test_add_and_list_trips_in_time_order(client):
    signup(client)
    later = add_trip(client, flight_time=flight_in(10)).json()
    sooner = add_trip(client, airport="SFO", flight_time=flight_in(3)).json()
    assert [t["id"] for t in client.get("/api/trips").json()] == [sooner["id"], later["id"]]


def test_flight_time_keeps_its_moment_in_time(client):
    signup(client)
    trip = add_trip(client, flight_time="2027-01-05T09:30:00-08:00").json()
    # Stored and returned in UTC: 09:30 Pacific is 17:30 UTC.
    assert trip["flight_time"].startswith("2027-01-05T17:30:00")


def test_rejects_bad_input(client):
    signup(client)
    assert add_trip(client, airport="LAX").status_code == 422
    assert add_trip(client, direction="sideways").status_code == 422
    assert add_trip(client, flight_time="2027-01-05T09:30:00").status_code == 422  # no timezone
    assert add_trip(client, flight_time=flight_in(-1)).status_code == 422  # in the past
    assert add_trip(client, flight_time=flight_in(400)).status_code == 422  # typo'd year


def test_you_only_see_your_own_trips(client):
    signup(client, email="ana@scu.edu", first_name="Ana")
    add_trip(client)
    client.cookies.clear()
    signup(client)
    assert client.get("/api/trips").json() == []


def test_delete_own_trip(client):
    signup(client)
    trip = add_trip(client).json()
    assert client.delete(f"/api/trips/{trip['id']}").status_code == 204
    assert client.get("/api/trips").json() == []


def test_cannot_delete_someone_elses_trip(client):
    signup(client, email="ana@scu.edu", first_name="Ana")
    anas_trip = add_trip(client).json()
    client.cookies.clear()
    signup(client)
    assert client.delete(f"/api/trips/{anas_trip['id']}").status_code == 404
