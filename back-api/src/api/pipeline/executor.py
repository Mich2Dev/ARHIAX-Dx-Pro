"""Pipeline tool executor — calls Gemini 2.5 Flash (primary) or mock (fallback)."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time

from google import genai
from google.genai import types as genai_types

from api.config import Settings
from api.pipeline.prompts import build_prompt, get_model_config

log = logging.getLogger("arhiax.pipeline")

# Retry config
MAX_RETRIES = 3
RETRY_DELAYS = [3, 8, 15]  # seconds between retries (increased)

# Model fallback chain — if primary is overloaded, try these in order
# gemini-2.5-flash puede estar en preview — usamos 2.0-flash como fallback estable
MODEL_FALLBACK_CHAIN: dict[str, list[str]] = {
    "gemini-2.5-flash": ["gemini-2.0-flash", "gemini-1.5-flash"],
    "gemini-2.5-pro":   ["gemini-2.5-flash", "gemini-2.0-flash"],
    "gemini-2.0-flash": ["gemini-2.5-flash", "gemini-1.5-flash"],
}


class PipelineExecutor:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client: genai.Client | None = None
        if settings.gemini_api_key:
            self._client = genai.Client(api_key=settings.gemini_api_key)

    async def run_tool(self, tool_name: str, context: dict, model_route: dict) -> dict:
        prompt = build_prompt(tool_name, context)
        tool_config = get_model_config(tool_name)
        model = tool_config["model"]
        max_tokens = tool_config["max_tokens"]
        temperature = tool_config["temperature"]
        if self._client:
            return await self._call_with_model_fallback(tool_name, prompt, model, max_tokens, temperature)
        return self._mock_response(tool_name, "mock-no-key")

    async def _call_with_model_fallback(
        self, tool_name: str, prompt: str, model: str, max_tokens: int, temperature: float
    ) -> dict:
        """Try primary model with retries, then fallback models, then mock."""
        models_to_try = [model] + MODEL_FALLBACK_CHAIN.get(model, [])

        for model_attempt in models_to_try:
            result = await self._call_gemini_with_retry(tool_name, prompt, model_attempt, max_tokens, temperature)
            # If result is NOT a mock/error, return it
            model_used = result.get("model_used", "")
            if not model_used.startswith("gemini-error") and not model_used.startswith("mock"):
                if model_attempt != model:
                    log.info("Tool %s succeeded with fallback model %s", tool_name, model_attempt)
                return result
            log.warning("Tool %s failed on model %s, trying next...", tool_name, model_attempt)

        # All models exhausted — return last result (mock)
        return result  # type: ignore[return-value]

    async def _call_gemini_with_retry(
        self, tool_name: str, prompt: str, model: str, max_tokens: int, temperature: float
    ) -> dict:
        """Call one specific Gemini model with retries on transient errors."""
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                return await self._call_gemini(tool_name, prompt, model, max_tokens, temperature)
            except Exception as exc:
                last_error = exc
                err_str = str(exc).lower()
                is_retryable = any(k in err_str for k in [
                    "connection", "remote", "timeout", "503", "429", "reset", "eof", "overload"
                ])
                if is_retryable and attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAYS[attempt]
                    log.warning(
                        "Tool %s model %s attempt %d failed (%s), retrying in %ds...",
                        tool_name, model, attempt + 1, str(exc)[:80], delay
                    )
                    await asyncio.sleep(delay)
                    continue
                break
        return self._mock_response(tool_name, f"gemini-error: {str(last_error)[:80]}")

    async def _call_gemini(self, tool_name: str, prompt: str, model: str, max_tokens: int, temperature: float) -> dict:
        t0 = time.monotonic()
        response = await self._client.aio.models.generate_content(
            model=model,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                max_output_tokens=min(max_tokens, 16384),
                temperature=temperature,
                response_mime_type="application/json",
            ),
        )
        latency_ms = int((time.monotonic() - t0) * 1000)

        # Check finish reason — raise on blocking reasons so retry/fallback kicks in
        if response.candidates:
            finish = str(response.candidates[0].finish_reason)
            if "SAFETY" in finish or "RECITATION" in finish:
                raise ValueError(f"Blocked by Gemini: {finish}")

        raw = response.text
        if not raw:
            # Empty response — treat as retryable
            raise ValueError("Empty response from Gemini (text=None)")

        # Try direct parse first — with response_mime_type=application/json,
        # Gemini returns valid UTF-8 JSON. Only attempt encoding fix if that fails.
        output = _parse_json(raw)
        if "raw_output" in output and len(output) == 1:
            # Direct parse failed — try encoding fix (handles rare mojibake)
            fixed = _fix_encoding(raw)
            if fixed != raw:
                output = _parse_json(fixed)
        tokens = None
        if response.usage_metadata:
            tokens = response.usage_metadata.total_token_count
        return {
            "tool": tool_name,
            "model_used": model,
            "tokens_used": tokens,
            "latency_ms": latency_ms,
            "output": output,
        }

    def _mock_response(self, tool_name: str, model_label: str) -> dict:
        mock_outputs: dict[str, dict] = {
            "g01_receptor":     {"session_id": "mock-session", "mandate_confirmed": True, "diagnostic_type": "organizational", "activated_modules": []},
            "g02_configurador": {"domain_config": {}, "benchmarks": [], "kpis": [], "frameworks": ["ISO 9001"]},
            "g03_cienciometro": {"literature_map": [{"title": "Mock Study", "relevance": "HIGH", "key_finding": "Mock finding"}]},
            "g04_cartografo":   {"process_map": {}, "actors": [], "flows": [], "capabilities": []},
            "g05_brechas":      {"gaps": ["Brecha 1", "Brecha 2"], "hypotheses": ["H1", "H2"], "priority_areas": ["Área 1"]},
            "g06_bpmn_architect":{"bpmn_description": "AS-IS mock", "pools": [], "lanes": [], "tasks": [], "gateways": [], "critical_paths": []},
            "g07_cuellos":      {"bottlenecks": [{"name": "Cuello mock", "impacto_horas": 10, "severidad": "HIGH"}], "total_opportunity_loss": "Mock"},
            "g08_optimizador":  {"improvement_options": [], "roi_scenarios": []},
            "g09a_preguntas":   {"questions": [{"id": "Q1", "text": "Pregunta mock", "roles": ["Estratégico", "Táctico", "Operativo"], "type": "likert_5", "dimension": "DIM-01"}]},
            "g09b_ramificacion":{"role_tracks": {"Estratégico": {"question_ids": ["Q1"], "estimated_minutes": 10}, "Táctico": {"question_ids": ["Q1"], "estimated_minutes": 12}, "Operativo": {"question_ids": ["Q1"], "estimated_minutes": 8}}, "branching_rules": []},
            "g09c_validacion":  {"irr_alpha_estimated": 0.78, "irr_status": "APROBADO", "instrument_quality": "ALTA"},
            "g10a_scoring":     {"scoring_summary": {"overall_score": 62, "overall_percentile": 35, "benchmark_score": 78}, "dimension_scores": [], "role_scores": {"Estratégico": {"score": 71}, "Táctico": {"score": 63}, "Operativo": {"score": 52}}, "delta_sigma": {"max_gap": 2.3, "gap_pairs": []}},
            "g10b_psicometria": {"cronbach_alpha_overall": 0.82, "internal_consistency": "BUENA", "instrument_reliability": "ALTA"},
            "g11a_bayesiano":   {"confirmed_hypotheses": ["H01"], "rejected_hypotheses": [], "critical_perception_gaps": [], "bayesian_summary": "Análisis mock"},
            "g11b_nlp":         {"themes": [], "sentiment_by_role": {}, "nlp_summary": "NLP mock"},
            "irr_calculator":   {"krippendorff_alpha": 0.82, "irr_status": "APROBADO", "promotion_signal": True},
            "scoring_engine":   {"normalized_scores": {}, "aggregated_dimensions": {}, "percentile_ranks": {}},
            "g12_hallazgos":    {"findings_matrix": [{"id": "F01", "finding": "Hallazgo mock", "priority": "ALTA", "impact_score": 7, "bayesian_confidence": 0.85}], "problem_statements": [{"statement": "Problema mock identificado."}], "strategic_recommendations": [{"recommendation": "Acción recomendada mock", "timeframe": "90_dias"}], "executive_summary_findings": "Resumen mock de hallazgos."},
            "g13_redactor":     {"executive_summary": "Resumen ejecutivo mock del diagnóstico.", "main_findings": [], "strategic_recommendations": [], "next_steps": ["Paso 1 mock"], "roadmap": {"days_90": {"theme": "Estabilización", "actions": ["Acción 1"]}, "days_180": {"theme": "Optimización", "actions": ["Acción 2"]}, "days_365": {"theme": "Transformación", "actions": ["Acción 3"]}}, "full_narrative": "Narrativa mock."},
            "g14_qa_control":   {"qa_score": 91, "quality_dimensions": {"coherencia_interna": {"score": 18, "max": 20}, "completitud": {"score": 19, "max": 20}, "claridad_ejecutiva": {"score": 18, "max": 20}, "evidencia": {"score": 18, "max": 20}, "accionabilidad": {"score": 18, "max": 20}}, "issues_found": [], "approved_for_rendering": True, "qa_notes": "QA mock aprobado"},
            "docx_generator":   {"document_sections": [], "metadata": {}, "formatting_notes": "Mock"},
            "academic_search":  {"sources": []},
            "web_search":       {"sector_context": "Mock", "trends": [], "benchmarks": [], "regulatory_context": "Mock"},
            "bpmn_generator":   {"bpmn_xml": "<definitions/>", "diagram_elements": [], "validation_status": "valid"},
        }
        return {
            "tool": tool_name,
            "model_used": model_label,
            "tokens_used": 0,
            "latency_ms": 50,
            "output": mock_outputs.get(tool_name, {"result": "mock"}),
        }


def _fix_encoding(text: str) -> str:
    """Fix mojibake encoding issues from Gemini responses."""
    try:
        # Try to fix latin1 → utf8 mojibake
        return text.encode("latin1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return text


def _parse_json(raw: str) -> dict:
    """Parse JSON from Gemini response, handling various wrapping formats."""
    # 1. Direct parse (fastest path — works when response_mime_type=application/json)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # 2. Strip markdown code fences
    stripped = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
    stripped = re.sub(r"\s*```$", "", stripped.strip())
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    # 3. Find the first '{' and last '}' — handles leading/trailing text
    start = raw.find("{")
    end   = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = raw[start:end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # 4. Try to fix truncated JSON by finding the last complete top-level key
    # This handles cases where Gemini hits max_output_tokens mid-JSON
    if start != -1:
        candidate = raw[start:]
        # Try progressively shorter substrings from the end
        for trim in range(0, min(500, len(candidate)), 10):
            try:
                return json.loads(candidate[:len(candidate) - trim] if trim > 0 else candidate)
            except json.JSONDecodeError:
                continue

    # 5. Last resort — store raw for debugging (increased limit)
    log.warning("_parse_json: could not parse JSON, storing raw_output (%d chars)", len(raw))
    return {"raw_output": raw[:12000]}
