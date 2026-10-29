"""Sending email (the sign-up verification code).

Backends, chosen with the EMAIL_BACKEND setting:
  console  prints the email in the server log. For local development
           only: anyone who can read the log can see the codes.
  resend   sends real email through resend.com's API (needs your own
           domain to email anyone but yourself).
  smtp     sends through any mail server, e.g. Gmail with an app
           password, which needs no domain (about 500 emails a day).

Routes only ever call `mailer.send(...)`, so tests swap in a fake that
just records what would have been sent.
"""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from typing import Protocol

import httpx

from app.config import Settings

logger = logging.getLogger("breakrides.mail")


class MailError(Exception):
    pass


class Mailer(Protocol):
    def send(self, to: str, subject: str, text: str) -> None: ...


class ConsoleMailer:
    def send(self, to: str, subject: str, text: str) -> None:
        print(f"\n--- email to {to} ---\nSubject: {subject}\n\n{text}\n--- end email ---\n", flush=True)


class ResendMailer:
    URL = "https://api.resend.com/emails"

    def __init__(self, api_key: str, sender: str):
        if not api_key:
            raise ValueError("EMAIL_BACKEND=resend needs RESEND_API_KEY")
        self.api_key = api_key
        self.sender = sender

    def send(self, to: str, subject: str, text: str) -> None:
        try:
            response = httpx.post(
                self.URL,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"from": self.sender, "to": [to], "subject": subject, "text": text},
                timeout=10,
            )
        except httpx.HTTPError as exc:
            raise MailError("Couldn't reach the email service") from exc
        if response.status_code >= 300:
            # Log the status only: the response could echo the address.
            logger.error("Resend rejected an email (HTTP %s)", response.status_code)
            raise MailError("The email service rejected the message")


class SMTPMailer:
    def __init__(self, host: str, port: int, username: str, password: str, sender: str):
        if not (username and password):
            raise ValueError("EMAIL_BACKEND=smtp needs SMTP_USERNAME and SMTP_PASSWORD")
        self.host, self.port = host, port
        self.username, self.password = username, password
        self.sender = sender

    def send(self, to: str, subject: str, text: str) -> None:
        message = EmailMessage()
        message["From"] = self.sender
        message["To"] = to
        message["Subject"] = subject
        message.set_content(text)
        try:
            with smtplib.SMTP(self.host, self.port, timeout=10) as server:
                server.starttls()  # encrypt before sending the password
                server.login(self.username, self.password)
                server.send_message(message)
        except (smtplib.SMTPException, OSError) as exc:
            logger.error("SMTP send failed (%s)", type(exc).__name__)
            raise MailError("Couldn't send the email") from exc


def make_mailer(settings: Settings) -> Mailer:
    if settings.email_backend == "resend":
        return ResendMailer(settings.resend_api_key, settings.email_from)
    if settings.email_backend == "smtp":
        return SMTPMailer(
            settings.smtp_host, settings.smtp_port,
            settings.smtp_username, settings.smtp_password, settings.email_from,
        )
    if settings.email_backend != "console":
        raise ValueError(f"Unknown EMAIL_BACKEND {settings.email_backend!r}")
    return ConsoleMailer()
