"use client";

import { CheckCircle, Circle } from "lucide-react";
import {
  emptyHypothesis,
  isHypothesisComplete,
  type ProHypothesis,
} from "./hypothesisPack";

export interface ProScopeData {
  survey_mode: "single_rater" | "multi_rater";
  roles: string[];
  dimensions: string[];
  hypothesis_pack: ProHypothesis[];
  grey_sources: string[];
}

export const defaultScope: ProScopeData = {
  survey_mode: "multi_rater",
  roles: ["executive", "operations", "technology"],
  dimensions: ["strategy", "process", "technology"],
  hypothesis_pack: [emptyHypothesis(0)],
  grey_sources: [""],
};

const ROLES = [
  { value: "executive",  label: "Estratégico",  desc: "Alta dirección y gobernanza (C-suite)" },
  { value: "operations", label: "Operativo",    desc: "Ejecución y procesos en planta" },
  { value: "technology", label: "Táctico",      desc: "Gestión, coordinación y tecnología" },
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
  function setSurveyMode(mode: "single_rater" | "multi_rater") {
    if (mode === "single_rater") {
      onChange({ ...data, survey_mode: mode, roles: ["executive"] });
      return;
    }
    const roles = data.roles.length >= 2
      ? data.roles
      : ["executive", "operations", "technology"];
    onChange({ ...data, survey_mode: mode, roles });
  }

  function toggleRole(v: string) {
    if (data.survey_mode === "single_rater") return;
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
  const minRoles = data.survey_mode === "single_rater" ? 1 : 2;
  const canNext =
    data.roles.length >= minRoles &&
    data.dimensions.length > 0 &&
    completeHyps.length > 0;

  return (
    <div>
      <div style={{ marginBottom: "24px" }}>
        <h2 style={{ margin: 0, fontSize: "20px", fontWeight: 500, color: "#171717", fontFamily: "Cormorant Garamond, serif" }}>
          Alcance del diagnóstico
        </h2>
        <p style={{ margin: "6px 0 0", fontSize: "13px", color: "#706f69" }}>
          Elija quién responde la encuesta y ancle hipótesis a incidentes reales — el sistema adapta el informe automáticamente.
        </p>
      </div>

      <div style={{ marginBottom: "28px" }}>
        <p style={{ margin: "0 0 12px", fontSize: "12px", fontWeight: 500, color: "#171717", fontFamily: "IBM Plex Mono, monospace", paddingBottom: "8px", borderBottom: "1px solid rgba(23,23,23,0.1)" }}>
          ¿Quién responde la encuesta? *
        </p>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
          {([
            { mode: "single_rater" as const, title: "Una sola persona", desc: "CEO, dueño o decisor único. Informe de perspectiva única." },
            { mode: "multi_rater" as const, title: "Varias personas", desc: "2–3 roles (dirección, operación, táctico). Compara brechas entre niveles." },
          ]).map(opt => {
            const active = data.survey_mode === opt.mode;
            return (
              <button key={opt.mode} type="button" onClick={() => setSurveyMode(opt.mode)} style={{
                display: "flex", flexDirection: "column", alignItems: "flex-start", gap: "6px",
                padding: "14px 16px", textAlign: "left",
                border: active ? "1px solid #222522" : "1px solid rgba(23,23,23,0.12)",
                background: active ? "rgba(23,23,23,0.04)" : "#fff",
                cursor: "pointer",
              }}>
                <span style={{ fontSize: "13px", fontWeight: 600, color: "#171717" }}>{opt.title}</span>
                <span style={{ fontSize: "11px", color: "#706f69", lineHeight: 1.45 }}>{opt.desc}</span>
              </button>
            );
          })}
        </div>
      </div>

      <div style={{ marginBottom: "28px" }}>
        <p style={{ margin: "0 0 12px", fontSize: "12px", fontWeight: 500, color: "#171717", fontFamily: "IBM Plex Mono, monospace", paddingBottom: "8px", borderBottom: "1px solid rgba(23,23,23,0.1)" }}>
          Roles participantes *{" "}
          <span style={{ fontWeight: 400, color: "#706f69", textTransform: "none" }}>
            {data.survey_mode === "single_rater"
              ? "(perspectiva única — decisor)"
              : "(multi-rater — cada rol responde por separado)"}
          </span>
        </p>
        <p style={{ margin: "0 0 12px", fontSize: "12px", color: "#706f69", lineHeight: 1.5 }}>
          {data.survey_mode === "single_rater"
            ? "Solo el decisor principal responde. Las dimensiones (abajo) definen qué se evalúa."
            : "Cada rol debe responder la encuesta por separado. Las dimensiones son qué se evalúa, no quién responde."}
        </p>
        <div className="dx-form-grid-2" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
          {ROLES.map(r => {
            const active = data.roles.includes(r.value);
            const locked = data.survey_mode === "single_rater" && r.value !== "executive";
            return (
              <button key={r.value} type="button" onClick={() => toggleRole(r.value)} disabled={locked} style={{
                display: "flex", alignItems: "flex-start", gap: "10px",
                padding: "12px 14px", textAlign: "left",
                border: active ? "1px solid #222522" : "1px solid rgba(23,23,23,0.12)",
                background: active ? "rgba(23,23,23,0.04)" : "#fff",
                cursor: locked ? "not-allowed" : "pointer",
                opacity: locked ? 0.45 : 1,
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
