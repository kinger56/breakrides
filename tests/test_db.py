from app.db import normalize_url


def test_postgres_urls_get_the_psycopg_driver():
    neon = "postgresql://db.example.com/breakrides?sslmode=require"
    assert normalize_url(neon) == (
        "postgresql+psycopg://db.example.com/breakrides?sslmode=require"
    )
    assert normalize_url("postgres://host/db").startswith("postgresql+psycopg://")


def test_other_urls_are_unchanged():
    for url in ("sqlite://", "sqlite:///breakrides.db", "postgresql+psycopg://h/db"):
        assert normalize_url(url) == url
