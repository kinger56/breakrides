"""Settings, read from environment variables (or a local .env file).

Keeping settings out of the code means the same code runs on a laptop
(SQLite, plain http) and in production (Postgres, https) with no edits.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    database_url: str
    # Only students may sign up: emails must end in @<this domain>.
    allowed_email_domain: str
    session_days: int
    # Browsers only send "secure" cookies over https, so this must be off
    # for local http development and on in production.
    secure_cookies: bool
    # How emails are sent: "console" prints them in the server log
    # (development only), "resend" uses resend.com's API, "smtp" uses any
    # mail server, e.g. Gmail with an app password.
    email_backend: str = "console"
    resend_api_key: str = ""
    email_from: str = "BreakRides <onboarding@resend.dev>"
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    # Shown on the site as "Questions or feedback?" (hidden if empty).
    feedback_email: str = ""


def load_settings() -> Settings:
    return Settings(
        database_url=os.getenv("DATABASE_URL", "sqlite:///breakrides.db"),
        allowed_email_domain=os.getenv("ALLOWED_EMAIL_DOMAIN", "scu.edu").lower(),
        session_days=int(os.getenv("SESSION_DAYS", "30")),
        secure_cookies=os.getenv("SECURE_COOKIES", "false").lower() == "true",
        email_backend=os.getenv("EMAIL_BACKEND", "console"),
        resend_api_key=os.getenv("RESEND_API_KEY", ""),
        email_from=os.getenv("EMAIL_FROM", "BreakRides <onboarding@resend.dev>"),
        smtp_host=os.getenv("SMTP_HOST", "smtp.gmail.com"),
        smtp_port=int(os.getenv("SMTP_PORT", "587")),
        smtp_username=os.getenv("SMTP_USERNAME", ""),
        smtp_password=os.getenv("SMTP_PASSWORD", ""),
        feedback_email=os.getenv("FEEDBACK_EMAIL", ""),
    )
