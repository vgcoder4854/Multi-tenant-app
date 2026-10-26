"""Import every model so ``Base.metadata`` is complete.

Used by Alembic (``target_metadata``) and anywhere the full schema must be
registered. Importing this module has the side effect of registering all tables.
"""
from __future__ import annotations

from app.models import comms, identity, work, workflow

__all__ = ["identity", "work", "workflow", "comms"]
