"""Application entrypoint for ARHIAX Dx."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from arhiax_dx.config import Settings
from arhiax_dx.installation import build_installation_report
from arhiax_dx.installation_assets import build_install_blueprint
from arhiax_dx.models import DiagnosticRequest, DiagnosticResponse
from arhiax_dx.services.diagnostics import DiagnosticService
from arhiax_dx.services.evidence import EvidenceLedger
from arhiax_dx.services.governance import GovernanceEngine
from arhiax_dx.services.provenance import ProvenanceSigner
from arhiax_dx.services.tool_registry import ToolRegistry


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    settings.ensure_runtime_dirs()

    registry = ToolRegistry(settings)
    governance = GovernanceEngine(settings, registry)
    ledger = EvidenceLedger(settings.ledger_path)
    signer = ProvenanceSigner(settings)
    service = DiagnosticService(settings, registry, governance, ledger, signer)

    app = FastAPI(
        title=settings.project_name,
        version=settings.agent_version,
        summary="Governed organizational diagnostics agent with multi-rater and Bayesian workflow controls.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:8000"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok", "service": "arhiax-dx-agent"}

    @app.get("/readyz")
    def readyz() -> dict[str, str]:
        return {
            "status": "ready",
            "mode": settings.mode,
            "ledger_path": str(settings.ledger_path),
            "public_key_id": settings.public_key_id,
            "agent_version": settings.agent_version,
        }

    @app.get("/v1/compliance/posture")
    def compliance_posture() -> dict[str, object]:
        return {
            "processing_model": "governed pipeline orchestration with append-only evidence",
            "agent_identity": registry.agent_identity(),
            "tool_manifest": registry.tool_manifest(),
            "data_scopes": registry.data_scopes(),
            "operations": registry.operations(),
            "autonomy_profile": registry.autonomy_profile(),
            "policy_matrix": registry.policy_matrix(),
            "model_strategy_summary": registry.model_strategy(),
            "bbr_baseline": registry.bbr_baseline(),
            "governance_metadata": settings.governance_metadata(),
            "public_key_preview": signer.key_material_preview(),
        }

    @app.get("/v1/compliance/install-readiness")
    def install_readiness() -> dict[str, object]:
        return build_installation_report(settings=settings, registry=registry, signer=signer)

    @app.get("/v1/compliance/install-blueprint")
    def install_blueprint() -> dict[str, object]:
        return build_install_blueprint(settings)

    @app.post("/v1/diagnostics/evaluate", response_model=DiagnosticResponse)
    def evaluate(request: DiagnosticRequest) -> DiagnosticResponse:
        return service.evaluate(request)

    return app


app = create_app()
