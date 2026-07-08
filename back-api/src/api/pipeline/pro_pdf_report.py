"""
Informe Pro ejecutivo — páginas densas, orientación por sección, datos del pipeline.
"""
from __future__ import annotations

import io
import re
import xml.sax.saxutils as _xml
from datetime import datetime
from typing import Any

from api.pipeline.pro_report_data import build_pro_report_data, validate_report_for_deliverables
from api.pipeline.pro_pdf_charts import (
    bottleneck_chart,
    delta_sigma_bars,
    dimension_radar,
    role_bar_chart,
    triangulation_flow,
)

try:
    from reportlab.lib import colors as _rl_colors
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, Flowable, KeepTogether,
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
    from reportlab.graphics.shapes import Drawing
    from reportlab.graphics import renderPDF
    PDF_OK = True
    colors = _rl_colors
    W, H = LETTER
    C_INK = colors.HexColor("#1a1a1a")
    C_GRAY = colors.HexColor("#5c5a54")
    C_PAPER = colors.HexColor("#faf7f2")
    C_ACCENT = colors.HexColor("#8b7355")
    C_NAVY = colors.HexColor("#1e3a4f")
    C_NAVY_LT = colors.HexColor("#2d5270")
    C_RED = colors.HexColor("#9b2c2c")
    C_GREEN = colors.HexColor("#276749")
    C_AMBER = colors.HexColor("#b7791f")
    C_WHITE = colors.white
    C_OFFWH = colors.HexColor("#f0ebe3")
    C_GUIDE = colors.HexColor("#e8eef3")
    C_BORDER = colors.HexColor("#d4cdc2")
    MX = 1.15 * cm
    MY_T = 1.55 * cm
    MY_B = 1.05 * cm
    CW = W - 2 * MX
    GAP = 0.22 * cm
except ImportError:
    PDF_OK = False


def _safe(v: Any, fb: str = "—") -> str:
    if v is None:
        return fb
    t = str(v).strip()
    return t if t else fb


def _cols_fracs(*fracs: float) -> list[float]:
    """Anchos que suman exactamente CW."""
    total = sum(fracs) or 1.0
    return [CW * f / total for f in fracs]


def _cols_fixed_flex(fixed_cm: list[float], flex_fracs: list[float]) -> list[float]:
    """Columnas fijas (cm) al INICIO + fracciones del espacio restante al FINAL."""
    fixed_sum = sum(fixed_cm)
    rem = max(CW - fixed_sum, CW * 0.5)
    ftotal = sum(flex_fracs) or 1.0
    return list(fixed_cm) + [rem * f / ftotal for f in flex_fracs]


def _cols_equal(n: int) -> list[float]:
    return [CW / n] * n


def _esc_html(text: str) -> str:
    """Escapa XML y conserva etiquetas simples b/i/br."""
    text = _safe(text)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</?(b|i)>", "", text, flags=re.I)
    return _xml.escape(text).replace("\n", "<br/>")


class _ScaledDrawing(Flowable):
    def __init__(self, drawing: Drawing, max_w: float):
        self._d = drawing
        self._mw = max_w
        self.width = drawing.width
        self.height = drawing.height

    def wrap(self, aw, ah):
        sc = min(1.0, self._mw / max(self._d.width, 1))
        self.width = self._d.width * sc
        self.height = self._d.height * sc
        self._sc = sc
        return self.width, self.height

    def draw(self):
        self.canv.saveState()
        self.canv.scale(self._sc, self._sc)
        renderPDF.draw(self._d, self.canv, 0, 0)
        self.canv.restoreState()


def _gfx(d: Drawing) -> _ScaledDrawing:
    return _ScaledDrawing(d, CW)


def _styles() -> dict:
    return {
        "h1": ParagraphStyle("h1", fontSize=13, textColor=C_NAVY, fontName="Helvetica-Bold",
                              spaceAfter=4, leading=16),
        "h2": ParagraphStyle("h2", fontSize=11.5, textColor=C_NAVY, fontName="Helvetica-Bold",
                              spaceBefore=12, spaceAfter=6, leading=14),
        "h3": ParagraphStyle("h3", fontSize=9.5, textColor=C_ACCENT, fontName="Helvetica-Bold",
                              spaceBefore=3, spaceAfter=3, leading=12),
        "body": ParagraphStyle("body", fontSize=10, textColor=C_INK, leading=13,
                               spaceAfter=3, alignment=TA_JUSTIFY),
        "body_b": ParagraphStyle("body_b", fontSize=10, textColor=C_INK, leading=13,
                                  fontName="Helvetica-Bold", spaceAfter=3),
        "small": ParagraphStyle("small", fontSize=9, textColor=C_GRAY, leading=12,
                                wordWrap="LTR", splitLongWords=True),
        "guide": ParagraphStyle("guide", fontSize=9, textColor=C_NAVY_LT, leading=12,
                                alignment=TA_JUSTIFY, spaceBefore=4, spaceAfter=6),
        "cell": ParagraphStyle(
            "cell", fontSize=9, textColor=C_INK, leading=12,
            wordWrap="LTR", splitLongWords=True,
        ),
        "cell_b": ParagraphStyle(
            "cell_b", fontSize=9, textColor=C_INK, leading=12,
            fontName="Helvetica-Bold", wordWrap="LTR",
        ),
        "cell_hdr": ParagraphStyle(
            "cell_hdr", fontSize=9, textColor=C_PAPER, leading=12,
            fontName="Helvetica-Bold", wordWrap="LTR",
        ),
        "band": ParagraphStyle("band", fontSize=11, textColor=C_PAPER, fontName="Helvetica-Bold"),
        "band_sub": ParagraphStyle("band_sub", fontSize=8, textColor=C_OFFWH),
        "kpi_v": ParagraphStyle("kpi_v", fontSize=13, textColor=C_ACCENT, fontName="Helvetica-Bold",
                                 alignment=TA_CENTER, leading=16),
        "kpi_l": ParagraphStyle("kpi_l", fontSize=8.5, textColor=C_GRAY, alignment=TA_CENTER,
                                 leading=11, wordWrap="LTR", splitLongWords=True),
        "toc": ParagraphStyle("toc", fontSize=9, textColor=C_INK, leading=13, leftIndent=8),
        "toc_sec": ParagraphStyle("toc_sec", fontSize=9, textColor=C_NAVY, fontName="Helvetica-Bold",
                                   leading=13),
        "part_lbl": ParagraphStyle("part_lbl", fontSize=9, textColor=C_ACCENT, fontName="Helvetica-Bold",
                                    leading=11),
        "part_t": ParagraphStyle("part_t", fontSize=14, textColor=C_PAPER, fontName="Helvetica-Bold",
                                  leading=17),
        "part_sub": ParagraphStyle("part_sub", fontSize=8.5, textColor=C_OFFWH, leading=11),
        "sec_num": ParagraphStyle("sec_num", fontSize=10, textColor=C_PAPER, fontName="Helvetica-Bold",
                                   alignment=TA_CENTER, leading=12),
        "sec_title": ParagraphStyle("sec_title", fontSize=12.5, textColor=C_NAVY, fontName="Helvetica-Bold",
                                      leading=15),
        "sec_sub": ParagraphStyle("sec_sub", fontSize=8.5, textColor=C_ACCENT, leading=11,
                                    fontName="Helvetica-Oblique"),
    }


def _p(t, st):
    return Paragraph(_esc_html(t), st)


def _th(t, s) -> Paragraph:
    """Celda de encabezado de tabla (texto claro sobre fondo navy)."""
    return _p(t, s["cell_hdr"])


def _fit_widths(widths: list[float]) -> list[float]:
    """Escala anchos para que sumen exactamente CW."""
    wsum = sum(widths)
    if wsum <= 0:
        return [CW]
    if wsum > CW * 1.001 or wsum < CW * 0.999:
        scale = CW / wsum
        return [w * scale for w in widths]
    return list(widths)


def _simple_table(rows: list, widths: list, *, grid: bool = True) -> Table:
    t = Table(rows, colWidths=_fit_widths(widths), splitByRow=1)
    style = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]
    if grid:
        style.extend([
            ("GRID", (0, 0), (-1, -1), 0.3, C_BORDER),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [C_PAPER, C_OFFWH]),
        ])
    t.setStyle(TableStyle(style))
    return t


def _hdr_table(rows: list, widths: list) -> Table:
    t = Table(rows, colWidths=_fit_widths(widths), repeatRows=1, splitByRow=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), C_NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), C_PAPER),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.4, C_BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_PAPER, C_OFFWH]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


def _ddf_hypothesis_blocks(hypotheses: list, s: dict) -> list:
    """Hipótesis DDF en bloques legibles (evita columnas estrechas)."""
    out: list = []
    for h in hypotheses:
        if not isinstance(h, dict):
            continue
        hid = _safe(h.get("id"))
        banner = Table([[
            _p(f"<b>{hid}</b>", s["cell_b"]),
            _p(f"Confianza: <b>{_safe(h.get('confianza'))}</b>", s["cell"]),
        ]], colWidths=_cols_fracs(0.55, 1.0))
        banner.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), C_OFFWH),
            ("BOX", (0, 0), (-1, -1), 0.5, C_BORDER),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        out.append(banner)
        out.append(_p(f"<b>Hipótesis:</b> {_safe(h.get('enunciado'))}", s["body"]))
        out.append(_p(f"<b>Condición refutadora:</b> {_safe(h.get('refutadora'))}", s["body"]))
        dato = h.get("dato_duro")
        if dato and str(dato).strip() not in ("", "—", "-"):
            out.append(_p(f"<b>Dato duro:</b> {_safe(dato)}", s["small"]))
        out.append(Spacer(1, GAP * 1.5))
    return out


def _prose(data: dict, key: str, s: dict) -> list:
    """Inserta párrafos densos de sustento analítico."""
    out: list = []
    for para in (data.get("dense_narratives") or {}).get(key) or []:
        out.append(_p(para, s["body"]))
    return out


def _part_divider(part: str, title: str, subtitle: str, s: dict, *, first: bool = False) -> list:
    """Franja de parte — título y subtítulo DENTRO de la banda navy (sin texto fantasma)."""
    out: list = []
    if not first:
        out.append(PageBreak())
    title_row = Table(
        [[Paragraph(f"PARTE&nbsp;{part}", s["part_lbl"]),
          Paragraph(_esc_html(title), s["part_t"])]],
        colWidths=[2.5 * cm, CW - 2.5 * cm],
    )
    title_row.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    rows = [[title_row]]
    if subtitle:
        rows.append([Paragraph(_esc_html(subtitle), s["part_sub"])])
    stripe = Table(rows, colWidths=[CW])
    band_style = [
        ("BACKGROUND", (0, 0), (-1, -1), C_NAVY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 2 if subtitle else 8),
    ]
    if subtitle:
        band_style += [
            ("TOPPADDING", (0, 1), (-1, 1), 0),
            ("BOTTOMPADDING", (0, 1), (-1, 1), 8),
        ]
    stripe.setStyle(TableStyle(band_style))
    out.append(stripe)
    out.append(Spacer(1, GAP * 3))
    return out


def _section(sec_id: str, title: str, subtitle: str, content: list, s: dict, *, keep: int = 2) -> list:
    """Encabezado pegado solo a intro corta (evita páginas en blanco por bloques enormes)."""
    hdr = _section_hdr(sec_id, title, subtitle, s)
    if not content:
        return hdr
    intro: list = []
    rest: list = []
    for item in content:
        if len(intro) < keep and not isinstance(item, (Table, _ScaledDrawing, KeepTogether)):
            intro.append(item)
        else:
            rest.append(item)
    if intro:
        return [KeepTogether(hdr + intro)] + rest
    return hdr + content


def _emit_part(story: list, divider: list, sections: list[list]) -> None:
    """Inserta una PARTE y sus secciones. PageBreak va aparte — nunca dentro de KeepTogether."""
    breaks = [f for f in divider if isinstance(f, PageBreak)]
    body = [f for f in divider if not isinstance(f, PageBreak)]
    merged: list = []
    for sec in sections:
        merged.extend(sec)
    if breaks:
        story.extend(breaks)
    story.extend(body)
    story.extend(merged)


def _section_hdr(sec_id: str, title: str, subtitle: str, s: dict) -> list:
    num_w = 1.15 * cm
    txt_w = CW - num_w
    num_box = Table([[Paragraph(sec_id, s["sec_num"])]], colWidths=[num_w])
    num_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_NAVY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    txt = Table(
        [[Paragraph(_esc_html(title), s["sec_title"])],
         [Paragraph(_esc_html(subtitle), s["sec_sub"])]],
        colWidths=[txt_w],
    )
    txt.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
    ]))
    row = Table([[num_box, txt]], colWidths=[num_w, txt_w])
    row.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    sep = Table([[""]], colWidths=[CW], rowHeights=[1])
    sep.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.8, C_ACCENT)]))
    return [row, sep, Spacer(1, GAP * 2)]


def _band(title: str, subtitle: str, s: dict) -> list:
    """Compat: delega a encabezado de sección sin número."""
    return _section_hdr("", title, subtitle, s)


def _guide(text: str, s: dict) -> list:
    if not text:
        return []
    return [_p(f"<i>Orientacion:</i> {_safe(text)}", s["guide"])]


def _kpi_strip(items: list[tuple[str, str, Any]], s: dict) -> Table:
    n = len(items)
    vals = [[_p(str(v), s["kpi_v"]) for _, _, v in items]]
    lbls = [[_p(lbl, s["kpi_l"]) for lbl, _, _ in items]]
    t = Table(vals + lbls, colWidths=_fit_widths([CW / n] * n))
    t.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BOX", (0, 0), (-1, -1), 0.6, C_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, C_BORDER),
        ("BACKGROUND", (0, 0), (-1, 0), C_OFFWH),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def _page_hdr_footer(canvas, doc):
    canvas.saveState()
    pg = canvas.getPageNumber()
    if pg <= 1:
        canvas.restoreState()
        return
    hdr_y = H - MY_T + 0.25 * cm
    ftr_y = MY_B - 0.35 * cm
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(C_GRAY)
    canvas.drawString(MX, hdr_y, "ARHIAX Dx Pro - Informe de Diagnostico Ejecutivo")
    canvas.drawRightString(W - MX, hdr_y, f"Pag. {pg - 1}")
    canvas.setStrokeColor(C_BORDER)
    canvas.line(MX, hdr_y - 0.1 * cm, W - MX, hdr_y - 0.1 * cm)
    canvas.drawString(MX, ftr_y, "Sinergia - PMEL/ATK - Confidencial")
    canvas.restoreState()


def _cover(canvas, case: Any, data: dict, s: dict):
    canvas.saveState()
    canvas.setFillColor(C_NAVY)
    canvas.rect(0, 0, W, H, fill=1, stroke=0)
    meta = data["meta"]
    exec_ = data["executive"]
    eng = data.get("engagement") or {}
    canvas.setFont("Helvetica-Bold", 10)
    canvas.setFillColor(C_ACCENT)
    canvas.drawString(MX, H - MY_T, "ARHIAX Dx Pro · PMEL/ATK · Informe de Diagnóstico")
    canvas.setFont("Helvetica-Bold", 22)
    canvas.setFillColor(C_PAPER)
    y = H * 0.62
    for line in _safe(meta["client_name"]).split()[:6]:
        canvas.drawString(MX, y, line)
        y -= 26
    canvas.setFont("Helvetica", 11)
    canvas.setFillColor(C_OFFWH)
    canvas.drawString(MX, H * 0.48, _safe(meta["domain"]))
    canvas.setStrokeColor(C_ACCENT)
    canvas.setLineWidth(1.2)
    canvas.line(MX, H * 0.44, W - MX, H * 0.44)
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(C_GRAY)
    lines = [
        "Triangulación DDF · Encuesta Multi-Rater · Actualización Bayesiana · BPMN AS-IS/TO-BE",
        f"Engagement: {meta.get('engagement_id', '—')}  ·  Caso: {meta.get('case_id', '—')}",
        f"{eng.get('city', '')}, {eng.get('country', '')}  ·  {eng.get('sector', '')}  ·  {eng.get('size_org', '')} FTE",
        datetime.now().strftime("%d de %B de %Y") + f"  ·  {eng.get('confidentiality', 'Confidencial')}",
    ]
    yl = H * 0.36
    for ln in lines:
        canvas.drawString(MX, yl, ln)
        yl -= 14
    score = exec_.get("overall_score", "—")
    canvas.setFillColor(C_ACCENT)
    canvas.setFont("Helvetica-Bold", 28)
    canvas.drawString(MX, H * 0.14, f"{score}")
    canvas.setFont("Helvetica", 10)
    canvas.setFillColor(C_PAPER)
    canvas.drawString(MX + 50, H * 0.145, "/100 madurez")
    canvas.drawString(MX + 50, H * 0.115, f"{exec_.get('total_responses', 0)} respondentes · δσ crítico detectado")
    canvas.restoreState()


def _sec_index(data: dict, s: dict) -> list:
    outline = data.get("outline") or []
    content: list = []
    content.append(_p("<b>Contenido del informe</b>", s["h2"]))
    toc_rows = []
    part_row_idx: list[int] = []
    for part in outline:
        part_row_idx.append(len(toc_rows))
        toc_rows.append([
            Paragraph("&nbsp;", s["toc"]),
            _p(f"PARTE {part['part']} — {part['title']}", s["toc_sec"]),
        ])
        for sec in part.get("sections") or []:
            toc_rows.append([
                _p(sec["id"], s["toc_sec"]),
                _p(sec["title"], s["toc"]),
            ])
    toc_t = _simple_table(toc_rows, _cols_fixed_flex([1.3 * cm], [1]), grid=False)
    toc_style = [("LEFTPADDING", (0, 1), (-1, -1), 8),
                 ("TOPPADDING", (0, 0), (-1, -1), 3),
                 ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    for idx in part_row_idx:
        toc_style.append(("TOPPADDING", (0, idx), (-1, idx), 7))
        toc_style.append(("LINEBELOW", (0, idx), (-1, idx), 0.4, C_BORDER))
    toc_t.setStyle(TableStyle(toc_style))
    content.append(toc_t)
    return _section("1.0", "Indice general", "Estructura del informe por partes y secciones", content, s)


def _sec_context(data: dict, s: dict) -> list:
    guides = data.get("section_guides") or {}
    eng = data.get("engagement") or {}
    content: list = []
    content += _guide(guides.get("context", ""), s)
    content += _prose(data, "context", s)
    content.append(_p("<b>Perfil del engagement</b>", s["h2"]))
    prof = [
        ["Razón social", _safe(eng.get("legal_name"))],
        ["NIT", _safe(eng.get("nit"))],
        ["Sector / Tamaño", f"{_safe(eng.get('sector'))} · {_safe(eng.get('size_org'))} empleados"],
        ["Ubicación", f"{_safe(eng.get('city'))}, {_safe(eng.get('country'))}"],
        ["Antigüedad", f"{_safe(eng.get('years_operating'))} años operando"],
        ["Sponsor", f"{_safe(eng.get('contact_name'))} — {_safe(eng.get('contact_role'))}"],
        ["Plazo diagnóstico", _safe(eng.get("deadline"))],
        ["Confidencialidad", _safe(eng.get("confidentiality"))],
    ]
    pt = _simple_table(
        [[Paragraph(f"<b>{k}</b>", s["cell_b"]), _p(v, s["cell"])] for k, v in prof],
        _cols_fixed_flex([3.2 * cm], [1]),
    )
    content.append(pt)
    content.append(Spacer(1, GAP))
    content.append(_p("<b>Síntoma reportado y contexto</b>", s["h2"]))
    content.append(_p(_safe(eng.get("symptom")), s["body"]))
    content.append(_p(
        f"<b>Desde cuándo:</b> {_safe(eng.get('problem_since'))} · "
        f"<b>Intentos previos:</b> {_safe(eng.get('previous_attempts'))}",
        s["small"],
    ))
    content.append(_p(f"<b>Resultado esperado:</b> {_safe(eng.get('expected_outcome'))}", s["body"]))
    sources = eng.get("grey_sources") or []
    if sources:
        content.append(_p("<b>Fuentes grises aportadas:</b> " + "; ".join(_safe(x) for x in sources), s["small"]))
    return _section("1.1", "Contexto del engagement", "Perfil del cliente, sintoma y alcance", content, s, keep=8)


def _sec_executive(data: dict, s: dict) -> list:
    guides = data.get("section_guides") or {}
    ex = data["executive"]
    content: list = []
    content += _guide(guides.get("executive", ""), s)
    content += _prose(data, "executive", s)
    content.append(_kpi_strip([
        ("Madurez", "", f"{ex.get('overall_score', '—')}/100"),
        ("Respondentes", "", ex.get("total_responses", 0)),
        ("Hipótesis DDF", "", len(data.get("triz_ddf", {}).get("hypotheses_intake") or [])),
        ("Pérdida est.", "", f"USD {data.get('bottlenecks', {}).get('total_loss_usd', '—')}/mes"),
    ], s))
    content.append(Spacer(1, GAP))
    content.append(_p(ex.get("thesis"), s["body"]))
    content.append(Spacer(1, GAP))
    content.append(_p("<b>Implicaciones estratégicas inmediatas</b>", s["h2"]))
    for imp in ex.get("implications") or []:
        content.append(_p(f"• {imp}", s["body"]))
    content.append(Spacer(1, GAP))
    content.append(_p(f"<b>Próximo paso recomendado:</b> {_safe(ex.get('next_step'))}", s["body_b"]))
    return _section("2.1", "Resumen ejecutivo", "Sintesis integrada del diagnostico", content, s)


def _sec_methodology(data: dict, s: dict) -> list:
    guides = data.get("section_guides") or {}
    m = data.get("methodology") or {}
    content: list = []
    content += _guide(guides.get("methodology", ""), s)
    content += _prose(data, "methodology", s)
    content.append(_p(data.get("triangulation", {}).get("model", ""), s["body"]))
    rows = [[_th("Fase", s), _th("Agentes y alcance analítico", s)]]
    for phase, desc in m.get("phases", []):
        rows.append([_p(phase, s["cell_b"]), _p(desc, s["cell"])])
    content.append(_hdr_table(rows, _cols_fixed_flex([3.2 * cm], [1])))
    content.append(Spacer(1, GAP))
    content.append(_p("<b>Qué se evalúa en este caso</b>", s["h2"]))
    for item in m.get("evaluates", []):
        content.append(_p(f"• {item}", s["body"]))
    eng = data.get("engagement") or {}
    roles = eng.get("roles") or []
    dims = eng.get("dimensions") or []
    if roles or dims:
        content.append(Spacer(1, GAP))
        content.append(_p(
            f"<b>Configuración del instrumento:</b> roles {', '.join(roles)} · "
            f"dimensiones {', '.join(dims)}",
            s["small"],
        ))
    return _section(
        "1.2", "Metodologia ARHIAX Dx Pro",
        f"{m.get('pipeline_agents', 18)} agentes en 5 fases", content, s,
    )


def _sec_triangulation(data: dict, s: dict) -> list:
    guides = data.get("section_guides") or {}
    tri = data.get("triangulation") or {}
    scoring = data.get("scoring") or {}
    content: list = []
    content += _guide(guides.get("triangulation", ""), s)
    content += _prose(data, "triangulation", s)
    flow = triangulation_flow(CW, 66)
    if flow:
        content.append(_gfx(flow))
    content.append(Spacer(1, GAP))

    role_scores = scoring.get("role_scores") or {}
    gap_pairs = (scoring.get("delta_sigma") or {}).get("gap_pairs") or tri.get("gap_pairs") or []
    rb = role_bar_chart(role_scores, CW, 78)
    db = delta_sigma_bars(gap_pairs, CW)
    if rb:
        content.append(_gfx(rb))
        content.append(Spacer(1, GAP))
    if db:
        content.append(_gfx(db))
        content.append(Spacer(1, GAP * 2))

    max_d = tri.get("max_delta_sigma") or (scoring.get("delta_sigma") or {}).get("max_gap")
    if max_d:
        col = C_RED if float(max_d) > 2 else C_GREEN
        content.append(_p(
            f"<b>δσ máximo entre roles: {max_d}</b> — "
            + ("BRECHA CRÍTICA: la dirección y operación perciben capacidades de forma incompatible. "
               "Acción: alinear KPIs antes de nuevas inversiones.")
            if float(max_d) > 2 else "dentro de rango aceptable de alineamiento",
            ParagraphStyle("dg", parent=s["body"], textColor=col, spaceBefore=6),
        ))

    content.append(Spacer(1, GAP))
    content.append(_p("<b>Matriz de triangulación</b>", s["h2"]))
    rows = [[
        _th("ID", s), _th("Evidencia DDF / incidente", s),
        _th("Señal encuesta", s), _th("Bayesiano", s), _th("Psicometría", s),
    ]]
    for r in tri.get("rows") or []:
        rows.append([
            _p(r.get("id"), s["cell_b"]),
            _p(r.get("ddf"), s["cell"]),
            _p(r.get("survey"), s["cell"]),
            _p(r.get("bayesian"), s["cell"]),
            _p(r.get("psych"), s["cell"]),
        ])
    content.append(_hdr_table(rows, _cols_fracs(0.45, 2.3, 1.35, 0.85, 0.85)))
    return _section("2.2", "Triangulacion de evidencia", "DDF + encuesta multi-rater + bayesiano", content, s)


def _sec_maturity(data: dict, s: dict) -> list:
    guides = data.get("section_guides") or {}
    scoring = data.get("scoring") or {}
    dim_scores = scoring.get("dimension_scores") or data.get("maturity", {}).get("dimension_scores") or []
    content: list = []
    content += _guide(guides.get("maturity", ""), s)
    content += _prose(data, "maturity", s)
    overall = scoring.get("overall_score", "—")
    bench = scoring.get("benchmark_score", 75)
    gap_global = int(overall) - int(bench) if str(overall).isdigit() else "—"
    content.append(_p(
        f"Índice global: <b>{overall}/100</b> · Benchmark sectorial: <b>{bench}</b> · "
        f"Brecha: <b>{gap_global} puntos</b>. "
        "Un score inferior a 70 indica capacidad operativa por debajo del estándar del sector.",
        s["body"],
    ))
    radar = dimension_radar(dim_scores, min(CW * 0.55, 10 * cm), 95)
    rows = [[_th("Dimensión", s), _th("Score", s),
               _th("Benchmark", s), _th("Brecha", s), _th("Lectura", s)]]
    for d in dim_scores:
        sc = d.get("score", 0)
        reading = "Capacidad estable" if sc >= 70 else ("Brecha relevante" if sc >= 55 else "Riesgo operativo")
        rows.append([
            _p(d.get("dimension") or d.get("name"), s["cell"]),
            _p(sc, s["cell"]),
            _p(d.get("benchmark", 75), s["cell"]),
            _p(d.get("gap"), s["cell"]),
            _p(reading, s["cell"]),
        ])
    tbl = _hdr_table(rows, _cols_fracs(1.7, 0.55, 0.65, 0.55, 1.2)) if len(rows) > 1 else None
    if radar:
        content.append(_gfx(radar))
        content.append(Spacer(1, GAP))
    if tbl:
        content.append(tbl)

    role_scores = scoring.get("role_scores") or {}
    if role_scores:
        content.append(Spacer(1, GAP))
        content.append(_p("<b>Scores por nivel jerárquico — interpretación</b>", s["h2"]))
        rr = [[_th("Rol", s), _th("Score", s), _th("N", s),
               _th("Perfil", s), _th("Interpretación", s)]]
        interp = {
            "optimista": "Sobreestima capacidades vs piso",
            "crítico": "Subestima o reporta fricción real",
        }
        for role, info in role_scores.items():
            if isinstance(info, dict):
                perc = info.get("perception", "—")
                rr.append([
                    _p(role, s["cell"]),
                    _p(info.get("score"), s["cell"]),
                    _p(info.get("n_responses"), s["cell"]),
                    _p(perc, s["cell"]),
                    _p(interp.get(perc, "Percepción moderada"), s["cell"]),
                ])
        content.append(_hdr_table(rr, _cols_fracs(1.0, 0.55, 0.45, 0.85, 2.3)))
    return _section("2.3", "Diagnostico de madurez", "Indice global y desglose por dimension y rol", content, s)


def _sec_cienciometria(data: dict, s: dict) -> list:
    guides = data.get("section_guides") or {}
    cien = data.get("cienciometria") or {}
    content: list = []
    content += _guide(guides.get("cienciometria", ""), s)
    content += _prose(data, "cienciometria", s)
    if cien.get("consensus"):
        content.append(_p(cien["consensus"], s["body"]))
    rows = [[_th("Estudio / fuente", s), _th("Año", s),
               _th("Relevancia", s), _th("Hallazgo aplicable", s)]]
    for lit in cien.get("literature") or []:
        if isinstance(lit, dict):
            rows.append([
                _p(lit.get("title"), s["cell"]),
                _p(lit.get("year"), s["cell"]),
                _p(lit.get("relevance"), s["cell"]),
                _p(lit.get("key_finding"), s["cell"]),
            ])
    content.append(_hdr_table(rows, _cols_fracs(1.5, 0.4, 0.6, 2.1)))
    if cien.get("methodologies"):
        content.append(Spacer(1, GAP))
        content.append(_p("<b>Metodologías validadas aplicadas:</b> " +
                        "; ".join(_safe(m) for m in cien["methodologies"][:6]), s["small"]))
    return _section("3.1", "Cienciometria y base cientifica", "Literatura y consenso aplicado al dominio", content, s)


def _sec_cartografia(data: dict, s: dict) -> list:
    guides = data.get("section_guides") or {}
    cart = data.get("cartografia") or {}
    content: list = []
    content += _guide(guides.get("cartografia", ""), s)
    content += _prose(data, "cartografia", s)
    sector = cart.get("sector_process") or {}
    if sector.get("description"):
        content.append(_p(sector["description"], s["body"]))
    if cart.get("industry_cases"):
        content.append(Spacer(1, GAP))
        content.append(_p("<b>Casos sectoriales comparables</b>", s["h2"]))
        rows = [[_th("Tipo empresa", s), _th("Problema", s),
                   _th("Solución", s), _th("Resultado", s)]]
        for c in cart["industry_cases"][:4]:
            if isinstance(c, dict):
                rows.append([
                    _p(c.get("company_type"), s["cell"]),
                    _p(c.get("problem"), s["cell"]),
                    _p(c.get("solution"), s["cell"]),
                    _p(c.get("result"), s["cell"]),
                ])
        content.append(_hdr_table(rows, _cols_fracs(0.9, 1.5, 1.5, 1.3)))
    if cart.get("benchmarks"):
        content.append(Spacer(1, GAP))
        content.append(_p("<b>Benchmarks sectoriales vs situación del cliente</b>", s["h2"]))
        brows = [[_th("KPI", s), _th("Sector P50", s),
                  _th("Cliente", s), _th("Brecha", s)]]
        for b in cart["benchmarks"]:
            if isinstance(b, dict):
                brows.append([_p(b.get("kpi"), s["cell"]), _p(b.get("sector_p50"), s["cell"]),
                              _p(b.get("cliente"), s["cell"]), _p(b.get("gap"), s["cell"])])
        content.append(_hdr_table(brows, _cols_fracs(1.4, 0.8, 1.0, 0.8)))
    if cart.get("best_practices"):
        content.append(Spacer(1, GAP))
        content.append(_p("<b>Mejores prácticas recomendadas</b>", s["h2"]))
        for bp in cart["best_practices"][:5]:
            if isinstance(bp, dict):
                content.append(_p(f"• <b>{_safe(bp.get('practice'))}</b> — {_safe(bp.get('impact'))}", s["body"]))
    techs = cart.get("technologies") or []
    if techs:
        content.append(_p("<b>Stack tecnológico típico del sector:</b> " + " · ".join(_safe(t) for t in techs), s["small"]))
    return _section("3.2", "Cartografia sectorial", "Benchmarks, casos comparables y tecnologias", content, s)


def _sec_ddf(data: dict, s: dict) -> list:
    guides = data.get("section_guides") or {}
    triz = data.get("triz_ddf") or {}
    content: list = []
    content += _guide(guides.get("ddf", ""), s)
    content += _prose(data, "ddf", s)
    hypotheses = triz.get("hypotheses_intake") or []
    if hypotheses:
        content.append(_p("<b>Hipótesis del intake DDF</b>", s["h2"]))
        content.extend(_ddf_hypothesis_blocks(hypotheses, s))
    content.append(_p("<b>Incidentes documentados (evidencia DDF)</b>", s["h2"]))
    for h in triz.get("hypotheses_intake") or []:
        inc = h.get("incidente")
        if inc and inc != "—":
            content.append(_p(f"<b>{h.get('id')}:</b> {inc}", s["body"]))
        contra = h.get("contradiction")
        if contra:
            content.append(_p(f"<i>Contradicción TRIZ:</i> {contra}", s["small"]))
    return _section("3.3", "Marco DDF", "Hipotesis ancladas a incidentes y refutacion", content, s)


def _sec_process(data: dict, s: dict) -> list:
    guides = data.get("section_guides") or {}
    asis = data.get("asis") or {}
    tobe = data.get("tobe") or {}
    content: list = []
    content += _guide(guides.get("process", ""), s)
    content += _prose(data, "process", s)
    content.append(_p(f"<b>Proceso:</b> {_safe(asis.get('process_name'))}", s["h2"]))
    steps = asis.get("steps") or []
    if steps:
        content.append(_p(" → ".join(_safe(x) for x in steps), s["body"]))
    if asis.get("activities"):
        content.append(Spacer(1, GAP))
        content.append(_p("<b>Detalle de actividades AS-IS</b>", s["h2"]))
        ar = [[_th("Actividad", s), _th("Lane", s),
               _th("Crítica", s), _th("Cuello", s), _th("Notas / evidencia", s)]]
        for a in asis["activities"][:10]:
            if isinstance(a, dict):
                note = _safe(a.get("notes"), "—")
                ar.append([
                    _p(a.get("name"), s["cell"]),
                    _p(a.get("lane"), s["cell"]),
                    _p("Sí" if a.get("is_critical") else "No", s["cell"]),
                    _p("Sí" if a.get("is_bottleneck") else "No", s["cell"]),
                    _p(note, s["cell"]),
                ])
        content.append(_hdr_table(ar, _cols_fracs(1.4, 0.7, 0.45, 0.45, 2.2)))

    content.append(Spacer(1, GAP))
    content.append(_p("<b>TO-BE — flujo objetivo</b>", s["h2"]))
    if tobe.get("steps"):
        content.append(_p(" → ".join(_safe(x) for x in tobe["steps"]), s["body"]))
    opts = tobe.get("options") or []
    if opts:
        content.append(Spacer(1, GAP))
        content.append(_p("<b>Opciones de mejora con ROI estimado</b>", s["h2"]))
        orows = [[_th("Opción", s), _th("Descripción", s),
                  _th("ROI%", s), _th("Payback", s),
                  _th("Inversión", s), _th("Ahorro/mes", s)]]
        for o in opts[:4]:
            if isinstance(o, dict):
                orows.append([
                    _p(o.get("name"), s["cell"]),
                    _p(o.get("description") or "", s["cell"]),
                    _p(o.get("roi_percent"), s["cell"]),
                    _p(f"{o.get('payback_months', '—')}m", s["cell"]),
                    _p(f"USD {o.get('investment_usd', '—'):,}" if o.get("investment_usd") else "—", s["cell"]),
                    _p(f"USD {o.get('monthly_savings_usd', '—'):,}" if o.get("monthly_savings_usd") else "—", s["cell"]),
                ])
        content.append(_hdr_table(orows, _cols_fracs(0.9, 2.2, 0.5, 0.55, 0.85, 0.85)))
    return _section("4.1", "Proceso AS-IS / TO-BE", "Flujo actual, objetivo y opciones ROI", content, s)


def _sec_matrix(data: dict, s: dict) -> list:
    content: list = []
    rows = [[_th("Componente", s), _th("AS-IS", s),
             _th("TO-BE", s), _th("Impacto estimado", s)]]
    for m in data.get("matrix_asis_tobe") or []:
        if isinstance(m, dict):
            rows.append([
                _p(m.get("component"), s["cell"]),
                _p(m.get("as_is"), s["cell"]),
                _p(m.get("to_be"), s["cell"]),
                _p(m.get("impact"), s["cell"]),
            ])
    content.append(_hdr_table(rows, _cols_fracs(0.85, 1.5, 1.5, 1.3)))
    content.append(Spacer(1, GAP))
    content.append(_p(
        "Cada fila representa un componente del sistema operativo. La columna TO-BE describe el estado "
        "objetivo tras la intervención. El impacto se expresa en USD/mes recuperables o en reducción de brecha δσ.",
        s["guide"],
    ))
    return _section("4.2", "Matriz AS-IS -> TO-BE", "Componentes, brechas e impacto economico", content, s)


def _fmt_cell(val: Any) -> str:
    """Formatea listas/dicts para celdas legibles (no repr Python)."""
    if val is None:
        return "—"
    if isinstance(val, list):
        parts = [_safe(x) for x in val if x and str(x).strip() not in ("", "—")]
        return "; ".join(parts) if parts else "—"
    if isinstance(val, dict):
        return _safe(val.get("summary") or val.get("text") or str(val))
    return _safe(val)


def _sec_findings(data: dict, s: dict) -> list:
    guides = data.get("section_guides") or {}
    find = data.get("findings") or {}
    bott = data.get("bottlenecks") or {}
    content: list = []
    content += _guide(guides.get("findings", ""), s)
    content += _prose(data, "findings", s)
    rows = [[
        _th("Hallazgo", s), _th("Evidencia", s),
        _th("Prioridad", s), _th("Tratamiento recomendado", s),
    ]]
    for f in find.get("matrix") or []:
        if isinstance(f, dict):
            rows.append([
                _p(f.get("finding") or f.get("name"), s["cell"]),
                _p(_fmt_cell(f.get("evidence") or f.get("source")), s["cell"]),
                _p(f.get("priority") or f.get("severity"), s["cell"]),
                _p(f.get("treatment") or f.get("recommendation"), s["cell"]),
            ])
    content.append(_hdr_table(rows, _cols_fracs(1.2, 1.1, 0.55, 2.3)))
    content.append(Spacer(1, GAP))
    content.append(_p("<b>Cuellos de botella cuantificados</b>", s["h2"]))
    brows = [[_th("Cuello", s), _th("Impacto", s),
              _th("USD/mes", s), _th("Severidad", s)]]
    for b in bott.get("items") or []:
        if isinstance(b, dict):
            brows.append([
                _p(b.get("name"), s["cell"]),
                _p(b.get("impact_score"), s["cell"]),
                _p(f"USD {b.get('estimated_cost_usd_month', '—'):,}" if b.get("estimated_cost_usd_month") else "—", s["cell"]),
                _p(b.get("severity"), s["cell"]),
            ])
    content.append(_hdr_table(brows, _cols_fracs(1.8, 0.6, 0.9, 0.7)))
    if bott.get("total_loss_usd"):
        content.append(Spacer(1, GAP))
        content.append(_p(
            f"<b>Pérdida de oportunidad total estimada: USD {bott['total_loss_usd']:,}/mes</b> "
            f"(USD {int(bott['total_loss_usd']) * 12:,}/año). "
            "Esta cifra representa el costo de no intervenir en los cuellos identificados.",
            ParagraphStyle("loss", parent=s["body"], textColor=C_RED, fontName="Helvetica-Bold",
                           spaceBefore=4, spaceAfter=6),
        ))
    bc = bottleneck_chart(bott.get("items") or [], CW)
    if bc:
        content.append(Spacer(1, GAP * 2))
        content.append(_gfx(bc))
    return _section("4.3", "Hallazgos y cuellos", "Priorizacion por severidad y costo USD/mes", content, s)


def _sec_decision_rules(data: dict, s: dict) -> list:
    content: list = []
    rows = [[
        _th("Regla", s), _th("Descripción / condición", s),
        _th("Acción si se cumple", s), _th("Condición de falsación", s),
    ]]
    for r in data.get("decision_rules") or []:
        if isinstance(r, dict):
            rows.append([
                _p(r.get("rule"), s["cell_b"]),
                _p(r.get("description") or r.get("condition"), s["cell"]),
                _p(r.get("action") or r.get("evidence"), s["cell"]),
                _p(r.get("falsification", "—"), s["cell"]),
            ])
    content.append(_hdr_table(rows, _cols_fracs(0.65, 1.5, 1.3, 1.3)))
    content.append(Spacer(1, GAP))
    content.append(_p(
        "Las reglas de decisión vinculan señales empíricas (δσ, incidentes, KPIs) con acciones concretas. "
        "Si la condición de falsación se cumple, la hipótesis debe revisarse o descartarse.",
        s["guide"],
    ))
    return _section("4.4", "Reglas de decision", "Criterios para confirmar o descartar hipotesis", content, s)


def _sec_roadmap(data: dict, s: dict) -> list:
    guides = data.get("section_guides") or {}
    content: list = []
    content += _guide(guides.get("roadmap", ""), s)
    content += _prose(data, "roadmap", s)
    rows = [[
        _th("Horizonte", s), _th("Acciones", s), _th("Resultado esperado", s),
    ]]
    for r in data.get("roadmap") or []:
        if isinstance(r, dict):
            rows.append([
                _p(r.get("phase"), s["cell_b"]),
                _p(r.get("content"), s["cell"]),
                _p(r.get("kpi") or r.get("owner"), s["cell"]),
            ])
    content.append(_hdr_table(rows, _cols_fracs(1.1, 3.0, 1.7)))
    next_steps = data.get("next_steps") or []
    if next_steps:
        content.append(Spacer(1, GAP))
        content.append(_p("<b>Próximos pasos inmediatos</b>", s["h2"]))
        for step in next_steps:
            content.append(_p(f"• {step}", s["body"]))
    return _section("5.1", "Roadmap de implementacion", "Secuencia 90 / 180 / 365 dias y proximos pasos", content, s)


def _sec_psychometrics(data: dict, s: dict) -> list:
    guides = data.get("section_guides") or {}
    psy = data.get("psychometrics") or {}
    bay = data.get("bayesian") or {}
    content: list = []
    content += _guide(guides.get("psychometrics", ""), s)
    content += _prose(data, "psychometrics", s)
    cron = psy.get("cronbach") or psy.get("cronbach_alpha_overall") or "—"
    irr = psy.get("irr") or "—"
    content.append(_kpi_strip([
        ("α Cronbach", "", cron),
        ("IRR Krippendorff", "", irr),
        ("QA G14", "", data.get("governance", {}).get("qa_score", "—")),
        ("Confirmadas", "", len(bay.get("confirmed") or [])),
    ], s))
    if cron != "—" or irr != "—":
        content.append(_p(
            f"α Cronbach = {cron}: consistencia interna del instrumento. "
            f"IRR Krippendorff = {irr}: acuerdo inter-evaluador entre roles. "
            "Valores >0.80 indican fiabilidad ALTA para decisiones estratégicas.",
            s["body"],
        ))
    if bay.get("summary") and not str(bay.get("summary", "")).lower().startswith("mock"):
        content.append(_p(bay["summary"], s["body"]))
    content.append(Spacer(1, GAP))
    content.append(_p("<b>Actualización bayesiana de hipótesis</b>", s["h2"]))
    for h in (bay.get("confirmed") or [])[:5]:
        label = h if isinstance(h, str) else h.get("hypothesis", str(h))
        content.append(_p(f"✓ <b>Confirmada:</b> {label} — evidencia multi-rater y DDF convergen.", s["body"]))
    for h in (bay.get("rejected") or [])[:3]:
        label = h if isinstance(h, str) else h.get("hypothesis", str(h))
        content.append(_p(f"✗ <b>Rechazada:</b> {label}", ParagraphStyle("no", parent=s["body"], textColor=C_RED)))
    qa = data.get("governance", {}).get("qa_score")
    if qa is not None:
        try:
            qa_val = float(qa)
            estado = "supera el umbral" if qa_val >= 85 else "por debajo del umbral"
            content.append(Spacer(1, GAP))
            content.append(_p(
                f"<b>Control de calidad G14:</b> {qa}/100 — {estado} mínimo de publicación (85).",
                s["small"],
            ))
        except (TypeError, ValueError):
            pass
    return _section("2.4", "Psicometria, IRR y bayesiano", "Validez del instrumento y hipotesis", content, s)


def _sec_narrative_governance(data: dict, case: Any, s: dict) -> list:
    gov = data.get("governance") or {}
    meta = data["meta"]
    content: list = []
    content += _prose(data, "narrative", s)
    content.append(_p("<b>Trazabilidad del pipeline (18 etapas)</b>", s["h2"]))
    _AGENT_DESC = {
        "g01_receptor": "Validacion de mandato y alcance diagnostico",
        "g02_configurador": "Benchmarks sectoriales y KPIs de referencia",
        "g03_cienciometro": "Revision bibliografica y consenso cientifico",
        "g04_cartografo": "Mapa sectorial, casos comparables, patentometria",
        "g05_brechas": "Brechas AS-IS vs benchmark y priorizacion",
        "g06_bpmn_architect": "Modelado BPMN del proceso AS-IS",
        "g07_cuellos": "Cuantificacion de cuellos y perdida USD/mes",
        "g08_optimizador": "Opciones TO-BE con ROI y roadmap",
        "g09a_preguntas": "Banco de preguntas multi-rater Likert",
        "g09b_ramificacion": "Ramificacion por rol y tiempo estimado",
        "g09c_validacion": "Validacion psicometrica del instrumento",
        "g10a_scoring": "Scoring por dimension, rol y delta sigma",
        "g10b_psicometria": "Alpha Cronbach e analisis por item",
        "g11a_bayesiano": "Actualizacion bayesiana de hipotesis DDF",
        "g11b_nlp": "Analisis NLP de respuestas abiertas",
        "g12_hallazgos": "Matriz de hallazgos priorizados",
        "g13_redactor": "Narrativa ejecutiva integrada",
        "g14_qa_control": "Control de calidad >=85 para publicacion",
        "bpmn_generator": "Generacion XML BPMN Camunda",
        "irr_calculator": "IRR Krippendorff inter-evaluador",
        "scoring_engine": "Normalizacion y percentiles",
    }
    stages = list((gov.get("stage_outcomes") or {}).items())
    if stages:
        srows = [[_th("Agente", s), _th("Función", s), _th("Outcome", s)]]
        for name, info in stages:
            srows.append([
                _p(name, s["cell"]),
                _p(_AGENT_DESC.get(name, "Etapa del pipeline Pro"), s["cell"]),
                _p((info or {}).get("outcome"), s["cell"]),
            ])
        content.append(_hdr_table(srows, _cols_fracs(1.1, 1.4, 1.8)))
    content.append(Spacer(1, GAP))
    cert = _simple_table([[
        _p(f"<b>ID Caso:</b> {meta.get('case_id')}", s["small"]),
        _p(f"<b>Trace:</b> {case.trace_id or '—'}", s["small"]),
        _p(f"<b>Estado:</b> {meta.get('case_status')}", s["small"]),
        _p(f"<b>Generado:</b> {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}", s["small"]),
    ]], _cols_equal(4))
    cert.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_OFFWH),
        ("BOX", (0, 0), (-1, -1), 0.5, C_BORDER),
    ]))
    content.append(cert)
    content.append(Spacer(1, GAP))
    content.append(_p(
        "Este informe fue generado por ARHIAX Dx Pro bajo gobernanza PMEL/ATK. "
        "Toda recomendación está trazada a evidencia DDF, respuestas de encuesta y veredicto bayesiano. "
        "La reproducción parcial requiere autorización del sponsor del engagement.",
        s["small"],
    ))
    return _section("5.2", "Narrativa y gobernanza", "Sintesis integrada y trazabilidad PMEL/ATK", content, s)


def build_pro_pdf_dense(case: Any, evidence: list | None = None) -> bytes:
    if not PDF_OK:
        raise RuntimeError("reportlab no instalado")

    data = build_pro_report_data(case)
    missing = validate_report_for_deliverables(data, case)
    if missing:
        raise RuntimeError(
            "Informe incompleto — no se genera PDF sin datos reales del pipeline: "
            + "; ".join(missing)
        )
    s = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=LETTER,
        leftMargin=MX, rightMargin=MX,
        topMargin=MY_T, bottomMargin=MY_B,
        title=f"Diagnóstico — {case.client_name}",
    )

    story: list = []
    # Página 1 = portada (onFirstPage). El salto evita escribir sobre la portada.
    story.append(PageBreak())

    # PARTE I — Contexto y marco metodológico
    p1 = (data.get("outline") or [{}])[0]
    _emit_part(story, _part_divider(
        p1.get("part", "I"), p1.get("title", "Contexto y marco metodologico"),
        p1.get("subtitle", ""), s, first=True,
    ), [_sec_index(data, s), _sec_context(data, s), _sec_methodology(data, s)])

    # PARTE II — Diagnóstico cuantitativo
    p2 = (data.get("outline") or [{}, {}])[1] if len(data.get("outline") or []) > 1 else {}
    _emit_part(story, _part_divider(
        p2.get("part", "II"), p2.get("title", "Diagnostico cuantitativo"),
        p2.get("subtitle", ""), s,
    ), [_sec_executive(data, s), _sec_triangulation(data, s), _sec_maturity(data, s), _sec_psychometrics(data, s)])

    # PARTE III — Fundamento analítico
    p3 = (data.get("outline") or [{}, {}, {}])[2] if len(data.get("outline") or []) > 2 else {}
    _emit_part(story, _part_divider(
        p3.get("part", "III"), p3.get("title", "Fundamento analitico"),
        p3.get("subtitle", ""), s,
    ), [_sec_cienciometria(data, s), _sec_cartografia(data, s), _sec_ddf(data, s)])

    # PARTE IV — Proceso y mejoras
    p4 = (data.get("outline") or [{}, {}, {}, {}])[3] if len(data.get("outline") or []) > 3 else {}
    _emit_part(story, _part_divider(
        p4.get("part", "IV"), p4.get("title", "Proceso y mejoras"),
        p4.get("subtitle", ""), s,
    ), [_sec_process(data, s), _sec_matrix(data, s), _sec_findings(data, s), _sec_decision_rules(data, s)])

    # PARTE V — Plan de acción y cierre
    p5 = (data.get("outline") or [{}, {}, {}, {}, {}])[4] if len(data.get("outline") or []) > 4 else {}
    _emit_part(story, _part_divider(
        p5.get("part", "V"), p5.get("title", "Plan de accion y cierre"),
        p5.get("subtitle", ""), s,
    ), [_sec_roadmap(data, s), _sec_narrative_governance(data, case, s)])

    doc.build(story, onFirstPage=lambda c, d: _cover(c, case, data, s), onLaterPages=_page_hdr_footer)
    buf.seek(0)
    return buf.read()
