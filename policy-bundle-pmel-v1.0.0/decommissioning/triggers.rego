# PMEL Decommissioning Triggers — D1/D2/D3/D4 classification
# Package: arhia.pmel.decommissioning.triggers
# Source: TR-036 §2 (los 4 disparadores); TR-032 D-30
# Enforces: Clasificación correcta del disparador y asignación de SLA correspondiente.
# ARHIA Controls: C36 (decomisionamiento auditable)

package arhia.pmel.decommissioning.triggers

import rego.v1

# Trigger types with SLAs and scope defaults
trigger_definitions := {
    "D1_revocation_total": {
        "sla_days": 30,
        "first_action_hours": 4,
        "scope": "full",
        "authority_notifiable": false,
        "automation_allowed": false
    },
    "D1_revocation_participant": {
        "sla_days": 15,
        "first_action_hours": 24,
        "scope": "participant_only",
        "authority_notifiable": false,
        "automation_allowed": false
    },
    "D1_revocation_llm_only": {
        "sla_days": 30,
        "first_action_hours": 4,
        "scope": "llm_only",
        "authority_notifiable": false,
        "automation_allowed": false
    },
    "D2_contract_termination": {
        "sla_days": 30,
        "first_action_hours": 24,
        "scope": "full",
        "authority_notifiable": false,
        "automation_allowed": false
    },
    "D3_natural_closure": {
        "sla_days": 30,
        "first_action_hours": 240,  # 10 days
        "scope": "full",
        "authority_notifiable": false,
        "automation_allowed": true  # only automatable disparador
    },
    "D4_forced_incident": {
        "sla_days": 3,  # 72h
        "first_action_hours": 1,
        "scope": "court_defined_or_full",
        "authority_notifiable": true,
        "automation_allowed": false
    }
}

default decision := {"outcome": "DENY", "reason": "unknown_trigger_type"}

# input.classify = {
#   "raw_trigger_type": "revocation",
#   "revocation_scope": "full" | "participant" | "llm_only",
#   "contract_termination_reason": "...",
#   "incident_type": "...",
#   "regulatory_order": true|false
# }

# Classify raw trigger into canonical type
canonical_type := "D1_revocation_total" if {
    input.classify.raw_trigger_type == "revocation"
    input.classify.revocation_scope == "full"
}

canonical_type := "D1_revocation_participant" if {
    input.classify.raw_trigger_type == "revocation"
    input.classify.revocation_scope == "participant"
}

canonical_type := "D1_revocation_llm_only" if {
    input.classify.raw_trigger_type == "revocation"
    input.classify.revocation_scope == "llm_only"
}

canonical_type := "D2_contract_termination" if {
    input.classify.raw_trigger_type == "contract_termination"
}

canonical_type := "D3_natural_closure" if {
    input.classify.raw_trigger_type == "retention_expiry"
}

canonical_type := "D4_forced_incident" if {
    input.classify.raw_trigger_type == "incident"
}

# PERMIT: trigger classified, SLA assigned
decision := {
    "outcome": "PERMIT",
    "reason": "trigger_classified",
    "canonical_type": canonical_type,
    "sla_days": trigger_definitions[canonical_type].sla_days,
    "first_action_hours": trigger_definitions[canonical_type].first_action_hours,
    "scope": trigger_definitions[canonical_type].scope,
    "authority_notifiable": trigger_definitions[canonical_type].authority_notifiable,
    "automation_allowed": trigger_definitions[canonical_type].automation_allowed
} if {
    canonical_type in object.keys(trigger_definitions)
}

# ESCALATE: D4 with preservation inversa (judicial order) requires Asesor Legal review
escalate[msg] if {
    canonical_type == "D4_forced_incident"
    input.classify.regulatory_order == true
    msg := "D4 with regulatory preservation order — Asesor Legal must validate scope before crypto_shred (TR-036 §4.2)"
}

# ESCALATE: D1 parcial requires tombstone path until G-08 closes (D-60)
escalate[msg] if {
    canonical_type == "D1_revocation_participant"
    input.g08_closed == false
    msg := "D1 parcial: G-08 (per-participant encryption) still open — execute as tombstone lógico with deferred crypto-shred at next D3 cycle (D-60)"
}

# SUSPEND: D4 with incident not yet contained → delay decommissioning until IR completes containment
suspend[msg] if {
    canonical_type == "D4_forced_incident"
    input.classify.incident_contained == false
    msg := "D4: incident not yet contained — decommissioning suspended pending IR containment per TR-033 §8"
}

# AUDIT every trigger classification
audit[record] if {
    record := {
        "event": "decommissioning_trigger_classified",
        "raw_input": input.classify,
        "canonical_type": canonical_type,
        "sla_days": trigger_definitions[canonical_type].sla_days,
        "timestamp": input.timestamp,
        "trace_id": input.trace_id
    }
}
