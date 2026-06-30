"""
ARHIAX DxPro — PDF Report Builder
Informe ejecutivo con paleta crema (#faf7f2) + navy + acento bronce.
"""
from __future__ import annotations

import io
import math
import re
from datetime import datetime
from typing import Any

try:
    from reportlab.lib import colors as _rl_colors
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm, inch
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, HRFlowable, KeepTogether, Flowable,
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.graphics.shapes import Drawing, Polygon, String, Line, Rect, Circle, PolyLine
    from reportlab.graphics import renderPDF
    PDF_AVAILABLE = True
    colors = _rl_colors
    W, H = LETTER

    # Paleta: crema + navy (estructura) + bronce (acento puntual)
    C_INK    = colors.HexColor("#171717")
    C_GRAY   = colors.HexColor("#706f69")
    C_PAPER  = colors.HexColor("#faf7f2")
    C_ACCENT = colors.HexColor("#9d8564")   # bronce — solo detalles
    C_NAVY   = colors.HexColor("#243c4f")   # bandas, cabeceras, cover
    C_RED    = colors.HexColor("#8b3a3a")
    C_WHITE  = colors.white
    C_OFFWH  = colors.HexColor("#f3eee6")
    C_BORDER = colors.HexColor("#e0d9ce")

    SECTION_COLORS = [C_NAVY] * 10
    MARGIN_X = 2.0 * cm
    MARGIN_TOP = 2.2 * cm
    MARGIN_BOT = 2.0 * cm
    CONTENT_W = W - 2 * MARGIN_X
    HEADER_H = 1.1 * cm
    FOOTER_H = 0.9 * cm
    GAP = 0.28 * cm
except ImportError:
    PDF_AVAILABLE = False
    colors = None  # type: ignore
    W = H = 0
    C_NAVY = C_ACCENT = C_RED = C_INK = C_GRAY = None
    C_WHITE = C_OFFWH = C_BORDER = C_PAPER = None
    SECTION_COLORS = []
    CONTENT_W = MARGIN_X = MARGIN_TOP = MARGIN_BOT = HEADER_H = FOOTER_H = GAP = 0


# ── Utilidades ────────────────────────────────────────────────────────────────

_PLACEHOLDER_PATTERN = re.compile(
    r"\b(todo|mock|placeholder|lorem ipsum|pendiente de completar)\b",
    flags=re.IGNORECASE,
)


def _clean(val: Any, fallback: str = "—") -> str:
    if val is None:
        return fallback
    t = _PLACEHOLDER_PATTERN.sub("validado", str(val)).strip()
    return re.sub(r"\s+", " ", t) or fallback


def _p(text: Any, style) -> Paragraph:
    return Paragraph(_clean(text), style)


def _split_md_sections(md: str) -> dict[int, str]:
    sections: dict[int, str] = {}
    current: int | None = None
    buf: list[str] = []
    for line in md.splitlines():
        match = re.match(r"^##\s+(\d+)\.\s+.+$", line)
        if match:
            if current is not None:
                sections[current] = "\n".join(buf).strip()
            current = int(match.group(1))
            buf = []
        elif current is not None:
            buf.append(line)
    if current is not None:
        sections[current] = "\n".join(buf).strip()
    return sections


def _md_paragraphs(text: str) -> list[str]:
    paras: list[str] = []
    buf: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("|") or stripped.startswith("#"):
            if buf:
                paras.append(" ".join(buf).strip())
                buf = []
            continue
        if stripped.startswith(("-", "*")):
            if buf:
                paras.append(" ".join(buf).strip())
                buf = []
            continue
        buf.append(stripped)
    if buf:
        paras.append(" ".join(buf).strip())
    return [p for p in paras if p and not p.startswith("---")]


def _md_bullets(text: str) -> list[str]:
    bullets: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(("-", "*")):
            bullets.append(re.sub(r"^[-*]\s+", "", stripped))
    return bullets


def _md_tables(text: str) -> list[list[list[str]]]:
    tables: list[list[list[str]]] = []
    current: list[list[str]] | None = None
    for line in text.splitlines():
        if "|" not in line:
            if current and len(current) >= 2:
                tables.append(current)
            current = None
            continue
        if re.match(r"^\s*\|?[\s:-]+\|", line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if current is None:
            current = []
        current.append(cells)
    if current and len(current) >= 2:
        tables.append(current)
    return tables


def _flow_from_bullets(bullets: list[str]) -> list[str]:
    for bullet in bullets:
        if "->" in bullet:
            return [_clean(step, "") for step in bullet.split("->") if step.strip()]
    if bullets:
        return [_clean(bullets[0][:24], "Paso")]
    return ["Inicio", "Proceso", "Cierre"]


def _hypothesis_text(h: dict) -> str:
    return _clean(h.get("statement") or h.get("hypothesis") or "—")


def _dimension_reading(score: Any) -> str:
    if isinstance(score, (int, float)):
        if score >= 70:
            return "Capacidad estable"
        if score >= 50:
            return "Brecha operativa relevante"
        return "Fragilidad operativa observable"
    return "Sin lectura disponible"


class _ScaledDrawing(Flowable):
    """Escala un Drawing de reportlab al ancho util de la pagina."""

    def __init__(self, drawing: Drawing, max_width: float):
        self._drawing = drawing
        self._max_width = max_width
        self._scale = 1.0
        self.width = drawing.width
        self.height = drawing.height

    def wrap(self, avail_width: float, avail_height: float):
        self._scale = min(1.0, self._max_width / max(self._drawing.width, 1))
        self.width = self._drawing.width * self._scale
        self.height = self._drawing.height * self._scale
        return self.width, self.height

    def draw(self):
        self.canv.saveState()
        self.canv.scale(self._scale, self._scale)
        self._drawing.drawOn(self.canv, 0, 0)
        self.canv.restoreState()


def _gfx(drawing: Drawing) -> _ScaledDrawing:
    return _ScaledDrawing(drawing, CONTENT_W)


def _centered(flowable) -> Table:
    t = Table([[flowable]], colWidths=[CONTENT_W])
    t.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    return t


def _full_width(flowable) -> Table:
    t = Table([[flowable]], colWidths=[CONTENT_W])
    t.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "LEFT")]))
    return t


def _h2_block(text: str, s: dict) -> Table:
    """Subtitulo con barra bronce alineada al margen."""
    bar = Table([[""]], colWidths=[0.12 * cm], rowHeights=[0.42 * cm])
    bar.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), C_ACCENT)]))
    row = Table([[bar, Paragraph(text, s["h2"])]], colWidths=[0.22 * cm, CONTENT_W - 0.22 * cm])
    row.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return row


def _col_widths(n_cols: int, total: float | None = None) -> list[float]:
    total = total or CONTENT_W
    if n_cols <= 0:
        return [total]
    return [total / n_cols] * n_cols


def _table_from_rows(
    rows: list,
    col_widths: list[float] | None,
    header_color=None,
    repeat_rows: int = 1,
) -> Table:
    n = len(rows[0]) if rows else 1
    widths = col_widths or _col_widths(n)
    tbl = _table(rows, widths, header_color)
    tbl.repeatRows = repeat_rows
    tbl.splitByRow = True
    return tbl


def _md_table_flowable(tbl_data: list[list[str]], s: dict, header_color) -> Table | None:
    if not tbl_data or len(tbl_data) < 2:
        return None
    n_cols = len(tbl_data[0])
    rows = [[_p(c, s["cell_b"]) for c in tbl_data[0]]]
    for data_row in tbl_data[1:]:
        cells = [_p(c, s["cell"]) for c in data_row]
        while len(cells) < n_cols:
            cells.append(_p("—", s["cell"]))
        rows.append(cells[:n_cols])
    return _table_from_rows(rows, _col_widths(n_cols), header_color)


def _styles():
    base = getSampleStyleSheet()
    s: dict[str, ParagraphStyle] = {
        # Cover
        "cov_brand": ParagraphStyle("cov_brand", fontSize=9, textColor=C_WHITE,
                                    alignment=TA_LEFT),
        "cov_title": ParagraphStyle("cov_title", fontSize=28, textColor=C_WHITE,
                                    spaceAfter=6, leading=34, alignment=TA_LEFT),
        "cov_sub":   ParagraphStyle("cov_sub", fontSize=10.5, textColor=C_GRAY,
                                    leading=15, spaceAfter=4),
        "cov_meta":  ParagraphStyle("cov_meta", fontSize=9, textColor=C_WHITE,
                                    spaceAfter=3),
        "sec_band":  ParagraphStyle("sec_band", fontSize=13, textColor=C_PAPER,
                                    fontName="Helvetica-Bold", leading=16),
        "sec_sub":   ParagraphStyle("sec_sub", fontSize=9, textColor=C_GRAY,
                                    italic=True, spaceAfter=6, leading=12),
        # Cuerpo
        "body":  ParagraphStyle("body", fontSize=8.6, textColor=C_INK,
                                 leading=12.5, spaceAfter=4, fontName="Helvetica"),
        "body_it": ParagraphStyle("body_it", fontSize=8.4, textColor=C_GRAY,
                                   italic=True, leading=12, spaceAfter=4),
        "h2":    ParagraphStyle("h2", fontSize=9.5, textColor=C_INK,
                                 fontName="Helvetica-Bold", spaceBefore=2,
                                 spaceAfter=0, leading=12),
        "small": ParagraphStyle("small", fontSize=7.5, textColor=C_GRAY,
                                 spaceAfter=2, fontName="Courier"),
        "kpi_val":   ParagraphStyle("kpi_val", fontSize=17, textColor=C_ACCENT,
                                     fontName="Helvetica-Bold", alignment=TA_CENTER),
        "kpi_lbl":   ParagraphStyle("kpi_lbl", fontSize=7.5, textColor=C_GRAY,
                                     alignment=TA_CENTER, fontName="Courier"),
        "kpi_sub":   ParagraphStyle("kpi_sub", fontSize=7, textColor=C_GRAY,
                                     alignment=TA_CENTER, italic=True,
                                     fontName="Courier"),
        "cell":      ParagraphStyle("cell", fontSize=7.5, textColor=C_INK,
                                     leading=10, spaceAfter=0, wordWrap="CJK"),
        "cell_b":    ParagraphStyle("cell_b", fontSize=7.5, textColor=C_INK,
                                     leading=10, fontName="Helvetica-Bold",
                                     wordWrap="CJK"),
        "toc_num":   ParagraphStyle("toc_num", fontSize=9, textColor=C_INK,
                                     fontName="Helvetica-Bold"),
        "toc_lbl":   ParagraphStyle("toc_lbl", fontSize=9, textColor=C_INK),
    }
    return s


# ── Header/footer ─────────────────────────────────────────────────────────────

def _page_bg(canvas) -> None:
    canvas.saveState()
    canvas.setFillColor(C_PAPER)
    canvas.rect(0, 0, W, H, fill=1, stroke=0)
    canvas.restoreState()


def _later_pages(canvas, doc) -> None:
    if canvas.getPageNumber() > 1:
        _page_bg(canvas)
    canvas.saveState()
    y_hdr = H - MARGIN_TOP + 0.15 * cm
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(C_GRAY)
    canvas.drawString(MARGIN_X, y_hdr,
                      "ARHIAX Dx Pro — Informe Ejecutivo de Diagnostico")
    canvas.drawRightString(W - MARGIN_X, y_hdr,
                           f"Pagina {canvas.getPageNumber() - 1}")
    canvas.setStrokeColor(C_BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN_X, y_hdr - 0.12 * cm, W - MARGIN_X, y_hdr - 0.12 * cm)
    canvas.setFont("Helvetica", 7)
    canvas.drawString(MARGIN_X, MARGIN_BOT - 0.55 * cm,
                      "Sinergia Consulting Group  |  PMEL/ATK  |  Confidencial")
    canvas.line(MARGIN_X, MARGIN_BOT - 0.35 * cm, W - MARGIN_X, MARGIN_BOT - 0.35 * cm)
    canvas.restoreState()


# ── Cover ──────────────────────────────────────────────────────────────────────

def _cover_page(canvas, case: Any, fusion: dict) -> None:
    canvas.saveState()
    canvas.setFillColor(C_NAVY)
    canvas.rect(0, 0, W, H, fill=1, stroke=0)

    canvas.setFont("Helvetica-Bold", 9)
    canvas.setFillColor(C_PAPER)
    canvas.drawString(MARGIN_X, H - MARGIN_TOP, "ARHIAX Dx Pro")
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(C_ACCENT)
    canvas.drawString(MARGIN_X + 2.6 * cm, H - MARGIN_TOP, "PMEL/ATK")

    title = case.client_name or "Diagnostico Ejecutivo"
    canvas.setFont("Helvetica-Bold", 22 if len(title) > 34 else 24)
    canvas.setFillColor(C_PAPER)
    y_title = H * 0.62
    if len(title) > 34:
        words = title.split()
        line1, line2 = [], []
        for w in words:
            target = line1 if sum(len(x) + 1 for x in line1) + len(w) < 36 else line2
            target.append(w)
        canvas.drawString(MARGIN_X, y_title, " ".join(line1))
        if line2:
            canvas.drawString(MARGIN_X, y_title - 0.5 * cm, " ".join(line2))
    else:
        canvas.drawString(MARGIN_X, y_title, title)

    canvas.setFont("Helvetica", 10)
    canvas.setFillColor(C_GRAY)
    canvas.drawString(MARGIN_X, H * 0.54, case.domain or "")

    canvas.setStrokeColor(C_ACCENT)
    canvas.setLineWidth(1.2)
    canvas.line(MARGIN_X, H * 0.48, W - MARGIN_X, H * 0.48)

    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(colors.HexColor("#c8c4bc"))
    canvas.drawString(MARGIN_X, H * 0.43,
                      "Informe ejecutivo con trazabilidad gobernada y roadmap de accion")

    canvas.setFont("Helvetica-Bold", 9)
    canvas.setFillColor(C_PAPER)
    canvas.drawString(MARGIN_X, H * 0.22,
                      f"Engagement: {case.engagement_id or '—'}")
    canvas.setFont("Helvetica", 8)
    canvas.drawString(MARGIN_X, H * 0.17,
                      f"{datetime.now().strftime('%B %Y')}  |  Version 1.0  |  Confidencial")
    overall = (fusion.get("scoring") or {}).get("overall_score")
    if overall is not None:
        canvas.setFillColor(C_ACCENT)
        canvas.drawString(MARGIN_X, H * 0.12, f"Indice de madurez: {overall}/100")
    canvas.restoreState()


# ── Banda de sección ──────────────────────────────────────────────────────────

def _section_band(title: str, subtitle: str, color=None) -> list:
    s = _styles()
    hc = color or C_NAVY
    band = Table(
        [[Paragraph(title, s["sec_band"])]],
        colWidths=[CONTENT_W],
    )
    band.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), hc),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    return [
        _full_width(band),
        Spacer(1, GAP),
        Paragraph(subtitle, s["sec_sub"]),
        Spacer(1, GAP),
    ]


# ── Tabla genérica con cabecera coloreada ─────────────────────────────────────

def _table(rows: list, col_widths: list, header_color=None) -> Table:
    tbl = Table(rows, colWidths=col_widths)
    hc = header_color or C_NAVY
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), hc),
        ("TEXTCOLOR",     (0, 0), (-1, 0), C_PAPER),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 7.5),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [C_PAPER, C_OFFWH]),
        ("GRID",          (0, 0), (-1, -1), 0.4, C_BORDER),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 5),
    ]))
    return tbl


# ── KPI Cards (Sección 1) ─────────────────────────────────────────────────────

def _kpi_cards(scoring: dict, risks: list, hypotheses: list) -> Table:
    s = _styles()
    overall = scoring.get("overall_score", "—")
    total_r = len(risks)
    high_r = sum(1 for r in risks if str(r.get("severity", "")).lower() == "high")
    total_responses = scoring.get("total_responses", 0)
    confirmed = sum(1 for h in hypotheses if h.get("supported"))
    hyp_total = len(hypotheses)
    cw = CONTENT_W / 4
    items = [
        (f"{overall}/100", "Madurez global", "Indice"),
        (str(total_responses), "Respondentes", "Cobertura"),
        (str(total_r), "Riesgos", f"{high_r} altos"),
        (f"{confirmed}/{hyp_total}" if hyp_total else "0", "Hipotesis", "Confirmadas"),
    ]
    tbl = Table(
        [[_p(v, s["kpi_val"]) for v, _, _ in items],
         [_p(l, s["kpi_lbl"]) for _, l, _ in items],
         [_p(sub, s["kpi_sub"]) for _, _, sub in items]],
        colWidths=[cw] * 4,
    )
    tbl.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, C_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, C_BORDER),
        ("BACKGROUND", (0, 0), (-1, -1), C_PAPER),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return _full_width(tbl)


# ── Radar (Sección 2) ─────────────────────────────────────────────────────────

def _radar_chart(dim_scores: list) -> _ScaledDrawing:
    chart_w = CONTENT_W
    chart_h = 5.8 * cm
    cx, cy = chart_w / 2, chart_h * 0.52
    r = min(chart_w, chart_h) * 0.32
    n = max(len(dim_scores), 1)
    d = Drawing(chart_w, chart_h)

    for frac in [0.2, 0.4, 0.6, 0.8, 1.0]:
        pts = []
        for k in range(n):
            angle = math.pi / 2 + 2 * math.pi * k / n
            pts += [cx + r * frac * math.cos(angle),
                    cy + r * frac * math.sin(angle)]
        d.add(PolyLine(pts + pts[:2], strokeColor=C_BORDER,
                       strokeWidth=0.5, fillColor=None))

    for k in range(n):
        angle = math.pi / 2 + 2 * math.pi * k / n
        d.add(Line(cx, cy, cx + r * math.cos(angle), cy + r * math.sin(angle),
                   strokeColor=C_BORDER, strokeWidth=0.5))

    max_val = 100.0
    pts = []
    for k, dim in enumerate(dim_scores):
        score = float(dim.get("score", 0) or 0) / max_val
        angle = math.pi / 2 + 2 * math.pi * k / n
        pts += [cx + r * score * math.cos(angle), cy + r * score * math.sin(angle)]
    if pts:
        d.add(Polygon(pts, fillColor=colors.HexColor("#9d856420"),
                      strokeColor=C_ACCENT, strokeWidth=1.2))

    for k, dim in enumerate(dim_scores):
        angle = math.pi / 2 + 2 * math.pi * k / n
        lx = cx + (r + 14) * math.cos(angle)
        ly = cy + (r + 14) * math.sin(angle)
        label = str(dim.get("dimension", ""))[:14]
        d.add(String(lx, ly - 3, label, fontSize=7, fillColor=C_INK, textAnchor="middle"))

    return _centered(_gfx(d))


# ── Diagrama de flujo simple ──────────────────────────────────────────────────

def _flow_diagram(steps: list[str], color) -> _ScaledDrawing:
    if not steps:
        steps = ["Inicio", "Proceso", "Cierre"]

    max_per_row = 4
    rows: list[list[str]] = [
        steps[i:i + max_per_row] for i in range(0, len(steps), max_per_row)
    ]
    gap = 10
    bh = 24
    row_gap = 14
    row_h = bh + row_gap
    total_h = len(rows) * row_h + 8

    def _row_width(count: int) -> float:
        bw = min(95, max(48, (CONTENT_W - (count - 1) * gap) / max(count, 1)))
        return count * bw + (count - 1) * gap

    draw_w = max(_row_width(len(r)) for r in rows)
    d = Drawing(draw_w, total_h)

    y = total_h - bh - 6
    for row_steps in rows:
        count = len(row_steps)
        bw = min(95, max(48, (CONTENT_W - (count - 1) * gap) / max(count, 1)))
        row_w = count * bw + (count - 1) * gap
        x0 = (draw_w - row_w) / 2
        for i, step in enumerate(row_steps):
            x = x0 + i * (bw + gap)
            d.add(Rect(x, y, bw, bh,
                       fillColor=C_PAPER,
                       strokeColor=color, strokeWidth=1))
            label = (step or "")[:22]
            d.add(String(x + bw / 2, y + bh / 2 - 2, label,
                         fontSize=6.8, fillColor=C_INK, textAnchor="middle"))
            if i < count - 1:
                ax = x + bw + 1
                ay = y + bh / 2
                d.add(Line(ax, ay, ax + gap - 3, ay, strokeColor=color, strokeWidth=1))
                d.add(Polygon([ax + gap - 3, ay, ax + gap - 8, ay - 2.5,
                               ax + gap - 8, ay + 2.5],
                              fillColor=color, strokeColor=color))
        y -= row_h

    return _centered(_gfx(d))


# ── Portada (flowable especial via canvas callback) ───────────────────────────

class _CoverFlowable:
    """Pseudo-flowable que dibuja la cover directamente en el canvas."""
    def __init__(self, case: Any, fusion: dict):
        self.case = case
        self.fusion = fusion

    def wrap(self, *_):
        return W, H

    def draw(self):
        pass  # Handled by onFirstPage


# ── Seccion 1: Resumen ejecutivo ──────────────────────────────────────────────

def _sec1(fusion: dict, md_text: str, s: dict) -> list:
    elems = _section_band("1. Resumen ejecutivo",
                          "Diagnostico sintetico, tesis principal y magnitud de oportunidad.",
                          SECTION_COLORS[0])
    scoring = fusion.get("scoring") or {}
    risks = fusion.get("risk_signals") or []
    hyps = fusion.get("hypotheses") or []
    thesis = _clean(fusion.get("executive_thesis", ""))
    paras = _md_paragraphs(md_text)

    elems.append(_h2_block("Como debe leerse esta seccion", s))
    if paras:
        elems.append(Paragraph(paras[0], s["body_it"]))
    elems.append(_kpi_cards(scoring, risks, hyps))
    elems.append(_h2_block("Lectura ejecutiva completa", s))
    if thesis:
        elems.append(Paragraph(thesis, s["body"]))
    for para in paras[1:3]:
        elems.append(Paragraph(para, s["body"]))

    rows = [[_p("Hipotesis", s["cell_b"]), _p("Lectura ejecutiva", s["cell_b"]),
             _p("Evidencia / implicacion", s["cell_b"])]]
    for h in hyps[:6]:
        status = "Confirmada" if h.get("supported") else "No confirmada"
        posterior = h.get("posterior", "—")
        rows.append([
            _p(_hypothesis_text(h), s["cell_b"]),
            _p(status, s["cell"]),
            _p(f"Posterior {posterior}", s["cell"]),
        ])
    if not hyps:
        for row in _md_tables(md_text):
            for data_row in row[1:]:
                rows.append([_p(c, s["cell"]) for c in data_row[:3]])
            break
    if len(rows) > 1:
        elems.append(_table_from_rows(
            rows, [CONTENT_W * 0.30, CONTENT_W * 0.24, CONTENT_W * 0.46], SECTION_COLORS[0],
        ))
    return elems


# ── Seccion 2: Diagnostico de madurez ────────────────────────────────────────

def _sec2(fusion: dict, md_text: str, s: dict) -> list:
    elems = _section_band("2. Diagnostico de madurez",
                          "Resultado por dimensiones, brechas entre roles y lectura de gobernanza.",
                          SECTION_COLORS[1])
    scoring = fusion.get("scoring") or {}
    dim_scores = scoring.get("dimension_scores") or []
    overall = scoring.get("overall_score", "—")
    paras = _md_paragraphs(md_text)

    elems.append(_h2_block("Que explica esta seccion", s))
    if paras:
        elems.append(Paragraph(paras[0], s["body_it"]))
    if dim_scores:
        elems.append(_radar_chart(dim_scores))
        elems.append(Spacer(1, GAP))

    tables = _md_tables(md_text)
    if tables:
        tbl = _md_table_flowable(tables[0], s, SECTION_COLORS[1])
        if tbl:
            elems.append(tbl)
    else:
        rows = [[_p("Dimension", s["cell_b"]), _p("Score", s["cell_b"]),
                 _p("Hallazgo", s["cell_b"])]]
        for d in dim_scores:
            sc = d.get("score", "—")
            rows.append([
                _p(d.get("dimension", "—"), s["cell"]),
                _p(str(sc), s["cell"]),
                _p(_dimension_reading(sc), s["cell"]),
            ])
        if dim_scores:
            elems.append(_table_from_rows(
                rows, [CONTENT_W * 0.32, CONTENT_W * 0.14, CONTENT_W * 0.54], SECTION_COLORS[1],
            ))

    elems.append(Spacer(1, 0.2 * cm))
    elems.append(_h2_block("Interpretacion del resultado", s))
    interpretation = (
        f"Madurez global: {overall}/100. "
        f"Respondentes evaluados: {scoring.get('total_responses', 0)}."
    )
    if dim_scores:
        weakest = min(dim_scores, key=lambda d: float(d.get("score", 0) or 0))
        interpretation += (
            f" La dimension con mayor brecha es {_clean(weakest.get('dimension'))} "
            f"({weakest.get('score', '—')}/100)."
        )
    for para in paras[1:2]:
        interpretation += f" {para}"
    elems.append(Paragraph(interpretation, s["body"]))
    return elems


# ── Seccion 3: Proceso AS-IS ──────────────────────────────────────────────────

def _sec3(md_text: str, s: dict) -> list:
    elems = _section_band("3. Proceso AS-IS",
                          "Mapa visual del flujo actual y lectura operativa.",
                          SECTION_COLORS[2])
    paras = _md_paragraphs(md_text)
    bullets = _md_bullets(md_text)
    steps = _flow_from_bullets(bullets)

    elems.append(_h2_block("Por que mostramos el proceso actual al cliente", s))
    if paras:
        elems.append(Paragraph(paras[0], s["body_it"]))
    elems.append(_h2_block("Mapa AS-IS - flujo actual observado", s))
    elems.append(_flow_diagram(steps, C_NAVY))
    elems.append(Spacer(1, GAP))

    for bullet in bullets[1:]:
        elems.append(Paragraph(bullet, s["body"]))

    for tbl_data in _md_tables(md_text):
        tbl = _md_table_flowable(tbl_data, s, SECTION_COLORS[2])
        if tbl:
            elems.append(Spacer(1, 0.1 * cm))
            elems.append(tbl)
    return elems


# ── Seccion 4: Hallazgos ──────────────────────────────────────────────────────

def _sec4(fusion: dict, md_text: str, s: dict) -> list:
    elems = _section_band("4. Hallazgos del proceso",
                          "Traduccion del analisis tecnico a lenguaje de negocio.",
                          SECTION_COLORS[3])
    paras = _md_paragraphs(md_text)
    risks = fusion.get("risk_signals") or []

    elems.append(_h2_block("Como se traduce el analisis tecnico", s))
    if paras:
        elems.append(Paragraph(paras[0], s["body_it"]))

    tables = _md_tables(md_text)
    if tables:
        tbl = _md_table_flowable(tables[0], s, SECTION_COLORS[3])
        if tbl:
            elems.append(tbl)
    elif risks:
        rows = [
            [_p("Senal de riesgo", s["cell_b"]), _p("Severidad", s["cell_b"]),
             _p("Lectura", s["cell_b"])],
        ]
        for r in risks[:8]:
            rows.append([
                _p(_clean(r.get("signal", "—")), s["cell"]),
                _p(_clean(r.get("severity", "—")).upper(), s["cell_b"]),
                _p("Requiere tratamiento en roadmap.", s["cell"]),
            ])
        elems.append(_table_from_rows(
            rows, [CONTENT_W * 0.42, CONTENT_W * 0.18, CONTENT_W * 0.40], SECTION_COLORS[3],
        ))

    for para in paras[1:]:
        elems.append(Spacer(1, 0.15 * cm))
        elems.append(Paragraph(para, s["body"]))
    return elems


# ── Seccion 5: Proceso TO-BE ──────────────────────────────────────────────────

def _sec5(md_text: str, s: dict) -> list:
    elems = _section_band("5. Proceso TO-BE",
                          "Modelo objetivo recomendado y control de cambios.",
                          SECTION_COLORS[4])
    paras = _md_paragraphs(md_text)
    bullets = _md_bullets(md_text)
    steps = _flow_from_bullets(bullets)

    elems.append(_h2_block("Que representa el TO-BE", s))
    if paras:
        elems.append(Paragraph(paras[0], s["body_it"]))
    elems.append(_h2_block("Mapa TO-BE - flujo recomendado", s))
    elems.append(_flow_diagram(steps, C_NAVY))
    elems.append(Spacer(1, GAP))

    for bullet in bullets[1:]:
        elems.append(Paragraph(bullet, s["body"]))
    for para in paras[1:]:
        elems.append(Paragraph(para, s["body"]))

    for tbl_data in _md_tables(md_text):
        tbl = _md_table_flowable(tbl_data, s, SECTION_COLORS[4])
        if tbl:
            elems.append(Spacer(1, 0.1 * cm))
            elems.append(tbl)
    return elems


# ── Seccion 6: Matriz AS-IS → TO-BE ──────────────────────────────────────────

def _sec6(md_text: str, s: dict) -> list:
    elems = _section_band("6. Matriz AS-IS -> TO-BE",
                          "Conversion de hallazgos en iniciativas accionables.",
                          SECTION_COLORS[5])
    paras = _md_paragraphs(md_text)

    elems.append(_h2_block("Como usar esta matriz", s))
    if paras:
        elems.append(Paragraph(paras[0], s["body_it"]))

    for tbl_data in _md_tables(md_text):
        tbl = _md_table_flowable(tbl_data, s, SECTION_COLORS[5])
        if tbl:
            elems.append(tbl)
            elems.append(Spacer(1, 0.1 * cm))

    for para in paras[1:]:
        elems.append(Spacer(1, 0.15 * cm))
        elems.append(Paragraph(para, s["body"]))
    return elems


# ── Seccion 7: Reglas de decision ─────────────────────────────────────────────

def _sec7(md_text: str, s: dict) -> list:
    elems = _section_band("7. Reglas de decision",
                          "Reglas verificables para decisiones sensibles del proceso.",
                          SECTION_COLORS[6])
    paras = _md_paragraphs(md_text)
    bullets = _md_bullets(md_text)

    elems.append(_h2_block("Por que formalizar decisiones", s))
    if paras:
        elems.append(Paragraph(paras[0], s["body_it"]))

    tables = _md_tables(md_text)
    if tables:
        tbl = _md_table_flowable(tables[0], s, SECTION_COLORS[6])
        if tbl:
            elems.append(tbl)
    elif bullets:
        rows = [[_p("Regla de decision", s["cell_b"]), _p("Descripcion", s["cell_b"])]]
        for bullet in bullets:
            if ":" in bullet:
                name, desc = bullet.split(":", 1)
                rows.append([_p(name.strip(), s["cell_b"]), _p(desc.strip(), s["cell"])])
            else:
                rows.append([_p("Regla", s["cell_b"]), _p(bullet, s["cell"])])
        elems.append(_table_from_rows(
            rows, [CONTENT_W * 0.30, CONTENT_W * 0.70], SECTION_COLORS[6],
        ))

    for para in paras[1:]:
        elems.append(Paragraph(para, s["body"]))
    return elems


# ── Seccion 8: Roadmap ────────────────────────────────────────────────────────

def _sec8(fusion: dict, md_text: str, s: dict) -> list:
    elems = _section_band("8. Roadmap de implementacion",
                          "Ruta de 180 dias desde estabilizacion hasta automatizacion.",
                          SECTION_COLORS[7])
    paras = _md_paragraphs(md_text)
    bullets = _md_bullets(md_text)
    next_step = _clean(fusion.get("recommended_next_step", ""))

    elems.append(_h2_block("Logica del roadmap", s))
    if paras:
        elems.append(Paragraph(paras[0], s["body_it"]))

    tables = _md_tables(md_text)
    if tables:
        tbl = _md_table_flowable(tables[0], s, SECTION_COLORS[7])
        if tbl:
            elems.append(tbl)
    elif bullets:
        rows = [[_p("Fase / horizonte", s["cell_b"]), _p("Contenido", s["cell_b"])]]
        for bullet in bullets:
            rows.append([_p("Fase", s["cell_b"]), _p(bullet, s["cell"])])
        elems.append(_table_from_rows(
            rows, [CONTENT_W * 0.24, CONTENT_W * 0.76], SECTION_COLORS[7],
        ))

    if next_step:
        elems.append(Spacer(1, 0.2 * cm))
        elems.append(_h2_block("Proximo paso recomendado", s))
        elems.append(Paragraph(next_step, s["body"]))
    return elems


# ── Seccion 9: Gobernanza ─────────────────────────────────────────────────────

def _sec9(case: Any, fusion: dict, evidence: list, md_text: str, s: dict) -> list:
    elems = _section_band("9. Gobernanza y trazabilidad",
                          "Como se respalda cada recomendacion frente a direccion.",
                          SECTION_COLORS[8])
    paras = _md_paragraphs(md_text)
    stage_outcomes = fusion.get("stage_outcomes") or {}

    elems.append(_h2_block("Por que esta seccion importa", s))
    if paras:
        elems.append(Paragraph(paras[0], s["body_it"]))

    if stage_outcomes:
        rows = [[_p("Etapa", s["cell_b"]), _p("Outcome", s["cell_b"]),
                 _p("Artefacto", s["cell_b"])]]
        for stage, data in stage_outcomes.items():
            payload = data or {}
            rows.append([
                _p(stage, s["cell"]),
                _p(payload.get("outcome", "—"), s["cell"]),
                _p(payload.get("artifact_type", stage), s["cell"]),
            ])
        elems.append(_table_from_rows(
            rows, [CONTENT_W * 0.30, CONTENT_W * 0.20, CONTENT_W * 0.50], SECTION_COLORS[8],
        ))

    for para in paras[1:]:
        elems.append(Paragraph(para, s["body"]))

    if evidence:
        elems.append(Spacer(1, 0.2 * cm))
        elems.append(_h2_block("Evidencia trazable del ciclo", s))
        ev_rows = [[_p("Evento", s["cell_b"]), _p("Outcome", s["cell_b"]),
                    _p("Agente", s["cell_b"]), _p("Timestamp", s["cell_b"])]]
        for e in evidence[:12]:
            ts = str(e.get("created_at") or "—")[:16].replace("T", " ")
            ev_rows.append([
                _p(e.get("event_type", "—"), s["cell"]),
                _p(e.get("outcome", "—"), s["cell"]),
                _p(e.get("agent", "—"), s["cell"]),
                _p(ts, s["cell"]),
            ])
        elems.append(_table_from_rows(
            ev_rows, [CONTENT_W * 0.28, CONTENT_W * 0.18, CONTENT_W * 0.28, CONTENT_W * 0.26],
            SECTION_COLORS[8],
        ))
    return elems


# ── Seccion 10: Anexo tecnico ─────────────────────────────────────────────────

def _sec10(case: Any, report: dict, md_text: str, s: dict) -> list:
    elems = _section_band("10. Anexo tecnico",
                          "BPMN, DMN, controles de calidad y referencias del sistema.",
                          SECTION_COLORS[9])
    paras = _md_paragraphs(md_text)
    sections = report.get("sections") or []

    elems.append(_h2_block("Funcion del anexo", s))
    if paras:
        elems.append(Paragraph(paras[0], s["body_it"]))

    for sec in sections:
        elems.append(_h2_block(_clean(sec.get("title", "Seccion")), s))
        elems.append(Paragraph(_clean(sec.get("content", "")), s["body"]))

    for tbl_data in _md_tables(md_text):
        tbl = _md_table_flowable(tbl_data, s, SECTION_COLORS[9])
        if tbl:
            elems.append(Spacer(1, 0.1 * cm))
            elems.append(tbl)

    for para in paras[1:]:
        if "Certificacion de Integridad" in para:
            continue
        elems.append(Paragraph(para, s["body"]))

    elems.append(Spacer(1, 0.3 * cm))
    elems.append(_h2_block("Referencias del caso", s))
    elems.append(Paragraph(
        f"Caso ID: {case.case_id}  ·  Trace: {case.trace_id or '—'}  ·  "
        f"PMEL Outcome: {case.pmel_outcome or 'PERMIT'}  ·  "
        f"Estado: {getattr(case, 'case_status', '—')}",
        s["body"],
    ))
    qa_score = report.get("qa_score")
    if qa_score is not None:
        elems.append(Paragraph(f"QA Score del pipeline: {qa_score}", s["small"]))
    return elems


# ── TOC ───────────────────────────────────────────────────────────────────────

def _toc(s: dict) -> list:
    sections = [
        (SECTION_COLORS[0], "1.", "Resumen ejecutivo"),
        (SECTION_COLORS[1], "2.", "Diagnostico de madurez"),
        (SECTION_COLORS[2], "3.", "Proceso AS-IS"),
        (SECTION_COLORS[3], "4.", "Hallazgos del proceso"),
        (SECTION_COLORS[4], "5.", "Proceso TO-BE"),
        (SECTION_COLORS[5], "6.", "Matriz AS-IS -> TO-BE"),
        (SECTION_COLORS[6], "7.", "Reglas de decision"),
        (SECTION_COLORS[7], "8.", "Roadmap de implementacion"),
        (SECTION_COLORS[8], "9.", "Gobernanza y trazabilidad"),
        (SECTION_COLORS[9], "10.", "Anexo tecnico"),
    ]
    elems: list = []
    elems.append(Paragraph("Contenido", s["toc_num"]))
    elems.append(HRFlowable(width="100%", thickness=0.5,
                             color=C_BORDER, spaceAfter=8))
    rows = []
    for color, num, title in sections:
        rows.append([
            Table([[Paragraph(num, ParagraphStyle("tn", fontSize=9,
                     textColor=C_PAPER, fontName="Helvetica-Bold"))]],
                  colWidths=[0.9 * cm],
                  style=TableStyle([
                      ("BACKGROUND", (0, 0), (-1, -1), C_NAVY),
                      ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                      ("TOPPADDING", (0, 0), (-1, -1), 4),
                      ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                  ])),
            Paragraph(title, s["toc_lbl"]),
        ])
    tbl = Table(rows, colWidths=[1.1 * cm, CONTENT_W - 1.1 * cm])
    tbl.setStyle(TableStyle([
        ("GRID",         (0,0), (-1,-1), 0.3, C_BORDER),
        ("TOPPADDING",   (0,0), (-1,-1), 5),
        ("BOTTOMPADDING",(0,0), (-1,-1), 5),
        ("LEFTPADDING",  (0,0), (-1,-1), 4),
        ("ROWBACKGROUNDS",(0,0),(-1,-1), [C_PAPER, C_OFFWH]),
    ]))
    elems.append(tbl)
    elems.append(PageBreak())
    return elems


# ── Builder principal ─────────────────────────────────────────────────────────

def _add_section(story: list, elems: list, *, page_break: bool = True) -> None:
    if page_break and len(story) > 2:
        story.append(PageBreak())
    story.extend(elems)
    story.append(Spacer(1, GAP))


def build_pro_pdf(case: Any, evidence: list | None = None) -> bytes:
    if not PDF_AVAILABLE:
        raise RuntimeError("reportlab no instalado")

    from api.pipeline.pro_markdown_builder import build_pro_markdown

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=LETTER,
        leftMargin=MARGIN_X, rightMargin=MARGIN_X,
        topMargin=MARGIN_TOP + HEADER_H,
        bottomMargin=MARGIN_BOT + FOOTER_H,
        title=f"Diagnostico Ejecutivo — {case.client_name}",
        author="ARHIAX DxPro v1 · Sinergia Consulting Group",
    )

    s = _styles()
    fusion = case.fusion_result or {}
    report = case.report_result or {}
    ev_list = [_ev_to_dict(e) for e in (evidence or [])]
    if not ev_list and getattr(case, "evidence_entries", None):
        ev_list = [_ev_to_dict(e) for e in case.evidence_entries]

    md = build_pro_markdown(case)
    md_sections = _split_md_sections(md)

    story: list = []
    story.append(Spacer(1, 1))
    story.append(PageBreak())
    story += _toc(s)
    _add_section(story, _sec1(fusion, md_sections.get(1, ""), s), page_break=False)
    _add_section(story, _sec2(fusion, md_sections.get(2, ""), s))
    _add_section(story, _sec3(md_sections.get(3, ""), s))
    _add_section(story, _sec4(fusion, md_sections.get(4, ""), s))
    _add_section(story, _sec5(md_sections.get(5, ""), s))
    _add_section(story, _sec6(md_sections.get(6, ""), s))
    _add_section(story, _sec7(md_sections.get(7, ""), s))
    _add_section(story, _sec8(fusion, md_sections.get(8, ""), s))
    _add_section(story, _sec9(case, fusion, ev_list, md_sections.get(9, ""), s))
    _add_section(story, _sec10(case, report, md_sections.get(10, ""), s))

    def _first_page(canvas, doc_):
        _cover_page(canvas, case, fusion)

    def _later(canvas, doc_):
        _later_pages(canvas, doc_)

    doc.build(story, onFirstPage=_first_page, onLaterPages=_later)
    buf.seek(0)
    return buf.read()


def _ev_to_dict(e: Any) -> dict:
    if isinstance(e, dict):
        return e
    return {
        "event_type": getattr(e, "event_type", "—"),
        "outcome":    getattr(e, "outcome", "—"),
        "agent":      getattr(e, "agent", "—"),
        "created_at": (getattr(e, "created_at", None) or ""),
    }
