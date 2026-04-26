"""DX Pro agent implementations guarded by PMEL policy checks."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from pathlib import Path

from .bpmn import parse_model, run_lint
from .llm_client import MODEL_OPUS, MODEL_SONNET, LlmClient
from .prompts import SYSTEM_BPMN_LINT, SYSTEM_TO_BE_GENERATOR, SYSTEM_VISUAL_INTERPRETER
from .research import HypothesisBuilder, LensClient, OpenAlexClient
from .runtime import DxProRuntime


class GovernedAgent:
    component = "generic_agent"
    subject = "dxpro-agent"
    step = "agent_pre_execution"
    prompt_name = "pmel-capture-agent-v1.0"

    def __init__(self, runtime: DxProRuntime, llm_client: LlmClient | None = None) -> None:
        self.runtime = runtime
        self.llm_client = llm_client

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
                            "models": ["claude-sonnet-4-6"],
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


# ---------------------------------------------------------------------------
# TO-BE Generator — Claude Opus 4.7
# ---------------------------------------------------------------------------

class PmelToBeGenerator(GovernedAgent):
    component = "to_be_generator"
    subject = "pmel-to-be-generator"
    step = "to_be_generation"
    prompt_name = "pmel-to-be-generator-v1.0"

    def _build_artifact(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self.llm_client is not None:
            return self._build_with_llm(payload)
        return self._build_stub(payload)

    def _build_with_llm(self, payload: dict[str, Any]) -> dict[str, Any]:
        user_prompt = json.dumps(
            {
                "engagement_id": payload.get("engagement_id", "unknown"),
                "cycle_number": payload.get("cycle_number", 1),
                "scope_mode": payload.get("scope_mode", "standard"),
                "as_is_bpmn_xml": payload.get("as_is_bpmn", ""),
                "as_is_process_summary_prose": payload.get("as_is_prose", {}),
                "hypothesis_pack": payload.get("hypothesis_pack", {}),
                "previous_lint_report": payload.get("lint_report"),
            },
            ensure_ascii=False,
            indent=2,
        )
        result = self.llm_client.complete(
            model=MODEL_OPUS,
            system=SYSTEM_TO_BE_GENERATOR,
            user=user_prompt,
        )
        result["artifact_type"] = "pmel_to_be_blueprint"
        result["llm_mode"] = "claude"
        result["llm_model"] = MODEL_OPUS
        return result

    def _build_stub(self, payload: dict[str, Any]) -> dict[str, Any]:
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
            "llm_mode": "stub",
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


# ---------------------------------------------------------------------------
# BPMN Lint Agent — Claude Sonnet 4.7
# Deterministic analysis runs in Python; Claude only writes the messages.
# ---------------------------------------------------------------------------

class PmelBpmnLintAgent(GovernedAgent):
    component = "lint_agent"
    subject = "pmel-bpmn-lint-agent"
    step = "bpmn_lint"
    prompt_name = "pmel-bpmn-lint-agent-v1.0"

    def __init__(
        self,
        runtime: DxProRuntime,
        llm_client: LlmClient | None = None,
        verb_lexicon_path: Path | None = None,
    ) -> None:
        super().__init__(runtime, llm_client)
        self.verb_lexicon_path = verb_lexicon_path

    def _build_artifact(self, payload: dict[str, Any]) -> dict[str, Any]:
        structural_report = self._run_deterministic_analysis(payload)
        if self.llm_client is not None and structural_report["issue_count"] > 0:
            return self._enrich_with_llm(structural_report)
        return structural_report

    def _run_deterministic_analysis(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Catalog R01..R12 deterministic analysis."""
        raw_model = payload.get("bpmn_model", {}) or {}
        model = parse_model(raw_model)
        report = run_lint(model, verb_lexicon_path=self.verb_lexicon_path)

        return {
            "artifact_type": "pmel_bpmn_lint_report",
            "llm_mode": "stub",
            "catalog_version": "1.0",
            "rules_checked": [
                "R01", "R02", "R03", "R04", "R05", "R06",
                "R07", "R08", "R09", "R10", "R11", "R12",
            ],
            "outcome": report.outcome,
            "node_count": report.node_count,
            "edge_count": report.edge_count,
            "issue_count": report.issue_count,
            "critical_count": report.critical_count,
            "issues": [i.to_dict() for i in report.issues],
        }

    def _enrich_with_llm(self, structural_report: dict[str, Any]) -> dict[str, Any]:
        """Ask Claude to write human-readable messages for each violation."""
        user_prompt = json.dumps(
            {
                "bpmn_lint_report": structural_report,
                "instruction": (
                    "Redacta mensajes claros y accionables para cada issue en el reporte. "
                    "El análisis determinístico ya está hecho — solo escribe los mensajes."
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
        narrative = self.llm_client.complete(
            model=MODEL_SONNET,
            system=SYSTEM_BPMN_LINT,
            user=user_prompt,
        )
        structural_report["lint_narrative"] = narrative
        structural_report["llm_mode"] = "claude"
        structural_report["llm_model"] = MODEL_SONNET
        return structural_report


# ---------------------------------------------------------------------------
# Visual Interpreter — Claude Opus 4.7 (multimodal)
# ---------------------------------------------------------------------------

class PmelVisualInterpreter(GovernedAgent):
    component = "visual_interpreter"
    subject = "pmel-visual-interpreter"
    step = "visual_interpretation"
    prompt_name = "pmel-visual-interpreter-v1.0"

    def _build_artifact(self, payload: dict[str, Any]) -> dict[str, Any]:
        images: list[dict[str, str]] = payload.get("images", [])
        if self.llm_client is not None and images:
            return self._build_with_llm(payload, images)
        return self._build_stub(payload)

    def _build_with_llm(self, payload: dict[str, Any], images: list[dict[str, str]]) -> dict[str, Any]:
        text_prompt = json.dumps(
            {
                "engagement_id": payload.get("engagement_id", "unknown"),
                "consultant_notes": payload.get("consultant_notes", ""),
                "instruction": "Interpreta las imágenes adjuntas y produce el artefacto PMEL solicitado.",
            },
            ensure_ascii=False,
        )
        result = self.llm_client.complete_with_vision(
            model=MODEL_OPUS,
            system=SYSTEM_VISUAL_INTERPRETER,
            text_prompt=text_prompt,
            images=images,
        )
        result["artifact_type"] = "pmel_visual_interpretation"
        result["llm_mode"] = "claude"
        result["llm_model"] = MODEL_OPUS
        result["image_count"] = len(images)
        return result

    def _build_stub(self, payload: dict[str, Any]) -> dict[str, Any]:
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
            "llm_mode": "stub",
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


# ---------------------------------------------------------------------------
# DMN Engine — deterministic Python rule evaluator (no LLM needed)
# ---------------------------------------------------------------------------

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
        decision = (
            matched_rule.get("then", {})
            if matched_rule
            else table.get("default", {"decision": "manual_review"})
        )
        return {
            "artifact_type": "dmn_decision_result",
            "table_id": table.get("id", "anonymous_decision_table"),
            "matched_rule_id": matched_rule.get("id") if matched_rule else None,
            "decision": decision,
            "facts_hash_sha256": hashlib.sha256(
                repr(sorted(facts.items())).encode("utf-8")
            ).hexdigest(),
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


# ---------------------------------------------------------------------------
# Crypto Participant — governance planning only, no LLM needed
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# RGC — Hypothesis Builder agent
# Connects external research sources (OpenAlex + Lens.org) and synthesizes
# a grounded hypothesis_pack for the TO-BE Generator.
# ---------------------------------------------------------------------------

class RgcAgent(GovernedAgent):
    component = "rgc_hypothesis_builder"
    subject = "pmel-rgc-agent"
    step = "rgc_hypothesis_build"
    prompt_name = "pmel-rgc-hypothesis-builder-v1.0"

    def __init__(
        self,
        runtime: DxProRuntime,
        llm_client: LlmClient | None = None,
        openalex: OpenAlexClient | None = None,
        lens: LensClient | None = None,
    ) -> None:
        super().__init__(runtime, llm_client)
        self._openalex = openalex
        self._lens = lens

    def _build_artifact(self, payload: dict[str, Any]) -> dict[str, Any]:
        engagement_id = str(payload.get("engagement_id", "unknown"))
        domain = str(payload.get("domain", ""))
        pain_points = list(payload.get("pain_points") or [])

        if not pain_points:
            return {
                "artifact_type": "pmel_hypothesis_pack",
                "hypothesis_pack_version": "1.0",
                "engagement_id": engagement_id,
                "domain": domain,
                "hypotheses": [],
                "error": "no_pain_points_provided",
            }

        builder = HypothesisBuilder(
            llm_client=self.llm_client,
            openalex=self._openalex or OpenAlexClient(),
            lens=self._lens or LensClient(),
        )
        try:
            pack = builder.build(
                engagement_id=engagement_id,
                domain=domain,
                pain_points=pain_points,
            )
        finally:
            if self._openalex is None and builder.openalex is not None:
                builder.openalex.close()
            if self._lens is None and builder.lens is not None:
                builder.lens.close()

        pack["artifact_type"] = "pmel_hypothesis_pack"
        return pack
