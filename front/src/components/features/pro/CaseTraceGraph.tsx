"use client";

/**
 * Mapa de traza — grafo force tipo Obsidian (red de conexiones).
 * companion: panel junto al workspace · full: vista Mapa ampliada.
 * Inventario visible del ciclo; no es el grafo interno de un modelo.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import {
  forceCenter,
  forceCollide,
  forceLink,
  forceManyBody,
  forceSimulation,
  forceX,
  forceY,
  type SimulationLinkDatum,
  type SimulationNodeDatum,
} from "d3-force";
import {
  buildNeuralCaseGraph,
  familyLabel,
  GRAPH_FILTERS,
  humanSourceLabel,
  kindHue,
  nodeMatchesFilter,
  statusLabelEs,
  type GraphFilterId,
  type NetNode,
} from "@/lib/case-decision-graph";
import type { BrainSectionHint, BrainVariant } from "@/components/features/pro/CaseDecisionBrain";

type Props = {
  caseData: any;
  variant?: BrainVariant;
  section?: BrainSectionHint;
};

type SimNode = SimulationNodeDatum & NetNode & { x: number; y: number; degree: number };
type SimLink = SimulationLinkDatum<SimNode> & { weight: number; live: boolean };

const SECTION_FILTER: Partial<Record<BrainSectionHint, GraphFilterId>> = {
  encargo: "all",
  metodo: "metodo",
  campo: "field",
  sintesis: "pipeline",
  docs: "report",
  sello: "seal",
  mapa: "all",
};

function nodeFill(n: NetNode) {
  if (n.activation === "blocked" || n.status === "failed") return "#8b3a3a";
  if (n.activation === "current" || n.status === "running") return "#9b6d4d";
  if (n.status === "done") return kindHue(n.kind);
  return "#a8a49c";
}

/** Obsidian: más links → círculo más grande. */
function nodeRadius(n: { weight?: number; kind?: string; degree?: number }) {
  const deg = n.degree ?? 0;
  const hub = 7 + Math.sqrt(deg) * 4.2 + (n.weight ?? 0.5) * 4;
  if (n.kind === "phenomenon") return Math.max(hub, 15);
  return hub;
}

function edgeAttach(
  ax: number,
  ay: number,
  bx: number,
  by: number,
  ra: number,
  rb: number
): { x1: number; y1: number; x2: number; y2: number } | null {
  const dx = bx - ax;
  const dy = by - ay;
  const dist = Math.hypot(dx, dy);
  if (!Number.isFinite(dist) || dist < 1) return null;
  const pad = 1.2;
  if (ra + rb + pad * 2 >= dist) return null;
  const ux = dx / dist;
  const uy = dy / dist;
  return {
    x1: ax + ux * (ra + pad),
    y1: ay + uy * (ra + pad),
    x2: bx - ux * (rb + pad),
    y2: by - uy * (rb + pad),
  };
}

function resolveEnd(end: string | number | SimNode, byId: Map<string, SimNode>): SimNode | null {
  if (end && typeof end === "object" && "id" in end) return byId.get(end.id) ?? end;
  if (typeof end === "string") return byId.get(end) ?? null;
  return null;
}

function linkEnds(l: SimLink, byId: Map<string, SimNode>): { a: SimNode; b: SimNode } | null {
  const a = resolveEnd(l.source as string | number | SimNode, byId);
  const b = resolveEnd(l.target as string | number | SimNode, byId);
  if (!a || !b) return null;
  return { a, b };
}

export function CaseTraceGraph({ caseData, variant = "full", section }: Props) {
  const companion = variant === "companion";
  const graph = useMemo(() => buildNeuralCaseGraph(caseData), [caseData]);
  const [filter, setFilter] = useState<GraphFilterId>("all");
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(graph.cursorId);
  const [tick, setTick] = useState(0);
  const wrapRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ w: companion ? 420 : 900, h: companion ? 420 : 560 });
  const simNodes = useRef<SimNode[]>([]);
  const simLinks = useRef<SimLink[]>([]);
  const simRef = useRef<ReturnType<typeof forceSimulation<SimNode>> | null>(null);
  const [view, setView] = useState({ x: 0, y: 0, k: 1 });
  const viewRef = useRef(view);
  const dragPan = useRef<{ x: number; y: number; vx: number; vy: number } | null>(null);
  const fitAfterLayout = useRef(true);

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
        n.kind.toLowerCase().includes(q)
      );
    });
  }, [graph.nodes, filter, query]);

  const nodeIdsKey = useMemo(() => filteredNodes.map((n) => n.id).join(","), [filteredNodes]);
  const layoutKey = useMemo(
    () => `${filter}|${query}|${size.w}x${size.h}|${nodeIdsKey}`,
    [filter, query, size.w, size.h, nodeIdsKey]
  );

  useEffect(() => {
    viewRef.current = view;
  }, [view]);

  useEffect(() => {
    if (!section) return;
    const next = SECTION_FILTER[section] ?? "all";
    setFilter(next);
    fitAfterLayout.current = true;
  }, [section]);

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
    let lastW = 0;
    let lastH = 0;
    const ro = new ResizeObserver(() => {
      const r = el.getBoundingClientRect();
      const w = Math.max(260, r.width);
      const h = Math.max(companion ? 320 : 400, r.height);
      if (Math.abs(w - lastW) < 6 && Math.abs(h - lastH) < 6) return;
      lastW = w;
      lastH = h;
      setSize({ w, h });
      fitAfterLayout.current = true;
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, [companion]);

  function computeFit(nodes: SimNode[], w: number, h: number) {
    const placed = nodes.filter(
      (n) => typeof n.x === "number" && typeof n.y === "number" && Number.isFinite(n.x) && Number.isFinite(n.y)
    );
    if (placed.length === 0 || w < 40 || h < 40) return { x: 0, y: 0, k: 1 };
    let minX = Infinity;
    let maxX = -Infinity;
    let minY = Infinity;
    let maxY = -Infinity;
    placed.forEach((n) => {
      const r = nodeRadius(n);
      minX = Math.min(minX, n.x! - r - 20);
      maxX = Math.max(maxX, n.x! + r + 20);
      minY = Math.min(minY, n.y! - r - 8);
      maxY = Math.max(maxY, n.y! + r + 18);
    });
    const bw = Math.max(80, maxX - minX);
    const bh = Math.max(80, maxY - minY);
    const pad = companion ? 26 : 34;
    const kRaw = Math.min((w - pad * 2) / bw, (h - pad * 2) / bh, 1.4);
    const k = Number.isFinite(kRaw) ? Math.max(0.14, kRaw) : 1;
    const cx = (minX + maxX) / 2;
    const cy = (minY + maxY) / 2;
    const x = w / 2 - cx * k;
    const y = h / 2 - cy * k;
    return {
      k,
      x: Number.isFinite(x) ? x : 0,
      y: Number.isFinite(y) ? y : 0,
    };
  }

  function fitAll() {
    try {
      setView(computeFit(simNodes.current, size.w, size.h));
    } catch {
      /* ignore */
    }
  }

  // Force tipo Obsidian: center / repel / link / distance → clusters orgánicos.
  useEffect(() => {
    const nCount = filteredNodes.length;
    const cx = size.w / 2;
    const cy = size.h / 2;
    const seedR = Math.min(size.w, size.h) * 0.22;

    const degree = new Map<string, number>();
    const visibleIds = new Set(filteredNodes.map((n) => n.id));
    graph.synapses.forEach((s) => {
      if (!s.visible || !visibleIds.has(s.from) || !visibleIds.has(s.to) || s.from === s.to) return;
      degree.set(s.from, (degree.get(s.from) ?? 0) + 1);
      degree.set(s.to, (degree.get(s.to) ?? 0) + 1);
    });

    const nodes: SimNode[] = filteredNodes.map((n, i) => {
      const prev = simNodes.current.find((p) => p.id === n.id);
      const a = (i / Math.max(nCount, 1)) * Math.PI * 2 - Math.PI / 2;
      const jitter = ((i * 17) % 9) - 4;
      return {
        ...n,
        degree: degree.get(n.id) ?? 0,
        x: prev?.x ?? cx + Math.cos(a) * seedR + jitter,
        y: prev?.y ?? cy + Math.sin(a) * seedR + jitter * 0.6,
        fx: undefined,
        fy: undefined,
        vx: 0,
        vy: 0,
      };
    });

    const links: SimLink[] = graph.synapses
      .filter((s) => s.visible && visibleIds.has(s.from) && visibleIds.has(s.to) && s.from !== s.to)
      .map((s) => ({
        source: s.from,
        target: s.to,
        weight: s.weight,
        live: s.live,
      }));

    simNodes.current = nodes;
    simLinks.current = links;

    // Escalado estilo Obsidian forces (viewport más chico que un vault).
    const repel = nCount > 28 ? -520 : nCount > 14 ? -380 : -260;
    const linkDist = companion ? 54 : 72;
    const centerPull = companion ? 0.22 : 0.16;

    let raf = 0;
    const bump = () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => setTick((t) => t + 1));
    };

    const freeze = () => {
      nodes.forEach((n) => {
        if (typeof n.x === "number" && typeof n.y === "number") {
          n.fx = n.x;
          n.fy = n.y;
        }
      });
      sim.alpha(0).stop();
      bump();
      if (fitAfterLayout.current) {
        fitAfterLayout.current = false;
        try {
          setView(computeFit(nodes, size.w, size.h));
        } catch {
          /* ignore */
        }
      }
    };

    simRef.current?.stop();
    const sim = forceSimulation<SimNode>(nodes)
      .force(
        "link",
        forceLink<SimNode, SimLink>(links)
          .id((d) => d.id)
          .distance((l) => linkDist + (1 - l.weight) * 36)
          .strength((l) => 0.35 + l.weight * 0.35)
      )
      .force(
        "charge",
        forceManyBody()
          .strength(repel)
          .distanceMax(Math.min(size.w, size.h) * 0.85)
      )
      .force("center", forceCenter(cx, cy).strength(centerPull))
      .force("x", forceX(cx).strength(0.04))
      .force("y", forceY(cy).strength(0.04))
      .force(
        "collide",
        forceCollide<SimNode>()
          .radius((d) => nodeRadius(d) + (companion ? 10 : 14))
          .strength(0.95)
          .iterations(3)
      )
      .alpha(1)
      .alphaDecay(0.028)
      .velocityDecay(0.35)
      .on("tick", bump)
      .on("end", freeze);

    simRef.current = sim;
    bump();

    return () => {
      cancelAnimationFrame(raf);
      sim.stop();
    };
  }, [layoutKey]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      e.stopPropagation();
      const rect = el.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;
      const cur = viewRef.current;
      const k0 = cur.k > 0.0001 ? cur.k : 1;
      const factor = e.deltaY > 0 ? 0.9 : 1.11;
      const nextK = Math.min(3.4, Math.max(0.12, k0 * factor));
      const wx = (mx - cur.x) / k0;
      const wy = (my - cur.y) / k0;
      const nx = mx - wx * nextK;
      const ny = my - wy * nextK;
      if (!Number.isFinite(nextK) || !Number.isFinite(nx) || !Number.isFinite(ny)) return;
      setView({ k: nextK, x: nx, y: ny });
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, [size.w, size.h]);

  void tick;

  const nodeById = useMemo(() => {
    const m = new Map<string, SimNode>();
    simNodes.current.forEach((n) => m.set(n.id, n));
    return m;
  }, [tick]);

  const selected = filteredNodes.find((n) => n.id === selectedId) ?? null;
  const connected = useMemo(() => {
    const ids = new Set<string>();
    if (!selectedId) return ids;
    ids.add(selectedId);
    simLinks.current.forEach((l) => {
      const ends = linkEnds(l, nodeById);
      if (!ends) return;
      if (ends.a.id === selectedId) ids.add(ends.b.id);
      if (ends.b.id === selectedId) ids.add(ends.a.id);
    });
    return ids;
  }, [selectedId, tick, nodeById]);

  function focusNode(id: string) {
    setSelectedId(id);
  }

  function applyFilter(id: GraphFilterId) {
    setFilter(id);
    fitAfterLayout.current = true;
  }

  function onBgDown(e: React.PointerEvent) {
    if ((e.target as HTMLElement).closest("[data-node]")) return;
    dragPan.current = { x: e.clientX, y: e.clientY, vx: viewRef.current.x, vy: viewRef.current.y };
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
  }
  function onBgMove(e: React.PointerEvent) {
    const drag = dragPan.current;
    if (!drag) return;
    const x = drag.vx + (e.clientX - drag.x);
    const y = drag.vy + (e.clientY - drag.y);
    setView((v) => ({ ...v, x, y }));
  }
  function onBgUp(e?: React.PointerEvent) {
    dragPan.current = null;
    if (e) {
      try {
        (e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId);
      } catch {
        /* already released */
      }
    }
  }

  const pct = Math.round(graph.progress * 100);

  return (
    <section
      style={{
        border: "1px solid rgba(23,23,23,0.12)",
        background: "#f4f1ea",
        overflow: "hidden",
        height: companion ? "100%" : undefined,
        display: "flex",
        flexDirection: "column",
      }}
    >
      <header
        style={{
          padding: companion ? "12px 14px" : "14px 16px",
          borderBottom: "1px solid rgba(23,23,23,0.1)",
          display: "grid",
          gap: companion ? 10 : 12,
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "flex-start" }}>
          <div style={{ minWidth: 0 }}>
            <p
              style={{
                margin: 0,
                fontSize: 10,
                fontFamily: "IBM Plex Mono, monospace",
                color: "#56624b",
                letterSpacing: "0.1em",
              }}
            >
              RED DEL CASO
            </p>
            <p
              style={{
                margin: "4px 0 0",
                fontFamily: "Cormorant Garamond, Georgia, serif",
                fontSize: companion ? 20 : 26,
                fontWeight: 500,
                color: "#171717",
                lineHeight: 1.05,
              }}
            >
              {graph.stats.clientName}
            </p>
            <p style={{ margin: "4px 0 0", fontSize: 12, color: "#706f69" }}>
              {graph.phaseLabel} · {pct}% · {filteredNodes.length} nodos · {simLinks.current.length} vínculos
            </p>
          </div>
          {!companion && (
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <button
                type="button"
                onClick={fitAll}
                style={{
                  padding: "8px 10px",
                  border: "1px solid rgba(23,23,23,0.14)",
                  background: "#fff",
                  fontSize: 10,
                  fontFamily: "IBM Plex Mono, monospace",
                  color: "#706f69",
                  cursor: "pointer",
                  whiteSpace: "nowrap",
                }}
              >
                Ver todo
              </button>
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Buscar…"
                style={{
                  width: 140,
                  padding: "8px 10px",
                  border: "1px solid rgba(23,23,23,0.14)",
                  background: "#fff",
                  fontSize: 12,
                  fontFamily: "IBM Plex Mono, monospace",
                  color: "#171717",
                }}
              />
            </div>
          )}
          {companion && (
            <button
              type="button"
              onClick={fitAll}
              style={{
                padding: "7px 10px",
                border: "1px solid rgba(23,23,23,0.14)",
                background: "#fff",
                fontSize: 10,
                fontFamily: "IBM Plex Mono, monospace",
                color: "#706f69",
                cursor: "pointer",
              }}
            >
              Ver todo
            </button>
          )}
        </div>

        <div style={{ display: "flex", gap: 0, flexWrap: "wrap", border: "1px solid rgba(23,23,23,0.1)" }}>
          {GRAPH_FILTERS.map((f) => {
            const on = filter === f.id;
            return (
              <button
                key={f.id}
                type="button"
                onClick={() => applyFilter(f.id)}
                title={f.hint}
                style={{
                  padding: companion ? "7px 9px" : "8px 11px",
                  border: "none",
                  borderRight: "1px solid rgba(23,23,23,0.08)",
                  background: on ? "#171717" : "#fff",
                  color: on ? "#f4f1ea" : "#706f69",
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
      </header>

      <div
        className="cw-map-grid"
        style={{
          display: "grid",
          gridTemplateColumns: companion ? "1fr" : "minmax(200px, 230px) minmax(0, 1fr)",
          flex: 1,
          minHeight: companion ? 340 : 460,
        }}
      >
        {!companion && (
          <aside
            style={{
              borderRight: "1px solid rgba(23,23,23,0.1)",
              maxHeight: "min(68vh, 620px)",
              overflow: "auto",
              background: "#fff",
            }}
          >
            <p
              style={{
                margin: 0,
                padding: "10px 12px 6px",
                fontSize: 9,
                fontFamily: "IBM Plex Mono, monospace",
                color: "#706f69",
                letterSpacing: "0.08em",
                position: "sticky",
                top: 0,
                background: "#fff",
                zIndex: 1,
                borderBottom: "1px solid rgba(23,23,23,0.06)",
              }}
            >
              ÍNDICE · {filteredNodes.length}
            </p>
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
                    padding: "10px 12px",
                    border: "none",
                    borderBottom: "1px solid rgba(23,23,23,0.05)",
                    background: on ? "rgba(86,98,75,0.1)" : "transparent",
                    color: "#171717",
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
                    <span style={{ fontSize: 12, lineHeight: 1.3 }}>{n.label}</span>
                  </span>
                  <span
                    style={{
                      display: "block",
                      marginTop: 3,
                      marginLeft: 16,
                      fontSize: 10,
                      fontFamily: "IBM Plex Mono, monospace",
                      color: "#706f69",
                    }}
                  >
                    {familyLabel(n.kind)} · {statusLabelEs(n.status)}
                  </span>
                </button>
              );
            })}
          </aside>
        )}

        <div style={{ display: "flex", flexDirection: "column", minWidth: 0, minHeight: 0 }}>
          <div
            ref={wrapRef}
            style={{
              position: "relative",
              height: companion ? "min(44vh, 400px)" : "min(58vh, 560px)",
              minHeight: companion ? 280 : 360,
              background:
                "radial-gradient(ellipse at 50% 45%, #f7f4ed 0%, #ebe6dc 62%, #e4dfd4 100%)",
              touchAction: "none",
              overscrollBehavior: "contain",
              flex: "0 0 auto",
            }}
            onPointerDown={onBgDown}
            onPointerMove={onBgMove}
            onPointerUp={onBgUp}
            onPointerCancel={onBgUp}
          >
            <svg
              width="100%"
              height="100%"
              viewBox={`0 0 ${Math.max(1, size.w)} ${Math.max(1, size.h)}`}
              preserveAspectRatio="xMidYMid meet"
              style={{ display: "block" }}
            >
              <g
                transform={`translate(${Number.isFinite(view.x) ? view.x : 0},${Number.isFinite(view.y) ? view.y : 0}) scale(${
                  Number.isFinite(view.k) && view.k > 0 ? view.k : 1
                })`}
              >
                {simLinks.current.map((l, i) => {
                  const ends = linkEnds(l, nodeById);
                  if (!ends) return null;
                  const { a, b } = ends;
                  if (
                    typeof a.x !== "number" ||
                    typeof a.y !== "number" ||
                    typeof b.x !== "number" ||
                    typeof b.y !== "number" ||
                    !Number.isFinite(a.x) ||
                    !Number.isFinite(a.y) ||
                    !Number.isFinite(b.x) ||
                    !Number.isFinite(b.y)
                  ) {
                    return null;
                  }
                  const attach = edgeAttach(a.x, a.y, b.x, b.y, nodeRadius(a), nodeRadius(b));
                  if (!attach) return null;
                  const hot = selectedId != null && (a.id === selectedId || b.id === selectedId);
                  const dim = selectedId != null && !hot;
                  return (
                    <line
                      key={`${a.id}->${b.id}-${i}`}
                      x1={attach.x1}
                      y1={attach.y1}
                      x2={attach.x2}
                      y2={attach.y2}
                      stroke={l.live ? "#9b6d4d" : hot ? "#3d4636" : "#7a7468"}
                      strokeWidth={hot ? 2.2 : l.live ? 1.7 : 1.25}
                      strokeOpacity={dim ? 0.12 : hot ? 0.92 : 0.55}
                      strokeLinecap="round"
                    />
                  );
                })}
                {simNodes.current.map((n) => {
                  if (
                    typeof n.x !== "number" ||
                    typeof n.y !== "number" ||
                    !Number.isFinite(n.x) ||
                    !Number.isFinite(n.y)
                  ) {
                    return null;
                  }
                  const r = nodeRadius(n);
                  const dim = selectedId != null && !connected.has(n.id);
                  const sel = n.id === selectedId;
                  const showLabel =
                    sel ||
                    (selectedId
                      ? connected.has(n.id)
                      : n.degree >= 3 ||
                        n.kind === "phenomenon" ||
                        n.kind === "epoche" ||
                        n.kind === "finding" ||
                        view.k > 1.15);
                  const raw = companion ? n.short || n.label : n.label;
                  const label = raw.length > (companion ? 16 : 20) ? `${raw.slice(0, companion ? 15 : 19)}…` : raw;
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
                      {sel && (
                        <circle r={r + 6} fill="none" stroke="#171717" strokeWidth={1.2} strokeOpacity={0.55} />
                      )}
                      <circle
                        r={r + 3}
                        fill={nodeFill(n)}
                        opacity={0.18}
                        style={{ pointerEvents: "none" }}
                      />
                      <circle
                        r={r}
                        fill={nodeFill(n)}
                        stroke={sel ? "#171717" : "rgba(255,255,255,0.85)"}
                        strokeWidth={sel ? 1.6 : 1.1}
                      />
                      {showLabel && (
                        <text
                          y={r + 13}
                          textAnchor="middle"
                          fill="#171717"
                          fontSize={9.5}
                          fontFamily="IBM Plex Mono, monospace"
                          opacity={sel ? 1 : 0.82}
                          style={{ pointerEvents: "none" }}
                        >
                          {label}
                        </text>
                      )}
                    </g>
                  );
                })}
              </g>
            </svg>

            <p
              style={{
                position: "absolute",
                left: 10,
                bottom: 10,
                margin: 0,
                fontSize: 10,
                fontFamily: "IBM Plex Mono, monospace",
                color: "#706f69",
              }}
            >
              Clic = detalle · rueda = zoom · arrastrá · Ver todo
            </p>
          </div>

          {selected && (
            <div
              style={{
                borderTop: "1px solid rgba(23,23,23,0.1)",
                background: "#fff",
                padding: companion ? "12px 14px" : "14px 16px",
                maxHeight: companion ? 160 : 200,
                overflow: "auto",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "baseline" }}>
                <p
                  style={{
                    margin: 0,
                    fontSize: 10,
                    fontFamily: "IBM Plex Mono, monospace",
                    color: "#56624b",
                    letterSpacing: "0.06em",
                  }}
                >
                  {selected.layerName} · {familyLabel(selected.kind)} · {statusLabelEs(selected.status)}
                </p>
                <button
                  type="button"
                  onClick={() => setSelectedId(null)}
                  style={{
                    border: "none",
                    background: "transparent",
                    color: "#706f69",
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
                  margin: "6px 0 0",
                  fontFamily: "Cormorant Garamond, Georgia, serif",
                  fontWeight: 500,
                  fontSize: companion ? 18 : 22,
                  lineHeight: 1.15,
                  color: "#171717",
                }}
              >
                {selected.label}
              </h3>
              <p style={{ margin: "8px 0 0", fontSize: 13, color: "#171717", lineHeight: 1.5 }}>{selected.detail}</p>
              <p style={{ margin: "8px 0 0", fontSize: 11, fontFamily: "IBM Plex Mono, monospace", color: "#706f69" }}>
                Origen · {humanSourceLabel(selected.source)}
              </p>
            </div>
          )}
        </div>
      </div>

      <style>{`
        @media (max-width: 820px) {
          .cw-map-grid { grid-template-columns: 1fr !important; }
        }
      `}</style>
    </section>
  );
}
