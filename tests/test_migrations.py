"""The migrations must build exactly the schema the models describe.

If someone changes a model without adding a migration, production
(which only runs migrations) would break. This test catches that.
"""

import os

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import inspect

from app.db import Base, make_engine

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


def test_migrations_can_be_undone(tmp_path):
    url = f"sqlite:///{tmp_path / 'migrated.db'}"
    config = alembic_config(url)
    command.upgrade(config, "head")
    command.downgrade(config, "base")
    engine = make_engine(url)
    assert set(inspect(engine).get_table_names()) <= {"alembic_version"}
    engine.dispose()
