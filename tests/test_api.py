from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from dxpro_runtime.api import create_app
from dxpro_runtime.config import RuntimeConfig


def _client(tmp_path: Path) -> TestClient:
    config = RuntimeConfig(
        root_dir=tmp_path,
        ledger_path=tmp_path / "evidence.jsonl",
        evidence_secret="test-secret",
        policy_bundle_path=tmp_path / "missing-bundle",
    )
    return TestClient(create_app(config))


def _diagnostic_payload() -> dict:
    return {
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


def test_fastapi_health_and_posture(tmp_path: Path) -> None:
    client = _client(tmp_path)

    health = client.get("/healthz")
    posture = client.get("/v1/compliance/posture")

    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert posture.status_code == 200
    assert posture.json()["agent_identity"]["name"] == "ARHIAX-DxPro-v1"


def test_fastapi_diagnostic_evaluate(tmp_path: Path) -> None:
    client = _client(tmp_path)

    response = client.post("/v1/diagnostics/evaluate", json=_diagnostic_payload())

    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"]["status"] == "PERMIT"
    assert payload["certificate"]["signature_algorithm"] == "HMAC-SHA256"
    assert payload["certificate_evidence_id"] is not None
    assert payload["pmel_step"]["outcome"] == "PERMIT"


def test_fastapi_evidence_verify_after_diagnostic(tmp_path: Path) -> None:
    client = _client(tmp_path)

    client.post("/v1/diagnostics/evaluate", json=_diagnostic_payload())
    response = client.get("/v1/evidence/verify")

    assert response.status_code == 200
    assert response.json() == {"valid": True, "entries_checked": 7}


def test_fastapi_certificate_verify_and_audit_pack(tmp_path: Path) -> None:
    client = _client(tmp_path)
    diagnostic = client.post("/v1/diagnostics/evaluate", json=_diagnostic_payload()).json()

    verify = client.post("/v1/certificates/verify", json={"certificate": diagnostic["certificate"]})
    audit_pack = client.get(f"/v1/audit-pack/{diagnostic['trace_id']}")

    assert verify.status_code == 200
    assert verify.json()["trusted"] is True
    assert audit_pack.status_code == 200
    assert audit_pack.json()["entry_count"] == 7
    assert audit_pack.json()["certificate_verifications"][0]["trusted"] is True
