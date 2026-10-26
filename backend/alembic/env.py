"""Alembic environment.

Reads DATABASE_URL from application settings (never hard-coded) and points
``target_metadata`` at the SQLAlchemy models.

While building the schema we generate migrations one group at a time by setting
``MODEL_GROUPS`` (e.g. ``MODEL_GROUPS=identity,work``). With no such variable the
full model registry is imported.
"""
from __future__ import annotations

import importlib
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import settings
from app.core.database import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Inject the URL from app settings.
config.set_main_option("sqlalchemy.url", settings.database_url)

# --- Import models (optionally a subset, for staged migrations) ---
_groups = os.environ.get("MODEL_GROUPS")
if _groups:
    for _g in _groups.split(","):
        importlib.import_module(f"app.models.{_g.strip()}")
else:
    import app.models.registry  # noqa: F401

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            # SQLite needs batch mode to alter tables later.
            render_as_batch=settings.is_sqlite,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
