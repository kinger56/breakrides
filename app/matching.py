"""The matching engine: which students should share a ride?

Every function here is *pure*: trips in, ride groups out. No database, no
network, no clock. That makes the core logic easy to test and explain.

The rules
---------
Two trips can share a ride if they go to/from the same airport in the same
direction, and their ideal ride times are within `window` of each other.
A group has at most `max_size` riders (4 fit in a regular Uber/Lyft).

Ideal ride time:
  to the airport:   flight time - (2 hours at the airport + drive time)
  from the airport: flight time + 45 minutes to deplane and get bags

The algorithm (greedy)
----------------------
Sort trips by ride time. Start a group with the earliest trip, keep adding
the next trip while it is within `window` of the group's first trip and the
group isn't full, then start a new group. For points on a line, this greedy
approach is proven to produce the fewest possible groups, and a
property-based test checks it against brute force.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta

DEFAULT_WINDOW = timedelta(minutes=60)
DEFAULT_MAX_SIZE = 4

TIME_AT_AIRPORT_BEFORE_FLIGHT = timedelta(hours=2)
TIME_TO_DEPLANE = timedelta(minutes=45)
# Typical drive time from Santa Clara University.
DRIVE_TIME = {
    "SJC": timedelta(minutes=15),
    "SFO": timedelta(minutes=50),
    "OAK": timedelta(minutes=50),
}
# Rough one-way rideshare fare from campus, in dollars. Estimates only:
# real fares change with demand. Used to show how much sharing saves.
FARE_ESTIMATE = {"SJC": 25, "SFO": 70, "OAK": 75}


@dataclass(frozen=True)
class TripRequest:
    trip_id: int
    user_id: int
    first_name: str
    airport: str
    direction: str  # "to_airport" or "from_airport"
    flight_time: datetime


@dataclass(frozen=True)
class RideGroup:
    airport: str
    direction: str
    trips: tuple[TripRequest, ...]
    pickup_time: datetime  # when the shared ride leaves

    @property
    def size(self) -> int:
        return len(self.trips)

    @property
    def cost_per_person(self) -> float:
        return round(FARE_ESTIMATE[self.airport] / self.size, 2)

    @property
    def savings_per_person(self) -> float:
        return round(FARE_ESTIMATE[self.airport] - self.cost_per_person, 2)


def ideal_ride_time(trip: TripRequest) -> datetime:
    if trip.direction == "to_airport":
        return trip.flight_time - TIME_AT_AIRPORT_BEFORE_FLIGHT - DRIVE_TIME[trip.airport]
    return trip.flight_time + TIME_TO_DEPLANE


def _pickup_time(direction: str, trips: list[TripRequest]) -> datetime:
    times = [ideal_ride_time(t) for t in trips]
    # Going to the airport, leave when the earliest flight needs to, so
    # nobody misses their flight. Coming back, leave once the last person
    # has their bags.
    return min(times) if direction == "to_airport" else max(times)


def match(
    trips: list[TripRequest],
    window: timedelta = DEFAULT_WINDOW,
    max_size: int = DEFAULT_MAX_SIZE,
) -> list[RideGroup]:
    """Group trips into shared rides. Every trip ends up in exactly one
    group; a trip with no match gets a group of one."""
    by_route: dict[tuple[str, str], list[TripRequest]] = defaultdict(list)
    for trip in trips:
        by_route[(trip.airport, trip.direction)].append(trip)

    groups: list[RideGroup] = []
    # Sorted so the output is the same every time, whatever the input order.
    for (airport, direction), route_trips in sorted(by_route.items()):
        # Ties broken by trip_id, again so results are stable.
        route_trips.sort(key=lambda t: (ideal_ride_time(t), t.trip_id))
        current: list[TripRequest] = []
        for trip in route_trips:
            fits = (
                current
                and len(current) < max_size
                and ideal_ride_time(trip) - ideal_ride_time(current[0]) <= window
                # Someone who entered the same flight twice can't ride with themself.
                and all(t.user_id != trip.user_id for t in current)
            )
            if not fits and current:
                groups.append(RideGroup(airport, direction, tuple(current), _pickup_time(direction, current)))
                current = []
            current.append(trip)
        if current:
            groups.append(RideGroup(airport, direction, tuple(current), _pickup_time(direction, current)))
    return groups


def group_for_trip(groups: list[RideGroup], trip_id: int) -> RideGroup | None:
    for group in groups:
        if any(t.trip_id == trip_id for t in group.trips):
            return group
    return None
