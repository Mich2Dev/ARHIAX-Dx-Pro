"""
Genera un PDF v7 de demostracion usando el builder conectado al markdown del sistema.
Ejecutar: python gen_pdf_v7_demo.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "back-api", "src"))


class FakeCase:
    case_id = "DEMO-2026-001"
    id = "uuid-demo-001"
    engagement_id = "ENG-001"
    trace_id = "TRC-ABC-123"
    pmel_outcome = "PERMIT"
    case_status = "review_pending"
    client_name = "Caribe Freight Services S.A.S."
    domain = "Logistica y cadena de suministro"
    evidence_entries = []

    fusion_result = {
        "executive_thesis": (
            "El diagnostico identifica brechas en gobierno operativo y trazabilidad. "
            "La madurez global sugiere capacidad comercial con fragilidad en procesos "
            "y decisiones no formalizadas."
        ),
        "scoring": {
            "overall_score": 58.4,
            "total_responses": 12,
            "dimension_scores": [
                {"dimension": "process", "score": 52},
                {"dimension": "governance", "score": 41},
                {"dimension": "technology", "score": 63},
                {"dimension": "people", "score": 72},
                {"dimension": "strategy", "score": 55},
            ],
        },
        "risk_signals": [
            {"signal": "Criterios de aprobacion no documentados", "severity": "high"},
            {"signal": "Retrabajo circular sin tope de iteraciones", "severity": "high"},
            {"signal": "Seguimiento en correos y chats", "severity": "medium"},
        ],
        "hypotheses": [
            {
                "statement": "Intake incompleto genera retrabajo",
                "prior": 0.5,
                "posterior": 0.78,
                "supported": True,
            },
            {
                "statement": "Decision informal aumenta variabilidad",
                "prior": 0.5,
                "posterior": 0.71,
                "supported": True,
            },
            {
                "statement": "Volumen supera capacidad actual",
                "prior": 0.5,
                "posterior": 0.32,
                "supported": False,
            },
        ],
        "recommended_next_step": (
            "Revisar hallazgos con el equipo directivo y priorizar quick wins "
            "de intake en las proximas 4 semanas."
        ),
        "stage_outcomes": {
            "g10_scoring": {"outcome": "PERMIT", "artifact_type": "scoring"},
            "g11_bayesian": {"outcome": "PERMIT", "artifact_type": "bayesian"},
            "g12_hallazgos": {"outcome": "PERMIT", "artifact_type": "hallazgos"},
            "g13_redactor": {"outcome": "PERMIT", "artifact_type": "redactor"},
        },
    }

    report_result = {
        "sections": [
            {
                "title": "Resumen Ejecutivo",
                "content": "Diagnostico de Caribe Freight Services S.A.S. en logistica. Indice 58.4/100.",
            },
            {
                "title": "Metodologia",
                "content": "Encuesta multi-rater con 12 respondentes. Escala Likert 1-5.",
            },
        ],
        "qa_score": 0.87,
    }

    render_result = {"markdown": ""}


evidence = [
    {
        "event_type": "diagnostic_evaluation",
        "outcome": "PERMIT",
        "agent": "GeminiPipeline",
        "created_at": "2026-06-26T08:05:30",
    },
    {
        "event_type": "grammar_gate",
        "outcome": "draft_ready",
        "agent": "grammar-gate",
        "created_at": "2026-06-26T08:06:00",
    },
]

from api.pipeline.pro_pdf_builder import build_pro_pdf

out_path = os.path.join(os.path.dirname(__file__), "diagnostico_v7_sistema.pdf")
pdf_bytes = build_pro_pdf(FakeCase(), evidence)
with open(out_path, "wb") as f:
    f.write(pdf_bytes)

print(f"PDF generado: {out_path} ({len(pdf_bytes) // 1024} KB)")
