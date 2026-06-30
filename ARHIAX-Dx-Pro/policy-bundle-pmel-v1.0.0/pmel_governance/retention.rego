# PMEL Retention Enforcement
# Package: arhia.pmel.governance.retention
# Source: Paso 6 §3.8, §4.6 (retención escalonada); TR-035 R-11, R-17; TR-036 §2.3
# Enforces: Retention windows per data type. Actions to trigger automatic D3 decommissioning when windows expire.
# ARHIA Controls: C12 (limitación temporal retención)

package arhia.pmel.governance.retention

import rego.v1
import data.thresholds

default decision := {"outcome": "AUDIT", "reason": "retention_check_not_applicable"}

# Retention windows (days)
retention_windows := {
    "recordings_original": 30,
    "transcripts_pseudonymized": thresholds.documental_retention_days,  # default e.g. 5 years externalized
    "llm_prompts": 30,
    "llm_responses": 30,
    "bpmn_artifacts_intermediate": 30,
    "telemetry_logs": 90,
    "artefacts_delivered_signed": thresholds.documental_retention_days,
    "aibom_metadata": thresholds.documental_retention_days
}

# input.retention_check = {
#   "data_type": "recordings_original",
#   "created_at": "2026-03-01T10:00:00Z",
#   "age_days": 35,
#   "deployment_id": "..."
# }

window_for_type := retention_windows[input.retention_check.data_type]
age_days := input.retention_check.age_days

within_window if age_days < window_for_type

expired if age_days >= window_for_type

# PERMIT: data within retention window, normal access
decision := {"outcome": "PERMIT", "reason": "within_retention_window", "data_type": input.retention_check.data_type, "age": age_days, "window": window_for_type} if {
    input.retention_check.data_type in object.keys(retention_windows)
    within_window
}

# DENY: accessing data past retention window (except legitimate auditor access)
deny[msg] if {
    expired
    not input.retention_check.is_auditor_access
    msg := sprintf("Retention violation: accessing %v data aged %v days past window of %v days (C12)", [input.retention_check.data_type, age_days, window_for_type])
}

# MODIFY: trigger automatic D3 decommissioning when expired
modify[action] if {
    expired
    input.retention_check.data_type in {"recordings_original", "llm_prompts", "llm_responses", "bpmn_artifacts_intermediate"}
    action := {
        "operation": "trigger_d3_decommissioning",
        "data_type": input.retention_check.data_type,
        "deployment_id": input.retention_check.deployment_id,
        "rationale": "Retention window expired — auto-trigger TR-036 D3 protocol"
    }
}

# ESCALATE: documental retention type expired — needs legal review before decommissioning
escalate[msg] if {
    expired
    input.retention_check.data_type in {"transcripts_pseudonymized", "artefacts_delivered_signed", "aibom_metadata"}
    msg := sprintf("Documental retention window expired for %v — Asesor Legal review before D3 (R-17)", [input.retention_check.data_type])
}

# AUDIT all retention checks
audit[record] if {
    record := {
        "event": "retention_evaluated",
        "data_type": input.retention_check.data_type,
        "age_days": age_days,
        "window_days": window_for_type,
        "expired": expired,
        "deployment_id": input.retention_check.deployment_id,
        "trace_id": input.trace_id
    }
}
