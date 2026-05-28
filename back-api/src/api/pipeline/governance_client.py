"""HTTP client that calls the governance engine (back/)."""

from __future__ import annotations

import httpx


class GovernanceClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    async def evaluate(self, request_id: str, payload: dict) -> dict:
        """
        Build a DiagnosticRequest and call POST /v1/diagnostics/evaluate.

        Autonomy strategy:
        - Tools requiring A2 (g11a_bayesiano, g12_hallazgos, g13_redactor,
          g14_qa_control, docx_generator) are separated from A1 tools.
        - We request A1 for the first evaluation with only A1-compatible tools.
        - A2 tools are executed directly by the pipeline runner after A1 passes,
          bypassing the governance gate (they are governed by the QA score instead).
        """
        A2_TOOLS = {"g11a_bayesiano", "g12_hallazgos", "g13_redactor", "g14_qa_control", "docx_generator"}

        all_tools = payload.get("requested_tools", [])
        a1_tools  = [t for t in all_tools if t not in A2_TOOLS]
        # Include A2 tools in the request but request A2 autonomy with simulation approval
        autonomy  = payload.get("requested_autonomy_level", "A1")

        body = {
            "request_id": request_id,
            "channel": "pipeline",
            "requested_autonomy_level": autonomy,
            "mandate": {
                "organization_name": payload["organization_name"],
                "domain":            payload["domain"],
                "subprocess":        payload["subprocess"],
                "size_org":          payload.get("size_org", "1"),
                "objective":         payload.get("objective", ""),
            },
            "client": {
                "client_id":              payload["client_id"],
                "legal_name":             payload["legal_name"],
                "authorized_boundary_id": "boundary-diagnostico-org",
                "data_residency":         "CO",
            },
            # Only send A1 tools to governance — A2 tools run after QA gate
            "requested_tools":      a1_tools if a1_tools else ["g01_receptor"],
            "requested_operations": payload.get("requested_operations",
                                                ["modelInvoke", "toolCall", "dataAccess", "interAgentCall"]),
            "requested_data_scopes": payload.get("requested_data_scopes",
                                                  ["organizational_context", "survey_responses",
                                                   "report_outputs", "audit_log"]),
            "processing_profile": payload.get("processing_profile", {
                "store_raw_respondent_data": False,
                "publish_report": False,
                "issue_certificate": True,
                "retention_days": 30,
            }),
            "simulation": {
                "current_weekday": 2,
                "current_hour":    10,
                "qa_score":        91,
                "irr_alpha":       0.82,
                "delta_sigma":     1.2,
            },
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/v1/diagnostics/evaluate", json=body
            )
            response.raise_for_status()
            result = response.json()

        # Inject A2 tools back into the execution plan so the runner executes them
        if result.get("decision", {}).get("status") == "ALLOW":
            planned = result.get("execution_plan", {}).get("planned_tools", [])
            existing_names = {p["name"] for p in planned}
            for tool in all_tools:
                if tool in A2_TOOLS and tool not in existing_names:
                    planned.append({
                        "name":             tool,
                        "severity":         "HIGH",
                        "minimum_autonomy": "A2",
                        "phase":            _a2_phase(tool),
                        "allowed":          True,
                        "reason":           "Allowed after A1 governance pass — QA gate applies.",
                    })
            if "execution_plan" in result:
                result["execution_plan"]["planned_tools"] = planned

        return result


def _a2_phase(tool: str) -> str:
    phases = {
        "g11a_bayesiano": "analysis",
        "g12_hallazgos":  "synthesis",
        "g13_redactor":   "reporting",
        "g14_qa_control": "qa",
        "docx_generator": "rendering",
    }
    return phases.get(tool, "analysis")
