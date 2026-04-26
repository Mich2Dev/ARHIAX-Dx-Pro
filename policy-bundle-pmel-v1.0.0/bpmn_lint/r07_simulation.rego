# R7 — Simulación probe sin deadlock ni livelock
# Package: arhia.pmel.bpmn_lint.r07_simulation
# Source: Catalogo BPMN-Lint v1.0 §4 R7; TR-032 D-35
# Enforces: Sobre 100 simulaciones determinísticas (Simulator SM-03), ≥98 deben completar, 0 deadlocks.
# Severity: critical
# ARHIA Controls: C35

package arhia.pmel.bpmn_lint.r07_simulation

import rego.v1

default decision := {"outcome": "AUDIT", "reason": "r07_not_applicable"}

# input.bpmn.simulation_result = {
#   "runs_total": 100,
#   "runs_completed": 99,
#   "runs_deadlocked": 0,
#   "runs_livelocked": 0,
#   "runs_errored": 1,
#   "success_threshold": 0.98
# }

sim := input.bpmn.simulation_result

success_rate := sim.runs_completed / sim.runs_total

deadlock_count := sim.runs_deadlocked
livelock_count := sim.runs_livelocked

# DENY: any deadlock is immediate fail (critical)
deny[msg] if {
    deadlock_count > 0
    msg := sprintf("R7 violation: %v deadlock(s) detected in simulation — process can hang (critical)", [deadlock_count])
}

# DENY: any livelock is immediate fail
deny[msg] if {
    livelock_count > 0
    msg := sprintf("R7 violation: %v livelock(s) detected — process loops without progress (critical)", [livelock_count])
}

# DENY: success rate below threshold
deny[msg] if {
    success_rate < sim.success_threshold
    msg := sprintf("R7 violation: success rate %.2f below threshold %.2f (completed %v of %v)", [success_rate, sim.success_threshold, sim.runs_completed, sim.runs_total])
}

decision := {"outcome": "PERMIT", "reason": "r07_simulation_passed", "success_rate": success_rate} if {
    deadlock_count == 0
    livelock_count == 0
    success_rate >= sim.success_threshold
}

decision := {"outcome": "DENY", "reason": "r07_simulation_failed", "success_rate": success_rate, "deadlocks": deadlock_count, "livelocks": livelock_count} if {
    any_fail
}

any_fail if deadlock_count > 0
any_fail if livelock_count > 0
any_fail if success_rate < sim.success_threshold

audit[record] if {
    record := {
        "event": "bpmn_lint_r07_evaluated",
        "simulation": sim,
        "success_rate": success_rate,
        "trace_id": input.trace_id
    }
}
