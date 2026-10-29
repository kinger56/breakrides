"""The migrations must build exactly the schema the models describe.

If someone changes a model without adding a migration, production
(which only runs migrations) would break. This test catches that.
"""

import os

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import inspect

from app.db import Base, make_engine
from tests.conftest import TEST_DATABASE_URL

ROOT = os.path.dirname(os.path.dirname(__file__))


def alembic_config(url):
    config = Config(os.path.join(ROOT, "alembic.ini"))
    config.set_main_option("script_location", os.path.join(ROOT, "migrations"))
    config.attributes["database_url"] = url
    return config


def test_migrations_match_the_models(tmp_path):
    url = f"sqlite:///{tmp_path / 'migrated.db'}"
    command.upgrade(alembic_config(url), "head")
    engine = make_engine(url)
    with engine.connect() as connection:
        differences = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    engine.dispose()
    assert differences == [], f"models changed without a migration: {differences}"


@pytest.mark.skipif(TEST_DATABASE_URL.startswith("sqlite"), reason="needs TEST_DATABASE_URL=postgres")
def test_migrations_on_postgres():
    """Same check on real Postgres (CI sets TEST_DATABASE_URL)."""
    engine = make_engine(TEST_DATABASE_URL)
    Base.metadata.drop_all(engine)  # tables left by other tests
    with engine.begin() as connection:
        connection.exec_driver_sql("DROP TABLE IF EXISTS alembic_version")
    config = alembic_config(TEST_DATABASE_URL)
    command.upgrade(config, "head")
    with engine.connect() as connection:
        differences = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    command.downgrade(config, "base")
    engine.dispose()
    assert differences == [], f"models changed without a migration: {differences}"


def test_migrations_can_be_undone(tmp_path):
    url = f"sqlite:///{tmp_path / 'migrated.db'}"
    config = alembic_config(url)
    command.upgrade(config, "head")
    command.downgrade(config, "base")
    engine = make_engine(url)
    assert set(inspect(engine).get_table_names()) <= {"alembic_version"}
    engine.dispose()
