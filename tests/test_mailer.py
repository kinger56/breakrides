import httpx
import pytest

from app import mailer as mailer_module
from app.config import Settings
from app.mailer import ConsoleMailer, MailError, ResendMailer, SMTPMailer, make_mailer


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


class FakeSMTP:
    instances = []

    def __init__(self, host, port, timeout):
        self.host, self.port, self.steps = host, port, []
        FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self):
        self.steps.append("starttls")

    def login(self, user, password):
        self.steps.append(("login", user, password))

    def send_message(self, message):
        self.steps.append(("send", message["To"], message["Subject"], message.get_content()))


def test_smtp_encrypts_before_logging_in_and_sends(monkeypatch):
    monkeypatch.setattr(mailer_module.smtplib, "SMTP", FakeSMTP)
    FakeSMTP.instances.clear()
    SMTPMailer("smtp.gmail.com", 587, "rides@gmail.com", "app-pass", "BreakRides <rides@gmail.com>").send(
        "ben@scu.edu", "Your code", "123456"
    )
    smtp = FakeSMTP.instances[0]
    assert (smtp.host, smtp.port) == ("smtp.gmail.com", 587)
    assert smtp.steps[0] == "starttls"  # never send the password unencrypted
    assert smtp.steps[1] == ("login", "rides@gmail.com", "app-pass")
    assert smtp.steps[2] == ("send", "ben@scu.edu", "Your code", "123456\n")


def test_smtp_failures_become_mail_errors(monkeypatch):
    def refuse(*a, **k):
        raise OSError("connection refused")

    monkeypatch.setattr(mailer_module.smtplib, "SMTP", refuse)
    with pytest.raises(MailError):
        SMTPMailer("h", 587, "u", "p", "f").send("ben@scu.edu", "s", "t")


def test_smtp_and_unknown_backends():
    smtp = Settings("sqlite://", "scu.edu", 30, False, email_backend="smtp",
                    smtp_username="u", smtp_password="p")
    assert isinstance(make_mailer(smtp), SMTPMailer)
    with pytest.raises(ValueError):
        make_mailer(Settings("sqlite://", "scu.edu", 30, False, email_backend="smtp"))
    with pytest.raises(ValueError):
        make_mailer(Settings("sqlite://", "scu.edu", 30, False, email_backend="carrier-pigeon"))
