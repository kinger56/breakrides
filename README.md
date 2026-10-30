# BreakRides

[![tests](https://github.com/kinger56/breakrides/actions/workflows/tests.yml/badge.svg)](https://github.com/kinger56/breakrides/actions/workflows/tests.yml)

**Split a ride to the airport with other students flying out at the same time.**

**Live: [breakrides.onrender.com](https://breakrides.onrender.com)** (Santa Clara `@scu.edu` emails only)
<sub>Hosted on Render's free tier: if nobody has visited in 15 minutes, the first load takes about a minute.</sub>

> 🚧 Week 5 of 6: deployed. Next: a pilot with real students before winter break. See the [plan](docs/PLAN.md).

<p align="center"><img src="docs/screenshot-confirmed-group.jpg" alt="A confirmed ride group: pickup time, both riders confirmed, $35 each instead of $70, and the other rider's email" width="300"></p>

Santa Clara students heading to or from SJC, SFO or OAK over a break add their flight.
BreakRides matches them with students on nearby flights into groups of up to 4 and shows
how much each person saves by sharing one rideshare.

## What works so far
- Accounts limited to `@scu.edu` emails, **verified with a 6-digit emailed code**, with salted scrypt password hashing and secure session cookies
- **Confirm before contact is shared:** each rider confirms their group; once everyone has, the group locks and members see each other's email. If the group changes first, earlier confirmations stop counting.
- **Login rate limiting** (5 failures per account, 20 per IP, per 15 minutes)
- Add, list and delete your flights
- **Matching engine:** groups trips by airport, direction and a 60-minute window, picks a pickup time that gets everyone there on time, and splits the estimated fare
- **React + TypeScript frontend:** sign up, add a flight, and see your ride group with pickup time and savings. Mobile-first, with light and dark mode.
- 70 backend tests (including property-based tests showing the matcher always produces the fewest possible groups) and frontend tests for Pacific-time handling

## Run it locally

You'll need Python 3.12+ and Node.js.

```bash
# Backend (terminal 1)
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload       # API on :8000, docs at /docs

# Frontend (terminal 2)
cd frontend
npm install
npm run dev                         # open http://localhost:5173
```

In development, Vite forwards `/api` requests to FastAPI. For production, `npm run build` creates `frontend/dist`, and FastAPI serves it from the same server as the API.

## Deploy (Render + Neon)

`render.yaml` describes the service. In production:

- **Database:** PostgreSQL on [Neon](https://neon.tech) (free tier). Tables come from Alembic migrations (`migrations/`), which run on every start, so schema changes keep existing data.
- **Email:** `EMAIL_BACKEND=smtp` with a Gmail app password (no domain needed), or `resend` with a verified domain.
- **Safety:** https-only cookies, deploys only after CI passes, and the visitor's real IP is read from Render's proxy headers so per-IP login limits work.

Secrets (`DATABASE_URL`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `EMAIL_FROM`) are entered in Render's dashboard and never committed.

## Tests

```bash
pytest -v                    # backend (SQLite)
TEST_DATABASE_URL=postgresql://user:pass@localhost/test pytest   # backend on Postgres
cd frontend && npm test      # frontend
```

CI runs the backend tests on both SQLite and PostgreSQL, and checks that the migrations produce exactly the schema the models describe.
