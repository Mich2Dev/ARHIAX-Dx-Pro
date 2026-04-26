"""Runtime configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RuntimeConfig:
    root_dir: Path
    ledger_path: Path
    evidence_secret: str
    policy_bundle_path: Path
    opa_url: str | None = None


def load_config() -> RuntimeConfig:
    root = Path(os.getenv("DXPRO_RUNTIME_ROOT", Path.cwd())).resolve()
    ledger_path = Path(os.getenv("DXPRO_LEDGER_PATH", root / "data" / "evidence.jsonl"))
    bundle_path = Path(
        os.getenv("DXPRO_POLICY_BUNDLE_PATH", root / "policy-bundle-pmel-v1.0.0")
    )
    return RuntimeConfig(
        root_dir=root,
        ledger_path=ledger_path,
        evidence_secret=os.getenv("DXPRO_EVIDENCE_SECRET", "dxpro-dev-secret-change-me"),
        policy_bundle_path=bundle_path,
        opa_url=os.getenv("DXPRO_OPA_URL") or None,
    )

