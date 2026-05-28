# R6 — Consistencia de tablas DMN asociadas a gateways XOR
# Package: arhia.pmel.bpmn_lint.r06_dmn
# Source: Catalogo BPMN-Lint v1.0 §4 R6; TR-032 D-35
# Enforces: Si un XOR gateway tiene una DMN asociada, la DMN debe ser consistente, completa y ejecutable.
# Severity: critical
# ARHIA Controls: C15 (parcial), C21
# Gap: G-07 (motor DMN ejecutable pendiente) — hasta cierre, delega en validación mejorada por metadata

package arhia.pmel.bpmn_lint.r06_dmn

import rego.v1

default decision := {"outcome": "AUDIT", "reason": "r06_not_applicable"}

# input.bpmn.xor_with_dmn = [{gateway_id, dmn_id, dmn_metadata, dmn_consistent, dmn_complete}]

inconsistent_dmns contains pair if {
    some pair in input.bpmn.xor_with_dmn
    pair.dmn_consistent == false
}

incomplete_dmns contains pair if {
    some pair in input.bpmn.xor_with_dmn
    pair.dmn_complete == false
}

# DENY: DMN is inconsistent (conflicting rules)
deny[msg] if {
    count(inconsistent_dmns) > 0
    ids := [pair.dmn_id | some pair in inconsistent_dmns]
    msg := sprintf("R6 violation: inconsistent DMN tables (conflicting rules): %v (critical)", [ids])
}

# DENY: DMN is incomplete (input combinations without rule)
deny[msg] if {
    count(incomplete_dmns) > 0
    ids := [pair.dmn_id | some pair in incomplete_dmns]
    msg := sprintf("R6 violation: incomplete DMN tables (missing rules for input combinations): %v (critical)", [ids])
}

# ESCALATE: G-07 still open → full DMN engine not yet integrated; validation is metadata-only
escalate[msg] if {
    input.g07_closed == false
    count(input.bpmn.xor_with_dmn) > 0
    msg := "R6 metadata-only validation applied (G-07 pending motor DMN ejecutable). Consultor must verify DMN logic manually."
}

decision := {"outcome": "PERMIT", "reason": "r06_dmn_consistent_and_complete"} if {
    count(inconsistent_dmns) == 0
    count(incomplete_dmns) == 0
    count(input.bpmn.xor_with_dmn) > 0
}

decision := {"outcome": "PERMIT", "reason": "r06_no_dmn_associated"} if {
    count(input.bpmn.xor_with_dmn) == 0
}

decision := {"outcome": "DENY", "reason": "r06_dmn_issues", "inconsistent": inconsistent_dmns, "incomplete": incomplete_dmns} if {
    total := count(inconsistent_dmns) + count(incomplete_dmns)
    total > 0
}

audit[record] if {
    record := {
        "event": "bpmn_lint_r06_evaluated",
        "xor_with_dmn_count": count(input.bpmn.xor_with_dmn),
        "inconsistent_count": count(inconsistent_dmns),
        "incomplete_count": count(incomplete_dmns),
        "g07_open": input.g07_closed == false,
        "trace_id": input.trace_id
    }
}
