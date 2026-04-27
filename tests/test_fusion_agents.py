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


def _consent() -> dict:
    return {"action": "ingest_to_llm", "consents": {"T1": True, "T3": True}}


def _responses() -> list[dict]:
    return [
        {"role": "executive", "dimension": "strategy", "item_id": "strategy-1", "score": 4},
        {"role": "operations", "dimension": "strategy", "item_id": "strategy-1", "score": 2},
        {"role": "technology", "dimension": "strategy", "item_id": "strategy-1", "score": 3},
        {"role": "executive", "dimension": "process", "item_id": "process-1", "score": 3},
        {"role": "operations", "dimension": "process", "item_id": "process-1", "score": 2},
        {"role": "technology", "dimension": "process", "item_id": "process-1", "score": 4},
        {"role": "executive", "dimension": "technology", "item_id": "technology-1", "score": 3},
        {"role": "operations", "dimension": "technology", "item_id": "technology-1", "score": 2},
        {"role": "technology", "dimension": "technology", "item_id": "technology-1", "score": 4},
    ]


def _bpmn_model() -> dict:
    return {
        "nodes": [
            {"id": "start", "type": "start_event", "name": "Inicio"},
            {"id": "t1", "type": "task", "name": "Validar pedido"},
            {"id": "end", "type": "end_event", "name": "Fin"},
        ],
        "edges": [
            {"source": "start", "target": "t1"},
            {"source": "t1", "target": "end"},
        ],
        "prose": {"flow": "Se inicia el proceso, se valida el pedido y se finaliza."},
    }


def test_fusion_agent_endpoints_are_governed_and_return_artifacts(tmp_path: Path) -> None:
    client = _client(tmp_path)

    question_bank = client.post(
        "/v1/agents/questions/adaptive-bank",
        json={
            "consent": _consent(),
            "engagement_id": "eng-fusion-001",
            "roles": ["executive", "operations"],
            "dimensions": ["strategy", "process"],
            "pain_points": ["manual customs clearance handoffs"],
        },
    )
    scoring = client.post(
        "/v1/agents/scoring/multi-role",
        json={"consent": _consent(), "responses": _responses()},
    )
    psychometrics = client.post(
        "/v1/agents/psychometrics/evaluate",
        json={
            "consent": _consent(),
            "response_matrix": [[4, 3, 3], [2, 2, 2], [3, 4, 4]],
        },
    )
    irr = client.post(
        "/v1/agents/reliability/irr",
        json={"consent": _consent(), "ratings": _responses()},
    )

    assert question_bank.status_code == 200
    assert question_bank.json()["outcome"] == "PERMIT"
    assert question_bank.json()["artifact"]["artifact_type"] == "question_bank_pack"
    assert question_bank.json()["artifact"]["question_count"] == 4
    assert scoring.status_code == 200
    assert scoring.json()["artifact"]["artifact_type"] == "multi_role_scoring_pack"
    assert scoring.json()["artifact"]["maturity_level"] == "emerging"
    assert scoring.json()["artifact_evidence_id"] is not None
    assert psychometrics.status_code == 200
    assert psychometrics.json()["artifact"]["artifact_type"] == "psychometric_quality_pack"
    assert psychometrics.json()["artifact"]["item_count"] == 3
    assert irr.status_code == 200
    assert irr.json()["artifact"]["artifact_type"] == "irr_reliability_pack"
    assert irr.json()["artifact"]["recommended_action"] in {"proceed", "recapture_or_hil_review"}


def test_bayesian_qa_and_intelligence_pack_integration(tmp_path: Path) -> None:
    client = _client(tmp_path)
    scoring_pack = client.post(
        "/v1/agents/scoring/multi-role",
        json={"consent": _consent(), "responses": _responses()},
    ).json()["artifact"]

    bayesian = client.post(
        "/v1/agents/synthesis/bayesian",
        json={
            "consent": _consent(),
            "hypotheses": [
                {"id": "DH1", "statement": "Strategy alignment is limiting innovation.", "prior": 0.55},
                {"id": "DH2", "statement": "Technology handoffs are limiting traceability.", "prior": 0.45},
            ],
            "evidence_signals": [
                {"id": "sig-1", "hypothesis_ids": ["DH1"], "likelihood_ratio": 2.0},
                {"id": "sig-2", "hypothesis_ids": ["DH2"], "likelihood_ratio": 1.2},
            ],
        },
    )
    qa = client.post(
        "/v1/agents/qa/executive",
        json={
            "consent": _consent(),
            "scoring_pack": scoring_pack,
            "psychometric_pack": {"cronbach_alpha": 0.81},
            "irr_pack": {"agreement_index": 0.8},
            "bayesian_pack": bayesian.json()["artifact"],
            "hypothesis_pack": {"hypotheses": [{"id": "H1"}]},
            "contrast_pack": {"contrast_matrix": []},
            "to_be_pack": {"change_ledger": []},
        },
    )
    intelligence = client.post(
        "/v1/agents/diagnostic/intelligence-pack",
        json={
            "consent": _consent(),
            "scoring_pack": scoring_pack,
            "bayesian_pack": bayesian.json()["artifact"],
            "contrast_pack": {"contrast_matrix": [{"hypothesis_id": "H1"}]},
            "qa_pack": qa.json()["artifact"],
        },
    )

    assert bayesian.status_code == 200
    assert bayesian.json()["artifact"]["artifact_type"] == "bayesian_synthesis_pack"
    assert bayesian.json()["artifact"]["top_hypothesis_id"] == "DH1"
    assert qa.status_code == 200
    assert qa.json()["artifact"]["artifact_type"] == "executive_qa_pack"
    assert qa.json()["artifact"]["readiness"] == "approved"
    assert intelligence.status_code == 200
    assert intelligence.json()["artifact"]["artifact_type"] == "diagnostic_intelligence_pack"
    assert intelligence.json()["artifact"]["recommended_next_step"] == "generate_to_be_blueprint"
    assert intelligence.json()["artifact"]["diagnostic_intelligence_version"] == "1.1"
    assert intelligence.json()["artifact"]["executive_summary"]["decision_posture"] == "ready_for_tobe"
    assert intelligence.json()["artifact"]["priority_themes"]
    assert intelligence.json()["artifact"]["initiative_portfolio"]


def test_fusion_agent_denies_without_consent(tmp_path: Path) -> None:
    client = _client(tmp_path)

    response = client.post(
        "/v1/agents/scoring/multi-role",
        json={"responses": _responses()},
    )

    assert response.status_code == 200
    assert response.json()["outcome"] == "DENY"
    assert response.json()["artifact"] is None


def test_diagnostic_fusion_cycle_orchestrates_child_agents(tmp_path: Path) -> None:
    client = _client(tmp_path)

    response = client.post(
        "/v1/agents/diagnostic/run-fusion-cycle",
        json={
            "consent": _consent(),
            "engagement_id": "eng-cycle-001",
            "domain": "customs agency innovation",
            "roles": ["executive", "operations", "technology"],
            "dimensions": ["strategy", "process", "technology"],
            "responses": _responses(),
            "response_matrix": [[4, 3, 3], [2, 2, 2], [3, 4, 4]],
            "diagnostic_hypotheses": [
                {"id": "DH1", "statement": "Technology traceability is a bottleneck.", "prior": 0.55}
            ],
            "evidence_signals": [
                {"id": "sig-1", "hypothesis_ids": ["DH1"], "likelihood_ratio": 1.6}
            ],
            "hypothesis_pack": {
                "hypothesis_pack_version": "1.0",
                "engagement_id": "eng-cycle-001",
                "domain": "customs agency innovation",
                "hypotheses": [{"id": "H1", "statement": "Reduce manual handoffs."}],
            },
            "grey_sources": [
                {
                    "id": "grey-cycle-001",
                    "title": "Customs operations benchmark",
                    "content": "Manual handoffs increase customs clearance cycle time.",
                }
            ],
            "bpmn_model": _bpmn_model(),
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["outcome"] == "PERMIT"
    artifact = body["artifact"]
    assert artifact["artifact_type"] == "diagnostic_fusion_cycle_pack"
    assert artifact["stage_count"] == 11
    assert artifact["artifacts"]["question_bank"]["artifact_type"] == "question_bank_pack"
    assert artifact["artifacts"]["scoring_pack"]["artifact_type"] == "multi_role_scoring_pack"
    assert artifact["artifacts"]["bayesian_pack"]["top_hypothesis_id"] == "DH1"
    assert artifact["artifacts"]["diagnostic_intelligence_pack"]["artifact_type"] == "diagnostic_intelligence_pack"
    assert artifact["executive_summary"]["diagnostic_thesis"] == "Technology traceability is a bottleneck."
    assert artifact["recommended_next_step"] == "generate_to_be_blueprint"
    assert artifact["risk_signal_count"] >= 1


def test_diagnostic_intelligence_flags_quality_risks(tmp_path: Path) -> None:
    client = _client(tmp_path)

    response = client.post(
        "/v1/agents/diagnostic/intelligence-pack",
        json={
            "consent": _consent(),
            "scoring_pack": {
                "overall_score": 2.1,
                "maturity_level": "initial",
                "largest_role_gaps": [
                    {
                        "dimension": "technology",
                        "gap": 2.0,
                        "highest_role": "technology",
                        "lowest_role": "operations",
                    }
                ],
            },
            "psychometric_pack": {"cronbach_alpha": 0.62, "quality_status": "review"},
            "irr_pack": {"agreement_index": 0.63, "reliability_status": "review"},
            "bayesian_pack": {
                "top_hypothesis_id": "DH1",
                "prioritized_hypotheses": [
                    {
                        "id": "DH1",
                        "statement": "Technology traceability is limiting operational control.",
                        "posterior": 0.78,
                    }
                ],
            },
            "contrast_pack": {
                "contrast_matrix": [
                    {
                        "hypothesis_id": "H1",
                        "support_level": "moderate",
                        "requires_hil": True,
                        "hil_reason": "Regulatory boundary needs validation.",
                    }
                ],
                "recommended_hil_questions": [
                    {"question": "Which regulatory controls are mandatory?", "priority": "high"}
                ],
            },
            "hypothesis_pack": {"hypotheses": [{"id": "H1", "statement": "Improve traceability."}]},
            "qa_pack": {"readiness": "requires_review", "missing_artifacts": ["to_be_pack"]},
        },
    )

    assert response.status_code == 200
    artifact = response.json()["artifact"]
    assert artifact["executive_summary"]["risk_level"] == "high"
    assert artifact["executive_summary"]["decision_posture"] == "requires_consultant_review"
    assert len(artifact["risk_signals"]) >= 5
    assert artifact["recommended_hil_questions"]
    assert artifact["initiative_portfolio"][0]["governance_gate"] == "HIL"
