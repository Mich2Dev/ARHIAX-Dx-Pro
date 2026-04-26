# R1 — Gateways balanceados
# Package: arhia.pmel.bpmn_lint.r01_gateways
# Source: Catalogo BPMN-Lint v1.0 §4 R1; TR-032 D-35
# Enforces: Para cada gateway divergente, existe un gateway convergente equivalente que cierra las ramas.
# Severity: critical
# ARHIA Controls: C21 (BPMN-Lint quality gate)

package arhia.pmel.bpmn_lint.r01_gateways

import rego.v1

default decision := {"outcome": "AUDIT", "reason": "r01_not_applicable"}

# Extract gateway balance data from input
# input.bpmn.gateways = [{id, type, direction, pair_id?}, ...]

# Identify divergent gateways (splits)
divergent_gateways contains gw if {
    some gw in input.bpmn.gateways
    gw.direction == "diverging"
    gw.type in {"exclusive", "inclusive", "parallel"}
}

# Identify convergent gateways (joins)
convergent_gateways contains gw if {
    some gw in input.bpmn.gateways
    gw.direction == "converging"
    gw.type in {"exclusive", "inclusive", "parallel"}
}

# Unbalanced divergent gateways: divergent without matching convergent of same type
unbalanced_divergent contains gw_id if {
    some gw in divergent_gateways
    not has_matching_converge(gw)
    gw_id := gw.id
}

has_matching_converge(gw) if {
    some conv in convergent_gateways
    conv.pair_id == gw.id
    conv.type == gw.type
}

# DENY: critical rule — unbalanced gateways block PMEL delivery
deny[msg] if {
    count(unbalanced_divergent) > 0
    msg := sprintf("R1 violation: unbalanced divergent gateways without matching convergent: %v (critical, blocks delivery)", [unbalanced_divergent])
}

# PERMIT: all divergent gateways properly closed
decision := {"outcome": "PERMIT", "reason": "r01_all_gateways_balanced"} if {
    count(divergent_gateways) > 0
    count(unbalanced_divergent) == 0
}

# PERMIT: no gateways in this BPMN
decision := {"outcome": "PERMIT", "reason": "r01_no_gateways_present"} if {
    count(input.bpmn.gateways) == 0
}

decision := {"outcome": "DENY", "reason": "r01_unbalanced", "gateways": unbalanced_divergent} if {
    count(unbalanced_divergent) > 0
}

# AUDIT
audit[record] if {
    record := {
        "event": "bpmn_lint_r01_evaluated",
        "divergent_count": count(divergent_gateways),
        "convergent_count": count(convergent_gateways),
        "unbalanced": unbalanced_divergent,
        "trace_id": input.trace_id
    }
}
