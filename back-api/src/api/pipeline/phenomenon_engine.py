"""Phenomenon Engine — abordaje estilo Governex (P01–P07) para cualquier caso."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any

from api.pipeline.llm_guard import PipelineStageFailureError
from api.pipeline.prompts.phenomenon import DEFAULT_LENS_PACK
from api.pipeline.pro_coherence import build_case_anchors, derive_subprocess

PHENOMENON_VERSION = "1.0"

PHENOMENON_LLM_PHASES: list[str] = [
    "p02_epoche",
    "p03_convergence",
    "p04_contradiction",
    "p05_localization",
    "p06_kill_critic",
    "p07_derivation",
]

PHASE_TIMEOUTS: dict[str, float] = {
    "p02_epoche": 90.0,
    "p03_convergence": 120.0,
    "p04_contradiction": 90.0,
    "p05_localization": 90.0,
    "p06_kill_critic": 90.0,
    "p07_derivation": 90.0,
}

DOCUMENT_TYPES = frozenset({
    "internal_phenomenon",
    "discovery_form",
    "commercial_proposal",
    "horizon_map",
    "executive_report",
    "seed_data_template",
    "survey_instrument",
    "architecture_tr",
    "sprint_spec",
})


def _json_str(value: Any, limit: int = 12000) -> str:
    try:
        text = json.dumps(value, ensure_ascii=False, indent=2)
    except (TypeError, ValueError):
        text = str(value)
    if len(text) > limit:
        return text[:limit] + "\n... [TRUNCADO]"
    return text


def build_p01_reception(
    *,
    client_name: str,
    domain: str,
    input_payload: dict | None,
) -> dict[str, Any]:
    """P01 determinista: normaliza material bruto del intake."""
    payload = input_payload or {}
    extra = payload.get("extra") or {}

    paquete = payload.get("paquete_hipotesis") or []
    hypotheses = payload.get("hypotheses") or []
    incidents: list[str] = []
    hypothesis_statements: list[str] = []

    for h in paquete:
        if not isinstance(h, dict):
            continue
        for key in ("enunciado", "incidente_texto", "observacion_refutadora"):
            val = h.get(key)
            if val:
                if key == "incidente_texto":
                    incidents.append(str(val))
                elif key == "enunciado":
                    hypothesis_statements.append(str(val))
                else:
                    hypothesis_statements.append(str(val))

    symptom = str(extra.get("symptom") or payload.get("symptom") or "").strip()
    if not symptom and hypothesis_statements:
        symptom = hypothesis_statements[0]

    client_diagnosis = str(
        extra.get("client_stated_diagnosis")
        or extra.get("client_diagnosis")
        or payload.get("client_stated_diagnosis")
        or ""
    ).strip()

    core_processes = extra.get("core_processes") or payload.get("core_processes")
    if not core_processes and symptom:
        core_processes = _infer_processes_from_symptom(symptom)

    subprocess = (
        extra.get("subprocess")
        or payload.get("subprocess")
        or derive_subprocess(symptom, domain, str(extra.get("expected_outcome") or ""))
    )

    people_mentions = _extract_people_mentions(
        symptom,
        extra.get("contact_name"),
        extra.get("previous_attempts"),
        " ".join(incidents),
    )

    return {
        "client_name": client_name,
        "domain": domain,
        "sector": str(extra.get("sector") or domain or ""),
        "symptom": symptom,
        "client_stated_diagnosis": client_diagnosis,
        "expected_outcome": str(extra.get("expected_outcome") or ""),
        "previous_attempts": str(extra.get("previous_attempts") or ""),
        "size_org": str(extra.get("size_org") or ""),
        "location": ", ".join(
            x for x in (extra.get("city"), extra.get("country")) if x
        ),
        "sponsor": " — ".join(
            x for x in (extra.get("contact_name"), extra.get("contact_role")) if x
        ),
        "core_processes": core_processes if isinstance(core_processes, list) else [],
        "hypotheses": hypothesis_statements,
        "incidents": incidents,
        "grey_sources": list(payload.get("grey_sources") or []),
        "subprocess": subprocess,
        "people_mentions": people_mentions,
        "survey_mode": payload.get("survey_mode"),
        "roles": payload.get("roles") or [],
    }


def _infer_processes_from_symptom(symptom: str) -> list[str]:
    lowered = symptom.lower()
    candidates = [
        ("cotiz", "Cotización"),
        ("requis", "Requisición y compras"),
        ("liquid", "Liquidación / cierre"),
        ("manten", "Mantenimiento"),
        ("proyect", "Gestión de proyectos"),
        ("innov", "Innovación"),
        ("despach", "Despacho / logística"),
    ]
    found: list[str] = []
    for needle, label in candidates:
        if needle in lowered and label not in found:
            found.append(label)
    return found


def _extract_people_mentions(*chunks: Any) -> list[str]:
    import re

    blob = " ".join(str(c) for c in chunks if c)
    # Simple capitalized name patterns common in intake
    names = re.findall(r"\b([A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,}(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,})?)\b", blob)
    skip = {"Construcción", "Colombia", "Barranquilla", "Operaciones", "Global"}
    return [n for n in dict.fromkeys(names) if n not in skip][:8]


def build_phenomenon_prompt(phase: str, context: dict[str, Any]) -> str:
    from api.pipeline.prompts.phenomenon import (
        P02_EPOCHE,
        P03_CONVERGENCE,
        P04_CONTRADICTION,
        P05_LOCALIZATION,
        P06_KILL_CRITIC,
        P07_DERIVATION,
    )

    p01 = context.get("p01_reception") or {}
    mapping = {
        "p02_epoche": lambda: P02_EPOCHE.format(p01_reception=_json_str(p01)),
        "p03_convergence": lambda: P03_CONVERGENCE.format(
            p02_epoche=_json_str(context.get("p02_epoche")),
            lens_pack=context.get("lens_pack") or DEFAULT_LENS_PACK,
        ),
        "p04_contradiction": lambda: P04_CONTRADICTION.format(
            p03_convergence=_json_str(context.get("p03_convergence")),
            p01_reception=_json_str(p01),
        ),
        "p05_localization": lambda: P05_LOCALIZATION.format(
            p04_contradiction=_json_str(context.get("p04_contradiction")),
            p01_reception=_json_str(p01),
        ),
        "p06_kill_critic": lambda: P06_KILL_CRITIC.format(
            p03_convergence=_json_str(context.get("p03_convergence")),
            p04_contradiction=_json_str(context.get("p04_contradiction")),
            p05_localization=_json_str(context.get("p05_localization")),
        ),
        "p07_derivation": lambda: P07_DERIVATION.format(
            p06_kill_critic=_json_str(context.get("p06_kill_critic")),
            p05_localization=_json_str(context.get("p05_localization")),
            p03_convergence=_json_str(context.get("p03_convergence")),
        ),
    }
    builder = mapping.get(phase)
    if not builder:
        raise ValueError(f"Fase desconocida: {phase}")
    return builder()


def validate_phase_output(phase: str, output: dict) -> list[str]:
    """Validación mínima fail-closed por fase."""
    issues: list[str] = []
    if not isinstance(output, dict):
        return ["output no es objeto JSON"]

    if phase == "p03_convergence":
        if not str(output.get("phenomenon_named") or "").strip():
            issues.append("falta phenomenon_named")
        if not output.get("lenses_used"):
            issues.append("falta lenses_used")

    elif phase == "p04_contradiction":
        motor = output.get("resolution_motor") or {}
        if not str(motor.get("name") or "").strip():
            issues.append("falta resolution_motor.name")

    elif phase == "p05_localization":
        if not str(output.get("hinge_question") or "").strip():
            issues.append("falta hinge_question")

    elif phase == "p06_kill_critic":
        if "gates_passed" not in output:
            issues.append("falta gates_passed")

    elif phase == "p07_derivation":
        docs = output.get("recommended_documents") or []
        if not docs:
            issues.append("falta recommended_documents")
        for d in docs:
            if isinstance(d, dict) and d.get("type") not in DOCUMENT_TYPES:
                issues.append(f"tipo de documento inválido: {d.get('type')}")

    return issues


def build_summary(analysis: dict[str, Any]) -> dict[str, Any]:
    p03 = analysis.get("p03_convergence") or {}
    p04 = analysis.get("p04_contradiction") or {}
    p06 = analysis.get("p06_kill_critic") or {}
    p07 = analysis.get("p07_derivation") or {}
    motor = p04.get("resolution_motor") or {}

    return {
        "phenomenon_named": p03.get("phenomenon_named"),
        "convergence_summary": p03.get("convergence_summary"),
        "resolution_motor": motor.get("name"),
        "resolution_rule": motor.get("rule"),
        "hinge_question": (analysis.get("p05_localization") or {}).get("hinge_question"),
        "gates_passed": bool(p06.get("gates_passed")),
        "blocking_reasons": list(p06.get("blocking_reasons") or []),
        "recommended_documents": list(p07.get("recommended_documents") or []),
        "next_operational_step": p07.get("next_operational_step"),
        "commercial_safe": bool(p07.get("commercial_safe", True)),
        "use_survey": bool(p07.get("use_survey", True)),
    }


async def run_phenomenon_analysis(
    executor: Any,
    *,
    client_name: str,
    domain: str,
    input_payload: dict | None,
) -> dict[str, Any]:
    """
    Ejecuta P01–P07. Retorna phenomenon_analysis completo.
    Lanza PipelineStageFailureError si una fase LLM falla validación.
    """
    context: dict[str, Any] = {
        "lens_pack": DEFAULT_LENS_PACK,
        "client_name": client_name,
        "domain": domain,
    }
    stages: list[dict] = []

    p01 = build_p01_reception(
        client_name=client_name,
        domain=domain,
        input_payload=input_payload,
    )
    context["p01_reception"] = p01
    stages.append({
        "tool_name": "p01_reception",
        "status": "completed",
        "model_used": "deterministic",
        "output": p01,
    })

    # Anclas para coherencia downstream
    ctx_for_anchors = {
        "objective": p01.get("symptom"),
        "sector": p01.get("sector"),
        "domain": domain,
        "subprocess": p01.get("subprocess"),
        "expected_outcome": p01.get("expected_outcome"),
        "paquete_hipotesis": (input_payload or {}).get("paquete_hipotesis") or [],
        "corpus_incidentes": p01.get("incidents") or [],
    }
    context["case_anchors"] = build_case_anchors(ctx_for_anchors)

    for phase in PHENOMENON_LLM_PHASES:
        stages.append({"tool_name": phase, "status": "running", "output": None})
        idx = len(stages) - 1
        timeout = PHASE_TIMEOUTS.get(phase, 90.0)

        try:
            prompt = build_phenomenon_prompt(phase, context)
            res = await asyncio.wait_for(
                executor._call_gemini_with_retry(
                    phase,
                    prompt,
                    "gemini-2.5-flash",
                    8192,
                    0.2,
                ),
                timeout=timeout,
            )
            output = res.get("output", {})
            issues = validate_phase_output(phase, output)
            if issues:
                raise PipelineStageFailureError(
                    phase,
                    f"validación: {'; '.join(issues)}",
                )
            context[phase] = output
            stages[idx].update({
                "status": "completed",
                "model_used": res.get("model_used"),
                "tokens_used": res.get("tokens_used"),
                "latency_ms": res.get("latency_ms"),
                "output": output,
            })
        except asyncio.TimeoutError:
            msg = f"Tiempo agotado ({timeout}s)"
            stages[idx].update({"status": "failed", "output": {"error": msg}})
            raise PipelineStageFailureError(phase, msg)
        except PipelineStageFailureError:
            stages[idx].update({
                "status": "failed",
                "output": {"error": "falló la fase"},
            })
            raise
        except Exception as exc:
            msg = str(exc)[:240]
            stages[idx].update({"status": "failed", "output": {"error": msg}})
            raise PipelineStageFailureError(phase, msg) from exc

    now = datetime.now(timezone.utc).isoformat()
    analysis: dict[str, Any] = {
        "version": PHENOMENON_VERSION,
        "status": "completed",
        "updated_at": now,
        "stages": stages,
        "p01_reception": p01,
    }
    for phase in PHENOMENON_LLM_PHASES:
        analysis[phase] = context.get(phase)

    summary = build_summary(analysis)
    analysis["summary"] = summary

    if not summary.get("gates_passed"):
        analysis["status"] = "completed_with_warnings"
    return analysis


def phenomenon_analysis_for_detail(payload: dict | None) -> dict | None:
    """Vista resumida para API/UI."""
    raw = (payload or {}).get("phenomenon_analysis")
    if not raw or not isinstance(raw, dict):
        return None
    summary = raw.get("summary") or build_summary(raw)
    return {
        "status": raw.get("status"),
        "version": raw.get("version"),
        "updated_at": raw.get("updated_at"),
        "summary": summary,
        "stages": raw.get("stages") or [],
    }
