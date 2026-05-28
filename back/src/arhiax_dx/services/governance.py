"""Governance checks for ARHIAX Dx."""

from __future__ import annotations

import hashlib
from datetime import datetime
from zoneinfo import ZoneInfo

from arhiax_dx.config import Settings
from arhiax_dx.models import DiagnosticRequest, GovernanceDecision, RuleOutcome, RuleResult, Severity, DecisionStatus
from arhiax_dx.services.tool_registry import ToolRegistry, autonomy_rank


def _detect_prompt_injection(*values: str) -> bool:
    haystack = " ".join(values).lower()
    patterns = [
        "ignore previous instructions",
        "system prompt",
        "developer message",
        "bypass policy",
        "reveal hidden",
    ]
    return any(pattern in haystack for pattern in patterns)


class GovernanceEngine:
    def __init__(self, settings: Settings, registry: ToolRegistry):
        self.settings = settings
        self.registry = registry

    def evaluate_preflight(self, request: DiagnosticRequest) -> tuple[GovernanceDecision, list[RuleResult]]:
        rules = [
            self._identity_rule(request),
            self._boundary_rule(request),
            self._mandate_rule(request),
            self._tool_declaration_rule(request),
            self._operation_rule(request),
            self._data_scope_rule(request),
            self._autonomy_validity_rule(request),
            self._autonomy_change_rule(request),
            self._tool_autonomy_rule(request),
            self._anonymization_rule(request),
            self._prompt_injection_rule(request),
            self._operating_window_rule(request),
            self._evidence_rule(),
        ]
        return self._decision_from_rules(rules), rules

    def evaluate_execution(self, request: DiagnosticRequest) -> tuple[GovernanceDecision, list[RuleResult]]:
        rules = [
            self._qa_rule(request),
            self._publication_rule(request),
            self._delta_sigma_rule(request),
            self._irr_rule(request),
            self._retention_rule(request),
        ]
        return self._decision_from_rules(rules), rules

    @staticmethod
    def execution_fingerprint(request: DiagnosticRequest) -> str:
        raw = "|".join(
            [
                request.client.client_id,
                request.mandate.organization_name,
                request.mandate.domain,
                request.mandate.subprocess,
                ",".join(sorted(request.requested_tools)),
            ]
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _decision_from_rules(self, rules: list[RuleResult]) -> GovernanceDecision:
        failures = [rule.message for rule in rules if rule.outcome == RuleOutcome.FAIL]
        escalations = [rule.message for rule in rules if rule.outcome == RuleOutcome.ESCALATE]
        logs = [rule.message for rule in rules if rule.outcome == RuleOutcome.LOG_ONLY]
        if failures:
            return GovernanceDecision(status=DecisionStatus.DENY, reasons=failures, policy_bundles=self.settings.policy_bundles, requires_human=False)
        if escalations:
            return GovernanceDecision(status=DecisionStatus.ESCALATE_TO_HUMAN, reasons=escalations, policy_bundles=self.settings.policy_bundles, requires_human=True)
        if logs:
            return GovernanceDecision(status=DecisionStatus.ALLOW_WITH_HIC_NOTIFICATION, reasons=logs, policy_bundles=self.settings.policy_bundles, requires_human=False)
        return GovernanceDecision(status=DecisionStatus.ALLOW, reasons=[], policy_bundles=self.settings.policy_bundles, requires_human=False)

    def _identity_rule(self, request: DiagnosticRequest) -> RuleResult:
        if request.client.client_id and request.client.legal_name:
            return RuleResult(rule_id="DX-G1-IDENTITY", description="Diagnostic envelope must identify the client and legal entity.", outcome=RuleOutcome.PASS, severity=Severity.MEDIUM, message="Client identity metadata is present.")
        return RuleResult(rule_id="DX-G1-IDENTITY", description="Diagnostic envelope must identify the client and legal entity.", outcome=RuleOutcome.FAIL, severity=Severity.CRITICAL, message="Client identity metadata is incomplete.")

    def _boundary_rule(self, request: DiagnosticRequest) -> RuleResult:
        expected = self.registry.agent_identity()["authorization_boundary_id"]
        if request.client.authorized_boundary_id == expected:
            return RuleResult(rule_id="DX-G2-BOUNDARY", description="The request must stay inside the governed authorization boundary.", outcome=RuleOutcome.PASS, severity=Severity.MEDIUM, message="Authorization boundary matches the governed ARHIAX Dx boundary.")
        return RuleResult(rule_id="DX-G2-BOUNDARY", description="The request must stay inside the governed authorization boundary.", outcome=RuleOutcome.FAIL, severity=Severity.CRITICAL, message="Request boundary does not match boundary-diagnostico-org.")

    @staticmethod
    def _mandate_rule(request: DiagnosticRequest) -> RuleResult:
        if request.mandate.size_org:
            return RuleResult(rule_id="DX-MANDATE-001", description="Mandate must include organization size before running the governed pipeline.", outcome=RuleOutcome.PASS, severity=Severity.MEDIUM, message="Mandate contains size_org and can be routed.")
        return RuleResult(rule_id="DX-MANDATE-001", description="Mandate must include organization size before running the governed pipeline.", outcome=RuleOutcome.FAIL, severity=Severity.HIGH, message="Mandate is incomplete: size_org is required before execution.")

    def _tool_declaration_rule(self, request: DiagnosticRequest) -> RuleResult:
        undeclared = [tool for tool in request.requested_tools if tool not in self.registry.declared_tool_names()]
        if not undeclared:
            return RuleResult(rule_id="DX-TOOLS-001", description="Requested tools must be declared in the governed catalog.", outcome=RuleOutcome.PASS, severity=Severity.MEDIUM, message="All requested tools are declared in the ARHIAX Dx catalog.")
        return RuleResult(rule_id="DX-TOOLS-001", description="Requested tools must be declared in the governed catalog.", outcome=RuleOutcome.FAIL, severity=Severity.CRITICAL, message=f"Undeclared tools requested: {', '.join(undeclared)}.")

    def _operation_rule(self, request: DiagnosticRequest) -> RuleResult:
        undeclared = [item for item in request.requested_operations if item not in self.registry.declared_operation_names()]
        if not undeclared:
            return RuleResult(rule_id="DX-OPS-001", description="Requested operations must be declared and enabled.", outcome=RuleOutcome.PASS, severity=Severity.MEDIUM, message="Requested operations are declared and enabled.")
        return RuleResult(rule_id="DX-OPS-001", description="Requested operations must be declared and enabled.", outcome=RuleOutcome.FAIL, severity=Severity.CRITICAL, message=f"Undeclared operations requested: {', '.join(undeclared)}.")

    def _data_scope_rule(self, request: DiagnosticRequest) -> RuleResult:
        undeclared = [item for item in request.requested_data_scopes if item not in self.registry.declared_scope_names()]
        if not undeclared:
            return RuleResult(rule_id="DX-DATA-001", description="Requested data scopes must be declared in the governed scope catalog.", outcome=RuleOutcome.PASS, severity=Severity.MEDIUM, message="Requested data scopes are declared.")
        return RuleResult(rule_id="DX-DATA-001", description="Requested data scopes must be declared in the governed scope catalog.", outcome=RuleOutcome.FAIL, severity=Severity.CRITICAL, message=f"Undeclared data scopes requested: {', '.join(undeclared)}.")

    @staticmethod
    def _autonomy_validity_rule(request: DiagnosticRequest) -> RuleResult:
        if autonomy_rank(request.requested_autonomy_level) >= 0:
            return RuleResult(rule_id="DX-AUTONOMY-001", description="Requested autonomy level must be valid.", outcome=RuleOutcome.PASS, severity=Severity.MEDIUM, message="Requested autonomy level is valid.")
        return RuleResult(rule_id="DX-AUTONOMY-001", description="Requested autonomy level must be valid.", outcome=RuleOutcome.FAIL, severity=Severity.CRITICAL, message="Requested autonomy level is invalid.")

    def _autonomy_change_rule(self, request: DiagnosticRequest) -> RuleResult:
        initial = self.registry.agent_identity()["initial_autonomy_level"]
        if autonomy_rank(request.requested_autonomy_level) <= autonomy_rank(initial):
            return RuleResult(rule_id="DX-AUTONOMY-002", description="Autonomy changes require objective metrics and human approval.", outcome=RuleOutcome.PASS, severity=Severity.MEDIUM, message="Requested autonomy does not exceed the packaged starting level.")
        if not request.simulation.get("human_approval", False):
            return RuleResult(rule_id="DX-AUTONOMY-002", description="Autonomy changes require objective metrics and human approval.", outcome=RuleOutcome.FAIL, severity=Severity.HIGH, message="Changing autonomy level requires director-sinergia-001 approval.")
        promotion = self.registry.promotion_assessment(request.simulation)
        if not promotion["eligible_for_a2"]:
            return RuleResult(rule_id="DX-AUTONOMY-002", description="Autonomy changes require objective metrics and human approval.", outcome=RuleOutcome.FAIL, severity=Severity.HIGH, message="Promotion to A2 was requested without satisfying BBR, QA, and IRR thresholds.")
        return RuleResult(rule_id="DX-AUTONOMY-002", description="Autonomy changes require objective metrics and human approval.", outcome=RuleOutcome.PASS, severity=Severity.MEDIUM, message="Promotion requirements for A2 are satisfied.")

    def _tool_autonomy_rule(self, request: DiagnosticRequest) -> RuleResult:
        blocked = []
        for tool_name in request.requested_tools:
            tool = self.registry.get_tool(tool_name)
            if tool and autonomy_rank(tool["minimum_autonomy"]) > autonomy_rank(request.requested_autonomy_level):
                blocked.append(tool_name)
        if not blocked:
            return RuleResult(rule_id="DX-TOOLS-002", description="Requested tools must fit under the current autonomy level.", outcome=RuleOutcome.PASS, severity=Severity.MEDIUM, message="Requested tools fit under the requested autonomy level.")
        return RuleResult(rule_id="DX-TOOLS-002", description="Requested tools must fit under the current autonomy level.", outcome=RuleOutcome.FAIL, severity=Severity.HIGH, message=f"Tools require higher autonomy than {request.requested_autonomy_level}: {', '.join(blocked)}.")

    @staticmethod
    def _anonymization_rule(request: DiagnosticRequest) -> RuleResult:
        if request.processing_profile.store_raw_respondent_data or request.simulation.get("non_anonymized_respondent_data", False):
            return RuleResult(rule_id="DX-DATA-002", description="Respondent data must remain anonymized and non-retained in raw form.", outcome=RuleOutcome.FAIL, severity=Severity.CRITICAL, message="The request attempts to process non-anonymized respondent data.")
        return RuleResult(rule_id="DX-DATA-002", description="Respondent data must remain anonymized and non-retained in raw form.", outcome=RuleOutcome.PASS, severity=Severity.HIGH, message="Respondent handling remains anonymized and governed.")

    @staticmethod
    def _prompt_injection_rule(request: DiagnosticRequest) -> RuleResult:
        if _detect_prompt_injection(request.mandate.objective or "", str(request.simulation.get("prompt_text", ""))):
            return RuleResult(rule_id="DX-RISK-001", description="Prompt injection patterns must be denied with incident handling.", outcome=RuleOutcome.FAIL, severity=Severity.CRITICAL, message="Prompt injection pattern detected in the mandate payload.")
        return RuleResult(rule_id="DX-RISK-001", description="Prompt injection patterns must be denied with incident handling.", outcome=RuleOutcome.PASS, severity=Severity.HIGH, message="No prompt injection pattern was detected.")

    def _operating_window_rule(self, request: DiagnosticRequest) -> RuleResult:
        weekday = request.simulation.get("current_weekday")
        hour = request.simulation.get("current_hour")
        if weekday is None or hour is None:
            now = datetime.now(ZoneInfo(self.settings.operating_timezone))
            weekday = now.weekday()
            hour = now.hour
        inside = int(weekday) < 5 and self.settings.operating_window_start <= int(hour) < self.settings.operating_window_end
        if inside:
            return RuleResult(rule_id="DX-OPS-002", description="Execution must stay inside the configured operating window.", outcome=RuleOutcome.PASS, severity=Severity.MEDIUM, message="Request is inside the operating window.")
        return RuleResult(rule_id="DX-OPS-002", description="Execution must stay inside the configured operating window.", outcome=RuleOutcome.FAIL, severity=Severity.MEDIUM, message="Request is outside the configured operating window and must be queued for the next business window.")

    @staticmethod
    def _evidence_rule() -> RuleResult:
        return RuleResult(rule_id="DX-G5-EVIDENCE", description="Every governed decision must emit evidence.", outcome=RuleOutcome.PASS, severity=Severity.MEDIUM, message="Evidence-by-construction is active.")

    @staticmethod
    def _qa_rule(request: DiagnosticRequest) -> RuleResult:
        requested_docx = "docx_generator" in request.requested_tools or bool(request.simulation.get("generate_docx", False))
        qa_score = float(request.simulation.get("qa_score", 100.0))
        if requested_docx and qa_score < 85.0:
            return RuleResult(rule_id="DX-QA-001", description="DOCX generation requires QA >= 85 before approval.", outcome=RuleOutcome.FAIL, severity=Severity.HIGH, message="QA score is below 85/100, so final document generation is denied.")
        return RuleResult(rule_id="DX-QA-001", description="DOCX generation requires QA >= 85 before approval.", outcome=RuleOutcome.PASS, severity=Severity.MEDIUM, message="QA gate is satisfied for the current execution.")

    @staticmethod
    def _publication_rule(request: DiagnosticRequest) -> RuleResult:
        if request.processing_profile.publish_report or request.simulation.get("publish_report", False):
            return RuleResult(rule_id="DX-HIC-001", description="Publishing the final report always requires human approval.", outcome=RuleOutcome.ESCALATE, severity=Severity.HIGH, message="Publishing the report requires director-sinergia-001 approval.")
        return RuleResult(rule_id="DX-HIC-001", description="Publishing the final report always requires human approval.", outcome=RuleOutcome.PASS, severity=Severity.MEDIUM, message="No publication request was made in this execution.")

    @staticmethod
    def _delta_sigma_rule(request: DiagnosticRequest) -> RuleResult:
        if float(request.simulation.get("delta_sigma", 0.0)) > 2.0:
            return RuleResult(rule_id="DX-HIC-002", description="Critical perception gaps require human review.", outcome=RuleOutcome.ESCALATE, severity=Severity.MEDIUM, message="A critical delta_sigma gap was detected and must be reviewed by a human.")
        return RuleResult(rule_id="DX-HIC-002", description="Critical perception gaps require human review.", outcome=RuleOutcome.PASS, severity=Severity.MEDIUM, message="No critical delta_sigma gap was detected.")

    @staticmethod
    def _irr_rule(request: DiagnosticRequest) -> RuleResult:
        irr_alpha = request.simulation.get("irr_alpha")
        if irr_alpha is not None and float(irr_alpha) < 0.70:
            return RuleResult(rule_id="DX-RISK-002", description="Low inter-rater reliability requires human review.", outcome=RuleOutcome.ESCALATE, severity=Severity.HIGH, message="IRR is below 0.70 and requires human review before continuing.")
        return RuleResult(rule_id="DX-RISK-002", description="Low inter-rater reliability requires human review.", outcome=RuleOutcome.PASS, severity=Severity.MEDIUM, message="IRR is within the acceptable range or was not provided.")

    @staticmethod
    def _retention_rule(request: DiagnosticRequest) -> RuleResult:
        if request.processing_profile.retention_days > 30:
            return RuleResult(rule_id="DX-DATA-003", description="Outputs must not be retained beyond 30 days.", outcome=RuleOutcome.FAIL, severity=Severity.HIGH, message="Retention policy exceeds the 30-day data minimization limit.")
        return RuleResult(rule_id="DX-DATA-003", description="Outputs must not be retained beyond 30 days.", outcome=RuleOutcome.PASS, severity=Severity.MEDIUM, message="Retention policy stays within the 30-day maximum.")
