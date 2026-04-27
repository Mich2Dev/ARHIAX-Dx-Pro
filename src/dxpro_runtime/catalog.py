"""Standalone governance catalog for ARHIAX DX Pro."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


AUTONOMY_LEVELS = ["A0", "A1", "A2", "A3", "A4"]


def autonomy_rank(level: str) -> int:
    try:
        return AUTONOMY_LEVELS.index(level)
    except ValueError:
        return -1


@dataclass(frozen=True)
class DxProCatalog:
    """In-process catalog so DX Pro does not depend on ARHIAX DX."""

    version: str = "2026.04-dxpro"

    def agent_identity(self) -> dict[str, Any]:
        return {
            "name": "ARHIAX-DxPro-v1",
            "product": "ARHIAX DX Pro",
            "authorization_boundary_id": "boundary-diagnostico-org-pro",
            "initial_autonomy_level": "A1",
            "max_autonomy_level": "A2",
            "standard": "ARHIAX PMEL/ATK",
        }

    def tool_manifest(self) -> list[dict[str, Any]]:
        base_tools = [
            ("g01_receptor", "intake", "MEDIUM"),
            ("g02_configurador", "intake", "MEDIUM"),
            ("g03_cienciometro", "research", "MEDIUM"),
            ("g04_cartografo", "mapping", "MEDIUM"),
            ("g05_brechas", "mapping", "MEDIUM"),
            ("g06_bpmn_architect", "design", "HIGH"),
            ("g07_cuellos", "quantification", "HIGH"),
            ("g08_optimizador", "design", "HIGH"),
            ("g09a_preguntas", "survey_design", "MEDIUM"),
            ("g09b_ramificacion", "survey_design", "MEDIUM"),
            ("g09c_validacion", "survey_design", "MEDIUM"),
            ("g10a_scoring", "analysis", "HIGH"),
            ("g10b_psicometria", "analysis", "HIGH"),
            ("g11a_bayesiano", "analysis", "HIGH"),
            ("g11b_nlp", "analysis", "MEDIUM"),
            ("g12_hallazgos", "synthesis", "HIGH"),
            ("g13_redactor", "reporting", "HIGH"),
            ("g14_qa_control", "qa", "CRITICAL"),
            ("docx_generator", "rendering", "CRITICAL"),
            ("academic_search", "research", "MEDIUM"),
            ("web_search", "research", "MEDIUM"),
            ("irr_calculator", "analysis", "HIGH"),
            ("bpmn_generator", "design", "HIGH"),
            ("scoring_engine", "analysis", "HIGH"),
        ]
        pro_tools = [
            ("pmel_capture_agent", "pmel_capture", "HIGH"),
            ("pmel_to_be_generator", "pmel_design", "HIGH"),
            ("pmel_visual_interpreter", "pmel_interpretation", "HIGH"),
            ("pmel_bpmn_lint_agent", "pmel_validation", "CRITICAL"),
            ("dmn_engine", "decision_modeling", "HIGH"),
            ("crypto_participant", "decommissioning", "CRITICAL"),
            ("rgc_hypothesis_builder", "research_grounding", "HIGH"),
            ("rgc_deep_research_contraster", "research_contrast", "HIGH"),
            ("adaptive_question_bank", "survey_design", "HIGH"),
            ("multi_role_scoring", "analysis", "HIGH"),
            ("psychometrics", "analysis", "HIGH"),
            ("irr_reliability", "analysis", "HIGH"),
            ("bayesian_synthesis", "analysis", "HIGH"),
            ("executive_qa", "qa", "CRITICAL"),
            ("diagnostic_intelligence", "synthesis", "CRITICAL"),
        ]
        tools: list[dict[str, Any]] = []
        for name, phase, severity in base_tools + pro_tools:
            tools.append(
                {
                    "name": name,
                    "phase": phase,
                    "severity": severity,
                    "minimum_autonomy": "A1",
                    "default_pipeline": name.startswith("g") or name in {"irr_calculator", "pmel_capture_agent", "pmel_bpmn_lint_agent"},
                }
            )
        return tools

    def data_scopes(self) -> list[dict[str, Any]]:
        names = [
            "organizational_context",
            "survey_responses",
            "audit_log",
            "process_interviews",
            "pmel_artifacts",
            "bpmn_models",
            "decision_tables",
            "execution_evidence",
            "psychometric_metrics",
            "scoring_outputs",
            "diagnostic_intelligence",
        ]
        return [{"name": name, "retention_max_days": 30} for name in names]

    def operations(self) -> list[dict[str, Any]]:
        names = [
            "modelInvoke",
            "toolCall",
            "dataAccess",
            "pmelCapture",
            "pmelLint",
            "bpmnGenerate",
            "reportDraft",
            "certificateIssue",
            "questionBankBuild",
            "multiRoleScore",
            "psychometricEvaluate",
            "irrEvaluate",
            "bayesianSynthesize",
            "executiveQa",
            "diagnosticIntegrate",
        ]
        return [{"name": name, "enabled": True} for name in names]

    def autonomy_profile(self) -> dict[str, Any]:
        return {
            "initial": "A1",
            "maximum": "A2",
            "promotion_requirements": {
                "to": "A2",
                "bbr_clean_days": 30,
                "qa_average_last5_min": 87,
                "irr_alpha_min": 0.75,
                "human_approval_required": True,
            },
        }

    def policy_matrix(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "outcomes": ["PERMIT", "DENY", "ESCALATE", "MODIFY", "AUDIT", "SUSPEND"],
            "bundles": ["PMEL-B01", "PMEL-B02", "PMEL-B03", "PMEL-B04", "PMEL-B05"],
        }

    def model_strategy(self) -> dict[str, Any]:
        return {
            "primary": "client_bound_model",
            "fallback": "client_bound_fallback",
            "routing": "stage_and_tool_sensitive",
            "no_provider_credentials_packaged": True,
        }

    def bbr_baseline(self) -> dict[str, Any]:
        return {
            "minimum_clean_days_for_promotion": 30,
            "deny_on_repeated_violations_30d": 3,
            "evidence_required": True,
        }

    def declared_tool_names(self) -> set[str]:
        return {item["name"] for item in self.tool_manifest()}

    def declared_scope_names(self) -> set[str]:
        return {item["name"] for item in self.data_scopes()}

    def declared_operation_names(self) -> set[str]:
        return {item["name"] for item in self.operations() if item["enabled"]}

    def default_pipeline_tools(self) -> list[str]:
        return [item["name"] for item in self.tool_manifest() if item["default_pipeline"]]

    def get_tool(self, name: str) -> dict[str, Any] | None:
        return next((item for item in self.tool_manifest() if item["name"] == name), None)
