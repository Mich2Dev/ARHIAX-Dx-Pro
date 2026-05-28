"""Append-only evidence ledger that stores hashes and metadata only."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def canonical_json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


class EvidenceLedger:
    def __init__(self, ledger_path: Path):
        self.ledger_path = ledger_path
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.ledger_path.exists():
            self.ledger_path.touch()

    def append(self, entry: dict[str, Any]) -> dict[str, Any]:
        previous_hash = self._last_hash()
        envelope = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "previous_hash": previous_hash,
            **entry,
        }
        envelope_hash = hashlib.sha256(canonical_json(envelope).encode("utf-8")).hexdigest()
        envelope["entry_hash"] = envelope_hash
        with self.ledger_path.open("a", encoding="utf-8") as handle:
            handle.write(canonical_json(envelope) + "\n")
        return envelope

    def _last_hash(self) -> str:
        last_line = ""
        with self.ledger_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    last_line = line.strip()
        if not last_line:
            return "GENESIS"
        return json.loads(last_line)["entry_hash"]
