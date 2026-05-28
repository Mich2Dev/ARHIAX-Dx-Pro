# PMEL Decommissioning — Crypto-Shred pre-conditions (Paso 7)
# Package: arhia.pmel.decommissioning.crypto_shred
# Source: TR-036 §3.7 (Paso 7 borrado criptográfico); D-61 (KMS key destruction is primary method)
# Enforces: Crypto-shred cannot execute unless all prior steps (1-5) have signed evidences.
#           KMS deletion window must be >= 7 days (AWS minimum, cannot be reduced).
# ARHIA Controls: C36

package arhia.pmel.decommissioning.crypto_shred

import rego.v1

default decision := {"outcome": "DENY", "reason": "crypto_shred_preconditions_not_met"}

# input.precondition_check = {
#   "case_id": "DECOM-2026-0042",
#   "evidence_01_signed": true,
#   "evidence_02_signed": true,
#   "evidence_03_signed": true,
#   "evidence_04a_signed": true,
#   "evidence_04b_signed": true,
#   "evidence_04c_signed": true,
#   "evidence_05a_signed": true,
#   "evidence_05b_signed_or_waiver": true,
#   "kms_deletion_window_days": 7,
#   "regulatory_preservation_required": false,
#   "preservation_executed": false,
#   "dry_run": false
# }

required_evidences := {
    "evidence_01_signed",
    "evidence_02_signed",
    "evidence_03_signed",
    "evidence_04a_signed",
    "evidence_04b_signed",
    "evidence_04c_signed",
    "evidence_05a_signed",
    "evidence_05b_signed_or_waiver"
}

all_evidences_signed if {
    every ev in required_evidences {
        input.precondition_check[ev] == true
    }
}

# DENY: any evidence missing
deny[msg] if {
    missing := [ev | some ev in required_evidences; input.precondition_check[ev] != true]
    count(missing) > 0
    msg := sprintf("Crypto-shred blocked: missing signed evidences from prior steps: %v (TR-036 §3)", [missing])
}

# DENY: KMS deletion window below AWS minimum of 7 days
deny[msg] if {
    input.precondition_check.kms_deletion_window_days < 7
    msg := sprintf("Crypto-shred blocked: KMS deletion window %v days < 7 days AWS minimum (TR-036 §3.7)", [input.precondition_check.kms_deletion_window_days])
}

# DENY: regulatory preservation required but not yet executed
deny[msg] if {
    input.precondition_check.regulatory_preservation_required == true
    input.precondition_check.preservation_executed == false
    msg := "Crypto-shred blocked: D4 preservation order active but preservation not yet executed (TR-036 §4.2)"
}

# PERMIT: all preconditions met, crypto_shred may proceed
decision := {
    "outcome": "PERMIT",
    "reason": "crypto_shred_preconditions_satisfied",
    "case_id": input.precondition_check.case_id,
    "kms_deletion_window_days": input.precondition_check.kms_deletion_window_days
} if {
    all_evidences_signed
    input.precondition_check.kms_deletion_window_days >= 7
    preservation_ok
}

preservation_ok if input.precondition_check.regulatory_preservation_required == false
preservation_ok if {
    input.precondition_check.regulatory_preservation_required == true
    input.precondition_check.preservation_executed == true
}

decision := {"outcome": "DENY", "reason": "crypto_shred_preconditions_failed"} if {
    not all_evidences_signed
}

decision := {"outcome": "DENY", "reason": "kms_window_too_short"} if {
    input.precondition_check.kms_deletion_window_days < 7
}

decision := {"outcome": "DENY", "reason": "preservation_required_not_executed"} if {
    input.precondition_check.regulatory_preservation_required == true
    input.precondition_check.preservation_executed == false
}

# MODIFY: if dry_run flag requested, convert to verify-only
modify[action] if {
    input.precondition_check.dry_run == true
    action := {
        "operation": "dry_run_only",
        "skip_kms_schedule_deletion": true,
        "emit_plan_report": true
    }
}

# AUDIT every crypto_shred evaluation (high-stakes regulatory evidence)
audit[record] if {
    record := {
        "event": "crypto_shred_preconditions_evaluated",
        "case_id": input.precondition_check.case_id,
        "all_evidences_signed": all_evidences_signed,
        "kms_window_days": input.precondition_check.kms_deletion_window_days,
        "preservation_ok": preservation_ok,
        "dry_run": input.precondition_check.dry_run,
        "timestamp": input.timestamp,
        "trace_id": input.trace_id
    }
}
