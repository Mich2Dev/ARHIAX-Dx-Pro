from __future__ import annotations

from api.services.grammar_gate import lint_markdown


def test_grammar_gate_blocks_critical_encoding() -> None:
    report = lint_markdown(
        text="# Reporte\n\nTexto con mojibake \u00c3\u00a1 roto.",
        source="test-case",
    )
    assert report["publish_decision"]["allowed"] is False
    assert report["critical"] >= 1
    assert report["report_status"] == "blocked_by_grammar"


def test_grammar_gate_requires_confirmation_on_major_findings() -> None:
    text = (
        "# Diagnóstico ARHIAX\n\n"
        "## Tesis Ejecutiva\n"
        "La operación de Arhiax DxPro requiere ajustes de lenguaje canónico.\n\n"
        "## Contexto\n"
        "Se evaluaron procesos con evidencia multi-rater.\n\n"
        "## Hallazgos\n"
        "Brechas operativas identificadas.\n\n"
        "## Recomendaciones\n"
        "Hoja de ruta en 90 días.\n"
    )
    report = lint_markdown(text=text, source="test-case")
    assert report["publish_decision"]["allowed"] is True
    assert report["publish_decision"]["confirm_required"] is True
    assert report["report_status"] == "consultant_review_required"
    assert report["canonical_engine"] == "marcelo_v0.3"


def test_grammar_gate_allows_publish_when_clean() -> None:
    text = (
        "# Diagnóstico Ejecutivo ARHIAX\n\n"
        "## Tesis Ejecutiva\n"
        + ("La operación presenta fricciones trazables entre áreas y requiere una intervención estructurada. " * 20)
        + "\n\n## Contexto\n"
        + ("Se evaluaron procesos, gobernanza y capacidades tecnológicas con evidencia multi-rater. " * 10)
        + "\n\n## Hallazgos\n"
        + ("Se identificaron cuellos de botella en handoffs, métricas no alineadas y brechas de control. " * 10)
        + "\n\n## Recomendaciones\n"
        + ("Se propone hoja de ruta en 90/180/365 días con controles de seguimiento y ownership definido. " * 10)
    )
    report = lint_markdown(text=text, source="test-case")
    assert report["critical"] == 0
    assert report["publish_decision"]["allowed"] is True
    assert report["publish_decision"]["confirm_required"] is False
    assert report["report_status"] == "draft_ready"
    assert report["rules_count"] == 24
