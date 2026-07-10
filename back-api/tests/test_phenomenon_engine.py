"""Tests for phenomenon engine (deterministic phases)."""
from types import SimpleNamespace

from api.pipeline.phenomenon_engine import (
    build_p01_reception,
    build_summary,
    validate_phase_output,
)
from api.pipeline.pro_phenomenon_documents import (
    build_discovery_form_markdown,
    build_internal_phenomenon_markdown,
)


def _case_with_analysis():
    analysis = {
        "status": "completed",
        "p01_reception": {
            "client_name": "CD Global",
            "domain": "Operaciones",
            "symptom": "Lentitud en cotización",
            "incidents": ["Ingeniero demora días en liquidación"],
            "core_processes": ["Cotización"],
        },
        "p02_epoche": {
            "naive_diagnoses": [{"label": "falta personal", "what_it_hides": "saber no depositado"}],
            "suspended_view": "Repetición del criterio",
        },
        "p03_convergence": {
            "phenomenon_named": "criterio cautivo",
            "convergence_summary": "El saber no se sedimenta",
            "lenses_used": [{"id": "ver", "finding": "x"}],
        },
        "p04_contradiction": {
            "technical_contradiction": {"statement": "más personas empeora autonomía"},
            "physical_contradiction": {"statement": "criterio en persona y sistema"},
            "resolution_motor": {"name": "80/20", "rule": "típico al sistema"},
        },
        "p05_localization": {
            "core_subsystems": [{"name": "Cotización", "pain_signal": "lento"}],
            "hinge_question": "¿Lista sale del APU?",
            "priority_order": ["Requisición"],
        },
        "p06_kill_critic": {"gates_passed": True, "risks": []},
        "p07_derivation": {
            "recommended_documents": [{"type": "discovery_form", "priority": 1}],
            "next_operational_step": "Recolectar datos",
        },
        "summary": build_summary({
            "p03_convergence": {"phenomenon_named": "criterio cautivo"},
            "p04_contradiction": {"resolution_motor": {"name": "80/20"}},
            "p05_localization": {},
            "p06_kill_critic": {"gates_passed": True},
            "p07_derivation": {},
        }),
    }
    return SimpleNamespace(
        client_name="CD Global",
        domain="Operaciones",
        input_payload={"phenomenon_analysis": analysis},
    )


def test_p01_reception_from_intake():
    payload = {
        "extra": {
            "symptom": "Lentitud en cotización, requisición y liquidación",
            "sector": "Construcción",
            "expected_outcome": "Un sistema agéntico",
            "previous_attempts": "Usar tablas dinámicas",
            "contact_name": "Ivania Rua",
            "contact_role": "CEO",
        },
        "paquete_hipotesis": [
            {
                "enunciado": "Falta de automatización en liquidación",
                "incidente_texto": "Un ingeniero demora días haciendo una liquidación",
            }
        ],
    }
    p01 = build_p01_reception(
        client_name="CD GLOBAL",
        domain="Operaciones y producción",
        input_payload=payload,
    )
    assert "cotiz" in p01["symptom"].lower()
    assert p01["incidents"]
    assert "Cotización" in p01["core_processes"] or len(p01["core_processes"]) >= 1


def test_validate_p03_requires_phenomenon_named():
    issues = validate_phase_output("p03_convergence", {"lenses_used": []})
    assert any("phenomenon_named" in i for i in issues)


def test_build_summary_gates():
    analysis = {
        "p03_convergence": {"phenomenon_named": "criterio cautivo", "convergence_summary": "x"},
        "p04_contradiction": {"resolution_motor": {"name": "80/20", "rule": "típico vs atípico"}},
        "p05_localization": {"hinge_question": "¿Sale del APU?"},
        "p06_kill_critic": {"gates_passed": False, "blocking_reasons": ["dataset"]},
        "p07_derivation": {
            "recommended_documents": [{"type": "discovery_form", "priority": 1}],
            "next_operational_step": "Recolectar datos",
            "commercial_safe": False,
        },
    }
    s = build_summary(analysis)
    assert s["phenomenon_named"] == "criterio cautivo"
    assert s["gates_passed"] is False
    assert s["commercial_safe"] is False


def test_internal_phenomenon_markdown():
    md = build_internal_phenomenon_markdown(_case_with_analysis())
    assert "criterio cautivo" in md
    assert "Epoqué" in md or "Epoque" in md.lower() or "epoqué" in md.lower()
    assert "Kill Critic" in md


def test_discovery_form_markdown():
    md = build_discovery_form_markdown(_case_with_analysis())
    assert "Formulario de descubrimiento" in md
    assert "Q1" in md
    assert "APU" in md
