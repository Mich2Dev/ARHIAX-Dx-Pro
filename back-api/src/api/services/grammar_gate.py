"""Canonical grammar gate — ported from Marcelo's dxpro_runtime/grammar (24 rules)."""

from __future__ import annotations

from typing import Any, Literal

from api.pipeline.canonical_grammar.lint import lint_text
from api.pipeline.canonical_grammar.models import GrammarAudience

Audience = Literal["internal", "client", "technical", "executive"]


def _map_audience(audience: str) -> GrammarAudience:
    if audience in ("internal", "client", "technical", "executive"):
        return audience  # type: ignore[return-value]
    return "executive"


def _report_status(decision: dict[str, Any]) -> str:
    if not decision.get("allowed"):
        return "blocked_by_grammar"
    if decision.get("confirm_required"):
        return "consultant_review_required"
    return "draft_ready"


def lint_markdown(text: str, source: str, audience: str = "executive") -> dict[str, Any]:
    """Return grammar gate report compatible with Pro router + Marcelo API shape."""
    report = lint_text(
        text or "",
        audience=_map_audience(audience),
        source=source,
    )
    payload = report.model_dump(mode="json")
    decision = payload.get("publish_decision") or {}
    warnings = int(payload.get("major", 0)) + int(payload.get("minor", 0)) + int(payload.get("advisory", 0))

    return {
        "source": payload.get("source", source),
        "audience": payload.get("audience", audience),
        "source_hash": payload.get("text_hash_sha256"),
        "text_hash_sha256": payload.get("text_hash_sha256"),
        "timestamp": payload.get("timestamp"),
        "score": payload.get("score", 0),
        "critical": payload.get("critical", 0),
        "major": payload.get("major", 0),
        "minor": payload.get("minor", 0),
        "advisory": payload.get("advisory", 0),
        "total": payload.get("total", 0),
        "warnings": warnings,
        "findings": payload.get("findings", []),
        "publish_decision": decision,
        "report_status": _report_status(decision),
        "canonical_engine": "marcelo_v0.3",
        "rules_count": 24,
    }
