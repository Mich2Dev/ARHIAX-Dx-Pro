"""Shared runtime models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


ATK_OUTCOMES = {"PERMIT", "DENY", "ESCALATE", "MODIFY", "AUDIT", "SUSPEND"}


@dataclass(frozen=True)
class PolicyDecision:
    package: str
    outcome: str
    reason: str
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def allowed(self) -> bool:
        return self.outcome in {"PERMIT", "AUDIT", "MODIFY"}


@dataclass(frozen=True)
class EvaluationRequest:
    package: str
    input: dict[str, Any]
    subject: str = "pmel-runtime"
    trace_id: str = ""


@dataclass(frozen=True)
class EvaluationResponse:
    decision: PolicyDecision
    evidence_id: str
    trace_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "evidence_id": self.evidence_id,
            "decision": {
                "package": self.decision.package,
                "outcome": self.decision.outcome,
                "reason": self.decision.reason,
                "allowed": self.decision.allowed,
                "details": self.decision.details,
            },
        }


@dataclass(frozen=True)
class StepDecision:
    trace_id: str
    subject: str
    outcome: str
    reason: str
    allowed: bool
    decisions: list[dict[str, Any]]
    evidence_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "subject": self.subject,
            "outcome": self.outcome,
            "reason": self.reason,
            "allowed": self.allowed,
            "evidence_id": self.evidence_id,
            "decisions": self.decisions,
        }
