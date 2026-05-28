"""Installation readiness reporting for client-hosted ARHIAX Dx deployments."""

from __future__ import annotations

import json
from typing import Any

from arhiax_dx.config import Settings
from arhiax_dx.installation_assets import binding_status_report, build_install_blueprint
from arhiax_dx.services.provenance import ProvenanceSigner
from arhiax_dx.services.tool_registry import ToolRegistry


def build_installation_report(
    settings: Settings | None = None,
    registry: ToolRegistry | None = None,
    signer: ProvenanceSigner | None = None,
) -> dict[str, Any]:
    settings = settings or Settings()
    registry = registry or ToolRegistry(settings)
    signer = signer or ProvenanceSigner(settings)

    metadata = settings.governance_metadata()
    install_blueprint = build_install_blueprint(settings)
    install_bindings = binding_status_report(settings)

    packaged_controls = [
        {
            "control": "governance_spec_packaged",
            "status": "ready",
            "details": f"Governance spec version {metadata['governance_spec_version']} is embedded in runtime metadata.",
        },
        {
            "control": "tool_catalog_packaged",
            "status": "ready",
            "details": f"Tool catalog version {metadata['tool_catalog_version']} is packaged with the runtime.",
        },
        {
            "control": "policy_bundle_versioning",
            "status": "ready",
            "details": f"Policy bundle version {metadata['policy_bundle_version']} is emitted in evidence and certificates.",
        },
        {
            "control": "model_strategy_packaged",
            "status": "ready",
            "details": "Model routing and fallback strategy are packaged in specs/model_strategy.json.",
        },
        {
            "control": "install_time_blueprint_packaged",
            "status": "ready",
            "details": f"Install-time bindings are packaged in {settings.install_manifest_path}.",
        },
    ]

    post_install_requirements = [
        {
            "requirement": "signing_key_injected",
            "status": "configured" if bool(settings.private_key_b64) else "pending_after_install",
            "details": "Inject an Ed25519 signing key from client KMS/HSM or sealed-secret workflow.",
        },
        {
            "requirement": "gemini_primary_injected",
            "status": "configured" if bool(settings.gemini_api_key) else "pending_after_install",
            "details": "Provide GEMINI_API_KEY for primary model routing.",
        },
        {
            "requirement": "anthropic_fallback_injected",
            "status": "configured" if bool(settings.anthropic_api_key) else "pending_after_install",
            "details": "Provide ANTHROPIC_API_KEY for fallback routing.",
        },
        {
            "requirement": "hic_webhook_configured",
            "status": "configured" if bool(settings.hic_webhook_url) else "pending_after_install",
            "details": "Provide HIC_WEBHOOK_URL for governed escalations.",
        },
    ]
    post_install_requirements.extend(install_bindings)

    return {
        "agent": settings.project_name,
        "agent_version": settings.agent_version,
        "mode": settings.mode,
        "public_key_preview": signer.key_material_preview(),
        "governance_metadata": metadata,
        "packaged_controls": packaged_controls,
        "post_install_requirements": post_install_requirements,
        "install_blueprint": install_blueprint,
        "tool_manifest": registry.tool_manifest(),
        "install_ready": all(
            item["status"] in {"configured", "optional_not_enabled"} for item in post_install_requirements
        ),
    }


def main() -> None:
    report = build_installation_report()
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
