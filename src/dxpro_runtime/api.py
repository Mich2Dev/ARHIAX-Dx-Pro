"""FastAPI surface for the standalone DX Pro runtime."""

from __future__ import annotations

from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, Security

from .api_models import AgentExecuteRequest, CertificateVerifyRequest, DiagnosticEvaluateRequest, PmelCaptureRequest, PmelPolicyRequest, PmelStepRequest
from .auth import ApiKeyAuth, api_key_header
from .capture_agent import PmelCaptureAgent
from .catalog import DxProCatalog
from .config import RuntimeConfig, load_config
from .diagnostics import DiagnosticService
from .evidence import EvidenceLedger
from .llm_client import LlmClient
from .policy import PolicyEngine
from .pro_agents import CryptoParticipant, DmnEngine, PmelBpmnLintAgent, PmelToBeGenerator, PmelVisualInterpreter, RgcAgent
from .rate_limit import NullRateLimiter, RateLimiter
from .runtime import DxProRuntime


def build_runtime(config: RuntimeConfig | None = None) -> DxProRuntime:
    config = config or load_config()
    return DxProRuntime(
        policy_engine=PolicyEngine(config.policy_bundle_path, config.opa_url),
        ledger=EvidenceLedger(config.ledger_path, config.evidence_secret),
    )


def _build_security_dependency(config: RuntimeConfig):
    """Compose API-key auth + per-key rate limiting into one FastAPI dep."""
    auth = ApiKeyAuth(valid_keys=config.api_keys, required=config.is_production)
    limiter = (
        RateLimiter(
            requests_per_minute=config.rate_limit_per_minute,
            burst=config.rate_limit_burst,
        )
        if config.rate_limit_per_minute > 0
        else NullRateLimiter()
    )

    def secure(api_key: str | None = Security(api_key_header)) -> str | None:
        fingerprint = auth(api_key)
        limiter.check(fingerprint or "anonymous")
        return fingerprint

    return secure


def create_app(config: RuntimeConfig | None = None) -> FastAPI:
    config = config or load_config()
    catalog = DxProCatalog()
    runtime = build_runtime(config)
    llm_client = LlmClient(config.anthropic_api_key) if config.anthropic_api_key else None
    capture_agent = PmelCaptureAgent(runtime)
    verb_lexicon_path = config.policy_bundle_path / "data" / "lexicon_verbs_es.json"
    pro_agents = {
        "to_be_generator": PmelToBeGenerator(runtime, llm_client),
        "bpmn_lint_agent": PmelBpmnLintAgent(runtime, llm_client, verb_lexicon_path),
        "visual_interpreter": PmelVisualInterpreter(runtime, llm_client),
        "dmn_engine": DmnEngine(runtime),
        "crypto_participant": CryptoParticipant(runtime),
        "rgc_agent": RgcAgent(runtime, llm_client),
    }
    diagnostics = DiagnosticService(config, catalog, runtime)

    secure = _build_security_dependency(config)
    protected = [Depends(secure)]

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

    # ----- Public endpoints (no auth, for load balancers and discovery) -----
    @app.get("/")
    def root() -> dict[str, Any]:
        return {
            "service": "arhiax-dxpro-runtime",
            "mode": "standalone",
            "auth_required": config.is_production or bool(config.api_keys),
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
                "POST /v1/agents/research/build-hypothesis-pack",
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
            "env": config.env,
            "ledger_path": str(config.ledger_path),
            "policy_bundle_path": str(config.policy_bundle_path),
            "policy_engine_mode": runtime.policy_engine.mode,
            "opa_mode": runtime.policy_engine.mode in {"opa-http", "opa-cli"},
            "auth_required": config.is_production or bool(config.api_keys),
            "rate_limit_per_minute": config.rate_limit_per_minute,
        }

    # ----- Protected endpoints (require API key + rate-limited) -----
    @app.get("/v1/compliance/posture", dependencies=protected)
    def compliance_posture() -> dict[str, Any]:
        return diagnostics.compliance_posture()

    @app.get("/v1/compliance/install-readiness", dependencies=protected)
    def install_readiness() -> dict[str, Any]:
        return diagnostics.install_readiness()

    @app.get("/v1/compliance/install-blueprint", dependencies=protected)
    def install_blueprint() -> dict[str, Any]:
        return diagnostics.install_blueprint()

    @app.get("/v1/evidence", dependencies=protected)
    def evidence(limit: int = Query(50, ge=1, le=500), trace_id: str | None = None) -> dict[str, Any]:
        if trace_id:
            return {"entries": runtime.ledger.find_by_trace(trace_id)}
        return {"entries": runtime.ledger.list(limit=limit)}

    @app.get("/v1/pmel/runs/{trace_id}", dependencies=protected)
    def pmel_run(trace_id: str) -> dict[str, Any]:
        entries = runtime.ledger.find_by_trace(trace_id)
        if not entries:
            raise HTTPException(status_code=404, detail={"error": "trace_not_found", "trace_id": trace_id})
        return {"trace_id": trace_id, "entries": entries}

    @app.get("/v1/evidence/verify", dependencies=protected)
    def verify_evidence() -> dict[str, Any]:
        return runtime.ledger.verify()

    @app.post("/v1/certificates/verify", dependencies=protected)
    def verify_certificate(request: CertificateVerifyRequest) -> dict[str, Any]:
        return diagnostics.verify_certificate(request.certificate)

    @app.get("/v1/audit-pack/{trace_id}", dependencies=protected)
    def audit_pack(trace_id: str) -> dict[str, Any]:
        pack = diagnostics.audit_pack(trace_id)
        if pack is None:
            raise HTTPException(status_code=404, detail={"error": "trace_not_found", "trace_id": trace_id})
        return pack

    @app.post("/v1/diagnostics/evaluate", dependencies=protected)
    def evaluate_diagnostic(request: DiagnosticEvaluateRequest) -> dict[str, Any]:
        return diagnostics.evaluate(request.to_payload())

    @app.post("/v1/pmel/evaluate", dependencies=protected)
    @app.post("/v1/dxpro/pmel/evaluate", dependencies=protected)
    def evaluate_pmel(request: PmelPolicyRequest) -> dict[str, Any]:
        return runtime.evaluate(request.to_payload()).to_dict()

    @app.post("/v1/pmel/run-step", dependencies=protected)
    @app.post("/v1/dxpro/pmel/run-step", dependencies=protected)
    def run_pmel_step(request: PmelStepRequest) -> dict[str, Any]:
        return runtime.run_step(request.to_payload()).to_dict()

    @app.post("/v1/pmel/capture", dependencies=protected)
    @app.post("/v1/dxpro/pmel/capture", dependencies=protected)
    def capture_pmel(request: PmelCaptureRequest) -> dict[str, Any]:
        return capture_agent.capture(request.to_payload())

    @app.post("/v1/agents/to-be/generate", dependencies=protected)
    @app.post("/v1/dxpro/agents/to-be/generate", dependencies=protected)
    def generate_to_be(request: AgentExecuteRequest) -> dict[str, Any]:
        return pro_agents["to_be_generator"].execute(request.to_payload())

    @app.post("/v1/agents/bpmn-lint", dependencies=protected)
    @app.post("/v1/dxpro/agents/bpmn-lint", dependencies=protected)
    def lint_bpmn(request: AgentExecuteRequest) -> dict[str, Any]:
        return pro_agents["bpmn_lint_agent"].execute(request.to_payload())

    @app.post("/v1/agents/visual-interpret", dependencies=protected)
    @app.post("/v1/dxpro/agents/visual-interpret", dependencies=protected)
    def interpret_visual(request: AgentExecuteRequest) -> dict[str, Any]:
        return pro_agents["visual_interpreter"].execute(request.to_payload())

    @app.post("/v1/agents/dmn/evaluate", dependencies=protected)
    @app.post("/v1/dxpro/agents/dmn/evaluate", dependencies=protected)
    def evaluate_dmn(request: AgentExecuteRequest) -> dict[str, Any]:
        return pro_agents["dmn_engine"].execute(request.to_payload())

    @app.post("/v1/agents/crypto/decommission", dependencies=protected)
    @app.post("/v1/dxpro/agents/crypto/decommission", dependencies=protected)
    def decommission_crypto(request: AgentExecuteRequest) -> dict[str, Any]:
        return pro_agents["crypto_participant"].execute(request.to_payload())

    @app.post("/v1/agents/research/build-hypothesis-pack", dependencies=protected)
    @app.post("/v1/dxpro/agents/research/build-hypothesis-pack", dependencies=protected)
    def build_hypothesis_pack(request: AgentExecuteRequest) -> dict[str, Any]:
        return pro_agents["rgc_agent"].execute(request.to_payload())

    return app


app = create_app()
