"""Runtime configuration for ARHIAX Dx."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from arhiax_dx.specs import default_specs_path


def _split_csv(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass(slots=True)
class Settings:
    project_name: str = os.getenv("ARHIAX_DX_PROJECT_NAME", "ARHIAX Dx Agent")
    agent_version: str = os.getenv("ARHIAX_DX_AGENT_VERSION", "5.1.0")
    environment: str = os.getenv("ARHIAX_DX_ENV", "development")
    mode: str = os.getenv("ARHIAX_DX_MODE", "mock")
    host: str = os.getenv("ARHIAX_DX_HOST", "0.0.0.0")
    port: int = int(os.getenv("ARHIAX_DX_PORT", "8088"))
    ledger_path: Path = Path(os.getenv("ARHIAX_DX_LEDGER_PATH", "var/evidence-ledger.jsonl"))
    install_manifest_path: Path = Path(
        os.getenv("ARHIAX_DX_INSTALL_MANIFEST_PATH", "var/install/client-install-manifest.json")
    )
    public_key_id: str = os.getenv("ARHIAX_DX_PUBLIC_KEY_ID", "dx-local-ed25519")
    private_key_b64: str = os.getenv("ARHIAX_DX_ED25519_PRIVATE_KEY", "")
    governance_spec_version: str = os.getenv("ARHIAX_DX_GOVERNANCE_SPEC_VERSION", "2026.04")
    policy_bundle_version: str = os.getenv("ARHIAX_DX_POLICY_BUNDLE_VERSION", "2026.04")
    tool_catalog_version: str = os.getenv("ARHIAX_DX_TOOL_CATALOG_VERSION", "2026.04")
    specs_path: Path = Path(os.getenv("ARHIAX_DX_SPECS_PATH", str(default_specs_path())))
    operating_timezone: str = os.getenv("ARHIAX_DX_OPERATING_TIMEZONE", "America/Bogota")
    operating_window_start: int = int(os.getenv("ARHIAX_DX_OPERATING_WINDOW_START", "7"))
    operating_window_end: int = int(os.getenv("ARHIAX_DX_OPERATING_WINDOW_END", "22"))
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    hic_webhook_url: str = os.getenv("HIC_WEBHOOK_URL", "")
    whatsapp_business_webhook: str = os.getenv("WHATSAPP_BUSINESS_WEBHOOK", "")
    policy_bundles: list[str] = field(
        default_factory=lambda: _split_csv(
            os.getenv("ARHIAX_DX_POLICY_BUNDLES", "DX-B01,DX-B02,DX-B03,DX-B04,DX-B05")
        )
    )

    def ensure_runtime_dirs(self) -> None:
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self.install_manifest_path.parent.mkdir(parents=True, exist_ok=True)

    def governance_metadata(self) -> dict[str, str]:
        return {
            "agent_version": self.agent_version,
            "governance_spec_version": self.governance_spec_version,
            "policy_bundle_version": self.policy_bundle_version,
            "tool_catalog_version": self.tool_catalog_version,
        }
