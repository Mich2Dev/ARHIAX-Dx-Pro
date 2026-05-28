"""Local persistence for DX Pro diagnostic cases."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class CaseStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, case_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        record = dict(payload)
        record["case_id"] = case_id
        record["updated_at"] = datetime.now(timezone.utc).isoformat()
        path = self._path(case_id)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(record, handle, ensure_ascii=False, indent=2)
        return record

    def load(self, case_id: str) -> dict[str, Any] | None:
        path = self._path(case_id)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def list(self, limit: int = 50) -> list[dict[str, Any]]:
        items = []
        for path in sorted(self.root.glob("*.json"), reverse=True):
            items.append(json.loads(path.read_text(encoding="utf-8")))
            if len(items) >= limit:
                break
        return items

    def append_history(self, case_id: str, event: dict[str, Any]) -> dict[str, Any] | None:
        record = self.load(case_id)
        if record is None:
            return None
        history = list(record.get("history") or [])
        history.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **event,
            }
        )
        record["history"] = history
        return self.save(case_id, record)

    def _path(self, case_id: str) -> Path:
        return self.root / f"{case_id}.json"
