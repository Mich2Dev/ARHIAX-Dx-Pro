"""WebSocket endpoint for pipeline progress streaming."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from api.db import get_async_session_local, get_db
from api.models import Diagnostic

router = APIRouter(tags=["websocket"])


@router.websocket("/v2/diagnostics/{diagnostic_id}/stream")
async def stream(websocket: WebSocket, diagnostic_id: str) -> None:
    await websocket.accept()
    try:
        while True:
            async with get_async_session_local()() as db:
                result = await db.execute(
                    select(Diagnostic)
                    .options(selectinload(Diagnostic.stages))
                    .where(Diagnostic.id == diagnostic_id)
                )
                d = result.scalar_one_or_none()

            if d is None:
                await websocket.send_text(json.dumps({"error": "not found"}))
                break

            payload = {
                "status": d.status,
                "decision": d.decision,
                "stages": [
                    {
                        "id": s.id,
                        "tool_name": s.tool_name,
                        "phase": s.phase,
                        "status": s.status,
                        "model_used": s.model_used,
                        "tokens_used": s.tokens_used,
                        "latency_ms": s.latency_ms,
                    }
                    for s in (d.stages or [])
                ],
            }
            await websocket.send_text(json.dumps(payload))

            if d.status not in ("pending", "running"):
                break

            await asyncio.sleep(2)
    except WebSocketDisconnect:
        pass
