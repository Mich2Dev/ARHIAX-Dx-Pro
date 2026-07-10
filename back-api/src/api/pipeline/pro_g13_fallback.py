"""Narrativa ejecutiva determinística cuando G13 (Gemini) no devuelve JSON válido."""
from __future__ import annotations

import json
from typing import Any


def coerce_tool_dict(value: Any) -> dict[str, Any]:
    """Normaliza output de etapa (dict, JSON string o envoltorio)."""
    if isinstance(value, dict):
        if value.get("error"):
            return {}
        inner = value.get("output")
        if isinstance(inner, dict) and inner:
            return inner
        if set(value.keys()) == {"raw_output"}:
            return {}
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def build_g13_fallback_minimal(context: dict[str, Any]) -> dict[str, Any]:
    """G13 mínimo desde intake + cuellos de botella si G12 no está disponible."""
    org = str(context.get("organization_name") or "La organización")
    subprocess = str(context.get("subprocess") or context.get("diagnostic_area") or "el proceso")
    symptom = str(context.get("objective") or "")
    phenomenon = str(context.get("phenomenon_named") or "")
    g07 = coerce_tool_dict(context.get("g07_cuellos"))
    total_loss = g07.get("total_opportunity_loss_usd_month")

    exec_para = f"En {org}, el diagnóstico de «{subprocess}» confirma ineficiencias operativas"
    if phenomenon:
        exec_para += f" asociadas al fenómeno «{phenomenon}»"
    if total_loss:
        exec_para += f", con pérdida estimada de USD {total_loss}/mes"
    exec_para += "."

    finding_text = symptom[:280] if symptom else f"Brechas de madurez en {subprocess}"
    return {
        "executive_summary": exec_para,
        "context": str((context.get("case_anchors") or {}).get("summary") or ""),
        "main_findings": [{
            "rank": 1,
            "finding": finding_text,
            "evidence": "Intake del caso y análisis de cuellos de botella (G07)",
            "impact": f"USD {total_loss}/mes estimados" if total_loss else "Alto impacto operativo",
        }],
        "perception_gaps": "Evaluación con perspectiva única del decisor.",
        "bottlenecks_summary": (
            f"Pérdida de oportunidad estimada: USD {total_loss}/mes."
            if total_loss
            else "Retrabajo y falta de reutilización de información histórica."
        ),
        "strategic_recommendations": [{
            "priority": 1,
            "recommendation": f"Automatizar y estandarizar {subprocess}",
            "rationale": "Reduce tiempo de ciclo y dependencia de memoria individual",
            "expected_roi": "Por cuantificar en fase de implementación",
        }],
        "roadmap": {
            "days_90": {
                "theme": "Quick wins",
                "actions": ["Plantillas y APUs reutilizables", "Repositorio único de obras"],
                "expected_outcome": "Menos retrabajo",
                "investment": "Bajo",
            },
        },
        "next_steps": [
            "Validar hallazgos con dirección",
            "Definir piloto de automatización",
        ],
        "full_narrative": exec_para + "\n\n" + finding_text,
        "_fallback_minimal": True,
        "_trusted_fallback": True,
    }


def build_g13_fallback_from_g12(g12: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Construye un G13 mínimo pero usable a partir de hallazgos ya validados (G12)."""
    org = str(context.get("organization_name") or "La organización")
    subprocess = str(context.get("subprocess") or context.get("diagnostic_area") or "el proceso")
    sector = str(context.get("sector") or "")
    phenomenon = str(context.get("phenomenon_named") or "")

    findings = [f for f in (g12.get("findings_matrix") or []) if isinstance(f, dict)]
    recs = [r for r in (g12.get("strategic_recommendations") or []) if isinstance(r, dict)]
    g07 = context.get("g07_cuellos") if isinstance(context.get("g07_cuellos"), dict) else {}
    total_loss = g07.get("total_opportunity_loss_usd_month")

    main_findings: list[dict[str, Any]] = []
    for i, f in enumerate(findings[:3], 1):
        evidence = f.get("evidence") or []
        ev_text = "; ".join(str(e) for e in evidence)[:240] if evidence else str(f.get("finding") or "")
        main_findings.append({
            "rank": i,
            "finding": str(f.get("finding") or f"Hallazgo {i} en {subprocess}"),
            "evidence": ev_text,
            "impact": f"Prioridad {f.get('priority', 'ALTA')} · impacto {f.get('impact_score', '—')}/10",
        })

    strategic_recommendations: list[dict[str, Any]] = []
    for i, r in enumerate(recs[:3], 1):
        strategic_recommendations.append({
            "priority": i,
            "recommendation": str(r.get("recommendation") or f"Mejora {i} en {subprocess}"),
            "rationale": str(r.get("timeframe") or r.get("investment_level") or "Corto plazo"),
            "expected_roi": str(r.get("expected_impact") or "Por cuantificar"),
        })

    exec_para = str(g12.get("executive_summary_findings") or "").strip()
    if not exec_para:
        parts = [f"En {org}, el diagnóstico del subproceso «{subprocess}»"]
        if sector:
            parts.append(f"en el sector {sector}")
        if phenomenon:
            parts.append(f"confirma el fenómeno «{phenomenon}»")
        if total_loss:
            parts.append(f"con pérdida de oportunidad estimada de USD {total_loss}/mes")
        exec_para = ", ".join(parts) + "."

    loss_line = (
        f"La pérdida de oportunidad total estimada es USD {total_loss}/mes."
        if total_loss
        else "Los cuellos de botella concentran tiempo de ingeniería en retrabajo y búsqueda manual de información."
    )

    narrative_parts = [exec_para]
    for f in findings[:2]:
        narrative_parts.append(str(f.get("finding") or ""))
    if strategic_recommendations:
        narrative_parts.append(
            f"La prioridad inmediata es: {strategic_recommendations[0]['recommendation']}."
        )
    full_narrative = "\n\n".join(p for p in narrative_parts if p.strip())

    return {
        "executive_summary": exec_para[:600],
        "context": str((context.get("case_anchors") or {}).get("summary") or ""),
        "main_findings": main_findings,
        "perception_gaps": (
            "Perspectiva única del decisor (encuesta single-rater); "
            "no se detectaron brechas multi-nivel en este ciclo."
        ),
        "bottlenecks_summary": loss_line,
        "strategic_recommendations": strategic_recommendations,
        "roadmap": {
            "days_90": {
                "theme": "Estabilización y quick wins",
                "actions": [
                    f"Estandarizar plantillas reutilizables para {subprocess}",
                    "Centralizar histórico de obras y APUs",
                ],
                "expected_outcome": "Reducir retrabajo en cotización y liquidación",
                "investment": "Bajo",
            },
            "days_180": {
                "theme": "Automatización asistida",
                "actions": ["Pilotar flujo agéntico de cotización", "Trazabilidad de requisiciones"],
                "expected_outcome": "Menos dependencia de WhatsApp y hojas sueltas",
                "investment": "Medio",
            },
            "days_365": {
                "theme": "Memoria operacional",
                "actions": ["Memoria por equipo instalado", "KPIs de ciclo de cotización"],
                "expected_outcome": "Operación predecible y escalable",
                "investment": "Medio-Alto",
            },
        },
        "next_steps": [
            "Validar hallazgos con dirección en sesión de 60 minutos",
            "Priorizar piloto en cotización de tiendas repetitivas",
            "Definir fuentes de datos semilla (APUs, planos, liquidaciones previas)",
        ],
        "full_narrative": full_narrative[:4000],
        "_fallback_from_g12": True,
        "_trusted_fallback": True,
    }
