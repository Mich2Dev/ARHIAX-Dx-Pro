"""Loads and exposes the ARHIAX Dx governed tool catalog."""

from __future__ import annotations

from typing import Any

from arhiax_dx.config import Settings
from arhiax_dx.specs import load_json_spec


def autonomy_rank(level: str) -> int:
    ranks = ["A0", "A1", "A2", "A3", "A4"]
    try:
        return ranks.index(level)
    except ValueError:
        return -1


class ToolRegistry:
    def __init__(self, settings: Settings):
        specs_root = settings.specs_path
        self.settings = settings
        self._agent_identity = load_json_spec(str(specs_root / "agent_identity.json"))
        self._tool_catalog = load_json_spec(str(specs_root / "tool_catalog.json"))
        self._data_scopes = load_json_spec(str(specs_root / "data_scopes.json"))
        self._operation_catalog = load_json_spec(str(specs_root / "operation_catalog.json"))
        self._autonomy_profile = load_json_spec(str(specs_root / "autonomy_profile.json"))
        self._policy_matrix = load_json_spec(str(specs_root / "policy_matrix.json"))
        self._model_strategy = load_json_spec(str(specs_root / "model_strategy.json"))
        self._bbr_baseline = load_json_spec(str(specs_root / "bbr_baseline.json"))

    def agent_identity(self) -> dict[str, Any]:
        return self._agent_identity

    def tool_manifest(self) -> list[dict[str, Any]]:
        return self._tool_catalog["tools"]

    def data_scopes(self) -> list[dict[str, Any]]:
        return self._data_scopes["scopes"]

    def operations(self) -> list[dict[str, Any]]:
        return self._operation_catalog["operations"]

    def model_strategy(self) -> dict[str, Any]:
        return self._model_strategy

    def bbr_baseline(self) -> dict[str, Any]:
        return self._bbr_baseline

    def autonomy_profile(self) -> dict[str, Any]:
        return self._autonomy_profile

    def policy_matrix(self) -> dict[str, Any]:
        return self._policy_matrix

    def declared_tool_names(self) -> set[str]:
        return {item["name"] for item in self._tool_catalog["tools"]}

    def declared_scope_names(self) -> set[str]:
        return {item["name"] for item in self._data_scopes["scopes"]}

    def declared_operation_names(self) -> set[str]:
        return {item["name"] for item in self._operation_catalog["operations"] if item["enabled"]}

    def default_pipeline_tools(self) -> list[str]:
        return [item["name"] for item in self._tool_catalog["tools"] if item.get("default_pipeline", False)]

    def get_tool(self, name: str) -> dict[str, Any] | None:
        return next((item for item in self._tool_catalog["tools"] if item["name"] == name), None)

    def active_model_routes(self, tool_names: list[str]) -> list[dict[str, Any]]:
        routes: list[dict[str, Any]] = []
        tool_set = set(tool_names)
        for route in self._model_strategy["routes"]:
            matched = sorted(tool_set.intersection(route["tools"]))
            if matched:
                routes.append(
                    {
                        "stage": route["stage"],
                        "matched_tools": matched,
                        "primary": route["primary"],
                        "fallback": route["fallback"],
                        "max_tokens": route["max_tokens"],
                        "temperature": route["temperature"],
                    }
                )
        return routes

    def promotion_assessment(self, simulation: dict[str, Any]) -> dict[str, Any]:
        approval = bool(simulation.get("human_approval", False))
        bbr_clean_days = int(simulation.get("bbr_clean_days", 0))
        qa_average = float(simulation.get("qa_average_last5", simulation.get("qa_score", 0)))
        irr_alpha = float(simulation.get("irr_alpha", 0.0))
        eligible = bbr_clean_days >= 30 and qa_average >= 87.0 and irr_alpha >= 0.75 and approval
        return {
            "eligible_for_a2": eligible,
            "metrics": {
                "bbr_clean_days": bbr_clean_days,
                "qa_average_last5": qa_average,
                "irr_alpha": irr_alpha,
                "human_approval": approval,
            },
            "requirements": self._autonomy_profile["promotion_requirements"],
        }
