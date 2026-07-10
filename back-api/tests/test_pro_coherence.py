"""Tests for survey mode and case coherence guards."""
import pytest

from api.pipeline.llm_guard import PipelineStageFailureError
from api.pipeline.pro_coherence import (
    build_case_anchors,
    coherence_issues,
    derive_subprocess,
    validate_output_coherence,
)
from api.pipeline.pro_survey_mode import (
    MULTI_RATER,
    SINGLE_RATER,
    min_responses_for_mode,
    resolve_survey_mode,
    roles_for_mode,
)


def test_resolve_single_from_mode():
    assert resolve_survey_mode("single_rater", ["executive", "operations"]) == SINGLE_RATER


def test_resolve_multi_from_roles():
    assert resolve_survey_mode(None, ["executive", "operations"]) == MULTI_RATER
    assert resolve_survey_mode(None, ["executive"]) == SINGLE_RATER


def test_roles_for_single_mode():
    assert roles_for_mode(SINGLE_RATER, ["executive", "operations"]) == ["executive"]


def test_min_responses_single():
    assert min_responses_for_mode(SINGLE_RATER, ["executive"]) == 1
    assert min_responses_for_mode(MULTI_RATER, ["executive", "operations"]) == 2


def test_derive_subprocess_from_symptom():
    symptom = (
        "Lentitud en los procesos de cotización, requisición, liquidación "
        "y gestión del mantenimiento"
    )
    sp = derive_subprocess(symptom, "Operaciones y producción")
    assert "cotiz" in sp.lower() or "liquid" in sp.lower()


def test_coherence_rejects_vacation_bpmn():
    ctx = {
        "objective": "Lentitud en cotización y liquidación en construcción",
        "sector": "Construcción",
        "domain": "Operaciones y producción",
        "subprocess": "cotización, requisición, liquidación",
        "paquete_hipotesis": [
            {
                "hipotesis_id": "H-01",
                "enunciado": "Falta de automatización",
                "incidente_texto": "Un ingeniero demora días haciendo una liquidación",
            }
        ],
    }
    ctx["case_anchors"] = build_case_anchors(ctx)
    bad_g06 = {
        "process_name": "Gestión de Solicitudes de Vacaciones",
        "activities": [{"name": "Completar formulario de vacaciones", "lane": "RRHH"}],
    }
    issues = coherence_issues("g06_bpmn_architect", bad_g06, ctx)
    assert issues
    with pytest.raises(PipelineStageFailureError):
        validate_output_coherence("g06_bpmn_architect", bad_g06, ctx)


def test_coherence_rejects_onboarding_cartography():
    ctx = {
        "objective": "Lentitud en cotización y liquidación",
        "sector": "Construcción",
        "domain": "Operaciones",
        "subprocess": "cotización y liquidación",
        "paquete_hipotesis": [],
    }
    ctx["case_anchors"] = build_case_anchors(ctx)
    bad_g04 = {
        "industry_cases": [
            {
                "problem": "Alta rotación por falta de onboarding estandarizado",
                "solution": "Programa de onboarding gamificado",
            }
        ]
    }
    issues = coherence_issues("g04_cartografo", bad_g04, ctx)
    assert any("onboarding" in i or "ajeno" in i for i in issues)


def test_coherence_rejects_credit_narrative():
    ctx = {
        "objective": "Lentitud en cotización y liquidación",
        "sector": "Construcción",
        "domain": "Operaciones",
        "subprocess": "cotización y liquidación",
        "paquete_hipotesis": [],
    }
    ctx["case_anchors"] = build_case_anchors(ctx)
    bad_g13 = {
        "executive_summary": "La empresa debe mejorar la aprobación de solicitudes de crédito.",
        "full_narrative": "Proceso de solicitud de crédito lento.",
    }
    issues = coherence_issues("g13_redactor", bad_g13, ctx)
    assert any("credit" in i or "crédito" in i for i in issues)
