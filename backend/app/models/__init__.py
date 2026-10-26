"""ORM models package.

Submodules are imported explicitly where needed (e.g. ``from app.models.identity
import User``). The package ``__init__`` is intentionally empty so that Alembic can
import schema groups one at a time while generating staged migrations; see
``app/models/registry.py`` for the "import everything" entry point.
"""
