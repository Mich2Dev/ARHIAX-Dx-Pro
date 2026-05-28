"""Minimal PMEL Capture Agent stub."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from .runtime import DxProRuntime


class PmelCaptureAgent:
    """First governed agent stub for PMEL interview intake."""

    def __init__(self, runtime: DxProRuntime) -> None:
        self.runtime = runtime

    def capture(self, payload: dict[str, Any]) -> dict[str, Any]:
        interview_text = str(payload.get("interview_text", "")).strip()
        subject = payload.get("subject", "pmel-capture-agent")
        run_payload = {
            "subject": subject,
            "step": "capture_pre_ingest",
            "trace_id": payload.get("trace_id", ""),
            "input": {
                "autonomy": payload.get(
                    "autonomy",
                    {"component": "capture_agent", "requested_level": "A2"},
                ),
                "consent": payload.get(
                    "consent",
                    {"action": "ingest_to_llm", "consents": {}},
                ),
                "aibom": payload.get("aibom", {}),
                "execution": payload.get(
                    "execution",
                    {
                        "component": "capture_agent",
                        "current_cycle": 1,
                        "last_outcome": "in_progress",
                    },
                ),
            },
        }
        step = self.runtime.run_step(run_payload)
        result = step.to_dict()
        result["artifact"] = None

        if step.allowed:
            result["artifact"] = self._draft_artifact(interview_text)
        return result

    def _draft_artifact(self, interview_text: str) -> dict[str, Any]:
        sentences = [part.strip() for part in re.split(r"[.\n]+", interview_text) if part.strip()]
        activities = []
        for index, sentence in enumerate(sentences[:8], start=1):
            activities.append(
                {
                    "id": f"act-{index:03d}",
                    "label": sentence[:120],
                    "source": "interview_text",
                }
            )
        return {
            "artifact_type": "pmel_capture_draft",
            "source_hash_sha256": hashlib.sha256(interview_text.encode("utf-8")).hexdigest(),
            "activity_count": len(activities),
            "activities": activities,
        }
