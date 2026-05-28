"""End-to-end governed diagnostic orchestration."""

from __future__ import annotations

import hashlib
import json

from arhiax_dx.config import Settings
from arhiax_dx.models import CapabilityRecord, DecisionStatus, DiagnosticRequest, DiagnosticResponse, ExecutionPlan, GovernanceDecision, PlannedTool, Severity
from arhiax_dx.services.evidence import EvidenceLedger
from arhiax_dx.services.governance import GovernanceEngine
from arhiax_dx.services.provenance import ProvenanceSigner
from arhiax_dx.services.tool_registry import ToolRegistry, autonomy_rank


def _stable_hash(payload: dict) -> str:
    canonical = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class DiagnosticService:
    def __init__(self, settings: Settings, registry: ToolRegistry, governance: GovernanceEngine, ledger: EvidenceLedger, signer: ProvenanceSigner):
        self.settings = settings
        self.registry = registry
        self.governance = governance
        self.ledger = ledger
        self.signer = signer

    def evaluate(self, request: DiagnosticRequest) -> DiagnosticResponse:
        preflight_decision, preflight_rules = self.governance.evaluate_preflight(request)
        execution_fingerprint = self.governance.execution_fingerprint(request)
        execution_plan = self._build_execution_plan(request, execution_fingerprint)

        if preflight_decision.status == DecisionStatus.DENY:
            return self._response_from_denial(request, execution_plan, preflight_decision, preflight_rules)

        execution_decision, execution_rules = self.governance.evaluate_execution(request)
        final_decision = self._merge_decisions(preflight_decision, execution_decision)
        rule_results = preflight_rules + execution_rules
        records = self._capability_records(execution_plan)
        execution_plan.execution_status = self._status_from_decision(final_decision)

        ledger_entry = self.ledger.append({
            "request_id": request.request_id,
            "client_id": request.client.client_id,
            "execution_fingerprint": execution_fingerprint,
            "decision": final_decision.status.value,
            "policy_bundles": final_decision.policy_bundles,
            "governance_metadata": self.settings.governance_metadata(),
            "rule_ids": [rule.rule_id for rule in rule_results],
            "planned_tools": [tool.name for tool in execution_plan.planned_tools],
            "reasons": final_decision.reasons,
        })

        certificate = None
        if request.processing_profile.issue_certificate:
            certificate = self.signer.issue_certificate(execution_fingerprint, final_decision, rule_results, records, ledger_entry["entry_hash"])
        return DiagnosticResponse(request_id=request.request_id, decision=final_decision, execution_plan=execution_plan, certificate=certificate, rule_results=rule_results, human_review_required=final_decision.requires_human)

    def _build_execution_plan(self, request: DiagnosticRequest, execution_fingerprint: str) -> ExecutionPlan:
        tool_names = request.requested_tools or self.registry.default_pipeline_tools()
        planned_tools: list[PlannedTool] = []
        for tool_name in tool_names:
            tool = self.registry.get_tool(tool_name)
            if tool is None:
                planned_tools.append(PlannedTool(name=tool_name, severity=Severity.CRITICAL, minimum_autonomy="A4", phase="undeclared", allowed=False, reason="Tool is not declared in the governed catalog."))
                continue
            allowed = autonomy_rank(tool["minimum_autonomy"]) <= autonomy_rank(request.requested_autonomy_level)
            planned_tools.append(
                PlannedTool(
                    name=tool["name"],
                    severity=Severity(tool["severity"]),
                    minimum_autonomy=tool["minimum_autonomy"],
                    phase=tool["phase"],
                    allowed=allowed,
                    reason=f"Allowed under autonomy {request.requested_autonomy_level}." if allowed else f"Requires {tool['minimum_autonomy']}.",
                )
            )
        required_human_gates = []
        if request.processing_profile.publish_report or request.simulation.get("publish_report", False):
            required_human_gates.append("publish_report")
        if float(request.simulation.get("delta_sigma", 0.0)) > 2.0:
            required_human_gates.append("critical_delta_sigma")
        if request.requested_autonomy_level == "A2":
            required_human_gates.append("autonomy_promotion")
        return ExecutionPlan(
            pipeline_name=self.registry.agent_identity()["name"],
            execution_fingerprint=execution_fingerprint,
            execution_status="PENDING",
            requested_tools=tool_names,
            planned_tools=planned_tools,
            active_models=self.registry.active_model_routes(tool_names),
            required_human_gates=required_human_gates,
            promotion_readiness=self.registry.promotion_assessment(request.simulation),
        )

    @staticmethod
    def _capability_records(plan: ExecutionPlan) -> list[CapabilityRecord]:
        records: list[CapabilityRecord] = []
        for tool in plan.planned_tools:
            payload = {"phase": tool.phase, "minimum_autonomy": tool.minimum_autonomy, "allowed": tool.allowed, "reason": tool.reason}
            records.append(CapabilityRecord(capability=tool.name, criticality=tool.severity, payload=payload, payload_hash=_stable_hash(payload)))
        return records

    def _response_from_denial(self, request: DiagnosticRequest, plan: ExecutionPlan, decision: GovernanceDecision, rules):
        plan.execution_status = "FAIL"
        ledger_entry = self.ledger.append({
            "request_id": request.request_id,
            "client_id": request.client.client_id,
            "execution_fingerprint": plan.execution_fingerprint,
            "decision": decision.status.value,
            "policy_bundles": decision.policy_bundles,
            "governance_metadata": self.settings.governance_metadata(),
            "rule_ids": [rule.rule_id for rule in rules],
            "planned_tools": [tool.name for tool in plan.planned_tools],
            "reasons": decision.reasons,
        })
        certificate = None
        if request.processing_profile.issue_certificate:
            certificate = self.signer.issue_certificate(plan.execution_fingerprint, decision, rules, self._capability_records(plan), ledger_entry["entry_hash"])
        return DiagnosticResponse(request_id=request.request_id, decision=decision, execution_plan=plan, certificate=certificate, rule_results=rules, human_review_required=decision.requires_human)

    @staticmethod
    def _merge_decisions(preflight: GovernanceDecision, execution: GovernanceDecision) -> GovernanceDecision:
        if execution.status in {DecisionStatus.DENY, DecisionStatus.ESCALATE_TO_HUMAN}:
            return execution
        return execution

    @staticmethod
    def _status_from_decision(decision: GovernanceDecision) -> str:
        if decision.status == DecisionStatus.ALLOW:
            return "PASS"
        if decision.status in {DecisionStatus.ALLOW_WITH_HIC_NOTIFICATION, DecisionStatus.ESCALATE_TO_HUMAN}:
            return "PARTIAL"
        return "FAIL"
