# R4 — Lanes con al menos una actividad o evento
# Package: arhia.pmel.bpmn_lint.r04_lanes
# Source: Catalogo BPMN-Lint v1.0 §4 R4; TR-032 D-35
# Enforces: Toda lane declarada debe contener al menos un elemento (actividad, evento, o gateway).
# Severity: material (not critical)
# ARHIA Controls: C21

package arhia.pmel.bpmn_lint.r04_lanes

import rego.v1

default decision := {"outcome": "AUDIT", "reason": "r04_not_applicable"}

# input.bpmn.lanes = [{id, name, element_count}]

empty_lanes contains lane_id if {
    some lane in input.bpmn.lanes
    lane.element_count == 0
    lane_id := lane.id
}

# R4 is material (not critical): escalate instead of deny
escalate[msg] if {
    count(empty_lanes) > 0
    msg := sprintf("R4 material warning: empty lanes detected: %v — Consultor should remove or populate", [empty_lanes])
}

decision := {"outcome": "PERMIT", "reason": "r04_all_lanes_populated"} if {
    count(empty_lanes) == 0
}

decision := {"outcome": "ESCALATE", "reason": "r04_empty_lanes", "empty_lanes": empty_lanes} if {
    count(empty_lanes) > 0
}

# MODIFY: propose removing empty lanes automatically in non-regulated tiers
modify[action] if {
    count(empty_lanes) > 0
    input.deployment.tier in {"lite"}
    action := {
        "operation": "remove_empty_lanes",
        "targets": empty_lanes,
        "requires_consultant_confirmation": true
    }
}

audit[record] if {
    record := {
        "event": "bpmn_lint_r04_evaluated",
        "total_lanes": count(input.bpmn.lanes),
        "empty_lanes": empty_lanes,
        "trace_id": input.trace_id
    }
}
