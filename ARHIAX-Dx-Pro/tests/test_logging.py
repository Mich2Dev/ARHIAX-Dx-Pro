"""Tests for structured logging and metrics endpoints."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from dxpro_runtime.api import create_app
from dxpro_runtime.config import RuntimeConfig
from dxpro_runtime.logging_config import METRICS, log_event, log_llm_call, log_llm_error, log_pmel_decision


def _client(tmp_path: Path) -> TestClient:
    config = RuntimeConfig(
        root_dir=tmp_path,
        ledger_path=tmp_path / "evidence.jsonl",
        evidence_secret="test-secret",
        policy_bundle_path=tmp_path / "missing-bundle",
        case_store_root=tmp_path / "cases",
        export_root=tmp_path / "exports",
    )
    return TestClient(create_app(config))


def test_healthz_includes_new_fields(tmp_path: Path) -> None:
    client = _client(tmp_path)
    response = client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "llm_available" in body
    assert "opa_mode" in body
    assert "ledger_ok" in body
    assert isinstance(body["llm_available"], bool)
    assert isinstance(body["ledger_ok"], bool)
    assert isinstance(body["opa_mode"], str)


def test_healthz_llm_available_false_without_api_key(tmp_path: Path) -> None:
    client = _client(tmp_path)
    body = client.get("/healthz").json()
    # No ANTHROPIC_API_KEY configured in test client
    assert body["llm_available"] is False


def test_metrics_endpoint_returns_counters(tmp_path: Path) -> None:
    client = _client(tmp_path)
    # Make a request to increment counters
    client.get("/healthz")
    response = client.get("/v1/metrics")
    assert response.status_code == 200
    body = response.json()
    assert "requests_total" in body
    assert "requests_by_status" in body
    assert "llm_calls_total" in body
    assert "llm_errors_total" in body
    assert "pmel_decisions_by_outcome" in body
    assert isinstance(body["requests_total"], int)
    assert body["requests_total"] >= 0


def test_metrics_increments_on_requests(tmp_path: Path) -> None:
    client = _client(tmp_path)
    before = client.get("/v1/metrics").json()["requests_total"]
    client.get("/healthz")
    client.get("/healthz")
    after = client.get("/v1/metrics").json()["requests_total"]
    assert after > before


def test_log_event_emits_json(capsys: object) -> None:
    log_event("test_event", trace_id="trace-001", foo="bar")
    captured = getattr(capsys, "readouterr")()
    lines = [l for l in captured.out.strip().splitlines() if l]
    assert lines, "Expected at least one log line"
    entry = json.loads(lines[-1])
    assert entry["event"] == "test_event"
    assert entry["trace_id"] == "trace-001"
    assert entry["service"] == "arhiax-dxpro"
    assert "timestamp" in entry
    assert "level" in entry


def test_log_event_has_required_fields(capsys: object) -> None:
    log_event("check_fields", trace_id="t-123")
    captured = getattr(capsys, "readouterr")()
    lines = [l for l in captured.out.strip().splitlines() if l]
    entry = json.loads(lines[-1])
    for field in ("timestamp", "level", "service", "trace_id", "event"):
        assert field in entry, f"Missing field: {field}"


def test_log_llm_call_increments_counter(capsys: object) -> None:
    before = METRICS.llm_calls_total
    log_llm_call(trace_id="t-llm", model="claude-sonnet-4-6", input_tokens=100, output_tokens=200)
    assert METRICS.llm_calls_total == before + 1


def test_log_llm_error_increments_counter(capsys: object) -> None:
    before = METRICS.llm_errors_total
    log_llm_error(trace_id="t-err", model="claude-sonnet-4-6", error="timeout")
    assert METRICS.llm_errors_total == before + 1


def test_log_pmel_decision_increments_counter(capsys: object) -> None:
    before = METRICS.pmel_decisions_by_outcome.get("PERMIT", 0)
    log_pmel_decision(trace_id="t-pmel", outcome="PERMIT", agent="test_agent")
    assert METRICS.pmel_decisions_by_outcome["PERMIT"] == before + 1
