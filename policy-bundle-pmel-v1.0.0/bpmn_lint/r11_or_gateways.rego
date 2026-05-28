# R11 — Uso correcto de gateway inclusivo (OR) con rama garantizada y cierre
# Package: arhia.pmel.bpmn_lint.r11_or_gateways
# Source: Catalogo BPMN-Lint v1.0 §4 R11; TR-032 D-35
# Enforces: Todo OR divergente debe: (a) garantizar que al menos una rama se active en cualquier input; (b) tener un OR convergente que cierre.
# Severity: material
# ARHIA Controls: C21

package arhia.pmel.bpmn_lint.r11_or_gateways

import rego.v1

default decision := {"outcome": "AUDIT", "reason": "r11_not_applicable"}

# input.bpmn.or_gateway_analysis = [
#   {gateway_id, at_least_one_branch_activates: bool, has_matching_converge: bool}
# ]

unguarded_or contains g_id if {
    some g in input.bpmn.or_gateway_analysis
    g.at_least_one_branch_activates == false
    g_id := g.gateway_id
}

unclosed_or contains g_id if {
    some g in input.bpmn.or_gateway_analysis
    g.has_matching_converge == false
    g_id := g.gateway_id
}

# Material severity: escalate
escalate[msg] if {
    count(unguarded_or) > 0
    msg := sprintf("R11 material warning: OR gateways without guaranteed branch activation: %v — process may stall", [unguarded_or])
}

escalate[msg] if {
    count(unclosed_or) > 0
    msg := sprintf("R11 material warning: OR gateways without matching convergent: %v — parallel tokens may leak", [unclosed_or])
}

decision := {"outcome": "PERMIT", "reason": "r11_all_or_gateways_valid"} if {
    count(unguarded_or) == 0
    count(unclosed_or) == 0
    count(input.bpmn.or_gateway_analysis) > 0
}

decision := {"outcome": "PERMIT", "reason": "r11_no_or_gateways"} if {
    count(input.bpmn.or_gateway_analysis) == 0
}

decision := {"outcome": "ESCALATE", "reason": "r11_or_issues", "unguarded": unguarded_or, "unclosed": unclosed_or} if {
    total := count(unguarded_or) + count(unclosed_or)
    total > 0
}

audit[record] if {
    record := {
        "event": "bpmn_lint_r11_evaluated",
        "total_or_gateways": count(input.bpmn.or_gateway_analysis),
        "unguarded": unguarded_or,
        "unclosed": unclosed_or,
        "trace_id": input.trace_id
    }
}
