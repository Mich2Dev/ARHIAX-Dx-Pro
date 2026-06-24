"""Tests for server startup and factory pattern."""

from __future__ import annotations

from pathlib import Path

from dxpro_runtime.api import create_app
from dxpro_runtime.config import RuntimeConfig
from fastapi.testclient import TestClient


def _config(tmp_path: Path) -> RuntimeConfig:
    return RuntimeConfig(
        root_dir=tmp_path,
        ledger_path=tmp_path / "evidence.jsonl",
        evidence_secret="test-secret",
        policy_bundle_path=Path(__file__).parent.parent / "policy-bundle-pmel-v1.0.0",
        case_store_root=tmp_path / "cases",
        export_root=tmp_path / "exports",
    )


def test_create_app_returns_fastapi_app(tmp_path: Path) -> None:
    app = create_app(_config(tmp_path))
    assert app is not None
    assert hasattr(app, "router")
    assert len(app.router.routes) > 0


def test_create_app_healthz_responds(tmp_path: Path) -> None:
    app = create_app(_config(tmp_path))
    client = TestClient(app)
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json().get("status") == "ok"


def test_create_app_is_callable_twice(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    app1 = create_app(cfg)
    app2 = create_app(cfg)
    assert app1.title == app2.title
    assert len(app1.router.routes) == len(app2.router.routes)
