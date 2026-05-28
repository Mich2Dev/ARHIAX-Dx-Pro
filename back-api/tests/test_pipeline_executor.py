"""Tests for pipeline executor — mock mode (no real Gemini calls)."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from api.pipeline.executor import PipelineExecutor, _parse_json, _fix_encoding
from api.config import Settings


@pytest.fixture
def mock_settings():
    s = MagicMock(spec=Settings)
    s.gemini_api_key = ""  # no key → mock mode
    return s


@pytest.fixture
def executor_mock(mock_settings):
    return PipelineExecutor(mock_settings)


@pytest.fixture
def executor_with_key():
    s = MagicMock(spec=Settings)
    s.gemini_api_key = "fake-key-for-testing"
    return PipelineExecutor(s)


# ── Mock mode tests ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mock_mode_returns_valid_output(executor_mock):
    result = await executor_mock.run_tool("g01_receptor", {"organization_name": "Test"}, {})
    assert result["model_used"] == "mock-no-key"
    assert result["output"]["mandate_confirmed"] is True


@pytest.mark.asyncio
async def test_mock_mode_all_tools(executor_mock):
    tools = [
        "g01_receptor", "g02_configurador", "g03_cienciometro", "g04_cartografo",
        "g05_brechas", "g06_bpmn_architect", "g07_cuellos", "g08_optimizador",
        "g09a_preguntas", "g09b_ramificacion", "g09c_validacion",
        "g10a_scoring", "g10b_psicometria", "g11a_bayesiano", "g11b_nlp",
        "irr_calculator", "scoring_engine", "g12_hallazgos", "g13_redactor",
        "g14_qa_control", "docx_generator",
    ]
    for tool in tools:
        result = await executor_mock.run_tool(tool, {}, {})
        assert "output" in result, f"Tool {tool} missing 'output'"
        assert isinstance(result["output"], dict), f"Tool {tool} output is not dict"


@pytest.mark.asyncio
async def test_mock_g09a_has_questions(executor_mock):
    result = await executor_mock.run_tool("g09a_preguntas", {}, {})
    assert "questions" in result["output"]
    assert len(result["output"]["questions"]) > 0


@pytest.mark.asyncio
async def test_mock_g14_qa_score_above_85(executor_mock):
    result = await executor_mock.run_tool("g14_qa_control", {}, {})
    assert result["output"]["qa_score"] >= 85
    assert result["output"]["approved_for_rendering"] is True


@pytest.mark.asyncio
async def test_mock_g10a_has_role_scores(executor_mock):
    result = await executor_mock.run_tool("g10a_scoring", {}, {})
    output = result["output"]
    assert "role_scores" in output
    assert "Estratégico" in output["role_scores"]
    assert "Táctico" in output["role_scores"]
    assert "Operativo" in output["role_scores"]


@pytest.mark.asyncio
async def test_mock_g10a_has_delta_sigma(executor_mock):
    result = await executor_mock.run_tool("g10a_scoring", {}, {})
    assert "delta_sigma" in result["output"]
    assert "max_gap" in result["output"]["delta_sigma"]


# ── Model fallback tests ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fallback_to_lite_on_503(executor_with_key):
    """When primary model gives 503 error result, should try flash-lite."""
    call_count = {"n": 0}

    async def mock_call(tool_name, prompt, model, max_tokens, temperature):
        call_count["n"] += 1
        if model == "gemini-2.5-flash":
            # Real behavior: _call_gemini_with_retry returns mock on failure
            return {
                "tool": tool_name,
                "model_used": "gemini-error: 503 UNAVAILABLE overloaded",
                "tokens_used": 0,
                "latency_ms": 0,
                "output": {},
            }
        # flash-lite succeeds
        return {
            "tool": tool_name,
            "model_used": model,
            "tokens_used": 100,
            "latency_ms": 500,
            "output": {"result": "ok"},
        }

    with patch.object(executor_with_key, "_call_gemini_with_retry", side_effect=mock_call):
        result = await executor_with_key._call_with_model_fallback(
            "g01_receptor", "test prompt", "gemini-2.5-flash", 4096, 0.2
        )

    assert result["model_used"] == "gemini-2.5-flash-lite"
    assert call_count["n"] == 2  # tried flash, then flash-lite


@pytest.mark.asyncio
async def test_all_models_fail_returns_mock(executor_with_key):
    """When all models fail, should return mock response."""
    async def always_fail(tool_name, prompt, model, max_tokens, temperature):
        return {
            "tool": tool_name,
            "model_used": f"gemini-error: 503 overloaded",
            "tokens_used": 0,
            "latency_ms": 0,
            "output": {},
        }

    with patch.object(executor_with_key, "_call_gemini_with_retry", side_effect=always_fail):
        result = await executor_with_key._call_with_model_fallback(
            "g01_receptor", "test prompt", "gemini-2.5-flash", 4096, 0.2
        )

    assert "gemini-error" in result["model_used"] or "mock" in result["model_used"]


# ── JSON parsing tests ────────────────────────────────────────────────────────

def test_parse_valid_json():
    result = _parse_json('{"key": "value", "number": 42}')
    assert result["key"] == "value"
    assert result["number"] == 42


def test_parse_json_in_markdown():
    raw = '```json\n{"status": "ok"}\n```'
    result = _parse_json(raw)
    assert result["status"] == "ok"


def test_parse_json_embedded_in_text():
    raw = 'Here is the result: {"status": "ok", "score": 91} end'
    result = _parse_json(raw)
    assert result["status"] == "ok"


def test_parse_invalid_json_returns_raw():
    raw = "This is not JSON at all"
    result = _parse_json(raw)
    assert "raw_output" in result


def test_fix_encoding_passthrough():
    text = "Hello world"
    assert _fix_encoding(text) == text


def test_fix_encoding_mojibake():
    # Simulate mojibake: utf-8 bytes interpreted as latin-1
    original = "Análisis"
    mojibake = original.encode("utf-8").decode("latin-1")
    fixed = _fix_encoding(mojibake)
    assert fixed == original
