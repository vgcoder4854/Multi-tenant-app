"""Audit log schemas."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID | None
    actor_id: uuid.UUID | None
    action: str
    resource_type: str | None
    resource_id: uuid.UUID | None
    # ORM attribute is `meta`; the API exposes it as `metadata`.
    meta: dict[str, Any] = Field(default_factory=dict, serialization_alias="metadata")
    created_at: datetime
