"""Validación de coherencia: el output del pipeline debe anclarse al caso real."""
from __future__ import annotations

import json
import re
import unicodedata
from typing import Any

from api.pipeline.llm_guard import PipelineStageFailureError

_STOPWORDS = frozenset(
    """
    el la los las un una unos unas de del al en y o que con por para sin sobre este esta
    estos estas como mas muy tan ser estar tiene tienen desde cuando donde cual cuales
    """.split()
)

# Temas que suelen ser alucinación si no aparecen en el intake.
_DRIFT_RULES: list[dict[str, Any]] = [
    {
        "id": "hr_onboarding",
        "output_patterns": [
            r"\bonboarding\b",
            r"integraci[oó]n de nuevos",
            r"empleados de nuevo ingreso",
            r"time-to-productivity",
        ],
        "anchor_patterns": [
            r"\bonboarding\b",
            r"nuevo ingreso",
            r"contrataci[oó]n",
            r"recursos humanos",
            r"\brrhh\b",
        ],
    },
    {
        "id": "vacation",
        "output_patterns": [
            r"\bvacaciones\b",
            r"solicitud de vacaciones",
            r"\bvacation\b",
            r"d[ií]as de vacaciones",
        ],
        "anchor_patterns": [r"\bvacaciones\b", r"permiso laboral", r"ausencia"],
    },
    {
        "id": "credit",
        "output_patterns": [
            r"solicitud(es)? de cr[eé]dito",
            r"aprobaci[oó]n de (solicitudes de )?cr[eé]dito",
            r"\bcredit application\b",
            r"formularios? de solicitud de cr[eé]dito",
        ],
        "anchor_patterns": [
            r"\bcr[eé]dito\b",
            r"financiaci[oó]n",
            r"pr[eé]stamo",
            r"cartera",
        ],
    },
]

_COHERENCE_TOOLS = frozenset({
    "g03_cienciometro",
    "g04_cartografo",
    "g06_bpmn_architect",
    "g12_hallazgos",
    "g13_redactor",
})


def _normalize(text: str) -> str:
    t = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def _tokens(text: str, *, min_len: int = 5) -> set[str]:
    words = re.findall(r"[a-záéíóúñ]{3,}", _normalize(text))
    return {w for w in words if len(w) >= min_len and w not in _STOPWORDS}


def derive_subprocess(symptom: str, domain: str, expected_outcome: str = "") -> str:
    """Subproceso concreto a partir del síntoma — evita usar solo el área diagnóstica."""
    blob = (symptom or "").strip()
    if not blob:
        return domain or "proceso operativo"
    m = re.search(
        r"(?:lentitud|demora|retraso|ineficiencia|problema|dificultad)\s+en\s+(.{8,120})",
        _normalize(blob),
        flags=re.IGNORECASE,
    )
    if m:
        chunk = m.group(1).split(".")[0].strip(" ,;")
        if len(chunk) >= 8:
            return chunk[:120]
    if "," in blob:
        parts = [p.strip() for p in blob.split(",") if len(p.strip()) >= 6]
        if parts:
            return "; ".join(parts[:4])[:120]
    return blob[:120] if len(blob) >= 12 else (domain or "proceso operativo")


def build_case_anchors(context: dict[str, Any]) -> dict[str, Any]:
    """Texto ancla y tokens para validar que el LLM no se desvíe."""
    symptom = str(context.get("objective") or "")
    sector = str(context.get("sector") or "")
    domain = str(context.get("domain") or context.get("diagnostic_area") or "")
    subprocess = str(context.get("subprocess") or "")
    expected = str(context.get("expected_outcome") or "")
    phenomenon_named = str(context.get("phenomenon_named") or "")

    incidents: list[str] = []
    for inc in context.get("corpus_incidentes") or []:
        if inc:
            incidents.append(str(inc))
    for h in context.get("paquete_hipotesis") or []:
        if isinstance(h, dict):
            for key in ("incidente_texto", "enunciado", "observacion_refutadora"):
                val = h.get(key)
                if val:
                    incidents.append(str(val))

    anchor_blob = " ".join(
        x for x in (symptom, sector, domain, subprocess, expected, phenomenon_named, *incidents) if x
    )
    tokens = _tokens(anchor_blob)

    summary_parts = [f"Síntoma: {symptom[:200]}"]
    if phenomenon_named:
        summary_parts.append(f"Fenómeno nombrado: {phenomenon_named}")
    if sector:
        summary_parts.append(f"Sector económico: {sector}")
    if domain:
        summary_parts.append(f"Área diagnóstica: {domain}")
    if subprocess:
        summary_parts.append(f"Subproceso: {subprocess}")
    if incidents:
        summary_parts.append(f"Incidente DDF: {incidents[0][:160]}")

    return {
        "symptom": symptom,
        "sector": sector,
        "domain": domain,
        "subprocess": subprocess,
        "expected_outcome": expected,
        "phenomenon_named": phenomenon_named,
        "incidents": incidents,
        "anchor_blob": anchor_blob,
        "tokens": sorted(tokens),
        "summary": " | ".join(summary_parts),
    }


def _output_text(output: Any) -> str:
    try:
        return _normalize(json.dumps(output, ensure_ascii=False))
    except (TypeError, ValueError):
        return _normalize(str(output))


def _check_drift(anchors: dict[str, Any], text: str) -> list[str]:
    issues: list[str] = []
    anchor_blob = anchors.get("anchor_blob") or ""
    for rule in _DRIFT_RULES:
        for pat in rule["output_patterns"]:
            if not re.search(pat, text, flags=re.IGNORECASE):
                continue
            allowed = any(
                re.search(ap, anchor_blob, flags=re.IGNORECASE)
                for ap in rule["anchor_patterns"]
            )
            if not allowed:
                issues.append(
                    f"contenido ajeno al caso ({rule['id']}): el intake no menciona este tema"
                )
                break
    return issues


def _check_anchor_overlap(anchors: dict[str, Any], text: str, *, min_hits: int = 2) -> list[str]:
    raw_tokens = anchors.get("tokens") or ()
    tokens = raw_tokens if isinstance(raw_tokens, set) else set(raw_tokens)
    if len(tokens) < 2:
        return []
    hits = sum(1 for t in tokens if t in text)
    if hits < min_hits:
        return [
            f"poca relación con el síntoma del cliente ({hits}/{min_hits} términos clave)"
        ]
    return []


def _check_g06_process(anchors: dict[str, Any], output: dict) -> list[str]:
    issues: list[str] = []
    name = str(output.get("process_name") or "")
    activities = output.get("activities") or []
    act_text = " ".join(
        str(a.get("name") or "") for a in activities if isinstance(a, dict)
    )
    blob = _normalize(f"{name} {act_text}")
    issues.extend(_check_drift(anchors, blob))
    issues.extend(_check_anchor_overlap(anchors, blob, min_hits=2))
    return issues


def _check_g04_cartography(anchors: dict[str, Any], output: dict) -> list[str]:
    parts: list[str] = []
    for case in output.get("industry_cases") or []:
        if isinstance(case, dict):
            parts.extend(
                str(case.get(k) or "")
                for k in ("problem", "solution", "result", "company_type")
            )
    sp = output.get("sector_standard_process") or {}
    if isinstance(sp, dict):
        parts.append(str(sp.get("description") or ""))
    blob = _normalize(" ".join(parts))
    issues = _check_drift(anchors, blob)
    issues.extend(_check_anchor_overlap(anchors, blob, min_hits=2))
    return issues


def coherence_issues(tool_name: str, output: Any, context: dict[str, Any]) -> list[str]:
    if tool_name not in _COHERENCE_TOOLS or not isinstance(output, dict):
        return []
    if output.get("error"):
        return [str(output["error"])]

    anchors = context.get("case_anchors") or build_case_anchors(context)
    text = _output_text(output)

    issues: list[str] = []
    issues.extend(_check_drift(anchors, text))

    if tool_name == "g06_bpmn_architect":
        issues.extend(_check_g06_process(anchors, output))
    elif tool_name == "g04_cartografo":
        issues.extend(_check_g04_cartography(anchors, output))
    elif tool_name in ("g03_cienciometro", "g12_hallazgos", "g13_redactor"):
        issues.extend(_check_anchor_overlap(anchors, text, min_hits=2))

    # G03 debe estar en español si el caso está en español
    if tool_name == "g03_cienciometro":
        consensus = str(output.get("scientific_consensus") or "")
        if consensus and len(re.findall(r"[a-zA-Z]", consensus)) > 40:
            es_markers = len(re.findall(r"\b(de|la|el|en|y|que|los|las)\b", _normalize(consensus)))
            if es_markers < 3:
                issues.append("cienciometría en idioma no alineado con el caso (esperado español)")

    return issues


def validate_output_coherence(tool_name: str, output: Any, context: dict[str, Any]) -> None:
    """Fail-closed si el output del agente no está anclado al caso."""
    if isinstance(output, dict) and output.get("_trusted_fallback"):
        return
    issues = coherence_issues(tool_name, output, context)
    if issues:
        detail = "; ".join(dict.fromkeys(issues))
        raise PipelineStageFailureError(
            tool_name,
            f"coherencia con el caso: {detail}",
        )
