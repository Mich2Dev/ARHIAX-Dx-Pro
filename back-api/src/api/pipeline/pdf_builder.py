"""
ARHIAX Dx — PDF Report Builder
Generates a professional PDF from pipeline outputs using ReportLab.
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
    # ── Brand palette ─────────────────────────────────────────────────────────
    C_GREEN  = colors.HexColor("#0A7F5A")
    C_DARK   = colors.HexColor("#1A1A2E")
    C_GRAY   = colors.HexColor("#6B7280")
    C_LIGHT  = colors.HexColor("#F0FDF4")
    C_RED    = colors.HexColor("#DC2626")
    C_ORANGE = colors.HexColor("#EA580C")
    C_BLUE   = colors.HexColor("#2563EB")
    C_WHITE  = colors.white
    C_BLACK  = colors.black
except ImportError:
    PDF_AVAILABLE = False
    colors = None  # type: ignore
    C_GREEN = C_DARK = C_GRAY = C_LIGHT = C_RED = C_ORANGE = C_BLUE = C_WHITE = C_BLACK = None
    W = H = 0

# ── Page dimensions (usable width with 2 cm margins each side) ────────────────
# A4 = 21 cm wide; left+right = 4 cm → usable = 17 cm = ~482 pt
_USABLE_W = 17 * cm


def _safe(val: Any, fallback: str = "—") -> str:
    if val is None:
        return fallback
    s = str(val).strip()
    return s if s else fallback


def _p(text: Any, style, fallback: str = "—"):
    """Wrap text in a Paragraph so it wraps inside table cells."""
    return Paragraph(_safe(text, fallback), style)


def _styles():
    base = getSampleStyleSheet()
    custom = {
        "cover_title": ParagraphStyle(
            "cover_title", parent=base["Title"],
            fontSize=28, textColor=C_GREEN, spaceAfter=4, alignment=TA_CENTER,
        ),
        "cover_org": ParagraphStyle(
            "cover_org", parent=base["Title"],
            fontSize=20, textColor=C_DARK, spaceAfter=3, alignment=TA_CENTER,
        ),
        "cover_meta": ParagraphStyle(
            "cover_meta", parent=base["Normal"],
            fontSize=10, textColor=C_GRAY, alignment=TA_CENTER, spaceAfter=2,
        ),
        "h1": ParagraphStyle(
            "h1", parent=base["Heading1"],
            fontSize=15, textColor=C_GREEN, spaceBefore=8, spaceAfter=4,
        ),
        "h2": ParagraphStyle(
            "h2", parent=base["Heading2"],
            fontSize=12, textColor=C_DARK, spaceBefore=6, spaceAfter=3,
        ),
        "body": ParagraphStyle(
            "body", parent=base["Normal"],
            fontSize=10, textColor=C_DARK, spaceAfter=3, leading=13,
        ),
        "body_italic": ParagraphStyle(
            "body_italic", parent=base["Normal"],
            fontSize=10, textColor=C_GRAY, spaceAfter=3, leading=13, italic=True,
        ),
        "bullet": ParagraphStyle(
            "bullet", parent=base["Normal"],
            fontSize=10, textColor=C_DARK, spaceAfter=2, leftIndent=16,
            bulletIndent=6, leading=13,
        ),
        "small": ParagraphStyle(
            "small", parent=base["Normal"],
            fontSize=8, textColor=C_GRAY, spaceAfter=2,
        ),
        "badge_green": ParagraphStyle(
            "badge_green", parent=base["Normal"],
            fontSize=11, textColor=C_GREEN, spaceAfter=3, alignment=TA_CENTER,
        ),
        "badge_red": ParagraphStyle(
            "badge_red", parent=base["Normal"],
            fontSize=11, textColor=C_RED, spaceAfter=3, alignment=TA_CENTER,
        ),
        # Compact style for table cells
        "cell": ParagraphStyle(
            "cell", parent=base["Normal"],
            fontSize=8, textColor=C_DARK, spaceAfter=0, leading=11,
        ),
        "cell_bold": ParagraphStyle(
            "cell_bold", parent=base["Normal"],
            fontSize=8, textColor=C_DARK, spaceAfter=0, leading=11,
            fontName="Helvetica-Bold",
        ),
        "cell_small": ParagraphStyle(
            "cell_small", parent=base["Normal"],
            fontSize=7, textColor=C_GRAY, spaceAfter=0, leading=10,
        ),
    }
    return base, custom


# ── Table styles (built lazily to avoid import-time errors) ──────────────────

def _hdr_style():
    return TableStyle([
        ("BACKGROUND",     (0, 0), (-1, 0), C_GREEN),
        ("TEXTCOLOR",      (0, 0), (-1, 0), C_WHITE),
        ("FONTNAME",       (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",       (0, 0), (-1, -1), 8),
        ("GRID",           (0, 0), (-1, -1), 0.5, C_GRAY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
        ("VALIGN",         (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",     (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 4),
        ("LEFTPADDING",    (0, 0), (-1, -1), 5),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 5),
    ])


def _kv_style():
    return TableStyle([
        ("FONTSIZE",       (0, 0), (-1, -1), 9),
        ("GRID",           (0, 0), (-1, -1), 0.3, colors.HexColor("#E5E7EB")),
        ("BACKGROUND",     (0, 0), (0, -1), C_LIGHT),
        ("FONTNAME",       (0, 0), (0, -1), "Helvetica-Bold"),
        ("VALIGN",         (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",     (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 4),
        ("LEFTPADDING",    (0, 0), (-1, -1), 5),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 5),
    ])


# ── Section builders ──────────────────────────────────────────────────────────

def _cover(diagnostic: Any, qa: dict, irr: dict, s: dict) -> list:
    """Portada centrada verticalmente usando una tabla de una celda que ocupa la pagina."""
    qa_score  = qa.get("qa_score", 0)
    irr_alpha = irr.get("krippendorff_alpha", 0)

    # Construir el bloque central como lista de flowables dentro de una celda
    inner = []
    inner.append(Spacer(1, 0.5 * cm))
    inner.append(Paragraph("DIAGNÓSTICO ORGANIZACIONAL", s["cover_title"]))
    inner.append(Paragraph(diagnostic.organization_name.upper(), s["cover_org"]))
    inner.append(Spacer(1, 0.5 * cm))
    inner.append(HRFlowable(width="80%", thickness=3, color=C_GREEN, spaceAfter=12))
    inner.append(Spacer(1, 0.5 * cm))
    inner.append(Paragraph(f"Sector: {diagnostic.domain}  ·  Área: {diagnostic.subprocess}", s["cover_meta"]))
    inner.append(Paragraph(f"Fecha: {datetime.now().strftime('%d de %B de %Y')}  ·  Versión 1.0", s["cover_meta"]))
    inner.append(Paragraph("Confidencial — Uso Estratégico", s["cover_meta"]))
    inner.append(Spacer(1, 1.5 * cm))

    # Métricas clave en tabla 2 columnas
    metrics = []
    if qa_score:
        qa_style = s["badge_green"] if qa_score >= 85 else s["badge_red"]
        metrics.append(Paragraph(f"QA Score: {qa_score}/100", qa_style))
    if irr_alpha:
        irr_style = s["badge_green"] if irr_alpha >= 0.70 else s["badge_red"]
        metrics.append(Paragraph(f"IRR α Krippendorff: {irr_alpha:.2f}", irr_style))
    for m in metrics:
        inner.append(m)

    inner.append(Spacer(1, 1.5 * cm))

    # Benchmarks / scores por rol si están disponibles
    inner.append(HRFlowable(width="60%", thickness=1, color=C_GRAY, spaceAfter=8))
    inner.append(Spacer(1, 0.3 * cm))

    # Info del diagnóstico en mini-tabla
    extra_rows = []
    if diagnostic.objective:
        extra_rows.append([
            Paragraph("Síntoma diagnosticado", s["cover_meta"]),
            Paragraph(str(diagnostic.objective)[:120], s["cover_meta"]),
        ])
    if diagnostic.size_org:
        extra_rows.append([
            Paragraph("Tamaño organización", s["cover_meta"]),
            Paragraph(f"{diagnostic.size_org} empleados", s["cover_meta"]),
        ])
    extra_rows.append([
        Paragraph("Metodología", s["cover_meta"]),
        Paragraph("Pipeline 18 agentes IA · Multi-Rater · Bayesiano · BPMN", s["cover_meta"]),
    ])
    extra_rows.append([
        Paragraph("Gobernanza", s["cover_meta"]),
        Paragraph("18 reglas · Firma Ed25519 · Ledger append-only", s["cover_meta"]),
    ])

    if extra_rows:
        meta_tbl = Table(extra_rows, colWidths=[5*cm, 12*cm])
        meta_tbl.setStyle(TableStyle([
            ("FONTSIZE",      (0, 0), (-1, -1), 9),
            ("TEXTCOLOR",     (0, 0), (0, -1), C_GRAY),
            ("TEXTCOLOR",     (1, 0), (1, -1), C_DARK),
            ("TOPPADDING",    (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING",   (0, 0), (-1, -1), 0),
            ("ALIGN",         (0, 0), (0, -1), "RIGHT"),
        ]))
        inner.append(meta_tbl)

    inner.append(Spacer(1, 2 * cm))
    inner.append(Paragraph(
        "Preparado por <b>Sinergia Consulting Group</b> · ARHIAX Dx v5.1",
        s["small"]
    ))

    elems = inner + [PageBreak()]
    return elems


def _section_executive_summary(redactor: dict, diagnostic: Any, s: dict) -> list:
    elems = [Paragraph("1. Resumen Ejecutivo", s["h1"])]
    summary = redactor.get("executive_summary", "")
    if not summary:
        summary = (
            f"Diagnóstico organizacional de {diagnostic.organization_name} "
            f"en el área de {diagnostic.subprocess}, sector {diagnostic.domain}. "
            f"Análisis realizado con ARHIAX Dx v5.1 — pipeline de 18 agentes IA."
        )
    elems.append(Paragraph(summary, s["body"]))
    context = redactor.get("context", "")
    if context:
        elems.append(Spacer(1, 0.2 * cm))
        elems.append(Paragraph("Contexto del Diagnóstico", s["h2"]))
        elems.append(Paragraph(context, s["body"]))
    # No PageBreak — short section flows into next
    return elems


def _section_scope(diagnostic: Any, g01: dict, g02: dict, s: dict) -> list:
    elems = [Paragraph("2. Contexto y Alcance", s["h1"])]
    cell = s["cell"]
    rows = [
        [Paragraph("Organización", s["cell_bold"]),    Paragraph(_safe(diagnostic.organization_name), cell)],
        [Paragraph("Sector", s["cell_bold"]),           Paragraph(_safe(diagnostic.domain), cell)],
        [Paragraph("Subproceso", s["cell_bold"]),       Paragraph(_safe(diagnostic.subprocess), cell)],
        [Paragraph("Tamaño", s["cell_bold"]),           Paragraph(f"{diagnostic.size_org} empleados" if diagnostic.size_org else "—", cell)],
        [Paragraph("Objetivo", s["cell_bold"]),         Paragraph(_safe(diagnostic.objective), cell)],
        [Paragraph("Tipo diagnóstico", s["cell_bold"]), Paragraph(_safe(g01.get("diagnostic_type")), cell)],
        [Paragraph("Urgencia", s["cell_bold"]),         Paragraph(_safe(g01.get("urgency")), cell)],
        [Paragraph("Alcance", s["cell_bold"]),          Paragraph(_safe(g02.get("domain_config", {}).get("diagnostic_scope")), cell)],
        [Paragraph("Marcos de ref.", s["cell_bold"]),   Paragraph(", ".join(g02.get("frameworks", [])[:4]) or "—", cell)],
        [Paragraph("Fecha", s["cell_bold"]),            Paragraph(datetime.now().strftime("%d/%m/%Y"), cell)],
    ]
    tbl = Table(rows, colWidths=[4 * cm, 13 * cm])
    tbl.setStyle(_kv_style())
    elems.append(tbl)
    # Scope table is compact — no page break, flows into findings
    return elems


def _section_findings(hallazgos: dict, redactor: dict, bayesiano: dict, s: dict) -> list:
    elems = [Paragraph("3. Hallazgos Principales", s["h1"])]

    exec_sum = hallazgos.get("executive_summary_findings", "")
    if exec_sum:
        elems.append(Paragraph(exec_sum, s["body_italic"]))
        elems.append(Spacer(1, 0.2 * cm))

    findings = hallazgos.get("findings_matrix", [])
    cell = s["cell"]
    cell_s = s["cell_small"]
    if findings:
        # ID=1.2, Hallazgo=10.3, Prioridad=2.2, Confianza=2, Impacto=1.3 → total=17
        data = [[
            Paragraph("ID", s["cell_bold"]),
            Paragraph("Hallazgo", s["cell_bold"]),
            Paragraph("Prioridad", s["cell_bold"]),
            Paragraph("Confianza", s["cell_bold"]),
            Paragraph("Impacto", s["cell_bold"]),
        ]]
        for f in findings[:8]:
            conf = f.get("bayesian_confidence", 0)
            data.append([
                Paragraph(_safe(f.get("id")), cell),
                Paragraph(_safe(f.get("finding")), cell),
                Paragraph(_safe(f.get("priority")), cell),
                Paragraph(f"{conf:.0%}" if conf else "—", cell),
                Paragraph(str(f.get("impact_score", "—")), cell),
            ])
        tbl = Table(data, colWidths=[1.2*cm, 10.3*cm, 2.2*cm, 2*cm, 1.3*cm])
        tbl.setStyle(_hdr_style())
        elems.append(tbl)
    else:
        for f in redactor.get("main_findings", [])[:5]:
            text = f.get("finding", str(f)) if isinstance(f, dict) else str(f)
            elems.append(Paragraph(f"• {text}", s["bullet"]))

    pss = hallazgos.get("problem_statements", [])
    if pss:
        elems.append(Spacer(1, 0.2 * cm))
        elems.append(Paragraph("Declaraciones del Problema", s["h2"]))
        for ps in pss[:3]:
            stmt = ps.get("statement", str(ps)) if isinstance(ps, dict) else str(ps)
            elems.append(Paragraph(f"• {stmt}", s["bullet"]))

    # Confirmed and rejected hypotheses from bayesiano
    confirmed = bayesiano.get("confirmed_hypotheses", [])
    rejected  = bayesiano.get("rejected_hypotheses", [])
    if confirmed or rejected:
        elems.append(Spacer(1, 0.2 * cm))
        elems.append(Paragraph("Hipótesis Confirmadas y Rechazadas", s["h2"]))
        if confirmed:
            elems.append(Paragraph("<font color='#0A7F5A'><b>Confirmadas:</b></font>", s["body"]))
            for h in confirmed[:5]:
                label = h.get("hypothesis", str(h)) if isinstance(h, dict) else str(h)
                elems.append(Paragraph(f"✓ {label}", s["bullet"]))
        if rejected:
            elems.append(Paragraph("<font color='#DC2626'><b>Rechazadas:</b></font>", s["body"]))
            for h in rejected[:5]:
                label = h.get("hypothesis", str(h)) if isinstance(h, dict) else str(h)
                elems.append(Paragraph(f"✗ {label}", s["bullet"]))

    elems.append(PageBreak())
    return elems


def _section_perception_gaps(scoring: dict, bayesiano: dict, redactor: dict, s: dict) -> list:
    elems = [Paragraph("4. Brechas de Percepción Multi-Rater", s["h1"])]

    gaps_text = redactor.get("perception_gaps", "")
    if gaps_text:
        elems.append(Paragraph(gaps_text, s["body"]))
        elems.append(Spacer(1, 0.2 * cm))

    role_scores = scoring.get("role_scores", {})
    cell = s["cell"]
    if role_scores:
        elems.append(Paragraph("Scores por Nivel Jerárquico", s["h2"]))
        data = [[
            Paragraph("Rol", s["cell_bold"]),
            Paragraph("Score", s["cell_bold"]),
            Paragraph("Percepción", s["cell_bold"]),
        ]]
        for role, d in role_scores.items():
            score = d.get("score", 0) if isinstance(d, dict) else 0
            perc  = d.get("perception", "") if isinstance(d, dict) else ""
            data.append([
                Paragraph(str(role), cell),
                Paragraph(str(score), cell),
                Paragraph(perc.capitalize(), cell),
            ])
        tbl = Table(data, colWidths=[5*cm, 3*cm, 9*cm])
        tbl.setStyle(_hdr_style())
        elems.append(tbl)
        elems.append(Spacer(1, 0.2 * cm))

    delta = scoring.get("delta_sigma", {})
    max_gap = delta.get("max_gap", 0)
    if max_gap:
        color = s["badge_red"] if max_gap > 2.0 else s["badge_green"]
        elems.append(Paragraph(f"Brecha de Percepción Máxima: δσ = {max_gap:.2f}", color))
        if max_gap > 2.0:
            elems.append(Paragraph(
                "⚠ BRECHA CRÍTICA — Diferencia significativa entre niveles jerárquicos. "
                "Escalado automático a revisión humana (HIC MEDIUM).", s["body"]
            ))

    dim_scores = scoring.get("dimension_scores", [])
    if dim_scores:
        elems.append(Spacer(1, 0.2 * cm))
        elems.append(Paragraph("Scores por Dimensión", s["h2"]))
        data = [[
            Paragraph("Dimensión", s["cell_bold"]),
            Paragraph("Score", s["cell_bold"]),
            Paragraph("Benchmark", s["cell_bold"]),
            Paragraph("Brecha", s["cell_bold"]),
        ]]
        for d in dim_scores:
            gap = d.get("gap", 0)
            data.append([
                Paragraph(_safe(d.get("name", d.get("dimension"))), cell),
                Paragraph(str(d.get("score", "—")), cell),
                Paragraph(str(d.get("benchmark", "—")), cell),
                Paragraph(f"{gap:+.0f}" if gap else "—", cell),
            ])
        tbl2 = Table(data, colWidths=[7*cm, 2.5*cm, 2.5*cm, 5*cm])
        tbl2.setStyle(_hdr_style())
        elems.append(tbl2)

    # No page break — NLP section follows immediately
    return elems


def _section_nlp(g11b_nlp: dict, s: dict) -> list:
    """4b. Análisis NLP — Respuestas Abiertas (after perception gaps)."""
    if not g11b_nlp:
        return []
    elems = [Paragraph("4b. Análisis NLP — Respuestas Abiertas", s["h1"])]
    cell = s["cell"]

    themes = g11b_nlp.get("themes", [])
    if themes:
        elems.append(Paragraph("Temas Identificados", s["h2"]))
        data = [[
            Paragraph("Tema", s["cell_bold"]),
            Paragraph("Frecuencia", s["cell_bold"]),
            Paragraph("Sentimiento", s["cell_bold"]),
            Paragraph("Descripción", s["cell_bold"]),
        ]]
        for t in themes[:8]:
            if isinstance(t, dict):
                data.append([
                    Paragraph(_safe(t.get("theme", t.get("name"))), cell),
                    Paragraph(str(t.get("frequency", t.get("count", "—"))), cell),
                    Paragraph(_safe(t.get("sentiment", "—")), cell),
                    Paragraph(_safe(t.get("description", "—")), cell),
                ])
            else:
                data.append([Paragraph(str(t), cell), Paragraph("—", cell), Paragraph("—", cell), Paragraph("—", cell)])
        tbl = Table(data, colWidths=[3.5*cm, 2*cm, 2.5*cm, 9*cm])
        tbl.setStyle(_hdr_style())
        elems.append(tbl)
        elems.append(Spacer(1, 0.2 * cm))

    sentiment_by_role = g11b_nlp.get("sentiment_by_role", {})
    if sentiment_by_role:
        elems.append(Paragraph("Sentimiento por Rol", s["h2"]))
        data = [[
            Paragraph("Rol", s["cell_bold"]),
            Paragraph("Positivo", s["cell_bold"]),
            Paragraph("Neutro", s["cell_bold"]),
            Paragraph("Negativo", s["cell_bold"]),
            Paragraph("Dominante", s["cell_bold"]),
        ]]
        for role, d in sentiment_by_role.items():
            if isinstance(d, dict):
                data.append([
                    Paragraph(str(role), cell),
                    Paragraph(str(d.get("positive", d.get("pos", "—"))), cell),
                    Paragraph(str(d.get("neutral", d.get("neu", "—"))), cell),
                    Paragraph(str(d.get("negative", d.get("neg", "—"))), cell),
                    Paragraph(_safe(d.get("dominant", d.get("overall", "—"))), cell),
                ])
            else:
                data.append([Paragraph(str(role), cell), Paragraph(str(d), cell),
                              Paragraph("—", cell), Paragraph("—", cell), Paragraph("—", cell)])
        tbl2 = Table(data, colWidths=[4*cm, 2.5*cm, 2.5*cm, 2.5*cm, 5.5*cm])
        tbl2.setStyle(_hdr_style())
        elems.append(tbl2)
        elems.append(Spacer(1, 0.2 * cm))

    hidden_issues = g11b_nlp.get("hidden_issues", [])
    if hidden_issues:
        elems.append(Paragraph("Problemas Ocultos Detectados", s["h2"]))
        for issue in hidden_issues[:6]:
            text = issue.get("issue", str(issue)) if isinstance(issue, dict) else str(issue)
            elems.append(Paragraph(f"• {text}", s["bullet"]))

    elems.append(PageBreak())
    return elems


def _section_bottlenecks(cuellos: dict, redactor: dict, s: dict) -> list:
    elems = [Paragraph("5. Cuellos de Botella Cuantificados", s["h1"])]

    summary = redactor.get("bottlenecks_summary", "")
    if summary:
        elems.append(Paragraph(summary, s["body"]))

    total_loss = cuellos.get("total_opportunity_loss_usd_month", "")
    total_hours = cuellos.get("total_hours_lost_month", "")
    if total_loss or total_hours:
        parts = []
        if total_loss:
            parts.append(f"<font color='#DC2626'><b>Pérdida total: USD {total_loss}/mes</b></font>")
        if total_hours:
            parts.append(f"<font color='#EA580C'><b>Horas perdidas: {total_hours} h/mes</b></font>")
        elems.append(Paragraph("  ·  ".join(parts), s["body"]))
        elems.append(Spacer(1, 0.2 * cm))

    bottlenecks = cuellos.get("bottlenecks", [])
    cell = s["cell"]
    if bottlenecks:
        data = [[
            Paragraph("ID", s["cell_bold"]),
            Paragraph("Cuello de Botella", s["cell_bold"]),
            Paragraph("Severidad", s["cell_bold"]),
            Paragraph("Impacto", s["cell_bold"]),
            Paragraph("Horas/mes", s["cell_bold"]),
            Paragraph("USD/mes", s["cell_bold"]),
        ]]
        for b in bottlenecks[:7]:
            data.append([
                Paragraph(_safe(b.get("id")), cell),
                Paragraph(_safe(b.get("name")), cell),
                Paragraph(_safe(b.get("severity")), cell),
                Paragraph(str(b.get("impact_score", "—")), cell),
                Paragraph(str(b.get("estimated_hours_lost_month", "—")), cell),
                Paragraph(str(b.get("estimated_cost_usd_month", "—")), cell),
            ])
        tbl = Table(data, colWidths=[1.2*cm, 6.3*cm, 2*cm, 1.5*cm, 2.5*cm, 3.5*cm])
        tbl.setStyle(_hdr_style())
        elems.append(tbl)

    # No page break — bayesian follows
    return elems


def _section_bayesian(bayesiano: dict, s: dict) -> list:
    elems = [Paragraph("6. Análisis Bayesiano de Hipótesis", s["h1"])]

    summary = bayesiano.get("bayesian_summary", "")
    if summary:
        elems.append(Paragraph(summary, s["body"]))
        elems.append(Spacer(1, 0.2 * cm))

    cell = s["cell"]

    # Try multiple key names the agent might use
    analysis = (
        bayesiano.get("bayesian_analysis")
        or bayesiano.get("hypothesis_analysis")
        or bayesiano.get("hypotheses")
        or []
    )
    if analysis:
        elems.append(Paragraph("Tabla de Hipótesis", s["h2"]))
        data = [[
            Paragraph("ID", s["cell_bold"]),
            Paragraph("Hipótesis", s["cell_bold"]),
            Paragraph("Prior", s["cell_bold"]),
            Paragraph("Posterior", s["cell_bold"]),
            Paragraph("Estado", s["cell_bold"]),
        ]]
        for item in analysis[:10]:
            if not isinstance(item, dict):
                continue
            confirmed  = item.get("confirmed", False)
            posterior  = item.get("posterior_probability", item.get("posterior", 0)) or 0
            prior      = item.get("prior_probability", item.get("prior", 0)) or 0
            hyp_text   = _safe(item.get("hypothesis", item.get("hypothesis_text", item.get("description"))))
            hyp_id     = _safe(item.get("hypothesis_id", item.get("id")))
            estado     = "✓ Confirmada" if confirmed else "✗ Rechazada"
            data.append([
                Paragraph(hyp_id, cell),
                Paragraph(hyp_text, cell),
                Paragraph(f"{prior:.2f}" if isinstance(prior, (int, float)) else str(prior), cell),
                Paragraph(f"{posterior:.2f}" if isinstance(posterior, (int, float)) else str(posterior), cell),
                Paragraph(estado, cell),
            ])
        if len(data) > 1:
            tbl = Table(data, colWidths=[1.2*cm, 9*cm, 1.5*cm, 1.5*cm, 3.8*cm])
            tbl.setStyle(_hdr_style())
            elems.append(tbl)
            elems.append(Spacer(1, 0.2 * cm))
    else:
        elems.append(Paragraph("No se encontraron hipótesis bayesianas en este diagnóstico.", s["body_italic"]))

    # Causality map
    causality = (
        bayesiano.get("causality_map")
        or bayesiano.get("causal_map")
        or bayesiano.get("causal_relationships")
        or []
    )
    if causality:
        elems.append(Paragraph("Mapa de Causalidad", s["h2"]))
        if isinstance(causality, list):
            for rel in causality[:8]:
                if isinstance(rel, dict):
                    cause  = _safe(rel.get("cause", rel.get("from", rel.get("source"))))
                    effect = _safe(rel.get("effect", rel.get("to", rel.get("target"))))
                    strength = rel.get("strength", rel.get("weight", ""))
                    label = f"{cause} → {effect}"
                    if strength:
                        label += f"  (fuerza: {strength})"
                    elems.append(Paragraph(f"• {label}", s["bullet"]))
                else:
                    elems.append(Paragraph(f"• {rel}", s["bullet"]))
        elif isinstance(causality, dict):
            for k, v in list(causality.items())[:8]:
                elems.append(Paragraph(f"• {k} → {v}", s["bullet"]))

    elems.append(PageBreak())
    return elems


def _section_irr_by_dimension(irr: dict, s: dict) -> list:
    """6b. IRR por Dimensión — after bayesian section."""
    by_dim = irr.get("by_dimension", {})
    if not by_dim:
        return []
    elems = [Paragraph("6b. IRR por Dimensión", s["h1"])]
    cell = s["cell"]
    data = [[
        Paragraph("Dimensión", s["cell_bold"]),
        Paragraph("Alpha Krippendorff", s["cell_bold"]),
        Paragraph("Estado", s["cell_bold"]),
        Paragraph("Notas", s["cell_bold"]),
    ]]
    for dim_name, dim_data in by_dim.items():
        if isinstance(dim_data, dict):
            alpha  = dim_data.get("krippendorff_alpha", dim_data.get("alpha", "—"))
            status = dim_data.get("status", dim_data.get("irr_status", "—"))
            notes  = dim_data.get("notes", dim_data.get("comment", "—"))
        else:
            alpha  = str(dim_data)
            status = "—"
            notes  = "—"
        alpha_str = f"{alpha:.3f}" if isinstance(alpha, float) else str(alpha)
        data.append([
            Paragraph(str(dim_name), cell),
            Paragraph(alpha_str, cell),
            Paragraph(_safe(status), cell),
            Paragraph(_safe(notes), cell),
        ])
    tbl = Table(data, colWidths=[5*cm, 3*cm, 3*cm, 6*cm])
    tbl.setStyle(_hdr_style())
    elems.append(tbl)
    # Short section — no page break
    return elems


def _section_recommendations(hallazgos: dict, redactor: dict, s: dict) -> list:
    elems = [Paragraph("7. Recomendaciones Estratégicas", s["h1"])]

    recs = hallazgos.get("strategic_recommendations") or redactor.get("strategic_recommendations", [])
    if not recs:
        elems.append(Paragraph("No se generaron recomendaciones.", s["body"]))
        elems.append(PageBreak())
        return elems

    cell = s["cell"]
    # col widths: #=1, Recomendación=8.5, Plazo=2, Impacto=3.5, Inversión=2 → total=17
    data = [[
        Paragraph("#", s["cell_bold"]),
        Paragraph("Recomendación", s["cell_bold"]),
        Paragraph("Plazo", s["cell_bold"]),
        Paragraph("Impacto esperado", s["cell_bold"]),
        Paragraph("Inversión", s["cell_bold"]),
    ]]
    for rec in recs[:6]:
        if not isinstance(rec, dict):
            data.append([Paragraph("—", cell), Paragraph(str(rec), cell),
                         Paragraph("—", cell), Paragraph("—", cell), Paragraph("—", cell)])
            continue
        tf = _safe(rec.get("timeframe", "")).replace("_", " ")
        data.append([
            Paragraph(str(rec.get("priority", rec.get("id", "—"))), cell),
            Paragraph(_safe(rec.get("recommendation")), cell),
            Paragraph(tf, cell),
            Paragraph(_safe(rec.get("expected_impact", rec.get("expected_roi", "—"))), cell),
            Paragraph(_safe(rec.get("investment_level", "—")), cell),
        ])
    tbl = Table(data, colWidths=[1*cm, 8.5*cm, 2*cm, 3.5*cm, 2*cm])
    tbl.setStyle(_hdr_style())
    elems.append(tbl)
    elems.append(PageBreak())
    return elems


def _section_roadmap(redactor: dict, optimizador: dict, s: dict) -> list:
    elems = [Paragraph("8. Roadmap de Implementación", s["h1"])]

    roadmap = redactor.get("roadmap") or optimizador.get("roadmap", {})
    if not roadmap:
        elems.append(Paragraph("Roadmap no disponible.", s["body"]))
        elems.append(PageBreak())
        return elems

    periods = [
        ("days_90",  "Primeros 90 días",  C_GREEN),
        ("days_180", "90 a 180 días",     C_BLUE),
        ("days_365", "180 a 365 días",    C_ORANGE),
    ]
    for key, label, color in periods:
        period = roadmap.get(key, {})
        if not period:
            continue
        elems.append(Paragraph(label, s["h2"]))
        if isinstance(period, dict):
            theme = period.get("theme", "")
            if theme:
                elems.append(Paragraph(f"Tema: {theme}", s["body_italic"]))
            for action in period.get("actions", [])[:5]:
                elems.append(Paragraph(f"• {action}", s["bullet"]))
            outcome = period.get("expected_outcome", "")
            if outcome:
                elems.append(Paragraph(f"Resultado esperado: {outcome}", s["body"]))
        elif isinstance(period, list):
            for action in period[:5]:
                elems.append(Paragraph(f"• {action}", s["bullet"]))
        elems.append(Spacer(1, 0.2 * cm))

    elems.append(PageBreak())
    return elems


def _section_next_steps(redactor: dict, s: dict) -> list:
    elems = [Paragraph("9. Próximos Pasos Inmediatos", s["h1"])]
    steps = redactor.get("next_steps", [])
    if not steps:
        elems.append(Paragraph("No se definieron próximos pasos.", s["body"]))
    for i, step in enumerate(steps[:6], 1):
        elems.append(Paragraph(f"{i}. {step}", s["bullet"]))
    # Short section — no page break, flows into QA
    return elems


def _section_qa(qa: dict, irr: dict, psico: dict, s: dict) -> list:
    elems = [Paragraph("10. Control de Calidad y Gobernanza", s["h1"])]

    qa_score = qa.get("qa_score", 0)
    if qa_score:
        style = s["badge_green"] if qa_score >= 85 else s["badge_red"]
        status = "APROBADO" if qa_score >= 85 else "REQUIERE REVISIÓN"
        elems.append(Paragraph(f"Score QA: {qa_score}/100 — {status}", style))

    dims = qa.get("quality_dimensions", {})
    cell = s["cell"]
    if dims:
        data = [[
            Paragraph("Dimensión QA", s["cell_bold"]),
            Paragraph("Score", s["cell_bold"]),
            Paragraph("Máx", s["cell_bold"]),
        ]]
        for dim_name, dim_data in dims.items():
            score = dim_data.get("score", 0) if isinstance(dim_data, dict) else 0
            max_s = dim_data.get("max", 20) if isinstance(dim_data, dict) else 20
            data.append([
                Paragraph(dim_name.replace("_", " ").title(), cell),
                Paragraph(str(score), cell),
                Paragraph(str(max_s), cell),
            ])
        tbl = Table(data, colWidths=[9*cm, 4*cm, 4*cm])
        tbl.setStyle(_hdr_style())
        elems.append(tbl)
        elems.append(Spacer(1, 0.2 * cm))

    irr_alpha = irr.get("krippendorff_alpha", 0)
    cronbach = psico.get("cronbach_alpha_overall", 0)
    if irr_alpha or cronbach:
        elems.append(Paragraph("Métricas Psicométricas", s["h2"]))
        rows = []
        if irr_alpha:
            rows.append([
                Paragraph("Krippendorff Alpha (IRR)", s["cell_bold"]),
                Paragraph(f"{irr_alpha:.3f}", cell),
                Paragraph(_safe(irr.get("irr_status")), cell),
            ])
        if cronbach:
            rows.append([
                Paragraph("Alpha de Cronbach", s["cell_bold"]),
                Paragraph(f"{cronbach:.3f}", cell),
                Paragraph(_safe(psico.get("internal_consistency")), cell),
            ])
        tbl2 = Table(rows, colWidths=[6*cm, 3*cm, 8*cm])
        tbl2.setStyle(_kv_style())
        elems.append(tbl2)
        elems.append(Spacer(1, 0.2 * cm))

    elems.append(Paragraph(
        "Este informe fue generado por ARHIAX Dx v5.1 bajo el framework de gobernanza de Sinergia Consulting Group. "
        "Pipeline de 18 agentes IA con evaluación de 18 reglas de gobernanza, firma Ed25519 y ledger append-only. "
        "Datos de respondentes procesados de forma anónima.",
        s["small"]
    ))
    return elems


# ── Main entry point ──────────────────────────────────────────────────────────

def build_pdf(diagnostic: Any, stages: list[Any]) -> bytes:
    """
    Build the executive PDF report from pipeline outputs.
    Returns raw bytes of the .pdf file.
    """
    if not PDF_AVAILABLE:
        raise RuntimeError("reportlab not installed. Run: pip install reportlab")

    # Extract outputs from completed stages
    outputs: dict[str, dict] = {}
    for stage in stages:
        if not stage.output or not isinstance(stage.output, dict):
            continue
        # stage.output structure: {"tool": "...", "model_used": "...", "output": {...}}
        # Extract the nested "output" dict, fallback to stage.output if no nesting
        tool_output = stage.output.get("output", {})
        if tool_output and isinstance(tool_output, dict):
            outputs[stage.tool_name] = tool_output
        elif stage.output and "tool" not in stage.output:
            # Legacy format: stage.output is the tool output directly
            outputs[stage.tool_name] = stage.output

    g01         = outputs.get("g01_receptor", {})
    g02         = outputs.get("g02_configurador", {})
    cuellos     = outputs.get("g07_cuellos", {})
    optimizador = outputs.get("g08_optimizador", {})
    scoring     = outputs.get("g10a_scoring", {})
    psico       = outputs.get("g10b_psicometria", {})
    bayesiano   = outputs.get("g11a_bayesiano", {})
    g11b_nlp    = outputs.get("g11b_nlp", {})
    hallazgos   = outputs.get("g12_hallazgos", {})
    redactor    = outputs.get("g13_redactor", {})
    qa          = outputs.get("g14_qa_control", {})
    irr         = outputs.get("irr_calculator", {})

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        title=f"Diagnóstico — {diagnostic.organization_name}",
        author="Sinergia Consulting Group · ARHIAX Dx v5.1",
    )

    _, s = _styles()
    story = []
    story += _cover(diagnostic, qa, irr, s)
    story += _section_executive_summary(redactor, diagnostic, s)
    story += _section_scope(diagnostic, g01, g02, s)
    story += _section_findings(hallazgos, redactor, bayesiano, s)
    story += _section_perception_gaps(scoring, bayesiano, redactor, s)
    story += _section_nlp(g11b_nlp, s)
    story += _section_bottlenecks(cuellos, redactor, s)
    story += _section_bayesian(bayesiano, s)
    story += _section_irr_by_dimension(irr, s)
    story += _section_recommendations(hallazgos, redactor, s)
    story += _section_roadmap(redactor, optimizador, s)
    story += _section_next_steps(redactor, s)
    story += _section_qa(qa, irr, psico, s)

    doc.build(story)
    buf.seek(0)
    return buf.read()

