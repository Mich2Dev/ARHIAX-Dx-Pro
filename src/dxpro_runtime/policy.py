"""Policy evaluation layer for ARHIAX-DX Pro."""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from typing import Any

from .models import EvaluationRequest, PolicyDecision


class PolicyEngine:
    def __init__(self, bundle_path: Path, opa_url: str | None = None) -> None:
        self.bundle_path = bundle_path
        self.opa_url = opa_url.rstrip("/") if opa_url else None
        self.manifest = self._load_manifest()

    def evaluate(self, request: EvaluationRequest) -> PolicyDecision:
        if self.opa_url:
            return self._evaluate_with_opa(request)
        return self._evaluate_native(request)

    def _load_manifest(self) -> dict[str, Any]:
        manifest_path = self.bundle_path / "manifest.json"
        if not manifest_path.exists():
            return {"bundle_name": "unknown", "packages": []}
        return json.loads(manifest_path.read_text(encoding="utf-8"))

    def _evaluate_with_opa(self, request: EvaluationRequest) -> PolicyDecision:
        path = request.package.replace(".", "/")
        payload = json.dumps({"input": request.input}).encode("utf-8")
        req = urllib.request.Request(
            f"{self.opa_url}/v1/data/{path}/decision",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
        result = data.get("result", {})
        return PolicyDecision(
            package=request.package,
            outcome=result.get("outcome", "DENY"),
            reason=result.get("reason", "opa_no_reason"),
            details={k: v for k, v in result.items() if k not in {"outcome", "reason"}},
        )

    def _evaluate_native(self, request: EvaluationRequest) -> PolicyDecision:
        package = request.package
        data = request.input

        if package == "arhia.pmel.base.autonomy":
            return self._autonomy(package, data)
        if package == "arhia.pmel.governance.consent_gates":
            return self._consent_gates(package, data)
        if package == "arhia.pmel.governance.cycle_limits":
            return self._cycle_limits(package, data)
        if package == "arhia.pmel.base.aibom":
            return self._aibom(package, data)

        return PolicyDecision(
            package=package,
            outcome="AUDIT",
            reason="native_evaluator_not_implemented_for_package",
            details={
                "mode": "native-fallback",
                "supported_packages": [
                    "arhia.pmel.base.autonomy",
                    "arhia.pmel.base.aibom",
                    "arhia.pmel.governance.consent_gates",
                    "arhia.pmel.governance.cycle_limits",
                ],
            },
        )

    def _autonomy(self, package: str, data: dict[str, Any]) -> PolicyDecision:
        requested = data.get("requested_level") or data.get("autonomy_level") or "A2"
        component = data.get("component", "unknown")
        violations = int(data.get("violations_30d", 0))

        if requested in {"A3", "A4"}:
            return PolicyDecision(package, "DENY", "autonomy_level_above_pmel_max", {"requested_level": requested})
        if violations >= 3:
            return PolicyDecision(package, "SUSPEND", "autonomy_repeated_violations", {"component": component})
        if requested not in {"A0", "A1", "A2"}:
            return PolicyDecision(package, "DENY", "unknown_autonomy_level", {"requested_level": requested})
        return PolicyDecision(package, "PERMIT", "autonomy_within_policy", {"component": component})

    def _consent_gates(self, package: str, data: dict[str, Any]) -> PolicyDecision:
        action = data.get("action", "")
        consents = data.get("consents", {})
        required_by_action = {
            "start_observation": {"T1"},
            "start_recording": {"T1", "T2"},
            "ingest_to_llm": {"T1", "T3"},
            "process_m2_upload": {"T1", "T3"},
        }
        required = required_by_action.get(action)
        if required is None:
            return PolicyDecision(package, "DENY", "unknown_consent_action", {"action": action})
        missing = sorted(t for t in required if not consents.get(t))
        if missing:
            return PolicyDecision(package, "DENY", "missing_required_consent", {"action": action, "missing": missing})
        return PolicyDecision(package, "PERMIT", "consent_gate_satisfied", {"action": action})

    def _cycle_limits(self, package: str, data: dict[str, Any]) -> PolicyDecision:
        execution = data.get("execution", data)
        component = execution.get("component", "unknown")
        current_cycle = int(execution.get("current_cycle", 0))
        last_outcome = execution.get("last_outcome", "in_progress")
        request_another = bool(execution.get("request_another_cycle", False))
        limits = {"capture_agent": 5, "to_be_generator": 3, "visual_interpreter": 1, "lint_agent": 3}
        limit = limits.get(component, 1)

        if current_cycle >= limit and last_outcome == "failed":
            return PolicyDecision(package, "SUSPEND", "cycle_exhausted_with_failure", {"component": component})
        if request_another and current_cycle >= limit:
            return PolicyDecision(package, "DENY", "cycle_limit_exceeded", {"component": component, "max": limit})
        if current_cycle == limit - 1:
            return PolicyDecision(package, "ESCALATE", "entering_last_available_cycle", {"component": component})
        return PolicyDecision(package, "PERMIT", "within_cycle_limit", {"component": component, "max": limit})

    def _aibom(self, package: str, data: dict[str, Any]) -> PolicyDecision:
        aibom = data.get("aibom", data)
        required = {"bundle_version", "models", "prompts", "owner"}
        missing = sorted(field for field in required if not aibom.get(field))
        if missing:
            return PolicyDecision(package, "DENY", "aibom_missing_required_fields", {"missing": missing})
        return PolicyDecision(package, "PERMIT", "aibom_minimal_valid", {"bundle_version": aibom.get("bundle_version")})

