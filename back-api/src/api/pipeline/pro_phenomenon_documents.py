"""Genera documentos derivados del análisis de fenómeno (estilo Governex)."""
from __future__ import annotations

from datetime import datetime
from typing import Any


def _get_analysis(case: Any) -> dict[str, Any]:
    payload = getattr(case, "input_payload", None) or {}
    analysis = payload.get("phenomenon_analysis") or {}
    if not isinstance(analysis, dict):
        return {}
    return analysis


def _status_ok(analysis: dict) -> bool:
    return analysis.get("status") in ("completed", "completed_with_warnings")


def _line(title: str, body: str | None) -> list[str]:
    if not body:
        return []
    return [f"### {title}", "", str(body).strip(), ""]


def build_internal_phenomenon_markdown(case: Any) -> str:
    """Análisis interno tipo «Siete Puntas» a partir de P01–P07."""
    analysis = _get_analysis(case)
    if not _status_ok(analysis):
        raise ValueError("El análisis de fenómeno no está completo.")

    p01 = analysis.get("p01_reception") or {}
    p02 = analysis.get("p02_epoche") or {}
    p03 = analysis.get("p03_convergence") or {}
    p04 = analysis.get("p04_contradiction") or {}
    p05 = analysis.get("p05_localization") or {}
    p06 = analysis.get("p06_kill_critic") or {}
    p07 = analysis.get("p07_derivation") or {}
    summary = analysis.get("summary") or {}

    client = p01.get("client_name") or getattr(case, "client_name", "Cliente")
    domain = p01.get("domain") or getattr(case, "domain", "")
    now = datetime.now().strftime("%d/%m/%Y")

    lines: list[str] = [
        f"# Análisis fenomenológico — {client}",
        "",
        "*Documento interno · Governex Thinking · Uso restringido*",
        "",
        f"| Campo | Valor |",
        f"|---|---|",
        f"| Cliente | {client} |",
        f"| Área | {domain} |",
        f"| Sector | {p01.get('sector') or '—'} |",
        f"| Fecha | {now} |",
        f"| Fenómeno | {summary.get('phenomenon_named') or p03.get('phenomenon_named') or '—'} |",
        f"| Gates | {'OK' if summary.get('gates_passed') else 'REVISAR'} |",
        "",
        "---",
        "",
        "## 00 · Material en bruto",
        "",
        f"**Síntoma:** {p01.get('symptom') or '—'}",
        "",
        f"**Resultado esperado:** {p01.get('expected_outcome') or '—'}",
        "",
        f"**Intentos previos:** {p01.get('previous_attempts') or '—'}",
        "",
    ]

    if p01.get("core_processes"):
        lines.append("**Procesos núcleo:** " + ", ".join(p01["core_processes"]))
        lines.append("")

    if p01.get("incidents"):
        lines.append("**Incidentes DDF:**")
        for inc in p01["incidents"]:
            lines.append(f"- {inc}")
        lines.append("")

    lines += ["---", "", "## 01 · Epoqué — suspensión del nombre falso", ""]

    for naive in p02.get("naive_diagnoses") or []:
        if isinstance(naive, dict):
            lines.append(f"### {naive.get('label', 'Diagnóstico ingenuo')}")
            lines.append("")
            if naive.get("why_prescribes_solution"):
                lines.append(f"*Por qué prescribe solución:* {naive['why_prescribes_solution']}")
                lines.append("")
            if naive.get("what_it_hides"):
                lines.append(f"*Qué oculta:* {naive['what_it_hides']}")
                lines.append("")

    lines += _line("Vista suspendida", p02.get("suspended_view"))

    lines += ["---", "", "## 02 · Convergencia — las siete lentes", ""]

    for lens in p03.get("lenses_used") or []:
        if not isinstance(lens, dict):
            continue
        tradition = lens.get("tradition") or lens.get("id") or "Lente"
        lines.append(f"### {tradition}")
        if lens.get("question"):
            lines.append(f"*Pregunta:* {lens['question']}")
        if lens.get("finding"):
            lines.append(f"*Hallazgo:* {lens['finding']}")
        lines.append("")

    lines += _line("Fenómeno nombrado", p03.get("phenomenon_named"))
    lines += _line("Síntesis", p03.get("convergence_summary"))

    lines += ["---", "", "## 03 · Contradicción maestra", ""]

    tech = p04.get("technical_contradiction") or {}
    phys = p04.get("physical_contradiction") or {}
    motor = p04.get("resolution_motor") or {}

    if tech.get("statement"):
        lines += _line("Contradicción técnica", tech["statement"])
    if phys.get("statement"):
        lines += _line("Contradicción física", phys["statement"])
    if motor.get("name"):
        lines.append(f"### Motor de resolución: {motor['name']}")
        lines.append("")
    if motor.get("rule"):
        lines += _line("Regla", motor["rule"])
    if motor.get("ideal_direction"):
        lines += _line("Dirección ideal", motor["ideal_direction"])

    lines += ["---", "", "## 04 · Localización — subsistemas y acoplamientos", ""]

    for sub in p05.get("core_subsystems") or []:
        if isinstance(sub, dict):
            lines.append(f"- **{sub.get('name', sub.get('id'))}:** {sub.get('pain_signal') or sub.get('function') or ''}")
    lines.append("")

    for coup in p05.get("broken_couplings") or []:
        if isinstance(coup, dict):
            lines.append(
                f"- Acoplamiento roto *{coup.get('from')} → {coup.get('to')}*: "
                f"{coup.get('symptom')} (medio: {coup.get('human_medium') or '—'})"
            )
    lines.append("")

    lines += _line("Pregunta bisagra", p05.get("hinge_question"))

    if p05.get("priority_order"):
        lines.append("**Orden de ataque:** " + " → ".join(str(x) for x in p05["priority_order"]))
        lines.append("")

    lines += ["---", "", "## 05 · Kill Critic", ""]

    for risk in p06.get("risks") or []:
        if isinstance(risk, dict):
            sev = risk.get("severity", "warn")
            passed = "✓" if risk.get("passed") else "✗"
            lines.append(f"- [{sev}] {passed} **{risk.get('id')}:** {risk.get('description')}")
            if risk.get("test"):
                lines.append(f"  - *Prueba:* {risk['test']}")
            if risk.get("mitigation"):
                lines.append(f"  - *Mitigación:* {risk['mitigation']}")
    lines.append("")

    gates = "PASAN" if p06.get("gates_passed") else "BLOQUEADOS / REVISAR"
    lines.append(f"**Gates:** {gates}")
    lines.append("")

    if p06.get("calibration_needs"):
        lines.append("**Calibración pendiente:**")
        for c in p06["calibration_needs"]:
            lines.append(f"- {c}")
        lines.append("")

    lines += ["---", "", "## 06 · Derivación — paquete recomendado", ""]

    lines += _line("Modo de engagement", p07.get("engagement_mode"))
    lines += _line("Siguiente paso operativo", p07.get("next_operational_step"))

    docs = p07.get("recommended_documents") or []
    if docs:
        lines.append("### Documentos recomendados")
        lines.append("")
        for d in sorted(docs, key=lambda x: (x.get("priority") or 99) if isinstance(x, dict) else 99):
            if isinstance(d, dict):
                lines.append(
                    f"- **{d.get('type')}** (prioridad {d.get('priority', '—')}): "
                    f"{d.get('purpose') or d.get('audience') or ''}"
                )
        lines.append("")

    lines += [
        "---",
        "",
        "*Generado por ARHIAX Dx Pro · Motor de Fenómeno P01–P07*",
        "",
    ]
    return "\n".join(lines)


def build_discovery_form_markdown(case: Any) -> str:
    """Formulario de descubrimiento derivado del fenómeno (preguntas situacionales)."""
    analysis = _get_analysis(case)
    if not _status_ok(analysis):
        raise ValueError("El análisis de fenómeno no está completo.")

    p01 = analysis.get("p01_reception") or {}
    p03 = analysis.get("p03_convergence") or {}
    p05 = analysis.get("p05_localization") or {}
    p06 = analysis.get("p06_kill_critic") or {}

    client = p01.get("client_name") or getattr(case, "client_name", "Cliente")
    phenomenon = p03.get("phenomenon_named") or "el fenómeno operativo"
    hinge = p05.get("hinge_question") or ""

    lines: list[str] = [
        f"# Formulario de descubrimiento — {client}",
        "",
        "*Para qué es este formulario:* capturar el conocimiento que vive en el equipo y calibrar "
        f"la frontera entre lo repetible (sistema) y lo que exige juicio (persona). Fenómeno: **{phenomenon}**.",
        "",
        "**Cómo responder:** use ejemplos concretos. Un caso real vale más que una descripción perfecta. "
        "Si no hay dato exacto, un estimado sincero sirve.",
        "",
        "---",
        "",
    ]

    qnum = 1
    processes = p05.get("core_subsystems") or []
    if not processes and p01.get("core_processes"):
        processes = [{"name": p, "function": p} for p in p01["core_processes"]]

    for proc in processes:
        if not isinstance(proc, dict):
            continue
        pname = proc.get("name") or proc.get("id") or "Proceso"
        lines += [
            f"## Bloque: {pname}",
            "",
            f"**Q{qnum}.** En *{pname}*, ¿qué es lo primero que suele corregirse o rehacerse en cada ciclo? "
            "¿Qué señal usa el equipo para saber que algo está mal sin que nadie se lo diga?",
            "",
        ]
        qnum += 1
        lines += [
            f"**Q{qnum}.** Cuéntenos un episodio reciente en *{pname}* donde el resultado fue peor de lo esperado. "
            "¿Qué no se vio a tiempo?",
            "",
        ]
        qnum += 1

    if hinge:
        lines += [
            "## Pregunta bisagra",
            "",
            f"**Q{qnum}.** {hinge}",
            "",
        ]
        qnum += 1

    lines += [
        "## Cierre",
        "",
        f"**Q{qnum}.** De las decisiones que hoy pasan por una sola persona, "
        "¿cuáles son de verdad juicio irreemplazable y cuáles ocurren solo porque no están sistematizadas?",
        "",
    ]
    qnum += 1

    cal = p06.get("calibration_needs") or []
    for need in cal[:3]:
        lines += [f"**Q{qnum}.** {need}", ""]
        qnum += 1

    lines += [
        "---",
        "",
        "*Generado por ARHIAX Dx Pro a partir del análisis de fenómeno.*",
        "",
    ]
    return "\n".join(lines)
