package arhia.pmel.decommissioning_test

import data.arhia.pmel.decommissioning.triggers
import data.arhia.pmel.decommissioning.crypto_shred

# =============================================================================
# Triggers
# =============================================================================

test_trigger_d1_total if {
    triggers.decision.outcome == "PERMIT" with input as {
        "classify": {
            "raw_trigger_type": "revocation",
            "revocation_scope": "full",
            "incident_contained": true
        },
        "g08_closed": false
    }
    triggers.decision.canonical_type == "D1_revocation_total" with input as {
        "classify": {"raw_trigger_type": "revocation", "revocation_scope": "full", "incident_contained": true},
        "g08_closed": false
    }
}

test_trigger_d1_partial_escalates_with_g08_open if {
    count(triggers.escalate) > 0 with input as {
        "classify": {"raw_trigger_type": "revocation", "revocation_scope": "participant", "incident_contained": true},
        "g08_closed": false
    }
}

test_trigger_d4_incident_72h_sla if {
    triggers.decision.outcome == "PERMIT" with input as {
        "classify": {
            "raw_trigger_type": "incident",
            "regulatory_order": false,
            "incident_contained": true
        },
        "g08_closed": true
    }
    triggers.decision.sla_days == 3 with input as {
        "classify": {"raw_trigger_type": "incident", "regulatory_order": false, "incident_contained": true},
        "g08_closed": true
    }
}

test_trigger_d4_suspend_if_not_contained if {
    count(triggers.suspend) > 0 with input as {
        "classify": {"raw_trigger_type": "incident", "regulatory_order": false, "incident_contained": false},
        "g08_closed": true
    }
}

# =============================================================================
# Crypto Shred Pre-conditions
# =============================================================================

full_preconditions_valid := {
    "precondition_check": {
        "case_id": "DECOM-2026-0042",
        "evidence_01_signed": true,
        "evidence_02_signed": true,
        "evidence_03_signed": true,
        "evidence_04a_signed": true,
        "evidence_04b_signed": true,
        "evidence_04c_signed": true,
        "evidence_05a_signed": true,
        "evidence_05b_signed_or_waiver": true,
        "kms_deletion_window_days": 7,
        "regulatory_preservation_required": false,
        "preservation_executed": false,
        "dry_run": false
    }
}

test_crypto_shred_permit_all_met if {
    crypto_shred.decision.outcome == "PERMIT" with input as full_preconditions_valid
}

test_crypto_shred_deny_missing_evidence if {
    # Shallow copy with evidence_05a removed
    invalid_input := {
        "precondition_check": {
            "case_id": "DECOM-2026-0043",
            "evidence_01_signed": true,
            "evidence_02_signed": true,
            "evidence_03_signed": true,
            "evidence_04a_signed": true,
            "evidence_04b_signed": true,
            "evidence_04c_signed": true,
            "evidence_05a_signed": false,
            "evidence_05b_signed_or_waiver": false,
            "kms_deletion_window_days": 7,
            "regulatory_preservation_required": false,
            "preservation_executed": false,
            "dry_run": false
        }
    }
    count(crypto_shred.deny) > 0 with input as invalid_input
}

test_crypto_shred_deny_window_too_short if {
    short_window := {
        "precondition_check": {
            "case_id": "DECOM-2026-0044",
            "evidence_01_signed": true, "evidence_02_signed": true, "evidence_03_signed": true,
            "evidence_04a_signed": true, "evidence_04b_signed": true, "evidence_04c_signed": true,
            "evidence_05a_signed": true, "evidence_05b_signed_or_waiver": true,
            "kms_deletion_window_days": 3,
            "regulatory_preservation_required": false, "preservation_executed": false, "dry_run": false
        }
    }
    count(crypto_shred.deny) > 0 with input as short_window
}

test_crypto_shred_deny_preservation_required_not_executed if {
    preservation_pending := {
        "precondition_check": {
            "case_id": "DECOM-2026-0045",
            "evidence_01_signed": true, "evidence_02_signed": true, "evidence_03_signed": true,
            "evidence_04a_signed": true, "evidence_04b_signed": true, "evidence_04c_signed": true,
            "evidence_05a_signed": true, "evidence_05b_signed_or_waiver": true,
            "kms_deletion_window_days": 7,
            "regulatory_preservation_required": true,
            "preservation_executed": false, "dry_run": false
        }
    }
    count(crypto_shred.deny) > 0 with input as preservation_pending
}

test_crypto_shred_modify_dry_run if {
    dry_run_input := {
        "precondition_check": {
            "case_id": "DECOM-2026-0046",
            "evidence_01_signed": true, "evidence_02_signed": true, "evidence_03_signed": true,
            "evidence_04a_signed": true, "evidence_04b_signed": true, "evidence_04c_signed": true,
            "evidence_05a_signed": true, "evidence_05b_signed_or_waiver": true,
            "kms_deletion_window_days": 7,
            "regulatory_preservation_required": false, "preservation_executed": false,
            "dry_run": true
        }
    }
    count(crypto_shred.modify) > 0 with input as dry_run_input
}
