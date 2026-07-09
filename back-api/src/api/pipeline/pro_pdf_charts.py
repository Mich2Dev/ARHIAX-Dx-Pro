"""Gráficas ReportLab para el informe Pro."""
from __future__ import annotations

import math
from typing import Any

try:
    from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon, Circle
    from reportlab.lib import colors as _rl_colors
    CHARTS_OK = True
    colors = _rl_colors
except ImportError:
    CHARTS_OK = False
    colors = None


def _hex(c: str):
    return colors.HexColor(c) if CHARTS_OK else None


C_NAVY = "#243c4f"
C_ACCENT = "#9d8564"
C_RED = "#8b3a3a"
C_GREEN = "#2d6a4f"
C_GRAY = "#706f69"
C_PAPER = "#faf7f2"
C_BORDER = "#e0d9ce"


def role_bar_chart(role_scores: dict, width: float = 460, height: float = 130) -> Drawing | None:
    if not CHARTS_OK or not role_scores:
        return None
    d = Drawing(width, height)
    d.add(Rect(0, 0, width, height, fillColor=_hex(C_PAPER), strokeColor=_hex(C_BORDER), strokeWidth=0.5))

    def _score(v: Any) -> float:
        if isinstance(v, dict):
            raw = v.get("score")
        else:
            raw = v
        try:
            return float(raw) if raw is not None else 0.0
        except (TypeError, ValueError):
            return 0.0

    items = [(k, _score(v)) for k, v in role_scores.items()]
    if not items:
        return d
    n = len(items)
    bar_w = min(70, (width - 40) / max(n, 1) - 12)
    x0 = 30
    max_s = max(s for _, s in items) or 100
    for i, (label, score) in enumerate(items):
        x = x0 + i * (bar_w + 14)
        h = (score / 100) * (height - 42)
        color = _hex(C_RED) if score < 55 else (_hex(C_ACCENT) if score < 70 else _hex(C_GREEN))
        d.add(Rect(x, 22, bar_w, h, fillColor=color, strokeColor=_hex(C_NAVY), strokeWidth=0.4))
        d.add(String(x + bar_w / 2, 8, label[:16], fontSize=8, fillColor=_hex(C_NAVY), textAnchor="middle"))
        d.add(String(x + bar_w / 2, 22 + h + 4, f"{score:.0f}", fontSize=9, fillColor=_hex(C_NAVY), textAnchor="middle"))
    d.add(Line(24, 22, width - 8, 22, strokeColor=_hex(C_BORDER)))
    d.add(String(8, height - 12, "Score por rol (0-100)", fontSize=9, fillColor=_hex(C_GRAY)))
    return d


def dimension_radar(dim_scores: list, width: float = 220, height: float = 160) -> Drawing | None:
    if not CHARTS_OK or not dim_scores:
        return None
    d = Drawing(width, height)
    cx, cy = width / 2, height * 0.52
    r = min(width, height) * 0.34
    n = len(dim_scores)
    for frac in [0.25, 0.5, 0.75, 1.0]:
        pts = []
        for k in range(n):
            ang = math.pi / 2 + 2 * math.pi * k / n
            pts += [cx + r * frac * math.cos(ang), cy + r * frac * math.sin(ang)]
        if len(pts) >= 6:
            d.add(Polygon(pts, fillColor=None, strokeColor=_hex(C_BORDER), strokeWidth=0.4))
    pts = []
    for k, dim in enumerate(dim_scores):
        score = float(dim.get("score", 0) or 0) / 100
        ang = math.pi / 2 + 2 * math.pi * k / n
        pts += [cx + r * score * math.cos(ang), cy + r * score * math.sin(ang)]
    if pts:
        d.add(Polygon(pts, fillColor=_hex("#9d856430"), strokeColor=_hex(C_ACCENT), strokeWidth=1.2))
    for k, dim in enumerate(dim_scores):
        ang = math.pi / 2 + 2 * math.pi * k / n
        lx = cx + (r + 10) * math.cos(ang)
        ly = cy + (r + 10) * math.sin(ang)
        lbl = str(dim.get("dimension") or dim.get("name", ""))[:14]
        d.add(String(lx, ly - 2, lbl, fontSize=7.5, fillColor=_hex(C_NAVY), textAnchor="middle"))
    return d


def delta_sigma_bars(gap_pairs: list, width: float = 460, height: float = 0) -> Drawing | None:
    """Barras horizontales δσ — etiqueta arriba, barra abajo, valor a la derecha.
    El color codifica severidad relativa a la mayor brecha del set (sin umbrales fijos)."""
    if not CHARTS_OK or not gap_pairs:
        return None
    items = [g for g in gap_pairs[:6] if isinstance(g, dict)]
    if not items:
        return None

    ml, mr, mt, mb = 12, 78, 20, 12
    bar_h, label_h, row_gap = 13, 11, 15
    row_h = label_h + bar_h + row_gap
    n = len(items)
    calc_h = mt + n * row_h + mb
    height = max(height, calc_h) if height > 0 else calc_h

    d = Drawing(width, height)
    d.add(Rect(0, 0, width, height, fillColor=_hex(C_PAPER), strokeColor=_hex(C_BORDER), strokeWidth=0.5))
    d.add(String(ml, height - 9, "Brechas de percepcion entre roles por dimension (delta-sigma)",
                 fontSize=7.5, fillColor=_hex(C_GRAY)))

    bar_area_w = width - ml - mr
    deltas = []
    for g in items:
        try:
            deltas.append(abs(float(g.get("delta") or 0)))
        except (TypeError, ValueError):
            deltas.append(0.0)
    max_delta = max(deltas) if deltas else 1.0
    if not max_delta:
        max_delta = 1.0

    y = height - mt - label_h
    for g, delta in zip(items, deltas):
        label = f"{g.get('roles', '')} · {g.get('dimension', '')}".strip(" ·")[:48]
        frac = delta / max_delta
        bw = max(6, frac * bar_area_w)
        # Severidad relativa: mayor brecha = navy intenso; menores = acento suave.
        if g.get("critical") or frac >= 0.85:
            col = _hex(C_NAVY)
        elif frac >= 0.5:
            col = _hex(C_ACCENT)
        else:
            col = _hex("#c4b79c")

        d.add(String(ml, y + 2, label, fontSize=7, fillColor=_hex(C_NAVY)))
        bar_y = y - bar_h
        d.add(Rect(ml, bar_y, bw, bar_h, fillColor=col, strokeColor=None, strokeWidth=0))
        d.add(String(ml + bw + 5, bar_y + 3, f"{delta:.1f}",
                     fontSize=7.5, fillColor=_hex(C_NAVY)))
        y = bar_y - row_gap

    # Eje base sutil
    d.add(Line(ml, mb, ml, height - mt - 2, strokeColor=_hex(C_BORDER), strokeWidth=0.5))
    return d


def bottleneck_chart(bottlenecks: list, width: float = 460, height: float = 0) -> Drawing | None:
    """Barras de impacto — etiqueta arriba, barra abajo, costo a la derecha."""
    if not CHARTS_OK or not bottlenecks:
        return None
    items = [b for b in bottlenecks[:5] if isinstance(b, dict)]
    if not items:
        return None

    ml, mr, mt, mb = 10, 90, 16, 10
    bar_h, label_h, row_gap = 16, 14, 14
    row_h = label_h + bar_h + row_gap
    n = len(items)
    calc_h = mt + n * row_h + mb
    height = max(height, calc_h) if height > 0 else calc_h

    d = Drawing(width, height)
    d.add(Rect(0, 0, width, height, fillColor=_hex(C_PAPER), strokeColor=_hex(C_BORDER), strokeWidth=0.5))
    d.add(String(ml, height - 8, "Impacto estimado por cuello de botella",
                 fontSize=7.5, fillColor=_hex(C_GRAY)))

    bar_area_w = width - ml - mr
    max_imp = max(float(b.get("impact_score", 5) or 5) for b in items) or 10

    y = height - mt - label_h
    for b in items:
        imp = float(b.get("impact_score", 5) or 5)
        name = str(b.get("name", "Cuello"))
        bw = max(10, (imp / max_imp) * bar_area_w)
        cost = b.get("estimated_cost_usd_month")
        extra = f"${cost:,}/mes" if cost else f"impacto {imp:.0f}"

        # Etiqueta en hasta 2 líneas si es larga
        if len(name) > 38:
            sp = name.rfind(" ", 0, 38)
            if sp < 8:
                sp = 38
            lines = [name[:sp], name[sp + 1:]]
            d.add(String(ml, y + 8, lines[0], fontSize=6.5, fillColor=_hex(C_NAVY)))
            d.add(String(ml, y - 1, lines[1][:42], fontSize=6.5, fillColor=_hex(C_NAVY)))
            bar_y = y - bar_h - 4
        else:
            d.add(String(ml, y + 2, name, fontSize=7, fillColor=_hex(C_NAVY)))
            bar_y = y - bar_h
        d.add(Rect(ml, bar_y, bw, bar_h, fillColor=_hex(C_NAVY), strokeWidth=0))
        d.add(String(ml + bw + 6, bar_y + 4, extra, fontSize=7, fillColor=_hex(C_GRAY)))
        y = bar_y - row_gap
    return d


def triangulation_flow(width: float = 460, height: float = 66) -> Drawing | None:
    """Diagrama: DDF → Encuesta → Bayesiano → Veredicto."""
    if not CHARTS_OK:
        return None
    d = Drawing(width, height)
    steps = ["DDF", "Multi-Rater", "δσ + Psico", "Bayesiano", "Veredicto"]
    n = len(steps)
    gap = 6
    box_w = max(48, (width - 20 - gap * (n - 1)) / n)
    fs = 7 if box_w >= 72 else 6
    # Título arriba; cajas centradas en la franja inferior (sin solaparse).
    title_h = 14
    bh = 28
    y = max(6, (height - title_h - bh) / 2)
    d.add(String(10, height - 10, "Modelo de triangulacion ARHIAX Dx",
                 fontSize=7.5, fillColor=_hex(C_GRAY)))
    for i, step in enumerate(steps):
        x = 10 + i * (box_w + gap)
        col = _hex(C_NAVY) if i < n - 1 else _hex(C_ACCENT)
        cyl = y + bh / 2
        d.add(Rect(x, y, box_w, bh, fillColor=_hex(C_PAPER), strokeColor=col, strokeWidth=1))
        d.add(String(x + box_w / 2, cyl - 2.5, step[:16], fontSize=fs,
                     fillColor=_hex(C_NAVY), textAnchor="middle"))
        if i < n - 1:
            ax = x + box_w + 1
            d.add(Line(ax, cyl, ax + gap - 2, cyl,
                       strokeColor=_hex(C_ACCENT), strokeWidth=1))
            d.add(Polygon([ax + gap - 2, cyl, ax, cyl - 2, ax, cyl + 2],
                          fillColor=_hex(C_ACCENT)))
    return d


def qa_gauge(score: float, width: float = 100, height: float = 56) -> Drawing | None:
    if not CHARTS_OK:
        return None
    d = Drawing(width, height)
    cx = width / 2
    col = _hex(C_GREEN) if score >= 85 else (_hex(C_ACCENT) if score >= 70 else _hex(C_RED))
    d.add(Circle(cx, 28, 22, fillColor=_hex(C_PAPER), strokeColor=col, strokeWidth=2))
    d.add(String(cx, 24, f"{score:.0f}", fontSize=14, fillColor=col, textAnchor="middle"))
    d.add(String(cx, 10, "QA", fontSize=7, fillColor=_hex(C_GRAY), textAnchor="middle"))
    return d
