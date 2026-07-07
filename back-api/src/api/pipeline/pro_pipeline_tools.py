"""Utilidades compartidas del pipeline Pro: G01–G08 + análisis post-encuesta."""
from __future__ import annotations

import asyncio
import json
from typing import Any

from api.pipeline.hypothesis_pack import build_hypothesis_pack, g05_from_paquete

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
    symptom = extra.get("symptom") or payload.get("symptom") or ""
    if not symptom and paquete:
        symptom = str(paquete[0].get("enunciado") or "")

    roles = body.get("roles") or payload.get("roles") or ["executive", "operations", "technology"]
    dimensions = body.get("dimensions") or payload.get("dimensions") or ["strategy", "process", "technology"]

    context: dict[str, Any] = {
        "organization_name": client_name or body.get("client_name", ""),
        "domain": domain or body.get("domain", ""),
        "subprocess": extra.get("subprocess") or payload.get("subprocess") or domain,
        "objective": symptom,
        "size_org": str(extra.get("size_org") or payload.get("size_org") or "51-200"),
        "paquete_hipotesis": paquete,
        "corpus_incidentes": [
            inc.get("texto")
            for fd in field_data.values()
            for inc in (fd.get("corpus_incidentes") or [])
            if isinstance(inc, dict) and inc.get("texto")
        ],
    }

    g05 = payload.get("g05_brechas") or g05_from_paquete(paquete, field_data)
    context["g05_brechas"] = g05

    g02 = payload.get("g02_configurador")
    if not g02:
        g02 = {
            "roles": [{"id": r, "label": r} for r in roles],
            "dimensions": [{"id": d, "name": d} for d in dimensions],
        }
    context["g02_configurador"] = g02

    return context


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

        try:
            res = await asyncio.wait_for(
                executor.run_tool(tool_name, context, {}),
                timeout=timeout,
            )
            output = res.get("output", {})
            context[tool_name] = output
            tool_results[tool_name] = res
            stages[idx].update({
                "status": "completed",
                "model_used": res.get("model_used"),
                "tokens_used": res.get("tokens_used"),
                "latency_ms": res.get("latency_ms"),
                "output": output,
            })
        except asyncio.TimeoutError:
            exc_msg = f"Tiempo de espera agotado en {tool_name} ({timeout}s)"
            context[tool_name] = {"error": exc_msg}
            tool_results[tool_name] = {"error": exc_msg}
            stages[idx].update({"status": "failed", "output": {"error": exc_msg}})
        except Exception as exc:
            context[tool_name] = {"error": str(exc)}
            tool_results[tool_name] = {"error": str(exc)}
            stages[idx].update({"status": "failed", "output": {"error": str(exc)}})

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
