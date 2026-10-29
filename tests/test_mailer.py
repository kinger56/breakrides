import httpx
import pytest

from app import mailer as mailer_module
from app.config import Settings
from app.mailer import ConsoleMailer, MailError, ResendMailer, make_mailer


def test_resend_sends_the_right_request(monkeypatch):
    calls = []

    def fake_post(url, headers, json, timeout):
        calls.append((url, headers, json))
        return httpx.Response(200)

    monkeypatch.setattr(mailer_module.httpx, "post", fake_post)
    ResendMailer("re_test_key", "BreakRides <rides@example.com>").send("ben@scu.edu", "Hi", "Body")
    url, headers, body = calls[0]
    assert url == "https://api.resend.com/emails"
    assert headers["Authorization"] == "Bearer re_test_key"
    assert body == {"from": "BreakRides <rides@example.com>", "to": ["ben@scu.edu"],
                    "subject": "Hi", "text": "Body"}


def test_resend_errors_become_mail_errors(monkeypatch):
    monkeypatch.setattr(mailer_module.httpx, "post", lambda *a, **k: httpx.Response(422))
    with pytest.raises(MailError):
        ResendMailer("key", "from@example.com").send("ben@scu.edu", "Hi", "Body")

    def offline(*a, **k):
        raise httpx.ConnectError("no network")

    monkeypatch.setattr(mailer_module.httpx, "post", offline)
    with pytest.raises(MailError):
        ResendMailer("key", "from@example.com").send("ben@scu.edu", "Hi", "Body")


def test_backend_is_chosen_by_settings():
    base = Settings("sqlite://", "scu.edu", 30, False)
    assert isinstance(make_mailer(base), ConsoleMailer)
    resend = Settings("sqlite://", "scu.edu", 30, False, email_backend="resend", resend_api_key="k")
    assert isinstance(make_mailer(resend), ResendMailer)
    with pytest.raises(ValueError):
        make_mailer(Settings("sqlite://", "scu.edu", 30, False, email_backend="resend"))
