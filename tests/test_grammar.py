from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from dxpro_runtime.api import create_app
from dxpro_runtime.config import RuntimeConfig
from dxpro_runtime.grammar.models import GrammarException, GrammarReport, PublishDecision
from dxpro_runtime.grammar.lint import lint_text, can_publish, compile_report_text

# Fixtures intencionales de mojibake en tests para verificar detección de encoding roto.
# Los caracteres Ã, Â, ¿ son datos de prueba, no errores reales.


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


# =============================================================================
# Motor lint
# =============================================================================

class TestLintText:
    def test_clean_text_no_findings(self):
        r = lint_text("Texto completamente correcto y canónico.")
        assert r.total == 0
        assert r.score == 100
        assert r.critical == 0
        assert r.major == 0

    def test_mojibake_produces_critical(self):
        r = lint_text("La aprobaciÃ³n todavÃ­a no estÃ¡ lista.")
        assert r.critical >= 1
        assert r.findings[0].severity == "critical"

    def test_hacer_sentido_produces_major(self):
        r = lint_text("La recomendación hace sentido para el cliente.")
        assert r.major >= 1
        assert any("GC-04-CALCO-001" in f.rule_id for f in r.findings)

    def test_en_base_a_produces_major(self):
        r = lint_text("Decidimos en base a los resultados.")
        assert r.major >= 1
        assert any("GC-04-CALCO-002" in f.rule_id for f in r.findings)

    def test_arhiax_minuscula_produces_major(self):
        r = lint_text("Arhiax opera como herramienta.")
        assert r.major >= 1
        assert any("GC-02-TERM-001" in f.rule_id for f in r.findings)

    def test_internal_audience_does_not_flag_custodio(self):
        r = lint_text("El custodio revisó el caso.", audience="internal")
        assert r.total == 0

    def test_client_audience_flags_custodio(self):
        r = lint_text("El custodio revisó el caso.", audience="client")
        assert r.total >= 1
        assert any("GC-07-REG-001" in f.rule_id for f in r.findings)

    def test_dxpro_runtime_path_not_flagged(self):
        r = lint_text("src/dxpro_runtime no debe sugerir Dx Pro.")
        assert not any("GC-02-TERM-003" in f.rule_id for f in r.findings)

    def test_oxford_comma_detected(self):
        r = lint_text("El informe evalúa procesos, datos, y gobernanza.")
        assert any("GC-03-OXFORD-001" in f.rule_id for f in r.findings)

    def test_text_hash_included(self):
        r = lint_text("Texto de prueba.")
        assert len(r.text_hash_sha256) == 64

    def test_score_rounding(self):
        r = lint_text("Ã rotas")
        assert r.score <= 75


# =============================================================================
# Decisión de publicación
# =============================================================================

class TestCanPublish:
    def test_critical_open_blocks(self):
        r = lint_text("Ã rotas")
        d = can_publish(r)
        assert d.allowed is False

    def test_critical_excepted_allows_with_confirm(self):
        r = lint_text("Ã rotas")
        exc = [
            GrammarException(
                finding_id="exc-1",
                rule_id=r.findings[0].rule_id,
                detected_text=r.findings[0].detected_text,
                reason="Texto de prueba controlado",
                reviewer="Test",
                created_at="2026-06-23T00:00:00Z",
            )
        ]
        d = can_publish(r, exc)
        assert d.allowed is True
        assert d.confirm_required is True

    def test_major_open_requires_confirm(self):
        r = lint_text("Arhiax DxPro opera como herramienta.")
        d = can_publish(r)
        assert d.allowed is True
        assert d.confirm_required is True

    def test_major_excepted_allows(self):
        r = lint_text("Arhiax DxPro opera como herramienta.")
        major = [f for f in r.findings if f.severity == "major"]
        exc = [
            GrammarException(
                finding_id=f"exc-{i}",
                rule_id=f.rule_id,
                detected_text=f.detected_text,
                reason="Excepción de prueba",
                reviewer="Test",
                created_at="2026-06-23T00:00:00Z",
            )
            for i, f in enumerate(major)
        ]
        d = can_publish(r, exc)
        assert d.allowed is True
        assert d.confirm_required is False

    def test_clean_allows(self):
        r = lint_text("Texto completamente correcto y canónico.")
        d = can_publish(r)
        assert d.allowed is True
        assert d.confirm_required is False

    def test_empty_exception_does_not_unblock(self):
        r = lint_text("Ã rotas")
        exc = [
            GrammarException(
                finding_id="exc-1",
                rule_id=r.findings[0].rule_id,
                detected_text=r.findings[0].detected_text,
                reason="",
                reviewer="Test",
                created_at="2026-06-23T00:00:00Z",
            )
        ]
        d = can_publish(r, exc)
        assert d.allowed is False


# =============================================================================
# compile_report_text
# =============================================================================

class TestCompileReportText:
    def test_includes_score_and_findings(self):
        r = lint_text("Arhiax DxPro opera como herramienta.")
        text = compile_report_text(r)
        assert "Revisión canónica ARHIAX" in text
        assert str(r.score) in text
        assert "GC-02-TERM" in text

    def test_includes_exception_status(self):
        r = lint_text("Arhiax DxPro opera como herramienta.")
        exc = [
            GrammarException(
                finding_id="exc-1",
                rule_id=r.findings[0].rule_id,
                detected_text=r.findings[0].detected_text,
                reason="Razón de prueba",
                reviewer="Revisor Test",
                created_at="2026-06-23T00:00:00Z",
            )
        ]
        text = compile_report_text(r, exc)
        assert "Excepcionado" in text
        assert "Razón de prueba" in text
        assert "Revisor Test" in text

    def test_reports_no_findings(self):
        r = lint_text("Texto completamente correcto y canónico.")
        text = compile_report_text(r)
        assert "Sin hallazgos" in text


# =============================================================================
# API
# =============================================================================

class TestGrammarAPI:
    def test_lint_endpoint_returns_200(self, tmp_path: Path):
        client = _client(tmp_path)
        resp = client.post("/v1/agents/grammar/lint", json={
            "text": "Arhiax DxPro opera como herramienta.",
            "audience": "client",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["score"] < 100
        assert data["total"] >= 1
        assert data["publish_decision"]["confirm_required"] is True

    def test_lint_endpoint_alias_works(self, tmp_path: Path):
        client = _client(tmp_path)
        resp = client.post("/v1/dxpro/agents/grammar/lint", json={
            "text": "Texto correcto.",
            "audience": "client",
        })
        assert resp.status_code == 200
        assert resp.json()["score"] == 100

    def test_lint_with_case_id_persists(self, tmp_path: Path):
        client = _client(tmp_path)
        case_id = "test-grammar-persist"
        # First create a case
        client.post("/v1/diagnostics/evaluate", json={
            "requested_autonomy_level": "A1",
            "mandate": {"organization_name": "Test"},
            "client": {"client_id": case_id, "legal_name": "Test"},
            "requested_tools": [],
            "requested_operations": [],
            "requested_data_scopes": [],
            "processing_profile": {},
            "simulation": {},
        })
        # Now lint with case_id
        client.post("/v1/agents/grammar/lint", json={
            "text": "Texto con Arhiax mal escrito.",
            "audience": "client",
            "case_id": case_id,
        })
        # Retrieve
        resp = client.get(f"/v1/cases/{case_id}/grammar")
        assert resp.status_code == 200
        data = resp.json()
        assert data["grammar_report"] is not None
        assert data["grammar_report"]["total"] >= 1

    def test_get_case_grammar_no_report(self, tmp_path: Path):
        client = _client(tmp_path)
        resp = client.get("/v1/cases/nonexistent/grammar")
        assert resp.status_code == 200
        data = resp.json()
        assert data["grammar_report"] is None

    def test_lint_empty_text_returns_400(self, tmp_path: Path):
        client = _client(tmp_path)
        resp = client.post("/v1/agents/grammar/lint", json={
            "text": "",
            "audience": "client",
        })
        assert resp.status_code == 400

    def test_lint_invalid_audience_returns_400(self, tmp_path: Path):
        client = _client(tmp_path)
        resp = client.post("/v1/agents/grammar/lint", json={
            "text": "Texto válido.",
            "audience": "invalid",
        })
        assert resp.status_code == 400


# =============================================================================
# Publish / HIL
# =============================================================================

class TestPublishGrammar:
    def test_publish_with_critical_open_blocked(self, tmp_path: Path):
        client = _client(tmp_path)
        case_id = "test-publish-blocked"
        # Create and lint
        client.post("/v1/diagnostics/evaluate", json={
            "requested_autonomy_level": "A1",
            "mandate": {"organization_name": "Test"},
            "client": {"client_id": case_id, "legal_name": "Test"},
            "requested_tools": [],
            "requested_operations": [],
            "requested_data_scopes": [],
            "processing_profile": {},
            "simulation": {},
        })
        client.post("/v1/agents/grammar/lint", json={
            "text": "Ã rotas",
            "audience": "client",
            "case_id": case_id,
        })
        resp = client.post(f"/v1/cases/{case_id}/publish", json={
            "case_id": case_id,
            "action": "publish",
            "grammar_confirmed": False,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["approved"] is False
        assert data["grammar_blocked"] is True

    def test_publish_with_major_open_needs_confirm(self, tmp_path: Path):
        client = _client(tmp_path)
        case_id = "test-publish-confirm"
        client.post("/v1/diagnostics/evaluate", json={
            "requested_autonomy_level": "A1",
            "mandate": {"organization_name": "Test"},
            "client": {"client_id": case_id, "legal_name": "Test"},
            "requested_tools": [],
            "requested_operations": [],
            "requested_data_scopes": [],
            "processing_profile": {},
            "simulation": {},
        })
        client.post("/v1/agents/grammar/lint", json={
            "text": "Arhiax DxPro opera como.",
            "audience": "client",
            "case_id": case_id,
        })
        resp = client.post(f"/v1/cases/{case_id}/publish", json={
            "case_id": case_id,
            "action": "publish",
            "grammar_confirmed": True,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["approved"] is True

    def test_publish_clean_allows(self, tmp_path: Path):
        client = _client(tmp_path)
        case_id = "test-publish-clean"
        client.post("/v1/diagnostics/evaluate", json={
            "requested_autonomy_level": "A1",
            "mandate": {"organization_name": "Test"},
            "client": {"client_id": case_id, "legal_name": "Test"},
            "requested_tools": [],
            "requested_operations": [],
            "requested_data_scopes": [],
            "processing_profile": {},
            "simulation": {},
        })
        client.post("/v1/agents/grammar/lint", json={
            "text": "Texto completamente correcto y canónico.",
            "audience": "client",
            "case_id": case_id,
        })
        resp = client.post(f"/v1/cases/{case_id}/publish", json={
            "case_id": case_id,
            "action": "publish",
            "grammar_confirmed": False,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["approved"] is True


class TestBypassPrevention:
    def test_approval_endpoint_blocks_critical_via_bypass(self, tmp_path: Path):
        client = _client(tmp_path)
        case_id = "test-bypass-critical"
        client.post("/v1/diagnostics/evaluate", json={
            "requested_autonomy_level": "A1",
            "mandate": {"organization_name": "Test"},
            "client": {"client_id": case_id, "legal_name": "Test"},
            "requested_tools": [],
            "requested_operations": [],
            "requested_data_scopes": [],
            "processing_profile": {},
            "simulation": {},
        })
        client.post("/v1/agents/grammar/lint", json={
            "text": "Ã rotas",
            "audience": "client",
            "case_id": case_id,
        })
        resp = client.post("/v1/agents/cases/approval", json={
            "case_id": case_id,
            "action": "publish",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("grammar_blocked") is True
        assert data.get("approved") is False
        assert data.get("grammar_bypass_detected") is True

    def test_approval_endpoint_blocks_major_without_confirm(self, tmp_path: Path):
        client = _client(tmp_path)
        case_id = "test-bypass-major"
        client.post("/v1/diagnostics/evaluate", json={
            "requested_autonomy_level": "A1",
            "mandate": {"organization_name": "Test"},
            "client": {"client_id": case_id, "legal_name": "Test"},
            "requested_tools": [],
            "requested_operations": [],
            "requested_data_scopes": [],
            "processing_profile": {},
            "simulation": {},
        })
        client.post("/v1/agents/grammar/lint", json={
            "text": "Arhiax DxPro opera como.",
            "audience": "client",
            "case_id": case_id,
        })
        resp = client.post("/v1/agents/cases/approval", json={
            "case_id": case_id,
            "action": "publish",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("grammar_confirm_required") is True
        assert data.get("approved") is False

    def test_approval_endpoint_approve_action_passes_through(self, tmp_path: Path):
        client = _client(tmp_path)
        case_id = "test-bypass-approve"
        client.post("/v1/diagnostics/evaluate", json={
            "requested_autonomy_level": "A1",
            "mandate": {"organization_name": "Test"},
            "client": {"client_id": case_id, "legal_name": "Test"},
            "requested_tools": [],
            "requested_operations": [],
            "requested_data_scopes": [],
            "processing_profile": {},
            "simulation": {},
        })
        resp = client.post("/v1/agents/cases/approval", json={
            "case_id": case_id,
            "action": "approve",
        })
        assert resp.status_code == 200
        data = resp.json()
        decisions = data.get("decisions", [])
        assert any(d.get("outcome") == "PERMIT" for d in decisions)


class TestExportGrammar:
    def test_export_blocks_critical_in_final(self, tmp_path: Path):
        from dxpro_runtime.report_exports import ReportExportService
        service = ReportExportService(tmp_path / "exports")
        report_pack = {
            "report_title": "Test",
            "client": {"name": "Test"},
            "engagement_id": "eng-1",
        }
        render_pack = {"markdown": "\u00c3 rotas"}
        with pytest.raises(RuntimeError, match="Export bloqueado por gram"):
            service.export("case-export-critical", report_pack, render_pack, ["docx"])

    def test_export_draft_allows_critical(self, tmp_path: Path):
        from dxpro_runtime.report_exports import ReportExportService
        service = ReportExportService(tmp_path / "exports")
        report_pack = {
            "report_title": "Test",
            "client": {"name": "Test"},
            "engagement_id": "eng-1",
        }
        render_pack = {"markdown": "\u00c3 rotas"}
        result = service.export("case-export-draft", report_pack, render_pack, ["draft", "markdown"])
        assert len(result) > 0
        assert report_pack.get("report_status") == "draft_requires_canonical_review"
        assert "grammar_report" in report_pack

    def test_export_attaches_grammar_report(self, tmp_path: Path):
        from dxpro_runtime.report_exports import ReportExportService
        service = ReportExportService(tmp_path / "exports")
        report_pack = {
            "report_title": "Test",
            "client": {"name": "Test"},
            "engagement_id": "eng-1",
        }
        render_pack = {"markdown": "Texto completamente correcto y canonico."}
        service.export("case-export-clean", report_pack, render_pack, ["markdown"])
        assert "grammar_report" in report_pack
        assert report_pack["grammar_report"]["score"] == 100
