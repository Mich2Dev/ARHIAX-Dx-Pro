"use client";

import { useState } from "react";
import {
  Download, Loader2, CheckCircle, AlertTriangle,
  Lightbulb, TrendingUp, Activity, ChevronDown, ChevronUp,
  ShieldCheck, Hash,
} from "lucide-react";
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Tooltip as RechartsTooltip } from "recharts";

// ── Panel PMEL / Gobernanza ───────────────────────────────────────────────────
export function ProGovernancePanel({ caseData }: { caseData: any }) {
  const [expanded, setExpanded] = useState(false);

  const outcome = caseData.pmel_outcome ?? "—";
  const traceId = caseData.trace_id;
  const consent = caseData.consent ?? {};
  const consents = consent.consents ?? {};

  const outcomeColor =
    outcome === "PERMIT"  ? "#56624b" :
    outcome === "DENY"    ? "#8b3a3a" :
    outcome === "SUSPEND" ? "#8b3a3a" :
    outcome === "ESCALATE"? "#9b6d4d" : "#706f69";

  const packages = [
    "arhia.pmel.base.autonomy",
    "arhia.pmel.governance.consent_gates",
    "arhia.pmel.base.aibom",
    "arhia.pmel.governance.cycle_limits",
  ];

  return (
    <div style={{ background: "rgba(244,241,234,0.96)", border: "1px solid rgba(23,23,23,0.14)", padding: "20px" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "16px" }}>
        <ShieldCheck size={16} style={{ color: "#56624b" }} />
        <h3 style={{ margin: 0, fontSize: "12px", fontFamily: "IBM Plex Mono, monospace", fontWeight: 500, color: "#222522" }}>
          GOBERNANZA PMEL/ATK
        </h3>
      </div>

      {/* Decisión */}
      <div style={{
        display: "flex", alignItems: "center", gap: "10px",
        padding: "10px 14px", marginBottom: "16px",
        background: `${outcomeColor}12`,
        border: `1px solid ${outcomeColor}30`,
      }}>
        <div style={{ width: "8px", height: "8px", borderRadius: "50%", background: outcomeColor, flexShrink: 0 }} />
        <span style={{ fontSize: "12px", fontFamily: "IBM Plex Mono, monospace", fontWeight: 500, color: outcomeColor }}>
          {outcome}
        </span>
      </div>

      {/* Consentimientos */}
      <div style={{ display: "grid", gap: "6px", marginBottom: "16px" }}>
        {Object.entries(consents).map(([key, val]) => (
          <div key={key} style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "11px", fontFamily: "IBM Plex Mono, monospace" }}>
            <span style={{ color: val ? "#56624b" : "#8b3a3a" }}>{val ? "✓" : "✗"}</span>
            <span style={{ color: "#706f69" }}>{key}</span>
            <span style={{ color: val ? "#56624b" : "#8b3a3a", marginLeft: "auto" }}>
              {val ? "otorgado" : "denegado"}
            </span>
          </div>
        ))}
      </div>

      {/* Toggle paquetes */}
      <button
        onClick={() => setExpanded(e => !e)}
        style={{
          width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "8px 0", background: "transparent", border: "none",
          borderTop: "1px solid rgba(23,23,23,0.14)", cursor: "pointer",
          fontSize: "11px", fontFamily: "IBM Plex Mono, monospace", color: "#706f69",
        }}
      >
        <span>{expanded ? "Ocultar paquetes" : `Ver ${packages.length} paquetes PMEL`}</span>
        {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
      </button>

      {expanded && (
        <div style={{ display: "grid", gap: "4px", marginTop: "8px" }}>
          {packages.map(pkg => (
            <div key={pkg} style={{ display: "flex", alignItems: "center", gap: "8px", padding: "6px 0", borderBottom: "1px solid rgba(23,23,23,0.07)" }}>
              <CheckCircle size={11} style={{ color: "#56624b", flexShrink: 0 }} />
              <span style={{ fontSize: "11px", fontFamily: "IBM Plex Mono, monospace", color: "#56624b" }}>{pkg}</span>
            </div>
          ))}
        </div>
      )}

      {/* Trace */}
      {traceId && (
        <div style={{ marginTop: "12px", paddingTop: "12px", borderTop: "1px solid rgba(23,23,23,0.14)" }}>
          <p style={{ margin: 0, fontSize: "10px", fontFamily: "IBM Plex Mono, monospace", color: "#706f69" }}>TRACE ID</p>
          <p style={{ margin: "4px 0 0", fontSize: "11px", fontFamily: "IBM Plex Mono, monospace", color: "#222522", wordBreak: "break-all" }}>
            {traceId}
          </p>
        </div>
      )}
    </div>
  );
}

// ── Autonomómetro Pro ─────────────────────────────────────────────────────────
export function ProAutonometer() {
  const levels = [
    { level: "A0", label: "Observación", color: "rgba(23,23,23,0.15)" },
    { level: "A1", label: "Asistido",    color: "#243c4f" },
    { level: "A2", label: "Autónomo",    color: "#56624b" },
    { level: "A3", label: "Avanzado",    color: "#9b6d4d" },
    { level: "A4", label: "Máximo",      color: "#8b3a3a" },
  ];
  const currentIdx = 1; // Pro opera en A1 por defecto

  return (
    <div style={{ background: "rgba(244,241,234,0.96)", border: "1px solid rgba(23,23,23,0.14)", padding: "20px" }}>
      <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "16px" }}>
        <Activity size={16} style={{ color: "#56624b" }} />
        <h3 style={{ margin: 0, fontSize: "12px", fontFamily: "IBM Plex Mono, monospace", fontWeight: 500, color: "#222522" }}>
          AUTONOMÓMETRO
        </h3>
        <span style={{
          marginLeft: "auto", fontSize: "10px", fontFamily: "IBM Plex Mono, monospace",
          padding: "2px 8px", background: "rgba(36,60,79,0.1)", color: "#243c4f",
        }}>
          A1 — Asistido
        </span>
      </div>

      {/* Barra */}
      <div style={{ display: "flex", gap: "3px", marginBottom: "8px" }}>
        {levels.map((l, i) => (
          <div key={l.level} style={{
            flex: 1, height: "8px",
            background: i <= currentIdx ? l.color : "rgba(23,23,23,0.08)",
          }} />
        ))}
      </div>
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        {levels.map(l => (
          <span key={l.level} style={{
            fontSize: "10px", fontFamily: "IBM Plex Mono, monospace",
            color: l.level === "A1" ? "#171717" : "#c0bdb6",
            fontWeight: l.level === "A1" ? 500 : 400,
          }}>{l.level}</span>
        ))}
      </div>
    </div>
  );
}

// ── Métricas de ejecución ─────────────────────────────────────────────────────
export function ProExecutionMetrics({ caseData }: { caseData: any }) {
  const stages = [
    caseData.fusion_result,
    caseData.report_result,
    caseData.render_result,
    caseData.export_result,
  ].filter(Boolean);

  const completed = stages.filter(s => s?.outcome === "PERMIT").length;
  const deliverables = (caseData.deliverables ?? []).length;
  const totalSize = (caseData.deliverables ?? []).reduce((a: number, d: any) => a + (d.size_bytes ?? 0), 0);

  return (
    <div style={{ background: "rgba(244,241,234,0.96)", border: "1px solid rgba(23,23,23,0.14)", padding: "20px" }}>
      <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "16px" }}>
        <TrendingUp size={16} style={{ color: "#56624b" }} />
        <h3 style={{ margin: 0, fontSize: "12px", fontFamily: "IBM Plex Mono, monospace", fontWeight: 500, color: "#222522" }}>
          MÉTRICAS
        </h3>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1px", background: "rgba(23,23,23,0.14)" }}>
        {[
          { label: "Etapas OK",     value: `${completed}/4`,                  color: "#56624b" },
          { label: "Entregables",   value: deliverables,                       color: "#243c4f" },
          { label: "Tamaño total",  value: `${(totalSize / 1024).toFixed(1)} KB`, color: "#706f69" },
          { label: "Estado",        value: caseData.case_status ?? "—",        color: "#9b6d4d" },
        ].map(({ label, value, color }) => (
          <div key={label} style={{ background: "#f4f1ea", padding: "12px" }}>
            <p style={{ margin: 0, fontSize: "10px", fontFamily: "IBM Plex Mono, monospace", color: "#706f69" }}>{label}</p>
            <p style={{ margin: "6px 0 0", fontSize: "18px", fontWeight: 500, color }}>{value}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

import { useDownloadProCase } from "@/hooks/useDownload";

// ── Panel de resultados completo ──────────────────────────────────────────────
export function ProResultsPanel({ caseData, caseId }: { caseData: any; caseId: string }) {
  const { download, loading: downloading, error: downloadError } = useDownloadProCase();
  const canDownload = ["approved", "published"].includes(caseData.case_status);

  const fusion  = caseData.fusion_result  ?? {};
  const report  = caseData.report_result  ?? {};
  const render  = caseData.render_result  ?? {};

  const scoring     = fusion.scoring ?? {};
  const hypotheses  = fusion.hypotheses ?? [];
  const riskSignals = fusion.risk_signals ?? [];
  const thesis      = fusion.executive_thesis ?? "";
  const nextStep    = fusion.recommended_next_step ?? "";
  const sections    = report.sections ?? [];
  const markdown    = render.markdown ?? "";

  return (
    <div style={{ display: "grid", gap: "1px" }}>

      {/* Barra de descarga */}
      <div style={{
        background: "#222522", padding: "20px 24px",
        display: "flex", alignItems: "center", justifyContent: "space-between", gap: "16px",
      }}>
        <div>
          <p style={{ margin: 0, fontSize: "14px", fontWeight: 500, color: "#f4f1ea" }}>
            Diagnóstico completado
          </p>
          <p style={{ margin: "4px 0 0", fontSize: "12px", color: "rgba(244,241,234,0.5)" }}>
            {(caseData.deliverables ?? []).length} entregables generados
          </p>
        </div>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "6px" }}>
          {!canDownload && (
            <p style={{ margin: 0, fontSize: "10px", color: "rgba(244,241,234,0.55)", fontFamily: "IBM Plex Mono, monospace" }}>
              Aprueba el caso para habilitar descargas
            </p>
          )}
          {downloadError && (
            <p style={{ margin: 0, fontSize: "10px", color: "#e8b4b4", fontFamily: "IBM Plex Mono, monospace", maxWidth: "280px", textAlign: "right" }}>
              {downloadError}
            </p>
          )}
          <div style={{ display: "flex", gap: "8px" }}>
          {["markdown", "docx", "pdf"].map(target => (
            <button
              key={target}
              onClick={() => download(caseId, target, caseData.client_name ?? "diagnostico").catch(() => {})}
              disabled={!!downloading || !canDownload}
              style={{
                display: "flex", alignItems: "center", gap: "6px",
                minHeight: "38px", border: "1px solid rgba(244,241,234,0.2)", padding: "8px 14px",
                background: downloading === target ? "rgba(244,241,234,0.1)" : "rgba(244,241,234,0.08)",
                color: "#f4f1ea", fontSize: "11px", fontFamily: "IBM Plex Mono, monospace",
                cursor: downloading ? "not-allowed" : "pointer",
                opacity: downloading && downloading !== target ? 0.4 : 1,
              }}
            >
              {downloading === target
                ? <Loader2 size={11} style={{ animation: "spin 1s linear infinite" }} />
                : <Download size={11} />
              }
              {target.toUpperCase()}
            </button>
          ))}
          </div>
        </div>
      </div>

      {/* Score global */}
      {scoring.overall_score != null && (
        <div style={{ background: "rgba(244,241,234,0.96)", padding: "24px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <CheckCircle size={16} style={{ color: "#56624b" }} />
              <h3 style={{ margin: 0, fontSize: "13px", fontWeight: 500, color: "#171717" }}>Índice de Madurez</h3>
            </div>
            <div style={{ fontSize: "36px", fontWeight: 500, color: scoring.overall_score >= 70 ? "#56624b" : "#9b6d4d", fontFamily: "Cormorant Garamond, serif" }}>
              {scoring.overall_score}
              <span style={{ fontSize: "16px", color: "#706f69", fontFamily: "Manrope, sans-serif" }}>/100</span>
            </div>
          </div>

          {/* Scores por dimensión */}
          {scoring.dimension_scores?.length > 0 && (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "24px", alignItems: "center" }}>
              <div style={{ display: "grid", gap: "8px" }}>
                {scoring.dimension_scores.map((d: any) => (
                  <div key={d.dimension} style={{ display: "grid", gridTemplateColumns: "120px 1fr 60px 60px", gap: "12px", alignItems: "center" }}>
                    <span style={{ fontSize: "12px", color: "#706f69", fontFamily: "IBM Plex Mono, monospace" }}>{d.dimension}</span>
                    <div style={{ height: "6px", background: "rgba(23,23,23,0.08)" }}>
                      <div style={{ height: "6px", background: d.score >= 70 ? "#56624b" : "#9b6d4d", width: `${d.score}%`, transition: "width 0.7s" }} />
                    </div>
                    <span style={{ fontSize: "12px", fontWeight: 500, color: "#171717", textAlign: "right" }}>{d.score}</span>
                    <span style={{ fontSize: "11px", color: d.gap >= 0 ? "#56624b" : "#8b3a3a", textAlign: "right", fontFamily: "IBM Plex Mono, monospace" }}>
                      {d.gap >= 0 ? "+" : ""}{d.gap}
                    </span>
                  </div>
                ))}
              </div>

              {/* Radar Chart Visual */}
              <div style={{ width: "100%", height: "240px", display: "flex", justifyContent: "center" }}>
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart cx="50%" cy="50%" outerRadius="70%" data={scoring.dimension_scores}>
                    <PolarGrid stroke="rgba(23,23,23,0.1)" />
                    <PolarAngleAxis dataKey="dimension" tick={{ fill: '#706f69', fontSize: 10, fontFamily: 'IBM Plex Mono, monospace' }} />
                    <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: 'rgba(23,23,23,0.3)', fontSize: 10 }} />
                    <Radar name="Score" dataKey="score" stroke="#56624b" strokeWidth={2} fill="#56624b" fillOpacity={0.15} />
                    <RechartsTooltip 
                      contentStyle={{ background: '#171717', border: 'none', borderRadius: '4px', color: '#f4f1ea', fontSize: '11px', fontFamily: 'IBM Plex Mono, monospace' }}
                      itemStyle={{ color: '#a8d8a8' }}
                    />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tesis ejecutiva */}
      {thesis && (
        <div style={{ background: "rgba(244,241,234,0.96)", padding: "24px" }}>
          <h3 style={{ margin: "0 0 12px", fontSize: "13px", fontWeight: 500, color: "#171717" }}>Tesis Ejecutiva</h3>
          <p style={{ margin: 0, fontSize: "14px", color: "#222522", lineHeight: 1.6 }}>{thesis}</p>
        </div>
      )}

      {/* Hipótesis */}
      {hypotheses.length > 0 && (
        <div style={{ background: "rgba(244,241,234,0.96)", padding: "24px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "16px" }}>
            <AlertTriangle size={16} style={{ color: "#9b6d4d" }} />
            <h3 style={{ margin: 0, fontSize: "13px", fontWeight: 500, color: "#171717" }}>
              Hipótesis Evaluadas ({hypotheses.length})
            </h3>
          </div>
          <div style={{ display: "grid", gap: "8px" }}>
            {hypotheses.map((h: any, i: number) => (
              <div key={i} style={{
                padding: "14px 16px",
                border: `1px solid ${h.supported ? "rgba(86,98,75,0.3)" : "rgba(23,23,23,0.14)"}`,
                background: h.supported ? "rgba(86,98,75,0.05)" : "transparent",
              }}>
                <div style={{ display: "flex", alignItems: "flex-start", gap: "10px" }}>
                  <span style={{
                    fontSize: "10px", fontFamily: "IBM Plex Mono, monospace", fontWeight: 500,
                    padding: "2px 6px", flexShrink: 0, marginTop: "2px",
                    background: h.supported ? "rgba(86,98,75,0.12)" : "rgba(23,23,23,0.06)",
                    color: h.supported ? "#56624b" : "#706f69",
                  }}>
                    {h.supported ? "CONFIRMADA" : "NO CONFIRMADA"}
                  </span>
                  <p style={{ margin: 0, fontSize: "13px", color: "#171717", flex: 1 }}>{h.statement}</p>
                  <div style={{ textAlign: "right", flexShrink: 0 }}>
                    <p style={{ margin: 0, fontSize: "11px", fontFamily: "IBM Plex Mono, monospace", color: "#706f69" }}>
                      prior: {h.prior}
                    </p>
                    <p style={{ margin: "2px 0 0", fontSize: "13px", fontWeight: 500, color: h.supported ? "#56624b" : "#9b6d4d" }}>
                      P={h.posterior}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Señales de riesgo */}
      {riskSignals.length > 0 && (
        <div style={{ background: "rgba(244,241,234,0.96)", padding: "24px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "16px" }}>
            <AlertTriangle size={16} style={{ color: "#8b3a3a" }} />
            <h3 style={{ margin: 0, fontSize: "13px", fontWeight: 500, color: "#171717" }}>
              Señales de Riesgo ({riskSignals.length})
            </h3>
          </div>
          <div style={{ display: "grid", gap: "6px" }}>
            {riskSignals.map((r: any, i: number) => (
              <div key={i} style={{
                display: "flex", alignItems: "center", gap: "12px", padding: "10px 14px",
                border: `1px solid ${r.severity === "high" ? "rgba(139,58,58,0.3)" : "rgba(155,109,77,0.3)"}`,
                background: r.severity === "high" ? "rgba(139,58,58,0.05)" : "rgba(155,109,77,0.05)",
              }}>
                <span style={{
                  fontSize: "10px", fontFamily: "IBM Plex Mono, monospace", fontWeight: 500,
                  padding: "2px 6px", flexShrink: 0,
                  background: r.severity === "high" ? "rgba(139,58,58,0.12)" : "rgba(155,109,77,0.12)",
                  color: r.severity === "high" ? "#8b3a3a" : "#9b6d4d",
                }}>
                  {r.severity?.toUpperCase()}
                </span>
                <span style={{ fontSize: "13px", color: "#171717" }}>{r.signal}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Secciones del reporte */}
      {sections.length > 0 && (
        <div style={{ background: "rgba(244,241,234,0.96)", padding: "24px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "16px" }}>
            <Lightbulb size={16} style={{ color: "#9b6d4d" }} />
            <h3 style={{ margin: 0, fontSize: "13px", fontWeight: 500, color: "#171717" }}>
              Reporte Ejecutivo — {sections.length} secciones
            </h3>
          </div>
          <div style={{ display: "grid", gap: "1px", background: "rgba(23,23,23,0.14)" }}>
            {sections.map((s: any, i: number) => (
              <SectionRow key={i} section={s} />
            ))}
          </div>
        </div>
      )}

      {/* Próximo paso */}
      {nextStep && (
        <div style={{
          background: "rgba(86,98,75,0.06)", border: "1px solid rgba(86,98,75,0.2)",
          borderLeft: "3px solid #56624b", padding: "20px 24px",
        }}>
          <p style={{ margin: "0 0 6px", fontSize: "11px", fontFamily: "IBM Plex Mono, monospace", color: "#56624b", fontWeight: 500 }}>
            PRÓXIMO PASO RECOMENDADO
          </p>
          <p style={{ margin: 0, fontSize: "14px", color: "#171717" }}>{nextStep}</p>
        </div>
      )}

      {/* Markdown preview */}
      {markdown && <MarkdownPreview markdown={markdown} />}
    </div>
  );
}

// ── Sección del reporte expandible ───────────────────────────────────────────
function SectionRow({ section }: { section: any }) {
  const [open, setOpen] = useState(false);
  return (
    <div style={{ background: "#f4f1ea" }}>
      <button
        onClick={() => section.content && setOpen(o => !o)}
        style={{
          width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "14px 16px", background: "transparent", border: "none",
          cursor: section.content ? "pointer" : "default", textAlign: "left",
        }}
      >
        <span style={{ fontSize: "13px", fontWeight: 500, color: "#171717" }}>{section.title}</span>
        {section.content && (
          open
            ? <ChevronUp size={13} style={{ color: "rgba(23,23,23,0.3)" }} />
            : <ChevronDown size={13} style={{ color: "rgba(23,23,23,0.3)" }} />
        )}
      </button>
      {open && section.content && (
        <div style={{ padding: "0 16px 16px", fontSize: "13px", color: "#706f69", lineHeight: 1.6 }}>
          {section.content}
        </div>
      )}
    </div>
  );
}

// ── Preview del Markdown ──────────────────────────────────────────────────────
function MarkdownPreview({ markdown }: { markdown: string }) {
  const [open, setOpen] = useState(false);
  const lines = markdown.split("\n").slice(0, 8).join("\n");

  return (
    <div style={{ background: "rgba(244,241,234,0.96)", padding: "24px" }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between",
          background: "transparent", border: "none", cursor: "pointer", padding: 0,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <Hash size={16} style={{ color: "#706f69" }} />
          <h3 style={{ margin: 0, fontSize: "13px", fontWeight: 500, color: "#171717" }}>
            Vista previa Markdown
          </h3>
        </div>
        {open ? <ChevronUp size={13} style={{ color: "rgba(23,23,23,0.3)" }} /> : <ChevronDown size={13} style={{ color: "rgba(23,23,23,0.3)" }} />}
      </button>

      {open && (
        <pre style={{
          marginTop: "16px", padding: "16px",
          background: "#171717", color: "#a8d8a8",
          fontFamily: "IBM Plex Mono, monospace", fontSize: "11px",
          lineHeight: 1.6, overflow: "auto", maxHeight: "320px",
          whiteSpace: "pre-wrap", wordBreak: "break-word",
        }}>
          {markdown}
        </pre>
      )}
      {!open && (
        <pre style={{
          marginTop: "12px", padding: "12px",
          background: "#171717", color: "#a8d8a8",
          fontFamily: "IBM Plex Mono, monospace", fontSize: "11px",
          lineHeight: 1.6, overflow: "hidden", maxHeight: "80px",
          whiteSpace: "pre-wrap", wordBreak: "break-word",
          opacity: 0.7,
        }}>
          {lines}…
        </pre>
      )}
    </div>
  );
}
