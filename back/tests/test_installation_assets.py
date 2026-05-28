from __future__ import annotations

import json

from arhiax_dx.installation_assets import binding_status_report, ensure_install_manifest


def test_install_manifest_is_generated(settings):
    manifest = ensure_install_manifest(settings)

    assert settings.install_manifest_path.exists()
    assert "bindings" in manifest
    assert "ed25519_signing" in manifest["bindings"]


def test_optional_bindings_default_to_not_enabled(settings):
    ensure_install_manifest(settings)
    report = binding_status_report(settings)
    by_name = {item["requirement"]: item for item in report}

    assert by_name["docx_renderer"]["status"] == "optional_not_enabled"
    assert by_name["bpmn_renderer"]["status"] == "optional_not_enabled"

    disk_manifest = json.loads(settings.install_manifest_path.read_text(encoding="utf-8"))
    assert disk_manifest["bindings"]["observability_stack"]["enabled"] is True
