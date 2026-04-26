"""DX Pro agent implementations guarded by PMEL policy checks."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from .runtime import DxProRuntime


class GovernedAgent:
    component = "generic_agent"
    subject = "dxpro-agent"
    step = "agent_pre_execution"
    prompt_name = "pmel-capture-agent-v1.0"

    def __init__(self, runtime: DxProRuntime) -> None:
        self.runtime = runtime

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        step = self._run_governance(payload)
        result = step.to_dict()
        result["agent"] = self.component
        result["artifact"] = None

        if not step.allowed:
            return result

        artifact = self._build_artifact(payload)
        evidence = self.runtime.ledger.append(
            {
                "trace_id": step.trace_id,
                "subject": step.subject,
                "event_type": "agent_artifact",
                "agent": self.component,
                "artifact_type": artifact["artifact_type"],
                "artifact_hash_sha256": self._stable_hash(artifact),
            }
        )
        result["artifact"] = artifact
        result["artifact_evidence_id"] = evidence["id"]
        return result

    def _run_governance(self, payload: dict[str, Any]):
        return self.runtime.run_step(
            {
                "subject": payload.get("subject", self.subject),
                "step": payload.get("step", self.step),
                "trace_id": payload.get("trace_id", ""),
                "input": {
                    "autonomy": payload.get(
                        "autonomy",
                        {"component": self.component, "requested_level": "A2"},
                    ),
                    "consent": payload.get(
                        "consent",
                        {"action": "ingest_to_llm", "consents": {"T1": True, "T3": True}},
                    ),
                    "aibom": payload.get(
                        "aibom",
                        {
                            "bundle_version": "2026.04-dxpro",
                            "models": ["claude-sonnet-4-7"],
                            "prompts": [self.prompt_name],
                            "owner": "Sinergia Consulting Group",
                        },
                    ),
                    "execution": payload.get(
                        "execution",
                        {
                            "component": self.component,
                            "current_cycle": 0,
                            "last_outcome": "in_progress",
                        },
                    ),
                },
            }
        )

    def _build_artifact(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def _stable_hash(self, payload: dict[str, Any]) -> str:
        raw = repr(sorted(payload.items())).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()


class PmelToBeGenerator(GovernedAgent):
    component = "to_be_generator"
    subject = "pmel-to-be-generator"
    step = "to_be_generation"
    prompt_name = "pmel-to-be-generator-v1.0"

    def _build_artifact(self, payload: dict[str, Any]) -> dict[str, Any]:
        activities = payload.get("as_is_activities") or payload.get("activities") or []
        objectives = payload.get("objectives") or ["reduce_waiting_time", "increase_traceability"]
        to_be_steps = []
        for index, activity in enumerate(activities[:10], start=1):
            label = activity.get("label", str(activity)) if isinstance(activity, dict) else str(activity)
            to_be_steps.append(
                {
                    "id": f"tobe-{index:03d}",
                    "label": self._normalize_label(label),
                    "source_activity": label[:160],
                    "control": "governed_handoff" if index > 1 else "validated_intake",
                }
            )
        if not to_be_steps:
            to_be_steps.append(
                {
                    "id": "tobe-001",
                    "label": "Validate mandate and route governed diagnostic work",
                    "source_activity": "implicit_intake",
                    "control": "validated_intake",
                }
            )
        return {
            "artifact_type": "pmel_to_be_blueprint",
            "objective_count": len(objectives),
            "objectives": objectives,
            "step_count": len(to_be_steps),
            "to_be_steps": to_be_steps,
            "risk_controls": ["consent_gate", "aibom_required", "cycle_limit", "human_publication_gate"],
        }

    def _normalize_label(self, label: str) -> str:
        cleaned = re.sub(r"\s+", " ", label).strip()
        if not cleaned:
            return "Governed process activity"
        first = cleaned[0].upper() + cleaned[1:]
        return f"Governed {first}"[:160]


class PmelBpmnLintAgent(GovernedAgent):
    component = "lint_agent"
    subject = "pmel-bpmn-lint-agent"
    step = "bpmn_lint"
    prompt_name = "pmel-bpmn-lint-agent-v1.0"

    def _build_artifact(self, payload: dict[str, Any]) -> dict[str, Any]:
        model = payload.get("bpmn_model", {})
        nodes = model.get("nodes", [])
        edges = model.get("edges", [])
        node_ids = {node.get("id") for node in nodes if isinstance(node, dict)}
        issues: list[dict[str, Any]] = []

        if not any(node.get("type") == "start_event" for node in nodes if isinstance(node, dict)):
            issues.append(self._issue("BPMN-R01", "DENY", "Missing start event."))
        if not any(node.get("type") == "end_event" for node in nodes if isinstance(node, dict)):
            issues.append(self._issue("BPMN-R02", "DENY", "Missing end event."))
        for edge in edges:
            if not isinstance(edge, dict):
                continue
            if edge.get("source") not in node_ids or edge.get("target") not in node_ids:
                issues.append(self._issue("BPMN-R03", "DENY", "Edge references an unknown node.", edge))
        connected = {edge.get("source") for edge in edges if isinstance(edge, dict)} | {edge.get("target") for edge in edges if isinstance(edge, dict)}
        for node in nodes:
            if isinstance(node, dict) and node.get("type") not in {"start_event", "end_event"} and node.get("id") not in connected:
                issues.append(self._issue("BPMN-R04", "AUDIT", "Node is orphaned.", {"node_id": node.get("id")}))

        outcome = "PERMIT"
        if any(issue["outcome"] == "DENY" for issue in issues):
            outcome = "DENY"
        elif issues:
            outcome = "AUDIT"
        return {
            "artifact_type": "pmel_bpmn_lint_report",
            "outcome": outcome,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "issue_count": len(issues),
            "issues": issues,
        }

    def _issue(self, rule_id: str, outcome: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"rule_id": rule_id, "outcome": outcome, "message": message, "details": details or {}}


class PmelVisualInterpreter(GovernedAgent):
    component = "visual_interpreter"
    subject = "pmel-visual-interpreter"
    step = "visual_interpretation"
    prompt_name = "pmel-visual-interpreter-v1.0"

    def _build_artifact(self, payload: dict[str, Any]) -> dict[str, Any]:
        observations = payload.get("observations") or payload.get("visual_notes") or []
        findings = []
        for index, observation in enumerate(observations[:8], start=1):
            text = observation.get("text", str(observation)) if isinstance(observation, dict) else str(observation)
            findings.append(
                {
                    "id": f"vis-{index:03d}",
                    "finding": text[:180],
                    "mapped_signal": self._classify_visual_signal(text),
                }
            )
        return {
            "artifact_type": "pmel_visual_interpretation",
            "finding_count": len(findings),
            "findings": findings,
            "confidence": "medium" if findings else "low",
        }

    def _classify_visual_signal(self, text: str) -> str:
        lowered = text.lower()
        if "espera" in lowered or "wait" in lowered:
            return "queue_or_delay"
        if "handoff" in lowered or "traspaso" in lowered:
            return "handoff_risk"
        if "manual" in lowered:
            return "manual_control"
        return "process_context"


class DmnEngine(GovernedAgent):
    component = "dmn_engine"
    subject = "dxpro-dmn-engine"
    step = "dmn_evaluation"
    prompt_name = "pmel-dmn-engine-v1.0"

    def _build_artifact(self, payload: dict[str, Any]) -> dict[str, Any]:
        table = payload.get("decision_table", {})
        facts = payload.get("facts", {})
        matched_rule = None
        for rule in table.get("rules", []):
            if self._matches(rule.get("when", {}), facts):
                matched_rule = rule
                break
        decision = matched_rule.get("then", {}) if matched_rule else table.get("default", {"decision": "manual_review"})
        return {
            "artifact_type": "dmn_decision_result",
            "table_id": table.get("id", "anonymous_decision_table"),
            "matched_rule_id": matched_rule.get("id") if matched_rule else None,
            "decision": decision,
            "facts_hash_sha256": hashlib.sha256(repr(sorted(facts.items())).encode("utf-8")).hexdigest(),
        }

    def _matches(self, conditions: dict[str, Any], facts: dict[str, Any]) -> bool:
        for key, expected in conditions.items():
            actual = facts.get(key)
            if isinstance(expected, dict):
                minimum = expected.get("min")
                maximum = expected.get("max")
                if minimum is not None and not (actual is not None and actual >= minimum):
                    return False
                if maximum is not None and not (actual is not None and actual <= maximum):
                    return False
                continue
            if actual != expected:
                return False
        return True


class CryptoParticipant(GovernedAgent):
    component = "crypto_participant"
    subject = "dxpro-crypto-participant"
    step = "crypto_decommissioning"
    prompt_name = "pmel-crypto-participant-v1.0"

    def _build_artifact(self, payload: dict[str, Any]) -> dict[str, Any]:
        targets = payload.get("targets", [])
        action = payload.get("action", "crypto_shred")
        target_records = []
        for index, target in enumerate(targets[:20], start=1):
            raw = repr(target).encode("utf-8")
            target_records.append(
                {
                    "id": f"target-{index:03d}",
                    "target_hash_sha256": hashlib.sha256(raw).hexdigest(),
                    "status": "scheduled",
                }
            )
        return {
            "artifact_type": "crypto_decommissioning_plan",
            "action": action,
            "target_count": len(target_records),
            "targets": target_records,
            "requires_operator_confirmation": True,
            "execution_mode": "plan_only",
        }
