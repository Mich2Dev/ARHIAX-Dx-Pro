# PMEL Autonomy Level Enforcement
# Package: arhia.pmel.base.autonomy
# Source: SDX-01 v1.0 §6.2 (A-Scale), TR-032 D-28
# Enforces: PMEL operates fixed at A2; never A3 or above.
# ARHIA Controls: C17 (A-Scale limits)

package arhia.pmel.base.autonomy

import rego.v1

# Default: deny unspecified autonomy requests
default allow := false
default decision := {"outcome": "DENY", "reason": "unspecified_autonomy_request"}

# Allowed autonomy levels for PMEL components
allowed_levels := {
    "capture_agent": "A2",
    "visual_interpreter": "A2",
    "to_be_generator": "A2",
    "bpmn_lint_agent": "A2",
    "simulator": "A1",
    "whisper": "A1",
    "reviewer_ux": "A0",
    "export": "A0",
    "cliente_ux_pro_enterprise": "A0",
    "dmn_engine": "A2",
    "crypto_participant": "A2",
    "rgc_hypothesis_builder": "A2",
    "rgc_deep_research_contraster": "A2",
    "adaptive_question_bank": "A2",
    "multi_role_scoring": "A2",
    "psychometrics": "A2",
    "irr_reliability": "A2",
    "bayesian_synthesis": "A2",
    "executive_qa": "A2",
    "diagnostic_intelligence": "A2",
    "diagnostic_fusion_cycle": "A2",
    "executive_report": "A2",
    "report_renderer": "A2",
    "report_exporter": "A2",
    "diagnostic_case_runner": "A2",
    "case_approval": "A2"
}

# PERMIT: agent operates at declared level matching allowed
allow if {
    input.agent.component in object.keys(allowed_levels)
    input.agent.autonomy_level == allowed_levels[input.agent.component]
}

decision := {"outcome": "PERMIT", "reason": "autonomy_within_policy"} if {
    allow
}

# DENY: agent attempting to escalate above A2
deny[msg] if {
    input.agent.autonomy_level in {"A3", "A4"}
    msg := sprintf("PMEL autonomy violation: component %v requested level %v; maximum allowed is A2 (D-28, C17)", [input.agent.component, input.agent.autonomy_level])
}

# DENY: component operating at unauthorized level
deny[msg] if {
    input.agent.component in object.keys(allowed_levels)
    input.agent.autonomy_level != allowed_levels[input.agent.component]
    not input.agent.autonomy_level in {"A3", "A4"}
    msg := sprintf("PMEL autonomy mismatch: component %v declared %v; policy requires %v (SDX-01 §6.2)", [input.agent.component, input.agent.autonomy_level, allowed_levels[input.agent.component]])
}

# SUSPEND: repeated policy violations from same component
suspend[msg] if {
    input.agent.violation_count >= 3
    msg := sprintf("PMEL component %v SUSPENDED: repeated autonomy violations (count=%v)", [input.agent.component, input.agent.violation_count])
}

# ESCALATE: unknown component not enumerated in allowed_levels
escalate[msg] if {
    not input.agent.component in object.keys(allowed_levels)
    msg := sprintf("Unknown PMEL component '%v' requests autonomy decision — escalate to Technical Reviewer", [input.agent.component])
}

# AUDIT: always log autonomy decisions for SDX-01 traceability
audit[record] if {
    record := {
        "event": "autonomy_decision",
        "component": input.agent.component,
        "requested_level": input.agent.autonomy_level,
        "policy_level": allowed_levels[input.agent.component],
        "timestamp": input.timestamp,
        "trace_id": input.trace_id
    }
}
