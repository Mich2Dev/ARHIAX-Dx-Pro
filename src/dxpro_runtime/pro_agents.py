"""DX Pro agent implementations guarded by PMEL policy checks."""

from __future__ import annotations

import hashlib
import json
import re
import statistics
from typing import Any

from pathlib import Path

from .bpmn import parse_model, run_lint
from .llm_client import MODEL_OPUS, MODEL_SONNET, LlmClient
from .prompts import SYSTEM_BPMN_LINT, SYSTEM_TO_BE_GENERATOR, SYSTEM_VISUAL_INTERPRETER
from .research import DeepResearchContraster, GreySourceClient, HypothesisBuilder, LensClient, OpenAlexClient
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

        artifact_payload = {**payload, "trace_id": step.trace_id}
        artifact = self._build_artifact(artifact_payload)
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
                        {"action": "ingest_to_llm", "consents": {}},
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


class RgcDeepResearchContrasterAgent(GovernedAgent):
    component = "rgc_deep_research_contraster"
    subject = "pmel-rgc-deep-research-contraster"
    step = "rgc_deep_research_contrast"
    prompt_name = "pmel-rgc-deep-research-contraster-v1.0"

    def __init__(
        self,
        runtime: DxProRuntime,
        llm_client: LlmClient | None = None,
        grey_client: GreySourceClient | None = None,
    ) -> None:
        super().__init__(runtime, llm_client)
        self._grey_client = grey_client

    def _build_artifact(self, payload: dict[str, Any]) -> dict[str, Any]:
        engagement_id = str(payload.get("engagement_id", "unknown"))
        domain = str(payload.get("domain", ""))
        pain_points = list(payload.get("pain_points") or [])
        hypothesis_pack = dict(payload.get("hypothesis_pack") or {})

        if not hypothesis_pack.get("hypotheses"):
            return {
                "artifact_type": "deep_research_contrast_pack",
                "contrast_pack_version": "1.0",
                "engagement_id": engagement_id,
                "domain": domain,
                "contrast_matrix": [],
                "error": "no_hypothesis_pack_provided",
            }

        builder = DeepResearchContraster(
            llm_client=self.llm_client,
            grey_client=self._grey_client,
        )
        pack = builder.build(
            engagement_id=engagement_id,
            domain=domain,
            pain_points=pain_points,
            hypothesis_pack=hypothesis_pack,
            provided_sources=list(payload.get("grey_sources") or payload.get("provided_sources") or []),
            urls=list(payload.get("urls") or []),
        )
        pack["artifact_type"] = "deep_research_contrast_pack"
        return pack


class AdaptiveQuestionBankAgent(GovernedAgent):
    component = "adaptive_question_bank"
    subject = "dxpro-adaptive-question-bank"
    step = "adaptive_question_bank"
    prompt_name = "pmel-adaptive-question-bank-v1.0"

    def _build_artifact(self, payload: dict[str, Any]) -> dict[str, Any]:
        engagement_id = str(payload.get("engagement_id", "unknown"))
        roles = _as_list(payload.get("roles")) or ["executive", "operations", "technology"]
        dimensions = _as_list(payload.get("dimensions")) or [
            "strategy",
            "process",
            "technology",
            "governance",
            "innovation",
        ]
        pain_points = _as_list(payload.get("pain_points"))
        questions: list[dict[str, Any]] = []
        for role in roles:
            for dimension in dimensions:
                qid = f"q-{len(questions) + 1:03d}"
                questions.append(
                    {
                        "id": qid,
                        "role": str(role),
                        "dimension": str(dimension),
                        "question": _question_for(str(role), str(dimension), pain_points),
                        "response_type": "likert_1_5",
                        "evidence_use": "multi_role_scoring",
                    }
                )
        branching_rules = [
            {
                "id": "branch-low-score",
                "when": {"response_lte": 2},
                "ask_followup": "Describe the blocker, owner, frequency and evidence available.",
            },
            {
                "id": "branch-high-variance",
                "when": {"role_variance_gte": 1.5},
                "ask_followup": "Explain why this dimension is perceived differently across roles.",
            },
        ]
        return {
            "artifact_type": "question_bank_pack",
            "question_bank_version": "1.0",
            "engagement_id": engagement_id,
            "role_count": len(roles),
            "dimension_count": len(dimensions),
            "question_count": len(questions),
            "questions": questions,
            "branching_rules": branching_rules,
            "validation_rules": [
                "minimum_one_response_per_role",
                "minimum_one_score_per_dimension",
                "followup_required_for_low_scores",
            ],
            "source_modules": ["g09a_preguntas", "g09b_ramificacion", "g09c_validacion"],
        }


class MultiRoleScoringAgent(GovernedAgent):
    component = "multi_role_scoring"
    subject = "dxpro-multi-role-scoring"
    step = "multi_role_scoring"
    prompt_name = "pmel-multi-role-scoring-v1.0"

    def _build_artifact(self, payload: dict[str, Any]) -> dict[str, Any]:
        responses = _numeric_responses(payload)
        by_role = _group_average(responses, "role")
        by_dimension = _group_average(responses, "dimension")
        by_role_dimension = _group_average(responses, "role_dimension")
        gaps = _dimension_gaps(responses)
        overall = _mean([r["score"] for r in responses])
        maturity = _maturity_level(overall)
        return {
            "artifact_type": "multi_role_scoring_pack",
            "scoring_pack_version": "1.0",
            "response_count": len(responses),
            "overall_score": round(overall, 3) if responses else None,
            "maturity_level": maturity,
            "scores_by_role": by_role,
            "scores_by_dimension": by_dimension,
            "scores_by_role_dimension": by_role_dimension,
            "largest_role_gaps": gaps[:5],
            "source_modules": ["g10a_scoring", "scoring_engine"],
        }


class PsychometricsAgent(GovernedAgent):
    component = "psychometrics"
    subject = "dxpro-psychometrics"
    step = "psychometric_evaluation"
    prompt_name = "pmel-psychometrics-v1.0"

    def _build_artifact(self, payload: dict[str, Any]) -> dict[str, Any]:
        matrix = _response_matrix(payload)
        alpha = _cronbach_alpha(matrix)
        item_count = len(matrix[0]) if matrix else 0
        respondent_count = len(matrix)
        completeness = _completion_ratio(matrix)
        flags = []
        if alpha is not None and alpha < 0.7:
            flags.append("low_internal_consistency")
        if completeness < 0.8:
            flags.append("low_completion")
        return {
            "artifact_type": "psychometric_quality_pack",
            "psychometric_pack_version": "1.0",
            "respondent_count": respondent_count,
            "item_count": item_count,
            "cronbach_alpha": round(alpha, 3) if alpha is not None else None,
            "completion_ratio": round(completeness, 3),
            "quality_status": "review" if flags else "acceptable",
            "flags": flags,
            "source_modules": ["g10b_psicometria"],
        }


class IrrReliabilityAgent(GovernedAgent):
    component = "irr_reliability"
    subject = "dxpro-irr-reliability"
    step = "irr_reliability"
    prompt_name = "pmel-irr-reliability-v1.0"

    def _build_artifact(self, payload: dict[str, Any]) -> dict[str, Any]:
        ratings = _numeric_responses(payload, default_role="rater")
        scale_min = float(payload.get("scale_min", 1))
        scale_max = float(payload.get("scale_max", 5))
        grouped: dict[str, list[float]] = {}
        for rating in ratings:
            grouped.setdefault(str(rating.get("item_id") or rating["dimension"]), []).append(rating["score"])
        item_stats = []
        stds = []
        for item_id, values in grouped.items():
            std = statistics.pstdev(values) if len(values) > 1 else 0.0
            stds.append(std)
            item_stats.append(
                {
                    "item_id": item_id,
                    "rater_count": len(values),
                    "mean_score": round(_mean(values), 3),
                    "std_dev": round(std, 3),
                }
            )
        scale_range = max(scale_max - scale_min, 1.0)
        agreement = max(0.0, 1.0 - (_mean(stds) / scale_range)) if stds else 0.0
        status = "acceptable" if agreement >= 0.75 else "review"
        return {
            "artifact_type": "irr_reliability_pack",
            "irr_pack_version": "1.0",
            "rating_count": len(ratings),
            "item_count": len(item_stats),
            "agreement_index": round(agreement, 3),
            "reliability_status": status,
            "item_stats": item_stats,
            "recommended_action": "proceed" if status == "acceptable" else "recapture_or_hil_review",
            "source_modules": ["irr_calculator"],
        }


class BayesianSynthesisAgent(GovernedAgent):
    component = "bayesian_synthesis"
    subject = "dxpro-bayesian-synthesis"
    step = "bayesian_synthesis"
    prompt_name = "pmel-bayesian-synthesis-v1.0"

    def _build_artifact(self, payload: dict[str, Any]) -> dict[str, Any]:
        hypotheses = list(payload.get("hypotheses") or [])
        evidence_signals = list(payload.get("evidence_signals") or [])
        if not hypotheses:
            hypotheses = _hypotheses_from_scoring(payload.get("scoring_pack") or {})
        synthesized = []
        for index, hypothesis in enumerate(hypotheses, start=1):
            hid = str(hypothesis.get("id") or f"DH{index}")
            prior = _clamp_probability(float(hypothesis.get("prior", 0.5)))
            posterior = prior
            used_signals = []
            for signal in evidence_signals:
                if hid not in _as_list(signal.get("hypothesis_ids")):
                    continue
                likelihood = float(signal.get("likelihood_ratio", 1.0))
                posterior = _bayes_update(posterior, likelihood)
                used_signals.append(signal.get("id", f"signal-{len(used_signals) + 1}"))
            synthesized.append(
                {
                    "id": hid,
                    "statement": hypothesis.get("statement", "Diagnostic hypothesis"),
                    "prior": round(prior, 3),
                    "posterior": round(posterior, 3),
                    "confidence": _posterior_confidence(posterior),
                    "evidence_signal_ids": used_signals,
                }
            )
        synthesized.sort(key=lambda row: row["posterior"], reverse=True)
        return {
            "artifact_type": "bayesian_synthesis_pack",
            "bayesian_pack_version": "1.0",
            "hypothesis_count": len(synthesized),
            "prioritized_hypotheses": synthesized,
            "top_hypothesis_id": synthesized[0]["id"] if synthesized else None,
            "source_modules": ["g11a_bayesiano"],
        }


class ExecutiveQaAgent(GovernedAgent):
    component = "executive_qa"
    subject = "dxpro-executive-qa"
    step = "executive_qa"
    prompt_name = "pmel-executive-qa-v1.0"

    def _build_artifact(self, payload: dict[str, Any]) -> dict[str, Any]:
        required = [
            "scoring_pack",
            "psychometric_pack",
            "irr_pack",
            "bayesian_pack",
            "hypothesis_pack",
            "contrast_pack",
            "to_be_pack",
        ]
        missing = [key for key in required if not payload.get(key)]
        risks = []
        irr = (payload.get("irr_pack") or {}).get("agreement_index")
        alpha = (payload.get("psychometric_pack") or {}).get("cronbach_alpha")
        if irr is not None and irr < 0.75:
            risks.append("low_irr")
        if alpha is not None and alpha < 0.7:
            risks.append("low_psychometric_consistency")
        if (payload.get("contrast_pack") or {}).get("recommended_hil_questions"):
            risks.append("open_hil_questions")
        readiness = "approved" if not missing and not risks else "requires_review"
        return {
            "artifact_type": "executive_qa_pack",
            "qa_pack_version": "1.0",
            "readiness": readiness,
            "missing_artifacts": missing,
            "risk_flags": risks,
            "publication_gate": "permit_draft" if readiness == "approved" else "block_final_publication",
            "source_modules": ["g14_qa_control"],
        }


class DiagnosticIntelligenceAgent(GovernedAgent):
    component = "diagnostic_intelligence"
    subject = "dxpro-diagnostic-intelligence"
    step = "diagnostic_intelligence_pack"
    prompt_name = "pmel-diagnostic-intelligence-v1.0"

    def _build_artifact(self, payload: dict[str, Any]) -> dict[str, Any]:
        bayesian = payload.get("bayesian_pack") or {}
        scoring = payload.get("scoring_pack") or {}
        contrast = payload.get("contrast_pack") or {}
        qa = payload.get("qa_pack") or {}
        top = list(bayesian.get("prioritized_hypotheses") or [])[:3]
        return {
            "artifact_type": "diagnostic_intelligence_pack",
            "diagnostic_intelligence_version": "1.0",
            "overall_score": scoring.get("overall_score"),
            "maturity_level": scoring.get("maturity_level"),
            "top_diagnostic_hypotheses": top,
            "contrast_rows": len(contrast.get("contrast_matrix") or []),
            "qa_readiness": qa.get("readiness", "not_evaluated"),
            "recommended_next_step": _next_step(scoring, bayesian, contrast, qa),
            "inputs_present": {
                key: bool(payload.get(key))
                for key in (
                    "question_bank",
                    "scoring_pack",
                    "psychometric_pack",
                    "irr_pack",
                    "bayesian_pack",
                    "hypothesis_pack",
                    "contrast_pack",
                    "qa_pack",
                )
            },
        }


class DiagnosticFusionCycleAgent(GovernedAgent):
    component = "diagnostic_fusion_cycle"
    subject = "dxpro-diagnostic-fusion-cycle"
    step = "diagnostic_fusion_cycle"
    prompt_name = "pmel-diagnostic-fusion-cycle-v1.0"

    def _build_artifact(self, payload: dict[str, Any]) -> dict[str, Any]:
        consent = payload.get("consent", {"action": "ingest_to_llm", "consents": {}})
        trace_id = str(payload.get("trace_id", ""))
        child_base = {
            "trace_id": trace_id,
            "consent": consent,
            "engagement_id": payload.get("engagement_id", "unknown"),
            "domain": payload.get("domain", ""),
        }

        children: dict[str, GovernedAgent] = {
            "question_bank": AdaptiveQuestionBankAgent(self.runtime, self.llm_client),
            "scoring": MultiRoleScoringAgent(self.runtime, self.llm_client),
            "psychometrics": PsychometricsAgent(self.runtime, self.llm_client),
            "irr": IrrReliabilityAgent(self.runtime, self.llm_client),
            "bayesian": BayesianSynthesisAgent(self.runtime, self.llm_client),
            "rgc": RgcAgent(self.runtime, self.llm_client),
            "deep_contrast": RgcDeepResearchContrasterAgent(self.runtime, self.llm_client),
            "to_be": PmelToBeGenerator(self.runtime, self.llm_client),
            "bpmn_lint": PmelBpmnLintAgent(self.runtime, self.llm_client),
            "executive_qa": ExecutiveQaAgent(self.runtime, self.llm_client),
            "intelligence": DiagnosticIntelligenceAgent(self.runtime, self.llm_client),
        }

        question_bank = children["question_bank"].execute(
            {
                **child_base,
                "roles": payload.get("roles"),
                "dimensions": payload.get("dimensions"),
                "pain_points": payload.get("pain_points", []),
            }
        )
        scoring = children["scoring"].execute(
            {**child_base, "responses": payload.get("responses", [])}
        )
        psychometrics = children["psychometrics"].execute(
            {
                **child_base,
                "responses": payload.get("responses", []),
                "response_matrix": payload.get("response_matrix"),
            }
        )
        irr = children["irr"].execute(
            {**child_base, "ratings": payload.get("ratings") or payload.get("responses", [])}
        )

        scoring_pack = _artifact(scoring)
        psychometric_pack = _artifact(psychometrics)
        irr_pack = _artifact(irr)
        bayesian = children["bayesian"].execute(
            {
                **child_base,
                "hypotheses": payload.get("diagnostic_hypotheses", []),
                "evidence_signals": payload.get("evidence_signals", []),
                "scoring_pack": scoring_pack,
            }
        )
        bayesian_pack = _artifact(bayesian)

        rgc = children["rgc"].execute(
            {
                **child_base,
                "pain_points": payload.get("pain_points", []),
                "openalex": payload.get("openalex"),
                "lens": payload.get("lens"),
            }
        )
        hypothesis_pack = dict(payload.get("hypothesis_pack") or _artifact(rgc) or {})
        deep_contrast = children["deep_contrast"].execute(
            {
                **child_base,
                "pain_points": payload.get("pain_points", []),
                "hypothesis_pack": hypothesis_pack,
                "grey_sources": payload.get("grey_sources", []),
                "urls": payload.get("urls", []),
            }
        )
        contrast_pack = _artifact(deep_contrast)

        to_be = children["to_be"].execute(
            {
                **child_base,
                "as_is_activities": payload.get("as_is_activities") or _activities_from_responses(payload),
                "as_is_bpmn": payload.get("as_is_bpmn", ""),
                "as_is_prose": payload.get("as_is_prose", {}),
                "hypothesis_pack": hypothesis_pack,
                "lint_report": payload.get("lint_report"),
            }
        )
        to_be_pack = _artifact(to_be)

        bpmn_lint = children["bpmn_lint"].execute(
            {
                **child_base,
                "bpmn_model": payload.get("bpmn_model", {}),
            }
        )
        qa = children["executive_qa"].execute(
            {
                **child_base,
                "scoring_pack": scoring_pack,
                "psychometric_pack": psychometric_pack,
                "irr_pack": irr_pack,
                "bayesian_pack": bayesian_pack,
                "hypothesis_pack": hypothesis_pack,
                "contrast_pack": contrast_pack,
                "to_be_pack": to_be_pack,
            }
        )
        qa_pack = _artifact(qa)
        intelligence = children["intelligence"].execute(
            {
                **child_base,
                "question_bank": _artifact(question_bank),
                "scoring_pack": scoring_pack,
                "psychometric_pack": psychometric_pack,
                "irr_pack": irr_pack,
                "bayesian_pack": bayesian_pack,
                "hypothesis_pack": hypothesis_pack,
                "contrast_pack": contrast_pack,
                "qa_pack": qa_pack,
            }
        )

        stages = {
            "question_bank": _stage_summary(question_bank),
            "scoring": _stage_summary(scoring),
            "psychometrics": _stage_summary(psychometrics),
            "irr": _stage_summary(irr),
            "bayesian": _stage_summary(bayesian),
            "rgc": _stage_summary(rgc),
            "deep_contrast": _stage_summary(deep_contrast),
            "to_be": _stage_summary(to_be),
            "bpmn_lint": _stage_summary(bpmn_lint),
            "executive_qa": _stage_summary(qa),
            "diagnostic_intelligence": _stage_summary(intelligence),
        }
        blocked = [name for name, stage in stages.items() if stage["outcome"] != "PERMIT"]
        return {
            "artifact_type": "diagnostic_fusion_cycle_pack",
            "fusion_cycle_version": "1.0",
            "engagement_id": payload.get("engagement_id", "unknown"),
            "domain": payload.get("domain", ""),
            "stage_count": len(stages),
            "blocked_stages": blocked,
            "cycle_status": "completed" if not blocked else "completed_with_blocked_stages",
            "stages": stages,
            "artifacts": {
                "question_bank": _artifact(question_bank),
                "scoring_pack": scoring_pack,
                "psychometric_pack": psychometric_pack,
                "irr_pack": irr_pack,
                "bayesian_pack": bayesian_pack,
                "hypothesis_pack": hypothesis_pack,
                "contrast_pack": contrast_pack,
                "to_be_pack": to_be_pack,
                "bpmn_lint_pack": _artifact(bpmn_lint),
                "executive_qa_pack": qa_pack,
                "diagnostic_intelligence_pack": _artifact(intelligence),
            },
        }


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _artifact(result: dict[str, Any]) -> dict[str, Any] | None:
    artifact = result.get("artifact")
    return artifact if isinstance(artifact, dict) else None


def _stage_summary(result: dict[str, Any]) -> dict[str, Any]:
    artifact = _artifact(result)
    return {
        "agent": result.get("agent"),
        "outcome": result.get("outcome"),
        "reason": result.get("reason"),
        "artifact_type": artifact.get("artifact_type") if artifact else None,
        "artifact_evidence_id": result.get("artifact_evidence_id"),
    }


def _activities_from_responses(payload: dict[str, Any]) -> list[dict[str, str]]:
    activities = []
    for index, response in enumerate(payload.get("responses") or [], start=1):
        dimension = response.get("dimension") or "diagnostic dimension"
        role = response.get("role") or "role"
        activities.append(
            {
                "id": f"asis-{index:03d}",
                "label": f"Assess {dimension} with {role}",
            }
        )
    return activities


def _question_for(role: str, dimension: str, pain_points: list[Any]) -> str:
    pain = str(pain_points[0]) if pain_points else "the current operating model"
    return (
        f"For {role}, rate the maturity of {dimension} in relation to {pain} "
        "and describe the strongest evidence for your rating."
    )


def _numeric_responses(payload: dict[str, Any], default_role: str = "role") -> list[dict[str, Any]]:
    out = []
    for index, item in enumerate(payload.get("responses") or payload.get("ratings") or [], start=1):
        score = item.get("score", item.get("value"))
        try:
            numeric = float(score)
        except (TypeError, ValueError):
            continue
        out.append(
            {
                "id": item.get("id", f"resp-{index:03d}"),
                "role": str(item.get("role") or item.get("rater") or default_role),
                "dimension": str(item.get("dimension") or item.get("item_id") or "overall"),
                "item_id": item.get("item_id"),
                "score": numeric,
            }
        )
    return out


def _group_average(responses: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    grouped: dict[str, list[float]] = {}
    for row in responses:
        if key == "role_dimension":
            group_key = f"{row['role']}::{row['dimension']}"
        else:
            group_key = str(row[key])
        grouped.setdefault(group_key, []).append(row["score"])
    return [
        {"group": group, "average": round(_mean(values), 3), "count": len(values)}
        for group, values in sorted(grouped.items())
    ]


def _dimension_gaps(responses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, list[float]]] = {}
    for row in responses:
        grouped.setdefault(row["dimension"], {}).setdefault(row["role"], []).append(row["score"])
    gaps = []
    for dimension, roles in grouped.items():
        role_scores = {role: _mean(values) for role, values in roles.items()}
        if len(role_scores) < 2:
            continue
        high_role = max(role_scores, key=role_scores.get)
        low_role = min(role_scores, key=role_scores.get)
        gaps.append(
            {
                "dimension": dimension,
                "gap": round(role_scores[high_role] - role_scores[low_role], 3),
                "highest_role": high_role,
                "lowest_role": low_role,
            }
        )
    return sorted(gaps, key=lambda row: row["gap"], reverse=True)


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _maturity_level(score: float) -> str:
    if score >= 4.2:
        return "advanced"
    if score >= 3.4:
        return "managed"
    if score >= 2.6:
        return "emerging"
    if score > 0:
        return "initial"
    return "insufficient_data"


def _response_matrix(payload: dict[str, Any]) -> list[list[float | None]]:
    matrix = payload.get("response_matrix")
    if isinstance(matrix, list):
        return [
            [float(value) if value is not None else None for value in row]
            for row in matrix
            if isinstance(row, list)
        ]
    responses = _numeric_responses(payload)
    respondents = sorted({str(r["role"]) for r in responses})
    items = sorted({str(r.get("item_id") or r["dimension"]) for r in responses})
    lookup = {(str(r["role"]), str(r.get("item_id") or r["dimension"])): r["score"] for r in responses}
    return [[lookup.get((respondent, item)) for item in items] for respondent in respondents]


def _cronbach_alpha(matrix: list[list[float | None]]) -> float | None:
    complete = [[value for value in row if value is not None] for row in matrix]
    complete = [row for row in complete if len(row) >= 2]
    if len(complete) < 2:
        return None
    item_count = min(len(row) for row in complete)
    trimmed = [row[:item_count] for row in complete]
    if item_count < 2:
        return None
    columns = [[row[i] for row in trimmed] for i in range(item_count)]
    item_variance = sum(statistics.pvariance(column) for column in columns)
    totals = [sum(row) for row in trimmed]
    total_variance = statistics.pvariance(totals)
    if total_variance == 0:
        return None
    return (item_count / (item_count - 1)) * (1 - item_variance / total_variance)


def _completion_ratio(matrix: list[list[float | None]]) -> float:
    cells = [value for row in matrix for value in row]
    if not cells:
        return 0.0
    return len([value for value in cells if value is not None]) / len(cells)


def _clamp_probability(value: float) -> float:
    return min(max(value, 0.01), 0.99)


def _bayes_update(prior: float, likelihood_ratio: float) -> float:
    odds = prior / (1 - prior)
    posterior_odds = odds * max(likelihood_ratio, 0.01)
    return posterior_odds / (1 + posterior_odds)


def _posterior_confidence(posterior: float) -> str:
    if posterior >= 0.75:
        return "high"
    if posterior >= 0.55:
        return "medium"
    return "low"


def _hypotheses_from_scoring(scoring_pack: dict[str, Any]) -> list[dict[str, Any]]:
    hypotheses = []
    for index, gap in enumerate(scoring_pack.get("largest_role_gaps") or [], start=1):
        hypotheses.append(
            {
                "id": f"DH{index}",
                "statement": f"Role perception gap in {gap.get('dimension')} is a diagnostic bottleneck.",
                "prior": 0.6 if gap.get("gap", 0) >= 1 else 0.5,
            }
        )
    return hypotheses


def _next_step(
    scoring: dict[str, Any],
    bayesian: dict[str, Any],
    contrast: dict[str, Any],
    qa: dict[str, Any],
) -> str:
    if qa.get("readiness") == "requires_review":
        return "resolve_qa_findings"
    if contrast.get("recommended_hil_questions"):
        return "run_hil_contrast_review"
    if bayesian.get("top_hypothesis_id"):
        return "generate_to_be_blueprint"
    if scoring.get("overall_score") is None:
        return "capture_more_responses"
    return "proceed_to_consultant_review"
