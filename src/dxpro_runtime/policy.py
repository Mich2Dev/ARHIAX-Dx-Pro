"""Policy evaluation layer for ARHIAX DX Pro.

OPA is the primary policy path. The native evaluator is a development and
degraded-mode fallback that covers every package declared in the PMEL bundle.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .models import EvaluationRequest, PolicyDecision


class PolicyEngine:
    def __init__(self, bundle_path: Path, opa_url: str | None = None, opa_path: str | None = None) -> None:
        self.bundle_path = bundle_path
        self.opa_url = opa_url.rstrip("/") if opa_url else None
        self.opa_path = opa_path or shutil.which("opa")
        self.manifest = self._load_manifest()
        self.mode = self._select_mode()

    def evaluate(self, request: EvaluationRequest) -> PolicyDecision:
        normalized = EvaluationRequest(
            package=request.package,
            input=self._normalize_input(request.package, request.input, request.trace_id),
            subject=request.subject,
            trace_id=request.trace_id,
        )
        if self.mode == "opa-http":
            return self._evaluate_with_opa_http(normalized)
        if self.mode == "opa-cli":
            return self._evaluate_with_opa_cli(normalized)
        return self._evaluate_native(normalized)

    def package_names(self) -> list[str]:
        return list(self.manifest.get("packages", []))

    def _select_mode(self) -> str:
        if self.opa_url:
            return "opa-http"
        if self.opa_path and self.bundle_path.exists():
            return "opa-cli"
        return "native-fallback"

    def _load_manifest(self) -> dict[str, Any]:
        manifest_path = self.bundle_path / "manifest.json"
        if not manifest_path.exists():
            return {"bundle_name": "unknown", "packages": []}
        return json.loads(manifest_path.read_text(encoding="utf-8"))

    def _evaluate_with_opa_http(self, request: EvaluationRequest) -> PolicyDecision:
        path = request.package.replace(".", "/")
        payload = json.dumps({"input": request.input}).encode("utf-8")
        req = urllib.request.Request(
            f"{self.opa_url}/v1/data/{path}/decision",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode("utf-8"))
            return self._decision_from_opa_result(request.package, data.get("result", {}), "opa-http")
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            fallback = self._evaluate_native(request)
            return PolicyDecision(
                package=request.package,
                outcome=fallback.outcome,
                reason=fallback.reason,
                details={**fallback.details, "opa_mode": "opa-http", "opa_error": str(exc), "fallback": True},
            )

    def _evaluate_with_opa_cli(self, request: EvaluationRequest) -> PolicyDecision:
        expression = f"data.{request.package}.decision"
        command = [str(self.opa_path), "eval", "--stdin-input", "--format", "json"]
        for path in self._opa_data_paths():
            command.extend(["--data", str(path)])
        command.append(expression)
        completed = subprocess.run(
            command,
            input=json.dumps(request.input),
            capture_output=True,
            text=True,
            timeout=10,
            cwd=self.bundle_path.parent,
        )
        if completed.returncode != 0:
            fallback = self._evaluate_native(request)
            return PolicyDecision(
                package=request.package,
                outcome=fallback.outcome,
                reason=fallback.reason,
                details={**fallback.details, "opa_mode": "opa-cli", "opa_error": completed.stderr.strip(), "fallback": True},
            )
        data = json.loads(completed.stdout)
        result = data["result"][0]["expressions"][0]["value"]
        return self._decision_from_opa_result(request.package, result, "opa-cli")

    def _opa_data_paths(self) -> list[Path]:
        productive_dirs = ["base", "pmel_governance", "bpmn_lint", "decommissioning", "data"]
        paths = [self.bundle_path / name for name in productive_dirs]
        existing = [path for path in paths if path.exists()]
        return existing or [self.bundle_path]

    def _decision_from_opa_result(self, package: str, result: dict[str, Any], mode: str) -> PolicyDecision:
        return PolicyDecision(
            package=package,
            outcome=result.get("outcome", "DENY"),
            reason=result.get("reason", "opa_no_reason"),
            details={**{k: v for k, v in result.items() if k not in {"outcome", "reason"}}, "policy_mode": mode},
        )

    def _evaluate_native(self, request: EvaluationRequest) -> PolicyDecision:
        package = request.package
        data = request.input
        handlers = {
            "arhia.pmel.base.autonomy": self._autonomy,
            "arhia.pmel.base.hic": self._hic,
            "arhia.pmel.base.aibom": self._aibom,
            "arhia.pmel.governance.consent_gates": self._consent_gates,
            "arhia.pmel.governance.cycle_limits": self._cycle_limits,
            "arhia.pmel.governance.retention": self._retention,
            "arhia.pmel.governance.sensitive_data": self._sensitive_data,
            "arhia.pmel.governance.to_be_prohibitions": self._to_be_prohibitions,
            "arhia.pmel.decommissioning.triggers": self._decommissioning_triggers,
            "arhia.pmel.decommissioning.crypto_shred": self._crypto_shred,
        }
        if package.startswith("arhia.pmel.bpmn_lint."):
            return self._bpmn_lint(package, data)
        handler = handlers.get(package)
        if handler:
            return handler(package, data)
        return PolicyDecision(package, "AUDIT", "package_not_declared_in_native_fallback", {"policy_mode": "native-fallback"})

    def _normalize_input(self, package: str, data: dict[str, Any], trace_id: str) -> dict[str, Any]:
        normalized = dict(data)
        normalized.setdefault("trace_id", trace_id)
        if package == "arhia.pmel.base.autonomy":
            if "agent" not in normalized:
                normalized["agent"] = {
                    "component": normalized.get("component", "capture_agent"),
                    "autonomy_level": normalized.get("requested_level") or normalized.get("autonomy_level") or "A2",
                    "violation_count": int(normalized.get("violations_30d", 0)),
                }
        elif package == "arhia.pmel.governance.consent_gates":
            if "gate_check" not in normalized:
                consents = normalized.get("consents", {})
                normalized["gate_check"] = {
                    "action": normalized.get("action", "ingest_to_llm"),
                    "participant_id": normalized.get("participant_id", "P001"),
                    "consents": {
                        "t1": self._consent_record(consents.get("T1") or consents.get("t1")),
                        "t3": self._consent_record(consents.get("T3") or consents.get("t3")),
                        "t2_by_participant": {
                            normalized.get("participant_id", "P001"): self._consent_record(
                                consents.get("T2") or consents.get("t2")
                            )
                        },
                    },
                }
        elif package == "arhia.pmel.base.aibom":
            normalized["aibom"] = self._normalize_aibom(normalized.get("aibom", normalized))
        elif package == "arhia.pmel.governance.cycle_limits":
            normalized.setdefault("execution", normalized.copy())
        elif package == "arhia.pmel.base.hic":
            normalized.setdefault("checkpoint", "post_capture_review")
            normalized.setdefault("artefact_present", True)
            normalized.setdefault("artefact_type", "consultant_approval")
            normalized.setdefault("signer_role", "consultor_pro")
            normalized.setdefault("artefact_signature_valid", True)
        elif package.startswith("arhia.pmel.bpmn_lint."):
            normalized.setdefault("bpmn", self._default_bpmn_input())
            normalized.setdefault("deployment", {"tier": "pro"})
            normalized.setdefault("g07_closed", True)
        elif package == "arhia.pmel.governance.retention":
            normalized.setdefault(
                "retention_check",
                {"data_type": "llm_prompts", "age_days": 0, "deployment_id": "dxpro-local", "is_auditor_access": False},
            )
        elif package == "arhia.pmel.governance.sensitive_data":
            normalized.setdefault(
                "content_analysis",
                {
                    "content_hash": "unknown",
                    "detected_categories": [],
                    "has_additional_consent": False,
                    "notification_dpo_sent_at": None,
                    "destination": "llm_prompt",
                    "identified_at": "",
                },
            )
            normalized.setdefault("hours_since_identification", 0)
        elif package == "arhia.pmel.governance.to_be_prohibitions":
            normalized.setdefault(
                "to_be",
                {
                    "added_activities": [],
                    "removed_activities": [],
                    "technology_proposals": [],
                    "headcount_changes": [],
                    "findings": [],
                    "regulatory_controls_mapped": [],
                    "validated_technology_list": [],
                },
            )
        elif package == "arhia.pmel.decommissioning.triggers":
            normalized.setdefault("classify", {"raw_trigger_type": "retention_expiry"})
            normalized.setdefault("g08_closed", True)
        elif package == "arhia.pmel.decommissioning.crypto_shred":
            normalized.setdefault("precondition_check", self._default_crypto_preconditions())
        return normalized

    def _consent_record(self, value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return {
                "signed": bool(value.get("signed", False)),
                "hash": value.get("hash", "hash-present" if value.get("signed") else ""),
                "signer_role": value.get("signer_role", "client_representative"),
            }
        return {
            "signed": bool(value),
            "hash": "hash-present" if value else "",
            "signer_role": "client_representative",
        }

    def _normalize_aibom(self, aibom: dict[str, Any]) -> dict[str, Any]:
        models = aibom.get("models") or [{"id": "claude-sonnet-4-7"}]
        prompts = aibom.get("prompts") or [{"id": "pmel-capture-agent-v1.0"}]
        return {
            "bundle_name": aibom.get("bundle_name", "pmel-runtime"),
            "bundle_version": aibom.get("bundle_version", "1.0.0"),
            "models": [{"id": item} if isinstance(item, str) else item for item in models],
            "prompts": [{"id": item} if isinstance(item, str) else item for item in prompts],
            "dependencies": aibom.get("dependencies", []),
            "sbom_reference": aibom.get("sbom_reference", "dxpro://sbom/local"),
            "generated_at": aibom.get("generated_at", "2026-04-26T00:00:00Z"),
            "generated_by": aibom.get("generated_by", aibom.get("owner", "Sinergia Consulting Group")),
            "signature": aibom.get("signature", "dev-signature"),
            "signature_verified": aibom.get("signature_verified", True),
            "type": aibom.get("type", "static_per_release"),
        }

    def _default_bpmn_input(self) -> dict[str, Any]:
        return {
            "gateways": [],
            "reachability_analysis": {"start_events": ["start"], "end_events": ["end"], "unreachable_starts": [], "unreachable_ends": []},
            "activities": [{"id": "act-1", "name": "Validar solicitud", "incoming_flows": ["f1"], "outgoing_flows": ["f2"], "is_compensation": False}],
            "lanes": [{"id": "lane-1", "name": "Consultor", "element_count": 1}],
            "tarjan_analysis": {"strongly_connected_components": [], "total_sccs": 0, "sccs_without_exit": 0},
            "xor_with_dmn": [],
            "simulation_result": {"runs_total": 100, "runs_completed": 100, "runs_deadlocked": 0, "runs_livelocked": 0, "runs_errored": 0, "success_threshold": 0.98},
            "activity_naming_analysis": [{"id": "act-1", "name": "Validar solicitud", "language": "es", "passes_r08": True}],
            "xor_sat_analysis": [],
            "error_events": [],
            "or_gateway_analysis": [],
            "prose_bpmn_similarity": {"overall_cosine": 0.9, "section_scores": {"proposito": 0.9}, "required_sections_present": 6},
        }

    def _default_crypto_preconditions(self) -> dict[str, Any]:
        return {
            "case_id": "DECOM-DXPRO-LOCAL",
            "evidence_01_signed": True,
            "evidence_02_signed": True,
            "evidence_03_signed": True,
            "evidence_04a_signed": True,
            "evidence_04b_signed": True,
            "evidence_04c_signed": True,
            "evidence_05a_signed": True,
            "evidence_05b_signed_or_waiver": True,
            "kms_deletion_window_days": 7,
            "regulatory_preservation_required": False,
            "preservation_executed": False,
            "dry_run": True,
        }

    def _autonomy(self, package: str, data: dict[str, Any]) -> PolicyDecision:
        agent = data.get("agent", {})
        component = agent.get("component", "unknown")
        requested = agent.get("autonomy_level", "A2")
        violations = int(agent.get("violation_count", 0))
        allowed = {
            "capture_agent": "A2",
            "visual_interpreter": "A2",
            "to_be_generator": "A2",
            "bpmn_lint_agent": "A2",
            "lint_agent": "A2",
            "dmn_engine": "A2",
            "crypto_participant": "A2",
            "rgc_hypothesis_builder": "A2",
            "rgc_deep_research_contraster": "A2",
            "adaptive_question_bank": "A2",
            "multi_role_scoring": "A2",
            "psychometrics": "A2",
            "irr_reliability": "A2",
            "bayesian_synthesis": "A2",
            "executive_qa": "A2",
            "diagnostic_intelligence": "A2",
            "diagnostic_agent": "A2",
        }
        if violations >= 3:
            return PolicyDecision(package, "SUSPEND", "autonomy_repeated_violations", {"component": component})
        if requested in {"A3", "A4"}:
            return PolicyDecision(package, "DENY", "autonomy_level_above_pmel_max", {"requested_level": requested})
        if component not in allowed:
            return PolicyDecision(package, "ESCALATE", "unknown_component", {"component": component})
        if requested != allowed[component]:
            return PolicyDecision(package, "DENY", "autonomy_level_mismatch", {"component": component, "required": allowed[component]})
        return PolicyDecision(package, "PERMIT", "autonomy_within_policy", {"component": component, "policy_mode": "native-fallback"})

    def _aibom(self, package: str, data: dict[str, Any]) -> PolicyDecision:
        aibom = data.get("aibom", data)
        required = {"bundle_name", "bundle_version", "models", "prompts", "dependencies", "sbom_reference", "generated_at", "generated_by", "signature"}
        missing = sorted(field for field in required if field not in aibom)
        if missing:
            return PolicyDecision(package, "DENY", "aibom_missing_required_fields", {"missing": missing})
        if not aibom.get("signature_verified", False):
            return PolicyDecision(package, "DENY", "aibom_signature_invalid")
        return PolicyDecision(package, "PERMIT", "aibom_valid", {"bundle_version": aibom.get("bundle_version")})

    def _hic(self, package: str, data: dict[str, Any]) -> PolicyDecision:
        if not data.get("artefact_present", False):
            return PolicyDecision(package, "ESCALATE", "hic_checkpoint_missing_artefact", {"checkpoint": data.get("checkpoint")})
        if not data.get("artefact_signature_valid", False):
            return PolicyDecision(package, "DENY", "hic_artefact_signature_invalid")
        return PolicyDecision(package, "PERMIT", "hic_checkpoint_satisfied", {"checkpoint": data.get("checkpoint")})

    def _consent_gates(self, package: str, data: dict[str, Any]) -> PolicyDecision:
        gate = data.get("gate_check", {})
        action = gate.get("action", "")
        consents = gate.get("consents", {})
        t1 = bool(consents.get("t1", {}).get("signed"))
        t3 = bool(consents.get("t3", {}).get("signed"))
        participant_id = gate.get("participant_id", "P001")
        t2 = bool(consents.get("t2_by_participant", {}).get(participant_id, {}).get("signed"))
        if action == "start_observation" and t1:
            return PolicyDecision(package, "PERMIT", "t1_valid_observation_permitted")
        if action == "start_recording" and t1 and t2:
            return PolicyDecision(package, "PERMIT", "t1_and_t2_valid_recording_permitted")
        if action in {"ingest_to_llm", "process_m2_upload"} and t1 and t3:
            return PolicyDecision(package, "PERMIT", "t1_and_t3_valid_llm_ingest_permitted")
        return PolicyDecision(package, "DENY", "missing_required_consent", {"action": action})

    def _cycle_limits(self, package: str, data: dict[str, Any]) -> PolicyDecision:
        execution = data.get("execution", data)
        component = execution.get("component", "unknown")
        current_cycle = int(execution.get("current_cycle", 0))
        last_outcome = execution.get("last_outcome", "in_progress")
        request_another = bool(execution.get("request_another_cycle", False))
        limits = {
            "capture_agent": 5,
            "to_be_generator": 3,
            "visual_interpreter": 1,
            "lint_agent": 3,
            "bpmn_lint_agent": 3,
            "dmn_engine": 1,
            "crypto_participant": 1,
            "rgc_hypothesis_builder": 1,
            "rgc_deep_research_contraster": 1,
            "adaptive_question_bank": 2,
            "multi_role_scoring": 2,
            "psychometrics": 1,
            "irr_reliability": 1,
            "bayesian_synthesis": 2,
            "executive_qa": 1,
            "diagnostic_intelligence": 2,
            "diagnostic_agent": 5,
        }
        limit = limits.get(component, 1)
        if current_cycle >= limit and last_outcome == "failed":
            return PolicyDecision(package, "SUSPEND", "cycle_exhausted_with_failure", {"component": component})
        if request_another and current_cycle >= limit:
            return PolicyDecision(package, "DENY", "cycle_limit_exceeded", {"component": component, "max": limit})
        if current_cycle > 0 and current_cycle == limit - 1:
            return PolicyDecision(package, "ESCALATE", "entering_last_available_cycle", {"component": component})
        return PolicyDecision(package, "PERMIT", "within_cycle_limit", {"component": component, "max": limit})

    def _retention(self, package: str, data: dict[str, Any]) -> PolicyDecision:
        check = data.get("retention_check", {})
        windows = {"recordings_original": 30, "llm_prompts": 30, "llm_responses": 30, "bpmn_artifacts_intermediate": 30, "telemetry_logs": 90}
        data_type = check.get("data_type", "llm_prompts")
        age = int(check.get("age_days", 0))
        window = int(check.get("window_days", windows.get(data_type, 1825)))
        if age < window:
            return PolicyDecision(package, "PERMIT", "within_retention_window", {"data_type": data_type, "age": age, "window": window})
        if check.get("is_auditor_access"):
            return PolicyDecision(package, "AUDIT", "expired_retention_auditor_access", {"data_type": data_type})
        if data_type in {"recordings_original", "llm_prompts", "llm_responses", "bpmn_artifacts_intermediate"}:
            return PolicyDecision(package, "MODIFY", "trigger_d3_decommissioning", {"data_type": data_type})
        return PolicyDecision(package, "ESCALATE", "documental_retention_expired", {"data_type": data_type})

    def _sensitive_data(self, package: str, data: dict[str, Any]) -> PolicyDecision:
        analysis = data.get("content_analysis", {})
        categories = analysis.get("detected_categories", [])
        if not categories:
            return PolicyDecision(package, "PERMIT", "no_sensitive_data_detected")
        if analysis.get("notification_dpo_sent_at") is None and int(data.get("hours_since_identification", 0)) > 48:
            return PolicyDecision(package, "SUSPEND", "dpo_notification_window_expired", {"categories": categories})
        if analysis.get("destination") == "llm_prompt" and not analysis.get("has_additional_consent", False):
            return PolicyDecision(package, "DENY", "sensitive_to_llm_without_consent", {"categories": categories})
        return PolicyDecision(package, "PERMIT", "sensitive_data_with_additional_consent", {"categories": categories})

    def _to_be_prohibitions(self, package: str, data: dict[str, Any]) -> PolicyDecision:
        to_be = data.get("to_be", {})
        p1 = [act.get("id") for act in to_be.get("added_activities", []) if not act.get("justified_by_findings")]
        regulated = {ctrl.get("activity_id") for ctrl in to_be.get("regulatory_controls_mapped", [])}
        p2 = [act.get("id") for act in to_be.get("removed_activities", []) if act.get("id") in regulated]
        validated = set(to_be.get("validated_technology_list", []))
        p3 = [tech.get("name") for tech in to_be.get("technology_proposals", []) if tech.get("name") not in validated]
        p4 = [change.get("id") for change in to_be.get("headcount_changes", []) if change.get("reduction", 0) > 0 and not change.get("has_justification_memo")]
        if p1 or p2:
            return PolicyDecision(package, "DENY", "to_be_hard_prohibitions_violated", {"p1": p1, "p2": p2})
        if p3 or p4:
            return PolicyDecision(package, "ESCALATE", "to_be_soft_prohibitions_flagged", {"p3": p3, "p4": p4})
        return PolicyDecision(package, "PERMIT", "to_be_all_prohibitions_respected")

    def _decommissioning_triggers(self, package: str, data: dict[str, Any]) -> PolicyDecision:
        classify = data.get("classify", {})
        raw = classify.get("raw_trigger_type")
        mapping = {
            ("revocation", "full"): "D1_revocation_total",
            ("revocation", "participant"): "D1_revocation_participant",
            ("revocation", "llm_only"): "D1_revocation_llm_only",
            ("contract_termination", None): "D2_contract_termination",
            ("retention_expiry", None): "D3_natural_closure",
            ("incident", None): "D4_forced_incident",
        }
        canonical = mapping.get((raw, classify.get("revocation_scope"))) or mapping.get((raw, None))
        if not canonical:
            return PolicyDecision(package, "DENY", "unknown_trigger_type", {"raw_trigger_type": raw})
        if canonical == "D4_forced_incident" and classify.get("incident_contained") is False:
            return PolicyDecision(package, "SUSPEND", "incident_not_contained", {"canonical_type": canonical})
        if canonical == "D1_revocation_participant" and not data.get("g08_closed", True):
            return PolicyDecision(package, "ESCALATE", "partial_revocation_requires_tombstone_path", {"canonical_type": canonical})
        return PolicyDecision(package, "PERMIT", "trigger_classified", {"canonical_type": canonical})

    def _crypto_shred(self, package: str, data: dict[str, Any]) -> PolicyDecision:
        check = data.get("precondition_check", {})
        required = [
            "evidence_01_signed",
            "evidence_02_signed",
            "evidence_03_signed",
            "evidence_04a_signed",
            "evidence_04b_signed",
            "evidence_04c_signed",
            "evidence_05a_signed",
            "evidence_05b_signed_or_waiver",
        ]
        missing = [item for item in required if check.get(item) is not True]
        if missing:
            return PolicyDecision(package, "DENY", "crypto_shred_preconditions_failed", {"missing": missing})
        if int(check.get("kms_deletion_window_days", 0)) < 7:
            return PolicyDecision(package, "DENY", "kms_window_too_short")
        if check.get("regulatory_preservation_required") and not check.get("preservation_executed"):
            return PolicyDecision(package, "DENY", "preservation_required_not_executed")
        if check.get("dry_run", False):
            return PolicyDecision(package, "MODIFY", "dry_run_only", {"case_id": check.get("case_id")})
        return PolicyDecision(package, "PERMIT", "crypto_shred_preconditions_satisfied", {"case_id": check.get("case_id")})

    def _bpmn_lint(self, package: str, data: dict[str, Any]) -> PolicyDecision:
        bpmn = data.get("bpmn", {})
        rule = package.rsplit(".", 1)[-1]
        if rule == "r01_gateways":
            unbalanced = [gw.get("id") for gw in bpmn.get("gateways", []) if gw.get("direction") == "diverging" and not gw.get("pair_id")]
            return self._permit_or(package, unbalanced, "r01_unbalanced", "r01_all_gateways_balanced")
        if rule == "r02_reachability":
            analysis = bpmn.get("reachability_analysis", {})
            bad = analysis.get("unreachable_starts", []) + analysis.get("unreachable_ends", [])
            return self._permit_or(package, bad, "r02_unreachable", "r02_all_reachable")
        if rule == "r03_orphans":
            orphans = [act.get("id") for act in bpmn.get("activities", []) if not act.get("is_compensation") and (not act.get("incoming_flows") or not act.get("outgoing_flows"))]
            return self._permit_or(package, orphans, "r03_orphans", "r03_no_orphans")
        if rule == "r04_lanes":
            empty = [lane.get("id") for lane in bpmn.get("lanes", []) if lane.get("element_count", 0) == 0]
            return PolicyDecision(package, "ESCALATE", "r04_empty_lanes", {"empty_lanes": empty}) if empty else PolicyDecision(package, "PERMIT", "r04_all_lanes_populated")
        if rule == "r05_acyclicity":
            sccs = int(bpmn.get("tarjan_analysis", {}).get("sccs_without_exit", 0))
            return PolicyDecision(package, "DENY", "r05_cycles_without_exit", {"sccs_without_exit": sccs}) if sccs else PolicyDecision(package, "PERMIT", "r05_acyclic_or_all_cycles_have_exits")
        if rule == "r06_dmn":
            pairs = bpmn.get("xor_with_dmn", [])
            bad = [pair for pair in pairs if not pair.get("dmn_consistent", True) or not pair.get("dmn_complete", True)]
            return self._permit_or(package, bad, "r06_dmn_issues", "r06_dmn_consistent_and_complete")
        if rule == "r07_simulation":
            sim = bpmn.get("simulation_result", {})
            total = max(int(sim.get("runs_total", 100)), 1)
            success_rate = int(sim.get("runs_completed", total)) / total
            fail = sim.get("runs_deadlocked", 0) > 0 or sim.get("runs_livelocked", 0) > 0 or success_rate < float(sim.get("success_threshold", 0.98))
            return PolicyDecision(package, "DENY", "r07_simulation_failed", {"success_rate": success_rate}) if fail else PolicyDecision(package, "PERMIT", "r07_simulation_passed", {"success_rate": success_rate})
        if rule == "r08_naming":
            invalid = [act for act in bpmn.get("activity_naming_analysis", []) if not act.get("passes_r08", True)]
            return PolicyDecision(package, "ESCALATE", "r08_naming_issues", {"invalid": invalid}) if invalid else PolicyDecision(package, "PERMIT", "r08_all_names_valid")
        if rule == "r09_xor_exclusive":
            bad = [entry for entry in bpmn.get("xor_sat_analysis", []) if not entry.get("is_mutually_exclusive", True) or not entry.get("is_complete", True)]
            return self._permit_or(package, bad, "r09_xor_issues", "r09_xor_exclusive_and_complete")
        if rule == "r10_error_handlers":
            unhandled = [ev.get("event_id") for ev in bpmn.get("error_events", []) if not ev.get("is_end_error") and not ev.get("has_boundary_handler") and not ev.get("has_escalation_route")]
            return PolicyDecision(package, "ESCALATE", "r10_unhandled_errors", {"unhandled": unhandled}) if unhandled else PolicyDecision(package, "PERMIT", "r10_all_errors_handled")
        if rule == "r11_or_gateways":
            bad = [gw for gw in bpmn.get("or_gateway_analysis", []) if not gw.get("at_least_one_branch_activates", True) or not gw.get("has_matching_converge", True)]
            return PolicyDecision(package, "ESCALATE", "r11_or_issues", {"issues": bad}) if bad else PolicyDecision(package, "PERMIT", "r11_all_or_gateways_valid")
        if rule == "r12_prose_bpmn":
            sim = bpmn.get("prose_bpmn_similarity", {})
            overall = float(sim.get("overall_cosine", 1.0))
            return PolicyDecision(package, "DENY", "r12_prose_bpmn_misaligned", {"cosine": overall}) if overall < 0.75 else PolicyDecision(package, "PERMIT", "r12_prose_bpmn_aligned", {"cosine": overall})
        return PolicyDecision(package, "AUDIT", "bpmn_lint_rule_not_mapped")

    def _permit_or(self, package: str, problems: list[Any], deny_reason: str, permit_reason: str) -> PolicyDecision:
        if problems:
            return PolicyDecision(package, "DENY", deny_reason, {"issues": problems})
        return PolicyDecision(package, "PERMIT", permit_reason)
