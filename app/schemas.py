"""Shapes of the JSON the API accepts and returns (validated by Pydantic).

Anything that doesn't match, like a misspelled airport or a flight time
without a timezone, is rejected with a 422 before our code ever runs.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import AwareDatetime, BaseModel, EmailStr, Field

Airport = Literal["SJC", "SFO", "OAK"]
Direction = Literal["to_airport", "from_airport"]


class SignupIn(BaseModel):
    email: EmailStr
    first_name: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=10, max_length=200)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(max_length=200)


class UserOut(BaseModel):
    id: int
    email: str
    first_name: str


class TripIn(BaseModel):
    airport: Airport
    direction: Direction
    # Must include a timezone, e.g. "2026-12-12T09:30:00-08:00".
    flight_time: AwareDatetime


class TripOut(BaseModel):
    id: int
    airport: Airport
    direction: Direction
    flight_time: datetime


class RiderOut(BaseModel):
    # First name only: no email or phone until riders confirm (week 4).
    first_name: str
    is_you: bool


class GroupOut(BaseModel):
    airport: Airport
    direction: Direction
    pickup_time: datetime
    matched: bool  # False if nobody else is on a nearby flight yet
    riders: list[RiderOut]
    fare_estimate: int
    cost_per_person: float
    savings_per_person: float
