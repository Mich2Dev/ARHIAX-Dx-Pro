import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Build sync URL (no asyncpg)
_raw = os.getenv("DATABASE_URL", "postgresql://arhiax:arhiax@localhost:5432/arhiax_dx")
_sync_url = _raw.replace("+asyncpg", "")

# Import Base and models WITHOUT initializing the async engine
from api.db import Base  # noqa: E402
import api.models  # noqa: F401,E402

target_metadata = Base.metadata

config.set_main_option("sqlalchemy.url", _sync_url)


def run_migrations_offline() -> None:
    context.configure(url=_sync_url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(_sync_url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
