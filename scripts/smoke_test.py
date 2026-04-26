from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("DXPRO_RUNTIME_ROOT", str(ROOT))

from dxpro_runtime.catalog import DxProCatalog
from dxpro_runtime.config import load_config
from dxpro_runtime.diagnostics import DiagnosticService
from dxpro_runtime.evidence import EvidenceLedger
from dxpro_runtime.policy import PolicyEngine
from dxpro_runtime.runtime import DxProRuntime
from dxpro_runtime.capture_agent import PmelCaptureAgent


def main() -> int:
    temp_dir = tempfile.TemporaryDirectory()
    os.environ["DXPRO_LEDGER_PATH"] = str(Path(temp_dir.name) / "evidence.jsonl")
    config = load_config()
    runtime = DxProRuntime(
        policy_engine=PolicyEngine(config.policy_bundle_path, config.opa_url),
        ledger=EvidenceLedger(config.ledger_path, config.evidence_secret),
    )
    diagnostics = DiagnosticService(config, DxProCatalog(), runtime)

    response = runtime.evaluate(
        {
            "subject": "pmel-capture-agent",
            "package": "arhia.pmel.governance.consent_gates",
            "input": {
                "action": "ingest_to_llm",
                "consents": {"T1": True, "T3": True},
            },
        }
    )
    verify = runtime.ledger.verify()
    step_response = runtime.run_step(
        {
            "subject": "pmel-capture-agent",
            "step": "pre_ingest",
            "input": {
                "autonomy": {"component": "capture_agent", "requested_level": "A2"},
                "consent": {
                    "action": "ingest_to_llm",
                    "consents": {"T1": True, "T3": True},
                },
                "aibom": {
                    "bundle_version": "1.0.0",
                    "models": ["claude-sonnet-4-7"],
                    "prompts": ["pmel-capture-v1"],
                    "owner": "Sinergia Consulting Group",
                },
                "execution": {
                    "component": "capture_agent",
                    "current_cycle": 1,
                    "last_outcome": "in_progress",
                },
            },
        }
    )
    verify_after_step = runtime.ledger.verify()
    capture = PmelCaptureAgent(runtime).capture(
        {
            "subject": "pmel-capture-agent",
            "interview_text": (
                "El cliente recibe solicitudes por WhatsApp. "
                "El analista valida datos. "
                "Luego genera una cotizacion."
            ),
            "consent": {
                "action": "ingest_to_llm",
                "consents": {"T1": True, "T3": True},
            },
            "aibom": {
                "bundle_version": "1.0.0",
                "models": ["claude-sonnet-4-7"],
                "prompts": ["pmel-capture-v1"],
                "owner": "Sinergia Consulting Group",
            },
        }
    )
    trace_entries = runtime.ledger.find_by_trace(capture["trace_id"])
    diagnostic = diagnostics.evaluate(
        {
            "requested_autonomy_level": "A1",
            "mandate": {
                "organization_name": "Cliente Demo",
                "domain": "diagnostico organizacional",
                "subprocess": "evaluacion",
                "size_org": "120",
                "objective": "Diagnosticar cuellos de botella",
            },
            "client": {
                "client_id": "client-001",
                "legal_name": "Cliente Demo S.A.S.",
                "authorized_boundary_id": "boundary-diagnostico-org-pro",
            },
            "requested_tools": ["g01_receptor", "g10a_scoring", "pmel_capture_agent"],
            "requested_operations": ["modelInvoke", "toolCall", "dataAccess", "pmelCapture"],
            "requested_data_scopes": ["organizational_context", "audit_log", "pmel_artifacts"],
            "processing_profile": {"issue_certificate": True, "retention_days": 30},
            "simulation": {"current_weekday": 2, "current_hour": 10, "qa_score": 95, "irr_alpha": 0.8},
            "pmel": {"consents": {"T1": True, "T3": True}},
        }
    )

    print(json.dumps(response.to_dict(), indent=2, ensure_ascii=False))
    print(json.dumps({"ledger_verify": verify}, indent=2, ensure_ascii=False))
    print(json.dumps(step_response.to_dict(), indent=2, ensure_ascii=False))
    print(json.dumps({"ledger_verify_after_step": verify_after_step}, indent=2, ensure_ascii=False))
    print(json.dumps(capture, indent=2, ensure_ascii=False))
    print(json.dumps({"capture_trace_entries": len(trace_entries)}, indent=2, ensure_ascii=False))
    print(json.dumps(diagnostic, indent=2, ensure_ascii=False))

    if response.decision.outcome != "PERMIT":
        return 1
    if step_response.outcome != "PERMIT":
        return 1
    if not verify_after_step["valid"]:
        return 1
    if capture["outcome"] != "PERMIT" or capture["artifact"] is None:
        return 1
    if len(trace_entries) != 5:
        return 1
    if diagnostic["decision"]["status"] != "PERMIT" or diagnostic["certificate"] is None:
        return 1
    if not runtime.ledger.verify()["valid"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
