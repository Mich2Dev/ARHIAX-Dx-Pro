"""Runtime configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from .secrets import resolve_secret

_DEV_SECRET = "dxpro-dev-secret-change-me"
_MIN_SECRET_LEN = 32
_DEFAULT_RATE_LIMIT_PER_MINUTE = 60


@dataclass(frozen=True)
class RuntimeConfig:
    root_dir: Path
    ledger_path: Path
    evidence_secret: str
    policy_bundle_path: Path
    case_store_root: Path
    export_root: Path
    env: str = "development"
    anthropic_api_key: str | None = None
    opa_url: str | None = None
    api_keys: tuple[str, ...] = field(default_factory=tuple)
    rate_limit_per_minute: int = _DEFAULT_RATE_LIMIT_PER_MINUTE
    rate_limit_burst: int | None = None

    @property
    def is_production(self) -> bool:
        return self.env == "production"


def load_config() -> RuntimeConfig:
    env = os.getenv("DXPRO_ENV", "development")

    secret = resolve_secret("DXPRO_EVIDENCE_SECRET", "evidence_secret") or _DEV_SECRET
    anthropic_api_key = resolve_secret("ANTHROPIC_API_KEY", "anthropic_api_key")
    api_keys_raw = resolve_secret("DXPRO_API_KEYS", "api_keys")

    api_keys = tuple(
        k.strip() for k in (api_keys_raw or "").split(",") if k.strip()
    )

    rate_limit_per_minute = int(
        os.getenv("DXPRO_RATE_LIMIT_PER_MINUTE", str(_DEFAULT_RATE_LIMIT_PER_MINUTE))
    )
    rate_limit_burst_env = os.getenv("DXPRO_RATE_LIMIT_BURST")
    rate_limit_burst = int(rate_limit_burst_env) if rate_limit_burst_env else None

    if env == "production":
        if secret == _DEV_SECRET:
            raise RuntimeError(
                "DXPRO_EVIDENCE_SECRET must be set to a strong secret in production. "
                "The default dev secret is not allowed."
            )
        if len(secret) < _MIN_SECRET_LEN:
            raise RuntimeError(
                f"DXPRO_EVIDENCE_SECRET must be at least {_MIN_SECRET_LEN} characters in production."
            )
        if not api_keys:
            raise RuntimeError(
                "DXPRO_API_KEYS must be configured in production (comma-separated list "
                "of API keys, or stored in Vault under 'api_keys')."
            )
        for k in api_keys:
            if len(k) < _MIN_SECRET_LEN:
                raise RuntimeError(
                    f"All entries in DXPRO_API_KEYS must be at least {_MIN_SECRET_LEN} characters."
                )
        if not anthropic_api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY must be configured in production."
            )
        if rate_limit_per_minute <= 0:
            raise RuntimeError("DXPRO_RATE_LIMIT_PER_MINUTE must be positive in production.")

    root = Path(os.getenv("DXPRO_RUNTIME_ROOT", Path.cwd())).resolve()
    ledger_path = Path(os.getenv("DXPRO_LEDGER_PATH", root / "data" / "evidence.jsonl"))
    bundle_path = Path(
        os.getenv("DXPRO_POLICY_BUNDLE_PATH", root / "policy-bundle-pmel-v1.0.0")
    )

    return RuntimeConfig(
        root_dir=root,
        ledger_path=ledger_path,
        evidence_secret=secret,
        policy_bundle_path=bundle_path,
        case_store_root=Path(os.getenv("DXPRO_CASE_STORE_ROOT", root / "data" / "cases")),
        export_root=Path(os.getenv("DXPRO_EXPORT_ROOT", root / "data" / "exports")),
        env=env,
        anthropic_api_key=anthropic_api_key,
        opa_url=os.getenv("DXPRO_OPA_URL") or None,
        api_keys=api_keys,
        rate_limit_per_minute=rate_limit_per_minute,
        rate_limit_burst=rate_limit_burst,
    )
