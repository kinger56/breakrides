"""Alembic setup: which database to migrate, and what the tables should be.

The URL comes from the same DATABASE_URL setting the app uses, so
`alembic upgrade head` migrates whichever database the app would use.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool

from app import models  # noqa: F401  (registers the tables on Base.metadata)
from app.config import load_settings
from app.db import Base, make_engine, normalize_url

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def database_url() -> str:
    # Tests pass a URL in directly; otherwise use the app's setting.
    return config.attributes.get("database_url") or load_settings().database_url


def run_migrations_offline() -> None:
    """Print the SQL instead of running it (`alembic upgrade head --sql`)."""
    context.configure(
        url=normalize_url(database_url()),
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = make_engine(database_url())
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # SQLite can't alter tables in place; batch mode rebuilds them.
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
