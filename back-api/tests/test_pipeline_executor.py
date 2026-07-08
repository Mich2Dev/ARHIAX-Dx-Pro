"""Tests for regulatory fail-closed pipeline executor."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from api.pipeline.executor import PipelineExecutor, _parse_json, _fix_encoding
from api.pipeline.llm_guard import (
    PipelineLLMUnavailableError,
    PipelineStageFailureError,
    require_gemini_key,
    validate_llm_result,
)
from api.config import Settings


@pytest.fixture
def executor_no_key():
    s = MagicMock(spec=Settings)
    s.gemini_api_key = ""
    return s


@pytest.fixture
def executor_with_key():
    s = MagicMock(spec=Settings)
    s.gemini_api_key = "fake-key-for-testing"
    return PipelineExecutor(s)


def test_require_gemini_key_missing():
    with pytest.raises(PipelineLLMUnavailableError):
        require_gemini_key("")


def test_validate_rejects_mock_label():
    with pytest.raises(PipelineStageFailureError):
        validate_llm_result("g01_receptor", {"model_used": "mock-no-key", "output": {"ok": True}})


def test_validate_rejects_mock_content():
    with pytest.raises(PipelineStageFailureError):
        validate_llm_result(
            "g12_hallazgos",
            {"model_used": "gemini-2.0-flash", "output": {"finding": "Hallazgo mock"}},
        )


def test_validate_accepts_real_result():
    validate_llm_result(
        "g01_receptor",
        {"model_used": "gemini-2.0-flash", "output": {"mandate_confirmed": True}},
    )


def test_executor_init_without_key_raises(executor_no_key):
    with pytest.raises(PipelineLLMUnavailableError):
        PipelineExecutor(executor_no_key)


@pytest.mark.asyncio
async def test_run_tool_without_key_not_reachable(executor_no_key):
    with pytest.raises(PipelineLLMUnavailableError):
        PipelineExecutor(executor_no_key)


@pytest.mark.asyncio
async def test_fallback_to_alternate_model(executor_with_key):
    call_count = {"n": 0}

    async def mock_call(tool_name, prompt, model, max_tokens, temperature):
        call_count["n"] += 1
        if model == "gemini-2.5-flash":
            raise RuntimeError("503 UNAVAILABLE overloaded")
        return {
            "tool": tool_name,
            "model_used": model,
            "tokens_used": 100,
            "latency_ms": 500,
            "output": {"mandate_confirmed": True},
        }

    with patch.object(executor_with_key, "_call_gemini_with_retry", side_effect=mock_call):
        result = await executor_with_key.run_tool("g01_receptor", {}, {})

    assert result["model_used"] == "gemini-2.0-flash"
    assert call_count["n"] == 2


@pytest.mark.asyncio
async def test_all_models_fail_raises(executor_with_key):
    async def always_fail(tool_name, prompt, model, max_tokens, temperature):
        raise RuntimeError("503 overloaded")

    with patch.object(executor_with_key, "_call_gemini_with_retry", side_effect=always_fail):
        with pytest.raises(PipelineStageFailureError):
            await executor_with_key.run_tool("g01_receptor", {}, {})


def test_parse_valid_json():
    result = _parse_json('{"key": "value", "number": 42}')
    assert result["key"] == "value"
    assert result["number"] == 42


def test_parse_json_in_markdown():
    raw = '```json\n{"status": "ok"}\n```'
    result = _parse_json(raw)
    assert result["status"] == "ok"


def test_parse_invalid_json_returns_raw():
    raw = "This is not JSON at all"
    result = _parse_json(raw)
    assert "raw_output" in result


def test_fix_encoding_mojibake():
    original = "Análisis"
    mojibake = original.encode("utf-8").decode("latin-1")
    fixed = _fix_encoding(mojibake)
    assert fixed == original
