"""ARHIAX Dx Pipeline API — main application."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.pipeline.llm_guard import require_gemini_key
from api.routers import auth, diagnostics, documents, ledger, reviews, survey, ws, users, dxpro, pro

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("api")

app = FastAPI(
    title="ARHIAX Dx Pipeline API",
    version="1.0.0",
    summary="Pipeline execution, persistence, and review layer for ARHIAX Dx.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:3003",
        "http://localhost:3004",
        "http://localhost:3005",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(diagnostics.router)
app.include_router(reviews.router)
app.include_router(ledger.router)
app.include_router(survey.router)
app.include_router(documents.router)
app.include_router(ws.router)
app.include_router(users.router)
app.include_router(dxpro.router)
app.include_router(pro.router)


@app.on_event("startup")
def _validate_regulatory_llm() -> None:
    try:
        require_gemini_key(settings.gemini_api_key)
        logger.info("Regulatory LLM guard: GEMINI_API_KEY presente — pipeline fail-closed activo.")
    except Exception as exc:
        logger.critical(
            "GEMINI_API_KEY ausente: el pipeline regulatorio NO ejecutará diagnósticos (%s)",
            exc,
        )


@app.get("/healthz")
def healthz() -> dict:
    llm_ready = bool((settings.gemini_api_key or "").strip())
    return {
        "status": "ok" if llm_ready else "degraded",
        "service": "arhiax-dx-pipeline-api",
        "llm_configured": llm_ready,
        "policy": "fail_closed_no_mock",
    }
