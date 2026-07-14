"use client";

import { Loader2, AlertTriangle, CheckCircle2, Download } from "lucide-react";
import type { CSSProperties } from "react";
import { apiPro } from "@/lib/api-pro";

type PhenomenonDoc = {
  type: string;
  priority?: number;
  audience?: string;
  purpose?: string;
};

type PhenomenonSummary = {
  phenomenon_named?: string;
  convergence_summary?: string;
  resolution_motor?: string;
  resolution_rule?: string;
  hinge_question?: string;
  gates_passed?: boolean;
  blocking_reasons?: string[];
  recommended_documents?: PhenomenonDoc[];
  next_operational_step?: string;
  commercial_safe?: boolean;
  use_survey?: boolean;
};

type PhenomenonData = {
  status?: string;
  version?: string;
  updated_at?: string;
  summary?: PhenomenonSummary;
  stages?: { tool_name: string; status: string }[];
};

const DOC_LABELS: Record<string, string> = {
  internal_phenomenon: "Análisis interno (fenómeno)",
  discovery_form: "Formulario de descubrimiento",
  commercial_proposal: "Propuesta comercial",
  horizon_map: "Mapa de horizonte",
  executive_report: "Informe ejecutivo",
  seed_data_template: "Plantilla de datos semilla",
  survey_instrument: "Instrumento de encuesta",
  architecture_tr: "Arquitectura técnica",
  sprint_spec: "Especificación de sprint",
};

interface Props {
  phenomenon?: PhenomenonData | null;
  caseId?: string;
  analyzing?: boolean;
  onAnalyze?: () => void;
}

async function downloadMd(path: string, fallbackName: string) {
  try {
    const res = await apiPro.get(path, { responseType: "blob" });
    const disp = res.headers["content-disposition"] as string | undefined;
    const match = disp?.match(/filename="?([^"]+)"?/);
    const name = match?.[1] || fallbackName;
    const url = URL.createObjectURL(res.data);
    const a = document.createElement("a");
    a.href = url;
    a.download = name;
    a.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    const msg = err instanceof Error ? err.message : "No se pudo descargar el documento.";
    window.alert(msg);
  }
}

export function ProPhenomenonPanel({ phenomenon, caseId, analyzing, onAnalyze }: Props) {
  const status = analyzing ? "running" : phenomenon?.status;
  const summary = phenomenon?.summary;
  const isRunning = status === "running";
  const isFailed = status === "failed";
  const hasResult = Boolean(summary?.phenomenon_named && !isRunning && !isFailed);

  return (
    <div
      style={{
        background: "#fff",
        border: "1px solid rgba(23,23,23,0.1)",
        padding: "22px 24px",
        marginBottom: 8,
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          gap: 16,
          flexWrap: "wrap",
        }}
      >
        <div style={{ maxWidth: 560 }}>
          <p
            style={{
              margin: 0,
              fontSize: 10,
              fontFamily: "IBM Plex Mono, monospace",
              letterSpacing: "0.1em",
              color: "#9b6d4d",
            }}
          >
            FENÓMENO · EPOJÉ → CONVERGENCIA → TRIZ → KILL CRITIC
          </p>
          <h3
            style={{
              margin: "8px 0 0",
              fontFamily: "Cormorant Garamond, Georgia, serif",
              fontSize: 26,
              fontWeight: 500,
              color: "#171717",
              lineHeight: 1.1,
            }}
          >
            {hasResult ? summary!.phenomenon_named : "Todavía sin nombrar"}
          </h3>
          <p style={{ margin: "10px 0 0", fontSize: 13, color: "#706f69", lineHeight: 1.5 }}>
            Suspendé el diagnóstico declarado del cliente, triangulá con las siete puntas y nombrá el fenómeno
            antes de instrumentar campo o vender.
          </p>
        </div>
        {onAnalyze && (
          <button
            type="button"
            onClick={onAnalyze}
            disabled={isRunning || analyzing}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              padding: "11px 16px",
              background: isRunning ? "rgba(23,23,23,0.08)" : "#171717",
              border: "none",
              color: isRunning ? "#706f69" : "#f4f1ea",
              fontSize: 12,
              fontFamily: "IBM Plex Mono, monospace",
              cursor: isRunning ? "wait" : "pointer",
            }}
          >
            {isRunning ? <Loader2 size={14} style={{ animation: "spin 1s linear infinite" }} /> : null}
            {isRunning ? "Analizando…" : hasResult ? "Re-analizar" : "Analizar fenómeno"}
          </button>
        )}
      </div>

      {isRunning && (
        <p
          style={{
            marginTop: 16,
            fontSize: 12,
            color: "#56624b",
            fontFamily: "IBM Plex Mono, monospace",
          }}
        >
          Epojé → convergencia → contradicción → kill critic…
        </p>
      )}

      {isFailed && (
        <div
          style={{
            marginTop: 16,
            padding: 12,
            background: "rgba(139,58,58,0.08)",
            border: "1px solid rgba(139,58,58,0.25)",
            fontSize: 13,
            color: "#8b3a3a",
          }}
        >
          <AlertTriangle size={14} style={{ display: "inline", marginRight: 8, verticalAlign: "middle" }} />
          El análisis falló. Revisá el intake (síntoma e incidentes) y reintentá.
        </div>
      )}

      {hasResult && summary && (
        <div style={{ marginTop: 20, display: "grid", gap: 14 }}>
          {summary.convergence_summary && (
            <div style={{ padding: "14px 16px", background: "#f4f1ea", borderLeft: "3px solid #56624b" }}>
              <p style={{ margin: 0, fontSize: 10, color: "#9b6d4d", fontFamily: "IBM Plex Mono, monospace" }}>
                CONVERGENCIA
              </p>
              <p style={{ margin: "8px 0 0", fontSize: 14, color: "#171717", lineHeight: 1.55 }}>
                {summary.convergence_summary}
              </p>
            </div>
          )}

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 12 }}>
            {summary.resolution_motor && (
              <div style={{ padding: 14, border: "1px solid rgba(23,23,23,0.08)", background: "#fff" }}>
                <p style={{ margin: 0, fontSize: 10, color: "#56624b", fontFamily: "IBM Plex Mono, monospace" }}>
                  MOTOR
                </p>
                <p style={{ margin: "6px 0 0", fontSize: 13, color: "#171717", lineHeight: 1.45 }}>
                  {summary.resolution_motor}
                </p>
                {summary.resolution_rule && (
                  <p style={{ margin: "8px 0 0", fontSize: 12, color: "#706f69" }}>{summary.resolution_rule}</p>
                )}
              </div>
            )}
            {summary.hinge_question && (
              <div style={{ padding: 14, border: "1px solid rgba(23,23,23,0.08)", background: "#fff" }}>
                <p style={{ margin: 0, fontSize: 10, color: "#56624b", fontFamily: "IBM Plex Mono, monospace" }}>
                  PREGUNTA BISAGRA
                </p>
                <p style={{ margin: "6px 0 0", fontSize: 13, color: "#171717", lineHeight: 1.45 }}>
                  {summary.hinge_question}
                </p>
              </div>
            )}
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: "#171717" }}>
            {summary.gates_passed ? (
              <>
                <CheckCircle2 size={16} color="#56624b" />
                <span>Kill Critic: OK para avanzar</span>
              </>
            ) : (
              <>
                <AlertTriangle size={16} color="#9b6d4d" />
                <span>Kill Critic con advertencias — revisá antes de propuesta comercial</span>
              </>
            )}
          </div>

          {(summary.blocking_reasons?.length ?? 0) > 0 && (
            <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12, color: "#8b3a3a", lineHeight: 1.5 }}>
              {summary.blocking_reasons!.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          )}

          {(summary.recommended_documents?.length ?? 0) > 0 && (
            <div>
              <p style={{ margin: "0 0 8px", fontSize: 10, fontFamily: "IBM Plex Mono, monospace", color: "#9b6d4d" }}>
                DOCUMENTOS DERIVADOS
              </p>
              <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13, lineHeight: 1.6, color: "#171717" }}>
                {summary.recommended_documents!.map((d, i) => (
                  <li key={i}>
                    {DOC_LABELS[d.type] ?? d.type}
                    {d.purpose ? ` — ${d.purpose}` : ""}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {summary.next_operational_step && (
            <p style={{ margin: 0, fontSize: 12, fontFamily: "IBM Plex Mono, monospace", color: "#56624b" }}>
              → {summary.next_operational_step}
            </p>
          )}

          {caseId && (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginTop: 4 }}>
              <button
                type="button"
                onClick={() => downloadMd(`/pro/cases/${caseId}/download/phenomenon-internal`, "fenomeno_interno.md")}
                style={dlBtn}
              >
                <Download size={12} /> Análisis interno (.md)
              </button>
              <button
                type="button"
                onClick={() => downloadMd(`/pro/cases/${caseId}/download/phenomenon-discovery`, "descubrimiento.md")}
                style={dlBtn}
              >
                <Download size={12} /> Formulario descubrimiento (.md)
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

const dlBtn: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: 6,
  padding: "8px 12px",
  background: "#f4f1ea",
  border: "1px solid rgba(23,23,23,0.12)",
  color: "#171717",
  fontSize: 11,
  fontFamily: "IBM Plex Mono, monospace",
  cursor: "pointer",
};
