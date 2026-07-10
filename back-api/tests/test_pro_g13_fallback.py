"""Tests for G13 deterministic fallback."""
from api.pipeline.pro_g13_fallback import build_g13_fallback_from_g12, build_g13_fallback_minimal


def test_g13_fallback_minimal():
    ctx = {
        "organization_name": "CD GLOBAL",
        "subprocess": "cotización",
        "objective": "Lentitud en cotización y liquidación",
        "phenomenon_named": "Saber disperso",
        "g07_cuellos": {"total_opportunity_loss_usd_month": 8000},
        "case_anchors": {"summary": "Síntoma: lentitud"},
    }
    g13 = build_g13_fallback_minimal(ctx)
    assert g13["executive_summary"]
    assert g13["_fallback_minimal"] is True


def test_g13_fallback_from_g12():
    g12 = {
        "findings_matrix": [
            {
                "id": "F01",
                "finding": "Retrabajo en cotizaciones de tiendas Dollar City",
                "evidence": ["Hipótesis H-01 confirmada"],
                "impact_score": 9,
                "priority": "CRITICA",
            }
        ],
        "strategic_recommendations": [
            {
                "recommendation": "Memoria de APUs reutilizables",
                "timeframe": "90_dias",
                "expected_impact": "Reducción 40% tiempo de cotización",
            }
        ],
        "executive_summary_findings": "CD Global pierde días rehaciendo liquidaciones.",
    }
    ctx = {
        "organization_name": "CD GLOBAL",
        "subprocess": "cotización y liquidación",
        "sector": "Construcción",
        "phenomenon_named": "Saber Operacional Disperso",
        "g07_cuellos": {"total_opportunity_loss_usd_month": 12000},
        "case_anchors": {"summary": "Síntoma: lentitud en cotización"},
    }
    g13 = build_g13_fallback_from_g12(g12, ctx)
    assert g13["executive_summary"]
    assert len(g13["main_findings"]) == 1
    assert g13["_fallback_from_g12"] is True
    assert "crédito" not in g13["full_narrative"].lower()
