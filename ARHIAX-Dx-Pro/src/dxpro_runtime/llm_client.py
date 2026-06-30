"""LLM client — soporta Anthropic Claude y Google Gemini con la misma interfaz."""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

MODEL_SONNET = "claude-sonnet-4-6"
MODEL_OPUS = "claude-opus-4-7"

# Modelos Gemini equivalentes
MODEL_GEMINI_PRO = "gemini-1.5-pro"
MODEL_GEMINI_FLASH = "gemini-1.5-flash"

_MAX_TOKENS = 8192


class LlmClient:
    """
    Cliente LLM unificado. Detecta automáticamente el proveedor por la clave:
    - Claves que empiezan con 'AIza' → Google Gemini
    - Cualquier otra → Anthropic Claude
    """

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._provider = "gemini" if api_key.startswith("AIza") else "anthropic"
        self._client: Any = None
        self._init_client()

    def _init_client(self) -> None:
        if self._provider == "gemini":
            try:
                import google.generativeai as genai  # noqa: PLC0415
                genai.configure(api_key=self._api_key)
                self._genai = genai
            except ImportError as exc:
                raise RuntimeError(
                    "google-generativeai no está instalado. Ejecuta: pip install google-generativeai"
                ) from exc
        else:
            try:
                import anthropic  # noqa: PLC0415
                self._client = anthropic.Anthropic(api_key=self._api_key)
            except ImportError as exc:
                raise RuntimeError(
                    "anthropic no está instalado. Ejecuta: pip install anthropic"
                ) from exc

    def _resolve_model(self, model: str) -> str:
        """Mapea modelos Claude a Gemini cuando se usa Gemini."""
        if self._provider != "gemini":
            return model
        # Mapeo Claude → Gemini
        mapping = {
            MODEL_SONNET: MODEL_GEMINI_PRO,
            MODEL_OPUS: MODEL_GEMINI_PRO,
            MODEL_GEMINI_PRO: MODEL_GEMINI_PRO,
            MODEL_GEMINI_FLASH: MODEL_GEMINI_FLASH,
        }
        return mapping.get(model, MODEL_GEMINI_PRO)

    def complete(self, *, model: str, system: str, user: str, trace_id: str = "") -> dict[str, Any]:
        """Envía una completación de texto y retorna el JSON parseado."""
        resolved_model = self._resolve_model(model)

        if self._provider == "gemini":
            result = self._complete_gemini(resolved_model, system, user)
        else:
            result = self._complete_anthropic(model, system, user, trace_id)

        self._log_call(trace_id=trace_id, model=resolved_model)
        return result

    def complete_with_vision(
        self,
        *,
        model: str,
        system: str,
        text_prompt: str,
        images: list[dict[str, str]],
        trace_id: str = "",
    ) -> dict[str, Any]:
        """Completación multimodal con imágenes base64."""
        resolved_model = self._resolve_model(model)

        if self._provider == "gemini":
            result = self._complete_gemini_vision(resolved_model, system, text_prompt, images)
        else:
            result = self._complete_anthropic_vision(model, system, text_prompt, images, trace_id)

        self._log_call(trace_id=trace_id, model=resolved_model)
        return result

    # ── Anthropic ─────────────────────────────────────────────────────────────

    def _complete_anthropic(self, model: str, system: str, user: str, trace_id: str) -> dict[str, Any]:
        response = self._client.messages.create(
            model=model,
            max_tokens=_MAX_TOKENS,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user}],
        )
        usage = response.usage
        if trace_id:
            try:
                from dxpro_runtime.logging_config import log_llm_call
                log_llm_call(trace_id=trace_id, model=model,
                             input_tokens=usage.input_tokens, output_tokens=usage.output_tokens)
            except Exception:
                pass
        return self._parse_json(response.content[0].text, model)

    def _complete_anthropic_vision(self, model: str, system: str, text_prompt: str,
                                    images: list[dict[str, str]], trace_id: str) -> dict[str, Any]:
        content: list[dict[str, Any]] = []
        for img in images:
            content.append({"type": "image", "source": {
                "type": "base64", "media_type": img["media_type"], "data": img["data"],
            }})
        content.append({"type": "text", "text": text_prompt})
        response = self._client.messages.create(
            model=model, max_tokens=_MAX_TOKENS,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": content}],
        )
        usage = response.usage
        if trace_id:
            try:
                from dxpro_runtime.logging_config import log_llm_call
                log_llm_call(trace_id=trace_id, model=model,
                             input_tokens=usage.input_tokens, output_tokens=usage.output_tokens)
            except Exception:
                pass
        return self._parse_json(response.content[0].text, model)

    # ── Gemini ────────────────────────────────────────────────────────────────

    def _complete_gemini(self, model: str, system: str, user: str) -> dict[str, Any]:
        genai_model = self._genai.GenerativeModel(
            model_name=model,
            system_instruction=system,
            generation_config=self._genai.GenerationConfig(
                response_mime_type="application/json",
                max_output_tokens=_MAX_TOKENS,
            ),
        )
        response = genai_model.generate_content(user)
        return self._parse_json(response.text, model)

    def _complete_gemini_vision(self, model: str, system: str, text_prompt: str,
                                 images: list[dict[str, str]]) -> dict[str, Any]:
        import base64
        genai_model = self._genai.GenerativeModel(
            model_name=model,
            system_instruction=system,
            generation_config=self._genai.GenerationConfig(
                response_mime_type="application/json",
                max_output_tokens=_MAX_TOKENS,
            ),
        )
        parts: list[Any] = []
        for img in images:
            parts.append({
                "inline_data": {
                    "mime_type": img["media_type"],
                    "data": img["data"],
                }
            })
        parts.append(text_prompt)
        response = genai_model.generate_content(parts)
        return self._parse_json(response.text, model)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _log_call(self, *, trace_id: str, model: str) -> None:
        if not trace_id:
            return
        try:
            from dxpro_runtime.logging_config import log_llm_call
            log_llm_call(trace_id=trace_id, model=model, input_tokens=0, output_tokens=0)
        except Exception:
            pass

    def _parse_json(self, text: str, model: str) -> dict[str, Any]:
        """Extrae y parsea JSON de la respuesta del LLM."""
        text = text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            logger.error("LLM retornó respuesta no-JSON del modelo %s: %s", model, text[:200])
            raise ValueError(f"Respuesta del LLM no es JSON válido: {exc}") from exc

    @property
    def provider(self) -> str:
        return self._provider
