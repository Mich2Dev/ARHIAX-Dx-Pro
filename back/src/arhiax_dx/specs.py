"""Helpers for loading development specs from the packaged repo."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


def default_specs_path() -> Path:
    return Path(__file__).resolve().parents[2] / "specs"


@lru_cache(maxsize=32)
def load_json_spec(spec_path: str) -> dict[str, Any]:
    return json.loads(Path(spec_path).read_text(encoding="utf-8"))
