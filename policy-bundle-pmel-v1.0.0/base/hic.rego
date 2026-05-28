# PMEL Human-in-Command (HIC) Checkpoints
# Package: arhia.pmel.base.hic
# Source: TR-032 D-09, D-13, D-38; SDX-01 §3.2 (C13, C14, C23, C24)
# Enforces: Human calificado must review before release of key artefactos.
# ARHIA Controls: C13 (supervisión por acción), C14 (gate pre-ingesta), C23 (low-confidence), C24 (delegación CAA)

package arhia.pmel.base.hic

import rego.v1

# HIC Checkpoint definitions for PMEL
# Each checkpoint maps to a stage where human review is mandatory or conditional

hic_checkpoints := {
    "pre_llm_ingest": {
        "description": "Before sending data to LLM providers",
        "required_roles": ["client_representative"],
        "artefact": "consent_t3_signed",
        "blocking": true,
        "control_ref": "C14"
    },
    "pre_entrevista_start": {
        "description": "Before starting each participant interview recording",
        "required_roles": ["participant"],
        "artefact": "consent_t2_signed",
        "blocking": true,
        "control_ref": "C14"
    },
    "post_capture_review": {
        "description": "After Capture-Agent produces AS-IS, before Lint",
        "required_roles": ["consultor_pro", "consultor_lite"],
        "artefact": "consultant_approval",
        "blocking": false,
        "control_ref": "C13"
    },
    "post_to_be_review": {
        "description": "After TO-BE-Generator produces proposal, before delivery",
        "required_roles": ["consultor_pro", "technical_reviewer"],
        "artefact": "reviewer_approval",
        "blocking": true,
        "control_ref": "C13"
    },
    "low_confidence_escalation": {
        "description": "Escalate when Visual-Interpreter confidence below threshold",
        "required_roles": ["consultor_pro"],
        "artefact": "low_confidence_resolution",
        "blocking": true,
        "control_ref": "C23"
    },
    "caa_delegation": {
        "description": "Delegate complex governance gaps to Consulta Arquitectura ARHIA",
        "required_roles": ["architecture_review_board"],
        "artefact": "caa_resolution_document",
        "blocking": true,
        "control_ref": "C24"
    }
}

# Default: deny if checkpoint not recognized
default decision := {"outcome": "DENY", "reason": "unknown_hic_checkpoint"}

# PERMIT: checkpoint satisfied (human artefact present and valid)
decision := {"outcome": "PERMIT", "reason": "hic_checkpoint_satisfied", "checkpoint": input.checkpoint} if {
    input.checkpoint in object.keys(hic_checkpoints)
    checkpoint := hic_checkpoints[input.checkpoint]
    input.artefact_present == true
    input.artefact_type == checkpoint.artefact
    input.signer_role in checkpoint.required_roles
    input.artefact_signature_valid == true
}

# DENY: blocking checkpoint with missing artefact
deny[msg] if {
    input.checkpoint in object.keys(hic_checkpoints)
    checkpoint := hic_checkpoints[input.checkpoint]
    checkpoint.blocking == true
    input.artefact_present == false
    msg := sprintf("HIC checkpoint %v is BLOCKING and artefact %v is missing (control %v)", [input.checkpoint, checkpoint.artefact, checkpoint.control_ref])
}

# DENY: signer role not authorized for this checkpoint
deny[msg] if {
    input.checkpoint in object.keys(hic_checkpoints)
    checkpoint := hic_checkpoints[input.checkpoint]
    input.artefact_present == true
    not input.signer_role in checkpoint.required_roles
    msg := sprintf("HIC checkpoint %v: signer role %v not in required_roles %v", [input.checkpoint, input.signer_role, checkpoint.required_roles])
}

# DENY: signature invalid
deny[msg] if {
    input.artefact_signature_valid == false
    msg := sprintf("HIC checkpoint %v: artefact signature verification failed", [input.checkpoint])
}

# ESCALATE: non-blocking checkpoint missing artefact (soft escalation)
escalate[msg] if {
    input.checkpoint in object.keys(hic_checkpoints)
    checkpoint := hic_checkpoints[input.checkpoint]
    checkpoint.blocking == false
    input.artefact_present == false
    msg := sprintf("HIC checkpoint %v: non-blocking but artefact %v missing — escalate to Consultor", [input.checkpoint, checkpoint.artefact])
}

# AUDIT: always log HIC decisions
audit[record] if {
    record := {
        "event": "hic_checkpoint_evaluated",
        "checkpoint": input.checkpoint,
        "artefact_present": input.artefact_present,
        "signer_role": input.signer_role,
        "signature_valid": input.artefact_signature_valid,
        "timestamp": input.timestamp,
        "trace_id": input.trace_id
    }
}
