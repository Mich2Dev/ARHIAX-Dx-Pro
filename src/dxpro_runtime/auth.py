"""API key authentication with constant-time comparison."""

from __future__ import annotations

import hashlib
import hmac
from collections.abc import Iterable

from fastapi import HTTPException
from fastapi.security import APIKeyHeader

API_KEY_HEADER = "X-API-Key"

api_key_header = APIKeyHeader(name=API_KEY_HEADER, auto_error=False)


class ApiKeyAuth:
    """Validates API keys using constant-time comparison.

    When `valid_keys` is empty and `required` is False, requests pass through
    without auth (development mode). When `required` is True (production),
    an empty key set is a configuration error.
    """

    def __init__(self, valid_keys: Iterable[str], required: bool) -> None:
        self._valid_keys = tuple(k for k in valid_keys if k)
        self._required = required

    def __call__(self, presented: str | None) -> str | None:
        if not self._valid_keys:
            if self._required:
                raise HTTPException(
                    status_code=503,
                    detail={"error": "auth_misconfigured", "reason": "no_api_keys_configured"},
                )
            return None

        if presented is None:
            raise HTTPException(
                status_code=401,
                detail={"error": "missing_api_key", "header": API_KEY_HEADER},
            )

        for valid in self._valid_keys:
            if hmac.compare_digest(presented, valid):
                return self.fingerprint(presented)

        raise HTTPException(status_code=401, detail={"error": "invalid_api_key"})

    @staticmethod
    def fingerprint(key: str) -> str:
        """Non-secret short identifier for logs and rate-limiting."""
        return hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]
