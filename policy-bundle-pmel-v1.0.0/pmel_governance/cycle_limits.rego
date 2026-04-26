# PMEL Cycle Limits — Agent iteration caps
# Package: arhia.pmel.governance.cycle_limits
# Source: Paso 2 Prompts §1.5 (Capture), §4.5 (TO-BE); TR-032 D-10
# Enforces: Capture-Agent max 5 ciclos antes de escalar; TO-BE max 3 ciclos con Lint antes de unable_to_resolve_critical
# ARHIA Controls: C18 (kill-switch / pausa por agente)

package arhia.pmel.governance.cycle_limits

import rego.v1

default decision := {"outcome": "AUDIT", "reason": "cycle_limits_not_triggered"}

# Limits per component
limits := {
    "capture_agent": 5,
    "visual_interpreter": 1,  # one-shot
    "to_be_generator": 3,
    "bpmn_lint_agent": 3  # ciclos Generator↔Lint
}

# input.execution = {
#   "component": "to_be_generator",
#   "current_cycle": 3,
#   "total_cycles_elapsed": 3,
#   "last_outcome": "failed"
# }

current_component := input.execution.component
current_cycle := input.execution.current_cycle
limit_for_component := limits[current_component]

# DENY: request to continue past hard limit
deny[msg] if {
    current_component in object.keys(limits)
    current_cycle >= limit_for_component
    input.execution.request_another_cycle == true
    msg := sprintf("Cycle limit reached: component %v at cycle %v of max %v — cannot continue (D-10, C18)", [current_component, current_cycle, limit_for_component])
}

# SUSPEND: component reached limit with failed outcome → kill-switch
suspend[msg] if {
    current_component in object.keys(limits)
    current_cycle >= limit_for_component
    input.execution.last_outcome == "failed"
    msg := sprintf("Component %v SUSPENDED: %v cycles exhausted without resolution", [current_component, limit_for_component])
}

# ESCALATE: approaching limit (last cycle available)
escalate[msg] if {
    current_component in object.keys(limits)
    current_cycle == (limit_for_component - 1)
    msg := sprintf("Component %v on final cycle (%v of %v) — prepare escalation to Consultor if this fails", [current_component, current_cycle, limit_for_component])
}

# PERMIT: within limits
decision := {"outcome": "PERMIT", "reason": "within_cycle_limit", "cycle": current_cycle, "max": limit_for_component} if {
    current_component in object.keys(limits)
    current_cycle < limit_for_component
}

decision := {"outcome": "DENY", "reason": "cycle_limit_exceeded", "component": current_component, "cycle": current_cycle, "max": limit_for_component} if {
    current_component in object.keys(limits)
    current_cycle >= limit_for_component
    input.execution.request_another_cycle == true
}

decision := {"outcome": "SUSPEND", "reason": "cycle_exhausted_with_failure", "component": current_component} if {
    current_component in object.keys(limits)
    current_cycle >= limit_for_component
    input.execution.last_outcome == "failed"
}

audit[record] if {
    record := {
        "event": "cycle_limit_evaluated",
        "component": current_component,
        "current_cycle": current_cycle,
        "limit": limit_for_component,
        "last_outcome": input.execution.last_outcome,
        "trace_id": input.trace_id
    }
}
