"""FastAPI surface for the standalone DX Pro runtime."""

from __future__ import annotations

from typing import Any, cast

from fastapi import Depends, FastAPI, HTTPException, Query, Security

from .api_models import AgentExecuteRequest, CertificateVerifyRequest, DiagnosticEvaluateRequest, GrammarLintRequest, GrammarPublishRequest, PmelCaptureRequest, PmelPolicyRequest, PmelStepRequest
from .auth import ApiKeyAuth, api_key_header
from .case_store import CaseStore
from .capture_agent import PmelCaptureAgent
from .catalog import DxProCatalog
from .config import RuntimeConfig, load_config
from .diagnostics import DiagnosticService
from .evidence import EvidenceLedger
from .llm_client import LlmClient
from .policy import PolicyEngine
from .pro_agents import (
    AdaptiveQuestionBankAgent,
    BayesianSynthesisAgent,
    CaseApprovalAgent,
    CryptoParticipant,
    DiagnosticIntelligenceAgent,
    ReportExportAgent,
    RunDiagnosticCaseAgent,
    DiagnosticFusionCycleAgent,
    DmnEngine,
    ExecutiveReportAgent,
    ExecutiveQaAgent,
    IrrReliabilityAgent,
    MultiRoleScoringAgent,
    PmelBpmnLintAgent,
    PmelToBeGenerator,
    PmelVisualInterpreter,
    PsychometricsAgent,
    ReportRendererAgent,
    RgcAgent,
    RgcDeepResearchContrasterAgent,
)
from .grammar import GrammarService
from .grammar.models import GrammarAudience, GrammarException
from .rate_limit import NullRateLimiter, RateLimiter
from .report_exports import ReportExportService
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
    case_store = CaseStore(config.case_store_root)
    grammar_service = GrammarService(config.case_store_root)
    export_service = ReportExportService(config.export_root, grammar_service=grammar_service)
    verb_lexicon_path = config.policy_bundle_path / "data" / "lexicon_verbs_es.json"
    fusion_agent = DiagnosticFusionCycleAgent(runtime, llm_client)
    report_agent = ExecutiveReportAgent(runtime, llm_client)
    renderer_agent = ReportRendererAgent(runtime, llm_client)
    export_agent = ReportExportAgent(runtime, export_service, llm_client)
    pro_agents = {
        "to_be_generator": PmelToBeGenerator(runtime, llm_client),
        "bpmn_lint_agent": PmelBpmnLintAgent(runtime, llm_client, verb_lexicon_path),
        "visual_interpreter": PmelVisualInterpreter(runtime, llm_client),
        "dmn_engine": DmnEngine(runtime),
        "crypto_participant": CryptoParticipant(runtime),
        "rgc_agent": RgcAgent(runtime, llm_client),
        "rgc_deep_research_contraster": RgcDeepResearchContrasterAgent(runtime, llm_client),
        "adaptive_question_bank": AdaptiveQuestionBankAgent(runtime, llm_client),
        "multi_role_scoring": MultiRoleScoringAgent(runtime, llm_client),
        "psychometrics": PsychometricsAgent(runtime, llm_client),
        "irr_reliability": IrrReliabilityAgent(runtime, llm_client),
        "bayesian_synthesis": BayesianSynthesisAgent(runtime, llm_client),
        "executive_qa": ExecutiveQaAgent(runtime, llm_client),
        "diagnostic_intelligence": DiagnosticIntelligenceAgent(runtime, llm_client),
        "diagnostic_fusion_cycle": fusion_agent,
        "executive_report": report_agent,
        "report_renderer": renderer_agent,
        "report_exporter": export_agent,
        "case_approval": CaseApprovalAgent(runtime, case_store, llm_client),
        "diagnostic_case_runner": RunDiagnosticCaseAgent(
            runtime,
            case_store,
            fusion_agent,
            report_agent,
            renderer_agent,
            export_agent,
            llm_client,
        ),
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
    app.state.case_store = case_store
    app.state.export_service = export_service
    app.state.grammar_service = grammar_service

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
                "POST /v1/agents/research/deep-contrast",
                "POST /v1/agents/questions/adaptive-bank",
                "POST /v1/agents/scoring/multi-role",
                "POST /v1/agents/psychometrics/evaluate",
                "POST /v1/agents/reliability/irr",
                "POST /v1/agents/synthesis/bayesian",
                "POST /v1/agents/qa/executive",
                "POST /v1/agents/diagnostic/intelligence-pack",
                "POST /v1/agents/diagnostic/run-fusion-cycle",
                "POST /v1/agents/report/executive",
                "POST /v1/agents/report/render",
                "POST /v1/agents/report/export",
                "POST /v1/agents/cases/run",
                "POST /v1/agents/cases/approval",
                "POST /v1/agents/grammar/lint",
                "POST /v1/dxpro/agents/grammar/lint",
                "GET /v1/cases/{case_id}/grammar",
                "POST /v1/cases/{case_id}/publish",
                "GET /v1/cases",
                "GET /v1/cases/{case_id}",
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

    @app.get("/v1/cases", dependencies=protected)
    def list_cases(limit: int = Query(50, ge=1, le=200)) -> dict[str, Any]:
        return {"cases": case_store.list(limit=limit)}

    @app.get("/v1/cases/{case_id}", dependencies=protected)
    def get_case(case_id: str) -> dict[str, Any]:
        case = case_store.load(case_id)
        if case is None:
            raise HTTPException(status_code=404, detail={"error": "case_not_found", "case_id": case_id})
        return case

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

    @app.post("/v1/agents/research/deep-contrast", dependencies=protected)
    @app.post("/v1/dxpro/agents/research/deep-contrast", dependencies=protected)
    def deep_research_contrast(request: AgentExecuteRequest) -> dict[str, Any]:
        return pro_agents["rgc_deep_research_contraster"].execute(request.to_payload())

    @app.post("/v1/agents/questions/adaptive-bank", dependencies=protected)
    @app.post("/v1/dxpro/agents/questions/adaptive-bank", dependencies=protected)
    def build_adaptive_question_bank(request: AgentExecuteRequest) -> dict[str, Any]:
        return pro_agents["adaptive_question_bank"].execute(request.to_payload())

    @app.post("/v1/agents/scoring/multi-role", dependencies=protected)
    @app.post("/v1/dxpro/agents/scoring/multi-role", dependencies=protected)
    def score_multi_role(request: AgentExecuteRequest) -> dict[str, Any]:
        return pro_agents["multi_role_scoring"].execute(request.to_payload())

    @app.post("/v1/agents/psychometrics/evaluate", dependencies=protected)
    @app.post("/v1/dxpro/agents/psychometrics/evaluate", dependencies=protected)
    def evaluate_psychometrics(request: AgentExecuteRequest) -> dict[str, Any]:
        return pro_agents["psychometrics"].execute(request.to_payload())

    @app.post("/v1/agents/reliability/irr", dependencies=protected)
    @app.post("/v1/dxpro/agents/reliability/irr", dependencies=protected)
    def evaluate_irr(request: AgentExecuteRequest) -> dict[str, Any]:
        return pro_agents["irr_reliability"].execute(request.to_payload())

    @app.post("/v1/agents/synthesis/bayesian", dependencies=protected)
    @app.post("/v1/dxpro/agents/synthesis/bayesian", dependencies=protected)
    def synthesize_bayesian(request: AgentExecuteRequest) -> dict[str, Any]:
        return pro_agents["bayesian_synthesis"].execute(request.to_payload())

    @app.post("/v1/agents/qa/executive", dependencies=protected)
    @app.post("/v1/dxpro/agents/qa/executive", dependencies=protected)
    def run_executive_qa(request: AgentExecuteRequest) -> dict[str, Any]:
        return pro_agents["executive_qa"].execute(request.to_payload())

    @app.post("/v1/agents/diagnostic/intelligence-pack", dependencies=protected)
    @app.post("/v1/dxpro/agents/diagnostic/intelligence-pack", dependencies=protected)
    def build_diagnostic_intelligence_pack(request: AgentExecuteRequest) -> dict[str, Any]:
        return pro_agents["diagnostic_intelligence"].execute(request.to_payload())

    @app.post("/v1/agents/diagnostic/run-fusion-cycle", dependencies=protected)
    @app.post("/v1/dxpro/agents/diagnostic/run-fusion-cycle", dependencies=protected)
    def run_diagnostic_fusion_cycle(request: AgentExecuteRequest) -> dict[str, Any]:
        return pro_agents["diagnostic_fusion_cycle"].execute(request.to_payload())

    @app.post("/v1/agents/report/executive", dependencies=protected)
    @app.post("/v1/dxpro/agents/report/executive", dependencies=protected)
    def generate_executive_report(request: AgentExecuteRequest) -> dict[str, Any]:
        return pro_agents["executive_report"].execute(request.to_payload())

    @app.post("/v1/agents/report/render", dependencies=protected)
    @app.post("/v1/dxpro/agents/report/render", dependencies=protected)
    def render_executive_report(request: AgentExecuteRequest) -> dict[str, Any]:
        return pro_agents["report_renderer"].execute(request.to_payload())

    @app.post("/v1/agents/report/export", dependencies=protected)
    @app.post("/v1/dxpro/agents/report/export", dependencies=protected)
    def export_executive_report(request: AgentExecuteRequest) -> dict[str, Any]:
        return pro_agents["report_exporter"].execute(request.to_payload())

    @app.post("/v1/agents/cases/run", dependencies=protected)
    @app.post("/v1/dxpro/agents/cases/run", dependencies=protected)
    def run_diagnostic_case(request: AgentExecuteRequest) -> dict[str, Any]:
        return pro_agents["diagnostic_case_runner"].execute(request.to_payload())

    @app.post("/v1/agents/cases/approval", dependencies=protected)
    @app.post("/v1/dxpro/agents/cases/approval", dependencies=protected)
    def run_case_approval(request: AgentExecuteRequest) -> dict[str, Any]:
        payload = request.to_payload()
        action = str(payload.get("action", ""))
        case_id = str(payload.get("case_id", ""))
        if action == "publish" and case_id:
            decision = grammar_service.check_publish(case_id)
            if not decision.allowed:
                return {
                    "case_id": case_id,
                    "action": "publish",
                    "approved": False,
                    "reason": decision.reason,
                    "grammar_blocked": True,
                    "grammar_bypass_detected": True,
                }
            if decision.confirm_required:
                grammar_confirmed = payload.get("grammar_confirmed", False)
                if not grammar_confirmed:
                    return {
                        "case_id": case_id,
                        "action": "publish",
                        "approved": False,
                        "reason": "Se requiere confirmación gramatical. Envíe grammar_confirmed=true.",
                        "grammar_confirm_required": True,
                        "grammar_bypass_detected": True,
                    }
        return pro_agents["case_approval"].execute(payload)

    # --- Gramática Canónica ARHIAX ---
    @app.post("/v1/agents/grammar/lint", dependencies=protected)
    @app.post("/v1/dxpro/agents/grammar/lint", dependencies=protected)
    def grammar_lint(request: GrammarLintRequest) -> dict[str, Any]:
        if not request.text or not request.text.strip():
            raise HTTPException(status_code=400, detail={"error": "text_empty", "message": "El texto no puede estar vacío."})

        if request.audience not in ("internal", "client", "technical", "executive"):
            raise HTTPException(status_code=400, detail={"error": "invalid_audience", "message": f"Audiencia inválida: {request.audience}"})

        exceptions = [
            GrammarException(**e) for e in request.exceptions
            if e.get("reason", "").strip()
        ]

        report = grammar_service.run_lint(
            text=request.text,
            audience=cast(GrammarAudience, request.audience),
            source=request.source,
            case_id=request.case_id,
            exceptions=exceptions,
        )
        return report.model_dump(mode="json")

    @app.get("/v1/cases/{case_id}/grammar", dependencies=protected)
    def get_case_grammar(case_id: str) -> dict[str, Any]:
        summary = grammar_service.get_case_grammar(case_id)
        return summary.model_dump(mode="json")

    @app.post("/v1/cases/{case_id}/publish", dependencies=protected)
    def publish_case(case_id: str, request: GrammarPublishRequest) -> dict[str, Any]:
        case = case_store.load(case_id)
        if case is None:
            raise HTTPException(status_code=404, detail={"error": "case_not_found", "case_id": case_id})

        decision = grammar_service.check_publish(case_id)

        if not decision.allowed:
            return {
                "case_id": case_id,
                "action": "publish",
                "approved": False,
                "reason": decision.reason,
                "grammar_blocked": True,
            }

        if decision.confirm_required and not request.grammar_confirmed:
            return {
                "case_id": case_id,
                "action": "publish",
                "approved": False,
                "reason": "Se requiere confirmación gramatical. Envíe grammar_confirmed=true.",
                "grammar_confirm_required": True,
            }

        case_store.append_history(case_id, {
            "action": "publish",
            "grammar_checked": True,
            "grammar_score": decision.model_dump(mode="json") if decision else None,
            "reviewer": request.reviewer,
        })

        return {
            "case_id": case_id,
            "action": "publish",
            "approved": True,
            "reason": "Publicación aprobada. Gramática canónica verificada.",
        }

    return app
