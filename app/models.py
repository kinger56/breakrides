"""Database tables.

  users     students who signed up
  sessions  who is logged in (one row per logged-in browser)
  trips     one flight a student needs a ride for
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, UTCDateTime

AIRPORTS = ("SJC", "SFO", "OAK")
DIRECTIONS = ("to_airport", "from_airport")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    first_name: Mapped[str] = mapped_column(String(50))
    password_hash: Mapped[str] = mapped_column(String(255))
    # True once they've entered the code we emailed: proof they own the inbox.
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    trips: Mapped[list[Trip]] = relationship(back_populates="user", cascade="all, delete-orphan")


class LoginSession(Base):
    """A logged-in browser. The browser holds a random token in a cookie;
    we store only a hash of it, so a leaked database can't log anyone in."""

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)

    user: Mapped[User] = relationship()


class EmailCode(Base):
    """The 6-digit code emailed to a new user. Stored only as a hash, it
    expires after 15 minutes and allows 5 wrong tries."""

    __tablename__ = "email_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    code_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)
    attempts: Mapped[int] = mapped_column(Integer, default=0)


class Trip(Base):
    __tablename__ = "trips"
    # The database itself rejects bad values, even if a bug skips validation.
    __table_args__ = (
        CheckConstraint(f"airport IN {AIRPORTS}", name="valid_airport"),
        CheckConstraint(f"direction IN {DIRECTIONS}", name="valid_direction"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    airport: Mapped[str] = mapped_column(String(3))
    direction: Mapped[str] = mapped_column(String(12))
    flight_time: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    user: Mapped[User] = relationship(back_populates="trips")
