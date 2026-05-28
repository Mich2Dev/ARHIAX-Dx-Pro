package arhia.pmel.governance_test

import data.arhia.pmel.governance.to_be_prohibitions
import data.arhia.pmel.governance.cycle_limits
import data.arhia.pmel.governance.consent_gates
import data.arhia.pmel.governance.sensitive_data
import data.arhia.pmel.governance.retention

# =============================================================================
# TO-BE Prohibitions (P1-P4)
# =============================================================================

test_tobe_permit_clean if {
    to_be_prohibitions.decision.outcome == "PERMIT" with input as {
        "to_be": {
            "added_activities": [],
            "removed_activities": [],
            "technology_proposals": [],
            "headcount_changes": [],
            "findings": [],
            "regulatory_controls_mapped": [],
            "validated_technology_list": []
        }
    }
}

test_tobe_deny_p1_unjustified_addition if {
    count(to_be_prohibitions.deny) > 0 with input as {
        "to_be": {
            "added_activities": [{"id": "new_act", "justified_by_findings": []}],
            "removed_activities": [], "technology_proposals": [],
            "headcount_changes": [], "findings": [{"id": "f1"}],
            "regulatory_controls_mapped": [], "validated_technology_list": []
        }
    }
}

test_tobe_deny_p2_regulatory_removed if {
    count(to_be_prohibitions.deny) > 0 with input as {
        "to_be": {
            "added_activities": [],
            "removed_activities": [{"id": "validate_aml"}],
            "technology_proposals": [], "headcount_changes": [],
            "findings": [],
            "regulatory_controls_mapped": [{"activity_id": "validate_aml", "regulation": "AML"}],
            "validated_technology_list": []
        }
    }
}

test_tobe_escalate_p4_headcount_no_memo if {
    count(to_be_prohibitions.escalate) > 0 with input as {
        "to_be": {
            "added_activities": [], "removed_activities": [],
            "technology_proposals": [],
            "headcount_changes": [{"id": "hc1", "reduction": 3, "has_justification_memo": false}],
            "findings": [], "regulatory_controls_mapped": [],
            "validated_technology_list": []
        }
    }
}

# =============================================================================
# Cycle Limits
# =============================================================================

test_cycle_permit_within_limit if {
    cycle_limits.decision.outcome == "PERMIT" with input as {
        "execution": {"component": "capture_agent", "current_cycle": 2, "last_outcome": "in_progress", "request_another_cycle": false}
    }
}

test_cycle_deny_over_limit if {
    count(cycle_limits.deny) > 0 with input as {
        "execution": {"component": "to_be_generator", "current_cycle": 3, "request_another_cycle": true, "last_outcome": "failed"}
    }
}

test_cycle_suspend_exhausted_failure if {
    count(cycle_limits.suspend) > 0 with input as {
        "execution": {"component": "capture_agent", "current_cycle": 5, "last_outcome": "failed"}
    }
}

test_cycle_escalate_final_cycle if {
    count(cycle_limits.escalate) > 0 with input as {
        "execution": {"component": "capture_agent", "current_cycle": 4, "last_outcome": "in_progress"}
    }
}

# =============================================================================
# Consent Gates
# =============================================================================

test_consent_permit_llm_with_t1_t3 if {
    consent_gates.decision.outcome == "PERMIT" with input as {
        "gate_check": {
            "action": "ingest_to_llm",
            "deployment_id": "D001",
            "consents": {
                "t1": {"signed": true, "hash": "h1", "signer_role": "client_representative"},
                "t3": {"signed": true, "hash": "h3", "signer_role": "client_representative"},
                "t2_by_participant": {}
            }
        }
    }
}

test_consent_deny_llm_without_t3 if {
    count(consent_gates.deny) > 0 with input as {
        "gate_check": {
            "action": "ingest_to_llm",
            "deployment_id": "D001",
            "consents": {
                "t1": {"signed": true, "hash": "h1", "signer_role": "client_representative"},
                "t3": {"signed": false, "hash": "", "signer_role": ""},
                "t2_by_participant": {}
            }
        }
    }
}

test_consent_deny_recording_without_t2 if {
    count(consent_gates.deny) > 0 with input as {
        "gate_check": {
            "action": "start_recording",
            "deployment_id": "D001",
            "participant_id": "P001",
            "consents": {
                "t1": {"signed": true, "hash": "h1", "signer_role": "client_representative"},
                "t3": {"signed": true, "hash": "h3", "signer_role": "client_representative"},
                "t2_by_participant": {"P001": {"signed": false, "signer_role": ""}}
            }
        }
    }
}

# =============================================================================
# Sensitive Data
# =============================================================================

test_sensitive_permit_no_categories if {
    sensitive_data.decision.outcome == "PERMIT" with input as {
        "content_analysis": {
            "content_hash": "h1", "detected_categories": [],
            "has_additional_consent": false, "notification_dpo_sent_at": null,
            "identified_at": "2026-04-17T10:00:00Z", "destination": "llm_prompt"
        },
        "hours_since_identification": 0
    }
}

test_sensitive_deny_llm_no_consent if {
    count(sensitive_data.deny) > 0 with input as {
        "content_analysis": {
            "content_hash": "h1", "detected_categories": ["health_data"],
            "has_additional_consent": false, "notification_dpo_sent_at": null,
            "identified_at": "2026-04-17T10:00:00Z", "destination": "llm_prompt"
        },
        "hours_since_identification": 1
    }
}

test_sensitive_suspend_48h_expired if {
    count(sensitive_data.suspend) > 0 with input as {
        "content_analysis": {
            "content_hash": "h1", "detected_categories": ["racial_ethnic_origin"],
            "has_additional_consent": false, "notification_dpo_sent_at": null,
            "identified_at": "2026-04-15T10:00:00Z", "destination": "log"
        },
        "hours_since_identification": 50
    }
}

# =============================================================================
# Retention
# =============================================================================

test_retention_permit_within_window if {
    retention.decision.outcome == "PERMIT" with input as {
        "retention_check": {
            "data_type": "recordings_original", "created_at": "2026-04-01T10:00:00Z",
            "age_days": 15, "deployment_id": "D001", "is_auditor_access": false
        }
    }
}

test_retention_deny_expired_non_auditor if {
    count(retention.deny) > 0 with input as {
        "retention_check": {
            "data_type": "recordings_original", "created_at": "2026-03-01T10:00:00Z",
            "age_days": 45, "deployment_id": "D001", "is_auditor_access": false
        }
    }
}
