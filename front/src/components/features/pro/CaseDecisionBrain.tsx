"use client";

/**
 * Traza espacial del caso — instrumento de lectura, no demo de partículas.
 * Motion: quieto por defecto; giro solo a pedido o al cambiar de fase.
 * variant companion = al lado del workspace; full = vista Mapa.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Html, OrbitControls } from "@react-three/drei";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";
import * as THREE from "three";
import {
  buildNeuralCaseGraph,
  humanSourceLabel,
  statusLabelEs,
  type NeuralCaseGraph,
  type NetNode,
  type Synapse,
} from "@/lib/case-decision-graph";

export type BrainVariant = "full" | "companion";

export type BrainSectionHint =
  | "encargo"
  | "metodo"
  | "campo"
  | "sintesis"
  | "sello"
  | "docs"
  | "mapa";

type Props = {
  caseData: any;
  variant?: BrainVariant;
  section?: BrainSectionHint;
};

/** Paleta Dx Pro — tinta, oliva, piedra, terracota puntual. */
const C = {
  bg: "#1a1b19",
  stage: "#141513",
  ink: "#e8e4dc",
  mute: "#8a8680",
  line: "#3a3b38",
  lineDim: "#2a2b28",
  done: "#6e7a68",
  current: "#c4a574",
  blocked: "#a67c72",
  idle: "#4a4b47",
  wire: "#4f514c",
  wireLive: "#8b7355",
  wireSel: "#c4a574",
  panel: "#f4f1ea",
  panelInk: "#171717",
  panelMute: "#706f69",
  panelLine: "rgba(23,23,23,0.12)",
  olive: "#56624b",
};

const SECTION_LAYER: Record<BrainSectionHint, number | null> = {
  encargo: 0,
  metodo: 1,
  campo: 2,
  sintesis: 3,
  docs: 4,
  sello: 5,
  mapa: null,
};

function nodeTone(n: NetNode, selected: boolean): string {
  if (n.status === "failed" || n.activation === "blocked") return C.blocked;
  if (selected || n.activation === "current" || n.status === "running") return C.current;
  if (n.status === "done" || n.activation === "past") return C.done;
  return C.idle;
}

function v3(n: NetNode) {
  return new THREE.Vector3(n.position[0], n.position[1], n.position[2]);
}

function makeCurve(a: THREE.Vector3, b: THREE.Vector3) {
  const mid = a.clone().add(b).multiplyScalar(0.5);
  mid.multiplyScalar(0.62);
  return new THREE.QuadraticBezierCurve3(a, mid, b);
}

function nodeRadius(kind: NetNode["kind"]) {
  switch (kind) {
    case "phenomenon":
      return 0.32;
    case "kill":
    case "motor":
    case "seal":
    case "finding":
      return 0.16;
    case "epoche":
      return 0.15;
    case "lens":
    case "stage":
      return 0.11;
    case "document":
    case "field":
      return 0.1;
    case "evidence":
    case "gate":
      return 0.08;
    default:
      return 0.1;
  }
}

function SynapseLines({
  graph,
  selectedId,
}: {
  graph: NeuralCaseGraph;
  selectedId: string | null;
}) {
  const byId = useMemo(() => {
    const m = new Map<string, NetNode>();
    graph.nodes.forEach((n) => m.set(n.id, n));
    return m;
  }, [graph.nodes]);

  const items = useMemo(() => {
    return graph.synapses
      .filter((s) => s.visible)
      .map((s) => {
        const from = byId.get(s.from);
        const to = byId.get(s.to);
        if (!from?.visible || !to?.visible) return null;
        const selected = Boolean(selectedId && (selectedId === s.from || selectedId === s.to));
        return { s, from, to, selected };
      })
      .filter(Boolean) as { s: Synapse; from: NetNode; to: NetNode; selected: boolean }[];
  }, [graph.synapses, byId, selectedId]);

  const hasSelection = Boolean(selectedId);

  return (
    <>
      {items.map(({ s, from, to, selected }) => {
        const curve = makeCurve(v3(from), v3(to));
        const radius = selected ? 0.012 : s.live ? 0.009 : 0.005;
        const color = selected ? C.wireSel : s.live ? C.wireLive : C.wire;
        const opacity = selected ? 0.75 : hasSelection ? 0.12 : s.live ? 0.45 : 0.22;
        return (
          <mesh key={s.id}>
            <tubeGeometry args={[curve, 20, radius, 4, false]} />
            <meshBasicMaterial color={color} transparent opacity={opacity} depthWrite={false} />
          </mesh>
        );
      })}
    </>
  );
}

function NodeMarker({
  node,
  selected,
  isCursor,
  onSelect,
}: {
  node: NetNode;
  selected: boolean;
  isCursor: boolean;
  onSelect: (id: string) => void;
}) {
  const [hovered, setHovered] = useState(false);
  const color = nodeTone(node, selected || hovered);
  const r = nodeRadius(node.kind);
  const showLabel = selected || isCursor || hovered;

  if (!node.visible) return null;

  return (
    <group position={node.position}>
      {selected && (
        <mesh>
          <ringGeometry args={[r * 1.35, r * 1.55, 32]} />
          <meshBasicMaterial color={C.current} transparent opacity={0.35} side={THREE.DoubleSide} />
        </mesh>
      )}
      <mesh
        onClick={(e) => {
          e.stopPropagation();
          onSelect(node.id);
        }}
        onPointerOver={(e) => {
          e.stopPropagation();
          setHovered(true);
          document.body.style.cursor = "pointer";
        }}
        onPointerOut={() => {
          setHovered(false);
          document.body.style.cursor = "default";
        }}
      >
        <sphereGeometry args={[r, 24, 24]} />
        <meshStandardMaterial
          color={color}
          roughness={0.82}
          metalness={0.04}
          emissive={selected || isCursor ? C.current : "#000000"}
          emissiveIntensity={selected || isCursor ? 0.06 : 0}
        />
      </mesh>
      {showLabel && (
        <Html distanceFactor={16} position={[0, r + 0.28, 0]} center style={{ pointerEvents: "none" }}>
          <div
            style={{
              padding: "4px 8px",
              background: "rgba(20,21,19,0.92)",
              color: C.ink,
              fontSize: 10,
              fontFamily: "IBM Plex Mono, monospace",
              border: `1px solid ${C.line}`,
              whiteSpace: "nowrap",
              maxWidth: 160,
              overflow: "hidden",
              textOverflow: "ellipsis",
              letterSpacing: "0.02em",
            }}
          >
            {node.label}
          </div>
        </Html>
      )}
    </group>
  );
}

function GlobeControls({
  azimuth,
  autoSpin,
  companion,
}: {
  azimuth: number | null;
  autoSpin: boolean;
  companion?: boolean;
}) {
  const controls = useRef<OrbitControlsImpl>(null);
  const { camera } = useThree();

  useEffect(() => {
    camera.position.set(0, companion ? 1.8 : 2.1, companion ? 11.5 : 12.8);
    camera.lookAt(0, 0, 0);
  }, [camera, companion]);

  useFrame(() => {
    const c = controls.current;
    if (!c || azimuth == null) return;
    const cur = c.getAzimuthalAngle();
    let diff = azimuth - cur;
    while (diff > Math.PI) diff -= Math.PI * 2;
    while (diff < -Math.PI) diff += Math.PI * 2;
    if (Math.abs(diff) > 0.006) {
      c.setAzimuthalAngle(cur + diff * 0.08);
      c.update();
    }
  });

  return (
    <OrbitControls
      ref={controls}
      enablePan={false}
      enableZoom={!companion}
      minDistance={companion ? 10 : 9}
      maxDistance={companion ? 14 : 16}
      target={[0, 0, 0]}
      autoRotate={autoSpin && azimuth == null}
      autoRotateSpeed={0.18}
      rotateSpeed={0.42}
      minPolarAngle={Math.PI * 0.32}
      maxPolarAngle={Math.PI * 0.68}
      enableDamping
      dampingFactor={0.08}
    />
  );
}

function Scene({
  graph,
  selectedId,
  azimuth,
  autoSpin,
  companion,
  onSelect,
}: {
  graph: NeuralCaseGraph;
  selectedId: string | null;
  azimuth: number | null;
  autoSpin: boolean;
  companion?: boolean;
  onSelect: (id: string) => void;
}) {
  return (
    <>
      <color attach="background" args={[C.stage]} />
      <fog attach="fog" args={[C.stage, companion ? 14 : 16, companion ? 26 : 30]} />
      <ambientLight intensity={0.55} color="#c8c4bc" />
      <directionalLight position={[5, 8, 3]} intensity={0.65} color="#f0ebe3" />
      <directionalLight position={[-4, 1, -5]} intensity={0.2} color="#6e7a68" />

      {/* Núcleo quieto — sin pulso */}
      <mesh>
        <sphereGeometry args={[0.55, 32, 32]} />
        <meshStandardMaterial color="#222321" roughness={0.9} metalness={0.05} />
      </mesh>
      <mesh>
        <ringGeometry args={[0.7, 0.72, 64]} />
        <meshBasicMaterial color={C.line} transparent opacity={0.5} side={THREE.DoubleSide} />
      </mesh>

      <SynapseLines graph={graph} selectedId={selectedId} />
      {graph.nodes.map((n) => (
        <NodeMarker
          key={n.id}
          node={n}
          selected={selectedId === n.id}
          isCursor={graph.cursorId === n.id}
          onSelect={onSelect}
        />
      ))}

      <GlobeControls azimuth={azimuth} autoSpin={autoSpin} companion={companion} />
    </>
  );
}

function Inspector({ node, onClose, compact }: { node: NetNode; onClose: () => void; compact?: boolean }) {
  return (
    <aside
      style={{
        position: "absolute",
        top: 12,
        right: 12,
        width: compact ? "min(250px, calc(100% - 24px))" : "min(300px, calc(100% - 24px))",
        maxHeight: compact ? "min(320px, calc(100% - 24px))" : "min(420px, calc(100% - 24px))",
        overflow: "auto",
        background: C.panel,
        border: `1px solid ${C.panelLine}`,
        zIndex: 3,
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "10px 12px",
          borderBottom: `1px solid ${C.panelLine}`,
        }}
      >
        <span
          style={{
            fontSize: 10,
            fontFamily: "IBM Plex Mono, monospace",
            color: C.olive,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
          }}
        >
          {node.layerName}
        </span>
        <button
          type="button"
          onClick={onClose}
          style={{
            border: "none",
            background: "transparent",
            cursor: "pointer",
            color: C.panelMute,
            fontFamily: "IBM Plex Mono, monospace",
            fontSize: 11,
          }}
        >
          cerrar
        </button>
      </div>
      <div style={{ padding: 14 }}>
        <h3
          style={{
            margin: 0,
            fontFamily: "Cormorant Garamond, Georgia, serif",
            fontWeight: 500,
            fontSize: compact ? 18 : 22,
            color: C.panelInk,
            lineHeight: 1.15,
          }}
        >
          {node.label}
        </h3>
        <p
          style={{
            margin: "8px 0 0",
            fontSize: 11,
            fontFamily: "IBM Plex Mono, monospace",
            color: C.panelMute,
          }}
        >
          {statusLabelEs(node.status)}
        </p>
        <p style={{ margin: "12px 0 0", fontSize: 13, color: C.panelInk, lineHeight: 1.5, opacity: 0.9 }}>
          {node.detail}
        </p>
        {node.signal ? (
          <p style={{ margin: "10px 0 0", fontSize: 12, color: C.olive, lineHeight: 1.45 }}>{node.signal}</p>
        ) : null}
        <div style={{ marginTop: 14, paddingTop: 12, borderTop: `1px solid ${C.panelLine}` }}>
          <p
            style={{
              margin: 0,
              fontSize: 9,
              fontFamily: "IBM Plex Mono, monospace",
              color: C.panelMute,
              letterSpacing: "0.08em",
            }}
          >
            ORIGEN
          </p>
          <p style={{ margin: "6px 0 0", fontSize: 12, color: C.panelMute, lineHeight: 1.4 }}>
            {humanSourceLabel(node.source)}
          </p>
        </div>
      </div>
    </aside>
  );
}

export function CaseDecisionBrain({ caseData, variant = "full", section }: Props) {
  const companion = variant === "companion";
  const graph = useMemo(() => buildNeuralCaseGraph(caseData), [caseData]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [focusLayer, setFocusLayer] = useState<number | null>(null);
  const [azimuth, setAzimuth] = useState<number | null>(null);
  const [autoSpin, setAutoSpin] = useState(false);
  const selected = graph.nodes.find((n) => n.id === selectedId && n.visible) ?? null;
  const userLocked = useRef(false);

  useEffect(() => {
    if (graph.cursorId && !userLocked.current) {
      const n = graph.nodes.find((x) => x.id === graph.cursorId);
      setSelectedId(graph.cursorId);
      if (n) {
        setFocusLayer(n.layerIndex);
        setAzimuth(graph.layerLabels[n.layerIndex]?.azimuth ?? null);
      }
    }
  }, [graph.cursorId, graph.nodes, graph.layerLabels]);

  useEffect(() => {
    if (!section) return;
    userLocked.current = false;
    const layer = SECTION_LAYER[section];
    setAutoSpin(false);
    if (layer == null) {
      setAzimuth(null);
      return;
    }
    setFocusLayer(layer);
    setAzimuth(graph.layerLabels[layer]?.azimuth ?? null);
    const first = graph.nodes.find((n) => n.layerIndex === layer && n.visible);
    if (first) setSelectedId(first.id);
  }, [section, graph.layerLabels, graph.nodes]);

  const pct = Math.round(graph.progress * 100);

  function goLayer(index: number) {
    userLocked.current = true;
    setFocusLayer(index);
    setAzimuth(graph.layerLabels[index].azimuth);
    setAutoSpin(false);
    const first = graph.nodes.find((n) => n.layerIndex === index && n.visible);
    if (first) setSelectedId(first.id);
  }

  function onSelectNode(id: string) {
    userLocked.current = true;
    setSelectedId(id);
    setAutoSpin(false);
    const n = graph.nodes.find((x) => x.id === id);
    if (n) {
      setFocusLayer(n.layerIndex);
      setAzimuth(graph.layerLabels[n.layerIndex].azimuth);
    }
  }

  const layerNodes =
    focusLayer == null ? [] : graph.nodes.filter((n) => n.visible && n.layerIndex === focusLayer);

  return (
    <section
      style={{
        border: `1px solid ${C.panelLine}`,
        background: C.panel,
        overflow: "hidden",
        height: companion ? "100%" : undefined,
        display: "flex",
        flexDirection: "column",
      }}
    >
      <style>{`
        .dx-nn-stage-full { height: min(70vh, 640px); min-height: 360px; }
        .dx-nn-stage-companion { height: min(54vh, 480px); min-height: 280px; flex: 1; }
        .dx-nn-layers {
          display: flex;
          gap: 0;
          padding: 0;
          border-bottom: 1px solid ${C.panelLine};
          overflow-x: auto;
          scrollbar-width: none;
        }
        .dx-nn-layers::-webkit-scrollbar { display: none; }
        .dx-nn-nodelist {
          display: flex;
          gap: 0;
          padding: 0;
          border-bottom: 1px solid ${C.panelLine};
          overflow-x: auto;
          scrollbar-width: none;
        }
        .dx-nn-nodelist::-webkit-scrollbar { display: none; }
        @media (max-width: 900px) {
          .dx-nn-stage-full { height: min(52vh, 460px); min-height: 280px; }
          .dx-nn-stage-companion { height: min(38vh, 320px); min-height: 240px; }
        }
      `}</style>

      <header
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 12,
          padding: companion ? "12px 14px" : "14px 16px",
          borderBottom: `1px solid ${C.panelLine}`,
          background: C.panel,
        }}
      >
        <div style={{ minWidth: 0, flex: "1 1 160px" }}>
          <p
            style={{
              margin: 0,
              fontSize: 10,
              fontFamily: "IBM Plex Mono, monospace",
              color: C.olive,
              letterSpacing: "0.1em",
            }}
          >
            TRAZA DEL CASO
          </p>
          <p
            style={{
              margin: "4px 0 0",
              fontFamily: "Cormorant Garamond, Georgia, serif",
              fontSize: companion ? 18 : 22,
              fontWeight: 500,
              color: C.panelInk,
              lineHeight: 1.1,
            }}
          >
            {graph.stats.clientName}
          </p>
          <p style={{ margin: "4px 0 0", fontSize: 12, color: C.panelMute }}>
            {graph.phaseLabel}
            {!companion ? ` · ${pct}%` : ""}
          </p>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <button
            type="button"
            onClick={() => {
              setAutoSpin((v) => !v);
              if (!autoSpin) setAzimuth(null);
            }}
            style={{
              fontSize: 10,
              fontFamily: "IBM Plex Mono, monospace",
              padding: "7px 11px",
              border: `1px solid ${C.panelLine}`,
              background: autoSpin ? C.panelInk : "transparent",
              color: autoSpin ? C.panel : C.panelMute,
              cursor: "pointer",
            }}
          >
            {autoSpin ? "Rotación on" : "Rotar"}
          </button>
          <div style={{ width: companion ? 64 : 88 }}>
            <div style={{ height: 2, background: C.panelLine, overflow: "hidden" }}>
              <div
                style={{
                  width: `${pct}%`,
                  height: "100%",
                  background: C.olive,
                  transition: "width 0.5s ease",
                }}
              />
            </div>
          </div>
        </div>
      </header>

      <div className="dx-nn-layers">
        {graph.layerLabels.map((L) => {
          const active = focusLayer === L.index;
          return (
            <button
              key={L.index}
              type="button"
              onClick={() => goLayer(L.index)}
              style={{
                flex: "0 0 auto",
                padding: companion ? "10px 12px" : "11px 14px",
                background: active ? C.panelInk : "transparent",
                color: active ? C.panel : C.panelMute,
                border: "none",
                borderRight: `1px solid ${C.panelLine}`,
                cursor: "pointer",
                fontSize: 11,
                fontFamily: "IBM Plex Mono, monospace",
                letterSpacing: "0.04em",
              }}
            >
              {L.name}
            </button>
          );
        })}
      </div>

      {!companion && layerNodes.length > 0 && (
        <div className="dx-nn-nodelist">
          {layerNodes.map((n) => (
            <button
              key={n.id}
              type="button"
              onClick={() => onSelectNode(n.id)}
              style={{
                flex: "0 0 auto",
                padding: "8px 12px",
                border: "none",
                borderRight: `1px solid ${C.panelLine}`,
                background: selectedId === n.id ? "rgba(86,98,75,0.1)" : "transparent",
                cursor: "pointer",
                fontSize: 11,
                fontFamily: "IBM Plex Mono, monospace",
                color: selectedId === n.id ? C.panelInk : C.panelMute,
                maxWidth: 180,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {n.label}
            </button>
          ))}
        </div>
      )}

      <div
        className={companion ? "dx-nn-stage-companion" : "dx-nn-stage-full"}
        style={{ position: "relative", background: C.stage, width: "100%" }}
      >
        <Canvas
          dpr={[1, 1.5]}
          camera={{ position: [0, companion ? 1.8 : 2.1, companion ? 11.5 : 12.8], fov: 36 }}
          gl={{ antialias: true, toneMapping: THREE.ACESFilmicToneMapping, powerPreference: "high-performance" }}
          style={{ width: "100%", height: "100%", touchAction: "none" }}
        >
          <Scene
            graph={graph}
            selectedId={selectedId}
            azimuth={azimuth}
            autoSpin={autoSpin}
            companion={companion}
            onSelect={onSelectNode}
          />
        </Canvas>

        {selected && <Inspector node={selected} compact={companion} onClose={() => setSelectedId(null)} />}

        <p
          style={{
            position: "absolute",
            left: 12,
            bottom: 12,
            margin: 0,
            fontSize: 10,
            fontFamily: "IBM Plex Mono, monospace",
            color: C.mute,
            maxWidth: "70%",
          }}
        >
          Arrastrá para orientar · tocá un nodo · fases arriba
        </p>
      </div>
    </section>
  );
}
