"""ARHIAX Dx Pipeline API — main application."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok", "service": "arhiax-dx-pipeline-api"}
