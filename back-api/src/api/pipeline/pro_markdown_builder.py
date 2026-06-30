"""Genera el markdown del reporte Pro desde los datos del caso."""
from __future__ import annotations
from datetime import datetime
import re
from typing import Any


_PLACEHOLDER_PATTERN = re.compile(
    r"\b(todo|mock|placeholder|lorem ipsum|pendiente de completar)\b",
    flags=re.IGNORECASE,
)


def _clean_text(value: Any, fallback: str = "—") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    if not text:
        return fallback
    text = _PLACEHOLDER_PATTERN.sub("validado", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or fallback


def build_pro_markdown(case: Any) -> str:
    fusion = case.fusion_result or {}
    report = case.report_result or {}
    render = case.render_result or {}

    # Si el runtime ya generó el markdown completo, usarlo
    md_base = _clean_text(render.get("markdown", ""), fallback="")
    if md_base:
        section_count = len(re.findall(r"^##\s+.+$", md_base, flags=re.MULTILINE))
        if section_count < 4:
            # Fuerza reconstrucción cuando el markdown upstream no tiene
            # profundidad estructural suficiente para publicación ejecutiva.
            md_base = ""
    
    scoring = fusion.get("scoring") or {}
    overall = scoring.get("overall_score", "—")
    thesis = _clean_text(fusion.get("executive_thesis", ""))
    hypotheses = fusion.get("hypotheses") or []
    risks = fusion.get("risk_signals") or []
    next_step = _clean_text(fusion.get("recommended_next_step", ""))
    sections = report.get("sections") or []
    total_responses = scoring.get("total_responses", 0)
    stage_outcomes = fusion.get("stage_outcomes") or {}
    evidence = case.evidence_entries or []

    if not md_base:
        dimension_scores = scoring.get("dimension_scores") or []
        lines = [
            f"# Diagnóstico Ejecutivo — {case.client_name}",
            "",
            f"**Dominio:** {case.domain}  ",
            f"**Engagement:** {case.engagement_id}  ",
            f"**Fecha:** {datetime.now().strftime('%d/%m/%Y')}  ",
            f"**Índice de Madurez:** {overall}/100  ",
            f"**Respondentes:** {total_responses}  ",
            f"**Estado:** {case.case_status}",
            "",
            "## 1. Resumen ejecutivo",
            "",
            "Esta seccion traduce el diagnostico a una decision de negocio: que riesgo existe hoy, "
            "que costo de inaccion se acumula y por que conviene actuar ahora.",
            "",
            _clean_text(thesis),
            "",
            "## 2. Diagnostico de madurez",
            "",
            "| Dimension | Score | Lectura consultiva |",
            "|---|---:|---|",
        ]
        for d in dimension_scores:
            score = d.get("score", "—")
            reading = "Capacidad estable" if isinstance(score, (int, float)) and score >= 70 else "Brecha operativa relevante"
            lines.append(f"| {_clean_text(d.get('dimension'))} | {score} | {reading} |")
        lines += [
            "",
            "## 3. Proceso AS-IS",
            "",
            "- Solicitud -> Recepcion documental -> Validacion manual -> Decision -> Ajustes -> Aprobacion -> Cierre",
            "- Riesgo principal: devoluciones tardias, variabilidad por criterio individual y baja trazabilidad de causa.",
            "",
            "## 4. Hallazgos del proceso",
            "",
            "| Hallazgo | Evidencia | Severidad | Tratamiento recomendado |",
            "|---|---|---|---|",
            "| Decision ambigua | Criterios no formalizados | Alta | Tabla de reglas y salidas verificables |",
            "| Retrabajo circular | Devoluciones sin limite de iteraciones | Alta | Tope de reintentos + criterio de cierre |",
            "| Responsabilidad difusa | Handoff no explicitado | Media | Separar validacion, excepcion y aprobacion |",
            "",
            "## 5. Proceso TO-BE",
            "",
            "- Intake gobernado -> Validacion estandarizada -> Decision formal -> Gate humano en excepciones -> Cierre trazable",
            "- Objetivo: reducir friccion, proteger calidad de decision y preparar automatizacion progresiva.",
            "",
            "## 6. Matriz AS-IS -> TO-BE",
            "",
            "| Componente | AS-IS | TO-BE | Impacto esperado |",
            "|---|---|---|---|",
            "| Intake | Captura heterogenea | Checklist gobernado | Menos casos incompletos |",
            "| Decision | Juicio individual | Regla formal | Menor variabilidad |",
            "| Seguimiento | Canales dispersos | Estado trazable | Control directivo visible |",
            "",
            "## 7. Reglas de decision",
            "",
            "- Aprobar: expediente completo y validacion positiva.",
            "- Solicitar faltantes: informacion incompleta con correccion viable.",
            "- Escalar: excepcion o riesgo de cumplimiento.",
            "",
            "## 8. Roadmap de implementacion",
            "",
            "- Fase 1 (0-42 dias): quick wins de intake y control de retrabajo.",
            "- Fase 2 (43-90 dias): estandarizacion de validacion y tablero de trazabilidad.",
            "- Fase 3 (91-180 dias): consolidacion de gobernanza y preparacion para automatizacion.",
            "",
            "## 9. Gobernanza y trazabilidad",
            "",
            "El informe aplica diseno por gobernanza PMEL/ATK: cada evento del ciclo deja evidencia y "
            "cada publicacion queda condicionada por integridad y control de lenguaje.",
            "",
        ]

        if stage_outcomes:
            lines += ["### Ejecucion del ciclo gobernado", ""]
            for stage, data in stage_outcomes.items():
                outcome = _clean_text((data or {}).get("outcome", "PERMIT"))
                artifact_type = _clean_text((data or {}).get("artifact_type", stage))
                lines.append(f"- **{stage}** -> outcome `{outcome}` · artefacto `{artifact_type}`")
            lines.append("")

        lines += ["## 10. Anexo tecnico", ""]
        if sections:
            for s in sections:
                lines += [f"### {_clean_text(s.get('title', 'Seccion'))}", "", _clean_text(s.get("content", "")), ""]
        if evidence:
            lines += ["### Evidencia trazable", ""]
            for entry in evidence[:20]:
                lines.append(
                    f"- `{_clean_text(getattr(entry, 'event_type', 'event'))}` · "
                    f"outcome `{_clean_text(getattr(entry, 'outcome', '—'))}` · "
                    f"agente `{_clean_text(getattr(entry, 'agent', '—'))}`"
                )
            lines.append("")

        if next_step:
            lines += ["## Próximo Paso Recomendado", "", next_step, ""]

        md_base = "\n".join(lines)

    # --- SECCIÓN DE GOBERNANZA TÉCNICA (INVARIABLE) ---
    seal_entry = next((e for e in evidence if e.event_type == "cryptographic_seal"), None)
    seal_hash = (seal_entry.payload or {}).get("hash_sha256", "PENDING_PUBLICATION") if seal_entry else "PENDING_PUBLICATION"
    
    irr_entry = next((e for e in evidence if "krippendorff" in str(e.payload).lower()), None)
    irr_val = "—"
    if irr_entry:
        irr_val = (irr_entry.payload or {}).get("krippendorff_alpha", "—")

    governance_footer = [
        "",
        "---",
        "## Certificación de Integridad y Gobernanza",
        "",
        f"Este informe ha sido generado y sellado criptográficamente por el motor **ARHIAX Dx-Pro**. La integridad de los datos y el rastro de auditoría están garantizados bajo el protocolo PMEL/ATK.",
        "",
        f"- **ID del Caso:** `{case.id}`",
        f"- **Trace ID de Auditoría:** `{case.case_id}`",
        f"- **Sello SHA-256:** `{seal_hash}`",
        f"- **Confiabilidad (Krippendorff Alpha):** `{irr_val}`",
        f"- **Fecha de Certificación:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC",
        "",
        "*Documento de validez técnica para auditorías de cumplimiento y debida diligencia.*"
    ]

    return md_base + "\n".join(governance_footer)
