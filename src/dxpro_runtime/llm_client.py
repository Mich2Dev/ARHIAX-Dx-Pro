"""Thin Anthropic client wrapper with prompt caching and JSON extraction."""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

MODEL_SONNET = "claude-sonnet-4-6"
MODEL_OPUS = "claude-opus-4-7"

_MAX_TOKENS = 8192


class LlmClient:
    """Wraps anthropic.Anthropic with prompt caching and structured JSON output."""

    def __init__(self, api_key: str) -> None:
        try:
            import anthropic  # noqa: PLC0415
        except ImportError as exc:
            raise RuntimeError("anthropic package is not installed. Run: pip install anthropic") from exc
        self._client = anthropic.Anthropic(api_key=api_key)

    def complete(self, *, model: str, system: str, user: str) -> dict[str, Any]:
        """Send a text completion and return the parsed JSON response."""
        response = self._client.messages.create(
            model=model,
            max_tokens=_MAX_TOKENS,
            system=[
                {
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user}],
        )
        return self._parse_json(response.content[0].text, model)

    def complete_with_vision(
        self,
        *,
        model: str,
        system: str,
        text_prompt: str,
        images: list[dict[str, str]],
    ) -> dict[str, Any]:
        """Send a multimodal completion with base64 images and return parsed JSON.

        Each entry in `images` must have keys: "data" (base64 string) and
        "media_type" (e.g. "image/jpeg", "image/png").
        """
        content: list[dict[str, Any]] = []
        for img in images:
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": img["media_type"],
                        "data": img["data"],
                    },
                }
            )
        content.append({"type": "text", "text": text_prompt})

        response = self._client.messages.create(
            model=model,
            max_tokens=_MAX_TOKENS,
            system=[
                {
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": content}],
        )
        return self._parse_json(response.content[0].text, model)

    def _parse_json(self, text: str, model: str) -> dict[str, Any]:
        """Extract and parse JSON from LLM response text."""
        text = text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            logger.error("LLM returned non-JSON response from model %s: %s", model, text[:200])
            raise ValueError(f"LLM response is not valid JSON: {exc}") from exc
