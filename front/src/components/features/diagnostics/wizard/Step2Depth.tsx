"use client";

import { DEPTH_PRESETS, type DepthKey } from "@/config/pipeline-presets";
import type { DiagnosticDepth } from "@/lib/types";
import { CheckCircle, Circle } from "lucide-react";

const DEPTH_ACCENT: Record<DepthKey, string> = {
  basic:    "#243c4f",
  standard: "#56624b",
  complete: "#171717",
};

export function Step2Depth({
  depth, publish, certificate,
  onDepth, onPublish, onCertificate, onNext, onBack,
}: {
  depth: DiagnosticDepth; publish: boolean; certificate: boolean;
  onDepth: (d: DiagnosticDepth) => void; onPublish: (v: boolean) => void;
  onCertificate: (v: boolean) => void; onNext: () => void; onBack: () => void;
}) {
  return (
    <div style={{ display: "grid", gap: "24px" }}>
      <div>
        <h2 style={{ margin: 0, fontSize: "20px", fontWeight: 500, color: "#171717", fontFamily: "Cormorant Garamond, serif" }}>
          Tipo de diagnóstico
        </h2>
        <p style={{ margin: "6px 0 0", fontSize: "13px", color: "#706f69" }}>
          Elige la profundidad del análisis. El sistema activará automáticamente los módulos necesarios.
        </p>
      </div>

      {/* Opciones de profundidad */}
      <div style={{ display: "grid", gap: "8px" }}>
        {(Object.entries(DEPTH_PRESETS) as [DepthKey, typeof DEPTH_PRESETS[DepthKey]][]).map(([key, preset]) => {
          const selected = depth === key;
          const accent = DEPTH_ACCENT[key];
          return (
            <button
              key={key}
              type="button"
              onClick={() => onDepth(key)}
              style={{
                width: "100%", textAlign: "left", padding: "16px",
                border: selected ? `1px solid ${accent}` : "1px solid rgba(23,23,23,0.12)",
                background: selected ? `${accent}08` : "#fff",
                cursor: "pointer", transition: "all 0.15s",
              }}
            >
              <div style={{ display: "flex", alignItems: "flex-start", gap: "12px" }}>
                <div style={{ marginTop: "2px", flexShrink: 0 }}>
                  {selected
                    ? <CheckCircle size={18} style={{ color: accent }} />
                    : <Circle size={18} style={{ color: "rgba(23,23,23,0.2)" }} />
                  }
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
                    <span style={{ fontSize: "14px", fontWeight: 500, color: "#171717" }}>{preset.label}</span>
                    <span style={{
                      fontSize: "10px", fontFamily: "IBM Plex Mono, monospace", fontWeight: 500,
                      padding: "2px 8px",
                      background: selected ? `${accent}14` : "rgba(23,23,23,0.06)",
                      color: selected ? accent : "#706f69",
                    }}>
                      {preset.tools.length} módulos
                    </span>
                    <span style={{ fontSize: "11px", color: "#706f69" }}>⏱ {preset.duration}</span>
                  </div>
                  <p style={{ margin: "4px 0 0", fontSize: "13px", color: "#706f69" }}>{preset.subtitle}</p>

                  {selected && (
                    <div style={{ marginTop: "14px", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
                      <div>
                        <p style={{ margin: "0 0 8px", fontSize: "10px", fontFamily: "IBM Plex Mono, monospace", color: "#56624b", fontWeight: 500 }}>✓ INCLUYE</p>
                        <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "grid", gap: "4px" }}>
                          {preset.includes.map(item => (
                            <li key={item} style={{ fontSize: "12px", color: "#222522", display: "flex", gap: "6px" }}>
                              <span style={{ color: "#56624b", flexShrink: 0 }}>·</span>{item}
                            </li>
                          ))}
                        </ul>
                      </div>
                      {preset.excludes.length > 0 && (
                        <div>
                          <p style={{ margin: "0 0 8px", fontSize: "10px", fontFamily: "IBM Plex Mono, monospace", color: "#706f69", fontWeight: 500 }}>✗ NO INCLUYE</p>
                          <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "grid", gap: "4px" }}>
                            {preset.excludes.map(item => (
                              <li key={item} style={{ fontSize: "12px", color: "#706f69", display: "flex", gap: "6px" }}>
                                <span style={{ flexShrink: 0 }}>·</span>{item}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </button>
          );
        })}
      </div>

      {/* Opciones */}
      <div style={{ borderTop: "1px solid rgba(23,23,23,0.1)", paddingTop: "20px" }}>
        <p style={{ margin: "0 0 14px", fontSize: "10px", fontFamily: "IBM Plex Mono, monospace", color: "#706f69", fontWeight: 500, letterSpacing: "0.06em" }}>
          OPCIONES
        </p>
        <label style={{ display: "flex", alignItems: "flex-start", gap: "12px", cursor: "pointer", padding: "12px", border: "1px solid rgba(23,23,23,0.08)", background: "rgba(23,23,23,0.02)" }}>
          <input
            type="checkbox"
            checked={certificate}
            onChange={e => onCertificate(e.target.checked)}
            style={{ marginTop: "2px", width: "14px", height: "14px", accentColor: "#171717", flexShrink: 0 }}
          />
          <div>
            <p style={{ margin: 0, fontSize: "13px", fontWeight: 500, color: "#171717" }}>Emitir certificado de gobernanza</p>
            <p style={{ margin: "3px 0 0", fontSize: "12px", color: "#706f69" }}>
              Genera un certificado firmado digitalmente que acredita cómo se ejecutó el diagnóstico.
            </p>
          </div>
        </label>
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", paddingTop: "8px" }}>
        <button type="button" onClick={onBack} className="btn-secondary" style={{ height: "38px", padding: "0 20px" }}>
          ← Atrás
        </button>
        <button type="button" onClick={onNext} className="btn-primary" style={{ height: "38px", padding: "0 24px" }}>
          Siguiente →
        </button>
      </div>
    </div>
  );
}
