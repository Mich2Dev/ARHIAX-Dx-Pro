"""
Seed script — creates the default admin user if no users exist.
Run automatically on startup via pipeline_runner or call directly:
  python -m api.seed
"""
from __future__ import annotations

import asyncio
import logging
import os

log = logging.getLogger("arhiax.seed")


async def seed_admin() -> None:
    from sqlalchemy import select
    from api.db import get_async_session_local, get_engine
    from api.models import User
    from api.auth import hash_password

    get_engine()
    SessionLocal = get_async_session_local()

    email    = os.getenv("SEED_ADMIN_EMAIL",    "admin@arhiax.com")
    password = os.getenv("SEED_ADMIN_PASSWORD", "arhiax-admin-2026")
    name     = os.getenv("SEED_ADMIN_NAME",     "Admin ARHIAX")

    async with SessionLocal() as db:
        existing = await db.execute(select(User))
        if existing.scalars().first():
            log.info("Seed skipped — users already exist")
            return

        user = User(
            email=email,
            name=name,
            role="admin",
            hashed_password=hash_password(password),
        )
        db.add(user)
        await db.commit()
        log.info("Seed admin created: %s / %s", email, password)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(seed_admin())
