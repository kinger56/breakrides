# BreakRides: 6-week plan

**Goal:** Santa Clara students heading to or from SJC, SFO or OAK over a school break
enter their flight, get matched with other students leaving at about the same time, and
split one rideshare instead of each paying for their own.

**Target:** a working pilot for **winter break 2026** (finals end around Dec 11), with
real students using it. "Matched N riders, saving about $X" is the line for the README
and resume.

Assumes about 8–10 hours a week. Each week ends with something that runs and is committed.

| Week | Dates (2026) | Focus | Done when |
|---|---|---|---|
| 1 | Oct 29 – Nov 4 | **Backend foundation** | Sign up, log in, add and delete trips through the API. Passwords hashed, sessions in the database, tests passing. |
| 2 | Nov 5 – 11 | **Matching engine** | Trips grouped by airport, direction and time window into groups of at most 4, with an estimated cost per person. Property-based tests prove the grouping rules. |
| 3 | Nov 12 – 18 | **React frontend** | Mobile-first pages: sign up / log in, "add my flight", "my ride group". Uses the API from weeks 1–2. |
| 4 | Nov 19 – 25 | **Trust and safety** | School-email verification (an email API such as Resend), riders confirm a group before contact info is shared, rate limiting on login. |
| 5 | Nov 26 – Dec 2 | **Deploy** | Live on Render with a free Postgres database (e.g. Neon), database migrations (Alembic), CI on GitHub Actions. Test with friends over Thanksgiving break. |
| 6 | Dec 3 – 9 | **Pilot and polish** | Share with SCU students before winter break. Fix what they report, record match and savings numbers, write the README with screenshots. |

## Stretch goals (after the pilot)
- Google Maps travel time, so the suggested pickup time accounts for traffic
- Group chat, or a one-tap "share a ride" link into Uber/Lyft
- Text a reminder the night before the ride

## Key design decisions
- **Python + FastAPI backend** (builds on Setlist Predictor), **React + TypeScript frontend** (the most-requested frontend skills in internship listings).
- **SQLAlchemy** talks to SQLite locally and in tests, and to PostgreSQL in production, with the same code.
- **Matching is a pure function** (`app/matching.py`): trips in, groups out, no database. It can be tested on its own, like Setlist Predictor's predictor.
- **Privacy first:** before a group is confirmed, other riders see only a first name and pickup time, never an email or phone number.
