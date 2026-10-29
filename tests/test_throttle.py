from app.throttle import Throttle
from tests.conftest import PASSWORD, signup


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def test_throttle_blocks_after_limit_then_recovers():
    clock = FakeClock()
    t = Throttle(limit=3, window_seconds=60, clock=clock)
    for _ in range(3):
        assert t.retry_after("k") == 0
        t.record("k")
    assert t.retry_after("k") > 0
    clock.now += 61
    assert t.retry_after("k") == 0


def test_keys_are_independent_and_reset_works():
    t = Throttle(limit=1, window_seconds=60, clock=FakeClock())
    t.record("a")
    assert t.retry_after("a") > 0 and t.retry_after("b") == 0
    t.reset("a")
    assert t.retry_after("a") == 0


# ---- login -------------------------------------------------------------------


def wrong_login(client, email="ben@scu.edu"):
    return client.post("/api/auth/login", json={"email": email, "password": "wrong-password!!"})


def test_five_wrong_passwords_lock_the_account_for_a_while(client):
    signup(client)
    client.cookies.clear()
    for _ in range(5):
        assert wrong_login(client).status_code == 401
    blocked = wrong_login(client)
    assert blocked.status_code == 429
    assert int(blocked.headers["retry-after"]) > 0
    # Even the right password is refused while locked: otherwise guessing
    # would just continue until it hit.
    right = client.post("/api/auth/login", json={"email": "ben@scu.edu", "password": PASSWORD})
    assert right.status_code == 429


def test_lock_expires(client, app):
    signup(client)
    client.cookies.clear()
    for _ in range(5):
        wrong_login(client)
    for throttle in (app.state.account_throttle, app.state.ip_throttle):
        throttle._clock = lambda: 10**9  # jump far into the future
    ok = client.post("/api/auth/login", json={"email": "ben@scu.edu", "password": PASSWORD})
    assert ok.status_code == 200


def test_successful_login_clears_earlier_failures(client):
    signup(client)
    client.cookies.clear()
    for _ in range(4):
        wrong_login(client)
    client.post("/api/auth/login", json={"email": "ben@scu.edu", "password": PASSWORD})
    client.cookies.clear()
    for _ in range(4):
        assert wrong_login(client).status_code == 401  # counter started over


def test_one_ip_guessing_many_accounts_is_blocked(client):
    for i in range(20):
        wrong_login(client, email=f"student{i}@scu.edu")
    assert wrong_login(client, email="someone-new@scu.edu").status_code == 429
