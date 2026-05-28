"""Typed access to a BPMN process graph.

The runtime accepts a JSON-shaped BPMN model (list of nodes, list of edges)
because that's what crosses the API boundary. This module wraps that dict
into a typed graph that the lint rules can traverse without re-validating.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Iterable

NODE_TYPE_START = "start_event"
NODE_TYPE_END = "end_event"
NODE_TYPE_TASK = "task"
NODE_TYPE_GATEWAY = "gateway"
NODE_TYPE_INTERMEDIATE = "intermediate_event"
NODE_TYPE_BOUNDARY = "boundary_event"

GATEWAY_XOR = "xor"
GATEWAY_AND = "and"
GATEWAY_OR = "or"


@dataclass(frozen=True)
class Node:
    id: str
    type: str
    name: str = ""
    lane: str | None = None
    gateway_subtype: str | None = None  # xor | and | or
    attached_to: str | None = None  # for boundary events
    is_external: bool = False
    is_loop_marker: bool = False
    dmn_table_id: str | None = None
    error_class: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def is_gateway(self) -> bool:
        return self.type == NODE_TYPE_GATEWAY

    @property
    def is_task(self) -> bool:
        return self.type == NODE_TYPE_TASK


@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    condition: str = ""
    is_default: bool = False
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class BpmnModel:
    nodes: list[Node]
    edges: list[Edge]
    declared_lanes: tuple[str, ...] = ()
    prose: dict[str, Any] = field(default_factory=dict)
    dmn_tables: dict[str, dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._by_id: dict[str, Node] = {n.id: n for n in self.nodes}
        self._outgoing: dict[str, list[Edge]] = defaultdict(list)
        self._incoming: dict[str, list[Edge]] = defaultdict(list)
        for edge in self.edges:
            self._outgoing[edge.source].append(edge)
            self._incoming[edge.target].append(edge)

    # -- access helpers ---------------------------------------------------

    def node(self, node_id: str) -> Node | None:
        return self._by_id.get(node_id)

    def has_node(self, node_id: str) -> bool:
        return node_id in self._by_id

    def outgoing(self, node_id: str) -> list[Edge]:
        return self._outgoing.get(node_id, [])

    def incoming(self, node_id: str) -> list[Edge]:
        return self._incoming.get(node_id, [])

    def filter(self, **conditions: Any) -> Iterable[Node]:
        for node in self.nodes:
            if all(getattr(node, k, None) == v for k, v in conditions.items()):
                yield node

    def starts(self) -> list[Node]:
        return [n for n in self.nodes if n.type == NODE_TYPE_START]

    def ends(self) -> list[Node]:
        return [n for n in self.nodes if n.type == NODE_TYPE_END]

    def gateways(self, subtype: str | None = None) -> list[Node]:
        gws = [n for n in self.nodes if n.is_gateway]
        if subtype is None:
            return gws
        return [n for n in gws if n.gateway_subtype == subtype]


def parse_model(payload: dict[str, Any]) -> BpmnModel:
    """Build a BpmnModel from the raw API payload."""
    raw_nodes = payload.get("nodes") or []
    raw_edges = payload.get("edges") or []

    nodes = [_parse_node(n) for n in raw_nodes if isinstance(n, dict)]
    edges = [_parse_edge(e) for e in raw_edges if isinstance(e, dict)]
    declared_lanes = tuple(payload.get("lanes") or ())

    return BpmnModel(
        nodes=nodes,
        edges=edges,
        declared_lanes=declared_lanes,
        prose=payload.get("prose") or {},
        dmn_tables=payload.get("dmn_tables") or {},
    )


def _parse_node(raw: dict[str, Any]) -> Node:
    return Node(
        id=str(raw.get("id", "")),
        type=str(raw.get("type", "")),
        name=str(raw.get("name", "")),
        lane=raw.get("lane"),
        gateway_subtype=raw.get("gateway_subtype") or raw.get("subtype"),
        attached_to=raw.get("attached_to"),
        is_external=bool(raw.get("external") or raw.get("system_call")),
        is_loop_marker=bool(raw.get("loop_marker")),
        dmn_table_id=raw.get("dmn_table_id"),
        error_class=raw.get("error_class"),
        raw=raw,
    )


def _parse_edge(raw: dict[str, Any]) -> Edge:
    return Edge(
        source=str(raw.get("source", "")),
        target=str(raw.get("target", "")),
        condition=str(raw.get("condition") or ""),
        is_default=bool(raw.get("default")),
        raw=raw,
    )
