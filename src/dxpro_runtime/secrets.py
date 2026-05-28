"""Secret resolution from HashiCorp Vault (KV v2) with env-var fallback.

Resolution order:
1. If `VAULT_ADDR` is set, fetch from Vault. In production, a Vault failure
   is fatal — no silent fallback.
2. Otherwise, read from the named environment variable.
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Any

logger = logging.getLogger(__name__)


def resolve_secret(env_var: str, vault_key: str | None = None) -> str | None:
    """Resolve a secret by env var name and optional Vault key."""
    vault_value = _try_vault(vault_key) if vault_key else None
    if vault_value is not None:
        return vault_value
    return os.getenv(env_var) or None


def _try_vault(key: str) -> str | None:
    vault_addr = os.getenv("VAULT_ADDR")
    if not vault_addr:
        return None

    try:
        data = _load_vault_data(vault_addr)
    except Exception as exc:
        env = os.getenv("DXPRO_ENV", "development")
        if env == "production":
            raise RuntimeError(f"vault read failed in production: {exc}") from exc
        logger.warning("vault read failed in %s mode, falling back to env: %s", env, exc)
        return None

    value = data.get(key)
    return value if isinstance(value, str) and value else None


@lru_cache(maxsize=1)
def _load_vault_data(vault_addr: str) -> dict[str, Any]:
    """Load the configured KV-v2 secret blob once per process."""
    try:
        import hvac  # noqa: PLC0415
    except ImportError as exc:
        raise RuntimeError(
            "VAULT_ADDR is set but the 'hvac' package is not installed. "
            "Install with: pip install 'arhiax-dxpro-runtime[vault]'"
        ) from exc

    token = os.getenv("VAULT_TOKEN")
    if not token:
        raise RuntimeError("VAULT_TOKEN must be set when VAULT_ADDR is configured")

    mount = os.getenv("VAULT_MOUNT_POINT", "secret")
    path = os.getenv("VAULT_SECRET_PATH", "dxpro")

    client = hvac.Client(url=vault_addr, token=token)
    if not client.is_authenticated():
        raise RuntimeError("vault authentication failed")

    response = client.secrets.kv.v2.read_secret_version(
        path=path,
        mount_point=mount,
        raise_on_deleted_version=True,
    )
    return response["data"]["data"]
