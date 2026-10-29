"""The web API, built with FastAPI.

Routes:
  POST   /api/auth/signup   create an account (school email only) and log in
  POST   /api/auth/login    log in
  POST   /api/auth/logout   log out
  GET    /api/me            who am I?
  POST   /api/trips         add a flight I need a ride for
  GET    /api/trips         my upcoming trips
  DELETE /api/trips/{id}    remove one of my trips
  GET    /api/trips/{id}/group  who I'm sharing a ride with for that trip
  GET    /api/health        {"status": "ok"} for the host's health check

Run locally:  uvicorn app.main:app --reload   (docs at /docs)
"""

from __future__ import annotations

from datetime import timedelta, timezone
from pathlib import Path
from typing import Iterator

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.staticfiles import StaticFiles
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app import security
from app.config import Settings, load_settings
from app.matching import FARE_ESTIMATE, TripRequest, group_for_trip, match
from app.db import Base, make_engine, make_session_factory, session_scope
from app.models import LoginSession, Trip, User, utcnow
from app.schemas import GroupOut, LoginIn, RiderOut, SignupIn, TripIn, TripOut, UserOut

# The React app, built by `npm run build` in frontend/.
FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"
SESSION_COOKIE = "session"
# Flights further out than this are almost certainly typos (wrong year).
MAX_DAYS_AHEAD = 365


def create_app(settings: Settings | None = None, frontend_dist: Path = FRONTEND_DIST) -> FastAPI:
    """Build the app. Tests call this with their own settings (an in-memory
    database), so they never touch the real one."""
    settings = settings or load_settings()
    engine = make_engine(settings.database_url)
    # Creates missing tables. Fine for now; week 5 switches to Alembic
    # migrations so the schema can change without losing data.
    Base.metadata.create_all(engine)

    app = FastAPI(title="BreakRides")
    app.state.settings = settings
    app.state.session_factory = make_session_factory(engine)
    _add_routes(app)
    # Serve the built React app at "/", from the same server as the API, so
    # the login cookie works without any cross-site setup. Mounted last, so
    # /api routes take priority. Skipped if the frontend hasn't been built.
    if frontend_dist.is_dir():
        app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
    return app


# --------------------------------------------------------------------------
# Dependencies
# --------------------------------------------------------------------------


def get_db(request: Request) -> Iterator[Session]:
    yield from session_scope(request.app.state.session_factory)


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """The logged-in user, or a 401 error. Routes that need a login just
    ask for `user: User = Depends(current_user)`."""
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        login = db.scalar(
            select(LoginSession).where(LoginSession.token_hash == security.hash_token(token))
        )
        if login and login.expires_at > utcnow():
            return login.user
    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Please log in.")


def _start_session(response: Response, user: User, db: Session, settings: Settings) -> None:
    token = security.new_session_token()
    db.add(
        LoginSession(
            token_hash=security.hash_token(token),
            user_id=user.id,
            expires_at=utcnow() + timedelta(days=settings.session_days),
        )
    )
    db.commit()
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=settings.session_days * 86400,
        httponly=True,  # page JavaScript can't read it, so XSS can't steal it
        samesite="lax",  # not sent on cross-site form posts (CSRF protection)
        secure=settings.secure_cookies,
    )


def _user_out(user: User) -> UserOut:
    return UserOut(id=user.id, email=user.email, first_name=user.first_name)


def _trip_out(trip: Trip) -> TripOut:
    return TripOut(
        id=trip.id,
        airport=trip.airport,
        direction=trip.direction,
        # Always answer in UTC, whatever timezone the trip was sent in.
        flight_time=trip.flight_time.astimezone(timezone.utc),
    )


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------


def _add_routes(app: FastAPI) -> None:
    settings: Settings = app.state.settings

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.post("/api/auth/signup", status_code=201)
    def signup(body: SignupIn, response: Response, db: Session = Depends(get_db)) -> UserOut:
        email = body.email.lower()
        if not email.endswith("@" + settings.allowed_email_domain):
            raise HTTPException(
                422, f"Please sign up with your @{settings.allowed_email_domain} email."
            )
        user = User(
            email=email,
            first_name=body.first_name.strip(),
            password_hash=security.hash_password(body.password),
        )
        db.add(user)
        try:
            db.commit()
        except IntegrityError:  # the unique constraint on email
            db.rollback()
            raise HTTPException(409, "An account with that email already exists.")
        _start_session(response, user, db, settings)
        return _user_out(user)

    @app.post("/api/auth/login")
    def login(body: LoginIn, response: Response, db: Session = Depends(get_db)) -> UserOut:
        user = db.scalar(select(User).where(User.email == body.email.lower()))
        # Same message whether the email or the password is wrong, so the
        # login form can't be used to find out who has an account.
        if user is None or not security.verify_password(body.password, user.password_hash):
            raise HTTPException(401, "Wrong email or password.")
        _start_session(response, user, db, settings)
        return _user_out(user)

    @app.post("/api/auth/logout", status_code=204)
    def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> None:
        token = request.cookies.get(SESSION_COOKIE)
        if token:
            db.execute(
                delete(LoginSession).where(LoginSession.token_hash == security.hash_token(token))
            )
            db.commit()
        response.delete_cookie(SESSION_COOKIE)

    @app.get("/api/me")
    def me(user: User = Depends(current_user)) -> UserOut:
        return _user_out(user)

    @app.post("/api/trips", status_code=201)
    def add_trip(
        body: TripIn, user: User = Depends(current_user), db: Session = Depends(get_db)
    ) -> TripOut:
        now = utcnow()
        if body.flight_time <= now:
            raise HTTPException(422, "That flight time is in the past.")
        if body.flight_time > now + timedelta(days=MAX_DAYS_AHEAD):
            raise HTTPException(422, "That flight is more than a year away. Check the year?")
        trip = Trip(
            user_id=user.id,
            airport=body.airport,
            direction=body.direction,
            flight_time=body.flight_time,
        )
        db.add(trip)
        db.commit()
        return _trip_out(trip)

    @app.get("/api/trips")
    def my_trips(user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[TripOut]:
        trips = db.scalars(
            select(Trip)
            .where(Trip.user_id == user.id, Trip.flight_time > utcnow())
            .order_by(Trip.flight_time)
        )
        return [_trip_out(t) for t in trips]

    @app.delete("/api/trips/{trip_id}", status_code=204)
    def delete_trip(
        trip_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
    ) -> None:
        trip = db.get(Trip, trip_id)
        # 404 (not 403) for other people's trips too, so IDs can't be probed.
        if trip is None or trip.user_id != user.id:
            raise HTTPException(404, "Trip not found.")
        db.delete(trip)
        db.commit()

    @app.get("/api/trips/{trip_id}/group")
    def ride_group(
        trip_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
    ) -> GroupOut:
        trip = db.get(Trip, trip_id)
        if trip is None or trip.user_id != user.id:
            raise HTTPException(404, "Trip not found.")

        # Match every upcoming trip on the same route. Groups are worked out
        # fresh each time, so they can change as people add trips; letting
        # riders confirm a group (and lock it) comes in week 4.
        route = db.scalars(
            select(Trip)
            .options(joinedload(Trip.user))
            .where(
                Trip.airport == trip.airport,
                Trip.direction == trip.direction,
                Trip.flight_time > utcnow(),
            )
        )
        requests = [
            TripRequest(t.id, t.user_id, t.user.first_name, t.airport, t.direction, t.flight_time)
            for t in route
        ]
        group = group_for_trip(match(requests), trip.id)
        if group is None:  # the trip's flight has already left
            raise HTTPException(404, "This trip is in the past.")

        return GroupOut(
            airport=group.airport,
            direction=group.direction,
            pickup_time=group.pickup_time.astimezone(timezone.utc),
            matched=group.size > 1,
            riders=[RiderOut(first_name=t.first_name, is_you=t.user_id == user.id) for t in group.trips],
            fare_estimate=FARE_ESTIMATE[group.airport],
            cost_per_person=group.cost_per_person,
            savings_per_person=group.savings_per_person,
        )


app = create_app()
