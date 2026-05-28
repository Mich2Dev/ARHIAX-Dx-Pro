"""
ARHIAX DxPro — PDF Report Builder
Genera un PDF ejecutivo completo desde los resultados del ciclo de fusión Pro.
"""
from __future__ import annotations

import io
from datetime import datetime
from typing import Any

try:
    from reportlab.lib import colors as _rl_colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, HRFlowable,
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    PDF_AVAILABLE = True
    colors = _rl_colors
    W, H = A4
    # Paleta Pro
    C_MOSS   = colors.HexColor("#56624b")
    C_CLAY   = colors.HexColor("#9b6d4d")
    C_INK    = colors.HexColor("#171717")
    C_CHAR   = colors.HexColor("#222522")
    C_PAPER  = colors.HexColor("#f4f1ea")
    C_GRAY   = colors.HexColor("#706f69")
    C_RED    = colors.HexColor("#8b3a3a")
    C_NAVY   = colors.HexColor("#243c4f")
    C_WHITE  = colors.white
except ImportError:
    PDF_AVAILABLE = False
    colors = None  # type: ignore
    C_MOSS = C_CLAY = C_INK = C_CHAR = C_PAPER = C_GRAY = C_RED = C_NAVY = C_WHITE = None

_USABLE_W = 17 * cm


def _safe(val: Any, fallback: str = "—") -> str:
    if val is None:
        return fallback
    s = str(val).strip()
    return s if s else fallback


def _p(text: Any, style, fallback: str = "—"):
    return Paragraph(_safe(text, fallback), style)


def _styles():
    base = getSampleStyleSheet()
    s = {
        "cover_title": ParagraphStyle("cover_title", parent=base["Title"],
            fontSize=26, textColor=C_MOSS, spaceAfter=4, alignment=TA_CENTER),
        "cover_org": ParagraphStyle("cover_org", parent=base["Title"],
            fontSize=18, textColor=C_INK, spaceAfter=3, alignment=TA_CENTER),
        "cover_meta": ParagraphStyle("cover_meta", parent=base["Normal"],
            fontSize=10, textColor=C_GRAY, alignment=TA_CENTER, spaceAfter=2),
        "h1": ParagraphStyle("h1", parent=base["Heading1"],
            fontSize=14, textColor=C_MOSS, spaceBefore=8, spaceAfter=4),
        "h2": ParagraphStyle("h2", parent=base["Heading2"],
            fontSize=11, textColor=C_INK, spaceBefore=5, spaceAfter=3),
        "body": ParagraphStyle("body", parent=base["Normal"],
            fontSize=10, textColor=C_INK, spaceAfter=3, leading=14),
        "body_italic": ParagraphStyle("body_italic", parent=base["Normal"],
            fontSize=10, textColor=C_GRAY, spaceAfter=3, leading=14, italic=True),
        "bullet": ParagraphStyle("bullet", parent=base["Normal"],
            fontSize=10, textColor=C_INK, spaceAfter=2, leftIndent=16, bulletIndent=6, leading=13),
        "small": ParagraphStyle("small", parent=base["Normal"],
            fontSize=8, textColor=C_GRAY, spaceAfter=2),
        "mono": ParagraphStyle("mono", parent=base["Normal"],
            fontSize=8, textColor=C_CHAR, spaceAfter=2, fontName="Courier"),
        "badge_ok": ParagraphStyle("badge_ok", parent=base["Normal"],
            fontSize=11, textColor=C_MOSS, spaceAfter=3, alignment=TA_CENTER),
        "badge_warn": ParagraphStyle("badge_warn", parent=base["Normal"],
            fontSize=11, textColor=C_CLAY, spaceAfter=3, alignment=TA_CENTER),
        "badge_err": ParagraphStyle("badge_err", parent=base["Normal"],
            fontSize=11, textColor=C_RED, spaceAfter=3, alignment=TA_CENTER),
        "cell": ParagraphStyle("cell", parent=base["Normal"],
            fontSize=8, textColor=C_INK, spaceAfter=0, leading=11),
        "cell_bold": ParagraphStyle("cell_bold", parent=base["Normal"],
            fontSize=8, textColor=C_INK, spaceAfter=0, leading=11, fontName="Helvetica-Bold"),
        "cell_small": ParagraphStyle("cell_small", parent=base["Normal"],
            fontSize=7, textColor=C_GRAY, spaceAfter=0, leading=10),
    }
    return base, s


def _hdr_style():
    return TableStyle([
        ("BACKGROUND",     (0, 0), (-1, 0), C_MOSS),
        ("TEXTCOLOR",      (0, 0), (-1, 0), C_WHITE),
        ("FONTNAME",       (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",       (0, 0), (-1, -1), 8),
        ("GRID",           (0, 0), (-1, -1), 0.4, C_GRAY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9f8f5")]),
        ("VALIGN",         (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",     (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 4),
        ("LEFTPADDING",    (0, 0), (-1, -1), 5),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 5),
    ])


def _kv_style():
    return TableStyle([
        ("FONTSIZE",       (0, 0), (-1, -1), 9),
        ("GRID",           (0, 0), (-1, -1), 0.3, colors.HexColor("#e8e5de")),
        ("BACKGROUND",     (0, 0), (0, -1), colors.HexColor("#f0ede6")),
        ("FONTNAME",       (0, 0), (0, -1), "Helvetica-Bold"),
        ("VALIGN",         (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",     (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 4),
        ("LEFTPADDING",    (0, 0), (-1, -1), 5),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 5),
    ])


# ── Portada ───────────────────────────────────────────────────────────────────

def _cover(case: Any, fusion: dict, s: dict) -> list:
    scoring = fusion.get("scoring", {})
    overall = scoring.get("overall_score")
    hyps    = fusion.get("hypotheses", [])
    confirmed = sum(1 for h in hyps if h.get("supported"))

    elems = []
    elems.append(Spacer(1, 1.5 * cm))
    elems.append(Paragraph("DIAGNÓSTICO EJECUTIVO PRO", s["cover_title"]))
    elems.append(Paragraph(case.client_name.upper(), s["cover_org"]))
    elems.append(Spacer(1, 0.4 * cm))
    elems.append(HRFlowable(width="70%", thickness=2, color=C_MOSS, spaceAfter=10))
    elems.append(Spacer(1, 0.4 * cm))
    elems.append(Paragraph(f"Dominio: {case.domain}", s["cover_meta"]))
    elems.append(Paragraph(f"Engagement: {case.engagement_id}", s["cover_meta"]))
    elems.append(Paragraph(f"Fecha: {datetime.now().strftime('%d de %B de %Y')}  ·  Versión 1.0", s["cover_meta"]))
    elems.append(Paragraph(case.input_payload.get("confidentiality", "Confidencial — Uso Estratégico") if case.input_payload else "Confidencial — Uso Estratégico", s["cover_meta"]))
    elems.append(Spacer(1, 1 * cm))

    # Métricas clave
    if overall is not None:
        badge_style = s["badge_ok"] if overall >= 70 else s["badge_warn"]
        elems.append(Paragraph(f"Índice de Madurez: {overall}/100", badge_style))
    if hyps:
        elems.append(Paragraph(f"Hipótesis confirmadas: {confirmed}/{len(hyps)}", s["badge_ok"]))

    elems.append(Spacer(1, 1.5 * cm))
    elems.append(HRFlowable(width="50%", thickness=1, color=C_GRAY, spaceAfter=8))
    elems.append(Spacer(1, 0.3 * cm))

    # Info del caso
    extra = case.input_payload or {}
    rows = []
    if extra.get("contact_name"):
        rows.append([_p("Contacto", s["cover_meta"]), _p(f"{extra['contact_name']} · {extra.get('contact_role','')}", s["cover_meta"])])
    if extra.get("sector"):
        rows.append([_p("Sector", s["cover_meta"]), _p(extra["sector"], s["cover_meta"])])
    rows.append([_p("Roles evaluados", s["cover_meta"]), _p(", ".join(extra.get("roles", [])), s["cover_meta"])])
    rows.append([_p("Dimensiones", s["cover_meta"]), _p(", ".join(extra.get("dimensions", [])), s["cover_meta"])])
    rows.append([_p("Gobernanza", s["cover_meta"]), _p("PMEL/ATK · Evidence Ledger HMAC · Ciclo de Fusión", s["cover_meta"])])

    if rows:
        tbl = Table(rows, colWidths=[4.5*cm, 12.5*cm])
        tbl.setStyle(TableStyle([
            ("FONTSIZE", (0,0), (-1,-1), 9),
            ("TEXTCOLOR", (0,0), (0,-1), C_GRAY),
            ("TOPPADDING", (0,0), (-1,-1), 3),
            ("BOTTOMPADDING", (0,0), (-1,-1), 3),
            ("LEFTPADDING", (0,0), (-1,-1), 0),
            ("ALIGN", (0,0), (0,-1), "RIGHT"),
        ]))
        elems.append(tbl)

    elems.append(Spacer(1, 2 * cm))
    elems.append(Paragraph("Preparado por <b>Sinergia Consulting Group</b> · ARHIAX DxPro v1", s["small"]))
    elems.append(PageBreak())
    return elems


# ── Tabla de contenidos ───────────────────────────────────────────────────────

def _toc(s: dict) -> list:
    elems = [Paragraph("Contenido", s["h1"])]
    sections = [
        ("1.", "Resumen Ejecutivo y Tesis Diagnóstica"),
        ("2.", "Contexto y Alcance del Caso"),
        ("3.", "Índice de Madurez — Scoring por Dimensión"),
        ("4.", "Hipótesis Evaluadas — Síntesis Bayesiana"),
        ("5.", "Señales de Riesgo"),
        ("6.", "Reporte Ejecutivo — Secciones"),
        ("7.", "Gobernanza PMEL/ATK — Evidencia"),
        ("8.", "Próximo Paso Recomendado"),
    ]
    data = [[_p(n, s["cell_bold"]), _p(t, s["cell"])] for n, t in sections]
    tbl = Table(data, colWidths=[1.5*cm, 15.5*cm])
    tbl.setStyle(TableStyle([
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#e8e5de")),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [colors.white, colors.HexColor("#f9f8f5")]),
    ]))
    elems.append(tbl)
    elems.append(PageBreak())
    return elems


# ── Sección 1: Resumen ejecutivo ──────────────────────────────────────────────

def _section_executive(fusion: dict, report: dict, s: dict) -> list:
    elems = [Paragraph("1. Resumen Ejecutivo y Tesis Diagnóstica", s["h1"])]
    thesis = fusion.get("executive_thesis", "")
    if thesis:
        elems.append(Paragraph(thesis, s["body"]))
    next_step = fusion.get("recommended_next_step", "")
    if next_step:
        elems.append(Spacer(1, 0.2*cm))
        elems.append(Paragraph("Próximo paso recomendado:", s["h2"]))
        elems.append(Paragraph(next_step, s["body"]))
    # Resumen del reporte si existe
    sections = report.get("sections", [])
    exec_section = next((sec for sec in sections if "resumen" in sec.get("title","").lower() or "ejecutivo" in sec.get("title","").lower()), None)
    if exec_section and exec_section.get("content"):
        elems.append(Spacer(1, 0.2*cm))
        elems.append(Paragraph(exec_section["content"], s["body_italic"]))
    return elems


# ── Sección 2: Contexto ───────────────────────────────────────────────────────

def _section_context(case: Any, s: dict) -> list:
    elems = [Paragraph("2. Contexto y Alcance del Caso", s["h1"])]
    extra = case.input_payload or {}
    cell = s["cell"]
    rows = [
        [_p("Cliente", s["cell_bold"]),         _p(case.client_name, cell)],
        [_p("Razón social", s["cell_bold"]),     _p(extra.get("legal_name", "—"), cell)],
        [_p("NIT", s["cell_bold"]),              _p(extra.get("nit", "—"), cell)],
        [_p("Sector", s["cell_bold"]),           _p(extra.get("sector", case.domain), cell)],
        [_p("Ciudad", s["cell_bold"]),           _p(f"{extra.get('city','—')}, {extra.get('country','Colombia')}", cell)],
        [_p("Empleados", s["cell_bold"]),        _p(extra.get("size_org", "—"), cell)],
        [_p("Años operando", s["cell_bold"]),    _p(extra.get("years_operating", "—"), cell)],
        [_p("Contacto", s["cell_bold"]),         _p(f"{extra.get('contact_name','—')} · {extra.get('contact_role','—')}", cell)],
        [_p("Email", s["cell_bold"]),            _p(extra.get("contact_email", "—"), cell)],
        [_p("Dominio", s["cell_bold"]),          _p(case.domain, cell)],
        [_p("Síntoma", s["cell_bold"]),          _p(extra.get("symptom", "—"), cell)],
        [_p("Desde", s["cell_bold"]),            _p(extra.get("problem_since", "—"), cell)],
        [_p("Resultado esperado", s["cell_bold"]), _p(extra.get("expected_outcome", "—"), cell)],
        [_p("Engagement ID", s["cell_bold"]),    _p(case.engagement_id, cell)],
        [_p("Confidencialidad", s["cell_bold"]), _p(extra.get("confidentiality", "Confidencial"), cell)],
    ]
    tbl = Table(rows, colWidths=[4.5*cm, 12.5*cm])
    tbl.setStyle(_kv_style())
    elems.append(tbl)
    elems.append(PageBreak())
    return elems


# ── Sección 3: Scoring ────────────────────────────────────────────────────────

def _section_scoring(fusion: dict, s: dict) -> list:
    elems = [Paragraph("3. Índice de Madurez — Scoring por Dimensión", s["h1"])]
    scoring = fusion.get("scoring", {})
    overall = scoring.get("overall_score")
    if overall is not None:
        badge = s["badge_ok"] if overall >= 70 else s["badge_warn"]
        elems.append(Paragraph(f"Índice global de madurez: {overall}/100", badge))
        elems.append(Spacer(1, 0.3*cm))

    dim_scores = scoring.get("dimension_scores", [])
    if dim_scores:
        cell = s["cell"]
        data = [[
            _p("Dimensión", s["cell_bold"]),
            _p("Score", s["cell_bold"]),
            _p("Benchmark", s["cell_bold"]),
            _p("Brecha", s["cell_bold"]),
            _p("Estado", s["cell_bold"]),
        ]]
        for d in dim_scores:
            gap = d.get("gap", 0)
            score = d.get("score", 0)
            estado = "✓ Por encima" if gap >= 0 else ("⚠ Brecha media" if gap >= -15 else "✗ Brecha crítica")
            data.append([
                _p(d.get("dimension", "—"), cell),
                _p(str(score), cell),
                _p(str(d.get("benchmark", 75)), cell),
                _p(f"{gap:+.0f}" if gap else "—", cell),
                _p(estado, cell),
            ])
        tbl = Table(data, colWidths=[5*cm, 2*cm, 2.5*cm, 2.5*cm, 5*cm])
        tbl.setStyle(_hdr_style())
        elems.append(tbl)

    roles = scoring.get("role_coverage", [])
    if roles:
        elems.append(Spacer(1, 0.3*cm))
        elems.append(Paragraph(f"Roles evaluados: {', '.join(roles)}", s["body"]))

    elems.append(PageBreak())
    return elems


# ── Sección 4: Hipótesis bayesianas ──────────────────────────────────────────

def _section_hypotheses(fusion: dict, s: dict) -> list:
    elems = [Paragraph("4. Hipótesis Evaluadas — Síntesis Bayesiana", s["h1"])]
    hyps = fusion.get("hypotheses", [])
    if not hyps:
        elems.append(Paragraph("No se definieron hipótesis para este diagnóstico.", s["body_italic"]))
        return elems

    cell = s["cell"]
    data = [[
        _p("ID", s["cell_bold"]),
        _p("Hipótesis", s["cell_bold"]),
        _p("Prior", s["cell_bold"]),
        _p("Posterior", s["cell_bold"]),
        _p("Estado", s["cell_bold"]),
    ]]
    for i, h in enumerate(hyps):
        confirmed = h.get("supported", False)
        data.append([
            _p(h.get("id", f"H{i+1}"), cell),
            _p(h.get("statement", "—"), cell),
            _p(str(h.get("prior", "—")), cell),
            _p(str(h.get("posterior", "—")), cell),
            _p("✓ Confirmada" if confirmed else "✗ No confirmada", cell),
        ])
    tbl = Table(data, colWidths=[1.2*cm, 9*cm, 1.5*cm, 1.8*cm, 3.5*cm])
    tbl.setStyle(_hdr_style())
    elems.append(tbl)
    elems.append(PageBreak())
    return elems


# ── Sección 5: Señales de riesgo ─────────────────────────────────────────────

def _section_risks(fusion: dict, s: dict) -> list:
    risks = fusion.get("risk_signals", [])
    if not risks:
        return []
    elems = [Paragraph("5. Señales de Riesgo", s["h1"])]
    cell = s["cell"]
    data = [[_p("Señal", s["cell_bold"]), _p("Severidad", s["cell_bold"])]]
    for r in risks:
        data.append([_p(r.get("signal", "—"), cell), _p(r.get("severity", "—").upper(), cell)])
    tbl = Table(data, colWidths=[13*cm, 4*cm])
    tbl.setStyle(_hdr_style())
    elems.append(tbl)
    elems.append(PageBreak())
    return elems


# ── Sección 6: Secciones del reporte ─────────────────────────────────────────

def _section_report(report: dict, s: dict) -> list:
    sections = report.get("sections", [])
    if not sections:
        return []
    elems = [Paragraph("6. Reporte Ejecutivo", s["h1"])]
    for sec in sections:
        title = sec.get("title", "")
        content = sec.get("content", "")
        if title:
            elems.append(Paragraph(title, s["h2"]))
        if content:
            elems.append(Paragraph(content, s["body"]))
        elems.append(Spacer(1, 0.2*cm))
    elems.append(PageBreak())
    return elems


# ── Sección 7: Gobernanza PMEL ────────────────────────────────────────────────

def _section_governance(case: Any, evidence: list, s: dict) -> list:
    elems = [Paragraph("7. Gobernanza PMEL/ATK — Evidencia", s["h1"])]
    cell = s["cell"]

    # Info del caso
    rows = [
        [_p("Case ID", s["cell_bold"]),      _p(case.case_id, cell)],
        [_p("Trace ID", s["cell_bold"]),     _p(case.trace_id or "—", cell)],
        [_p("PMEL Outcome", s["cell_bold"]), _p(case.pmel_outcome or "—", cell)],
        [_p("Aprobación", s["cell_bold"]),   _p(case.approval_status or "—", cell)],
        [_p("Revisor", s["cell_bold"]),      _p(case.reviewer_name or "—", cell)],
        [_p("Comentario", s["cell_bold"]),   _p(case.review_comment or "—", cell)],
    ]
    tbl = Table(rows, colWidths=[4*cm, 13*cm])
    tbl.setStyle(_kv_style())
    elems.append(tbl)

    # Evidencia
    if evidence:
        elems.append(Spacer(1, 0.4*cm))
        elems.append(Paragraph("Entradas de Evidencia Gobernada", s["h2"]))
        data = [[
            _p("Tipo", s["cell_bold"]),
            _p("Outcome", s["cell_bold"]),
            _p("Agente", s["cell_bold"]),
            _p("Timestamp", s["cell_bold"]),
        ]]
        for e in evidence[:15]:
            ts = e.get("created_at", "")
            if ts and len(ts) > 16:
                ts = ts[:16].replace("T", " ")
            data.append([
                _p(e.get("event_type", "—"), cell),
                _p(e.get("outcome", "—"), cell),
                _p(e.get("agent", "—"), cell),
                _p(ts, cell),
            ])
        tbl2 = Table(data, colWidths=[4.5*cm, 2.5*cm, 5*cm, 5*cm])
        tbl2.setStyle(_hdr_style())
        elems.append(tbl2)

    elems.append(PageBreak())
    return elems


# ── Sección 8: Próximo paso ───────────────────────────────────────────────────

def _section_next_step(fusion: dict, s: dict) -> list:
    next_step = fusion.get("recommended_next_step", "")
    if not next_step:
        return []
    elems = [Paragraph("8. Próximo Paso Recomendado", s["h1"])]
    elems.append(Paragraph(next_step, s["body"]))
    elems.append(Spacer(1, 0.5*cm))
    elems.append(Paragraph(
        "Este diagnóstico fue generado con el ciclo de fusión gobernado PMEL/ATK de ARHIAX DxPro v1. "
        "Toda la evidencia está registrada en el ledger append-only con cadena HMAC.",
        s["small"]
    ))
    return elems


# ── Builder principal ─────────────────────────────────────────────────────────

def build_pro_pdf(case: Any, evidence: list | None = None) -> bytes:
    """
    Genera el PDF ejecutivo completo del caso Pro.
    case: instancia de ProCase con fusion_result, report_result, etc.
    evidence: lista de entradas de evidencia del ledger.
    """
    if not PDF_AVAILABLE:
        raise RuntimeError("reportlab no está instalado")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
        title=f"Diagnóstico Pro — {case.client_name}",
        author="ARHIAX DxPro v1 · Sinergia Consulting Group",
    )

    _, s = _styles()
    fusion  = case.fusion_result  or {}
    report  = case.report_result  or {}
    ev_list = evidence or []

    story = []
    story += _cover(case, fusion, s)
    story += _toc(s)
    story += _section_executive(fusion, report, s)
    story += _section_context(case, s)
    story += _section_scoring(fusion, s)
    story += _section_hypotheses(fusion, s)
    story += _section_risks(fusion, s)
    story += _section_report(report, s)
    story += _section_governance(case, ev_list, s)
    story += _section_next_step(fusion, s)

    doc.build(story)
    buf.seek(0)
    return buf.read()
