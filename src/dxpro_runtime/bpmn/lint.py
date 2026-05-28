"""Deterministic implementation of BPMN-Lint catalog R01..R12 v1.0.

Severity matrix from sinergia_bpmn_lint_catalog-v1.0.md:
  - critical (DENY): R01, R02, R03, R05, R06, R07, R09, R12
  - material (AUDIT): R04, R08, R10, R11
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .model import (
    GATEWAY_AND,
    GATEWAY_OR,
    GATEWAY_XOR,
    NODE_TYPE_BOUNDARY,
    NODE_TYPE_END,
    NODE_TYPE_START,
    BpmnModel,
)

CRITICAL = "DENY"
MATERIAL = "AUDIT"

_CRITICAL_RULES = {"R01", "R02", "R03", "R05", "R06", "R07", "R09", "R12"}


@dataclass
class Issue:
    rule_id: str
    outcome: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "outcome": self.outcome,
            "message": self.message,
            "details": self.details,
        }


@dataclass
class LintReport:
    outcome: str
    issues: list[Issue]
    node_count: int
    edge_count: int

    @property
    def issue_count(self) -> int:
        return len(self.issues)

    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.issues if i.outcome == CRITICAL)

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "issue_count": self.issue_count,
            "critical_count": self.critical_count,
            "issues": [i.to_dict() for i in self.issues],
        }


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_lint(model: BpmnModel, *, verb_lexicon_path: Path | None = None) -> LintReport:
    """Run all 12 rules against `model` and aggregate the report."""
    issues: list[Issue] = []
    issues.extend(rule_r01_gateway_balance(model))
    issues.extend(rule_r02_reachability(model))
    issues.extend(rule_r03_no_orphans(model))
    issues.extend(rule_r04_lanes_have_content(model))
    issues.extend(rule_r05_acyclicity(model))
    issues.extend(rule_r06_dmn_consistency(model))
    issues.extend(rule_r07_simulation(model))
    issues.extend(rule_r08_verbal_naming(model, verb_lexicon_path))
    issues.extend(rule_r09_xor_exclusive_complete(model))
    issues.extend(rule_r10_error_handlers(model))
    issues.extend(rule_r11_or_with_closure(model))
    issues.extend(rule_r12_prose_concordance(model))

    if any(i.outcome == CRITICAL for i in issues):
        outcome = CRITICAL
    elif issues:
        outcome = MATERIAL
    else:
        outcome = "PERMIT"

    return LintReport(
        outcome=outcome,
        issues=issues,
        node_count=len(model.nodes),
        edge_count=len(model.edges),
    )


# ---------------------------------------------------------------------------
# R01 — Gateway balance (XOR opens → XOR closes; AND opens → AND closes)
# ---------------------------------------------------------------------------


def rule_r01_gateway_balance(model: BpmnModel) -> list[Issue]:
    issues: list[Issue] = []
    for subtype in (GATEWAY_XOR, GATEWAY_AND, GATEWAY_OR):
        splits = sum(
            1 for g in model.gateways(subtype) if len(model.outgoing(g.id)) > 1
        )
        joins = sum(
            1 for g in model.gateways(subtype) if len(model.incoming(g.id)) > 1
        )
        if splits != joins:
            issues.append(
                Issue(
                    rule_id="R01",
                    outcome=CRITICAL,
                    message=f"{subtype.upper()} gateways are unbalanced: {splits} splits vs {joins} joins.",
                    details={"subtype": subtype, "splits": splits, "joins": joins},
                )
            )
    return issues


# ---------------------------------------------------------------------------
# R02 — Every non-terminal node reachable from start AND can reach an end
# ---------------------------------------------------------------------------


def rule_r02_reachability(model: BpmnModel) -> list[Issue]:
    starts = [n.id for n in model.starts()]
    ends = [n.id for n in model.ends()]

    issues: list[Issue] = []
    if not starts:
        issues.append(Issue("R02", CRITICAL, "No start event present."))
        return issues
    if not ends:
        issues.append(Issue("R02", CRITICAL, "No end event present."))
        return issues

    forward = _bfs(model, starts, lambda nid: [e.target for e in model.outgoing(nid)])
    backward = _bfs(model, ends, lambda nid: [e.source for e in model.incoming(nid)])

    for node in model.nodes:
        if node.type == NODE_TYPE_BOUNDARY:
            continue  # boundary events are anchored, not part of main flow
        if node.id not in forward:
            issues.append(
                Issue(
                    "R02",
                    CRITICAL,
                    f"Node '{node.id}' is unreachable from any start event.",
                    {"node_id": node.id, "node_name": node.name},
                )
            )
        if node.id not in backward and node.type != NODE_TYPE_END:
            issues.append(
                Issue(
                    "R02",
                    CRITICAL,
                    f"Node '{node.id}' cannot reach any end event.",
                    {"node_id": node.id, "node_name": node.name},
                )
            )
    return issues


# ---------------------------------------------------------------------------
# R03 — No orphan tasks (≥1 inbound and ≥1 outbound, except start/end)
# ---------------------------------------------------------------------------


def rule_r03_no_orphans(model: BpmnModel) -> list[Issue]:
    issues: list[Issue] = []
    for node in model.nodes:
        if node.type in {NODE_TYPE_START, NODE_TYPE_END, NODE_TYPE_BOUNDARY}:
            continue
        if not model.incoming(node.id):
            issues.append(
                Issue(
                    "R03",
                    CRITICAL,
                    f"Node '{node.id}' has no inbound flow.",
                    {"node_id": node.id, "node_name": node.name},
                )
            )
        if not model.outgoing(node.id):
            issues.append(
                Issue(
                    "R03",
                    CRITICAL,
                    f"Node '{node.id}' has no outbound flow.",
                    {"node_id": node.id, "node_name": node.name},
                )
            )
    return issues


# ---------------------------------------------------------------------------
# R04 — Declared lanes must contain ≥1 task
# ---------------------------------------------------------------------------


def rule_r04_lanes_have_content(model: BpmnModel) -> list[Issue]:
    if not model.declared_lanes:
        return []
    occupied: set[str] = {n.lane for n in model.nodes if n.is_task and n.lane}
    issues: list[Issue] = []
    for lane in model.declared_lanes:
        if lane not in occupied:
            issues.append(
                Issue(
                    "R04",
                    MATERIAL,
                    f"Lane '{lane}' is declared but contains no tasks.",
                    {"lane": lane},
                )
            )
    return issues


# ---------------------------------------------------------------------------
# R05 — Acyclicity (loops only allowed if explicitly marked)
# ---------------------------------------------------------------------------


def rule_r05_acyclicity(model: BpmnModel) -> list[Issue]:
    cycles = _find_cycles(model)
    issues: list[Issue] = []
    for cycle in cycles:
        if any(model.node(n) and model.node(n).is_loop_marker for n in cycle):
            continue
        issues.append(
            Issue(
                "R05",
                CRITICAL,
                "Unmarked cycle detected. Use loop_marker=true for intentional loops.",
                {"cycle": cycle},
            )
        )
    return issues


# ---------------------------------------------------------------------------
# R06 — DMN consistency (gateways referencing DMN tables must match)
# ---------------------------------------------------------------------------


def rule_r06_dmn_consistency(model: BpmnModel) -> list[Issue]:
    issues: list[Issue] = []
    for gateway in model.gateways():
        table_id = gateway.dmn_table_id
        if not table_id:
            continue
        table = model.dmn_tables.get(table_id)
        if table is None:
            issues.append(
                Issue(
                    "R06",
                    CRITICAL,
                    f"Gateway '{gateway.id}' references DMN table '{table_id}' that is not provided.",
                    {"gateway_id": gateway.id, "missing_table_id": table_id},
                )
            )
            continue
        gw_outputs = {(e.condition or "").strip() for e in model.outgoing(gateway.id)}
        gw_outputs.discard("")
        table_outcomes = {str(o) for o in table.get("outcomes") or []}
        if table_outcomes and not gw_outputs.issubset(table_outcomes):
            extra = sorted(gw_outputs - table_outcomes)
            issues.append(
                Issue(
                    "R06",
                    CRITICAL,
                    (
                        f"Gateway '{gateway.id}' has outgoing conditions not covered by DMN "
                        f"table '{table_id}': {extra}."
                    ),
                    {"gateway_id": gateway.id, "table_id": table_id, "uncovered_conditions": extra},
                )
            )
    return issues


# ---------------------------------------------------------------------------
# R07 — Simulation: detect AND-join deadlocks (input must all be reachable)
# ---------------------------------------------------------------------------


def rule_r07_simulation(model: BpmnModel) -> list[Issue]:
    issues: list[Issue] = []
    starts = [n.id for n in model.starts()]
    if not starts:
        return issues
    forward = _bfs(model, starts, lambda nid: [e.target for e in model.outgoing(nid)])

    for gateway in model.gateways(GATEWAY_AND):
        incoming = model.incoming(gateway.id)
        if len(incoming) <= 1:
            continue
        unreachable = [e.source for e in incoming if e.source not in forward]
        if unreachable:
            issues.append(
                Issue(
                    "R07",
                    CRITICAL,
                    f"AND-join '{gateway.id}' will deadlock: input(s) unreachable from start.",
                    {"gateway_id": gateway.id, "unreachable_sources": unreachable},
                )
            )
    return issues


# ---------------------------------------------------------------------------
# R08 — Verbal naming for tasks (start with verb from lexicon)
# ---------------------------------------------------------------------------


def rule_r08_verbal_naming(model: BpmnModel, lexicon_path: Path | None) -> list[Issue]:
    verbs = _load_verbs(lexicon_path)
    issues: list[Issue] = []
    for task in (n for n in model.nodes if n.is_task):
        first_token = _first_token(task.name)
        if not first_token:
            issues.append(
                Issue(
                    "R08",
                    MATERIAL,
                    f"Task '{task.id}' has no name.",
                    {"node_id": task.id},
                )
            )
            continue
        if verbs and first_token.lower() not in verbs:
            issues.append(
                Issue(
                    "R08",
                    MATERIAL,
                    f"Task name '{task.name}' does not start with a recognised verb.",
                    {"node_id": task.id, "first_token": first_token},
                )
            )
    return issues


# ---------------------------------------------------------------------------
# R09 — XOR splits must be exclusive (default path or distinct conditions)
# ---------------------------------------------------------------------------


def rule_r09_xor_exclusive_complete(model: BpmnModel) -> list[Issue]:
    issues: list[Issue] = []
    for gateway in model.gateways(GATEWAY_XOR):
        outgoing = model.outgoing(gateway.id)
        if len(outgoing) <= 1:
            continue
        has_default = any(e.is_default for e in outgoing)
        conditions = [(e.condition or "").strip() for e in outgoing if not e.is_default]
        empty = [e for e in outgoing if not (e.condition or "").strip() and not e.is_default]
        if empty:
            issues.append(
                Issue(
                    "R09",
                    CRITICAL,
                    f"XOR gateway '{gateway.id}' has unconditional non-default branches.",
                    {"gateway_id": gateway.id, "empty_branches": len(empty)},
                )
            )
        if not has_default and len(set(conditions)) != len(conditions):
            issues.append(
                Issue(
                    "R09",
                    CRITICAL,
                    f"XOR gateway '{gateway.id}' has duplicate conditions and no default branch.",
                    {"gateway_id": gateway.id, "conditions": conditions},
                )
            )
        if not has_default and not conditions:
            issues.append(
                Issue(
                    "R09",
                    CRITICAL,
                    f"XOR gateway '{gateway.id}' has neither conditions nor a default branch.",
                    {"gateway_id": gateway.id},
                )
            )
    return issues


# ---------------------------------------------------------------------------
# R10 — External / system tasks should have boundary error handlers
# ---------------------------------------------------------------------------


def rule_r10_error_handlers(model: BpmnModel) -> list[Issue]:
    boundaries_by_target: dict[str, list[str]] = defaultdict(list)
    for node in model.nodes:
        if node.type == NODE_TYPE_BOUNDARY and node.attached_to:
            boundaries_by_target[node.attached_to].append(node.id)

    issues: list[Issue] = []
    for task in (n for n in model.nodes if n.is_task and n.is_external):
        if not boundaries_by_target.get(task.id):
            issues.append(
                Issue(
                    "R10",
                    MATERIAL,
                    f"External task '{task.id}' has no error boundary handler.",
                    {"node_id": task.id},
                )
            )
    return issues


# ---------------------------------------------------------------------------
# R11 — Every OR split must have a corresponding OR join
# ---------------------------------------------------------------------------


def rule_r11_or_with_closure(model: BpmnModel) -> list[Issue]:
    issues: list[Issue] = []
    or_splits = [g for g in model.gateways(GATEWAY_OR) if len(model.outgoing(g.id)) > 1]
    or_joins = [g for g in model.gateways(GATEWAY_OR) if len(model.incoming(g.id)) > 1]
    if len(or_splits) > len(or_joins):
        issues.append(
            Issue(
                "R11",
                MATERIAL,
                f"OR splits ({len(or_splits)}) outnumber OR joins ({len(or_joins)}); each OR split needs closure.",
                {"or_splits": len(or_splits), "or_joins": len(or_joins)},
            )
        )
    return issues


# ---------------------------------------------------------------------------
# R12 — Prose ↔ BPMN concordance (every task has prose support)
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(r"[a-záéíóúñü]+", re.IGNORECASE)
_R12_OVERLAP_THRESHOLD = 0.5


def rule_r12_prose_concordance(model: BpmnModel) -> list[Issue]:
    prose_text = _flatten_prose(model.prose)
    if not prose_text:
        return []
    prose_tokens = set(_TOKEN_RE.findall(prose_text.lower()))

    issues: list[Issue] = []
    for task in (n for n in model.nodes if n.is_task):
        task_tokens = set(_TOKEN_RE.findall(task.name.lower()))
        if not task_tokens:
            continue
        overlap = len(task_tokens & prose_tokens) / len(task_tokens)
        if overlap < _R12_OVERLAP_THRESHOLD:
            issues.append(
                Issue(
                    "R12",
                    CRITICAL,
                    f"Task '{task.name}' is not supported by the prose summary (overlap={overlap:.0%}).",
                    {
                        "node_id": task.id,
                        "task_name": task.name,
                        "overlap": round(overlap, 3),
                    },
                )
            )
    return issues


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _bfs(model: BpmnModel, seeds: list[str], next_fn) -> set[str]:
    seen: set[str] = set()
    stack = list(seeds)
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        if not model.has_node(current):
            continue
        stack.extend(next_fn(current))
    return seen


def _find_cycles(model: BpmnModel) -> list[list[str]]:
    """Return one representative cycle per back edge (DFS with stack)."""
    cycles: list[list[str]] = []
    visited: set[str] = set()
    stack: list[str] = []
    on_path: set[str] = set()

    def dfs(node_id: str) -> None:
        if node_id in on_path:
            cycle_start = stack.index(node_id)
            cycles.append(stack[cycle_start:] + [node_id])
            return
        if node_id in visited:
            return
        visited.add(node_id)
        on_path.add(node_id)
        stack.append(node_id)
        for edge in model.outgoing(node_id):
            dfs(edge.target)
        stack.pop()
        on_path.discard(node_id)

    for start in model.starts():
        dfs(start.id)
    # Catch disconnected components
    for node in model.nodes:
        if node.id not in visited:
            dfs(node.id)
    return cycles


def _flatten_prose(prose: dict[str, Any]) -> str:
    if not prose:
        return ""
    parts: list[str] = []

    def walk(value: Any) -> None:
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, dict):
            for v in value.values():
                walk(v)
        elif isinstance(value, list):
            for v in value:
                walk(v)

    walk(prose)
    return " ".join(parts)


def _first_token(text: str) -> str:
    match = _TOKEN_RE.search(text or "")
    return match.group(0) if match else ""


def _load_verbs(lexicon_path: Path | None) -> set[str]:
    if lexicon_path is None or not lexicon_path.exists():
        return set()
    try:
        data = json.loads(lexicon_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return set()
    if isinstance(data, list):
        return {str(v).lower() for v in data}
    if isinstance(data, dict):
        # Bundle format: {"lexicon_verbs_<lang>": {"verbs_infinitive": [...]}}
        for value in data.values():
            if isinstance(value, dict):
                for key in ("verbs_infinitive", "verbs"):
                    items = value.get(key)
                    if isinstance(items, list):
                        return {str(v).lower() for v in items}
        if isinstance(data.get("verbs"), list):
            return {str(v).lower() for v in data["verbs"]}
    return set()


__all__ = [
    "CRITICAL",
    "MATERIAL",
    "Issue",
    "LintReport",
    "rule_r01_gateway_balance",
    "rule_r02_reachability",
    "rule_r03_no_orphans",
    "rule_r04_lanes_have_content",
    "rule_r05_acyclicity",
    "rule_r06_dmn_consistency",
    "rule_r07_simulation",
    "rule_r08_verbal_naming",
    "rule_r09_xor_exclusive_complete",
    "rule_r10_error_handlers",
    "rule_r11_or_with_closure",
    "rule_r12_prose_concordance",
    "run_lint",
]
