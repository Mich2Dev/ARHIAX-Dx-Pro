# R10 — Eventos de error con handler o escalamiento definido
# Package: arhia.pmel.bpmn_lint.r10_error_handlers
# Source: Catalogo BPMN-Lint v1.0 §4 R10; TR-032 D-35
# Enforces: Todo evento de error intermedio debe tener un boundary event handler o ruta de escalamiento explícita.
# Severity: material
# ARHIA Controls: C21, C32

package arhia.pmel.bpmn_lint.r10_error_handlers

import rego.v1

default decision := {"outcome": "AUDIT", "reason": "r10_not_applicable"}

# input.bpmn.error_events = [{event_id, has_boundary_handler, has_escalation_route, is_end_error}]

# Error events without any handler or escalation (except end-error which is valid)
unhandled_errors contains event_id if {
    some ev in input.bpmn.error_events
    ev.is_end_error == false
    ev.has_boundary_handler == false
    ev.has_escalation_route == false
    event_id := ev.event_id
}

# Material severity: escalate, don't deny
escalate[msg] if {
    count(unhandled_errors) > 0
    msg := sprintf("R10 material warning: error events without handler or escalation: %v — Consultor should define error handling", [unhandled_errors])
}

decision := {"outcome": "PERMIT", "reason": "r10_all_errors_handled"} if {
    count(unhandled_errors) == 0
}

decision := {"outcome": "ESCALATE", "reason": "r10_unhandled_errors", "unhandled": unhandled_errors} if {
    count(unhandled_errors) > 0
}

# MODIFY: propose adding generic error handler routing to terminate event
modify[action] if {
    count(unhandled_errors) > 0
    action := {
        "operation": "suggest_add_error_handler",
        "targets": unhandled_errors,
        "requires_consultant_confirmation": true
    }
}

audit[record] if {
    record := {
        "event": "bpmn_lint_r10_evaluated",
        "total_error_events": count(input.bpmn.error_events),
        "unhandled_count": count(unhandled_errors),
        "trace_id": input.trace_id
    }
}
