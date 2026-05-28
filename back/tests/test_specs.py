from __future__ import annotations

from arhiax_dx.services.tool_registry import ToolRegistry


def test_specs_load_and_match_dx_contract(settings):
    registry = ToolRegistry(settings)

    assert registry.agent_identity()["authorization_boundary_id"] == "boundary-diagnostico-org"
    assert registry.agent_identity()["initial_autonomy_level"] == "A1"
    assert len(registry.tool_manifest()) == 24
    assert "g10a_scoring" in registry.declared_tool_names()
    assert "survey_responses" in registry.declared_scope_names()
    assert "humanInTheLoop" in registry.declared_operation_names()


def test_model_routes_are_available_for_reporting_tools(settings):
    registry = ToolRegistry(settings)

    routes = registry.active_model_routes(["g13_redactor", "docx_generator"])

    assert routes
    assert any(route["stage"] == "reporting" for route in routes)
