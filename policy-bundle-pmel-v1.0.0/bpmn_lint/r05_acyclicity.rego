# R5 — Acyclicidad del grafo de control (o loops con salida garantizada)
# Package: arhia.pmel.bpmn_lint.r05_acyclicity
# Source: Catalogo BPMN-Lint v1.0 §4 R5; TR-032 D-35
# Enforces: El grafo no debe contener ciclos, salvo que cada ciclo incluya al menos una rama de salida (via XOR con condición).
# Severity: critical
# ARHIA Controls: C21, C35

package arhia.pmel.bpmn_lint.r05_acyclicity

import rego.v1

default decision := {"outcome": "AUDIT", "reason": "r05_not_applicable"}

# input.bpmn.tarjan_analysis = {
#   "strongly_connected_components": [{"nodes": [...], "has_exit": true|false, "exit_gateway": "..."}],
#   "total_sccs": N,
#   "sccs_without_exit": N
# }

sccs_without_exit := input.bpmn.tarjan_analysis.sccs_without_exit

# DENY: critical — cycles without exit cause deadlock
deny[msg] if {
    sccs_without_exit > 0
    bad_sccs := [scc | some scc in input.bpmn.tarjan_analysis.strongly_connected_components; scc.has_exit == false]
    msg := sprintf("R5 violation: %v cycle(s) without guaranteed exit: %v (deadlock risk, critical)", [sccs_without_exit, bad_sccs])
}

decision := {"outcome": "PERMIT", "reason": "r05_acyclic_or_all_cycles_have_exits"} if {
    sccs_without_exit == 0
}

decision := {"outcome": "DENY", "reason": "r05_cycles_without_exit", "sccs_without_exit": sccs_without_exit} if {
    sccs_without_exit > 0
}

audit[record] if {
    record := {
        "event": "bpmn_lint_r05_evaluated",
        "total_sccs": input.bpmn.tarjan_analysis.total_sccs,
        "sccs_without_exit": sccs_without_exit,
        "trace_id": input.trace_id
    }
}
