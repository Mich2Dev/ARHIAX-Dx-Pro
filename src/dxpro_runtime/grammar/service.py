from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .lint import lint_text, can_publish
from .models import (
    GrammarAudience,
    GrammarException,
    GrammarReport,
    GrammarReportSummary,
    PublishDecision,
)


class GrammarService:
    def __init__(self, case_store_root: Path) -> None:
        self.case_store_root = case_store_root
        self.case_store_root.mkdir(parents=True, exist_ok=True)

    def run_lint(
        self,
        text: str,
        audience: GrammarAudience = "client",
        source: str = "manual",
        case_id: str | None = None,
        exceptions: list[GrammarException] | None = None,
    ) -> GrammarReport:
        report = lint_text(text, audience, source, exceptions)

        if case_id:
            self._persist(case_id, report, exceptions or [])

        return report

    def get_case_grammar(self, case_id: str) -> GrammarReportSummary:
        data = self._load_case(case_id)
        if data is None:
            return GrammarReportSummary(case_id=case_id, grammar_report=None, exceptions=[])
        return GrammarReportSummary(
            case_id=case_id,
            grammar_report=GrammarReport(**data["report"]) if data.get("report") else None,
            exceptions=[GrammarException(**e) for e in data.get("exceptions", [])],
        )

    def save_grammar_report(self, case_id: str, report_data: dict[str, Any]) -> None:
        self._persist(case_id, GrammarReport(**report_data), [])

    def check_publish(self, case_id: str) -> PublishDecision:
        data = self._load_case(case_id)
        if data is None or data.get("report") is None:
            return PublishDecision(allowed=True, confirm_required=True, reason="Sin revisión gramatical previa.")
        report = GrammarReport(**data["report"])
        exceptions = [GrammarException(**e) for e in data.get("exceptions", [])]
        return can_publish(report, exceptions)

    def _persist(self, case_id: str, report: GrammarReport, exceptions: list[GrammarException]) -> None:
        path = self._case_path(case_id)
        data: dict[str, Any] = {}
        if path.exists():
            import json
            data = json.loads(path.read_text(encoding="utf-8"))

        data["grammar"] = {
            "report": report.model_dump(mode="json"),
            "exceptions": [e.model_dump(mode="json") for e in exceptions],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        path.write_text(
            __import__("json").dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _load_case(self, case_id: str) -> dict[str, Any] | None:
        path = self._case_path(case_id)
        if not path.exists():
            return None
        import json
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        return data.get("grammar")

    def _case_path(self, case_id: str) -> Path:
        return self.case_store_root / f"{case_id}.json"
