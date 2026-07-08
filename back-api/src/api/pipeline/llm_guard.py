"""Regulatory fail-closed guards for LLM pipeline stages — no mock, no silent fallback."""

from __future__ import annotations

import json
import re
from typing import Any

_MOCK_MARKERS = re.compile(
    r"\b(mock|mock-no-key|placeholder|lorem ipsum|pendiente de completar)\b",
    re.IGNORECASE,
)


class PipelineLLMError(Exception):
    """Base error for governed pipeline LLM failures."""


class PipelineLLMUnavailableError(PipelineLLMError):
    """Raised when GEMINI_API_KEY is missing or the LLM client cannot be used."""


class PipelineStageFailureError(PipelineLLMError):
    """Raised when a pipeline stage cannot produce a valid LLM result."""

    def __init__(self, tool_name: str, reason: str):
        self.tool_name = tool_name
        self.reason = reason
        super().__init__(f"{tool_name}: {reason}")


def require_gemini_key(api_key: str) -> None:
    if not (api_key or "").strip():
        raise PipelineLLMUnavailableError(
            "GEMINI_API_KEY no configurada. El pipeline regulatorio no opera sin LLM real."
        )


def validate_llm_result(tool_name: str, result: dict[str, Any]) -> None:
    """Reject mock labels, error labels, empty output, or mock-like content."""
    model_used = str(result.get("model_used") or "").strip()
    if not model_used:
        raise PipelineStageFailureError(tool_name, "respuesta sin model_used")
    if model_used.startswith("mock") or model_used.startswith("gemini-error"):
        raise PipelineStageFailureError(tool_name, f"modelo inválido: {model_used}")

    output = result.get("output")
    if output is None:
        raise PipelineStageFailureError(tool_name, "output vacío")
    if isinstance(output, dict) and output.get("error"):
        raise PipelineStageFailureError(tool_name, str(output["error"]))

    try:
        blob = json.dumps(output, ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        raise PipelineStageFailureError(tool_name, f"output no serializable: {exc}") from exc

    if _MOCK_MARKERS.search(blob):
        raise PipelineStageFailureError(tool_name, "output contiene marcadores mock/placeholder")


def stages_failed(stages: list[dict] | None) -> list[dict]:
    return [s for s in (stages or []) if isinstance(s, dict) and s.get("status") == "failed"]


def assert_pipeline_stages_ok(
    stages: list[dict] | None,
    required_tools: list[str] | None = None,
) -> None:
    failed = stages_failed(stages)
    if failed:
        stage = failed[0]
        tool = str(stage.get("tool_name") or "unknown")
        out = stage.get("output")
        reason = out.get("error") if isinstance(out, dict) else str(out or "etapa fallida")
        raise PipelineStageFailureError(tool, str(reason))

    if not required_tools:
        return

    by_tool = {s.get("tool_name"): s for s in (stages or []) if isinstance(s, dict)}
    for tool in required_tools:
        stage = by_tool.get(tool)
        if not stage or stage.get("status") != "completed":
            raise PipelineStageFailureError(tool, "etapa no completada con LLM real")
