"""Notification schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import NotificationType


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID
    type: NotificationType
    title: str
    body: str | None
    resource_type: str | None
    resource_id: uuid.UUID | None
    is_read: bool
    created_at: datetime
    read_at: datetime | None


class UnreadCountOut(BaseModel):
    unread: int
