from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

GrammarAudience = Literal["internal", "client", "technical", "executive"]
GrammarSeverity = Literal["critical", "major", "minor", "advisory"]


class GrammarRule(BaseModel):
    id: str
    block: str
    title: str
    severity: GrammarSeverity
    pattern: str
    suggestion: str | None = None
    rationale: str
    audience: list[GrammarAudience] | None = None


class GrammarFinding(BaseModel):
    finding_id: str
    rule_id: str
    block: str
    severity: GrammarSeverity
    message: str
    detected_text: str
    suggestion: str | None = None
    rationale: str
    index: int | None = None
    excepted: bool = False


class GrammarException(BaseModel):
    finding_id: str
    rule_id: str
    detected_text: str
    reason: str
    reviewer: str
    created_at: str


class PublishDecision(BaseModel):
    allowed: bool
    confirm_required: bool = False
    reason: str | None = None


class GrammarReport(BaseModel):
    score: int = Field(ge=0, le=100)
    critical: int = Field(ge=0)
    major: int = Field(ge=0)
    minor: int = Field(ge=0)
    advisory: int = Field(ge=0)
    total: int = Field(ge=0)
    findings: list[GrammarFinding] = Field(default_factory=list)
    text_hash_sha256: str
    timestamp: str
    audience: GrammarAudience
    source: str
    publish_decision: PublishDecision


class GrammarReportSummary(BaseModel):
    case_id: str
    grammar_report: GrammarReport | None = None
    exceptions: list[GrammarException] = Field(default_factory=list)
