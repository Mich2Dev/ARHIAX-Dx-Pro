package arhia.pmel.base.hic_test

import data.arhia.pmel.base.hic

test_permit_consent_t3_for_llm_ingest if {
    hic.decision.outcome == "PERMIT" with input as {
        "checkpoint": "pre_llm_ingest",
        "artefact_present": true,
        "artefact_type": "consent_t3_signed",
        "signer_role": "client_representative",
        "artefact_signature_valid": true
    }
}

test_deny_missing_consent_t2 if {
    count(hic.deny) > 0 with input as {
        "checkpoint": "pre_entrevista_start",
        "artefact_present": false,
        "artefact_type": "consent_t2_signed",
        "signer_role": "participant",
        "artefact_signature_valid": false
    }
}

test_deny_wrong_signer_role if {
    count(hic.deny) > 0 with input as {
        "checkpoint": "pre_llm_ingest",
        "artefact_present": true,
        "artefact_type": "consent_t3_signed",
        "signer_role": "consultor_lite",
        "artefact_signature_valid": true
    }
}

test_escalate_non_blocking_missing if {
    count(hic.escalate) > 0 with input as {
        "checkpoint": "post_capture_review",
        "artefact_present": false,
        "artefact_type": "consultant_approval",
        "signer_role": "consultor_pro",
        "artefact_signature_valid": false
    }
}
