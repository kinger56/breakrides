"""Example-based tests for the matching engine."""

from datetime import datetime, timedelta, timezone

from app.matching import RideGroup, TripRequest, group_for_trip, ideal_ride_time, match

NOON = datetime(2026, 12, 12, 20, 0, tzinfo=timezone.utc)  # noon Pacific


def trip(trip_id, minutes=0, airport="SJC", direction="to_airport", user_id=None):
    return TripRequest(
        trip_id=trip_id,
        user_id=user_id if user_id is not None else trip_id,
        first_name=f"Student{trip_id}",
        airport=airport,
        direction=direction,
        flight_time=NOON + timedelta(minutes=minutes),
    )


def ids(groups):
    return [[t.trip_id for t in g.trips] for g in groups]


def test_ride_time_to_airport_allows_check_in_and_drive():
    # SFO: 2h at the airport + 50 min drive before a noon flight = 9:10.
    assert ideal_ride_time(trip(1, airport="SFO")) == NOON - timedelta(hours=2, minutes=50)


def test_ride_time_from_airport_allows_for_bags():
    assert ideal_ride_time(trip(1, direction="from_airport")) == NOON + timedelta(minutes=45)


def test_close_flights_share_a_ride():
    assert ids(match([trip(1, 0), trip(2, 30)])) == [[1, 2]]


def test_flights_far_apart_do_not():
    assert ids(match([trip(1, 0), trip(2, 61)])) == [[1], [2]]


def test_window_is_measured_from_the_groups_first_trip():
    # 0 and 50 match, 100 is 100 min after the first, so it starts a new group,
    # even though it is only 50 min after the second.
    assert ids(match([trip(1, 0), trip(2, 50), trip(3, 100)])) == [[1, 2], [3]]


def test_different_airports_or_directions_never_mix():
    trips = [trip(1), trip(2, airport="SFO"), trip(3, direction="from_airport")]
    assert sorted(len(g.trips) for g in match(trips)) == [1, 1, 1]


def test_groups_are_capped_at_four():
    groups = match([trip(i, i) for i in range(1, 7)])
    assert ids(groups) == [[1, 2, 3, 4], [5, 6]]


def test_same_person_twice_is_not_grouped_with_themself():
    groups = match([trip(1, 0, user_id=7), trip(2, 10, user_id=7)])
    assert ids(groups) == [[1], [2]]


def test_pickup_is_earliest_going_out_and_latest_coming_back():
    out = match([trip(1, 0), trip(2, 40)])[0]
    assert out.pickup_time == ideal_ride_time(trip(1, 0))  # don't make anyone miss a flight
    back = match([trip(1, 0, direction="from_airport"), trip(2, 40, direction="from_airport")])[0]
    assert back.pickup_time == ideal_ride_time(trip(2, 40, direction="from_airport"))  # wait for bags


def test_cost_is_split_evenly():
    group = RideGroup("SFO", "to_airport", (trip(1), trip(2)), NOON)
    assert group.cost_per_person == 35.0  # $70 fare / 2
    assert group.savings_per_person == 35.0


def test_input_order_does_not_change_the_result():
    trips = [trip(1, 0), trip(2, 20), trip(3, 90), trip(4, 100)]
    assert ids(match(trips)) == ids(match(list(reversed(trips))))


def test_group_for_trip():
    groups = match([trip(1, 0), trip(2, 200)])
    assert group_for_trip(groups, 2).trips[0].trip_id == 2
    assert group_for_trip(groups, 99) is None


def test_no_trips_no_groups():
    assert match([]) == []
