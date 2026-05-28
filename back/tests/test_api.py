from __future__ import annotations

import json


def test_healthz(client):
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_compliance_posture_exposes_governance_contract(client):
    response = client.get("/v1/compliance/posture")

    assert response.status_code == 200
    payload = response.json()
    assert payload["agent_identity"]["name"] == "ARHIAX-Dx-v1"
    assert payload["autonomy_profile"]["promotion_requirements"]["to"] == "A2"
    assert len(payload["tool_manifest"]) == 24


def test_evaluate_allow_writes_evidence_and_certificate(client, settings, request_payload):
    response = client.post("/v1/diagnostics/evaluate", json=request_payload)

    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"]["status"] == "ALLOW"
    assert payload["execution_plan"]["execution_status"] == "PASS"
    assert payload["certificate"] is not None
    lines = settings.ledger_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["decision"] == "ALLOW"


def test_evaluate_publication_escalates(client, request_payload):
    request_payload["processing_profile"]["publish_report"] = True

    response = client.post("/v1/diagnostics/evaluate", json=request_payload)

    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"]["status"] == "ESCALATE_TO_HUMAN"
    assert payload["human_review_required"] is True
