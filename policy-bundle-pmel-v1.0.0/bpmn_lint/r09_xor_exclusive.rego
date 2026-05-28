# R9 — Condiciones de XOR mutuamente excluyentes y completas
# Package: arhia.pmel.bpmn_lint.r09_xor_exclusive
# Source: Catalogo BPMN-Lint v1.0 §4 R9; TR-032 D-35
# Enforces: Las condiciones de salida de un XOR gateway deben ser mutuamente excluyentes (no solapan) y completas (cubren todos los inputs posibles).
# Severity: critical
# ARHIA Controls: C15 (parcial), C21
# Pre-computed by Lint-Agent using Z3/SAT solver

package arhia.pmel.bpmn_lint.r09_xor_exclusive

import rego.v1

default decision := {"outcome": "AUDIT", "reason": "r09_not_applicable"}

# input.bpmn.xor_sat_analysis = [
#   {gateway_id, is_mutually_exclusive: bool, is_complete: bool, overlap_conditions: [...], uncovered_conditions: [...]}
# ]

non_exclusive_xors contains entry if {
    some entry in input.bpmn.xor_sat_analysis
    entry.is_mutually_exclusive == false
}

incomplete_xors contains entry if {
    some entry in input.bpmn.xor_sat_analysis
    entry.is_complete == false
}

deny[msg] if {
    count(non_exclusive_xors) > 0
    ids := [e.gateway_id | some e in non_exclusive_xors]
    msg := sprintf("R9 violation: XOR gateways with overlapping conditions (non-exclusive): %v (critical, ambiguous execution)", [ids])
}

deny[msg] if {
    count(incomplete_xors) > 0
    ids := [e.gateway_id | some e in incomplete_xors]
    msg := sprintf("R9 violation: XOR gateways with incomplete conditions (uncovered inputs): %v (critical, undefined behavior)", [ids])
}

decision := {"outcome": "PERMIT", "reason": "r09_xor_exclusive_and_complete"} if {
    count(non_exclusive_xors) == 0
    count(incomplete_xors) == 0
    count(input.bpmn.xor_sat_analysis) > 0
}

decision := {"outcome": "PERMIT", "reason": "r09_no_xor_gateways"} if {
    count(input.bpmn.xor_sat_analysis) == 0
}

decision := {"outcome": "DENY", "reason": "r09_xor_issues", "non_exclusive": non_exclusive_xors, "incomplete": incomplete_xors} if {
    total := count(non_exclusive_xors) + count(incomplete_xors)
    total > 0
}

audit[record] if {
    record := {
        "event": "bpmn_lint_r09_evaluated",
        "total_xor_analyzed": count(input.bpmn.xor_sat_analysis),
        "non_exclusive_count": count(non_exclusive_xors),
        "incomplete_count": count(incomplete_xors),
        "trace_id": input.trace_id
    }
}
