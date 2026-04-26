package arhia.pmel.bpmn_lint_test

import data.arhia.pmel.bpmn_lint.r01_gateways
import data.arhia.pmel.bpmn_lint.r02_reachability
import data.arhia.pmel.bpmn_lint.r03_orphans
import data.arhia.pmel.bpmn_lint.r04_lanes
import data.arhia.pmel.bpmn_lint.r05_acyclicity
import data.arhia.pmel.bpmn_lint.r06_dmn
import data.arhia.pmel.bpmn_lint.r07_simulation
import data.arhia.pmel.bpmn_lint.r08_naming
import data.arhia.pmel.bpmn_lint.r09_xor_exclusive
import data.arhia.pmel.bpmn_lint.r10_error_handlers
import data.arhia.pmel.bpmn_lint.r11_or_gateways
import data.arhia.pmel.bpmn_lint.r12_prose_bpmn

# =============================================================================
# R1 — Gateways balanceados
# =============================================================================

test_r01_permit_all_balanced if {
    r01_gateways.decision.outcome == "PERMIT" with input as {
        "bpmn": {
            "gateways": [
                {"id": "g1", "type": "exclusive", "direction": "diverging", "pair_id": "g1"},
                {"id": "g2", "type": "exclusive", "direction": "converging", "pair_id": "g1"}
            ]
        }
    }
}

test_r01_deny_unbalanced if {
    count(r01_gateways.deny) > 0 with input as {
        "bpmn": {
            "gateways": [
                {"id": "g1", "type": "exclusive", "direction": "diverging", "pair_id": "g1"}
            ]
        }
    }
}

# =============================================================================
# R2 — Alcanzabilidad
# =============================================================================

test_r02_permit_all_reachable if {
    r02_reachability.decision.outcome == "PERMIT" with input as {
        "bpmn": {"reachability_analysis": {
            "start_events": ["s1"], "end_events": ["e1"],
            "unreachable_starts": [], "unreachable_ends": []
        }}
    }
}

test_r02_deny_unreachable_end if {
    count(r02_reachability.deny) > 0 with input as {
        "bpmn": {"reachability_analysis": {
            "start_events": ["s1"], "end_events": ["e1", "e_orphan"],
            "unreachable_starts": [], "unreachable_ends": ["e_orphan"]
        }}
    }
}

test_r02_escalate_no_start if {
    count(r02_reachability.escalate) > 0 with input as {
        "bpmn": {"reachability_analysis": {
            "start_events": [], "end_events": ["e1"],
            "unreachable_starts": [], "unreachable_ends": []
        }}
    }
}

# =============================================================================
# R3 — Orphans
# =============================================================================

test_r03_permit_no_orphans if {
    r03_orphans.decision.outcome == "PERMIT" with input as {
        "bpmn": {"activities": [
            {"id": "a1", "incoming_flows": ["f1"], "outgoing_flows": ["f2"], "is_compensation": false}
        ]}
    }
}

test_r03_deny_orphan_no_incoming if {
    count(r03_orphans.deny) > 0 with input as {
        "bpmn": {"activities": [
            {"id": "a1", "incoming_flows": [], "outgoing_flows": ["f1"], "is_compensation": false}
        ]}
    }
}

# =============================================================================
# R4 — Lanes (material)
# =============================================================================

test_r04_permit_populated if {
    r04_lanes.decision.outcome == "PERMIT" with input as {
        "bpmn": {"lanes": [{"id": "L1", "element_count": 3}]}
    }
}

test_r04_escalate_empty if {
    count(r04_lanes.escalate) > 0 with input as {
        "bpmn": {"lanes": [{"id": "L1", "element_count": 0}]}
    }
}

# =============================================================================
# R5 — Acyclicity
# =============================================================================

test_r05_permit_no_cycles if {
    r05_acyclicity.decision.outcome == "PERMIT" with input as {
        "bpmn": {"tarjan_analysis": {
            "total_sccs": 5, "sccs_without_exit": 0,
            "strongly_connected_components": []
        }}
    }
}

test_r05_deny_cycle_no_exit if {
    count(r05_acyclicity.deny) > 0 with input as {
        "bpmn": {"tarjan_analysis": {
            "total_sccs": 3, "sccs_without_exit": 1,
            "strongly_connected_components": [
                {"nodes": ["n1", "n2"], "has_exit": false}
            ]
        }}
    }
}

# =============================================================================
# R6 — DMN
# =============================================================================

test_r06_permit_no_dmn if {
    r06_dmn.decision.outcome == "PERMIT" with input as {
        "bpmn": {"xor_with_dmn": []}
    }
}

test_r06_deny_inconsistent if {
    count(r06_dmn.deny) > 0 with input as {
        "bpmn": {"xor_with_dmn": [
            {"gateway_id": "g1", "dmn_id": "d1", "dmn_consistent": false, "dmn_complete": true}
        ]}
    }
}

# =============================================================================
# R7 — Simulation
# =============================================================================

test_r07_permit_full_success if {
    r07_simulation.decision.outcome == "PERMIT" with input as {
        "bpmn": {"simulation_result": {
            "runs_total": 100, "runs_completed": 99,
            "runs_deadlocked": 0, "runs_livelocked": 0, "runs_errored": 1,
            "success_threshold": 0.98
        }}
    }
}

test_r07_deny_deadlock if {
    count(r07_simulation.deny) > 0 with input as {
        "bpmn": {"simulation_result": {
            "runs_total": 100, "runs_completed": 95,
            "runs_deadlocked": 5, "runs_livelocked": 0, "runs_errored": 0,
            "success_threshold": 0.98
        }}
    }
}

# =============================================================================
# R8 — Naming (material)
# =============================================================================

test_r08_permit_valid_names if {
    r08_naming.decision.outcome == "PERMIT" with input as {
        "bpmn": {"activity_naming_analysis": [
            {"id": "a1", "name": "Aprobar solicitud", "language": "es", "first_token": "aprobar", "is_valid_verb": true, "has_object": true, "passes_r08": true}
        ]}
    }
}

test_r08_escalate_invalid_names if {
    count(r08_naming.escalate) > 0 with input as {
        "bpmn": {"activity_naming_analysis": [
            {"id": "a1", "name": "Documento", "language": "es", "first_token": "documento", "is_valid_verb": false, "has_object": false, "passes_r08": false}
        ]}
    }
}

# =============================================================================
# R9 — XOR exclusive
# =============================================================================

test_r09_permit_exclusive_and_complete if {
    r09_xor_exclusive.decision.outcome == "PERMIT" with input as {
        "bpmn": {"xor_sat_analysis": [
            {"gateway_id": "x1", "is_mutually_exclusive": true, "is_complete": true,
             "overlap_conditions": [], "uncovered_conditions": []}
        ]}
    }
}

test_r09_deny_overlap if {
    count(r09_xor_exclusive.deny) > 0 with input as {
        "bpmn": {"xor_sat_analysis": [
            {"gateway_id": "x1", "is_mutually_exclusive": false, "is_complete": true,
             "overlap_conditions": ["cond1_and_cond2_both_true"], "uncovered_conditions": []}
        ]}
    }
}

# =============================================================================
# R10 — Error handlers (material)
# =============================================================================

test_r10_permit_all_handled if {
    r10_error_handlers.decision.outcome == "PERMIT" with input as {
        "bpmn": {"error_events": [
            {"event_id": "e1", "has_boundary_handler": true, "has_escalation_route": false, "is_end_error": false}
        ]}
    }
}

test_r10_escalate_unhandled if {
    count(r10_error_handlers.escalate) > 0 with input as {
        "bpmn": {"error_events": [
            {"event_id": "e1", "has_boundary_handler": false, "has_escalation_route": false, "is_end_error": false}
        ]}
    }
}

# =============================================================================
# R11 — OR gateways (material)
# =============================================================================

test_r11_permit_valid if {
    r11_or_gateways.decision.outcome == "PERMIT" with input as {
        "bpmn": {"or_gateway_analysis": [
            {"gateway_id": "or1", "at_least_one_branch_activates": true, "has_matching_converge": true}
        ]}
    }
}

test_r11_escalate_unguarded if {
    count(r11_or_gateways.escalate) > 0 with input as {
        "bpmn": {"or_gateway_analysis": [
            {"gateway_id": "or1", "at_least_one_branch_activates": false, "has_matching_converge": true}
        ]}
    }
}

# =============================================================================
# R12 — Prose-BPMN similarity
# =============================================================================

test_r12_permit_high_similarity if {
    r12_prose_bpmn.decision.outcome == "PERMIT" with input as {
        "bpmn": {"prose_bpmn_similarity": {
            "overall_cosine": 0.85,
            "section_scores": {
                "proposito": 0.90, "actores": 0.88, "secuencia": 0.82,
                "decisiones": 0.85, "errores_excepciones": 0.80, "salida_kpis": 0.87
            },
            "required_sections_present": 6
        }}
    }
}

test_r12_deny_below_threshold if {
    count(r12_prose_bpmn.deny) > 0 with input as {
        "bpmn": {"prose_bpmn_similarity": {
            "overall_cosine": 0.65,
            "section_scores": {
                "proposito": 0.60, "actores": 0.70, "secuencia": 0.65,
                "decisiones": 0.68, "errores_excepciones": 0.62, "salida_kpis": 0.65
            },
            "required_sections_present": 6
        }}
    }
}

test_r12_deny_missing_section if {
    count(r12_prose_bpmn.deny) > 0 with input as {
        "bpmn": {"prose_bpmn_similarity": {
            "overall_cosine": 0.85,
            "section_scores": {"proposito": 0.85},
            "required_sections_present": 1
        }}
    }
}
