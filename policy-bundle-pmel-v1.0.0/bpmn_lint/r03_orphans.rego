# R3 — Ausencia de actividades huérfanas
# Package: arhia.pmel.bpmn_lint.r03_orphans
# Source: Catalogo BPMN-Lint v1.0 §4 R3; TR-032 D-35
# Enforces: Toda actividad debe tener al menos un flujo entrante y uno saliente (salvo actividades con start/end events compensating).
# Severity: critical
# ARHIA Controls: C21

package arhia.pmel.bpmn_lint.r03_orphans

import rego.v1

default decision := {"outcome": "AUDIT", "reason": "r03_not_applicable"}

# input.bpmn.activities = [{id, name, incoming_flows, outgoing_flows, is_compensation}]

orphan_activities contains act_id if {
    some act in input.bpmn.activities
    act.is_compensation == false
    count(act.incoming_flows) == 0
    act_id := act.id
}

orphan_activities contains act_id if {
    some act in input.bpmn.activities
    act.is_compensation == false
    count(act.outgoing_flows) == 0
    act_id := act.id
}

deny[msg] if {
    count(orphan_activities) > 0
    msg := sprintf("R3 violation: orphan activities without incoming or outgoing flows: %v (critical)", [orphan_activities])
}

decision := {"outcome": "PERMIT", "reason": "r03_no_orphans"} if {
    count(orphan_activities) == 0
    count(input.bpmn.activities) > 0
}

decision := {"outcome": "DENY", "reason": "r03_orphans", "orphans": orphan_activities} if {
    count(orphan_activities) > 0
}

audit[record] if {
    record := {
        "event": "bpmn_lint_r03_evaluated",
        "total_activities": count(input.bpmn.activities),
        "orphans": orphan_activities,
        "trace_id": input.trace_id
    }
}
