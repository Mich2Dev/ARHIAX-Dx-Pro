# R12 — Correspondencia entre process_summary_prose y grafo BPMN
# Package: arhia.pmel.bpmn_lint.r12_prose_bpmn
# Source: Catalogo BPMN-Lint v1.0 §4 R12; TR-032 D-35, D-39
# Enforces: La prosa process_summary_prose (6 secciones fijas) debe corresponder semánticamente con el grafo BPMN.
#           Validado mediante cosine similarity de embeddings.
# Severity: critical
# ARHIA Controls: C34
# Gap: G-06 (threshold sin calibrar empíricamente). Threshold actual externalizado en data/thresholds.json.

package arhia.pmel.bpmn_lint.r12_prose_bpmn

import rego.v1
import data.thresholds

default decision := {"outcome": "AUDIT", "reason": "r12_not_applicable"}

# input.bpmn.prose_bpmn_similarity = {
#   "overall_cosine": 0.82,
#   "section_scores": {
#     "proposito": 0.85, "actores": 0.90, "secuencia": 0.80,
#     "decisiones": 0.75, "errores_excepciones": 0.70, "salida_kpis": 0.88
#   },
#   "required_sections_present": 6
# }

threshold := thresholds.r12_cosine_threshold  # default 0.75 until G-06 closes

overall := input.bpmn.prose_bpmn_similarity.overall_cosine

# Identify sections below threshold
low_scoring_sections := {sec: score |
    some sec, score in input.bpmn.prose_bpmn_similarity.section_scores
    score < threshold
}

# DENY if overall is below threshold
deny[msg] if {
    overall < threshold
    msg := sprintf("R12 violation: prose↔BPMN overall cosine %.3f below threshold %.3f (critical)", [overall, threshold])
}

# DENY if any section is critically misaligned (< threshold - 0.15 buffer)
deny[msg] if {
    some sec, score in input.bpmn.prose_bpmn_similarity.section_scores
    score < (threshold - 0.15)
    msg := sprintf("R12 violation: section '%v' cosine %.3f is critically below threshold (%.3f - 0.15)", [sec, score, threshold])
}

# DENY: missing required sections
deny[msg] if {
    input.bpmn.prose_bpmn_similarity.required_sections_present < 6
    msg := sprintf("R12 violation: only %v of 6 required sections present in process_summary_prose (D-39)", [input.bpmn.prose_bpmn_similarity.required_sections_present])
}

# ESCALATE if borderline (within threshold but some low sections)
escalate[msg] if {
    overall >= threshold
    count(low_scoring_sections) > 0
    msg := sprintf("R12 borderline: overall %.3f passes but sections below threshold: %v — Consultor should review", [overall, object.keys(low_scoring_sections)])
}

decision := {"outcome": "PERMIT", "reason": "r12_prose_bpmn_aligned", "cosine": overall} if {
    overall >= threshold
    count(low_scoring_sections) == 0
    input.bpmn.prose_bpmn_similarity.required_sections_present == 6
}

decision := {"outcome": "DENY", "reason": "r12_prose_bpmn_misaligned", "cosine": overall, "threshold": threshold, "low_sections": low_scoring_sections} if {
    overall < threshold
}

audit[record] if {
    record := {
        "event": "bpmn_lint_r12_evaluated",
        "overall_cosine": overall,
        "threshold": threshold,
        "low_sections_count": count(low_scoring_sections),
        "g06_open": thresholds.g06_closed == false,
        "trace_id": input.trace_id
    }
}
