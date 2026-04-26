"""Standalone governed diagnostic orchestration for ARHIAX DX Pro."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from .catalog import DxProCatalog, autonomy_rank
from .config import RuntimeConfig
from .provenance import ProvenanceSigner
from .runtime import DxProRuntime


OUTCOME_PRIORITY = {
    "PERMIT": 0,
    "AUDIT": 1,
    "MODIFY": 2,
    "ESCALATE": 3,
    "DENY": 4,
    "SUSPEND": 5,
}


class DiagnosticService:
    def __init__(self, config: RuntimeConfig, catalog: DxProCatalog, runtime: DxProRuntime) -> None:
        self.config = config
        self.catalog = catalog
        self.runtime = runtime
        self.signer = ProvenanceSigner(config.evidence_secret)

    def compliance_posture(self) -> dict[str, Any]:
        return {
            "processing_model": "standalone governed diagnostic pipeline with PMEL/ATK controls",
            "agent_identity": self.catalog.agent_identity(),
            "tool_manifest": self.catalog.tool_manifest(),
            "data_scopes": self.catalog.data_scopes(),
            "operations": self.catalog.operations(),
            "autonomy_profile": self.catalog.autonomy_profile(),
            "policy_matrix": self.catalog.policy_matrix(),
            "model_strategy_summary": self.catalog.model_strategy(),
            "bbr_baseline": self.catalog.bbr_baseline(),
            "policy_bundle": self.runtime.policy_engine.manifest,
            "ledger_head": self.runtime.ledger.head(),
        }

    def install_readiness(self) -> dict[str, Any]:
        checks = [
            {"id": "runtime_root", "status": "PASS", "detail": str(self.config.root_dir)},
            {"id": "ledger_path", "status": "PASS", "detail": str(self.config.ledger_path)},
            {
                "id": "policy_bundle",
                "status": "PASS" if self.config.policy_bundle_path.exists() else "FAIL",
                "detail": str(self.config.policy_bundle_path),
            },
            {
                "id": "opa_binding",
                "status": "PASS" if self.config.opa_url else "WARN",
                "detail": self.config.opa_url or "native fallback active",
            },
        ]
        return {
            "ready": all(item["status"] != "FAIL" for item in checks),
            "checks": checks,
            "required_install_bindings": self.install_blueprint()["required_bindings"],
        }

    def install_blueprint(self) -> dict[str, Any]:
        return {
            "product": "ARHIAX DX Pro",
            "mode": "standalone",
            "required_bindings": [
                "DXPRO_EVIDENCE_SECRET",
                "DXPRO_POLICY_BUNDLE_PATH",
                "DXPRO_LEDGER_PATH",
                "client_model_provider_keys",
                "human_intervention_channel",
                "observability_stack",
            ],
            "optional_bindings": ["DXPRO_OPA_URL"],
        }

    def verify_certificate(self, certificate: dict[str, Any]) -> dict[str, Any]:
        verification = self.signer.verify_certificate(certificate)
        evidence_hmac = certificate.get("evidence_hmac")
        trace_id = certificate.get("trace_id")
        evidence_match = False
        if trace_id and evidence_hmac:
            evidence_match = any(entry.get("entry_hmac") == evidence_hmac for entry in self.runtime.ledger.find_by_trace(str(trace_id)))
        return {
            **verification,
            "evidence_match": evidence_match,
            "trusted": verification["valid"] and evidence_match,
        }

    def audit_pack(self, trace_id: str) -> dict[str, Any] | None:
        entries = self.runtime.ledger.find_by_trace(trace_id)
        if not entries:
            return None
        certificates = [
            entry["certificate"]
            for entry in entries
            if entry.get("event_type") == "provenance_certificate" and isinstance(entry.get("certificate"), dict)
        ]
        diagnostic_entries = [entry for entry in entries if entry.get("event_type") == "diagnostic_evaluation"]
        pmel_entries = [entry for entry in entries if entry.get("event_type") in {"policy_decision", "pmel_step_aggregate"}]
        return {
            "audit_pack_version": "0.1.0-alpha",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "trace_id": trace_id,
            "ledger_verification": self.runtime.ledger.verify(),
            "entry_count": len(entries),
            "diagnostic_evidence_ids": [entry["id"] for entry in diagnostic_entries],
            "pmel_evidence_ids": [entry["id"] for entry in pmel_entries],
            "certificate_evidence_ids": [
                entry["id"] for entry in entries if entry.get("event_type") == "provenance_certificate"
            ],
            "certificates": certificates,
            "certificate_verifications": [self.verify_certificate(certificate) for certificate in certificates],
            "entries": entries,
        }

    def evaluate(self, payload: dict[str, Any]) -> dict[str, Any]:
        request_id = payload.get("request_id") or str(uuid.uuid4())
        trace_id = payload.get("trace_id") or str(uuid.uuid4())
        requested_tools = payload.get("requested_tools") or self.catalog.default_pipeline_tools()
        requested_operations = payload.get("requested_operations") or ["modelInvoke", "toolCall", "dataAccess", "pmelCapture"]
        requested_data_scopes = payload.get("requested_data_scopes") or ["organizational_context", "audit_log", "pmel_artifacts"]
        requested_autonomy_level = payload.get("requested_autonomy_level", "A1")

        rules = self._preflight_rules(payload, requested_tools, requested_operations, requested_data_scopes, requested_autonomy_level)
        rules.extend(self._execution_rules(payload))
        rule_outcome = self._aggregate_rule_outcome(rules)

        pmel_step = self._run_diagnostic_pmel_step(payload, trace_id, requested_autonomy_level)
        final_outcome = self._dominant_outcome([rule_outcome, pmel_step["outcome"]])
        decision = {
            "status": final_outcome,
            "allowed": final_outcome in {"PERMIT", "AUDIT", "MODIFY"},
            "requires_human": final_outcome == "ESCALATE",
            "reasons": self._decision_reasons(rules, pmel_step),
        }
        execution_fingerprint = self._execution_fingerprint(payload, requested_tools)
        execution_plan = self._build_execution_plan(requested_tools, requested_autonomy_level, final_outcome, execution_fingerprint)
        evidence = self.runtime.ledger.append(
            {
                "trace_id": trace_id,
                "request_id": request_id,
                "subject": "dxpro-diagnostic-agent",
                "event_type": "diagnostic_evaluation",
                "execution_fingerprint": execution_fingerprint,
                "decision": decision,
                "rule_ids": [rule["rule_id"] for rule in rules],
                "pmel_aggregate_evidence_id": pmel_step["evidence_id"],
                "planned_tools": [tool["name"] for tool in execution_plan["planned_tools"]],
            }
        )
        certificate = None
        certificate_evidence = None
        processing_profile = payload.get("processing_profile", {})
        if processing_profile.get("issue_certificate", True):
            certificate = self.signer.issue_certificate(
                trace_id=trace_id,
                request_id=request_id,
                decision=decision,
                rule_results=rules,
                evidence_hmac=evidence["entry_hmac"],
                metadata={"agent": self.catalog.agent_identity(), "catalog_version": self.catalog.version},
            )
            certificate_evidence = self.runtime.ledger.append(
                {
                    "trace_id": trace_id,
                    "request_id": request_id,
                    "subject": "dxpro-diagnostic-agent",
                    "event_type": "provenance_certificate",
                    "certificate": certificate,
                    "diagnostic_evidence_id": evidence["id"],
                    "diagnostic_evidence_hmac": evidence["entry_hmac"],
                }
            )
        return {
            "request_id": request_id,
            "trace_id": trace_id,
            "decision": decision,
            "execution_plan": execution_plan,
            "certificate": certificate,
            "rule_results": rules,
            "pmel_step": pmel_step,
            "evidence_id": evidence["id"],
            "certificate_evidence_id": certificate_evidence["id"] if certificate_evidence else None,
            "human_review_required": decision["requires_human"],
        }

    def _preflight_rules(
        self,
        payload: dict[str, Any],
        requested_tools: list[str],
        requested_operations: list[str],
        requested_data_scopes: list[str],
        requested_autonomy_level: str,
    ) -> list[dict[str, Any]]:
        client = payload.get("client", {})
        mandate = payload.get("mandate", {})
        processing_profile = payload.get("processing_profile", {})
        return [
            self._rule("DXPRO-G1-IDENTITY", bool(client.get("client_id") and client.get("legal_name")), "Client identity metadata is present.", "Client identity metadata is incomplete.", "CRITICAL"),
            self._rule("DXPRO-G2-BOUNDARY", client.get("authorized_boundary_id", self.catalog.agent_identity()["authorization_boundary_id"]) == self.catalog.agent_identity()["authorization_boundary_id"], "Authorization boundary matches DX Pro.", "Request boundary does not match DX Pro.", "CRITICAL"),
            self._rule("DXPRO-MANDATE-001", bool(mandate.get("size_org")), "Mandate contains size_org.", "Mandate is incomplete: size_org is required.", "HIGH"),
            self._undeclared_rule("DXPRO-TOOLS-001", requested_tools, self.catalog.declared_tool_names(), "tools"),
            self._undeclared_rule("DXPRO-OPS-001", requested_operations, self.catalog.declared_operation_names(), "operations"),
            self._undeclared_rule("DXPRO-DATA-001", requested_data_scopes, self.catalog.declared_scope_names(), "data scopes"),
            self._rule("DXPRO-AUTONOMY-001", 0 <= autonomy_rank(requested_autonomy_level) <= autonomy_rank("A2"), "Requested autonomy is valid for DX Pro.", "Requested autonomy is invalid or above DX Pro maximum A2.", "CRITICAL"),
            self._rule("DXPRO-DATA-002", not processing_profile.get("store_raw_respondent_data", False), "Respondent handling remains anonymized.", "The request attempts to process non-anonymized respondent data.", "CRITICAL"),
            self._prompt_injection_rule(payload),
            self._operating_window_rule(payload),
        ]

    def _execution_rules(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        simulation = payload.get("simulation", {})
        processing_profile = payload.get("processing_profile", {})
        requested_tools = set(payload.get("requested_tools") or [])
        qa_score = float(simulation.get("qa_score", 100))
        irr_alpha = simulation.get("irr_alpha")
        return [
            self._rule("DXPRO-QA-001", "docx_generator" not in requested_tools or qa_score >= 85, "QA gate is satisfied.", "QA score is below 85/100, final document generation is denied.", "HIGH"),
            self._rule("DXPRO-HIC-001", not processing_profile.get("publish_report", False), "No publication request was made.", "Publishing the report requires human approval.", "HIGH", fail_outcome="ESCALATE"),
            self._rule("DXPRO-HIC-002", float(simulation.get("delta_sigma", 0.0)) <= 2.0, "No critical delta_sigma gap was detected.", "A critical delta_sigma gap requires human review.", "MEDIUM", fail_outcome="ESCALATE"),
            self._rule("DXPRO-RISK-002", irr_alpha is None or float(irr_alpha) >= 0.70, "IRR is within acceptable range or absent.", "IRR is below 0.70 and requires human review.", "HIGH", fail_outcome="ESCALATE"),
            self._rule("DXPRO-DATA-003", int(processing_profile.get("retention_days", 30)) <= 30, "Retention policy stays within 30 days.", "Retention policy exceeds the 30-day limit.", "HIGH"),
        ]

    def _run_diagnostic_pmel_step(self, payload: dict[str, Any], trace_id: str, requested_autonomy_level: str) -> dict[str, Any]:
        pmel = payload.get("pmel", {})
        aibom = pmel.get(
            "aibom",
            {
                "bundle_version": self.catalog.version,
                "models": ["client_bound_model"],
                "prompts": ["dxpro-diagnostic-v1"],
                "owner": "Sinergia Consulting Group",
            },
        )
        consents = pmel.get("consents", {"T1": True, "T3": True})
        step = self.runtime.run_step(
            {
                "trace_id": trace_id,
                "subject": "dxpro-diagnostic-agent",
                "step": "diagnostic_pre_execution",
                "input": {
                    "autonomy": {
                        "component": "diagnostic_agent",
                        "requested_level": requested_autonomy_level,
                        "violations_30d": int(pmel.get("violations_30d", 0)),
                    },
                    "consent": {"action": pmel.get("action", "ingest_to_llm"), "consents": consents},
                    "aibom": aibom,
                    "execution": {
                        "component": pmel.get("component", "capture_agent"),
                        "current_cycle": int(pmel.get("current_cycle", 0)),
                        "last_outcome": pmel.get("last_outcome", "in_progress"),
                        "request_another_cycle": bool(pmel.get("request_another_cycle", False)),
                    },
                },
            }
        )
        return step.to_dict()

    def _build_execution_plan(self, requested_tools: list[str], autonomy_level: str, outcome: str, fingerprint: str) -> dict[str, Any]:
        planned_tools = []
        for tool_name in requested_tools:
            tool = self.catalog.get_tool(tool_name)
            if not tool:
                planned_tools.append({"name": tool_name, "allowed": False, "reason": "Tool is not declared.", "severity": "CRITICAL"})
                continue
            allowed = autonomy_rank(tool["minimum_autonomy"]) <= autonomy_rank(autonomy_level)
            planned_tools.append({**tool, "allowed": allowed, "reason": "Allowed under DX Pro governance." if allowed else f"Requires {tool['minimum_autonomy']}."})
        return {
            "pipeline_name": self.catalog.agent_identity()["name"],
            "execution_fingerprint": fingerprint,
            "execution_status": "PASS" if outcome in {"PERMIT", "AUDIT", "MODIFY"} else "PARTIAL" if outcome == "ESCALATE" else "FAIL",
            "requested_tools": requested_tools,
            "planned_tools": planned_tools,
            "active_models": self.catalog.model_strategy(),
        }

    def _rule(self, rule_id: str, passed: bool, pass_message: str, fail_message: str, severity: str, fail_outcome: str = "DENY") -> dict[str, Any]:
        return {
            "rule_id": rule_id,
            "outcome": "PASS" if passed else fail_outcome,
            "severity": severity,
            "message": pass_message if passed else fail_message,
        }

    def _undeclared_rule(self, rule_id: str, requested: list[str], declared: set[str], label: str) -> dict[str, Any]:
        missing = sorted(item for item in requested if item not in declared)
        return self._rule(rule_id, not missing, f"Requested {label} are declared.", f"Undeclared {label} requested: {', '.join(missing)}.", "CRITICAL")

    def _prompt_injection_rule(self, payload: dict[str, Any]) -> dict[str, Any]:
        mandate = payload.get("mandate", {})
        simulation = payload.get("simulation", {})
        haystack = f"{mandate.get('objective', '')} {simulation.get('prompt_text', '')}".lower()
        patterns = ["ignore previous instructions", "system prompt", "developer message", "bypass policy", "reveal hidden"]
        return self._rule("DXPRO-RISK-001", not any(pattern in haystack for pattern in patterns), "No prompt injection pattern was detected.", "Prompt injection pattern detected.", "CRITICAL")

    def _operating_window_rule(self, payload: dict[str, Any]) -> dict[str, Any]:
        simulation = payload.get("simulation", {})
        weekday = simulation.get("current_weekday")
        hour = simulation.get("current_hour")
        if weekday is None or hour is None:
            now = datetime.now(ZoneInfo("America/Bogota"))
            weekday = now.weekday()
            hour = now.hour
        inside = int(weekday) < 5 and 7 <= int(hour) < 22
        return self._rule("DXPRO-OPS-002", inside, "Request is inside operating window.", "Request is outside operating window.", "MEDIUM")

    def _aggregate_rule_outcome(self, rules: list[dict[str, Any]]) -> str:
        outcomes = []
        for rule in rules:
            if rule["outcome"] in {"DENY", "ESCALATE"}:
                outcomes.append(rule["outcome"])
        return self._dominant_outcome(outcomes or ["PERMIT"])

    def _dominant_outcome(self, outcomes: list[str]) -> str:
        return max(outcomes, key=lambda outcome: OUTCOME_PRIORITY.get(outcome, 4))

    def _decision_reasons(self, rules: list[dict[str, Any]], pmel_step: dict[str, Any]) -> list[str]:
        reasons = [rule["message"] for rule in rules if rule["outcome"] != "PASS"]
        if pmel_step["outcome"] != "PERMIT":
            reasons.append(pmel_step["reason"])
        return reasons

    def _execution_fingerprint(self, payload: dict[str, Any], requested_tools: list[str]) -> str:
        client = payload.get("client", {})
        mandate = payload.get("mandate", {})
        raw = "|".join(
            [
                str(client.get("client_id", "")),
                str(mandate.get("organization_name", "")),
                str(mandate.get("domain", "")),
                str(mandate.get("subprocess", "")),
                ",".join(sorted(requested_tools)),
            ]
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()
