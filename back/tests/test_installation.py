from __future__ import annotations

import json

from arhiax_dx.installation import build_installation_report
from arhiax_dx.installation_assets import ensure_install_manifest


def test_installation_report_starts_not_ready(settings):
    report = build_installation_report(settings=settings)

    assert report["install_ready"] is False
    assert any(item["status"] == "pending_after_install" for item in report["post_install_requirements"])


def test_installation_report_becomes_ready_when_required_bindings_are_configured(settings):
    manifest = ensure_install_manifest(settings)
    for name, binding in manifest["bindings"].items():
        if binding["required"]:
            binding["configured"] = True
    settings.install_manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    report = build_installation_report(settings=settings)

    assert report["install_ready"] is True
