"""Genera markdown del reporte Pro — estructura por partes alineada al PDF."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from api.pipeline.pro_report_data import build_pro_report_data

_PLACEHOLDER_PATTERN = re.compile(
    r"\b(todo|mock|placeholder|lorem ipsum|pendiente de completar)\b",
    flags=re.IGNORECASE,
)


def _clean(value: Any, fallback: str = "—") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    if not text:
        return fallback
    text = _PLACEHOLDER_PATTERN.sub("", text).strip()
    text = re.sub(r"</?[bi]>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or fallback


def _guide_block(guides: dict, key: str | None) -> list[str]:
    if not key or not guides.get(key):
        return []
    return [f"> *Orientación:* {_clean(guides[key])}", ""]


def _prose_block(data: dict, key: str | None) -> list[str]:
    if not key:
        return []
    lines: list[str] = []
    for para in (data.get("dense_narratives") or {}).get(key) or []:
        lines.append(_clean(para))
        lines.append("")
    return lines


def _section_header(sec_id: str, title: str) -> list[str]:
    return [f"## {sec_id} {title}", ""]


def _part_header(part: str, title: str, subtitle: str) -> list[str]:
    return [
        "---",
        "",
        f"# PARTE {part} — {title}",
        "",
        f"*{subtitle}*",
        "",
    ]


def build_pro_markdown(case: Any) -> str:
    data = build_pro_report_data(case)
    meta = data["meta"]
    exec_ = data["executive"]
    guides = data.get("section_guides") or {}
    eng = data.get("engagement") or {}
    lines: list[str] = [
        f"# Diagnóstico Ejecutivo — {meta['client_name']}",
        "",
        f"| Campo | Valor |",
        f"|---|---|",
        f"| Dominio | {meta['domain']} |",
        f"| Engagement | {meta['engagement_id']} |",
        f"| Fecha | {meta['date']} |",
        f"| Madurez | {exec_['overall_score']}/100 |",
        f"| Respondentes | {exec_['total_responses']} |",
        f"| Estado | {meta['case_status']} |",
        "",
    ]

    outline = data.get("outline") or []
    for part in outline:
        lines += _part_header(part["part"], part["title"], part.get("subtitle", ""))

        for sec in part.get("sections") or []:
            sid = sec["id"]
            stitle = sec["title"]
            gkey = sec.get("guide")
            pkey = sec.get("prose")

            lines += _section_header(sid, stitle)
            lines += _guide_block(guides, gkey)
            lines += _prose_block(data, pkey)

            # Contenido específico por sección
            if sid == "1.0":
                lines.append("### Estructura del informe")
                lines.append("")
                for p in outline:
                    lines.append(f"- **PARTE {p['part']}** — {p['title']}")
                    for s in p.get("sections") or []:
                        lines.append(f"  - {s['id']} {s['title']}")
                lines.append("")

            elif sid == "1.1":
                lines += [
                    "| Campo | Detalle |",
                    "|---|---|",
                    f"| Razón social | {_clean(eng.get('legal_name'))} |",
                    f"| NIT | {_clean(eng.get('nit'))} |",
                    f"| Sector / Tamaño | {_clean(eng.get('sector'))} · {_clean(eng.get('size_org'))} |",
                    f"| Ubicación | {_clean(eng.get('city'))}, {_clean(eng.get('country'))} |",
                    f"| Sponsor | {_clean(eng.get('contact_name'))} ({_clean(eng.get('contact_role'))}) |",
                    f"| Síntoma | {_clean(eng.get('symptom'))} |",
                    f"| Desde | {_clean(eng.get('problem_since'))} |",
                    f"| Resultado esperado | {_clean(eng.get('expected_outcome'))} |",
                    "",
                ]

            elif sid == "1.2":
                m = data.get("methodology") or {}
                lines.append("| Fase | Agentes y alcance |")
                lines.append("|---|---|")
                for phase, desc in m.get("phases", []):
                    lines.append(f"| {phase} | {_clean(desc)} |")
                lines.append("")

            elif sid == "2.1":
                lines.append(_clean(exec_["thesis"]))
                lines.append("")
                if exec_.get("implications"):
                    lines.append("### Implicaciones estratégicas")
                    lines.append("")
                    for imp in exec_["implications"]:
                        lines.append(f"- {_clean(imp)}")
                    lines.append("")
                if exec_.get("hypotheses"):
                    lines += ["| Hipótesis | Estado | Posterior |", "|---|---|---|"]
                    for h in exec_["hypotheses"][:8]:
                        status = "Confirmada" if h.get("supported") else "No confirmada"
                        lines.append(
                            f"| {_clean(h.get('statement') or h.get('hypothesis'))} | {status} | {h.get('posterior', '—')} |"
                        )
                    lines.append("")
                lines.append(f"**Próximo paso:** {_clean(exec_.get('next_step'))}")
                lines.append("")

            elif sid == "2.2":
                tri = data.get("triangulation") or {}
                lines += ["| ID | DDF | Encuesta | Bayesiano | Psicometría |", "|---|---|---|---|---|"]
                for r in tri.get("rows") or []:
                    lines.append(
                        f"| {_clean(r.get('id'))} | {_clean(r.get('ddf'))} | "
                        f"{_clean(r.get('survey'))} | {_clean(r.get('bayesian'))} | {_clean(r.get('psych'))} |"
                    )
                lines.append("")

            elif sid == "2.3":
                scoring = data.get("scoring") or {}
                dim_scores = scoring.get("dimension_scores") or data.get("maturity", {}).get("dimension_scores") or []
                lines += ["| Dimensión | Score | Benchmark | Brecha |", "|---|---:|---:|---:|"]
                for d in dim_scores:
                    lines.append(
                        f"| {_clean(d.get('dimension') or d.get('name'))} | {d.get('score', '—')} | "
                        f"{d.get('benchmark', 75)} | {d.get('gap', '—')} |"
                    )
                lines.append("")
                role_scores = scoring.get("role_scores") or {}
                if role_scores:
                    lines += ["| Rol | Score | N |", "|---|---:|---:|"]
                    for role, info in role_scores.items():
                        if isinstance(info, dict):
                            lines.append(f"| {role} | {info.get('score')} | {info.get('n_responses')} |")
                    lines.append("")

            elif sid == "2.4":
                psy = data["psychometrics"]
                bay = data["bayesian"]
                lines.append(f"- **α Cronbach:** {psy.get('cronbach', '—')}")
                lines.append(f"- **IRR Krippendorff:** {psy.get('irr', '—')}")
                lines.append(f"- **QA G14:** {data.get('governance', {}).get('qa_score', '—')}/100")
                lines.append("")
                for h in (bay.get("confirmed") or []):
                    lines.append(f"- Confirmada: {_clean(h if isinstance(h, str) else h.get('hypothesis'))}")
                lines.append("")

            elif sid == "3.1":
                cien = data["cienciometria"]
                lines += ["| Estudio | Año | Relevancia | Hallazgo |", "|---|---:|---|---|"]
                for lit in cien.get("literature") or []:
                    if isinstance(lit, dict):
                        lines.append(
                            f"| {_clean(lit.get('title'))} | {lit.get('year', '—')} | "
                            f"{_clean(lit.get('relevance'))} | {_clean(lit.get('key_finding'))} |"
                        )
                lines.append("")

            elif sid == "3.2":
                cart = data["cartografia"]
                sector = cart.get("sector_process") or {}
                if sector.get("description"):
                    lines += [_clean(sector["description"]), ""]
                if cart.get("benchmarks"):
                    lines += ["| KPI | Sector P50 | Cliente | Brecha |", "|---|---|---|---|"]
                    for b in cart["benchmarks"]:
                        if isinstance(b, dict):
                            lines.append(
                                f"| {_clean(b.get('kpi'))} | {_clean(b.get('sector_p50'))} | "
                                f"{_clean(b.get('cliente'))} | {_clean(b.get('gap'))} |"
                            )
                    lines.append("")
                if cart.get("industry_cases"):
                    lines += ["| Caso | Problema | Solución | Resultado |", "|---|---|---|---|"]
                    for c in cart["industry_cases"][:4]:
                        if isinstance(c, dict):
                            lines.append(
                                f"| {_clean(c.get('company_type'))} | {_clean(c.get('problem'))} | "
                                f"{_clean(c.get('solution'))} | {_clean(c.get('result'))} |"
                            )
                    lines.append("")

            elif sid == "3.3":
                triz = data["triz_ddf"]
                lines += ["| ID | Hipótesis | Refutadora | Conf. |", "|---|---|---|---|"]
                for h in triz.get("hypotheses_intake") or []:
                    lines.append(
                        f"| {_clean(h.get('id'))} | {_clean(h.get('enunciado'))[:80]} | "
                        f"{_clean(h.get('refutadora'))[:60]} | {_clean(h.get('confianza'))} |"
                    )
                lines.append("")
                for h in triz.get("hypotheses_intake") or []:
                    inc = h.get("incidente")
                    if inc and inc != "—":
                        lines.append(f"**{_clean(h.get('id'))}:** {_clean(inc)}")
                        lines.append("")

            elif sid == "4.1":
                asis = data["asis"]
                tobe = data["tobe"]
                if asis.get("steps"):
                    lines.append("**AS-IS:** " + " → ".join(_clean(s) for s in asis["steps"]))
                    lines.append("")
                if asis.get("activities"):
                    lines += ["| Actividad | Lane | Crítica | Cuello |", "|---|---|---|---|"]
                    for a in asis["activities"][:10]:
                        if isinstance(a, dict):
                            lines.append(
                                f"| {_clean(a.get('name'))} | {_clean(a.get('lane'))} | "
                                f"{'Sí' if a.get('is_critical') else 'No'} | "
                                f"{'Sí' if a.get('is_bottleneck') else 'No'} |"
                            )
                    lines.append("")
                if tobe.get("steps"):
                    lines.append("**TO-BE:** " + " → ".join(_clean(s) for s in tobe["steps"]))
                    lines.append("")
                if tobe.get("options"):
                    lines += ["| Opción | ROI% | Payback | Inversión | Ahorro/mes |", "|---|---:|---:|---:|---:|"]
                    for o in tobe["options"][:4]:
                        if isinstance(o, dict):
                            lines.append(
                                f"| {_clean(o.get('name'))} | {o.get('roi_percent', '—')}% | "
                                f"{o.get('payback_months', '—')}m | {o.get('investment_usd', '—')} | "
                                f"{o.get('monthly_savings_usd', '—')} |"
                            )
                    lines.append("")

            elif sid == "4.2":
                if data["matrix_asis_tobe"]:
                    lines += ["| Componente | AS-IS | TO-BE | Impacto |", "|---|---|---|---|"]
                    for row in data["matrix_asis_tobe"]:
                        lines.append(
                            f"| {_clean(row.get('component'))} | {_clean(row.get('as_is'))} | "
                            f"{_clean(row.get('to_be'))} | {_clean(row.get('impact'))} |"
                        )
                    lines.append("")

            elif sid == "4.3":
                find = data["findings"]
                bott = data["bottlenecks"]
                lines += ["| Hallazgo | Evidencia | Prioridad | Tratamiento |", "|---|---|---|---|"]
                for f in find.get("matrix") or []:
                    if isinstance(f, dict):
                        lines.append(
                            f"| {_clean(f.get('finding'))} | {_clean(f.get('evidence'))} | "
                            f"{_clean(f.get('priority'))} | {_clean(f.get('treatment'))} |"
                        )
                lines.append("")
                if bott.get("items"):
                    lines += ["| Cuello | Impacto | USD/mes | Severidad |", "|---|---:|---:|---|"]
                    for b in bott["items"]:
                        if isinstance(b, dict):
                            lines.append(
                                f"| {_clean(b.get('name'))[:60]} | {b.get('impact_score', '—')} | "
                                f"{b.get('estimated_cost_usd_month', '—')} | {_clean(b.get('severity'))} |"
                            )
                    lines.append("")
                if bott.get("total_loss_usd"):
                    lines.append(f"**Pérdida total estimada:** USD {bott['total_loss_usd']:,}/mes")
                    lines.append("")

            elif sid == "4.4":
                if data["decision_rules"]:
                    lines += ["| Regla | Condición | Acción | Falsación |", "|---|---|---|---|"]
                    for r in data["decision_rules"]:
                        if isinstance(r, dict):
                            lines.append(
                                f"| {_clean(r.get('rule'))} | {_clean(r.get('description'))[:60]} | "
                                f"{_clean(r.get('action') or r.get('evidence'))[:50]} | "
                                f"{_clean(r.get('falsification', '—'))[:50]} |"
                            )
                    lines.append("")

            elif sid == "5.1":
                if data["roadmap"]:
                    lines += ["| Horizonte | Acciones | Responsable | KPI |", "|---|---|---|---|"]
                    for phase in data["roadmap"]:
                        lines.append(
                            f"| {_clean(phase.get('phase'))} | {_clean(phase.get('content'))} | "
                            f"{_clean(phase.get('owner', '—'))} | {_clean(phase.get('kpi', '—'))} |"
                        )
                    lines.append("")

            elif sid == "5.2":
                if exec_.get("narrative"):
                    lines.append(_clean(exec_["narrative"]))
                    lines.append("")
                gov = data["governance"]
                if gov.get("stage_outcomes"):
                    lines += ["| Agente | Outcome |", "|---|---|"]
                    for stage, payload in gov["stage_outcomes"].items():
                        p = payload or {}
                        lines.append(f"| {stage} | {_clean(p.get('outcome'))} |")
                    lines.append("")

    psy = data["psychometrics"]
    gov = data["governance"]
    seal_hash = "PENDING_PUBLICATION"
    irr_val = psy.get("irr") or "—"
    for entry in gov.get("evidence") or []:
        et = getattr(entry, "event_type", None) or (entry.get("event_type") if isinstance(entry, dict) else None)
        pl = getattr(entry, "payload", None) or (entry.get("payload") if isinstance(entry, dict) else {}) or {}
        if et == "cryptographic_seal":
            seal_hash = pl.get("hash_sha256", seal_hash)

    lines += [
        "---",
        "## Certificación de integridad",
        "",
        f"- **ID del Caso:** `{case.id}`",
        f"- **Trace ID:** `{meta['case_id']}`",
        f"- **Sello SHA-256:** `{seal_hash}`",
        f"- **Krippendorff Alpha:** `{irr_val}`",
        f"- **Certificación:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC",
    ]

    return "\n".join(lines)
