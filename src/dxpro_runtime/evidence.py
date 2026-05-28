"""Append-only evidence ledger with HMAC chaining."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class EvidenceLedger:
    def __init__(self, path: Path, secret: str) -> None:
        self.path = path
        self.secret = secret.encode("utf-8")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: dict[str, Any]) -> dict[str, Any]:
        with self._exclusive_lock():
            head = self._head_unlocked()
            sequence = head["sequence"] + 1
            evidence_id = f"dxev-{sequence:010d}"
            timestamp = datetime.now(timezone.utc).isoformat()
            entry = {
                "id": evidence_id,
                "sequence_number": sequence,
                "timestamp": timestamp,
                "prev_hash": head["last_hash"],
                **record,
            }
            entry_json = json.dumps(entry, sort_keys=True, separators=(",", ":"))
            entry["entry_hmac"] = self._hmac(head["last_hash"], entry_json)

            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
            return entry

    def list(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._exclusive_lock():
            if not self.path.exists():
                return []
            entries: list[dict[str, Any]] = []
            with self.path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if line:
                        entries.append(json.loads(line))
        return entries[-limit:][::-1]

    def find_by_trace(self, trace_id: str) -> list[dict[str, Any]]:
        with self._exclusive_lock():
            if not self.path.exists():
                return []
            matches: list[dict[str, Any]] = []
            with self.path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    entry = json.loads(line)
                    if entry.get("trace_id") == trace_id:
                        matches.append(entry)
        matches.sort(key=lambda entry: entry["sequence_number"])
        return matches

    def head(self) -> dict[str, Any]:
        with self._exclusive_lock():
            return self._head_unlocked()

    def _head_unlocked(self) -> dict[str, Any]:
        last_hash = "0" * 64
        sequence = 0
        if not self.path.exists():
            return {"sequence": sequence, "last_hash": last_hash}
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                sequence = int(entry["sequence_number"])
                last_hash = entry["entry_hmac"]
        return {"sequence": sequence, "last_hash": last_hash}

    def verify(self) -> dict[str, Any]:
        with self._exclusive_lock():
            prev_hash = "0" * 64
            checked = 0
            if not self.path.exists():
                return {"valid": True, "entries_checked": 0}
            with self.path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    entry = json.loads(line)
                    stored_hmac = entry.pop("entry_hmac", "")
                    entry_json = json.dumps(entry, sort_keys=True, separators=(",", ":"))
                    expected = self._hmac(prev_hash, entry_json)
                    if not hmac.compare_digest(stored_hmac, expected):
                        return {
                            "valid": False,
                            "broken_at_sequence": entry.get("sequence_number"),
                            "entries_checked": checked,
                        }
                    prev_hash = stored_hmac
                    checked += 1
        return {"valid": True, "entries_checked": checked}

    def _hmac(self, prev_hash: str, entry_json: str) -> str:
        return hmac.new(self.secret, (prev_hash + entry_json).encode("utf-8"), hashlib.sha256).hexdigest()

    @contextmanager
    def _exclusive_lock(self):
        lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open("a+b") as lock_file:
            lock_file.seek(0, os.SEEK_END)
            if lock_file.tell() == 0:
                lock_file.write(b"0")
                lock_file.flush()
            lock_file.seek(0)
            if os.name == "nt":
                import msvcrt

                acquired = False
                for _ in range(100):
                    try:
                        msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                        acquired = True
                        break
                    except OSError:
                        time.sleep(0.05)
                if not acquired:
                    raise TimeoutError(f"Could not acquire ledger lock: {lock_path}")
                try:
                    yield
                finally:
                    lock_file.seek(0)
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
