"""Utilidades compartidas del pipeline Pro: G01–G08 + análisis post-encuesta."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from api.pipeline.hypothesis_pack import build_hypothesis_pack, g05_from_paquete
from api.pipeline.llm_guard import PipelineStageFailureError
from api.pipeline.pro_coherence import build_case_anchors, derive_subprocess, validate_output_coherence
from api.pipeline.pro_survey_mode import (
    roles_for_mode,
    resolve_survey_mode,
    survey_mode_instructions,
)
from api.pipeline.pro_g13_fallback import (
    build_g13_fallback_from_g12,
    build_g13_fallback_minimal,
    coerce_tool_dict,
)
from api.pipeline.pro_survey_roles import available_role_labels

log = logging.getLogger("arhiax.pipeline.pro")

RESEARCH_DESIGN_TOOLS: list[str] = [
    "g01_receptor",
    "g02_configurador",
    "g03_cienciometro",
    "g04_cartografo",
    "g05_brechas",
    "g06_bpmn_architect",
    "g07_cuellos",
    "g08_optimizador",
    "bpmn_generator",
]

SURVEY_TOOLS: list[str] = [
    "g09a_preguntas",
    "g09b_ramificacion",
    "g09c_validacion",
]

ANALYSIS_TOOLS: list[str] = [
    "g10a_scoring",
    "g10b_psicometria",
    "g11a_bayesiano",
    "g11b_nlp",
    "irr_calculator",
    "scoring_engine",
    "g12_hallazgos",
    "g13_redactor",
    "g14_qa_control",
]

TOOL_TIMEOUTS: dict[str, float] = {
    "g03_cienciometro": 120.0,
    "g04_cartografo": 120.0,
    "g06_bpmn_architect": 150.0,
    "g08_optimizador": 150.0,
    "bpmn_generator": 90.0,
    "g13_redactor": 150.0,
}


def _parse_jsonish(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return value
    return value


def extract_stage_outputs(stages: list[dict] | None) -> dict[str, Any]:
    """Extrae outputs indexados por tool_name desde pipeline_stages del caso Pro."""
    outputs: dict[str, Any] = {}
    for stage in stages or []:
        if not isinstance(stage, dict):
            continue
        if stage.get("status") != "completed":
            continue
        tool = stage.get("tool_name")
        if not tool:
            continue
        raw = stage.get("output")
        if not raw:
            continue
        if isinstance(raw, dict) and "output" in raw:
            outputs[tool] = _parse_jsonish(raw.get("output"))
        else:
            outputs[tool] = _parse_jsonish(raw)
    return outputs


def merge_outputs_into_context(context: dict, outputs: dict[str, Any]) -> dict:
    """Inyecta outputs previos al contexto (clave = tool_name)."""
    for tool, data in outputs.items():
        if data is not None:
            context[tool] = data
    return context


def build_pro_context(
    *,
    client_name: str,
    domain: str,
    input_payload: dict | None = None,
    body_dict: dict | None = None,
) -> dict[str, Any]:
    """Contexto inicial para G01–G09 a partir del caso o del payload de creación."""
    payload = input_payload or {}
    body = body_dict or {}

    paquete = payload.get("paquete_hipotesis") or body.get("paquete_hipotesis") or []
    field_data = payload.get("field_data") or body.get("field_data") or {}
    if not paquete and (body.get("hypotheses") or payload.get("hypotheses")):
        legacy = [h for h in (body.get("hypotheses") or payload.get("hypotheses") or []) if str(h).strip()]
        paquete, field_data = build_hypothesis_pack([], legacy_strings=legacy)

    extra = body.get("extra") or payload.get("extra") or {}
    # Campos del wizard se aplana en input_payload; leer también de la raíz.
    def _field(key: str, default: Any = "") -> Any:
        return extra.get(key) or payload.get(key) or body.get(key) or default

    survey_mode = resolve_survey_mode(
        body.get("survey_mode") or payload.get("survey_mode"),
        body.get("roles") or payload.get("roles"),
    )
    roles = roles_for_mode(
        survey_mode,
        body.get("roles") or payload.get("roles"),
    )
    dimensions = body.get("dimensions") or payload.get("dimensions") or ["strategy", "process", "technology"]

    sector = _field("sector")
    diagnostic_area = domain or body.get("domain") or payload.get("domain") or ""
    symptom = _field("symptom")
    if not symptom and paquete:
        symptom = str(paquete[0].get("enunciado") or "")
    expected_outcome = _field("expected_outcome")
    subprocess = (
        _field("subprocess")
        or payload.get("subprocess")
        or derive_subprocess(symptom, diagnostic_area, expected_outcome)
    )

    operativo_extra = {
        "sector": sector,
        "size_org": _field("size_org"),
        "years_operating": _field("years_operating"),
        "areas_count": _field("areas_count"),
        "expected_outcome": _field("expected_outcome"),
        "previous_attempts": _field("previous_attempts"),
    }
    from api.pipeline.pro_report_data import _format_quantitative_context
    operational_context = _format_quantitative_context(operativo_extra)

    context: dict[str, Any] = {
        "organization_name": client_name or body.get("client_name", ""),
        "domain": diagnostic_area,
        "diagnostic_area": diagnostic_area,
        "sector": sector or diagnostic_area,
        "subprocess": subprocess,
        "objective": symptom,
        "expected_outcome": expected_outcome,
        "size_org": str(_field("size_org") or "51-200"),
        "operational_context": operational_context,
        "paquete_hipotesis": paquete,
        "survey_mode": survey_mode,
        "roles": roles,
        "survey_mode_note": survey_mode_instructions(survey_mode, available_role_labels(roles)),
        "corpus_incidentes": [
            inc.get("texto")
            for fd in field_data.values()
            for inc in (fd.get("corpus_incidentes") or [])
            if isinstance(inc, dict) and inc.get("texto")
        ],
    }
    phen = payload.get("phenomenon_analysis") or {}
    phen_summary = phen.get("summary") if isinstance(phen.get("summary"), dict) else {}
    if phen_summary.get("phenomenon_named"):
        context["phenomenon_named"] = str(phen_summary["phenomenon_named"])
    if phen_summary.get("resolution_motor"):
        context["phenomenon_motor"] = str(phen_summary["resolution_motor"])
    p03 = phen.get("p03_convergence") if isinstance(phen.get("p03_convergence"), dict) else {}
    if p03.get("convergence_summary"):
        context["phenomenon_summary"] = str(p03["convergence_summary"])
    context["case_anchors"] = build_case_anchors(context)

    g05 = payload.get("g05_brechas") or g05_from_paquete(paquete, field_data)
    context["g05_brechas"] = g05

    g02 = payload.get("g02_configurador")
    if not g02:
        role_labels = available_role_labels(roles)
        g02 = {
            "roles": [{"id": r, "label": lbl} for r, lbl in zip(roles, role_labels)],
            "dimensions": [{"id": d, "name": d} for d in dimensions],
            "survey_mode": survey_mode,
        }
    context["g02_configurador"] = g02

    return context


def _apply_g13_fallback(context: dict) -> dict[str, Any]:
    g12 = coerce_tool_dict(context.get("g12_hallazgos"))
    if g12.get("findings_matrix") or g12.get("executive_summary_findings"):
        return build_g13_fallback_from_g12(g12, context)
    return build_g13_fallback_minimal(context)


async def _run_g13_redactor(
    executor: Any,
    context: dict,
    stages: list[dict],
    idx: int,
    timeout: float,
    tool_results: dict[str, dict],
) -> None:
    """G13: intenta Gemini una vez; si falla (JSON, coherencia, timeout), fallback sin tumbar el caso."""
    tool_name = "g13_redactor"
    stages[idx]["status"] = "running"
    res: dict[str, Any] | None = None
    output: dict[str, Any] | None = None
    used_fallback = False

    try:
        res = await asyncio.wait_for(
            executor.run_tool(tool_name, context, {}),
            timeout=timeout,
        )
        output = res.get("output", {})
        if isinstance(output, dict) and not output.get("error"):
            validate_output_coherence(tool_name, output, context)
    except (PipelineStageFailureError, asyncio.TimeoutError, Exception) as exc:
        reason = getattr(exc, "reason", None) or str(exc)
        log.warning("G13 LLM rechazado (%s); usando fallback determinístico", reason[:160])
        output = _apply_g13_fallback(context)
        used_fallback = True
        res = {
            "tool": tool_name,
            "model_used": "deterministic-g13-fallback",
            "tokens_used": 0,
            "latency_ms": 0,
            "output": output,
        }

    if not isinstance(output, dict) or output.get("error"):
        output = _apply_g13_fallback(context)
        used_fallback = True
        res = {
            "tool": tool_name,
            "model_used": "deterministic-g13-fallback",
            "tokens_used": 0,
            "latency_ms": 0,
            "output": output,
        }

    if used_fallback:
        log.info("G13 completado con fallback determinístico (sin validación LLM)")

    context[tool_name] = output
    tool_results[tool_name] = res or {"tool": tool_name, "output": output}
    stages[idx].update({
        "status": "completed",
        "model_used": (res or {}).get("model_used"),
        "tokens_used": (res or {}).get("tokens_used"),
        "latency_ms": (res or {}).get("latency_ms"),
        "output": output,
    })
    context.pop("coherence_retry_note", None)


def make_stage_list(tools: list[str], start_id: int = 0) -> list[dict]:
    return [
        {
            "id": start_id + i,
            "tool_name": t,
            "status": "pending",
            "model_used": None,
            "tokens_used": None,
            "latency_ms": None,
            "output": None,
        }
        for i, t in enumerate(tools)
    ]


async def run_tool_chain(
    executor: Any,
    tools: list[str],
    context: dict,
    stages: list[dict],
    stage_offset: int = 0,
    default_timeout: float = 120.0,
) -> tuple[dict[str, dict], list[dict]]:
    """
    Ejecuta herramientas en secuencia, actualizando stages in-place.
    Retorna (tool_results, stages).
    """
    tool_results: dict[str, dict] = {}

    for i, tool_name in enumerate(tools):
        idx = stage_offset + i
        if idx >= len(stages):
            stages.append({
                "id": idx,
                "tool_name": tool_name,
                "status": "pending",
                "model_used": None,
                "tokens_used": None,
                "latency_ms": None,
                "output": None,
            })

        stages[idx]["status"] = "running"
        timeout = TOOL_TIMEOUTS.get(tool_name, default_timeout)

        if tool_name == "g13_redactor":
            try:
                await _run_g13_redactor(
                    executor, context, stages, idx, timeout, tool_results
                )
            except PipelineStageFailureError as exc:
                context[tool_name] = {"error": exc.reason}
                tool_results[tool_name] = {"error": exc.reason}
                stages[idx].update({"status": "failed", "output": {"error": exc.reason}})
                raise
            except Exception as exc:
                exc_msg = str(exc)
                context[tool_name] = {"error": exc_msg}
                tool_results[tool_name] = {"error": exc_msg}
                stages[idx].update({"status": "failed", "output": {"error": exc_msg}})
                raise PipelineStageFailureError(tool_name, exc_msg) from exc
            continue

        max_attempts = 2 if tool_name == "g12_hallazgos" else 1
        last_coherence_exc: PipelineStageFailureError | None = None

        try:
            for attempt in range(max_attempts):
                if attempt > 0 and last_coherence_exc:
                    context["coherence_retry_note"] = (
                        f"REINTENTO {attempt + 1}: el intento anterior fue rechazado por "
                        f"{last_coherence_exc.reason}. No mencione crédito, vacaciones, "
                        "onboarding ni RRHH salvo que estén en el intake."
                    )
                try:
                    res = await asyncio.wait_for(
                        executor.run_tool(tool_name, context, {}),
                        timeout=timeout,
                    )
                    output = res.get("output", {})
                    if isinstance(output, dict) and not output.get("error"):
                        validate_output_coherence(tool_name, output, context)
                    context[tool_name] = output
                    tool_results[tool_name] = res
                    stages[idx].update({
                        "status": "completed",
                        "model_used": res.get("model_used"),
                        "tokens_used": res.get("tokens_used"),
                        "latency_ms": res.get("latency_ms"),
                        "output": output,
                    })
                    context.pop("coherence_retry_note", None)
                    break
                except PipelineStageFailureError as exc:
                    last_coherence_exc = exc
                    if attempt + 1 >= max_attempts:
                        raise
        except asyncio.TimeoutError:
            exc_msg = f"Tiempo de espera agotado en {tool_name} ({timeout}s)"
            context[tool_name] = {"error": exc_msg}
            tool_results[tool_name] = {"error": exc_msg}
            stages[idx].update({"status": "failed", "output": {"error": exc_msg}})
            raise PipelineStageFailureError(tool_name, exc_msg)
        except PipelineStageFailureError as exc:
            context[tool_name] = {"error": exc.reason}
            tool_results[tool_name] = {"error": exc.reason}
            stages[idx].update({"status": "failed", "output": {"error": exc.reason}})
            raise
        except Exception as exc:
            exc_msg = str(exc)
            context[tool_name] = {"error": exc_msg}
            tool_results[tool_name] = {"error": exc_msg}
            stages[idx].update({"status": "failed", "output": {"error": exc_msg}})
            raise PipelineStageFailureError(tool_name, exc_msg) from exc

    return tool_results, stages


def persist_research_design(input_payload: dict, outputs: dict[str, Any]) -> dict:
    """Guarda outputs de diseño en input_payload para reutilización en diagnóstico."""
    payload = dict(input_payload or {})
    research = dict(payload.get("research_design") or {})
    for tool in RESEARCH_DESIGN_TOOLS:
        if tool in outputs and outputs[tool]:
            research[tool] = outputs[tool]
    payload["research_design"] = research
    for tool in RESEARCH_DESIGN_TOOLS:
        if tool in outputs:
            payload[tool] = outputs[tool]
    return payload
