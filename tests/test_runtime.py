from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from dxpro_runtime.capture_agent import PmelCaptureAgent
from dxpro_runtime.catalog import DxProCatalog
from dxpro_runtime.config import RuntimeConfig
from dxpro_runtime.diagnostics import DiagnosticService
from dxpro_runtime.evidence import EvidenceLedger
from dxpro_runtime.models import EvaluationRequest
from dxpro_runtime.policy import PolicyEngine
from dxpro_runtime.pro_agents import CryptoParticipant, DmnEngine, PmelBpmnLintAgent, PmelToBeGenerator, PmelVisualInterpreter, RgcAgent
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


def _agent_consent() -> dict:
    return {"action": "ingest_to_llm", "consents": {"T1": True, "T3": True}}


def test_dxpro_compliance_posture_is_standalone(tmp_path: Path) -> None:
    service = _diagnostic_service(tmp_path)

    posture = service.compliance_posture()

    assert posture["agent_identity"]["name"] == "ARHIAX-DxPro-v1"
    assert posture["agent_identity"]["standard"] == "ARHIAX PMEL/ATK"
    assert "pmel_capture_agent" in {tool["name"] for tool in posture["tool_manifest"]}
    assert "rgc_hypothesis_builder" in {tool["name"] for tool in posture["tool_manifest"]}


def test_dxpro_diagnostic_evaluate_permits_and_certifies(tmp_path: Path) -> None:
    service = _diagnostic_service(tmp_path)

    response = service.evaluate(_diagnostic_payload())

    assert response["decision"]["status"] == "PERMIT"
    assert response["execution_plan"]["execution_status"] == "PASS"
    assert response["certificate"]["signature_algorithm"] == "HMAC-SHA256"
    assert response["certificate_evidence_id"] == "dxev-0000000007"
    assert response["pmel_step"]["outcome"] == "PERMIT"
    assert service.runtime.ledger.verify()["valid"] is True


def test_dxpro_certificate_verification_and_audit_pack(tmp_path: Path) -> None:
    service = _diagnostic_service(tmp_path)
    response = service.evaluate(_diagnostic_payload())

    verification = service.verify_certificate(response["certificate"])
    audit_pack = service.audit_pack(response["trace_id"])

    assert verification["valid"] is True
    assert verification["evidence_match"] is True
    assert verification["trusted"] is True
    assert audit_pack is not None
    assert audit_pack["entry_count"] == 7
    assert audit_pack["certificate_evidence_ids"] == ["dxev-0000000007"]


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


def test_dxpro_diagnostic_omitted_pmel_consent_denies(tmp_path: Path) -> None:
    service = _diagnostic_service(tmp_path)
    payload = _diagnostic_payload()
    payload.pop("pmel")

    response = service.evaluate(payload)

    assert response["decision"]["status"] == "DENY"
    assert response["pmel_step"]["outcome"] == "DENY"
    assert response["pmel_step"]["reason"] == "aggregate_deny"


def _runtime(tmp_path: Path) -> DxProRuntime:
    return DxProRuntime(
        policy_engine=PolicyEngine(tmp_path / "missing-bundle"),
        ledger=EvidenceLedger(tmp_path / "evidence.jsonl", "test-secret"),
    )


def test_to_be_generator_creates_blueprint(tmp_path: Path) -> None:
    agent = PmelToBeGenerator(_runtime(tmp_path))

    result = agent.execute(
        {
            "consent": _agent_consent(),
            "as_is_activities": [{"label": "recibir solicitud"}, {"label": "validar datos"}],
        }
    )

    assert result["outcome"] == "PERMIT"
    assert result["artifact"]["artifact_type"] == "pmel_to_be_blueprint"
    assert result["artifact"]["step_count"] == 2
    assert result["artifact_evidence_id"] == "dxev-0000000006"


def test_bpmn_lint_agent_reports_model_issues(tmp_path: Path) -> None:
    agent = PmelBpmnLintAgent(_runtime(tmp_path))

    result = agent.execute(
        {
            "consent": _agent_consent(),
            "bpmn_model": {"nodes": [{"id": "task-1", "type": "task"}], "edges": []},
        }
    )

    assert result["outcome"] == "PERMIT"
    assert result["artifact"]["artifact_type"] == "pmel_bpmn_lint_report"
    assert result["artifact"]["outcome"] == "DENY"
    assert result["artifact"]["issue_count"] >= 2


def test_visual_interpreter_maps_findings(tmp_path: Path) -> None:
    agent = PmelVisualInterpreter(_runtime(tmp_path))

    result = agent.execute(
        {
            "consent": _agent_consent(),
            "observations": [{"text": "Hay espera larga antes del handoff"}],
        }
    )

    assert result["artifact"]["artifact_type"] == "pmel_visual_interpretation"
    assert result["artifact"]["findings"][0]["mapped_signal"] == "queue_or_delay"


def test_dmn_engine_returns_matching_decision(tmp_path: Path) -> None:
    agent = DmnEngine(_runtime(tmp_path))

    result = agent.execute(
        {
            "consent": _agent_consent(),
            "facts": {"qa_score": 91, "risk": "low"},
            "decision_table": {
                "id": "publish_gate",
                "rules": [
                    {
                        "id": "approve-clean",
                        "when": {"qa_score": {"min": 85}, "risk": "low"},
                        "then": {"decision": "approve_draft"},
                    }
                ],
                "default": {"decision": "manual_review"},
            },
        }
    )

    assert result["artifact"]["artifact_type"] == "dmn_decision_result"
    assert result["artifact"]["matched_rule_id"] == "approve-clean"
    assert result["artifact"]["decision"]["decision"] == "approve_draft"


def test_crypto_participant_returns_plan_only(tmp_path: Path) -> None:
    agent = CryptoParticipant(_runtime(tmp_path))

    result = agent.execute(
        {
            "consent": _agent_consent(),
            "targets": [{"dataset": "raw-responses", "key_id": "kms-001"}],
        }
    )

    assert result["artifact"]["artifact_type"] == "crypto_decommissioning_plan"
    assert result["artifact"]["execution_mode"] == "plan_only"
    assert result["artifact"]["requires_operator_confirmation"] is True


def test_rgc_agent_returns_hypothesis_pack_when_governed(tmp_path: Path) -> None:
    agent = RgcAgent(_runtime(tmp_path))

    result = agent.execute(
        {
            "consent": _agent_consent(),
            "engagement_id": "eng-rgc-001",
            "domain": "service operations",
            "pain_points": ["manual handoff delays"],
        }
    )

    assert result["outcome"] == "PERMIT"
    assert result["artifact"]["artifact_type"] == "pmel_hypothesis_pack"
    assert result["artifact"]["llm_mode"] == "stub"
    assert result["artifact_evidence_id"] == "dxev-0000000006"


def test_pro_agent_blocks_artifact_when_consent_missing(tmp_path: Path) -> None:
    agent = PmelToBeGenerator(_runtime(tmp_path))

    result = agent.execute(
        {
            "consent": {"action": "ingest_to_llm", "consents": {"T1": True}},
            "as_is_activities": [{"label": "recibir solicitud"}],
        }
    )

    assert result["outcome"] == "DENY"
    assert result["artifact"] is None


def test_pro_agent_blocks_artifact_when_consent_omitted(tmp_path: Path) -> None:
    agent = PmelToBeGenerator(_runtime(tmp_path))

    result = agent.execute({"as_is_activities": [{"label": "recibir solicitud"}]})

    assert result["outcome"] == "DENY"
    assert result["artifact"] is None


def test_full_bundle_scope_covers_all_manifest_packages(tmp_path: Path) -> None:
    bundle_path = Path(__file__).resolve().parents[1] / "policy-bundle-pmel-v1.0.0"
    runtime = DxProRuntime(
        policy_engine=PolicyEngine(bundle_path, opa_path=""),
        ledger=EvidenceLedger(tmp_path / "evidence.jsonl", "test-secret"),
    )

    response = runtime.run_step({"subject": "pmel-full-bundle", "scope": "full_bundle", "input": {}})

    packages = {decision["package"] for decision in response.decisions}
    assert packages == set(runtime.policy_engine.package_names())
    assert len(response.decisions) == 22
    assert all(decision["reason"] != "native_evaluator_not_implemented_for_package" for decision in response.decisions)
    assert response.evidence_id == "dxev-0000000023"


def test_opa_cli_mode_evaluates_productive_bundle_without_legacy_tests() -> None:
    bundle_path = Path(__file__).resolve().parents[1] / "policy-bundle-pmel-v1.0.0"
    local_opa = bundle_path.parent / ".tools" / "opa.exe"
    opa_path = shutil.which("opa") or (str(local_opa) if local_opa.exists() else None)
    if not opa_path:
        pytest.skip("OPA binary not available")

    engine = PolicyEngine(bundle_path, opa_path=opa_path)
    decision = engine.evaluate(
        EvaluationRequest(
            package="arhia.pmel.base.aibom",
            input={},
        )
    )

    assert engine.mode == "opa-cli"
    assert decision.outcome == "PERMIT"
    assert decision.details["policy_mode"] == "opa-cli"
