"""Sending email (the sign-up verification code).

Two backends, chosen with the EMAIL_BACKEND setting:
  console  prints the email in the server log. For local development
           only: anyone who can read the log can see the codes.
  resend   sends real email through resend.com's API (free tier).

Routes only ever call `mailer.send(...)`, so tests swap in a fake that
just records what would have been sent.
"""

from __future__ import annotations

import logging
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


def make_mailer(settings: Settings) -> Mailer:
    if settings.email_backend == "resend":
        return ResendMailer(settings.resend_api_key, settings.email_from)
    return ConsoleMailer()
