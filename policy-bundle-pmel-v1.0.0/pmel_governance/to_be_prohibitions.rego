# PMEL TO-BE-Generator — 4 Prohibitions
# Package: arhia.pmel.governance.to_be_prohibitions
# Source: Paso 2 Prompts Canónicos §4 TO-BE-Generator; TR-032 D-05
# Enforces: Límites duros anti-alucinación sobre las propuestas TO-BE.
#   P1: No agregar actividades no derivables del AS-IS + hallazgos
#   P2: No eliminar actividades que cubren controles regulatorios identificados
#   P3: No especular sobre tecnología no validada
#   P4: No proponer reducciones de personal sin justificación explícita
# ARHIA Controls: C13, C17, C22

package arhia.pmel.governance.to_be_prohibitions

import rego.v1

default decision := {"outcome": "AUDIT", "reason": "to_be_prohibitions_not_triggered"}

# input.to_be = {
#   "added_activities": [...],       # activities in TO-BE not present in AS-IS
#   "removed_activities": [...],     # activities in AS-IS removed in TO-BE
#   "technology_proposals": [...],   # tech recommendations made
#   "headcount_changes": [...],      # reductions in personnel proposed
#   "findings": [...],               # findings identified (justify added/removed)
#   "regulatory_controls_mapped": [...]  # activities mapping to regulatory control
# }

# P1 violations: added activities without finding-based justification
p1_violations contains act_id if {
    some act in input.to_be.added_activities
    not has_finding_justification(act)
    act_id := act.id
}

has_finding_justification(activity) if {
    some finding in input.to_be.findings
    finding.id in activity.justified_by_findings
}

# P2 violations: removed activities that cover regulatory controls
p2_violations contains act_id if {
    some act in input.to_be.removed_activities
    some ctrl in input.to_be.regulatory_controls_mapped
    ctrl.activity_id == act.id
    act_id := act.id
}

# P3 violations: technology proposals for tech not in validated list
# input.to_be.validated_technology_list is configurable data
p3_violations contains tech_name if {
    some tech in input.to_be.technology_proposals
    not tech.name in input.to_be.validated_technology_list
    tech_name := tech.name
}

# P4 violations: headcount reductions without explicit justification memo
p4_violations contains change_id if {
    some change in input.to_be.headcount_changes
    change.reduction > 0
    change.has_justification_memo == false
    change_id := change.id
}

# DENY any P1 violation (critical — anti-hallucination)
deny[msg] if {
    count(p1_violations) > 0
    msg := sprintf("TO-BE P1 violation: activities added without finding-based justification: %v (anti-hallucination guard)", [p1_violations])
}

# DENY P2 violation: removing regulatory control activities is critical
deny[msg] if {
    count(p2_violations) > 0
    msg := sprintf("TO-BE P2 violation: removing activities that cover regulatory controls: %v (compliance risk)", [p2_violations])
}

# ESCALATE P3 (not critical but requires human validation)
escalate[msg] if {
    count(p3_violations) > 0
    msg := sprintf("TO-BE P3 escalation: proposed technologies not in validated list: %v — Technical Reviewer validation required", [p3_violations])
}

# ESCALATE P4
escalate[msg] if {
    count(p4_violations) > 0
    msg := sprintf("TO-BE P4 escalation: headcount reductions without justification memo: %v — Consultor must document", [p4_violations])
}

# PERMIT: all prohibitions respected
decision := {"outcome": "PERMIT", "reason": "to_be_all_prohibitions_respected"} if {
    count(p1_violations) == 0
    count(p2_violations) == 0
    count(p3_violations) == 0
    count(p4_violations) == 0
}

decision := {"outcome": "DENY", "reason": "to_be_hard_prohibitions_violated", "p1": p1_violations, "p2": p2_violations} if {
    total := count(p1_violations) + count(p2_violations)
    total > 0
}

decision := {"outcome": "ESCALATE", "reason": "to_be_soft_prohibitions_flagged", "p3": p3_violations, "p4": p4_violations} if {
    count(p1_violations) == 0
    count(p2_violations) == 0
    total := count(p3_violations) + count(p4_violations)
    total > 0
}

audit[record] if {
    record := {
        "event": "to_be_prohibitions_evaluated",
        "p1_count": count(p1_violations),
        "p2_count": count(p2_violations),
        "p3_count": count(p3_violations),
        "p4_count": count(p4_violations),
        "trace_id": input.trace_id
    }
}
