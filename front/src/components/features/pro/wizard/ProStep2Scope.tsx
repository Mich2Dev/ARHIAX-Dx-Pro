"use client";

import { CheckCircle, Circle } from "lucide-react";

// ── tipos ─────────────────────────────────────────────────────────────────────
export interface ProScopeData {
  roles: string[];
  dimensions: string[];
  hypotheses: string[];
  grey_sources: string[];
}

export const defaultScope: ProScopeData = {
  roles: ["executive", "operations", "technology"],
  dimensions: ["strategy", "process", "technology"],
  hypotheses: [""],
  grey_sources: [""],
};

// ── opciones ──────────────────────────────────────────────────────────────────
const ROLES = [
  { value: "executive",  label: "Ejecutivo",    desc: "Alta dirección y C-suite" },
  { value: "operations", label: "Operaciones",  desc: "Nivel táctico y operativo" },
  { value: "technology", label: "Tecnología",   desc: "Área de TI y sistemas" },
  { value: "strategy",   label: "Estrategia",   desc: "Planeación y estrategia" },
  { value: "finance",    label: "Finanzas",      desc: "Área financiera y contable" },
  { value: "hr",         label: "RRHH",          desc: "Recursos humanos" },
];

const DIMENSIONS = [
  { value: "strategy",   label: "Estrategia",   desc: "Alineación y dirección estratégica" },
  { value: "process",    label: "Procesos",      desc: "Eficiencia y madurez de procesos" },
  { value: "technology", label: "Tecnología",    desc: "Adopción y capacidad tecnológica" },
  { value: "people",     label: "Personas",      desc: "Cultura, talento y liderazgo" },
  { value: "finance",    label: "Finanzas",      desc: "Desempeño financiero y costos" },
  { value: "governance", label: "Gobernanza",    desc: "Cumplimiento y control interno" },
];

// ── estilos ───────────────────────────────────────────────────────────────────
const inp: React.CSSProperties = {
  flex: 1, minHeight: "38px", padding: "8px 12px",
  border: "1px solid rgba(23,23,23,0.18)",
  background: "rgba(255,255,255,0.6)",
  backdropFilter: "blur(4px)",
  color: "#171717", fontFamily: "Manrope, sans-serif", fontSize: "13px",
  outline: "none", boxSizing: "border-box" as const,
};

// ── componente ────────────────────────────────────────────────────────────────
export function ProStep2Scope({
  data, onChange, onNext, onBack,
}: {
  data: ProScopeData;
  onChange: (d: ProScopeData) => void;
  onNext: () => void;
  onBack: () => void;
}) {
  function toggleRole(v: string) {
    const roles = data.roles.includes(v) ? data.roles.filter(r => r !== v) : [...data.roles, v];
    onChange({ ...data, roles });
  }

  function toggleDim(v: string) {
    const dimensions = data.dimensions.includes(v) ? data.dimensions.filter(d => d !== v) : [...data.dimensions, v];
    onChange({ ...data, dimensions });
  }

  function setHyp(i: number, val: string) {
    const h = [...data.hypotheses]; h[i] = val;
    onChange({ ...data, hypotheses: h });
  }

  function setGrey(i: number, val: string) {
    const g = [...data.grey_sources]; g[i] = val;
    onChange({ ...data, grey_sources: g });
  }

  return (
    <div>
      <div style={{ marginBottom: "24px" }}>
        <h2 style={{ margin: 0, fontSize: "20px", fontWeight: 500, color: "#171717", fontFamily: "Cormorant Garamond, serif" }}>
          Alcance del diagnóstico
        </h2>
        <p style={{ margin: "6px 0 0", fontSize: "13px", color: "#706f69" }}>
          Define los roles, dimensiones e hipótesis que guiarán el ciclo de fusión.
        </p>
      </div>

      {/* Roles */}
      <div style={{ marginBottom: "28px" }}>
        <p style={{ margin: "0 0 12px", fontSize: "12px", fontWeight: 500, color: "#171717", fontFamily: "IBM Plex Mono, monospace", paddingBottom: "8px", borderBottom: "1px solid rgba(23,23,23,0.1)" }}>
          👥 Roles participantes *
        </p>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
          {ROLES.map(r => {
            const active = data.roles.includes(r.value);
            return (
              <button key={r.value} type="button" onClick={() => toggleRole(r.value)} style={{
                display: "flex", alignItems: "flex-start", gap: "10px",
                padding: "12px 14px", textAlign: "left",
                border: active ? "1px solid #222522" : "1px solid rgba(23,23,23,0.12)",
                background: active ? "rgba(23,23,23,0.04)" : "#fff",
                cursor: "pointer",
              }}>
                {active
                  ? <CheckCircle size={16} style={{ color: "#222522", flexShrink: 0, marginTop: "1px" }} />
                  : <Circle size={16} style={{ color: "rgba(23,23,23,0.2)", flexShrink: 0, marginTop: "1px" }} />
                }
                <div>
                  <p style={{ margin: 0, fontSize: "13px", fontWeight: 500, color: "#171717" }}>{r.label}</p>
                  <p style={{ margin: "2px 0 0", fontSize: "11px", color: "#706f69" }}>{r.desc}</p>
                </div>
              </button>
            );
          })}
        </div>
        {data.roles.length === 0 && (
          <p style={{ margin: "8px 0 0", fontSize: "11px", color: "#8b3a3a", fontFamily: "IBM Plex Mono, monospace" }}>
            Selecciona al menos un rol
          </p>
        )}
      </div>

      {/* Dimensiones */}
      <div style={{ marginBottom: "28px" }}>
        <p style={{ margin: "0 0 12px", fontSize: "12px", fontWeight: 500, color: "#171717", fontFamily: "IBM Plex Mono, monospace", paddingBottom: "8px", borderBottom: "1px solid rgba(23,23,23,0.1)" }}>
          📐 Dimensiones a evaluar *
        </p>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
          {DIMENSIONS.map(d => {
            const active = data.dimensions.includes(d.value);
            return (
              <button key={d.value} type="button" onClick={() => toggleDim(d.value)} style={{
                display: "flex", alignItems: "flex-start", gap: "10px",
                padding: "12px 14px", textAlign: "left",
                border: active ? "1px solid #56624b" : "1px solid rgba(23,23,23,0.12)",
                background: active ? "rgba(86,98,75,0.05)" : "#fff",
                cursor: "pointer",
              }}>
                {active
                  ? <CheckCircle size={16} style={{ color: "#56624b", flexShrink: 0, marginTop: "1px" }} />
                  : <Circle size={16} style={{ color: "rgba(23,23,23,0.2)", flexShrink: 0, marginTop: "1px" }} />
                }
                <div>
                  <p style={{ margin: 0, fontSize: "13px", fontWeight: 500, color: "#171717" }}>{d.label}</p>
                  <p style={{ margin: "2px 0 0", fontSize: "11px", color: "#706f69" }}>{d.desc}</p>
                </div>
              </button>
            );
          })}
        </div>
        {data.dimensions.length === 0 && (
          <p style={{ margin: "8px 0 0", fontSize: "11px", color: "#8b3a3a", fontFamily: "IBM Plex Mono, monospace" }}>
            Selecciona al menos una dimensión
          </p>
        )}
      </div>

      {/* Hipótesis */}
      <div style={{ marginBottom: "28px" }}>
        <p style={{ margin: "0 0 6px", fontSize: "12px", fontWeight: 500, color: "#171717", fontFamily: "IBM Plex Mono, monospace", paddingBottom: "8px", borderBottom: "1px solid rgba(23,23,23,0.1)" }}>
          🧪 Hipótesis diagnósticas (opcional)
        </p>
        <p style={{ margin: "0 0 12px", fontSize: "12px", color: "#706f69" }}>
          Enunciados que el sistema evaluará con síntesis bayesiana.
        </p>
        {data.hypotheses.map((h, i) => (
          <div key={i} style={{ display: "flex", gap: "8px", marginBottom: "8px" }}>
            <input style={inp} value={h} onChange={e => setHyp(i, e.target.value)}
              placeholder={`Hipótesis ${i + 1}: Ej: La trazabilidad tecnológica es un cuello de botella`} />
            {data.hypotheses.length > 1 && (
              <button type="button" onClick={() => onChange({ ...data, hypotheses: data.hypotheses.filter((_, j) => j !== i) })}
                style={{ width: "38px", border: "1px solid rgba(23,23,23,0.14)", background: "transparent", color: "#706f69", cursor: "pointer", fontSize: "16px" }}>
                ×
              </button>
            )}
          </div>
        ))}
        <button type="button" onClick={() => onChange({ ...data, hypotheses: [...data.hypotheses, ""] })}
          style={{ fontSize: "11px", fontFamily: "IBM Plex Mono, monospace", color: "#56624b", background: "transparent", border: "none", cursor: "pointer", padding: 0 }}>
          + Agregar hipótesis
        </button>
      </div>

      {/* Fuentes */}
      <div style={{ marginBottom: "28px" }}>
        <p style={{ margin: "0 0 6px", fontSize: "12px", fontWeight: 500, color: "#171717", fontFamily: "IBM Plex Mono, monospace", paddingBottom: "8px", borderBottom: "1px solid rgba(23,23,23,0.1)" }}>
          📚 Fuentes de contexto / literatura gris (opcional)
        </p>
        {data.grey_sources.map((g, i) => (
          <div key={i} style={{ display: "flex", gap: "8px", marginBottom: "8px" }}>
            <input style={inp} value={g} onChange={e => setGrey(i, e.target.value)}
              placeholder={`Fuente ${i + 1}: Ej: Benchmark sectorial 2024`} />
            {data.grey_sources.length > 1 && (
              <button type="button" onClick={() => onChange({ ...data, grey_sources: data.grey_sources.filter((_, j) => j !== i) })}
                style={{ width: "38px", border: "1px solid rgba(23,23,23,0.14)", background: "transparent", color: "#706f69", cursor: "pointer", fontSize: "16px" }}>
                ×
              </button>
            )}
          </div>
        ))}
        <button type="button" onClick={() => onChange({ ...data, grey_sources: [...data.grey_sources, ""] })}
          style={{ fontSize: "11px", fontFamily: "IBM Plex Mono, monospace", color: "#56624b", background: "transparent", border: "none", cursor: "pointer", padding: 0 }}>
          + Agregar fuente
        </button>
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", paddingTop: "8px" }}>
        <button onClick={onBack} style={{ height: "38px", padding: "0 20px", background: "transparent", color: "#706f69", border: "1px solid rgba(23,23,23,0.14)", fontSize: "12px", fontFamily: "IBM Plex Mono, monospace", cursor: "pointer" }}>
          ← Atrás
        </button>
        <button onClick={onNext} disabled={data.roles.length === 0 || data.dimensions.length === 0} style={{
          height: "38px", padding: "0 24px", background: "#171717", color: "#f4f1ea",
          border: "none", fontSize: "12px", fontFamily: "IBM Plex Mono, monospace", cursor: "pointer",
          opacity: (data.roles.length === 0 || data.dimensions.length === 0) ? 0.4 : 1,
        }}>
          Siguiente →
        </button>
      </div>
    </div>
  );
}
