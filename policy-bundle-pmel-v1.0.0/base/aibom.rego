# PMEL AIBOM (AI Bill of Materials) Validation
# Package: arhia.pmel.base.aibom
# Source: TR-032 D-31, SDX-01 §3.3 (C26)
# Enforces: Every PMEL execution must attach an AIBOM; inference-time dynamic AIBOM is roadmap (G-05)
# ARHIA Controls: C26 (AIBOM por release)

package arhia.pmel.base.aibom

import rego.v1

# Required AIBOM fields at release time (static AIBOM, gap G-05 pending for dynamic)
required_release_fields := {
    "bundle_name",
    "bundle_version",
    "models",
    "prompts",
    "dependencies",
    "sbom_reference",
    "generated_at",
    "generated_by",
    "signature"
}

# Allowed LLM model identifiers for PMEL
allowed_models := {
    "claude-sonnet-4-6",
    "claude-sonnet-4-7",
    "claude-opus-4-7",
    "whisper-large-v3-latam"
}

# Prompt version registry (prompts are versioned per Paso 2 §1.5)
allowed_prompts := {
    "pmel-capture-agent-v1.0",
    "pmel-visual-interpreter-v1.0",
    "pmel-to-be-generator-v1.0",
    "pmel-bpmn-lint-agent-v1.0",
    "pmel-dmn-engine-v1.0",
    "pmel-crypto-participant-v1.0",
    "pmel-rgc-hypothesis-builder-v1.0",
    "pmel-rgc-deep-research-contraster-v1.0",
    "pmel-adaptive-question-bank-v1.0",
    "pmel-multi-role-scoring-v1.0",
    "pmel-psychometrics-v1.0",
    "pmel-irr-reliability-v1.0",
    "pmel-bayesian-synthesis-v1.0",
    "pmel-executive-qa-v1.0",
    "pmel-diagnostic-intelligence-v1.0",
    "pmel-diagnostic-fusion-cycle-v1.0"
}

default decision := {"outcome": "DENY", "reason": "aibom_validation_failed"}

# PERMIT: AIBOM complete and valid
decision := {"outcome": "PERMIT", "reason": "aibom_valid", "bundle_version": input.aibom.bundle_version} if {
    aibom_complete
    aibom_models_authorized
    aibom_prompts_authorized
    aibom_signature_valid
}

aibom_complete if {
    every field in required_release_fields {
        field in object.keys(input.aibom)
    }
}

aibom_models_authorized if {
    every model in input.aibom.models {
        model.id in allowed_models
    }
}

aibom_prompts_authorized if {
    every prompt in input.aibom.prompts {
        prompt.id in allowed_prompts
    }
}

aibom_signature_valid if {
    input.aibom.signature_verified == true
}

# DENY: missing required fields
deny[msg] if {
    not aibom_complete
    missing := required_release_fields - object.keys(input.aibom)
    count(missing) > 0
    msg := sprintf("AIBOM incomplete: missing fields %v", [missing])
}

# DENY: unauthorized model in AIBOM
deny[msg] if {
    some model in input.aibom.models
    not model.id in allowed_models
    msg := sprintf("AIBOM contains unauthorized model: %v (allowed: %v)", [model.id, allowed_models])
}

# DENY: unauthorized prompt
deny[msg] if {
    some prompt in input.aibom.prompts
    not prompt.id in allowed_prompts
    msg := sprintf("AIBOM contains unauthorized prompt: %v", [prompt.id])
}

# DENY: signature missing or invalid
deny[msg] if {
    input.aibom.signature_verified == false
    msg := "AIBOM signature invalid — artefact may be tampered"
}

# ESCALATE: dynamic AIBOM requested but G-05 still open
escalate[msg] if {
    input.aibom.type == "dynamic_per_execution"
    input.g05_closed == false
    msg := "Dynamic AIBOM requested but gap G-05 not yet closed — using static AIBOM with escalation note"
}

# MODIFY: allow execution with static AIBOM when dynamic was requested but G-05 open
modify[action] if {
    input.aibom.type == "dynamic_per_execution"
    input.g05_closed == false
    action := {
        "use_aibom_type": "static_per_release",
        "add_audit_note": "dynamic_aibom_unavailable_g05_pending"
    }
}

# AUDIT: every AIBOM validation is logged
audit[record] if {
    record := {
        "event": "aibom_validated",
        "bundle_version": input.aibom.bundle_version,
        "aibom_type": input.aibom.type,
        "models": [m.id | some m in input.aibom.models],
        "prompts": [p.id | some p in input.aibom.prompts],
        "timestamp": input.timestamp,
        "trace_id": input.trace_id
    }
}
