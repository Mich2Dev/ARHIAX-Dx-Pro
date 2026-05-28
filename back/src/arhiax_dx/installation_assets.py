"""Install-time blueprints for client-hosted ARHIAX Dx deployments."""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from arhiax_dx.config import Settings


def build_install_blueprint(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings()
    return {
        "agent": settings.project_name,
        "agent_version": settings.agent_version,
        "governance_metadata": settings.governance_metadata(),
        "install_manifest_path": str(settings.install_manifest_path),
        "bindings": [
            {
                "binding": "ed25519_signing",
                "owner": "client_security",
                "required": True,
                "config_fields": ["public_key_id", "key_injection_mode", "kms_reference"],
                "notes": "Required for signing governed execution certificates.",
            },
            {
                "binding": "gemini_primary",
                "owner": "client_platform",
                "required": True,
                "config_fields": ["api_key_reference", "routing_scope"],
                "notes": "Primary model binding for Gemini stages.",
            },
            {
                "binding": "anthropic_fallback",
                "owner": "client_platform",
                "required": True,
                "config_fields": ["api_key_reference", "routing_scope"],
                "notes": "Fallback model binding used when Gemini returns 429 or 503.",
            },
            {
                "binding": "hic_webhook",
                "owner": "client_operations",
                "required": True,
                "config_fields": ["webhook_url", "channel_name"],
                "notes": "Primary human escalation channel for MEDIUM and HIGH incidents.",
            },
            {
                "binding": "whatsapp_critical",
                "owner": "client_operations",
                "required": False,
                "config_fields": ["enabled", "target_number", "api_reference"],
                "notes": "Optional CRITICAL escalation channel for immediate human response.",
            },
            {
                "binding": "docx_renderer",
                "owner": "client_platform",
                "required": False,
                "config_fields": ["enabled", "renderer_mode", "output_path"],
                "notes": "Optional Word rendering pipeline for final executive documents.",
            },
            {
                "binding": "bpmn_renderer",
                "owner": "client_platform",
                "required": False,
                "config_fields": ["enabled", "renderer_mode", "output_path"],
                "notes": "Optional BPMN rendering pipeline for process diagrams.",
            },
            {
                "binding": "observability_stack",
                "owner": "client_platform",
                "required": True,
                "config_fields": ["logging_target", "metrics_target", "alerting_target"],
                "notes": "Routes runtime logs, metrics, and alerts into the client stack.",
            },
        ],
    }


def install_manifest_template(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings()
    blueprint = build_install_blueprint(settings)
    manifest = {
        "agent": blueprint["agent"],
        "agent_version": blueprint["agent_version"],
        "governance_metadata": blueprint["governance_metadata"],
        "bindings": {},
    }
    for item in blueprint["bindings"]:
        manifest["bindings"][item["binding"]] = {
            "enabled": False if not item["required"] else True,
            "configured": False,
            "owner": item["owner"],
            "required": item["required"],
            "config": {field: "" for field in item["config_fields"]},
            "notes": item["notes"],
        }
    return manifest


def ensure_install_manifest(settings: Settings | None = None, overwrite: bool = False) -> dict[str, Any]:
    settings = settings or Settings()
    settings.ensure_runtime_dirs()
    manifest = install_manifest_template(settings)
    path = settings.install_manifest_path
    if overwrite or not path.exists():
        path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return manifest
    return load_install_manifest(settings)


def load_install_manifest(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings()
    path = settings.install_manifest_path
    if not path.exists():
        return deepcopy(install_manifest_template(settings))
    return json.loads(path.read_text(encoding="utf-8"))


def binding_status_report(settings: Settings | None = None) -> list[dict[str, Any]]:
    settings = settings or Settings()
    blueprint = build_install_blueprint(settings)
    manifest = load_install_manifest(settings)
    bindings = manifest.get("bindings", {})
    report: list[dict[str, Any]] = []
    for item in blueprint["bindings"]:
        name = item["binding"]
        manifest_binding = bindings.get(name, {})
        enabled = bool(manifest_binding.get("enabled", item["required"]))
        configured = bool(manifest_binding.get("configured", False))
        if not enabled and not item["required"]:
            status = "optional_not_enabled"
        elif configured:
            status = "configured"
        else:
            status = "pending_after_install"
        report.append(
            {
                "requirement": name,
                "status": status,
                "required": item["required"],
                "owner": item["owner"],
                "details": item["notes"],
            }
        )
    return report


def main() -> None:
    settings = Settings()
    manifest = ensure_install_manifest(settings)
    print(
        json.dumps(
            {
                "install_manifest_path": str(settings.install_manifest_path),
                "bindings": list(manifest["bindings"].keys()),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
