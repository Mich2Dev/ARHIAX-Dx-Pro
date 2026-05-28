# R2 — Alcanzabilidad de eventos de fin
# Package: arhia.pmel.bpmn_lint.r02_reachability
# Source: Catalogo BPMN-Lint v1.0 §4 R2; TR-032 D-35
# Enforces: Desde cada evento de inicio debe existir al menos un camino que conduzca a un evento de fin.
# Severity: critical
# ARHIA Controls: C21, C35

package arhia.pmel.bpmn_lint.r02_reachability

import rego.v1

default decision := {"outcome": "AUDIT", "reason": "r02_not_applicable"}

# input.bpmn.reachability_analysis = {
#   "start_events": [...],
#   "end_events": [...],
#   "unreachable_starts": [...],  # starts that cannot reach any end
#   "unreachable_ends": [...]     # ends that cannot be reached from any start
# }

unreachable_starts := input.bpmn.reachability_analysis.unreachable_starts
unreachable_ends := input.bpmn.reachability_analysis.unreachable_ends

# DENY: critical — if any start event cannot reach any end, process cannot complete
deny[msg] if {
    count(unreachable_starts) > 0
    msg := sprintf("R2 violation: start events cannot reach any end event: %v (process cannot complete)", [unreachable_starts])
}

# DENY: critical — if any end event is unreachable from all starts, process has dead code
deny[msg] if {
    count(unreachable_ends) > 0
    msg := sprintf("R2 violation: end events unreachable from any start: %v (dead code)", [unreachable_ends])
}

decision := {"outcome": "PERMIT", "reason": "r02_all_reachable"} if {
    count(unreachable_starts) == 0
    count(unreachable_ends) == 0
    count(input.bpmn.reachability_analysis.start_events) > 0
    count(input.bpmn.reachability_analysis.end_events) > 0
}

decision := {"outcome": "DENY", "reason": "r02_unreachable", "unreachable_starts": unreachable_starts, "unreachable_ends": unreachable_ends} if {
    total := count(unreachable_starts) + count(unreachable_ends)
    total > 0
}

# ESCALATE: no start or no end events present at all
escalate[msg] if {
    count(input.bpmn.reachability_analysis.start_events) == 0
    msg := "R2: no start events defined — escalate to Consultor for process validation"
}

escalate[msg] if {
    count(input.bpmn.reachability_analysis.end_events) == 0
    msg := "R2: no end events defined — escalate to Consultor for process validation"
}

audit[record] if {
    record := {
        "event": "bpmn_lint_r02_evaluated",
        "start_count": count(input.bpmn.reachability_analysis.start_events),
        "end_count": count(input.bpmn.reachability_analysis.end_events),
        "unreachable_starts": unreachable_starts,
        "unreachable_ends": unreachable_ends,
        "trace_id": input.trace_id
    }
}
