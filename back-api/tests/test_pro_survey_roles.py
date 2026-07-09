"""Tests for pro_survey_roles normalization."""
from api.pipeline.pro_survey_roles import available_role_labels, normalize_role_options


def test_standard_three_roles():
    opts = normalize_role_options(["executive", "operations", "technology"])
    labels = [o["label"] for o in opts]
    assert labels == ["Estratégico", "Operativo", "Táctico"]


def test_legacy_ivania_roles_no_english_strategy():
    raw = ["executive", "operations", "technology", "strategy"]
    labels = available_role_labels(raw)
    assert labels == ["Estratégico", "Operativo", "Táctico", "Planeación"]
    assert "strategy" not in labels
    assert "STRATEGY" not in labels


def test_dimensions_filtered_from_roles():
    opts = normalize_role_options(["executive", "process", "people"])
    labels = [o["label"] for o in opts]
    assert "Estratégico" in labels
    assert len(labels) == 1
