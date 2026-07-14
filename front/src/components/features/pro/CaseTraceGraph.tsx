"use client";

/**
 * Grafo 2D estilo Obsidian + filtros por familia (Método / TRIZ / PDF / pipeline).
 */

import { useEffect, useMemo, useRef, useState } from "react";
import {
  forceCenter,
  forceCollide,
  forceLink,
  forceManyBody,
  forceSimulation,
  type SimulationNodeDatum,
  type SimulationLinkDatum,
} from "d3-force";
import {
  activationColor,
  buildNeuralCaseGraph,
  familyLabel,
  GRAPH_FILTERS,
  humanSourceLabel,
  kindHue,
  nodeMatchesFilter,
  statusLabelEs,
  type GraphFilterId,
  type NetNode,
  type NeuralCaseGraph,
} from "@/lib/case-decision-graph";

type Props = { caseData: any };

type SimNode = SimulationNodeDatum & NetNode & { x: number; y: number };
type SimLink = SimulationLinkDatum<SimNode> & { weight: number; live: boolean };

function nodeFill(n: NetNode) {
  if (n.activation === "blocked") return "#b45454";
  if (n.activation === "current") return "#c47a28";
  if (n.status === "done") return kindHue(n.kind);
  if (n.status === "failed") return "#b45454";
  return "#5a5e58";
}

export function CaseTraceGraph({ caseData }: Props) {
  const graph = useMemo(() => buildNeuralCaseGraph(caseData), [caseData]);
  const [filter, setFilter] = useState<GraphFilterId>("all");
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(graph.cursorId);
  const [tick, setTick] = useState(0);
  const wrapRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ w: 900, h: 560 });
  const simNodes = useRef<SimNode[]>([]);
  const simLinks = useRef<SimLink[]>([]);
  const simRef = useRef<ReturnType<typeof forceSimulation<SimNode>> | null>(null);
  const [view, setView] = useState({ x: 0, y: 0, k: 1 });
  const dragPan = useRef<{ x: number; y: number; vx: number; vy: number } | null>(null);

  const filteredNodes = useMemo(() => {
    const q = query.trim().toLowerCase();
    return graph.nodes.filter((n) => {
      if (!n.visible) return false;
      if (!nodeMatchesFilter(n, filter)) return false;
      if (!q) return true;
      return (
        n.label.toLowerCase().includes(q) ||
        n.short.toLowerCase().includes(q) ||
        n.detail.toLowerCase().includes(q) ||
        n.signal.toLowerCase().includes(q) ||
        n.kind.toLowerCase().includes(q) ||
        n.source.toLowerCase().includes(q)
      );
    });
  }, [graph.nodes, filter, query]);

  const filteredIds = useMemo(() => new Set(filteredNodes.map((n) => n.id)), [filteredNodes]);

  useEffect(() => {
    if (graph.cursorId) setSelectedId(graph.cursorId);
  }, [graph.cursorId]);

  useEffect(() => {
    if (selectedId && !filteredIds.has(selectedId)) {
      setSelectedId(filteredNodes[0]?.id ?? null);
    }
  }, [filter, query, filteredIds, filteredNodes, selectedId]);

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => {
      const r = el.getBoundingClientRect();
      setSize({ w: Math.max(280, r.width), h: Math.max(420, r.height) });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    const nodes: SimNode[] = filteredNodes.map((n, i) => {
      const prev = simNodes.current.find((p) => p.id === n.id);
      const angle = (i / Math.max(1, filteredNodes.length)) * Math.PI * 2;
      const radius = 40 + Math.min(180, filteredNodes.length * 8);
      return {
        ...n,
        x: prev?.x ?? size.w / 2 + Math.cos(angle) * radius,
        y: prev?.y ?? size.h / 2 + Math.sin(angle) * radius,
      };
    });
    const byId = new Map(nodes.map((n) => [n.id, n]));
    const links: SimLink[] = graph.synapses
      .filter((s) => s.visible && byId.has(s.from) && byId.has(s.to))
      .map((s) => ({
        source: byId.get(s.from)!,
        target: byId.get(s.to)!,
        weight: s.weight,
        live: s.live,
      }));

    simNodes.current = nodes;
    simLinks.current = links;

    simRef.current?.stop();
    const sim = forceSimulation(nodes)
      .force(
        "link",
        forceLink<SimNode, SimLink>(links)
          .id((d) => d.id)
          .distance((l) => 60 + (1 - l.weight) * 45)
          .strength((l) => 0.3 + l.weight * 0.4)
      )
      .force("charge", forceManyBody().strength(filteredNodes.length < 12 ? -420 : -260))
      .force("center", forceCenter(size.w / 2, size.h / 2))
      .force(
        "collide",
        forceCollide<SimNode>().radius((d) => 20 + (d.weight ?? 0.5) * 16)
      )
      .alpha(1)
      .alphaDecay(0.03)
      .on("tick", () => setTick((t) => t + 1));

    simRef.current = sim;
    return () => {
      sim.stop();
    };
  }, [graph.synapses, filteredNodes, size.w, size.h]);

  const selected = graph.nodes.find((n) => n.id === selectedId) ?? null;
  const connected = useMemo(() => {
    if (!selectedId) return new Set<string>();
    const s = new Set<string>([selectedId]);
    graph.synapses.forEach((e) => {
      if (e.from === selectedId) s.add(e.to);
      if (e.to === selectedId) s.add(e.from);
    });
    return s;
  }, [graph.synapses, selectedId]);

  function focusNode(id: string) {
    setSelectedId(id);
    const n = simNodes.current.find((x) => x.id === id);
    if (n?.x != null && n?.y != null) {
      setView({
        x: size.w / 2 - n.x * 1.15,
        y: size.h / 2 - n.y * 1.15,
        k: Math.max(view.k, 1.15),
      });
    }
  }

  function onWheel(e: React.WheelEvent) {
    e.preventDefault();
    const factor = e.deltaY > 0 ? 0.92 : 1.08;
    setView((v) => ({ ...v, k: Math.min(2.6, Math.max(0.4, v.k * factor)) }));
  }

  function onBgDown(e: React.PointerEvent) {
    if ((e.target as Element).closest("[data-node]")) return;
    dragPan.current = { x: e.clientX, y: e.clientY, vx: view.x, vy: view.y };
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
  }
  function onBgMove(e: React.PointerEvent) {
    if (!dragPan.current) return;
    setView({
      ...view,
      x: dragPan.current.vx + (e.clientX - dragPan.current.x),
      y: dragPan.current.vy + (e.clientY - dragPan.current.y),
    });
  }
  function onBgUp() {
    dragPan.current = null;
  }

  void tick;

  const pct = Math.round(graph.progress * 100);
  const activeFilter = GRAPH_FILTERS.find((f) => f.id === filter)!;
  const showAllLabels = filter !== "all" || view.k >= 1.1 || filteredNodes.length <= 14;

  return (
    <section
      style={{
        border: "1px solid rgba(42,47,40,0.1)",
        borderRadius: 12,
        overflow: "hidden",
        background: "#1a1b19",
      }}
    >
      <header
        style={{
          padding: "12px 16px",
          borderBottom: "1px solid rgba(244,241,234,0.08)",
          display: "grid",
          gap: 10,
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
          <div>
            <p
              style={{
                margin: 0,
                fontSize: 10,
                fontFamily: "IBM Plex Mono, monospace",
                color: "#9b6d4d",
                letterSpacing: "0.1em",
              }}
            >
              MAPA · {graph.stats.clientName.toUpperCase()}
            </p>
            <p style={{ margin: "4px 0 0", fontSize: 13, color: "rgba(244,241,234,0.7)" }}>
              {activeFilter.hint} · {filteredNodes.length} nodos visibles · {pct}% ciclo
            </p>
          </div>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Buscar: TRIZ, tesis, PDF, epojé…"
            style={{
              minWidth: 220,
              flex: "1 1 220px",
              maxWidth: 340,
              background: "rgba(244,241,234,0.06)",
              border: "1px solid rgba(244,241,234,0.14)",
              color: "#f4f1ea",
              padding: "8px 12px",
              fontSize: 12,
              fontFamily: "IBM Plex Mono, monospace",
              borderRadius: 4,
            }}
          />
        </div>

        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
          {GRAPH_FILTERS.map((f) => {
            const on = filter === f.id;
            return (
              <button
                key={f.id}
                type="button"
                onClick={() => setFilter(f.id)}
                title={f.hint}
                style={{
                  padding: "6px 10px",
                  borderRadius: 4,
                  border: on ? "1px solid rgba(196,122,40,0.55)" : "1px solid rgba(244,241,234,0.12)",
                  background: on ? "rgba(196,122,40,0.18)" : "rgba(244,241,234,0.04)",
                  color: on ? "#f4f1ea" : "rgba(244,241,234,0.7)",
                  fontSize: 10,
                  fontFamily: "IBM Plex Mono, monospace",
                  cursor: "pointer",
                }}
              >
                {f.label}
              </button>
            );
          })}
        </div>

        <p style={{ margin: 0, fontSize: 11, color: "rgba(244,241,234,0.42)", lineHeight: 1.45 }}>
          <span style={{ color: "#3f6b4e" }}>Verde</span> = método (epojé · 7P · Φ) ·{" "}
          <span style={{ color: "#c47a28" }}>Ámbar</span> = TRIZ/motor ·{" "}
          <span style={{ color: "#243c4f" }}>Azul</span> = síntesis G10–G14 ·{" "}
          <span style={{ color: "#56624b" }}>Verde oliva</span> = docs/PDF · Lista izquierda = saltar al nodo.
        </p>
      </header>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(200px, 240px) minmax(0, 1fr)",
          minHeight: 460,
        }}
        className="cw-map-grid"
      >
        <aside
          style={{
            borderRight: "1px solid rgba(244,241,234,0.08)",
            maxHeight: "min(68vh, 620px)",
            overflow: "auto",
            background: "rgba(0,0,0,0.2)",
          }}
        >
          <p
            style={{
              margin: 0,
              padding: "10px 12px 6px",
              fontSize: 9,
              fontFamily: "IBM Plex Mono, monospace",
              color: "rgba(244,241,234,0.4)",
              letterSpacing: "0.08em",
              position: "sticky",
              top: 0,
              background: "#141512",
              zIndex: 1,
            }}
          >
            ÍNDICE · {filteredNodes.length}
          </p>
          {filteredNodes.length === 0 && (
            <p style={{ margin: "12px", fontSize: 12, color: "rgba(244,241,234,0.45)" }}>
              Nada con este filtro. Probá «Todo» o «Método».
            </p>
          )}
          {filteredNodes.map((n) => {
            const on = n.id === selectedId;
            return (
              <button
                key={n.id}
                type="button"
                onClick={() => focusNode(n.id)}
                style={{
                  display: "block",
                  width: "100%",
                  textAlign: "left",
                  padding: "9px 12px",
                  border: "none",
                  borderBottom: "1px solid rgba(244,241,234,0.05)",
                  background: on ? "rgba(196,122,40,0.16)" : "transparent",
                  color: "#f4f1ea",
                  cursor: "pointer",
                }}
              >
                <span style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <span
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: 999,
                      background: nodeFill(n),
                      flexShrink: 0,
                    }}
                  />
                  <span style={{ fontSize: 12, lineHeight: 1.25 }}>{n.label}</span>
                </span>
                <span
                  style={{
                    display: "block",
                    marginTop: 3,
                    marginLeft: 16,
                    fontSize: 9,
                    fontFamily: "IBM Plex Mono, monospace",
                    color: "rgba(244,241,234,0.4)",
                  }}
                >
                  {familyLabel(n.kind)} · {n.short} · {statusLabelEs(n.status)}
                </span>
              </button>
            );
          })}
        </aside>

        <div
          ref={wrapRef}
          style={{ position: "relative", height: "min(68vh, 620px)", minHeight: 420, touchAction: "none" }}
          onWheel={onWheel}
          onPointerDown={onBgDown}
          onPointerMove={onBgMove}
          onPointerUp={onBgUp}
        >
          <svg width={size.w} height={size.h} style={{ display: "block", width: "100%", height: "100%" }}>
            <g transform={`translate(${view.x},${view.y}) scale(${view.k})`}>
              {simLinks.current.map((l, i) => {
                const a = l.source as SimNode;
                const b = l.target as SimNode;
                if (a.x == null || b.x == null) return null;
                const hot = selectedId != null && (a.id === selectedId || b.id === selectedId);
                const dim = selectedId != null && !hot;
                return (
                  <line
                    key={i}
                    x1={a.x}
                    y1={a.y}
                    x2={b.x}
                    y2={b.y}
                    stroke={l.live ? "#c47a28" : hot ? "#7d9b82" : "#4a4d47"}
                    strokeWidth={hot ? 2.2 : l.live ? 1.6 : 1}
                    strokeOpacity={dim ? 0.15 : hot ? 0.9 : 0.4}
                  />
                );
              })}
              {simNodes.current.map((n) => {
                const r = 7 + (n.weight ?? 0.5) * 10;
                const dim = selectedId != null && !connected.has(n.id);
                const sel = n.id === selectedId;
                const showLabel =
                  showAllLabels ||
                  sel ||
                  n.kind === "phenomenon" ||
                  n.kind === "triz" ||
                  n.kind === "document" ||
                  n.kind === "finding" ||
                  (n.weight ?? 0) > 0.85;
                return (
                  <g
                    key={n.id}
                    data-node
                    transform={`translate(${n.x},${n.y})`}
                    style={{ cursor: "pointer" }}
                    onClick={(e) => {
                      e.stopPropagation();
                      focusNode(n.id);
                    }}
                    opacity={dim ? 0.22 : 1}
                  >
                    {sel && <circle r={r + 6} fill="none" stroke="#c47a28" strokeWidth={1.5} opacity={0.7} />}
                    <circle
                      r={r}
                      fill={nodeFill(n)}
                      stroke={sel ? "#f4f1ea" : "rgba(244,241,234,0.25)"}
                      strokeWidth={sel ? 1.5 : 0.8}
                    />
                    {showLabel && (
                      <text
                        y={r + 14}
                        textAnchor="middle"
                        fill="rgba(244,241,234,0.9)"
                        fontSize={11}
                        fontFamily="IBM Plex Mono, monospace"
                        style={{ pointerEvents: "none" }}
                      >
                        {n.short.length > 16 ? `${n.short.slice(0, 15)}…` : n.short}
                      </text>
                    )}
                  </g>
                );
              })}
            </g>
          </svg>

          {selected && (
            <aside
              style={{
                position: "absolute",
                top: 12,
                right: 12,
                width: "min(300px, calc(100% - 24px))",
                maxHeight: "calc(100% - 24px)",
                overflow: "auto",
                background: "rgba(34,37,34,0.96)",
                border: "1px solid rgba(244,241,234,0.12)",
                borderRadius: 10,
                padding: 14,
                color: "#f4f1ea",
                zIndex: 2,
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                <p style={{ margin: 0, fontSize: 10, fontFamily: "IBM Plex Mono, monospace", color: "#9b6d4d" }}>
                  {familyLabel(selected.kind)} · {selected.layerName}
                </p>
                <button
                  type="button"
                  onClick={() => setSelectedId(null)}
                  style={{
                    border: "none",
                    background: "transparent",
                    color: "rgba(244,241,234,0.45)",
                    cursor: "pointer",
                    fontFamily: "IBM Plex Mono, monospace",
                    fontSize: 11,
                  }}
                >
                  cerrar
                </button>
              </div>
              <h3
                style={{
                  margin: "8px 0 0",
                  fontFamily: "Cormorant Garamond, Georgia, serif",
                  fontWeight: 500,
                  fontSize: 20,
                  lineHeight: 1.15,
                }}
              >
                {selected.label}
              </h3>
              <p
                style={{
                  margin: "8px 0 0",
                  fontSize: 10,
                  fontFamily: "IBM Plex Mono, monospace",
                  color: activationColor(selected.activation),
                }}
              >
                {statusLabelEs(selected.status)} · peso {Math.round((selected.weight ?? 0) * 100)}%
              </p>
              <p style={{ margin: "12px 0 0", fontSize: 12, color: "#9bb09a", lineHeight: 1.45 }}>{selected.signal}</p>
              <p style={{ margin: "8px 0 0", fontSize: 13, color: "rgba(244,241,234,0.85)", lineHeight: 1.5 }}>
                {selected.detail}
              </p>
              {selected.meta?.en_informe || selected.kind === "document" || selected.kind === "finding" ? (
                <p
                  style={{
                    margin: "12px 0 0",
                    fontSize: 10,
                    fontFamily: "IBM Plex Mono, monospace",
                    color: "#56624b",
                  }}
                >
                  → Aparece en documentos / informe del caso
                </p>
              ) : null}
              <p
                style={{
                  margin: "14px 0 0",
                  fontSize: 9,
                  fontFamily: "IBM Plex Mono, monospace",
                  color: "#9b6d4d",
                  letterSpacing: "0.08em",
                }}
              >
                FUENTE
              </p>
              <p
                style={{
                  margin: "4px 0 0",
                  fontSize: 11,
                  fontFamily: "IBM Plex Mono, monospace",
                  color: "rgba(244,241,234,0.45)",
                  wordBreak: "break-all",
                }}
              >
                {selected.source || "—"}
              </p>
            </aside>
          )}

          <p
            style={{
              position: "absolute",
              left: 12,
              bottom: 12,
              margin: 0,
              fontSize: 10,
              fontFamily: "IBM Plex Mono, monospace",
              color: "rgba(244,241,234,0.4)",
            }}
          >
            Filtro arriba · lista izquierda · scroll zoom · arrastrá fondo
          </p>
        </div>
      </div>

      <style>{`
        @media (max-width: 820px) {
          .cw-map-grid { grid-template-columns: 1fr !important; }
          .cw-map-grid > aside { max-height: 180px !important; border-right: none !important; border-bottom: 1px solid rgba(244,241,234,0.08); }
        }
      `}</style>
    </section>
  );
}

export type { NeuralCaseGraph };
