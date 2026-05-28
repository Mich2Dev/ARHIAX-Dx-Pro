"""Genera el markdown del reporte Pro desde los datos del caso."""
from __future__ import annotations
from datetime import datetime
from typing import Any


def build_pro_markdown(case: Any) -> str:
    fusion = case.fusion_result or {}
    report = case.report_result or {}
    render = case.render_result or {}

    # Si el runtime ya generó el markdown completo, usarlo
    md_base = render.get("markdown", "")
    
    scoring = fusion.get("scoring") or {}
    overall = scoring.get("overall_score", "—")
    thesis = fusion.get("executive_thesis", "")
    hypotheses = fusion.get("hypotheses") or []
    risks = fusion.get("risk_signals") or []
    next_step = fusion.get("recommended_next_step", "")
    sections = report.get("sections") or []
    total_responses = scoring.get("total_responses", 0)

    if not md_base:
        lines = [
            f"# Diagnóstico Ejecutivo — {case.client_name}",
            f"",
            f"**Dominio:** {case.domain}  ",
            f"**Engagement:** {case.engagement_id}  ",
            f"**Fecha:** {datetime.now().strftime('%d/%m/%Y')}  ",
            f"**Índice de Madurez:** {overall}/100  ",
            f"**Respondentes:** {total_responses}  ",
            f"**Estado:** {case.case_status}",
            "",
        ]

        if thesis:
            lines += ["## Tesis Ejecutiva", "", thesis, ""]

        if scoring.get("dimension_scores"):
            lines += ["## Scoring por Dimensión", ""]
            for d in scoring["dimension_scores"]:
                lines.append(f"- **{d.get('dimension')}**: {d.get('score')}/100 (brecha: {d.get('gap', 0):+.0f})")
            lines.append("")

        if hypotheses:
            lines += ["## Hipótesis Evaluadas", ""]
            for h in hypotheses:
                estado = "✓ Confirmada" if h.get("supported") else "✗ No confirmada"
                lines.append(f"- [{estado}] {h.get('statement')} (P={h.get('posterior', '—')})")
            lines.append("")

        if risks:
            lines += ["## Señales de Riesgo", ""]
            for r in risks:
                lines.append(f"- [{r.get('severity', '').upper()}] {r.get('signal', '')}")
            lines.append("")

        if sections:
            for s in sections:
                lines += [f"## {s.get('title', 'Sección')}", "", s.get("content", ""), ""]

        if next_step:
            lines += ["## Próximo Paso Recomendado", "", next_step, ""]
        
        md_base = "\n".join(lines)

    # --- SECCIÓN DE GOBERNANZA TÉCNICA (INVARIABLE) ---
    evidence = case.evidence_entries or []
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
