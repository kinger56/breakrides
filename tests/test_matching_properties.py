"""Property-based tests: rules the matcher must follow for EVERY input.
Hypothesis generates hundreds of random sets of trips to try to break them."""

from datetime import datetime, timedelta, timezone
from itertools import combinations

from hypothesis import given, settings
from hypothesis import strategies as st

from app.matching import DEFAULT_MAX_SIZE, DEFAULT_WINDOW, TripRequest, ideal_ride_time, match

START = datetime(2026, 12, 10, tzinfo=timezone.utc)


def make_trips(raw, distinct_users=True):
    return [
        TripRequest(
            trip_id=i,
            user_id=i if distinct_users else user,
            first_name="x",
            airport=airport,
            direction=direction,
            flight_time=START + timedelta(minutes=minutes),
        )
        for i, (minutes, airport, direction, user) in enumerate(raw)
    ]


raw_trips = st.lists(
    st.tuples(
        st.integers(0, 8 * 60),  # flights packed into 8 hours, so groups form often
        st.sampled_from(["SJC", "SFO", "OAK"]),
        st.sampled_from(["to_airport", "from_airport"]),
        st.integers(0, 5),  # user, when testing repeat users
    ),
    max_size=40,
)


@settings(max_examples=300)
@given(raw=raw_trips, distinct=st.booleans())
def test_every_group_follows_the_rules(raw, distinct):
    trips = make_trips(raw, distinct)
    groups = match(trips)

    # Every trip is in exactly one group.
    placed = sorted(t.trip_id for g in groups for t in g.trips)
    assert placed == sorted(t.trip_id for t in trips)

    for g in groups:
        assert 1 <= g.size <= DEFAULT_MAX_SIZE
        assert {(t.airport, t.direction) for t in g.trips} == {(g.airport, g.direction)}
        times = [ideal_ride_time(t) for t in g.trips]
        assert max(times) - min(times) <= DEFAULT_WINDOW
        assert len({t.user_id for t in g.trips}) == g.size  # nobody rides with themself
        # Pickup never makes anyone late: before every flight's ideal time
        # going out, after everyone has landed coming back.
        if g.direction == "to_airport":
            assert all(g.pickup_time <= t for t in times)
        else:
            assert all(g.pickup_time >= t for t in times)


def fewest_groups_brute_force(times, window, max_size):
    """Try every way to split the trips into groups (fine for tiny inputs)."""
    n = len(times)
    best = {0: 0}
    for mask in range(1, 1 << n):
        members = [times[i] for i in range(n) if mask >> i & 1]
        options = []
        lowest = mask & -mask  # always put the lowest-numbered trip in the next group
        rest = mask ^ lowest
        others = [i for i in range(n) if rest >> i & 1]
        for k in range(min(max_size, len(members)) ):
            for combo in combinations(others, k):
                group = lowest | sum(1 << i for i in combo)
                ts = [times[i] for i in range(n) if group >> i & 1]
                if max(ts) - min(ts) <= window:
                    options.append(best[mask ^ group] + 1)
        best[mask] = min(options)
    return best[(1 << n) - 1]


@settings(max_examples=200)
@given(minutes=st.lists(st.integers(0, 300), min_size=1, max_size=7))
def test_greedy_uses_the_fewest_possible_groups(minutes):
    # One airport and direction, different people: compare against brute force.
    trips = make_trips([(m, "SJC", "to_airport", 0) for m in minutes])
    times = [ideal_ride_time(t) for t in trips]
    assert len(match(trips)) == fewest_groups_brute_force(times, DEFAULT_WINDOW, DEFAULT_MAX_SIZE)
