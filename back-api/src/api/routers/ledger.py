"""Evidence ledger read endpoint."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends

from api.auth import get_current_user
from api.config import settings
from api.models import User

router = APIRouter(prefix="/v2/ledger", tags=["ledger"])


@router.get("")
async def get_ledger(
    skip: int = 0,
    limit: int = 50,
    _user: User = Depends(get_current_user),
) -> dict:
    path = Path(settings.ledger_path)
    if not path.exists():
        return {"total": 0, "items": []}

    lines = [l.strip() for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    total = len(lines)
    page = lines[-(skip + limit): len(lines) - skip] if skip < total else []
    page.reverse()

    items = []
    for line in page:
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError:
            pass

    return {"total": total, "items": items}
