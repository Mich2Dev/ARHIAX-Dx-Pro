"use client";

import { CheckCircle, Circle } from "lucide-react";
import {
  emptyHypothesis,
  isHypothesisComplete,
  type ProHypothesis,
} from "./hypothesisPack";

export interface ProScopeData {
  roles: string[];
  dimensions: string[];
  hypothesis_pack: ProHypothesis[];
  grey_sources: string[];
}

export const defaultScope: ProScopeData = {
  roles: ["executive", "operations", "technology"],
  dimensions: ["strategy", "process", "technology"],
  hypothesis_pack: [emptyHypothesis(0)],
  grey_sources: [""],
};

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

const inp: React.CSSProperties = {
  width: "100%", minHeight: "38px", padding: "8px 12px",
  border: "1px solid rgba(23,23,23,0.18)",
  background: "rgba(255,255,255,0.6)",
  color: "#171717", fontFamily: "Manrope, sans-serif", fontSize: "13px",
  outline: "none", boxSizing: "border-box" as const,
};

const txt: React.CSSProperties = {
  ...inp, minHeight: "72px", resize: "vertical" as const, lineHeight: 1.45,
};

const label: React.CSSProperties = {
  display: "block", marginBottom: "4px", fontSize: "10px",
  fontFamily: "IBM Plex Mono, monospace", color: "#706f69",
  letterSpacing: "0.04em", textTransform: "uppercase",
};

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

  function updateHyp(i: number, patch: Partial<ProHypothesis>) {
    const hypothesis_pack = data.hypothesis_pack.map((h, idx) =>
      idx === i ? { ...h, ...patch } : h
    );
    onChange({ ...data, hypothesis_pack });
  }

  function setGrey(i: number, val: string) {
    const g = [...data.grey_sources]; g[i] = val;
    onChange({ ...data, grey_sources: g });
  }

  const completeHyps = data.hypothesis_pack.filter(isHypothesisComplete);
  const canNext = data.roles.length > 0 && data.dimensions.length > 0 && completeHyps.length > 0;

  return (
    <div>
      <div style={{ marginBottom: "24px" }}>
        <h2 style={{ margin: 0, fontSize: "20px", fontWeight: 500, color: "#171717", fontFamily: "Cormorant Garamond, serif" }}>
          Alcance del diagnóstico
        </h2>
        <p style={{ margin: "6px 0 0", fontSize: "13px", color: "#706f69" }}>
          Roles, dimensiones y hipótesis ancladas a incidentes reales — así la IA diseña preguntas específicas, no genéricas.
        </p>
      </div>

      <div style={{ marginBottom: "28px" }}>
        <p style={{ margin: "0 0 12px", fontSize: "12px", fontWeight: 500, color: "#171717", fontFamily: "IBM Plex Mono, monospace", paddingBottom: "8px", borderBottom: "1px solid rgba(23,23,23,0.1)" }}>
          Roles participantes *
        </p>
        <div className="dx-form-grid-2" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
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
      </div>

      <div style={{ marginBottom: "28px" }}>
        <p style={{ margin: "0 0 12px", fontSize: "12px", fontWeight: 500, color: "#171717", fontFamily: "IBM Plex Mono, monospace", paddingBottom: "8px", borderBottom: "1px solid rgba(23,23,23,0.1)" }}>
          Dimensiones a evaluar *
        </p>
        <div className="dx-form-grid-2" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
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
      </div>

      <div style={{ marginBottom: "28px" }}>
        <p style={{ margin: "0 0 6px", fontSize: "12px", fontWeight: 500, color: "#171717", fontFamily: "IBM Plex Mono, monospace", paddingBottom: "8px", borderBottom: "1px solid rgba(23,23,23,0.1)" }}>
          Hipótesis con incidente vivido *
        </p>
        <p style={{ margin: "0 0 16px", fontSize: "12px", color: "#706f69", lineHeight: 1.5 }}>
          Cada hipótesis necesita un enunciado, qué la refutaría y un episodio concreto vivido en la operación. Sin eso el instrumento cae a preguntas genéricas.
        </p>

        {data.hypothesis_pack.map((h, i) => (
          <div key={h.hipotesis_id} style={{
            marginBottom: "16px", padding: "16px",
            border: isHypothesisComplete(h) ? "1px solid rgba(86,98,75,0.35)" : "1px solid rgba(23,23,23,0.12)",
            background: "rgba(255,255,255,0.5)",
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "12px" }}>
              <span style={{ fontSize: "11px", fontFamily: "IBM Plex Mono, monospace", color: "#56624b" }}>{h.hipotesis_id}</span>
              {data.hypothesis_pack.length > 1 && (
                <button type="button" onClick={() => onChange({
                  ...data,
                  hypothesis_pack: data.hypothesis_pack.filter((_, j) => j !== i),
                })} style={{ background: "none", border: "none", color: "#8b3a3a", cursor: "pointer", fontSize: "12px" }}>
                  Eliminar
                </button>
              )}
            </div>

            <div style={{ marginBottom: "10px" }}>
              <label style={label}>Enunciado (qué sospechas que limita el throughput)</label>
              <input style={inp} value={h.enunciado} onChange={e => updateHyp(i, { enunciado: e.target.value })}
                placeholder="Ej: La aprobación de cambios en producción tarda más de lo que el mercado tolera" />
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", marginBottom: "10px" }}>
              <div>
                <label style={label}>Confianza</label>
                <select style={inp} value={h.confianza} onChange={e => updateHyp(i, { confianza: e.target.value as ProHypothesis["confianza"] })}>
                  <option value="ALTA">Alta</option>
                  <option value="MEDIA">Media</option>
                  <option value="BAJA">Baja</option>
                </select>
              </div>
              <div>
                <label style={label}>Dato duro esperado</label>
                <select style={inp} value={h.dato_duro} onChange={e => updateHyp(i, { dato_duro: e.target.value as ProHypothesis["dato_duro"] })}>
                  <option value="ALTO">Alto (restricción presente)</option>
                  <option value="BAJO">Bajo (no es cuello)</option>
                </select>
              </div>
            </div>

            <div style={{ marginBottom: "10px" }}>
              <label style={label}>Observación refutadora (qué verías si la hipótesis es falsa)</label>
              <input style={inp} value={h.observacion_refutadora} onChange={e => updateHyp(i, { observacion_refutadora: e.target.value })}
                placeholder="Ej: Los releases salen en menos de 48h sin escalamientos" />
            </div>

            <div>
              <label style={label}>Incidente vivido (episodio real, con contexto)</label>
              <textarea style={txt} value={h.incidente_texto} onChange={e => updateHyp(i, { incidente_texto: e.target.value })}
                placeholder="Ej: El martes pasado un fix crítico esperó 5 días en comité porque nadie sabía quién firmaba el despliegue..." />
            </div>
          </div>
        ))}

        <button type="button" onClick={() => onChange({
          ...data,
          hypothesis_pack: [...data.hypothesis_pack, emptyHypothesis(data.hypothesis_pack.length)],
        })}
          style={{ fontSize: "11px", fontFamily: "IBM Plex Mono, monospace", color: "#56624b", background: "transparent", border: "none", cursor: "pointer", padding: 0 }}>
          + Agregar hipótesis
        </button>
      </div>

      <div style={{ marginBottom: "28px" }}>
        <p style={{ margin: "0 0 6px", fontSize: "12px", fontWeight: 500, color: "#171717", fontFamily: "IBM Plex Mono, monospace", paddingBottom: "8px", borderBottom: "1px solid rgba(23,23,23,0.1)" }}>
          Fuentes de contexto (opcional)
        </p>
        {data.grey_sources.map((g, i) => (
          <div key={i} style={{ display: "flex", gap: "8px", marginBottom: "8px" }}>
            <input style={inp} value={g} onChange={e => setGrey(i, e.target.value)} placeholder={`Fuente ${i + 1}`} />
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
        <button onClick={onNext} disabled={!canNext} style={{
          height: "38px", padding: "0 24px", background: "#171717", color: "#f4f1ea",
          border: "none", fontSize: "12px", fontFamily: "IBM Plex Mono, monospace", cursor: "pointer",
          opacity: canNext ? 1 : 0.4,
        }}>
          Siguiente →
        </button>
      </div>
    </div>
  );
}
