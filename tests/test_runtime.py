from __future__ import annotations

from pathlib import Path

from dxpro_runtime.capture_agent import PmelCaptureAgent
from dxpro_runtime.catalog import DxProCatalog
from dxpro_runtime.config import RuntimeConfig
from dxpro_runtime.diagnostics import DiagnosticService
from dxpro_runtime.evidence import EvidenceLedger
from dxpro_runtime.models import EvaluationRequest
from dxpro_runtime.policy import PolicyEngine
from dxpro_runtime.runtime import DxProRuntime


def test_consent_gate_permit_records_evidence(tmp_path: Path) -> None:
    runtime = DxProRuntime(
        policy_engine=PolicyEngine(tmp_path / "missing-bundle"),
        ledger=EvidenceLedger(tmp_path / "evidence.jsonl", "test-secret"),
    )

    response = runtime.evaluate(
        {
            "subject": "pmel-capture-agent",
            "package": "arhia.pmel.governance.consent_gates",
            "input": {"action": "start_observation", "consents": {"T1": True}},
        }
    )

    assert response.decision.outcome == "PERMIT"
    assert response.evidence_id == "dxev-0000000001"
    assert runtime.ledger.verify()["valid"] is True


def test_autonomy_denies_a3() -> None:
    engine = PolicyEngine(Path("missing"))
    decision = engine.evaluate(
        EvaluationRequest(
            package="arhia.pmel.base.autonomy",
            input={"component": "capture_agent", "requested_level": "A3"},
        )
    )

    assert decision.outcome == "DENY"


def test_run_step_permit_records_individual_and_aggregate_evidence(tmp_path: Path) -> None:
    runtime = DxProRuntime(
        policy_engine=PolicyEngine(tmp_path / "missing-bundle"),
        ledger=EvidenceLedger(tmp_path / "evidence.jsonl", "test-secret"),
    )

    response = runtime.run_step(
        {
            "subject": "pmel-capture-agent",
            "step": "pre_ingest",
            "input": {
                "autonomy": {"component": "capture_agent", "requested_level": "A2"},
                "consent": {"action": "ingest_to_llm", "consents": {"T1": True, "T3": True}},
                "aibom": {
                    "bundle_version": "1.0.0",
                    "models": ["claude-sonnet-4-7"],
                    "prompts": ["pmel-capture-v1"],
                    "owner": "Sinergia",
                },
                "execution": {
                    "component": "capture_agent",
                    "current_cycle": 1,
                    "last_outcome": "in_progress",
                },
            },
        }
    )

    assert response.outcome == "PERMIT"
    assert response.allowed is True
    assert len(response.decisions) == 4
    assert response.evidence_id == "dxev-0000000005"
    assert runtime.ledger.verify() == {"valid": True, "entries_checked": 5}


def test_run_step_denies_missing_consent(tmp_path: Path) -> None:
    runtime = DxProRuntime(
        policy_engine=PolicyEngine(tmp_path / "missing-bundle"),
        ledger=EvidenceLedger(tmp_path / "evidence.jsonl", "test-secret"),
    )

    response = runtime.run_step(
        {
            "subject": "pmel-capture-agent",
            "step": "pre_ingest",
            "input": {
                "autonomy": {"component": "capture_agent", "requested_level": "A2"},
                "consent": {"action": "ingest_to_llm", "consents": {"T1": True}},
                "aibom": {
                    "bundle_version": "1.0.0",
                    "models": ["claude-sonnet-4-7"],
                    "prompts": ["pmel-capture-v1"],
                    "owner": "Sinergia",
                },
                "execution": {
                    "component": "capture_agent",
                    "current_cycle": 1,
                    "last_outcome": "in_progress",
                },
            },
        }
    )

    assert response.outcome == "DENY"
    assert response.allowed is False
    assert response.reason == "aggregate_deny"
    assert any(decision["reason"] == "missing_required_consent" for decision in response.decisions)


def test_find_by_trace_returns_ordered_entries(tmp_path: Path) -> None:
    runtime = DxProRuntime(
        policy_engine=PolicyEngine(tmp_path / "missing-bundle"),
        ledger=EvidenceLedger(tmp_path / "evidence.jsonl", "test-secret"),
    )
    response = runtime.run_step(
        {
            "trace_id": "trace-test-001",
            "subject": "pmel-capture-agent",
            "input": {
                "autonomy": {"component": "capture_agent", "requested_level": "A2"},
                "consent": {"action": "ingest_to_llm", "consents": {"T1": True, "T3": True}},
                "aibom": {
                    "bundle_version": "1.0.0",
                    "models": ["claude-sonnet-4-7"],
                    "prompts": ["pmel-capture-v1"],
                    "owner": "Sinergia",
                },
                "execution": {
                    "component": "capture_agent",
                    "current_cycle": 1,
                    "last_outcome": "in_progress",
                },
            },
        }
    )

    entries = runtime.ledger.find_by_trace(response.trace_id)

    assert len(entries) == 5
    assert entries[0]["event_type"] == "policy_decision"
    assert entries[-1]["event_type"] == "pmel_step_aggregate"


def test_capture_agent_returns_artifact_when_governance_permits(tmp_path: Path) -> None:
    runtime = DxProRuntime(
        policy_engine=PolicyEngine(tmp_path / "missing-bundle"),
        ledger=EvidenceLedger(tmp_path / "evidence.jsonl", "test-secret"),
    )
    agent = PmelCaptureAgent(runtime)

    result = agent.capture(
        {
            "interview_text": "Recibir solicitud. Validar datos. Enviar cotizacion.",
            "consent": {"action": "ingest_to_llm", "consents": {"T1": True, "T3": True}},
            "aibom": {
                "bundle_version": "1.0.0",
                "models": ["claude-sonnet-4-7"],
                "prompts": ["pmel-capture-v1"],
                "owner": "Sinergia",
            },
        }
    )

    assert result["outcome"] == "PERMIT"
    assert result["artifact"]["artifact_type"] == "pmel_capture_draft"
    assert result["artifact"]["activity_count"] == 3


def test_capture_agent_blocks_artifact_when_governance_denies(tmp_path: Path) -> None:
    runtime = DxProRuntime(
        policy_engine=PolicyEngine(tmp_path / "missing-bundle"),
        ledger=EvidenceLedger(tmp_path / "evidence.jsonl", "test-secret"),
    )
    agent = PmelCaptureAgent(runtime)

    result = agent.capture(
        {
            "interview_text": "Recibir solicitud. Validar datos.",
            "consent": {"action": "ingest_to_llm", "consents": {"T1": True}},
            "aibom": {
                "bundle_version": "1.0.0",
                "models": ["claude-sonnet-4-7"],
                "prompts": ["pmel-capture-v1"],
                "owner": "Sinergia",
            },
        }
    )

    assert result["outcome"] == "DENY"
    assert result["artifact"] is None


def _diagnostic_service(tmp_path: Path) -> DiagnosticService:
    config = RuntimeConfig(
        root_dir=tmp_path,
        ledger_path=tmp_path / "evidence.jsonl",
        evidence_secret="test-secret",
        policy_bundle_path=tmp_path / "missing-bundle",
    )
    runtime = DxProRuntime(
        policy_engine=PolicyEngine(config.policy_bundle_path),
        ledger=EvidenceLedger(config.ledger_path, config.evidence_secret),
    )
    return DiagnosticService(config, DxProCatalog(), runtime)


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
        "pmel": {
            "consents": {"T1": True, "T3": True},
            "aibom": {
                "bundle_version": "2026.04-dxpro",
                "models": ["client_bound_model"],
                "prompts": ["dxpro-diagnostic-v1"],
                "owner": "Sinergia",
            },
        },
    }


def test_dxpro_compliance_posture_is_standalone(tmp_path: Path) -> None:
    service = _diagnostic_service(tmp_path)

    posture = service.compliance_posture()

    assert posture["agent_identity"]["name"] == "ARHIAX-DxPro-v1"
    assert posture["agent_identity"]["standard"] == "ARHIAX PMEL/ATK"
    assert "pmel_capture_agent" in {tool["name"] for tool in posture["tool_manifest"]}


def test_dxpro_diagnostic_evaluate_permits_and_certifies(tmp_path: Path) -> None:
    service = _diagnostic_service(tmp_path)

    response = service.evaluate(_diagnostic_payload())

    assert response["decision"]["status"] == "PERMIT"
    assert response["execution_plan"]["execution_status"] == "PASS"
    assert response["certificate"]["signature_algorithm"] == "HMAC-SHA256"
    assert response["pmel_step"]["outcome"] == "PERMIT"
    assert service.runtime.ledger.verify()["valid"] is True


def test_dxpro_diagnostic_publication_escalates(tmp_path: Path) -> None:
    service = _diagnostic_service(tmp_path)
    payload = _diagnostic_payload()
    payload["processing_profile"]["publish_report"] = True

    response = service.evaluate(payload)

    assert response["decision"]["status"] == "ESCALATE"
    assert response["human_review_required"] is True
    assert any("Publishing the report requires" in reason for reason in response["decision"]["reasons"])


def test_dxpro_diagnostic_missing_pmel_consent_denies(tmp_path: Path) -> None:
    service = _diagnostic_service(tmp_path)
    payload = _diagnostic_payload()
    payload["pmel"]["consents"] = {"T1": True}

    response = service.evaluate(payload)

    assert response["decision"]["status"] == "DENY"
    assert response["pmel_step"]["outcome"] == "DENY"
