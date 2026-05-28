"""User model - Authentication and authorization."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, _now, _uuid


class User(Base):
    """
    User model for authentication and authorization.
    
    Roles:
    - operator: Can create and view diagnostics
    - reviewer: Can review and approve diagnostics
    - admin: Full system access
    """
    __tablename__ = "users"

    id: Mapped[str]      = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    email: Mapped[str]   = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str]    = mapped_column(String, nullable=False)
    role: Mapped[str]    = mapped_column(String, default="operator")  # operator | reviewer | admin
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


__all__ = ["User"]
