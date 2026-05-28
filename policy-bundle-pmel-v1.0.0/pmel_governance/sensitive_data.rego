# PMEL Sensitive Data Handling
# Package: arhia.pmel.governance.sensitive_data
# Source: Paso 6 §5.1 (Cláusula datos personales sensibles); TR-035 R-09
# Enforces: Datos sensibles detectados incidentalmente NO deben incluirse en prompts a LLM sin consentimiento adicional.
#           Notificación DPO Cliente en 48h desde identificación.
# ARHIA Controls: C06 (pseudonimización), C13 (supervisión humana)

package arhia.pmel.governance.sensitive_data

import rego.v1

# Categories of sensitive data under GDPR Art. 9 / LGPD Art. 11 / Ley 1581 special
sensitive_categories := {
    "racial_ethnic_origin",
    "religious_beliefs",
    "political_opinions",
    "union_affiliation",
    "genetic_data",
    "biometric_data",
    "health_data",
    "sexual_orientation",
    "sex_life"
}

default decision := {"outcome": "AUDIT", "reason": "sensitive_data_not_flagged"}

# input.content_analysis = {
#   "content_hash": "...",
#   "detected_categories": ["health_data", ...],
#   "has_additional_consent": false,
#   "notification_dpo_sent_at": null,
#   "identified_at": "2026-04-17T14:30:00Z",
#   "destination": "llm_prompt" | "log" | "artefact"
# }

detected_sensitive_categories contains cat if {
    some cat in input.content_analysis.detected_categories
    cat in sensitive_categories
}

has_additional_consent := input.content_analysis.has_additional_consent

# DENY: sending sensitive data to LLM without additional specific consent
deny[msg] if {
    count(detected_sensitive_categories) > 0
    input.content_analysis.destination == "llm_prompt"
    has_additional_consent == false
    msg := sprintf("Sensitive data categories detected (%v) — cannot send to LLM without additional specific consent (GDPR Art. 9.2.a, LGPD Art. 11.I). Content must be redacted or pseudonymized.", [detected_sensitive_categories])
}

# MODIFY: propose pseudonymization/redaction before ingest
modify[action] if {
    count(detected_sensitive_categories) > 0
    input.content_analysis.destination == "llm_prompt"
    has_additional_consent == false
    action := {
        "operation": "redact_or_pseudonymize",
        "targets": detected_sensitive_categories,
        "mandatory_before_ingest": true,
        "rationale": "Cláusula 5.1 Paso 6 — sensitive data detected"
    }
}

# ESCALATE: sensitive data detected but within 48h window — notify DPO Cliente
escalate[msg] if {
    count(detected_sensitive_categories) > 0
    input.content_analysis.notification_dpo_sent_at == null
    msg := sprintf("Sensitive data detected — DPO Cliente must be notified within 48h from %v (Cláusula 5.1 Paso 6)", [input.content_analysis.identified_at])
}

# SUSPEND: if notification window (48h) expired without DPO notification → compliance violation
suspend[msg] if {
    count(detected_sensitive_categories) > 0
    input.content_analysis.notification_dpo_sent_at == null
    input.hours_since_identification > 48
    msg := "SUSPEND: DPO Cliente notification window (48h) expired with sensitive data detected — compliance escalation required"
}

# PERMIT: sensitive data with additional consent, logged properly
decision := {"outcome": "PERMIT", "reason": "sensitive_data_with_additional_consent"} if {
    count(detected_sensitive_categories) > 0
    has_additional_consent == true
}

# PERMIT: no sensitive categories detected
decision := {"outcome": "PERMIT", "reason": "no_sensitive_data_detected"} if {
    count(detected_sensitive_categories) == 0
}

decision := {"outcome": "DENY", "reason": "sensitive_to_llm_without_consent", "categories": detected_sensitive_categories} if {
    count(detected_sensitive_categories) > 0
    input.content_analysis.destination == "llm_prompt"
    has_additional_consent == false
}

# AUDIT every sensitive data evaluation (mandatory under GDPR Art. 30 RoPA)
audit[record] if {
    record := {
        "event": "sensitive_data_evaluated",
        "content_hash": input.content_analysis.content_hash,
        "detected_categories": detected_sensitive_categories,
        "destination": input.content_analysis.destination,
        "additional_consent": has_additional_consent,
        "dpo_notified": input.content_analysis.notification_dpo_sent_at != null,
        "trace_id": input.trace_id
    }
}
