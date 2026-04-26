"""FastAPI surface for the standalone DX Pro runtime."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Query

from .api_models import AgentExecuteRequest, CertificateVerifyRequest, DiagnosticEvaluateRequest, PmelCaptureRequest, PmelPolicyRequest, PmelStepRequest
from .capture_agent import PmelCaptureAgent
from .catalog import DxProCatalog
from .config import RuntimeConfig, load_config
from .diagnostics import DiagnosticService
from .evidence import EvidenceLedger
from .policy import PolicyEngine
from .pro_agents import CryptoParticipant, DmnEngine, PmelBpmnLintAgent, PmelToBeGenerator, PmelVisualInterpreter
from .runtime import DxProRuntime


def build_runtime(config: RuntimeConfig | None = None) -> DxProRuntime:
    config = config or load_config()
    return DxProRuntime(
        policy_engine=PolicyEngine(config.policy_bundle_path, config.opa_url),
        ledger=EvidenceLedger(config.ledger_path, config.evidence_secret),
    )


def create_app(config: RuntimeConfig | None = None) -> FastAPI:
    config = config or load_config()
    catalog = DxProCatalog()
    runtime = build_runtime(config)
    capture_agent = PmelCaptureAgent(runtime)
    pro_agents = {
        "to_be_generator": PmelToBeGenerator(runtime),
        "bpmn_lint_agent": PmelBpmnLintAgent(runtime),
        "visual_interpreter": PmelVisualInterpreter(runtime),
        "dmn_engine": DmnEngine(runtime),
        "crypto_participant": CryptoParticipant(runtime),
    }
    diagnostics = DiagnosticService(config, catalog, runtime)

    app = FastAPI(
        title="ARHIAX DX Pro Runtime",
        version="0.1.0-alpha",
        summary="Standalone governed diagnostic runtime with PMEL/ATK controls.",
    )
    app.state.config = config
    app.state.catalog = catalog
    app.state.runtime = runtime
    app.state.capture_agent = capture_agent
    app.state.pro_agents = pro_agents
    app.state.diagnostics = diagnostics

    @app.get("/")
    def root() -> dict[str, Any]:
        return {
            "service": "arhiax-dxpro-runtime",
            "mode": "standalone",
            "endpoints": [
                "GET /healthz",
                "GET /readyz",
                "GET /v1/compliance/posture",
                "GET /v1/compliance/install-readiness",
                "GET /v1/compliance/install-blueprint",
                "POST /v1/diagnostics/evaluate",
                "POST /v1/pmel/evaluate",
                "POST /v1/pmel/run-step",
                "POST /v1/pmel/capture",
                "POST /v1/dxpro/pmel/evaluate",
                "POST /v1/dxpro/pmel/run-step",
                "POST /v1/dxpro/pmel/capture",
                "GET /v1/evidence",
                "GET /v1/evidence?trace_id={trace_id}",
                "GET /v1/pmel/runs/{trace_id}",
                "GET /v1/evidence/verify",
                "POST /v1/certificates/verify",
                "GET /v1/audit-pack/{trace_id}",
                "POST /v1/agents/to-be/generate",
                "POST /v1/agents/bpmn-lint",
                "POST /v1/agents/visual-interpret",
                "POST /v1/agents/dmn/evaluate",
                "POST /v1/agents/crypto/decommission",
            ],
        }

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok", "service": "arhiax-dxpro-runtime"}

    @app.get("/readyz")
    def readyz() -> dict[str, Any]:
        return {
            "status": "ready",
            "mode": "standalone",
            "ledger_path": str(config.ledger_path),
            "policy_bundle_path": str(config.policy_bundle_path),
            "policy_engine_mode": runtime.policy_engine.mode,
            "opa_mode": runtime.policy_engine.mode in {"opa-http", "opa-cli"},
        }

    @app.get("/v1/compliance/posture")
    def compliance_posture() -> dict[str, Any]:
        return diagnostics.compliance_posture()

    @app.get("/v1/compliance/install-readiness")
    def install_readiness() -> dict[str, Any]:
        return diagnostics.install_readiness()

    @app.get("/v1/compliance/install-blueprint")
    def install_blueprint() -> dict[str, Any]:
        return diagnostics.install_blueprint()

    @app.get("/v1/evidence")
    def evidence(limit: int = Query(50, ge=1, le=500), trace_id: str | None = None) -> dict[str, Any]:
        if trace_id:
            return {"entries": runtime.ledger.find_by_trace(trace_id)}
        return {"entries": runtime.ledger.list(limit=limit)}

    @app.get("/v1/pmel/runs/{trace_id}")
    def pmel_run(trace_id: str) -> dict[str, Any]:
        entries = runtime.ledger.find_by_trace(trace_id)
        if not entries:
            raise HTTPException(status_code=404, detail={"error": "trace_not_found", "trace_id": trace_id})
        return {"trace_id": trace_id, "entries": entries}

    @app.get("/v1/evidence/verify")
    def verify_evidence() -> dict[str, Any]:
        return runtime.ledger.verify()

    @app.post("/v1/certificates/verify")
    def verify_certificate(request: CertificateVerifyRequest) -> dict[str, Any]:
        return diagnostics.verify_certificate(request.certificate)

    @app.get("/v1/audit-pack/{trace_id}")
    def audit_pack(trace_id: str) -> dict[str, Any]:
        pack = diagnostics.audit_pack(trace_id)
        if pack is None:
            raise HTTPException(status_code=404, detail={"error": "trace_not_found", "trace_id": trace_id})
        return pack

    @app.post("/v1/diagnostics/evaluate")
    def evaluate_diagnostic(request: DiagnosticEvaluateRequest) -> dict[str, Any]:
        return diagnostics.evaluate(request.to_payload())

    @app.post("/v1/pmel/evaluate")
    @app.post("/v1/dxpro/pmel/evaluate")
    def evaluate_pmel(request: PmelPolicyRequest) -> dict[str, Any]:
        return runtime.evaluate(request.to_payload()).to_dict()

    @app.post("/v1/pmel/run-step")
    @app.post("/v1/dxpro/pmel/run-step")
    def run_pmel_step(request: PmelStepRequest) -> dict[str, Any]:
        return runtime.run_step(request.to_payload()).to_dict()

    @app.post("/v1/pmel/capture")
    @app.post("/v1/dxpro/pmel/capture")
    def capture_pmel(request: PmelCaptureRequest) -> dict[str, Any]:
        return capture_agent.capture(request.to_payload())

    @app.post("/v1/agents/to-be/generate")
    @app.post("/v1/dxpro/agents/to-be/generate")
    def generate_to_be(request: AgentExecuteRequest) -> dict[str, Any]:
        return pro_agents["to_be_generator"].execute(request.to_payload())

    @app.post("/v1/agents/bpmn-lint")
    @app.post("/v1/dxpro/agents/bpmn-lint")
    def lint_bpmn(request: AgentExecuteRequest) -> dict[str, Any]:
        return pro_agents["bpmn_lint_agent"].execute(request.to_payload())

    @app.post("/v1/agents/visual-interpret")
    @app.post("/v1/dxpro/agents/visual-interpret")
    def interpret_visual(request: AgentExecuteRequest) -> dict[str, Any]:
        return pro_agents["visual_interpreter"].execute(request.to_payload())

    @app.post("/v1/agents/dmn/evaluate")
    @app.post("/v1/dxpro/agents/dmn/evaluate")
    def evaluate_dmn(request: AgentExecuteRequest) -> dict[str, Any]:
        return pro_agents["dmn_engine"].execute(request.to_payload())

    @app.post("/v1/agents/crypto/decommission")
    @app.post("/v1/dxpro/agents/crypto/decommission")
    def decommission_crypto(request: AgentExecuteRequest) -> dict[str, Any]:
        return pro_agents["crypto_participant"].execute(request.to_payload())

    return app


app = create_app()
