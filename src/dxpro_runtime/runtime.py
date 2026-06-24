"""Evaluation orchestration."""

from __future__ import annotations

import uuid
from typing import Any

from .evidence import EvidenceLedger
from .models import EvaluationRequest, EvaluationResponse, PolicyDecision, StepDecision
from .policy import PolicyEngine


ATK_PRIORITY = {
    "PERMIT": 0,
    "AUDIT": 1,
    "MODIFY": 2,
    "ESCALATE": 3,
    "DENY": 4,
    "SUSPEND": 5,
}


class DxProRuntime:
    def __init__(self, policy_engine: PolicyEngine, ledger: EvidenceLedger) -> None:
        self.policy_engine = policy_engine
        self.ledger = ledger

    def evaluate(self, payload: dict[str, Any]) -> EvaluationResponse:
        trace_id = payload.get("trace_id") or str(uuid.uuid4())
        request = EvaluationRequest(
            package=payload["package"],
            input=payload.get("input", {}),
            subject=payload.get("subject", "pmel-runtime"),
            trace_id=trace_id,
        )
        decision = self.policy_engine.evaluate(request)
        evidence = self.ledger.append(
            {
                "trace_id": trace_id,
                "subject": request.subject,
                "package": decision.package,
                "input": request.input,
                "decision": {
                    "outcome": decision.outcome,
                    "reason": decision.reason,
                    "allowed": decision.allowed,
                    "details": decision.details,
                },
            }
        )
        return EvaluationResponse(decision=decision, evidence_id=evidence["id"], trace_id=trace_id)

    def run_step(self, payload: dict[str, Any]) -> StepDecision:
        trace_id = payload.get("trace_id") or str(uuid.uuid4())
        subject = payload.get("subject", "pmel-runtime")
        packages = payload.get("packages")
        if packages is None:
            packages = self._default_step_packages(payload)
        step_input = payload.get("input", {})
        decisions: list[dict[str, Any]] = []
        raw_decisions: list[PolicyDecision] = []

        for package in packages:
            policy_input = self._input_for_package(package, step_input)
            request = EvaluationRequest(
                package=package,
                input=policy_input,
                subject=subject,
                trace_id=trace_id,
            )
            decision = self.policy_engine.evaluate(request)
            evidence = self.ledger.append(
                {
                    "trace_id": trace_id,
                    "subject": subject,
                    "event_type": "policy_decision",
                    "package": decision.package,
                    "input": policy_input,
                    "decision": self._decision_dict(decision),
                }
            )
            decision_record = self._decision_dict(decision)
            decision_record["evidence_id"] = evidence["id"]
            decisions.append(decision_record)
            raw_decisions.append(decision)

        aggregate = self._aggregate_decisions(raw_decisions)
        aggregate_evidence = self.ledger.append(
            {
                "trace_id": trace_id,
                "subject": subject,
                "event_type": "pmel_step_aggregate",
                "step": payload.get("step", "unspecified"),
                "decision": self._decision_dict(aggregate),
                "decision_evidence_ids": [d["evidence_id"] for d in decisions],
            }
        )

        return StepDecision(
            trace_id=trace_id,
            subject=subject,
            outcome=aggregate.outcome,
            reason=aggregate.reason,
            allowed=aggregate.allowed,
            decisions=decisions,
            evidence_id=aggregate_evidence["id"],
        )

    def _default_step_packages(self, payload: dict[str, Any]) -> list[str]:
        if payload.get("scope") == "full_bundle":
            packages = self.policy_engine.package_names()
            if packages:
                return packages
        return [
            "arhia.pmel.base.autonomy",
            "arhia.pmel.governance.consent_gates",
            "arhia.pmel.base.aibom",
            "arhia.pmel.governance.cycle_limits",
        ]

    def _input_for_package(self, package: str, step_input: dict[str, Any]) -> dict[str, Any]:
        package_inputs = step_input.get("packages", {})
        if package in package_inputs:
            return package_inputs[package]
        if package == "arhia.pmel.base.autonomy":
            return step_input.get("autonomy", {})
        if package == "arhia.pmel.governance.consent_gates":
            return step_input.get("consent", {})
        if package == "arhia.pmel.base.aibom":
            return step_input.get("aibom", {})
        if package == "arhia.pmel.governance.cycle_limits":
            return step_input.get("execution", {})
        if package == "arhia.pmel.base.hic":
            return step_input.get("hic", {})
        if package.startswith("arhia.pmel.bpmn_lint."):
            return step_input.get("bpmn_lint", step_input.get("bpmn", {}))
        if package == "arhia.pmel.governance.to_be_prohibitions":
            return step_input.get("to_be", {})
        if package == "arhia.pmel.governance.sensitive_data":
            return step_input.get("sensitive_data", {})
        if package == "arhia.pmel.governance.retention":
            return step_input.get("retention", {})
        if package == "arhia.pmel.decommissioning.triggers":
            return step_input.get("decommissioning_trigger", {})
        if package == "arhia.pmel.decommissioning.crypto_shred":
            return step_input.get("crypto_shred", {})
        return step_input

    def _aggregate_decisions(self, decisions: list[PolicyDecision]) -> PolicyDecision:
        if not decisions:
            return PolicyDecision("arhia.pmel.aggregate", "DENY", "no_policy_decisions")
        strongest = max(decisions, key=lambda decision: ATK_PRIORITY.get(decision.outcome, 4))
        blockers = [
            {
                "package": decision.package,
                "outcome": decision.outcome,
                "reason": decision.reason,
            }
            for decision in decisions
            if ATK_PRIORITY.get(decision.outcome, 4) == ATK_PRIORITY.get(strongest.outcome, 4)
        ]
        reason = "all_policies_permit"
        if strongest.outcome != "PERMIT":
            reason = f"aggregate_{strongest.outcome.lower()}"
        return PolicyDecision(
            package="arhia.pmel.aggregate",
            outcome=strongest.outcome,
            reason=reason,
            details={"dominant_decisions": blockers, "decision_count": len(decisions)},
        )

    def _decision_dict(self, decision: PolicyDecision) -> dict[str, Any]:
        return {
            "package": decision.package,
            "outcome": decision.outcome,
            "reason": decision.reason,
            "allowed": decision.allowed,
            "details": decision.details,
        }
