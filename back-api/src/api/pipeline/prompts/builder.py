"""Assembles TOOL_PROMPTS dict and build_prompt() from all sub-modules."""
from __future__ import annotations

import json
import string

from .intake   import G01_RECEPTOR, G02_CONFIGURADOR, G05_BRECHAS
from .research import G03_CIENCIOMETRO, G04_CARTOGRAFO, ACADEMIC_SEARCH, WEB_SEARCH
from .design   import G06_BPMN_ARCHITECT, G07_CUELLOS, G08_OPTIMIZADOR, BPMN_GENERATOR
from .survey   import G09A_PREGUNTAS, G09B_RAMIFICACION, G09C_VALIDACION
from .analysis import (
    G10A_SCORING, G10B_PSICOMETRIA, G11A_BAYESIANO, G11B_NLP,
    IRR_CALCULATOR, SCORING_ENGINE,
)
from .reporting import G12_HALLAZGOS, G13_REDACTOR, G14_QA_CONTROL, DOCX_GENERATOR

TOOL_PROMPTS: dict[str, str] = {
    "g01_receptor":      G01_RECEPTOR,
    "g02_configurador":  G02_CONFIGURADOR,
    "g03_cienciometro":  G03_CIENCIOMETRO,
    "g04_cartografo":    G04_CARTOGRAFO,
    "g05_brechas":       G05_BRECHAS,
    "g06_bpmn_architect":G06_BPMN_ARCHITECT,
    "g07_cuellos":       G07_CUELLOS,
    "g08_optimizador":   G08_OPTIMIZADOR,
    "g09a_preguntas":    G09A_PREGUNTAS,
    "g09b_ramificacion": G09B_RAMIFICACION,
    "g09c_validacion":   G09C_VALIDACION,
    "g10a_scoring":      G10A_SCORING,
    "g10b_psicometria":  G10B_PSICOMETRIA,
    "g11a_bayesiano":    G11A_BAYESIANO,
    "g11b_nlp":          G11B_NLP,
    "irr_calculator":    IRR_CALCULATOR,
    "scoring_engine":    SCORING_ENGINE,
    "g12_hallazgos":     G12_HALLAZGOS,
    "g13_redactor":      G13_REDACTOR,
    "g14_qa_control":    G14_QA_CONTROL,
    "docx_generator":    DOCX_GENERATOR,
    "academic_search":   ACADEMIC_SEARCH,
    "web_search":        WEB_SEARCH,
    "bpmn_generator":    BPMN_GENERATOR,
}



# Per-tool context size limits (chars).
# Keys that carry large payloads (survey responses, full stage outputs) get more room.
_LARGE_CONTEXT_KEYS = {
    "survey_responses_real",   # raw JSON of all survey answers — needs full fidelity
    "g09a_preguntas",          # full instrument (18 questions + dimensions)
    "g09b_ramificacion",       # branching rules
    "g09c_validacion",         # validation output
    "g05_brechas",             # hypotheses used by G10a/G11a
    "g10a_scoring",            # scoring used by G10b/G11a/IRR
    "g11a_bayesiano",          # bayesian analysis used by G12/G13
    "g12_hallazgos",           # findings used by G13/G14
    "g13_redactor",            # narrative used by G14/docx — LARGEST output
}
_DEFAULT_LIMIT = 4000    # chars for regular context keys
_LARGE_LIMIT   = 12000   # chars for large-payload keys
_XLARGE_LIMIT  = 20000   # chars for G13 (narrative) which feeds G14 QA

# G13 output is the largest in the pipeline — G14 needs the full narrative to QA it
_XLARGE_CONTEXT_KEYS = {"g13_redactor"}


def build_prompt(tool_name: str, context: dict) -> str:
    """Build the prompt for a tool, injecting accumulated context.

    Context values are serialised to strings and truncated per-key so that
    critical payloads (survey responses, instrument, hypotheses) are never
    silently cut short while keeping the total prompt within model limits.
    """
    template = TOOL_PROMPTS.get(
        tool_name,
        "Ejecuta la herramienta con el contexto disponible. Responde en JSON.",
    )

    safe_ctx: dict[str, str] = {}
    for k, v in context.items():
        if k == "tool_name":
            continue
        if k in _XLARGE_CONTEXT_KEYS:
            limit = _XLARGE_LIMIT
        elif k in _LARGE_CONTEXT_KEYS:
            limit = _LARGE_LIMIT
        else:
            limit = _DEFAULT_LIMIT

        # If a previous stage stored raw_output (failed JSON parse), try to re-parse it
        # so downstream agents get structured data instead of a raw string blob
        if isinstance(v, dict) and "raw_output" in v and len(v) == 1:
            raw_str = v["raw_output"]
            start = raw_str.find("{")
            end   = raw_str.rfind("}")
            if start != -1 and end > start:
                try:
                    v = json.loads(raw_str[start:end + 1])
                except (json.JSONDecodeError, Exception):
                    pass  # keep original

        if isinstance(v, (dict, list)):
            serialised = json.dumps(v, ensure_ascii=False, indent=2)
        else:
            serialised = str(v)
        if len(serialised) > limit:
            # Truncate but add a visible marker so the LLM knows data was cut
            safe_ctx[k] = serialised[:limit] + "\n... [TRUNCADO — datos adicionales omitidos por límite de contexto]"
        else:
            safe_ctx[k] = serialised

    # Fill missing keys with empty string to avoid KeyError
    keys_needed = [fn for _, fn, _, _ in string.Formatter().parse(template) if fn]
    for k in keys_needed:
        if k not in safe_ctx:
            safe_ctx[k] = ""

    try:
        return template.format(**safe_ctx)
    except Exception:
        return template
