package arhia.pmel.base.aibom_test

import data.arhia.pmel.base.aibom

valid_aibom_input := {
    "aibom": {
        "bundle_name": "pmel-runtime",
        "bundle_version": "1.0.0",
        "type": "static_per_release",
        "models": [{"id": "claude-sonnet-4-7"}, {"id": "claude-opus-4-7"}, {"id": "whisper-large-v3-latam"}],
        "prompts": [{"id": "pmel-capture-agent-v1.0"}, {"id": "pmel-to-be-generator-v1.0"}],
        "dependencies": [],
        "sbom_reference": "sbom://2026-04-17",
        "generated_at": "2026-04-17T10:00:00Z",
        "generated_by": "build-system",
        "signature": "sig://...",
        "signature_verified": true
    },
    "g05_closed": false
}

test_permit_valid_aibom if {
    aibom.decision.outcome == "PERMIT" with input as valid_aibom_input
}

test_deny_unauthorized_model if {
    count(aibom.deny) > 0 with input as {
        "aibom": {
            "bundle_name": "pmel-runtime", "bundle_version": "1.0.0", "type": "static_per_release",
            "models": [{"id": "gpt-4-unauthorized"}],
            "prompts": [{"id": "pmel-capture-agent-v1.0"}],
            "dependencies": [], "sbom_reference": "ref", "generated_at": "t", "generated_by": "b",
            "signature": "s", "signature_verified": true
        }
    }
}

test_deny_missing_fields if {
    count(aibom.deny) > 0 with input as {
        "aibom": {"bundle_name": "pmel-runtime"}
    }
}

test_escalate_dynamic_with_g05_open if {
    input_with_dynamic := object.union(valid_aibom_input, {"aibom": object.union(valid_aibom_input.aibom, {"type": "dynamic_per_execution"})})
    count(aibom.escalate) > 0 with input as input_with_dynamic
}
