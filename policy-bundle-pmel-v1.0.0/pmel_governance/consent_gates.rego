# PMEL Consent Gates — T1/T2/T3 order enforcement
# Package: arhia.pmel.governance.consent_gates
# Source: Paso 6 Templates de Consentimiento §1.3 (orden T1→T3→T2); TR-032 D-36
# Enforces: Ninguna ingesta a LLM sin T3 firmado; ninguna grabación sin T2 firmado; ninguna captura sin T1 firmado.
# ARHIA Controls: C02 (consentimiento granular), C14 (gate pre-ingesta)

package arhia.pmel.governance.consent_gates

import rego.v1

default decision := {"outcome": "DENY", "reason": "consent_gate_undefined_action"}

# input.gate_check = {
#   "action": "start_observation" | "start_recording" | "ingest_to_llm" | "process_m2_upload",
#   "deployment_id": "...",
#   "participant_id": "..." (only for recording),
#   "consents": {
#     "t1": {"signed": true, "hash": "...", "signer_role": "client_representative"},
#     "t2_by_participant": {"P001": {"signed": true, ...}, "P002": {"signed": false, ...}},
#     "t3": {"signed": true, "hash": "...", "signer_role": "client_representative"}
#   }
# }

t1_valid if {
    input.gate_check.consents.t1.signed == true
    input.gate_check.consents.t1.signer_role == "client_representative"
    count(input.gate_check.consents.t1.hash) > 0
}

t3_valid if {
    input.gate_check.consents.t3.signed == true
    input.gate_check.consents.t3.signer_role == "client_representative"
    count(input.gate_check.consents.t3.hash) > 0
}

t2_valid_for_participant(pid) if {
    input.gate_check.consents.t2_by_participant[pid].signed == true
    input.gate_check.consents.t2_by_participant[pid].signer_role == "participant"
}

# Action: start_observation requires T1
deny[msg] if {
    input.gate_check.action == "start_observation"
    not t1_valid
    msg := "Consent gate: cannot start observation without valid T1 (Consentimiento 1) signed by client representative"
}

decision := {"outcome": "PERMIT", "reason": "t1_valid_observation_permitted"} if {
    input.gate_check.action == "start_observation"
    t1_valid
}

# Action: start_recording requires T1 + T2 for that participant
deny[msg] if {
    input.gate_check.action == "start_recording"
    not t1_valid
    msg := "Consent gate: cannot start recording without valid T1"
}

deny[msg] if {
    input.gate_check.action == "start_recording"
    t1_valid
    not t2_valid_for_participant(input.gate_check.participant_id)
    msg := sprintf("Consent gate: cannot start recording for participant %v without valid T2 (Consentimiento 2)", [input.gate_check.participant_id])
}

decision := {"outcome": "PERMIT", "reason": "t1_and_t2_valid_recording_permitted"} if {
    input.gate_check.action == "start_recording"
    t1_valid
    t2_valid_for_participant(input.gate_check.participant_id)
}

# Action: ingest_to_llm requires T1 + T3 (strictest gate)
deny[msg] if {
    input.gate_check.action == "ingest_to_llm"
    not t1_valid
    msg := "Consent gate: cannot ingest to LLM without valid T1"
}

deny[msg] if {
    input.gate_check.action == "ingest_to_llm"
    t1_valid
    not t3_valid
    msg := "Consent gate: cannot ingest to LLM without valid T3 (Consentimiento 3) — C14 enforcement"
}

decision := {"outcome": "PERMIT", "reason": "t1_and_t3_valid_llm_ingest_permitted"} if {
    input.gate_check.action == "ingest_to_llm"
    t1_valid
    t3_valid
}

# Action: process_m2_upload requires T1 + T3 (uploaded docs go to LLM)
deny[msg] if {
    input.gate_check.action == "process_m2_upload"
    not (t1_valid)
    msg := "Consent gate: M2 upload processing requires T1"
}

deny[msg] if {
    input.gate_check.action == "process_m2_upload"
    t1_valid
    not t3_valid
    msg := "Consent gate: M2 upload processing requires T3 (content goes to LLM)"
}

decision := {"outcome": "PERMIT", "reason": "t1_and_t3_valid_m2_upload_permitted"} if {
    input.gate_check.action == "process_m2_upload"
    t1_valid
    t3_valid
}

# AUDIT all consent gate evaluations (regulatory evidence)
audit[record] if {
    record := {
        "event": "consent_gate_evaluated",
        "action": input.gate_check.action,
        "deployment_id": input.gate_check.deployment_id,
        "participant_id": input.gate_check.participant_id,
        "t1_valid": t1_valid,
        "t3_valid": t3_valid,
        "timestamp": input.timestamp,
        "trace_id": input.trace_id
    }
}
