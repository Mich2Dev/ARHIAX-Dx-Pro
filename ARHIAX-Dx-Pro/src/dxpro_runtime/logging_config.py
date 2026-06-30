"""Structured JSON logging and in-memory metrics for DX Pro runtime."""

from __future__ import annotations

import json
import logging
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


# ---------------------------------------------------------------------------
# In-memory metrics counters (process-local, reset on restart)
# ---------------------------------------------------------------------------

class _Metrics:
    def __init__(self) -> None:
        self.requests_total: int = 0
        self.requests_by_status: dict[int, int] = defaultdict(int)
        self.llm_calls_total: int = 0
        self.llm_errors_total: int = 0
        self.pmel_decisions_by_outcome: dict[str, int] = defaultdict(int)

    def snapshot(self) -> dict[str, Any]:
        return {
            "requests_total": self.requests_total,
            "requests_by_status": dict(self.requests_by_status),
            "llm_calls_total": self.llm_calls_total,
            "llm_errors_total": self.llm_errors_total,
            "pmel_decisions_by_outcome": dict(self.pmel_decisions_by_outcome),
        }


METRICS = _Metrics()


# ---------------------------------------------------------------------------
# Structured logger
# ---------------------------------------------------------------------------

def _emit(record: dict[str, Any]) -> None:
    """Write a JSON log entry to stdout."""
    print(json.dumps(record, ensure_ascii=False, default=str), flush=True)


def log_event(
    event: str,
    *,
    level: str = "INFO",
    trace_id: str = "",
    **kwargs: Any,
) -> None:
    """Emit a structured log entry for a named event."""
    _emit({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "service": "arhiax-dxpro",
        "trace_id": trace_id,
        "event": event,
        **kwargs,
    })


def log_llm_call(
    *,
    trace_id: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> None:
    METRICS.llm_calls_total += 1
    log_event(
        "llm_call",
        trace_id=trace_id,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )


def log_llm_error(*, trace_id: str, model: str, error: str) -> None:
    METRICS.llm_errors_total += 1
    log_event(
        "llm_error",
        level="ERROR",
        trace_id=trace_id,
        model=model,
        error=error,
    )


def log_pmel_decision(*, trace_id: str, outcome: str, agent: str) -> None:
    METRICS.pmel_decisions_by_outcome[outcome] += 1
    log_event(
        "pmel_decision",
        trace_id=trace_id,
        outcome=outcome,
        agent=agent,
    )


def log_auth_rejected(*, fingerprint: str, reason: str) -> None:
    log_event(
        "auth_rejected",
        level="WARNING",
        trace_id="",
        fingerprint=fingerprint,
        reason=reason,
    )


# ---------------------------------------------------------------------------
# FastAPI middleware
# ---------------------------------------------------------------------------

class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """Emit one JSON log entry per HTTP request/response."""

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        trace_id = (
            request.headers.get("X-Trace-Id")
            or request.headers.get("X-Request-Id")
            or str(uuid.uuid4())
        )
        # Attach trace_id to request state so handlers can read it
        request.state.trace_id = trace_id

        start = time.monotonic()
        response: Response = await call_next(request)
        duration_ms = round((time.monotonic() - start) * 1000, 1)

        status = response.status_code
        METRICS.requests_total += 1
        METRICS.requests_by_status[status] += 1

        _emit({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": "INFO",
            "service": "arhiax-dxpro",
            "trace_id": trace_id,
            "event": "http_request",
            "method": request.method,
            "path": request.url.path,
            "status_code": status,
            "duration_ms": duration_ms,
        })

        return response
