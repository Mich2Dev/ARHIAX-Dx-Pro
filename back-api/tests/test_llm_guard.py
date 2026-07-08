"""Tests for llm_guard regulatory helpers."""
from __future__ import annotations

import pytest

from api.pipeline.llm_guard import (
    PipelineStageFailureError,
    assert_pipeline_stages_ok,
    stages_failed,
)


def test_stages_failed_detects_failures():
    stages = [
        {"tool_name": "g01_receptor", "status": "completed"},
        {"tool_name": "g09a_preguntas", "status": "failed", "output": {"error": "timeout"}},
    ]
    failed = stages_failed(stages)
    assert len(failed) == 1
    assert failed[0]["tool_name"] == "g09a_preguntas"


def test_assert_pipeline_stages_ok_raises_on_failed():
    stages = [{"tool_name": "g01_receptor", "status": "failed", "output": {"error": "sin llave"}}]
    with pytest.raises(PipelineStageFailureError) as exc:
        assert_pipeline_stages_ok(stages)
    assert exc.value.tool_name == "g01_receptor"


def test_assert_pipeline_stages_ok_requires_completed_tools():
    stages = [{"tool_name": "g01_receptor", "status": "completed"}]
    with pytest.raises(PipelineStageFailureError):
        assert_pipeline_stages_ok(stages, required_tools=["g01_receptor", "g09a_preguntas"])
