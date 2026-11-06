from app.db import normalize_url

# normalize_url only rewrites the scheme at the front, so these test URLs
# deliberately contain no username or password: test data should never
# look like a real credential.
HOST = "db.example.com/breakrides?sslmode=require"


def test_postgres_urls_get_the_psycopg_driver():
    expected = "postgresql+psycopg://" + HOST
    assert normalize_url("postgresql://" + HOST) == expected
    assert normalize_url("postgres://" + HOST) == expected


def test_other_urls_are_unchanged():
    for url in ("sqlite://", "sqlite:///breakrides.db", "postgresql+psycopg://" + HOST):
        assert normalize_url(url) == url
