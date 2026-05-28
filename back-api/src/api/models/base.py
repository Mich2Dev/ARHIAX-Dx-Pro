"""
Base utilities for SQLAlchemy models.
Shared helpers and base configuration.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from api.db import Base


def _now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


def _uuid() -> str:
    """Generate UUID string."""
    return str(uuid.uuid4())


__all__ = ["Base", "_now", "_uuid"]
