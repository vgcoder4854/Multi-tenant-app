"""Shared schema helpers (pagination envelope, etc.)."""
from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """Standard paginated response: ``{items, total, page, page_size}``."""

    items: list[T]
    total: int
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)


class Message(BaseModel):
    """Generic simple message response."""

    detail: str
