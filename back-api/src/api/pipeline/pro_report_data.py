"""Extrae secciones del reporte Pro desde outputs reales del pipeline — sin placeholders genéricos."""
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from api.pipeline.pro_pipeline_tools import (
    ANALYSIS_TOOLS,
    RESEARCH_DESIGN_TOOLS,
    extract_stage_outputs,
)
from api.pipeline.pro_survey_analytics import compute_live_scoring

SURVEY_EXTRA_TOOLS = ("g09a_preguntas", "g09b_ramificacion", "g09c_validacion", "g10b_psicometria")
_ALL_TOOLS = frozenset(RESEARCH_DESIGN_TOOLS + ANALYSIS_TOOLS + list(SURVEY_EXTRA_TOOLS))

# Estructura oficial del informe — PDF y Markdown comparten esta jerarquía
DOCUMENT_OUTLINE: list[dict] = [
    {
        "part": "I",
        "title": "Contexto y marco metodológico",
        "subtitle": "Perfil del engagement, índice e instrumentación ARHIAX Dx Pro",
        "sections": [
            {"id": "1.0", "title": "Índice general", "guide": None, "prose": None},
            {"id": "1.1", "title": "Contexto del engagement", "guide": "context", "prose": "context"},
            {"id": "1.2", "title": "Metodología ARHIAX Dx Pro", "guide": "methodology", "prose": "methodology"},
        ],
    },
    {
        "part": "II",
        "title": "Diagnóstico cuantitativo",
        "subtitle": "Madurez multi-rater, triangulación y validación psicométrica",
        "sections": [
            {"id": "2.1", "title": "Resumen ejecutivo", "guide": "executive", "prose": "executive"},
            {"id": "2.2", "title": "Triangulación de evidencia", "guide": "triangulation", "prose": "triangulation"},
            {"id": "2.3", "title": "Diagnóstico de madurez", "guide": "maturity", "prose": "maturity"},
            {"id": "2.4", "title": "Psicometría, IRR y bayesiano", "guide": "psychometrics", "prose": "psychometrics"},
        ],
    },
    {
        "part": "III",
        "title": "Fundamento analítico",
        "subtitle": "Cienciometría, cartografía sectorial e hipótesis DDF",
        "sections": [
            {"id": "3.1", "title": "Cienciometría y base científica", "guide": "cienciometria", "prose": "cienciometria"},
            {"id": "3.2", "title": "Cartografía sectorial", "guide": "cartografia", "prose": "cartografia"},
            {"id": "3.3", "title": "Marco DDF — hipótesis e incidentes", "guide": "ddf", "prose": "ddf"},
        ],
    },
    {
        "part": "IV",
        "title": "Proceso y mejoras",
        "subtitle": "AS-IS/TO-BE, brechas, hallazgos y reglas de decisión",
        "sections": [
            {"id": "4.1", "title": "Proceso AS-IS / TO-BE", "guide": "process", "prose": "process"},
            {"id": "4.2", "title": "Matriz AS-IS → TO-BE", "guide": "process", "prose": None},
            {"id": "4.3", "title": "Hallazgos y cuellos de botella", "guide": "findings", "prose": "findings"},
            {"id": "4.4", "title": "Reglas de decisión", "guide": None, "prose": None},
        ],
    },
    {
        "part": "V",
        "title": "Plan de acción y cierre",
        "subtitle": "Roadmap, narrativa ejecutiva y gobernanza PMEL/ATK",
        "sections": [
            {"id": "5.1", "title": "Roadmap de implementación", "guide": "roadmap", "prose": "roadmap"},
            {"id": "5.2", "title": "Narrativa integrada y gobernanza", "guide": None, "prose": "narrative"},
        ],
    },
]

_MISSING = "—"
_STUB_PATTERN = re.compile(
    r"\b(mock|placeholder|lorem ipsum|pendiente de completar|validado del diagn[oó]stico)\b",
    flags=re.IGNORECASE,
)


def _is_stub_text(value: Any) -> bool:
    if value is None:
        return True
    text = str(value).strip()
    if not text or text == _MISSING:
        return True
    if _STUB_PATTERN.search(text):
        return True
    if text.lower() in ("mock", "as-is validado", "hallazgo validado", "narrativa validado."):
        return True
    return len(text) < 25 and text.lower().endswith("validado")


def _derive_executive(case: Any, paquete: list, scoring: dict, g11a: dict, extra: dict, g13: dict) -> str:
    """Tesis ejecutiva solo con datos reales: encuesta, intake, bayesiano o redactor."""
    if g13.get("executive_summary") and not _is_stub_text(g13.get("executive_summary")):
        return str(g13["executive_summary"]).strip()
    parts: list[str] = []
    score = scoring.get("overall_score")
    responses = scoring.get("total_responses")
    if score is not None:
        parts.append(
            f"{case.client_name} registra madurez {score}/100 en «{case.domain}»"
            + (f" con {responses} respuestas multi-rater." if responses else ".")
        )
    symptom = extra.get("symptom")
    if symptom:
        parts.append(str(symptom).strip())
    delta = scoring.get("delta_sigma") or {}
    if delta.get("max_gap") is not None:
        parts.append(
            f"Brecha de percepción δσ={float(delta['max_gap']):.2f} entre roles medidos en encuesta."
        )
    for h in paquete[:2]:
        if isinstance(h, dict) and h.get("enunciado"):
            hid = h.get("hipotesis_id") or h.get("id") or "H"
            parts.append(f"{hid}: {str(h['enunciado'])[:180]}")
    summary = g11a.get("bayesian_summary")
    if summary and not _is_stub_text(summary):
        parts.append(str(summary).strip())
    elif g11a.get("confirmed_hypotheses"):
        confirmed = ", ".join(str(x) for x in g11a["confirmed_hypotheses"][:4])
        parts.append(f"Hipótesis confirmadas bayesianamente: {confirmed}.")
    return " ".join(parts) if parts else _MISSING


def _derive_findings_from_survey(scoring: dict, g11a: dict, paquete: list) -> list[dict]:
    """Hallazgos derivados únicamente de brechas δσ medidas o hipótesis del intake."""
    rows: list[dict] = []
    for gp in (scoring.get("delta_sigma") or {}).get("gap_pairs") or []:
        if not isinstance(gp, dict):
            continue
        finding = gp.get("interpretation") or (
            f"Brecha δσ={gp.get('delta')} en {gp.get('dimension', 'dimensión')}"
        )
        rows.append({
            "id": gp.get("id") or f"GAP-{len(rows) + 1:02d}",
            "finding": finding,
            "evidence": gp.get("roles") or "Encuesta multi-rater",
            "priority": "ALTA" if gp.get("critical") else "MEDIA",
            "dimension": gp.get("dimension"),
        })
    for gap in g11a.get("critical_perception_gaps") or []:
        if not isinstance(gap, dict):
            continue
        rows.append({
            "id": gap.get("hypothesis_id") or f"CPG-{len(rows) + 1:02d}",
            "finding": _txt(gap.get("interpretation") or gap.get("verdict")),
            "evidence": f"δσ={gap.get('delta_sigma', '—')} · {gap.get('roles', '')}",
            "priority": "ALTA",
        })
    for h in paquete[:4]:
        if not isinstance(h, dict) or not h.get("enunciado"):
            continue
        rows.append({
            "id": h.get("hipotesis_id") or h.get("id") or f"H-{len(rows) + 1:02d}",
            "finding": _txt(h.get("enunciado"))[:200],
            "evidence": _txt(h.get("incidente_texto") or h.get("observacion_refutadora"))[:120],
            "priority": h.get("confianza") or "MEDIA",
        })
    return rows


def _hydrate_findings_treatment(
    findings: list, g12: dict, g13: dict, bottlenecks: list
) -> None:
    """Tratamiento solo si el LLM lo vinculó explícitamente a un hallazgo o cuello."""
    if not findings:
        return
    recs = (
        (g12.get("strategic_recommendations") if isinstance(g12, dict) else None)
        or (g13.get("strategic_recommendations") if isinstance(g13, dict) else None)
        or []
    )
    rec_by_finding: dict[str, str] = {}
    for r in recs:
        if not isinstance(r, dict):
            continue
        text = _txt(r.get("recommendation") or r.get("action"), missing="")
        if _is_stub_text(text):
            continue
        for fid in r.get("linked_findings") or []:
            rec_by_finding.setdefault(str(fid), text)
    bott_by_id: dict[str, str] = {}
    for i, b in enumerate(bottlenecks or []):
        if isinstance(b, dict):
            bid = str(b.get("id") or f"CB-{i + 1:02d}")
            bott_by_id[bid] = _txt(b.get("name"))

    for f in findings:
        if not isinstance(f, dict):
            continue
        existing = f.get("treatment") or f.get("recommendation")
        if existing and not _is_stub_text(existing):
            continue
        fid = str(f.get("id") or "")
        treatment = rec_by_finding.get(fid)
        if not treatment:
            linked = f.get("linked_bottleneck")
            rec = next(
                (r for r in recs if isinstance(r, dict) and str(linked) in [str(x) for x in (r.get("linked_bottlenecks") or [])]),
                None,
            )
            if rec:
                treatment = _txt(rec.get("recommendation") or rec.get("action"), missing="")
        if treatment and not _is_stub_text(treatment):
            f["treatment"] = treatment


def _derive_matrix_from_gaps(gaps: list, g08: dict) -> list[dict]:
    """Matriz AS-IS→TO-BE solo desde brechas G05 o opciones TO-BE del LLM."""
    rows: list[dict] = []
    tobe_by_id: dict[str, dict] = {}
    for opt in g08.get("improvement_options") or []:
        if isinstance(opt, dict) and opt.get("id"):
            tobe_by_id[str(opt["id"])] = opt
    for gap in gaps[:8]:
        if not isinstance(gap, dict):
            continue
        to_be = _txt(gap.get("benchmark") or gap.get("to_be"), missing="")
        if not to_be or to_be == _MISSING:
            linked = gap.get("linked_option") or gap.get("option_id")
            if linked and tobe_by_id.get(str(linked)):
                to_be = _txt(tobe_by_id[str(linked)].get("description") or tobe_by_id[str(linked)].get("name"))
        rows.append({
            "component": _txt(gap.get("name") or gap.get("id")),
            "as_is": _txt(gap.get("as_is")),
            "to_be": to_be,
            "impact": _txt(gap.get("estimated_impact") or gap.get("gap_magnitude")),
        })
    return rows


def _derive_decision_rules_from_paquete(paquete: list, hypotheses_g05: list) -> list[dict]:
    """Reglas de decisión desde hipótesis G05 o intake DDF — sin plantillas genéricas."""
    rules: list[dict] = []
    items = hypotheses_g05 or paquete or []
    for h in items[:6]:
        if not isinstance(h, dict):
            continue
        signals = h.get("expected_signals") or {}
        fals = (
            signals.get("falsification_condition")
            or h.get("falsification_condition")
            or h.get("observacion_refutadora")
            or (signals.get("if_false") or {}).get("all_roles")
        )
        rules.append({
            "rule": _txt(h.get("id") or h.get("hipotesis_id")),
            "description": _txt(h.get("hypothesis") or h.get("enunciado")),
            "evidence": _txt(h.get("evidence_needed") or h.get("incidente_texto") or h.get("dato_duro")),
            "falsification": _txt(fals),
        })
    return rules


def _derive_implications(g13: dict, g12: dict, g11a: dict, scoring: dict) -> list[str]:
    """Implicaciones solo desde recomendaciones del LLM o hipótesis confirmadas."""
    items: list[str] = []
    for r in (g13.get("strategic_recommendations") or g12.get("strategic_recommendations") or [])[:6]:
        if isinstance(r, dict):
            text = _txt(r.get("recommendation") or r.get("action") or r.get("implication"), missing="")
            if text and not _is_stub_text(text):
                items.append(text)
        elif isinstance(r, str) and r.strip():
            items.append(r.strip())
    for imp in (g13.get("implications") or g12.get("implications") or [])[:4]:
        if isinstance(imp, str) and imp.strip() and not _is_stub_text(imp):
            items.append(imp.strip())
    confirmed = g11a.get("confirmed_hypotheses") or []
    if confirmed:
        items.append(
            "Hipótesis confirmadas bayesianamente: "
            + ", ".join(str(c) for c in confirmed[:5])
            + "."
        )
    delta = (scoring.get("delta_sigma") or {}).get("max_gap")
    if delta is not None and float(delta) > 2:
        items.append(
            f"Brecha δσ={float(delta):.2f}: alinear medición entre roles antes de ampliar inversión."
        )
    return items


def _derive_asis_activities_from_g06(g06: dict) -> list[dict]:
    """Actividades AS-IS solo desde salida G06."""
    out: list[dict] = []
    for a in g06.get("activities") or []:
        if isinstance(a, dict):
            out.append(dict(a))
    return out


def _format_quantitative_context(extra: dict) -> str:
    """Contexto operativo NO sensible para los prompts (perfil ya declarado en el intake).
    No incluye datos financieros confidenciales (costos, presupuestos, KPIs internos):
    esos no se solicitan al cliente por seguridad y para no sesgar el diagnóstico."""
    lines: list[str] = []
    mapping = (
        ("Sector declarado", extra.get("sector")),
        ("Empleados totales", extra.get("size_org")),
        ("Antigüedad de operación", extra.get("years_operating")),
        ("Áreas/sedes involucradas", extra.get("areas_count")),
        ("Resultado esperado", extra.get("expected_outcome")),
        ("Intentos previos", extra.get("previous_attempts")),
    )
    for label, val in mapping:
        if val not in (None, ""):
            lines.append(f"- {label}: {val}")
    return "\n".join(lines) if lines else "Sin datos operativos adicionales declarados por el cliente."


def _has_survey(case: Any) -> bool:
    sessions = getattr(case, "survey_sessions", None) or []
    return any(getattr(s, "responses", None) for s in sessions)


def validate_report_for_deliverables(data: dict[str, Any], case: Any) -> list[str]:
    """Fail-closed: bloquea PDF si faltan secciones críticas sin fuente real."""
    missing: list[str] = []
    executive = data.get("executive") or {}
    if _is_stub_text(executive.get("thesis")):
        missing.append("Resumen ejecutivo (fusion/g13)")
    if _has_survey(case):
        scoring = data.get("scoring") or {}
        if scoring.get("overall_score") in (None, "", _MISSING):
            missing.append("Scoring global de encuesta (g10a)")
        psych = data.get("psychometrics") or {}
        if psych.get("cronbach") in (None, "", _MISSING) and psych.get("reliability") in (None, "", _MISSING):
            missing.append("α Cronbach (g10b)")
        if psych.get("irr") in (None, "", _MISSING):
            missing.append("IRR Krippendorff (irr_calculator)")
    findings = (data.get("findings") or {}).get("matrix") or []
    if not findings:
        missing.append("Matriz de hallazgos (g12 o brechas δσ)")
    outputs = data.get("pipeline_outputs") or {}
    for tool, label in (
        ("g03_cienciometro", "Cienciometría (g03)"),
        ("g04_cartografo", "Cartografía sectorial (g04)"),
        ("g06_bpmn_architect", "Proceso AS-IS (g06)"),
        ("g07_cuellos", "Cuellos de botella (g07)"),
        ("g08_optimizador", "Optimización TO-BE (g08)"),
        ("g13_redactor", "Narrativa ejecutiva (g13)"),
    ):
        raw = outputs.get(tool)
        if not raw or (isinstance(raw, dict) and raw.get("error")):
            missing.append(label)
    g13 = outputs.get("g13_redactor") if isinstance(outputs.get("g13_redactor"), dict) else {}
    if not g13.get("executive_summary") and _is_stub_text(executive.get("narrative")):
        missing.append("Narrativa integrada (g13)")
    return missing


def _build_engagement_context(case: Any, payload: dict, extra: dict) -> dict:
    return {
        "legal_name": extra.get("legal_name") or case.client_name,
        "nit": extra.get("nit", "—"),
        "sector": extra.get("sector", "—"),
        "city": extra.get("city", "—"),
        "country": extra.get("country", "—"),
        "size_org": extra.get("size_org", "—"),
        "years_operating": extra.get("years_operating", "—"),
        "symptom": extra.get("symptom", "—"),
        "problem_since": extra.get("problem_since", "—"),
        "previous_attempts": extra.get("previous_attempts", "—"),
        "expected_outcome": extra.get("expected_outcome", "—"),
        "deadline": extra.get("deadline", "—"),
        "confidentiality": extra.get("confidentiality", "Confidencial"),
        "contact_name": extra.get("contact_name", "—"),
        "contact_role": extra.get("contact_role", "—"),
        "contact_email": extra.get("contact_email", "—"),
        "contact_phone": extra.get("contact_phone", "—"),
        "grey_sources": payload.get("grey_sources") or [],
        "roles": payload.get("roles") or [],
        "dimensions": payload.get("dimensions") or [],
        "domain": case.domain,
    }


def _section_guides(domain: str) -> dict[str, str]:
    return {
        "executive": (
            "Este resumen integra madurez multi-rater, hipótesis DDF y triangulación bayesiana. "
            "Cada afirmación está anclada a incidentes documentados y señales cuantitativas de la encuesta."
        ),
        "context": (
            "Esta sección presenta el perfil del engagement: sponsor, síntoma reportado, "
            "alcance acordado y fuentes grises aportadas por el cliente."
        ),
        "methodology": (
            "ARHIAX Dx Pro ejecuta 18 agentes especializados en cinco fases. "
            "La metodología combina cienciometría, cartografía sectorial, BPMN, instrumento psicométrico "
            "y actualización bayesiana para evitar diagnósticos basados solo en percepción directiva."
        ),
        "triangulation": (
            "La triangulación cruza tres fuentes independientes: (1) incidentes y observaciones refutadoras del DDF, "
            "(2) respuestas Likert por rol con cálculo de δσ, y (3) veredicto bayesiano posterior. "
            "Una hipótesis solo se confirma cuando convergen las tres."
        ),
        "maturity": (
            "El índice de madurez (0–100) agrega dimensiones estratégicas, de proceso, tecnología y gobernanza. "
            "Scores por rol revelan si la dirección sobreestima capacidades respecto a quien ejecuta en piso."
        ),
        "cienciometria": (
            "La base científica fundamenta las recomendaciones en literatura revisada y benchmarks sectoriales, "
            f"aplicados al dominio «{domain}»."
        ),
        "cartografia": (
            "La cartografía sectorial contextualiza el caso frente a distribuidores similares, "
            "tecnologías típicas y prácticas que han demostrado ROI en escenarios comparables."
        ),
        "ddf": (
            "El marco DDF (Datos Duros + Falsificación) obliga a cada hipótesis a tener incidente anclado "
            "y observación refutadora. Esto evita confirmar narrativas sin evidencia contrastable."
        ),
        "process": (
            "El mapa AS-IS describe el flujo actual con cuellos identificados. "
            "El TO-BE propone estados futuros priorizados por impacto económico y factibilidad de implementación."
        ),
        "findings": (
            "Los hallazgos priorizan acciones por severidad, confianza bayesiana y costo de oportunidad mensual. "
            "Cada fila enlaza síntoma → evidencia → tratamiento recomendado."
        ),
        "roadmap": (
            "El roadmap secuencia intervenciones en ventanas de 30, 90 y 180 días con responsables y KPIs verificables. "
            "Las acciones de corto plazo atacan δσ crítico; las de mediano plazo consolidan integración sistémica."
        ),
        "psychometrics": (
            "La confiabilidad del instrumento (α Cronbach, IRR Krippendorff) valida que las diferencias entre roles "
            "no se deben a ruido del cuestionario sino a brechas reales de percepción organizacional."
        ),
    }


def _split_paragraphs(text: str, *, max_parts: int = 4) -> list[str]:
    """Divide un texto largo real (del LLM) en párrafos, sin inventar contenido."""
    if not text or _is_stub_text(text):
        return []
    raw = str(text).strip()
    parts = [p.strip() for p in re.split(r"\n{2,}|\r\n\r\n", raw) if p.strip()]
    if len(parts) <= 1:
        parts = [p.strip() for p in re.split(r"(?<=[.;])\s+(?=[A-ZÁÉÍÓÚÑ])", raw) if p.strip()]
        merged: list[str] = []
        buf = ""
        for sentence in parts:
            buf = f"{buf} {sentence}".strip()
            if len(buf) >= 320:
                merged.append(buf)
                buf = ""
        if buf:
            merged.append(buf)
        parts = merged or [raw]
    return parts[:max_parts]


def _build_dense_narratives(
    case: Any, extra: dict, paquete: list, g13: dict, g11a: dict
) -> dict[str, list[str]]:
    """Prosa por sección — SOLO contenido real: narrativa del LLM (g13),
    contexto declarado por el usuario e hipótesis del intake. Nada inventado.
    Las secciones sin fuente real quedan vacías (renderizan sus tablas reales)."""
    out: dict[str, list[str]] = {}

    # Contexto: datos declarados por el usuario en el wizard (fuente real = formulario).
    ctx_bits: list[str] = []
    sector = _txt(extra.get("sector"), missing="")
    size_org = _txt(extra.get("size_org"), missing="")
    city = _txt(extra.get("city"), missing="")
    country = _txt(extra.get("country"), missing="")
    loc = ", ".join(x for x in (city, country) if x)
    ident = f"<b>{case.client_name}</b>"
    if sector:
        ident += f", sector {sector}"
    if size_org:
        ident += f", {size_org} colaboradores"
    if loc:
        ident += f", con sede en {loc}"
    ctx_bits.append(f"{ident}.")
    symptom = _txt(extra.get("symptom"), missing="")
    if symptom:
        line = f"Síntoma reportado por el cliente: {symptom}"
        since = _txt(extra.get("problem_since"), missing="")
        if since:
            line += f" (manifiesto desde {since})"
        prev = _txt(extra.get("previous_attempts"), missing="")
        if prev:
            line += f". Intentos previos: {prev}"
        ctx_bits.append(line + ".")
    sponsor = _txt(extra.get("contact_name"), missing="")
    if sponsor:
        srole = _txt(extra.get("contact_role"), missing="")
        outcome = _txt(extra.get("expected_outcome"), missing="")
        deadline = _txt(extra.get("deadline"), missing="")
        sp = f"Sponsor del diagnóstico: {sponsor}"
        if srole:
            sp += f" ({srole})"
        if outcome:
            sp += f". Resultado esperado declarado: {outcome}"
        if deadline:
            sp += f". Plazo acordado: {deadline}"
        ctx_bits.append(sp + ".")
    if ctx_bits:
        out["context"] = ctx_bits

    # Resumen ejecutivo y narrativa: SOLO del redactor LLM (g13).
    exec_summary = g13.get("executive_summary")
    exec_parts = _split_paragraphs(exec_summary, max_parts=3)
    if exec_parts:
        out["executive"] = exec_parts

    narrative = _split_paragraphs(g13.get("full_narrative"), max_parts=4)
    if narrative:
        out["narrative"] = narrative

    # DDF: hipótesis reales aportadas por el usuario en el intake.
    confirmed = str(g11a.get("confirmed_hypotheses") or "")
    hypo_blocks: list[str] = []
    for h in paquete or []:
        if not isinstance(h, dict):
            continue
        hid = h.get("hipotesis_id") or h.get("id") or "H"
        enun = _txt(h.get("enunciado"), missing="")
        if not enun:
            continue
        block = f"<b>{hid}</b> — {enun}"
        refut = _txt(h.get("observacion_refutadora"), missing="")
        if refut:
            block += f" Observación refutadora: {refut}."
        inc = _txt(h.get("incidente_texto"), missing="")
        if inc:
            block += f" Incidente anclado: {inc}."
        conf = _txt(h.get("confianza"), missing="")
        dato = _txt(h.get("dato_duro"), missing="")
        meta_bits = []
        if conf:
            meta_bits.append(f"confianza {conf}")
        if dato:
            meta_bits.append(f"dato duro {dato}")
        if meta_bits:
            block += f" ({'; '.join(meta_bits)})."
        if str(hid).replace("-", "") in confirmed.replace("-", ""):
            block += " Confirmada por la actualización bayesiana."
        hypo_blocks.append(block)
    if hypo_blocks:
        out["ddf"] = hypo_blocks

    return out


def _txt(value: Any, *, missing: str = _MISSING) -> str:
    if value is None:
        return missing
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)[:2000] if value else missing
    text = str(value).strip()
    return text if text else missing


def _as_dict(value: Any) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def _stage_note(tool: str, outputs: dict) -> str | None:
    data = outputs.get(tool)
    if not data:
        return f"*Etapa `{tool}` no ejecutada o sin salida.*"
    if isinstance(data, dict) and data.get("error"):
        return f"*Etapa `{tool}` falló: {data['error']}*"
    return None


def _collect_outputs(case: Any) -> dict[str, Any]:
    stages_out = extract_stage_outputs(case.pipeline_stages)
    payload = case.input_payload or {}
    research = payload.get("research_design") or {}
    fusion = case.fusion_result or {}
    stored = fusion.get("pipeline_outputs") or {}

    merged: dict[str, Any] = {}
    for src in (research, stored, stages_out, payload):
        if not isinstance(src, dict):
            continue
        for k, v in src.items():
            if k in _ALL_TOOLS:
                if v and not (isinstance(v, dict) and v.get("error")):
                    merged[k] = v
            elif k.replace("-", "_") in _ALL_TOOLS:
                merged[k.replace("-", "_")] = v
    return merged


def _triz_from_paquete(paquete: list) -> list[dict]:
    rows = []
    for h in paquete or []:
        if not isinstance(h, dict):
            continue
        enunciado = _txt(h.get("enunciado"), missing="")
        refutadora = _txt(h.get("observacion_refutadora"), missing="")
        if not enunciado:
            continue
        contradiction = (
            f"Si «{enunciado[:120]}» es válida, pero «{refutadora[:120]}» contradice la práctica observada."
            if refutadora
            else enunciado
        )
        rows.append({
            "id": h.get("hipotesis_id") or h.get("id") or f"H-{len(rows)+1:02d}",
            "contradiction": contradiction,
            "enunciado": enunciado,
            "refutadora": refutadora or _MISSING,
            "confianza": h.get("confianza", "MEDIA"),
            "dato_duro": h.get("dato_duro", "—"),
            "incidente": _txt(h.get("incidente_texto")),
        })
    return rows


def _asis_flow(g06: dict) -> list[str]:
    activities = g06.get("activities") or []
    if not activities:
        desc = g06.get("bpmn_description") or g06.get("process_notes")
        if desc:
            return [s.strip() for s in re.split(r"→|->|;", str(desc)) if s.strip()]
        return []
    seq = g06.get("sequence_flow") or []
    if seq:
        order = [seq[0].get("from", "")]
        visited = {order[0]}
        for _ in range(len(seq) + 1):
            nxt = next((e.get("to") for e in seq if e.get("from") == order[-1]), None)
            if not nxt or nxt in visited:
                break
            order.append(nxt)
            visited.add(nxt)
        id_to_name = {a.get("id"): a.get("name", a.get("id")) for a in activities}
        return [_txt(id_to_name.get(aid, aid)) for aid in order if aid]
    return [_txt(a.get("name", a.get("id"))) for a in activities[:20]]


def _tobe_flow(g08: dict, g06: dict) -> list[str]:
    rec = g08.get("recommended_option") or {}
    if isinstance(rec, dict) and rec.get("to_be_process"):
        proc = rec["to_be_process"]
        if isinstance(proc, list):
            return [_txt(x) for x in proc]
        return [s.strip() for s in re.split(r"→|->|;", str(proc)) if s.strip()]
    if isinstance(rec, str) and rec.strip():
        return [s.strip() for s in re.split(r"→|->|\.|;", rec) if s.strip()][:12]
    rec_id = rec.get("id") if isinstance(rec, dict) else None
    for opt in g08.get("improvement_options") or []:
        if isinstance(opt, dict) and opt.get("id") == rec_id:
            desc = opt.get("description") or opt.get("name")
            if desc:
                return [s.strip() for s in re.split(r"→|->|\.|;", str(desc)) if s.strip()][:12]
    roadmap = g08.get("implementation_roadmap") or {}
    phases = []
    for key in ("phase_90_days", "phase_180_days", "phase_365_days", "days_0_90", "days_91_180"):
        val = roadmap.get(key)
        if val:
            phases.append(_txt(val))
    if phases:
        return phases
    return _asis_flow(g06)


def _merge_scoring(g10a: dict, live: dict, fusion_scoring: dict) -> dict:
    out = dict(g10a or {})
    if fusion_scoring:
        for k, v in fusion_scoring.items():
            if v is not None and k not in out:
                out[k] = v
    if live:
        if not out.get("dimension_scores"):
            out["dimension_scores"] = live.get("dimension_scores", [])
        if not out.get("role_scores") or len(out.get("role_scores", {})) < 2:
            out["role_scores"] = live.get("role_scores", out.get("role_scores", {}))
        if not out.get("overall_score"):
            out["overall_score"] = live.get("overall_score")
        if not (out.get("delta_sigma") or {}).get("gap_pairs"):
            out["delta_sigma"] = live.get("delta_sigma", out.get("delta_sigma", {}))
        out["total_responses"] = live.get("total_responses", out.get("total_responses", 0))
        out["scoring_source"] = "live+pipeline"
    return out


def _build_triangulation(
    paquete: list,
    hypotheses_g05: list,
    scoring: dict,
    bayesian: dict,
    g11a_gaps: list,
    g10b: dict,
    irr: dict,
) -> dict:
    """Matriz de triangulación: DDF + encuesta + bayesiano + psicometría."""
    rows = []
    confirmed = {
        (h if isinstance(h, str) else h.get("hypothesis") or h.get("id", "")): True
        for h in (bayesian.get("confirmed_hypotheses") or [])
    }
    rejected = {
        (h if isinstance(h, str) else h.get("hypothesis") or h.get("id", "")): True
        for h in (bayesian.get("rejected_hypotheses") or [])
    }
    delta = scoring.get("delta_sigma") or {}
    max_gap = delta.get("max_gap", 0)

    intake_map = {h.get("hipotesis_id") or h.get("id"): h for h in paquete if isinstance(h, dict)}
    for h in hypotheses_g05[:8]:
        if isinstance(h, str):
            hid, stmt, evid = f"H-{len(rows)+1}", h, "—"
        elif isinstance(h, dict):
            hid = h.get("id") or h.get("hypothesis_id") or f"H-{len(rows)+1}"
            stmt = h.get("hypothesis") or h.get("enunciado") or str(h)
            evid = h.get("evidence_needed") or h.get("falsification_condition") or "—"
        else:
            continue
        intake = intake_map.get(hid) or {}
        stmt_full = intake.get("enunciado") or stmt
        survey_signal = evid
        if max_gap and "delta_sigma" in str(evid).lower():
            survey_signal = f"δσ máx={max_gap:.2f} · {evid}"
        elif max_gap:
            survey_signal = f"δσ máx={max_gap:.2f} entre roles"
        verdict = "Pendiente"
        for key in (hid, stmt, stmt_full):
            if key in confirmed or any(k in confirmed for k in (hid, stmt[:30])):
                verdict = "Confirmada"
                break
            if key in rejected:
                verdict = "Rechazada"
                break
        rows.append({
            "id": hid,
            "ddf": _txt(intake.get("incidente_texto") or intake.get("observacion_refutadora") or stmt_full)[:80],
            "survey": _txt(survey_signal)[:60],
            "bayesian": verdict,
            "psych": f"α={g10b.get('cronbach_alpha_overall', g10b.get('cronbach_alpha', '—'))}",
        })

    for h in paquete:
        if not isinstance(h, dict):
            continue
        hid = h.get("hipotesis_id") or h.get("id")
        if any(r.get("id") == hid for r in rows):
            continue
        rows.append({
            "id": hid or f"INT-{len(rows)+1}",
            "ddf": _txt(h.get("incidente_texto") or h.get("enunciado"))[:80],
            "survey": f"Confianza {h.get('confianza', '—')} · dato {h.get('dato_duro', '—')}",
            "bayesian": "En evaluación",
            "psych": f"IRR α={irr.get('krippendorff_alpha', '—')}",
        })

    for gap in g11a_gaps[:4]:
        if not isinstance(gap, dict):
            continue
        rows.append({
            "id": gap.get("hypothesis_id") or "GAP",
            "ddf": "Brecha de percepción crítica",
            "survey": f"δσ={gap.get('delta_sigma', '—')} · {gap.get('roles', '')}",
            "bayesian": _txt(gap.get("interpretation") or gap.get("verdict"))[:50],
            "psych": "Multi-rater",
        })

    return {
        "rows": rows,
        "max_delta_sigma": max_gap,
        "gap_pairs": delta.get("gap_pairs") or [],
        "critical_gaps": g11a_gaps,
        "model": (
            "Triangulación ARHIAX: (1) hipótesis ancladas a incidentes DDF, "
            "(2) señales cuantitativas multi-rater y δσ, (3) actualización bayesiana, "
            "(4) validación psicométrica α/IRR."
        ),
    }


_PROFILE_KEYS = (
    "legal_name", "nit", "sector", "city", "country", "size_org", "years_operating",
    "symptom", "problem_since", "previous_attempts", "expected_outcome", "deadline",
    "confidentiality", "contact_name", "contact_role", "contact_email", "contact_phone",
    "areas_count",
)


def _hydrate_extra(payload: dict) -> dict:
    """El wizard envía el perfil dentro de `extra`, pero el router lo aplana en la raíz
    de input_payload. Reconstruimos `extra` leyendo de ambos sitios para el reporte."""
    extra = dict(payload.get("extra") or {})
    for key in _PROFILE_KEYS:
        if not extra.get(key) and payload.get(key) not in (None, ""):
            extra[key] = payload[key]
    return extra


def _hydrate_paquete(paquete: list, field_data: dict) -> list:
    """`build_hypothesis_pack` traslada incidente_texto/dato_duro a field_data.
    Los reinyectamos en cada hipótesis para que el reporte tenga la evidencia DDF."""
    if not isinstance(paquete, list):
        return []
    out: list = []
    for h in paquete:
        if not isinstance(h, dict):
            out.append(h)
            continue
        h2 = dict(h)
        hid = str(h.get("hipotesis_id") or h.get("id") or "")
        fd = field_data.get(hid) or {}
        if not h2.get("incidente_texto"):
            incidents = fd.get("corpus_incidentes") or []
            if incidents and isinstance(incidents[0], dict):
                h2["incidente_texto"] = incidents[0].get("texto") or ""
        if not h2.get("dato_duro"):
            hard = fd.get("datos_duros") or []
            if hard and isinstance(hard[0], dict):
                h2["dato_duro"] = hard[0].get("nivel_dato") or ""
        out.append(h2)
    return out


def build_pro_report_data(case: Any) -> dict[str, Any]:
    """Estructura completa para markdown/PDF — solo datos de pipeline o vacío explícito."""
    outputs = _collect_outputs(case)
    payload = case.input_payload or {}
    fusion = case.fusion_result or {}
    live = compute_live_scoring(case)
    g10a_raw = _as_dict(outputs.get("g10a_scoring"))
    scoring = _merge_scoring(g10a_raw, live, fusion.get("scoring") or {})

    g03 = _as_dict(outputs.get("g03_cienciometro"))
    g04 = _as_dict(outputs.get("g04_cartografo"))
    g05 = _as_dict(outputs.get("g05_brechas"))
    g06 = _as_dict(outputs.get("g06_bpmn_architect"))
    g07 = _as_dict(outputs.get("g07_cuellos"))
    g08 = _as_dict(outputs.get("g08_optimizador"))
    bpmn = _as_dict(outputs.get("bpmn_generator"))
    g10b = _as_dict(outputs.get("g10b_psicometria"))
    g11a = _as_dict(outputs.get("g11a_bayesiano"))
    g12 = _as_dict(outputs.get("g12_hallazgos"))
    g13 = _as_dict(outputs.get("g13_redactor"))
    g14 = _as_dict(outputs.get("g14_qa_control"))
    irr = _as_dict(outputs.get("irr_calculator"))
    g11b = _as_dict(outputs.get("g11b_nlp"))

    if g10a_raw.get("scoring_summary"):
        scoring = {**scoring, **g10a_raw["scoring_summary"]}

    paquete = _hydrate_paquete(
        payload.get("paquete_hipotesis") or [], payload.get("field_data") or {}
    )
    triz_rows = _triz_from_paquete(paquete)
    findings = g12.get("findings_matrix") or g12.get("findings") or []
    gaps = g05.get("gaps") or []
    hypotheses_g05 = g05.get("hypotheses") or []
    bottlenecks = g07.get("bottlenecks") or []

    g11a_gaps = g11a.get("critical_perception_gaps") or []
    triangulation = _build_triangulation(paquete, hypotheses_g05, scoring, g11a, g11a_gaps, g10b, irr)

    dim_scores = scoring.get("dimension_scores") or []
    if not dim_scores and isinstance(scoring.get("dimensions"), list):
        dim_scores = scoring["dimensions"]

    extra = _hydrate_extra(payload)

    thesis = (
        fusion.get("executive_thesis")
        or g13.get("executive_summary")
        or (g13.get("full_narrative") or "")[:500]
        or _MISSING
    )
    if _is_stub_text(thesis):
        thesis = _derive_executive(case, paquete, scoring, g11a, extra, g13)

    asis_steps = _asis_flow(g06)
    tobe_steps = _tobe_flow(g08, g06)

    if not findings or all(_is_stub_text(f.get("finding")) for f in findings if isinstance(f, dict)):
        findings = _derive_findings_from_survey(scoring, g11a, paquete)

    if bottlenecks and all(_is_stub_text(b.get("name")) for b in bottlenecks if isinstance(b, dict)):
        bottlenecks = []

    _hydrate_findings_treatment(findings, g12, g13, bottlenecks)

    literature = g03.get("literature_map") or []

    matrix_rows = _derive_matrix_from_gaps(gaps, g08)
    if not matrix_rows:
        for gap in gaps[:8]:
            if not isinstance(gap, dict):
                continue
            matrix_rows.append({
                "component": _txt(gap.get("name") or gap.get("id")),
                "as_is": _txt(gap.get("as_is")),
                "to_be": _txt(gap.get("benchmark")),
                "impact": _txt(gap.get("estimated_impact") or gap.get("gap_magnitude")),
            })

    decision_rules = []
    for h in hypotheses_g05[:6]:
        if not isinstance(h, dict):
            continue
        signals = h.get("expected_signals") or {}
        fals = (
            signals.get("falsification_condition")
            or h.get("falsification_condition")
            or (signals.get("if_false") or {}).get("all_roles")
        )
        decision_rules.append({
            "rule": _txt(h.get("id")),
            "description": _txt(h.get("hypothesis")),
            "evidence": _txt(h.get("evidence_needed") or signals.get("falsification_condition")),
            "falsification": _txt(fals),
        })
    dmn = g08.get("decision_rules") or g13.get("decision_rules") or []
    for r in dmn[:6]:
        if isinstance(r, dict):
            decision_rules.append({
                "rule": _txt(r.get("name") or r.get("id")),
                "description": _txt(r.get("condition") or r.get("description")),
                "evidence": _txt(r.get("action") or r.get("outcome")),
                "falsification": _txt(r.get("falsification") or r.get("falsification_condition")),
            })
    if not decision_rules:
        decision_rules = _derive_decision_rules_from_paquete(paquete, hypotheses_g05)

    roadmap = []
    rm = g08.get("roadmap") or g13.get("roadmap") or {}
    for key, label in (
        ("days_90", "0–90 días"),
        ("days_180", "91–180 días"),
        ("days_365", "181–365 días"),
    ):
        ph = rm.get(key) if isinstance(rm, dict) else None
        if isinstance(ph, dict):
            actions = [a for a in (ph.get("actions") or []) if a]
            theme = _txt(ph.get("theme"), missing="")
            content = "; ".join(_txt(a) for a in actions) if actions else _txt(ph.get("theme"))
            outcome = ph.get("expected_outcome") or ph.get("investment") or ph.get("kpi")
            roadmap.append({
                "phase": label + (f" · {theme}" if theme else ""),
                "content": content,
                "kpi": _txt(outcome),
            })
    if not roadmap:
        impl = g08.get("implementation_roadmap") or {}
        for label, key in (
            ("0–90 días", "phase_90_days"),
            ("91–180 días", "phase_180_days"),
            ("181–365 días", "phase_365_days"),
        ):
            if impl.get(key):
                roadmap.append({"phase": label, "content": _txt(impl[key]), "kpi": _MISSING})

    next_steps_list: list[str] = []
    for step in (g13.get("next_steps") or [])[:6]:
        if isinstance(step, str) and step.strip():
            next_steps_list.append(step.strip())
        elif isinstance(step, dict):
            txt = _txt(step.get("action") or step.get("content") or step.get("step"), missing="")
            if txt:
                next_steps_list.append(txt)

    tobe_options = g08.get("improvement_options") or []
    asis_activities = _derive_asis_activities_from_g06(g06)

    cart_data = {
        "industry_cases": g04.get("industry_cases") or [],
        "best_practices": g04.get("best_practices") or [],
        "sector_process": g04.get("sector_standard_process") or {},
        "technologies": g04.get("typical_technologies") or [],
        "benchmarks": g04.get("benchmarks") or [],
        "patents_note": _txt(g04.get("patent_landscape") or g04.get("patentometria"), missing=""),
        "note": _stage_note("g04_cartografo", outputs) if not g04.get("industry_cases") else None,
    }

    total_loss = g07.get("total_opportunity_loss_usd_month")
    if not total_loss and bottlenecks:
        total_loss = sum(
            int(b.get("estimated_cost_usd_month", 0) or 0)
            for b in bottlenecks
            if isinstance(b, dict)
        )

    engagement = _build_engagement_context(case, payload, extra)
    guides = _section_guides(case.domain or "")
    implications = _derive_implications(g13, g12, g11a, scoring)
    narrative = g13.get("full_narrative") if g13.get("full_narrative") and not _is_stub_text(g13.get("full_narrative")) else _MISSING

    dense_narratives = _build_dense_narratives(case, extra, paquete, g13, g11a)

    recommended_next = fusion.get("recommended_next_step")
    if not recommended_next and next_steps_list:
        recommended_next = next_steps_list[0]
    elif not recommended_next:
        rec = g08.get("recommended_option")
        if isinstance(rec, dict):
            recommended_next = _txt(rec.get("name") or rec.get("description"), missing="")
        elif rec:
            recommended_next = _txt(rec, missing="")

    stage_outcomes = fusion.get("stage_outcomes") or {}
    if not stage_outcomes:
        for st in case.pipeline_stages or []:
            if isinstance(st, dict) and st.get("tool_name"):
                stage_outcomes[st["tool_name"]] = {
                    "outcome": "PERMIT" if st.get("status") == "completed" else st.get("status", "—").upper(),
                    "artifact_type": st["tool_name"],
                }

    return {
        "meta": {
            "client_name": case.client_name,
            "domain": case.domain,
            "engagement_id": case.engagement_id,
            "case_status": case.case_status,
            "date": datetime.now().strftime("%d/%m/%Y"),
            "trace_id": case.trace_id,
            "case_id": case.case_id,
        },
        "executive": {
            "thesis": thesis,
            "overall_score": scoring.get("overall_score", fusion.get("scoring", {}).get("overall_score", _MISSING)),
            "total_responses": scoring.get("total_responses", fusion.get("response_count", 0)),
            "hypotheses": fusion.get("hypotheses") or [],
            "risk_signals": fusion.get("risk_signals") or [],
            "next_step": recommended_next or _MISSING,
            "implications": implications,
            "narrative": narrative,
        },
        "engagement": engagement,
        "section_guides": guides,
        "dense_narratives": dense_narratives,
        "outline": DOCUMENT_OUTLINE,
        "maturity": {
            "dimension_scores": dim_scores,
            "note": _stage_note("g10a_scoring", outputs),
        },
        "cienciometria": {
            "literature": literature,
            "consensus": _txt(g03.get("scientific_consensus"), missing=""),
            "methodologies": g03.get("validated_methodologies") or [],
            "causal_factors": g03.get("causal_factors_documented") or [],
            "research_gaps": _txt(g03.get("research_gaps"), missing=""),
            "note": _stage_note("g03_cienciometro", outputs) if not literature else None,
        },
        "cartografia": cart_data,
        "triz_ddf": {
            "hypotheses_intake": triz_rows,
            "gaps": gaps,
            "hypotheses_g05": hypotheses_g05,
            "note": None if (triz_rows or hypotheses_g05) else _stage_note("g05_brechas", outputs),
        },
        "asis": {
            "process_name": _txt(g06.get("process_name"), missing="") or f"Proceso core — {case.domain}",
            "steps": asis_steps,
            "activities": asis_activities,
            "bottleneck_ids": g06.get("identified_bottlenecks") or [],
            "critical_path": g06.get("critical_path") or [],
            "notes": _txt(g06.get("process_notes"), missing=""),
            "bpmn_xml": bpmn.get("bpmn_xml") or bpmn.get("xml") or "",
            "note": _stage_note("g06_bpmn_architect", outputs) if not asis_steps else None,
        },
        "findings": {
            "matrix": findings,
            "from_g12_note": _stage_note("g12_hallazgos", outputs) if not findings else None,
        },
        "tobe": {
            "steps": tobe_steps,
            "options": tobe_options,
            "recommended": g08.get("recommended_option") or {},
            "note": _stage_note("g08_optimizador", outputs) if not tobe_steps and not g08.get("improvement_options") else None,
        },
        "bottlenecks": {
            "items": bottlenecks,
            "total_loss_usd": total_loss,
            "note": _stage_note("g07_cuellos", outputs) if not bottlenecks else None,
        },
        "matrix_asis_tobe": matrix_rows,
        "decision_rules": decision_rules,
        "roadmap": roadmap,
        "next_steps": next_steps_list,
        "psychometrics": {
            "cronbach": (
                g10b.get("cronbach_alpha_overall")
                or g10b.get("cronbach_alpha")
                or g10b.get("reliability")
            ),
            "cronbach_by_dimension": g10b.get("cronbach_by_dimension") or {},
            "internal_consistency": _txt(g10b.get("internal_consistency"), missing=""),
            "instrument_reliability": _txt(g10b.get("instrument_reliability"), missing=""),
            "items": g10b.get("item_analysis") or g10b.get("dimensions") or [],
            "irr": irr.get("krippendorff_alpha") or irr.get("overall_alpha"),
            "irr_by_dimension": irr.get("by_dimension") or irr.get("dimension_irr") or [],
            "note": _stage_note("g10b_psicometria", outputs),
        },
        "bayesian": {
            "confirmed": g11a.get("confirmed_hypotheses") or [],
            "rejected": g11a.get("rejected_hypotheses") or [],
            "summary": g11a.get("bayesian_summary") or "",
            "note": _stage_note("g11a_bayesiano", outputs),
        },
        "triangulation": triangulation,
        "scoring": scoring,
        "nlp": {
            "themes": g11b.get("themes") or [],
            "summary": g11b.get("nlp_summary") or "",
            "sentiment_by_role": g11b.get("sentiment_by_role") or {},
        },
        "methodology": {
            "pipeline_agents": 18,
            "phases": [
                ("Investigación", "G01–G05: mandato, benchmarks, cienciometría, cartografía, brechas"),
                ("Diseño proceso", "G06–G08: BPMN AS-IS, cuellos, TO-BE con ROI"),
                ("Instrumento", "G09a–c: preguntas multi-rater, ramificación, validación IRR"),
                ("Análisis", "G10–G11: scoring, psicometría, bayesiano, NLP"),
                ("Síntesis", "G12–G14: hallazgos, narrativa ejecutiva, QA ≥85"),
            ],
            "evaluates": [
                "Madurez por dimensión y rol (Likert 1–5 corregido)",
                "Brechas de percepción δσ entre Estratégico/Táctico/Operativo",
                "Hipótesis falseables del intake DDF vs evidencia empírica",
                "Cuellos de botella y pérdida USD/mes (G07)",
                "Fiabilidad α Cronbach e IRR Krippendorff",
                "Consenso científico y praxis sectorial (G03–G04)",
            ],
            "perception_gaps": g13.get("perception_gaps") or "",
        },
        "governance": {
            "stage_outcomes": stage_outcomes,
            "qa_score": g14.get("qa_score") or (case.report_result or {}).get("qa_score"),
            "evidence": case.evidence_entries or [],
        },
        "report_sections": (case.report_result or {}).get("sections") or [],
        "pipeline_outputs": outputs,
    }
