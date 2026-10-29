# BreakRides

**Split a ride to the airport with other students flying out at the same time.**

> 🚧 In progress: week 2 of 6. See the [plan](docs/PLAN.md). Live demo and screenshots coming in week 5.

Santa Clara students heading to or from SJC, SFO or OAK over a break add their flight.
BreakRides matches them with students on nearby flights into groups of up to 4 and shows
how much each person saves by sharing one rideshare.

## What works so far
- Accounts limited to `@scu.edu` emails, with salted scrypt password hashing and secure session cookies
- Add, list and delete your flights
- **Matching engine:** groups trips by airport, direction and a 60-minute window, picks a pickup time that gets everyone there on time, and splits the estimated fare
- 42 tests, including property-based tests showing the matcher always produces the fewest possible groups

## Run it locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs to try the API in your browser.

## Tests

```bash
pytest -v
```
