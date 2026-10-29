# BreakRides

**Split a ride to the airport with other students flying out at the same time.**

> 🚧 In progress: week 4 of 6. See the [plan](docs/PLAN.md). Live demo and screenshots coming in week 5.

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

## Tests

```bash
pytest -v                    # backend
cd frontend && npm test      # frontend
```
