"""Pipeline tool executor — Gemini only, regulatory fail-closed (no mock)."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time

from google import genai
from google.genai import types as genai_types

from api.config import Settings
from api.pipeline.llm_guard import (
    PipelineLLMUnavailableError,
    PipelineStageFailureError,
    require_gemini_key,
    validate_llm_result,
)
from api.pipeline.prompts import build_prompt, get_model_config

log = logging.getLogger("arhiax.pipeline")

MAX_RETRIES = 3
RETRY_DELAYS = [3, 8, 15]

MODEL_FALLBACK_CHAIN: dict[str, list[str]] = {
    "gemini-2.5-flash": ["gemini-2.0-flash", "gemini-1.5-flash"],
    "gemini-2.5-pro": ["gemini-2.5-flash", "gemini-2.0-flash"],
    "gemini-2.0-flash": ["gemini-2.5-flash", "gemini-1.5-flash"],
}


class PipelineExecutor:
    def __init__(self, settings: Settings):
        self.settings = settings
        require_gemini_key(settings.gemini_api_key)
        self._client = genai.Client(api_key=settings.gemini_api_key)

    async def run_tool(self, tool_name: str, context: dict, model_route: dict) -> dict:
        prompt = build_prompt(tool_name, context)
        tool_config = get_model_config(tool_name)
        model = tool_config["model"]
        max_tokens = tool_config["max_tokens"]
        temperature = tool_config["temperature"]
        result = await self._call_with_model_fallback(
            tool_name, prompt, model, max_tokens, temperature
        )
        validate_llm_result(tool_name, result)
        return result

    async def _call_with_model_fallback(
        self, tool_name: str, prompt: str, model: str, max_tokens: int, temperature: float
    ) -> dict:
        models_to_try = [model] + MODEL_FALLBACK_CHAIN.get(model, [])
        last_error: Exception | None = None

        for model_attempt in models_to_try:
            try:
                result = await self._call_gemini_with_retry(
                    tool_name, prompt, model_attempt, max_tokens, temperature
                )
                validate_llm_result(tool_name, result)
                if model_attempt != model:
                    log.info("Tool %s succeeded with fallback model %s", tool_name, model_attempt)
                return result
            except (PipelineStageFailureError, PipelineLLMUnavailableError):
                raise
            except Exception as exc:
                last_error = exc
                log.warning("Tool %s failed on model %s: %s", tool_name, model_attempt, exc)

        reason = str(last_error)[:240] if last_error else "todos los modelos Gemini fallaron"
        raise PipelineStageFailureError(tool_name, reason)

    async def _call_gemini_with_retry(
        self, tool_name: str, prompt: str, model: str, max_tokens: int, temperature: float
    ) -> dict:
        last_error: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                return await self._call_gemini(
                    tool_name, prompt, model, max_tokens, temperature, attempt=attempt
                )
            except PipelineLLMUnavailableError:
                raise
            except PipelineStageFailureError as exc:
                if attempt < MAX_RETRIES - 1 and _is_retryable_llm_output_error(exc):
                    delay = RETRY_DELAYS[attempt]
                    log.warning(
                        "Tool %s model %s attempt %d output error (%s), retrying in %ds...",
                        tool_name,
                        model,
                        attempt + 1,
                        exc.reason[:80],
                        delay,
                    )
                    await asyncio.sleep(delay)
                    continue
                raise
            except Exception as exc:
                last_error = exc
                err_str = str(exc).lower()
                is_retryable = any(
                    k in err_str
                    for k in ("connection", "remote", "timeout", "503", "429", "reset", "eof", "overload")
                )
                if is_retryable and attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAYS[attempt]
                    log.warning(
                        "Tool %s model %s attempt %d failed (%s), retrying in %ds...",
                        tool_name,
                        model,
                        attempt + 1,
                        str(exc)[:80],
                        delay,
                    )
                    await asyncio.sleep(delay)
                    continue
                break
        raise PipelineStageFailureError(
            tool_name,
            str(last_error)[:240] if last_error else "error desconocido en Gemini",
        )

    async def _call_gemini(
        self, tool_name: str, prompt: str, model: str, max_tokens: int, temperature: float,
        attempt: int = 0,
    ) -> dict:
        t0 = time.monotonic()
        effective_temp = max(0.1, float(temperature) - (attempt * 0.12))
        response = await self._client.aio.models.generate_content(
            model=model,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                max_output_tokens=min(max_tokens, 16384),
                temperature=effective_temp,
                response_mime_type="application/json",
                thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
            ),
        )
        latency_ms = int((time.monotonic() - t0) * 1000)

        if response.candidates:
            finish = str(response.candidates[0].finish_reason)
            if "SAFETY" in finish or "RECITATION" in finish:
                raise PipelineStageFailureError(tool_name, f"bloqueado por Gemini: {finish}")
            if "MAX_TOKENS" in finish:
                raise PipelineStageFailureError(
                    tool_name,
                    f"respuesta truncada por límite de tokens ({max_tokens}); "
                    "el JSON quedó incompleto",
                )

        raw = response.text
        if not raw:
            raise PipelineStageFailureError(tool_name, "respuesta vacía de Gemini")

        output = _parse_json(raw)
        if isinstance(output, dict) and output.keys() == {"raw_output"}:
            raise PipelineStageFailureError(tool_name, "JSON inválido en respuesta Gemini")

        if "raw_output" in output and len(output) == 1:
            fixed = _fix_encoding(raw)
            if fixed != raw:
                output = _parse_json(fixed)
                if isinstance(output, dict) and output.keys() == {"raw_output"}:
                    raise PipelineStageFailureError(tool_name, "JSON inválido tras corrección de encoding")

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


def _fix_encoding(text: str) -> str:
    try:
        return text.encode("latin1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return text


def _is_retryable_llm_output_error(exc: PipelineStageFailureError) -> bool:
    reason = exc.reason.lower()
    return any(
        k in reason
        for k in (
            "json inválido",
            "json invalido",
            "truncada",
            "respuesta vacía",
            "respuesta vacia",
            "incompleto",
        )
    )


def _parse_json(raw: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    stripped = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
    stripped = re.sub(r"\s*```$", "", stripped.strip())
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = raw[start : end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    if start != -1:
        candidate = raw[start:]
        for trim in range(0, min(500, len(candidate)), 10):
            try:
                return json.loads(candidate[: len(candidate) - trim] if trim > 0 else candidate)
            except json.JSONDecodeError:
                continue

        repaired = _repair_truncated_json(candidate)
        if repaired is not None:
            log.warning("_parse_json: recovered truncated JSON (%d chars)", len(raw))
            return repaired

    log.warning("_parse_json: could not parse JSON (%d chars)", len(raw))
    return {"raw_output": raw[:12000]}


def _repair_truncated_json(candidate: str) -> dict | None:
    """Best-effort repair of JSON truncated mid-structure (e.g. MAX_TOKENS).

    Trims to the last complete token and closes any open strings/brackets so the
    partial LLM output can still be used instead of discarded.
    """
    text = candidate.rstrip()
    if text.endswith(","):
        text = text[:-1]

    in_string = False
    escaped = False
    stack: list[str] = []
    for ch in text:
        if escaped:
            escaped = False
            continue
        if ch == "\\":
            escaped = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in "{[":
            stack.append(ch)
        elif ch == "}":
            if stack and stack[-1] == "{":
                stack.pop()
        elif ch == "]":
            if stack and stack[-1] == "[":
                stack.pop()

    if in_string:
        text += '"'
    closers = "".join("}" if b == "{" else "]" for b in reversed(stack))
    text += closers

    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None
