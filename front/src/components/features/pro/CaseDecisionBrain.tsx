"use client";

/**
 * Globo neural del caso: nodos en esfera, Φ al centro.
 * UX: girar el globo + tocar fase/nodo (sin orbitar como CAD).
 * variant companion = presente en todas las vistas; full = mapa dedicado.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Html, OrbitControls } from "@react-three/drei";
import type { Mesh } from "three";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";
import * as THREE from "three";
import {
  activationColor,
  buildNeuralCaseGraph,
  humanSourceLabel,
  statusLabelEs,
  type NeuralCaseGraph,
  type NetNode,
  type Synapse,
} from "@/lib/case-decision-graph";

export type BrainVariant = "full" | "companion";

/** Alineación vista workspace → capa del globo. */
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

const BG = "#e8e1d2";

const SECTION_LAYER: Record<BrainSectionHint, number | null> = {
  encargo: 0,
  metodo: 1,
  campo: 2,
  sintesis: 3,
  docs: 4,
  sello: 5,
  mapa: null,
};

function v3(n: NetNode) {
  return new THREE.Vector3(n.position[0], n.position[1], n.position[2]);
}

/** Cuerdas hacia el núcleo — lectura de red esférica. */
function makeCurve(a: THREE.Vector3, b: THREE.Vector3) {
  const mid = a.clone().add(b).multiplyScalar(0.5);
  mid.multiplyScalar(0.55);
  return new THREE.QuadraticBezierCurve3(a, mid, b);
}

function nodeRadius(kind: NetNode["kind"]) {
  switch (kind) {
    case "phenomenon":
      return 0.4;
    case "kill":
    case "motor":
    case "seal":
      return 0.22;
    case "epoche":
    case "finding":
      return 0.2;
    case "lens":
    case "stage":
      return 0.14;
    case "hypothesis":
    case "field":
    case "document":
      return 0.13;
    case "evidence":
    case "gate":
      return 0.11;
    default:
      return 0.12;
  }
}

function SynapseTubes({
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
    // Todas las conexiones visibles; la selección solo resalta.
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
        const radius = s.live ? 0.026 : selected ? 0.022 : 0.011;
        const color = s.live ? "#c47a28" : selected ? "#2f5d42" : "#9a9182";
        // Con selección: conexiones elegidas fuertes; el resto se atenúa pero sigue visible.
        const opacity = s.live
          ? 0.88
          : selected
            ? 0.9
            : hasSelection
              ? 0.22
              : Math.max(0.28, s.weight * 0.55);
        return (
          <mesh key={s.id}>
            <tubeGeometry args={[curve, 24, radius, 5, false]} />
            <meshStandardMaterial
              color={color}
              transparent
              opacity={opacity}
              roughness={0.7}
              depthWrite={false}
            />
          </mesh>
        );
      })}
    </>
  );
}

function FlowPackets({ graph }: { graph: NeuralCaseGraph }) {
  const byId = useMemo(() => {
    const m = new Map<string, NetNode>();
    graph.nodes.forEach((n) => m.set(n.id, n));
    return m;
  }, [graph.nodes]);

  const paths = useMemo(() => {
    return graph.synapses
      .filter((s) => s.visible && s.live && s.weight >= 0.55)
      .slice(0, 8)
      .map((s) => {
        const from = byId.get(s.from);
        const to = byId.get(s.to);
        if (!from || !to) return null;
        return { id: s.id, curve: makeCurve(v3(from), v3(to)) };
      })
      .filter(Boolean) as { id: string; curve: THREE.QuadraticBezierCurve3 }[];
  }, [graph.synapses, byId]);

  const refs = useRef<(Mesh | null)[]>([]);
  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    paths.forEach((p, i) => {
      const mesh = refs.current[i];
      if (!mesh) return;
      mesh.position.copy(p.curve.getPoint((t * 0.42 + i * 0.15) % 1));
    });
  });

  return (
    <>
      {paths.map((p, i) => (
        <mesh
          key={p.id}
          ref={(el) => {
            refs.current[i] = el;
          }}
        >
          <sphereGeometry args={[0.05, 10, 10]} />
          <meshStandardMaterial color="#c47a28" emissive="#c47a28" emissiveIntensity={0.4} />
        </mesh>
      ))}
    </>
  );
}

function Neuron({
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
  const group = useRef<THREE.Group>(null);
  const spawn = useRef(0);
  const [hovered, setHovered] = useState(false);
  const color = activationColor(node.activation);
  const r = nodeRadius(node.kind);
  const showLabel = selected || isCursor || hovered;

  useFrame((_, dt) => {
    if (!group.current) return;
    spawn.current = Math.min(1, spawn.current + dt * 2.4);
    let s = spawn.current;
    if (node.activation === "current") s *= 1 + Math.sin(performance.now() / 300) * 0.07;
    else if (selected || hovered) s *= 1.1;
    group.current.scale.setScalar(s);
  });

  if (!node.visible) return null;

  return (
    <group position={node.position} ref={group}>
      {isCursor && (
        <mesh>
          <sphereGeometry args={[r * 1.55, 24, 24]} />
          <meshBasicMaterial color="#c47a28" transparent opacity={0.12} depthWrite={false} />
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
        <sphereGeometry args={[r, 28, 28]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={
            node.activation === "current" ? 0.28 : selected || hovered ? 0.14 : 0.03
          }
          roughness={0.35}
          metalness={node.kind === "phenomenon" ? 0.22 : 0.08}
        />
      </mesh>
      {showLabel && (
        <Html distanceFactor={14} position={[0, r + 0.35, 0]} center style={{ pointerEvents: "none" }}>
          <div
            style={{
              padding: "3px 8px",
              background: "rgba(255,252,245,0.96)",
              color: "#2a2f28",
              fontSize: 10,
              fontFamily: "IBM Plex Mono, monospace",
              border: "1px solid rgba(42,47,40,0.1)",
              borderRadius: 999,
              whiteSpace: "nowrap",
              maxWidth: 150,
              overflow: "hidden",
              textOverflow: "ellipsis",
              boxShadow: "0 6px 16px rgba(42,47,40,0.1)",
            }}
          >
            {node.short}
            {node.kind === "lens" ? ` ${node.label.split("·")[0].trim()}` : ""}
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
  const polarDrift = useRef(0);

  useEffect(() => {
    camera.position.set(0, companion ? 2.1 : 2.4, companion ? 12.2 : 13.5);
    camera.lookAt(0, 0, 0);
  }, [camera, companion]);

  useFrame((_, dt) => {
    const c = controls.current;
    if (!c) return;
    if (azimuth != null) {
      const cur = c.getAzimuthalAngle();
      let diff = azimuth - cur;
      while (diff > Math.PI) diff -= Math.PI * 2;
      while (diff < -Math.PI) diff += Math.PI * 2;
      if (Math.abs(diff) > 0.008) {
        c.setAzimuthalAngle(cur + diff * 0.12);
        c.update();
      }
    } else if (autoSpin) {
      // Micro-oscilación polar: el globo “respira” además de girar.
      polarDrift.current += dt * 0.35;
      const base = Math.PI * 0.48;
      const wobble = Math.sin(polarDrift.current) * 0.04;
      c.setPolarAngle(base + wobble);
      c.update();
    }
  });

  return (
    <OrbitControls
      ref={controls}
      enablePan={false}
      enableZoom={!companion}
      minDistance={companion ? 10 : 9}
      maxDistance={companion ? 14 : 18}
      target={[0, 0, 0]}
      autoRotate={autoSpin && azimuth == null}
      autoRotateSpeed={companion ? 0.72 : 0.52}
      rotateSpeed={0.58}
      minPolarAngle={Math.PI * 0.28}
      maxPolarAngle={Math.PI * 0.72}
      enableDamping
      dampingFactor={0.065}
    />
  );
}

function CoreAura() {
  const mesh = useRef<Mesh>(null);
  useFrame(({ clock }) => {
    if (!mesh.current) return;
    const t = clock.getElapsedTime();
    const s = 1 + Math.sin(t * 1.1) * 0.06;
    mesh.current.scale.setScalar(s);
    const mat = mesh.current.material as THREE.MeshBasicMaterial;
    mat.opacity = 0.07 + Math.sin(t * 0.9) * 0.035;
  });
  return (
    <mesh ref={mesh}>
      <sphereGeometry args={[1.15, 32, 32]} />
      <meshBasicMaterial color="#c47a28" transparent opacity={0.08} depthWrite={false} />
    </mesh>
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
      <color attach="background" args={[BG]} />
      <fog attach="fog" args={[BG, companion ? 16 : 18, companion ? 28 : 32]} />
      <hemisphereLight args={["#fff8ec", "#9aa88e", 0.95]} />
      <directionalLight position={[6, 10, 4]} intensity={1.1} color="#fff4e0" />
      <directionalLight position={[-5, 2, -6]} intensity={0.32} color="#8fa88f" />
      <pointLight position={[0, 0, 0]} intensity={0.55} color="#f0d9a8" distance={12} />
      <CoreAura />

      <SynapseTubes graph={graph} selectedId={selectedId} />
      <FlowPackets graph={graph} />
      {graph.nodes.map((n) => (
        <Neuron
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
        top: 10,
        right: 10,
        width: compact ? "min(260px, calc(100% - 16px))" : "min(320px, calc(100% - 20px))",
        maxHeight: compact ? "min(340px, calc(100% - 16px))" : "min(460px, calc(100% - 20px))",
        overflow: "auto",
        background: "rgba(255,252,245,0.97)",
        border: "1px solid rgba(42,47,40,0.1)",
        borderRadius: 12,
        zIndex: 3,
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          padding: "10px 12px",
          borderBottom: "1px solid rgba(42,47,40,0.06)",
        }}
      >
        <span
          style={{
            fontSize: 10,
            fontFamily: "IBM Plex Mono, monospace",
            color: "#3f6b4e",
            letterSpacing: "0.06em",
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
            color: "#6b7280",
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
            fontSize: compact ? 17 : 20,
            color: "#1f2933",
            lineHeight: 1.15,
          }}
        >
          {node.label}
        </h3>
        <p
          style={{
            margin: "8px 0 0",
            fontSize: 10,
            fontFamily: "IBM Plex Mono, monospace",
            color: activationColor(node.activation),
          }}
        >
          {statusLabelEs(node.status)}
        </p>
        <p style={{ margin: "12px 0 0", fontSize: 12, color: "#3f6b4e", lineHeight: 1.5 }}>
          {node.signal}
        </p>
        <p style={{ margin: "8px 0 0", fontSize: 13, color: "#374151", lineHeight: 1.5 }}>
          {node.detail}
        </p>
        <div
          style={{
            marginTop: 14,
            paddingTop: 12,
            borderTop: "1px solid rgba(42,47,40,0.08)",
          }}
        >
          <p style={{ margin: 0, fontSize: 9, fontFamily: "IBM Plex Mono, monospace", color: "#9b6d4d", letterSpacing: "0.08em" }}>
            ORIGEN
          </p>
          <p style={{ margin: "6px 0 0", fontSize: 12, color: "#706f69", lineHeight: 1.4 }}>
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
  const [autoSpin, setAutoSpin] = useState(true);
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

  // Alinear el globo a la vista del workspace (sin desmontar el Canvas).
  useEffect(() => {
    if (!section) return;
    userLocked.current = false;
    const layer = SECTION_LAYER[section];
    if (layer == null) {
      setAzimuth(null);
      setAutoSpin(true);
      return;
    }
    setFocusLayer(layer);
    setAzimuth(graph.layerLabels[layer]?.azimuth ?? null);
    setAutoSpin(false);
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

  function resumeSpin() {
    userLocked.current = false;
    setAutoSpin(true);
    setAzimuth(null);
  }

  const layerNodes = focusLayer == null
    ? []
    : graph.nodes.filter((n) => n.visible && n.layerIndex === focusLayer);

  return (
    <section
      style={{
        marginTop: companion ? 0 : 0,
        border: "1px solid rgba(42,47,40,0.1)",
        borderRadius: 12,
        background: "#f4efe6",
        overflow: "hidden",
        height: companion ? "100%" : undefined,
        display: "flex",
        flexDirection: "column",
      }}
    >
      <style>{`
        .dx-nn-stage-full { height: min(72vh, 680px); min-height: 380px; }
        .dx-nn-stage-companion { height: min(58vh, 520px); min-height: 300px; flex: 1; }
        .dx-nn-layers {
          display: flex;
          gap: 6px;
          padding: 10px 12px;
          border-bottom: 1px solid rgba(42,47,40,0.06);
          overflow-x: auto;
          scrollbar-width: none;
        }
        .dx-nn-layers::-webkit-scrollbar { display: none; }
        .dx-nn-nodelist {
          display: flex;
          gap: 6px;
          padding: 8px 12px 10px;
          border-bottom: 1px solid rgba(42,47,40,0.05);
          overflow-x: auto;
          scrollbar-width: none;
        }
        .dx-nn-nodelist::-webkit-scrollbar { display: none; }
        @media (max-width: 900px) {
          .dx-nn-stage-full { height: min(56vh, 500px); min-height: 300px; }
          .dx-nn-stage-companion { height: min(42vh, 360px); min-height: 260px; }
        }
      `}</style>

      <header
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 12,
          padding: companion ? "10px 12px" : "12px 16px",
          borderBottom: "1px solid rgba(42,47,40,0.08)",
          background: "linear-gradient(180deg, #fffdf8, #ebe4d6)",
          flexWrap: "wrap",
        }}
      >
        <div style={{ minWidth: 0, flex: "1 1 160px" }}>
          <p
            style={{
              margin: 0,
              fontSize: 10,
              fontFamily: "IBM Plex Mono, monospace",
              color: "#3f6b4e",
              letterSpacing: "0.1em",
            }}
          >
            MAPA 3D · {graph.stats.clientName.toUpperCase()}
          </p>
          <p style={{ margin: "4px 0 0", fontSize: companion ? 12 : 13, color: "#4b5563" }}>
            {graph.phaseLabel}
            {!companion && (
              <>
                {" "}
                · {Math.round(graph.methodCoverage * 100)}% método · {graph.stats.visible} nodos
              </>
            )}
          </p>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <button
            type="button"
            onClick={() => {
              if (autoSpin) {
                setAutoSpin(false);
              } else {
                resumeSpin();
              }
            }}
            style={{
              fontSize: 10,
              fontFamily: "IBM Plex Mono, monospace",
              padding: "6px 10px",
              borderRadius: 8,
              border: "1px solid rgba(42,47,40,0.12)",
              background: autoSpin ? "#3f6b4e" : "#fffdf8",
              color: autoSpin ? "#fffdf8" : "#374151",
              cursor: "pointer",
            }}
          >
            {autoSpin ? "girando" : "girar"}
          </button>
          <div style={{ width: companion ? 72 : 100 }}>
            <div
              style={{
                height: 4,
                background: "rgba(42,47,40,0.08)",
                borderRadius: 99,
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  width: `${pct}%`,
                  height: "100%",
                  background: "linear-gradient(90deg, #3f6b4e, #c47a28)",
                  transition: "width 0.6s ease",
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
                padding: companion ? "6px 10px" : "8px 12px",
                background: active ? "#3f6b4e" : "#fffdf8",
                color: active ? "#fffdf8" : "#374151",
                border: "1px solid rgba(42,47,40,0.08)",
                borderRadius: 999,
                cursor: "pointer",
                textAlign: "left",
              }}
            >
              {!companion && (
                <span
                  style={{
                    display: "block",
                    fontSize: 9,
                    fontFamily: "IBM Plex Mono, monospace",
                    opacity: 0.7,
                  }}
                >
                  L{L.index}
                </span>
              )}
              <span style={{ fontSize: companion ? 11 : 12, fontFamily: "IBM Plex Mono, monospace" }}>{L.name}</span>
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
                padding: "6px 10px",
                borderRadius: 8,
                border: selectedId === n.id ? "1px solid #3f6b4e" : "1px solid rgba(42,47,40,0.08)",
                background: selectedId === n.id ? "rgba(63,107,78,0.1)" : "#fff",
                cursor: "pointer",
                fontSize: 11,
                fontFamily: "IBM Plex Mono, monospace",
                color: "#374151",
                maxWidth: 160,
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
        style={{ position: "relative", background: BG, width: "100%" }}
      >
        <Canvas
          dpr={[1, 1.75]}
          camera={{ position: [0, companion ? 2.1 : 2.4, companion ? 12.2 : 13.5], fov: companion ? 40 : 38 }}
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

        <div
          style={{
            position: "absolute",
            left: 10,
            bottom: 10,
            padding: "6px 10px",
            background: "rgba(255,252,245,0.92)",
            border: "1px solid rgba(42,47,40,0.08)",
            borderRadius: 8,
            fontSize: 9,
            fontFamily: "IBM Plex Mono, monospace",
            color: "#6b7280",
            maxWidth: "72%",
          }}
        >
          {companion
            ? "Gira con el caso · tocá una fase o un nodo"
            : "Fase → el globo gira · arrastrá para rotar · clic = detalle"}
        </div>
      </div>
    </section>
  );
}
