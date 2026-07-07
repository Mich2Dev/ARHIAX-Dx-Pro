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
    items = [(k, (v.get("score", 0) if isinstance(v, dict) else float(v or 0))) for k, v in role_scores.items()]
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


def delta_sigma_bars(gap_pairs: list, width: float = 460, height: float = 120) -> Drawing | None:
    if not CHARTS_OK or not gap_pairs:
        return None
    d = Drawing(width, height)
    d.add(Rect(0, 0, width, height, fillColor=_hex(C_PAPER), strokeColor=_hex(C_BORDER), strokeWidth=0.5))
    items = gap_pairs[:6]
    bar_h = 14
    y = height - 18
    for g in items:
        if not isinstance(g, dict):
            continue
        delta = float(g.get("delta", 0) or 0)
        label = f"{g.get('roles', '')} · {g.get('dimension', '')}"[:38]
        bw = min(width - 120, delta / 3.5 * (width - 120))
        col = _hex(C_RED) if g.get("critical") or delta > 2 else _hex(C_ACCENT)
        d.add(String(6, y - 2, label, fontSize=7.5, fillColor=_hex(C_NAVY)))
        d.add(Rect(6, y - bar_h - 4, max(bw, 4), bar_h, fillColor=col, strokeWidth=0))
        d.add(String(6 + max(bw, 4) + 4, y - bar_h, f"δσ={delta:.2f}", fontSize=8, fillColor=_hex(C_NAVY)))
        y -= bar_h + 10
        if y < 10:
            break
    d.add(Line(width - 70, 8, width - 8, 8, strokeColor=_hex(C_RED), strokeWidth=1))
    d.add(String(width - 70, 12, "umbral 2.0", fontSize=6, fillColor=_hex(C_RED)))
    return d


def bottleneck_chart(bottlenecks: list, width: float = 460, height: float = 110) -> Drawing | None:
    if not CHARTS_OK or not bottlenecks:
        return None
    d = Drawing(width, height)
    d.add(Rect(0, 0, width, height, fillColor=_hex(C_PAPER), strokeColor=_hex(C_BORDER), strokeWidth=0.5))
    items = bottlenecks[:5]
    bar_h = 16
    y = height - 20
    max_imp = max(float(b.get("impact_score", 5) or 5) for b in items if isinstance(b, dict)) or 10
    for b in items:
        if not isinstance(b, dict):
            continue
        imp = float(b.get("impact_score", 5) or 5)
        name = str(b.get("name", "Cuello"))[:32]
        bw = (imp / max_imp) * (width - 100)
        d.add(String(6, y - 2, name, fontSize=6.5, fillColor=_hex(C_NAVY)))
        d.add(Rect(6, y - bar_h - 4, max(bw, 6), bar_h, fillColor=_hex(C_NAVY), strokeWidth=0))
        cost = b.get("estimated_cost_usd_month")
        extra = f" ${cost}/mes" if cost else f" impacto {imp:.0f}"
        d.add(String(6 + max(bw, 6) + 4, y - bar_h, extra, fontSize=6.5, fillColor=_hex(C_GRAY)))
        y -= bar_h + 8
        if y < 8:
            break
    return d


def triangulation_flow(width: float = 460, height: float = 72) -> Drawing | None:
    """Diagrama: DDF → Encuesta → Bayesiano → Veredicto."""
    if not CHARTS_OK:
        return None
    d = Drawing(width, height)
    steps = ["DDF", "Multi-Rater", "δσ + Psico", "Bayesiano", "Veredicto"]
    n = len(steps)
    gap = 5
    box_w = max(48, (width - 20 - gap * (n - 1)) / n)
    y = 20
    bh = 32
    fs = 6 if box_w >= 72 else 5.5
    for i, step in enumerate(steps):
        x = 10 + i * (box_w + gap)
        col = _hex(C_NAVY) if i < n - 1 else _hex(C_ACCENT)
        d.add(Rect(x, y, box_w, bh, fillColor=_hex(C_PAPER), strokeColor=col, strokeWidth=1))
        d.add(String(x + box_w / 2, y + bh / 2 - 2, step[:16], fontSize=fs,
                     fillColor=_hex(C_NAVY), textAnchor="middle"))
        if i < n - 1:
            ax = x + box_w + 1
            d.add(Line(ax, y + bh / 2, ax + gap - 2, y + bh / 2,
                       strokeColor=_hex(C_ACCENT), strokeWidth=1))
            d.add(Polygon([ax + gap - 2, y + bh / 2, ax, y + bh / 2 - 2, ax, y + bh / 2 + 2],
                          fillColor=_hex(C_ACCENT)))
    d.add(String(10, height - 8, "Modelo de triangulacion ARHIAX Dx", fontSize=7, fillColor=_hex(C_GRAY)))
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
