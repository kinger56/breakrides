from app.db import normalize_url


def test_postgres_urls_get_the_psycopg_driver():
    neon = "postgresql://ben:secret@ep-cool-1.us-west-2.aws.neon.tech/breakrides?sslmode=require"
    assert normalize_url(neon) == (
        "postgresql+psycopg://ben:secret@ep-cool-1.us-west-2.aws.neon.tech/breakrides?sslmode=require"
    )
    assert normalize_url("postgres://u:p@host/db").startswith("postgresql+psycopg://")


def test_other_urls_are_unchanged():
    for url in ("sqlite://", "sqlite:///breakrides.db", "postgresql+psycopg://u:p@h/db"):
        assert normalize_url(url) == url
