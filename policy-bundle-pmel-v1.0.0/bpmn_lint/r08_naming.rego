# R8 — Nombres de actividad en forma verbo + objeto
# Package: arhia.pmel.bpmn_lint.r08_naming
# Source: Catalogo BPMN-Lint v1.0 §4 R8; TR-032 D-35
# Enforces: Cada actividad debe tener nombre compuesto por un verbo en infinitivo seguido por un objeto directo.
# Severity: material (not critical)
# ARHIA Controls: C34
# Data dependency: data/lexicon_verbs_{es,pt,en}.json

package arhia.pmel.bpmn_lint.r08_naming

import rego.v1
import data.lexicon_verbs_es
import data.lexicon_verbs_pt
import data.lexicon_verbs_en

default decision := {"outcome": "AUDIT", "reason": "r08_not_applicable"}

# Compute lexicon by language
lexicon_for_language(lang) := lexicon_verbs_es if lang == "es"
lexicon_for_language(lang) := lexicon_verbs_pt if lang == "pt"
lexicon_for_language(lang) := lexicon_verbs_en if lang == "en"

# Activities whose name does not start with a valid verb+object pattern
# The Lint-Agent runtime pre-computes the pattern check and provides the result.
# input.bpmn.activity_naming_analysis = [
#   {id, name, language, first_token, is_valid_verb, has_object, passes_r08}
# ]

invalid_names contains act if {
    some act in input.bpmn.activity_naming_analysis
    act.passes_r08 == false
}

# R8 is material: escalate for Consultor review, don't deny
escalate[msg] if {
    count(invalid_names) > 0
    names := [sprintf("%v ('%v')", [a.id, a.name]) | some a in invalid_names]
    msg := sprintf("R8 material warning: activities not in verb+object form: %v — Consultor should rename", [names])
}

decision := {"outcome": "PERMIT", "reason": "r08_all_names_valid"} if {
    count(invalid_names) == 0
    count(input.bpmn.activity_naming_analysis) > 0
}

decision := {"outcome": "ESCALATE", "reason": "r08_naming_issues", "invalid": invalid_names} if {
    count(invalid_names) > 0
}

# MODIFY: suggest rename using first verb from lexicon + nominalization of current name
modify[action] if {
    some act in invalid_names
    action := {
        "operation": "suggest_rename",
        "activity_id": act.id,
        "current_name": act.name,
        "requires_consultant_confirmation": true,
        "rationale": "R8 requires verb+object form"
    }
}

audit[record] if {
    record := {
        "event": "bpmn_lint_r08_evaluated",
        "total_activities": count(input.bpmn.activity_naming_analysis),
        "invalid_count": count(invalid_names),
        "trace_id": input.trace_id
    }
}
