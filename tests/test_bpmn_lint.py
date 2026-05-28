"""Tests for the 12 deterministic BPMN-Lint rules (R01..R12)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dxpro_runtime.bpmn import parse_model, run_lint
from dxpro_runtime.bpmn.lint import CRITICAL, MATERIAL


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _model(nodes, edges, **kwargs):
    return parse_model({"nodes": nodes, "edges": edges, **kwargs})


def _start(node_id="s", **kw):
    return {"id": node_id, "type": "start_event", **kw}


def _end(node_id="e", **kw):
    return {"id": node_id, "type": "end_event", **kw}


def _task(node_id, name="Validar pedido", **kw):
    return {"id": node_id, "type": "task", "name": name, **kw}


def _gw(node_id, subtype="xor", **kw):
    return {"id": node_id, "type": "gateway", "gateway_subtype": subtype, **kw}


def _edge(source, target, **kw):
    return {"source": source, "target": target, **kw}


def _well_formed_model():
    """A trivially valid linear process used as the baseline for negative tests."""
    nodes = [_start(), _task("t1", "Validar pedido"), _end()]
    edges = [_edge("s", "t1"), _edge("t1", "e")]
    prose = {"flow": "Se inicia el proceso, se valida el pedido y se finaliza."}
    return _model(nodes, edges, prose=prose)


def _has_rule(report, rule_id) -> bool:
    return any(i.rule_id == rule_id for i in report.issues)


# ---------------------------------------------------------------------------
# Baseline
# ---------------------------------------------------------------------------

def test_well_formed_model_has_no_issues() -> None:
    report = run_lint(_well_formed_model())
    assert report.outcome == "PERMIT"
    assert report.issue_count == 0


# ---------------------------------------------------------------------------
# R01 — gateway balance
# ---------------------------------------------------------------------------

def test_r01_unbalanced_xor_split_without_join() -> None:
    nodes = [
        _start(),
        _gw("g1", "xor"),
        _task("t1"),
        _task("t2"),
        _end("e1"),
        _end("e2"),
    ]
    edges = [
        _edge("s", "g1"),
        _edge("g1", "t1", condition="ok"),
        _edge("g1", "t2", condition="fail"),
        _edge("t1", "e1"),
        _edge("t2", "e2"),
    ]
    report = run_lint(_model(nodes, edges))
    assert _has_rule(report, "R01")
    assert report.outcome == CRITICAL


def test_r01_balanced_xor_passes() -> None:
    nodes = [
        _start(),
        _gw("g1", "xor"),
        _task("t1"),
        _task("t2"),
        _gw("g2", "xor"),
        _end(),
    ]
    edges = [
        _edge("s", "g1"),
        _edge("g1", "t1", condition="ok"),
        _edge("g1", "t2", default=True),
        _edge("t1", "g2"),
        _edge("t2", "g2"),
        _edge("g2", "e"),
    ]
    report = run_lint(_model(nodes, edges))
    assert not _has_rule(report, "R01")


# ---------------------------------------------------------------------------
# R02 — reachability
# ---------------------------------------------------------------------------

def test_r02_unreachable_node_is_critical() -> None:
    nodes = [_start(), _task("t1"), _task("orphan_island"), _end()]
    edges = [_edge("s", "t1"), _edge("t1", "e")]
    report = run_lint(_model(nodes, edges))
    assert _has_rule(report, "R02")


def test_r02_missing_start_event() -> None:
    nodes = [_task("t1"), _end()]
    edges = [_edge("t1", "e")]
    report = run_lint(_model(nodes, edges))
    assert _has_rule(report, "R02")


# ---------------------------------------------------------------------------
# R03 — orphans
# ---------------------------------------------------------------------------

def test_r03_task_without_outbound_flow() -> None:
    nodes = [_start(), _task("t1"), _task("t2"), _end()]
    edges = [_edge("s", "t1"), _edge("s", "t2")]
    report = run_lint(_model(nodes, edges))
    assert _has_rule(report, "R03")


# ---------------------------------------------------------------------------
# R04 — declared lanes have content (material)
# ---------------------------------------------------------------------------

def test_r04_declared_lane_without_tasks_is_material() -> None:
    nodes = [_start(), _task("t1", lane="ops"), _end()]
    edges = [_edge("s", "t1"), _edge("t1", "e")]
    report = run_lint(_model(nodes, edges, lanes=["ops", "compliance"]))
    issues = [i for i in report.issues if i.rule_id == "R04"]
    assert len(issues) == 1
    assert issues[0].outcome == MATERIAL


# ---------------------------------------------------------------------------
# R05 — acyclicity
# ---------------------------------------------------------------------------

def test_r05_unmarked_cycle_is_critical() -> None:
    nodes = [_start(), _task("t1"), _task("t2"), _end()]
    edges = [
        _edge("s", "t1"),
        _edge("t1", "t2"),
        _edge("t2", "t1"),  # cycle
        _edge("t2", "e"),
    ]
    report = run_lint(_model(nodes, edges))
    assert _has_rule(report, "R05")


def test_r05_marked_loop_is_allowed() -> None:
    nodes = [
        _start(),
        _task("t1"),
        _task("t2", loop_marker=True),
        _end(),
    ]
    edges = [
        _edge("s", "t1"),
        _edge("t1", "t2"),
        _edge("t2", "t1"),
        _edge("t2", "e"),
    ]
    report = run_lint(_model(nodes, edges))
    assert not _has_rule(report, "R05")


# ---------------------------------------------------------------------------
# R06 — DMN consistency
# ---------------------------------------------------------------------------

def test_r06_dmn_table_missing_is_critical() -> None:
    nodes = [
        _start(),
        _gw("g1", "xor", dmn_table_id="credit-decision"),
        _task("t1"),
        _task("t2"),
        _gw("g2", "xor"),
        _end(),
    ]
    edges = [
        _edge("s", "g1"),
        _edge("g1", "t1", condition="approve"),
        _edge("g1", "t2", condition="reject"),
        _edge("t1", "g2"),
        _edge("t2", "g2"),
        _edge("g2", "e"),
    ]
    report = run_lint(_model(nodes, edges))
    assert _has_rule(report, "R06")


def test_r06_dmn_table_with_uncovered_condition_is_critical() -> None:
    nodes = [
        _start(),
        _gw("g1", "xor", dmn_table_id="credit-decision"),
        _task("t1"),
        _task("t2"),
        _gw("g2", "xor"),
        _end(),
    ]
    edges = [
        _edge("s", "g1"),
        _edge("g1", "t1", condition="approve"),
        _edge("g1", "t2", condition="escalate"),  # not in DMN outcomes
        _edge("t1", "g2"),
        _edge("t2", "g2"),
        _edge("g2", "e"),
    ]
    dmn_tables = {"credit-decision": {"outcomes": ["approve", "reject"]}}
    report = run_lint(_model(nodes, edges, dmn_tables=dmn_tables))
    assert _has_rule(report, "R06")


# ---------------------------------------------------------------------------
# R07 — simulation deadlock
# ---------------------------------------------------------------------------

def test_r07_and_join_with_unreachable_input_deadlocks() -> None:
    # AND-join with one input that is not reachable from start
    nodes = [
        _start(),
        _task("t1"),
        _task("disconnected"),
        _gw("and_join", "and"),
        _end(),
    ]
    edges = [
        _edge("s", "t1"),
        _edge("t1", "and_join"),
        _edge("disconnected", "and_join"),
        _edge("and_join", "e"),
    ]
    report = run_lint(_model(nodes, edges))
    assert _has_rule(report, "R07")


# ---------------------------------------------------------------------------
# R08 — verbal naming (uses lexicon when provided)
# ---------------------------------------------------------------------------

def test_r08_task_name_without_verb_is_material(tmp_path: Path) -> None:
    lexicon = tmp_path / "verbs.json"
    lexicon.write_text(
        json.dumps({"lexicon_verbs_es": {"verbs_infinitive": ["validar", "aprobar"]}}),
        encoding="utf-8",
    )
    nodes = [_start(), _task("t1", name="Pedido importante"), _end()]
    edges = [_edge("s", "t1"), _edge("t1", "e")]
    report = run_lint(
        _model(nodes, edges, prose={"flow": "Pedido importante."}),
        verb_lexicon_path=lexicon,
    )
    issues = [i for i in report.issues if i.rule_id == "R08"]
    assert issues and issues[0].outcome == MATERIAL


def test_r08_with_verb_lexicon_passes(tmp_path: Path) -> None:
    lexicon = tmp_path / "verbs.json"
    lexicon.write_text(
        json.dumps({"lexicon_verbs_es": {"verbs_infinitive": ["validar"]}}),
        encoding="utf-8",
    )
    nodes = [_start(), _task("t1", name="Validar pedido"), _end()]
    edges = [_edge("s", "t1"), _edge("t1", "e")]
    report = run_lint(
        _model(nodes, edges, prose={"flow": "Validar pedido."}),
        verb_lexicon_path=lexicon,
    )
    assert not _has_rule(report, "R08")


# ---------------------------------------------------------------------------
# R09 — XOR exclusive/complete
# ---------------------------------------------------------------------------

def test_r09_xor_with_empty_branch_is_critical() -> None:
    nodes = [
        _start(),
        _gw("g1", "xor"),
        _task("t1"),
        _task("t2"),
        _gw("g2", "xor"),
        _end(),
    ]
    edges = [
        _edge("s", "g1"),
        _edge("g1", "t1", condition="ok"),
        _edge("g1", "t2"),  # empty condition, no default
        _edge("t1", "g2"),
        _edge("t2", "g2"),
        _edge("g2", "e"),
    ]
    report = run_lint(_model(nodes, edges))
    assert _has_rule(report, "R09")


def test_r09_xor_with_default_is_ok() -> None:
    nodes = [
        _start(),
        _gw("g1", "xor"),
        _task("t1"),
        _task("t2"),
        _gw("g2", "xor"),
        _end(),
    ]
    edges = [
        _edge("s", "g1"),
        _edge("g1", "t1", condition="ok"),
        _edge("g1", "t2", default=True),
        _edge("t1", "g2"),
        _edge("t2", "g2"),
        _edge("g2", "e"),
    ]
    report = run_lint(_model(nodes, edges))
    assert not _has_rule(report, "R09")


# ---------------------------------------------------------------------------
# R10 — error handlers on external tasks (material)
# ---------------------------------------------------------------------------

def test_r10_external_task_without_error_handler_is_material() -> None:
    nodes = [_start(), _task("t1", name="Llamar API crédito", external=True), _end()]
    edges = [_edge("s", "t1"), _edge("t1", "e")]
    report = run_lint(
        _model(
            nodes,
            edges,
            prose={"flow": "Llamar API crédito y finalizar."},
        )
    )
    issues = [i for i in report.issues if i.rule_id == "R10"]
    assert issues and issues[0].outcome == MATERIAL


def test_r10_external_task_with_boundary_event_passes() -> None:
    nodes = [
        _start(),
        _task("t1", name="Llamar API crédito", external=True),
        {
            "id": "be1",
            "type": "boundary_event",
            "attached_to": "t1",
            "error_class": "APIError",
        },
        _task("t2", name="Reintentar"),
        _end(),
    ]
    edges = [
        _edge("s", "t1"),
        _edge("t1", "e"),
        _edge("be1", "t2"),
        _edge("t2", "e"),
    ]
    report = run_lint(
        _model(nodes, edges, prose={"flow": "Llamar API crédito y reintentar si falla."})
    )
    assert not _has_rule(report, "R10")


# ---------------------------------------------------------------------------
# R11 — OR with closure
# ---------------------------------------------------------------------------

def test_r11_or_split_without_join_is_material() -> None:
    nodes = [
        _start(),
        _gw("g1", "or"),
        _task("t1"),
        _task("t2"),
        _end("e1"),
        _end("e2"),
    ]
    edges = [
        _edge("s", "g1"),
        _edge("g1", "t1"),
        _edge("g1", "t2"),
        _edge("t1", "e1"),
        _edge("t2", "e2"),
    ]
    report = run_lint(_model(nodes, edges))
    issues = [i for i in report.issues if i.rule_id == "R11"]
    assert issues and issues[0].outcome == MATERIAL


# ---------------------------------------------------------------------------
# R12 — prose ↔ BPMN concordance
# ---------------------------------------------------------------------------

def test_r12_task_unsupported_by_prose_is_critical() -> None:
    nodes = [
        _start(),
        _task("t1", name="Validar pedido"),
        _task("t2", name="Calcular score FICO sintético"),  # not in prose
        _end(),
    ]
    edges = [_edge("s", "t1"), _edge("t1", "t2"), _edge("t2", "e")]
    report = run_lint(
        _model(
            nodes,
            edges,
            prose={"flow": "Se valida el pedido y se finaliza."},
        )
    )
    issues = [i for i in report.issues if i.rule_id == "R12"]
    assert issues and issues[0].outcome == CRITICAL


def test_r12_no_prose_disables_check() -> None:
    nodes = [_start(), _task("t1", name="Cualquier cosa rara"), _end()]
    edges = [_edge("s", "t1"), _edge("t1", "e")]
    report = run_lint(_model(nodes, edges))  # no prose
    assert not _has_rule(report, "R12")


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def test_outcome_critical_when_any_rule_is_critical() -> None:
    nodes = [_start(), _task("t1", name="Pedido"), _end()]
    edges = [_edge("s", "t1"), _edge("t1", "e")]
    report = run_lint(
        _model(
            nodes,
            edges,
            prose={"flow": "Algo completamente distinto sin relación."},
        )
    )
    assert report.outcome == CRITICAL
    assert report.critical_count >= 1


def test_outcome_material_when_only_audit_issues() -> None:
    # Material-only example: declared lane without content, no critical violations
    nodes = [_start(), _task("t1", name="Validar pedido", lane="ops"), _end()]
    edges = [_edge("s", "t1"), _edge("t1", "e")]
    report = run_lint(
        _model(
            nodes,
            edges,
            lanes=["ops", "auditoria"],
            prose={"flow": "Validar pedido."},
        )
    )
    assert report.outcome == MATERIAL
    assert report.critical_count == 0
