"use client";

import { Loader2, Sparkles, AlertTriangle, CheckCircle2, Download } from "lucide-react";
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
  const hasResult = summary?.phenomenon_named && !isRunning && !isFailed;

  return (
    <div
      style={{
        background: "linear-gradient(135deg, #1a1a18 0%, #243c4f 100%)",
        borderRadius: "4px",
        padding: "20px 24px",
        marginBottom: "20px",
        color: "#f5f0e8",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "16px", flexWrap: "wrap" }}>
        <div>
          <p style={{ margin: 0, fontSize: "10px", fontFamily: "IBM Plex Mono, monospace", letterSpacing: "0.1em", color: "#9b6d4d" }}>
            MOTOR DE FENÓMENO · P01–P07
          </p>
          <h3 style={{ margin: "6px 0 0", fontFamily: "Cormorant Garamond, Georgia, serif", fontSize: "22px", fontWeight: 500 }}>
            Abordaje Governex
          </h3>
          <p style={{ margin: "8px 0 0", fontSize: "13px", color: "rgba(245,240,232,0.75)", maxWidth: "520px", lineHeight: 1.5 }}>
            Analiza el caso como consultor: refuta el diagnóstico del cliente, nombra el fenómeno real y deriva qué documentos generar.
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
              gap: "8px",
              padding: "10px 16px",
              background: isRunning ? "rgba(255,255,255,0.1)" : "#9b6d4d",
              border: "none",
              borderRadius: "2px",
              color: "#fff",
              fontSize: "12px",
              fontFamily: "IBM Plex Mono, monospace",
              cursor: isRunning ? "wait" : "pointer",
              opacity: isRunning ? 0.7 : 1,
            }}
          >
            {isRunning ? <Loader2 size={14} style={{ animation: "spin 1s linear infinite" }} /> : <Sparkles size={14} />}
            {isRunning ? "Analizando…" : hasResult ? "Re-analizar fenómeno" : "Analizar fenómeno"}
          </button>
        )}
      </div>

      {isRunning && (
        <p style={{ marginTop: "16px", fontSize: "12px", color: "rgba(245,240,232,0.8)", fontFamily: "IBM Plex Mono, monospace" }}>
          Ejecutando epoqué → convergencia → contradicción → kill critic…
        </p>
      )}

      {isFailed && (
        <div style={{ marginTop: "16px", padding: "12px", background: "rgba(139,58,58,0.3)", borderRadius: "2px", fontSize: "13px" }}>
          <AlertTriangle size={14} style={{ display: "inline", marginRight: "8px", verticalAlign: "middle" }} />
          El análisis de fenómeno falló. Reintente o revise el intake (síntoma e incidentes).
        </div>
      )}

      {hasResult && summary && (
        <div style={{ marginTop: "20px", display: "grid", gap: "14px" }}>
          <div style={{ padding: "14px", background: "rgba(0,0,0,0.25)", borderRadius: "2px" }}>
            <p style={{ margin: 0, fontSize: "10px", color: "#9b6d4d", fontFamily: "IBM Plex Mono, monospace" }}>FENÓMENO NOMBRADO</p>
            <p style={{ margin: "6px 0 0", fontSize: "16px", fontFamily: "Cormorant Garamond, Georgia, serif" }}>{summary.phenomenon_named}</p>
            {summary.convergence_summary && (
              <p style={{ margin: "8px 0 0", fontSize: "13px", color: "rgba(245,240,232,0.85)", lineHeight: 1.5 }}>{summary.convergence_summary}</p>
            )}
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "12px" }}>
            {summary.resolution_motor && (
              <div style={{ padding: "12px", background: "rgba(0,0,0,0.2)", borderRadius: "2px" }}>
                <p style={{ margin: 0, fontSize: "10px", color: "#56624b" }}>MOTOR</p>
                <p style={{ margin: "4px 0 0", fontSize: "13px" }}>{summary.resolution_motor}</p>
              </div>
            )}
            {summary.hinge_question && (
              <div style={{ padding: "12px", background: "rgba(0,0,0,0.2)", borderRadius: "2px" }}>
                <p style={{ margin: 0, fontSize: "10px", color: "#56624b" }}>PREGUNTA BISAGRA</p>
                <p style={{ margin: "4px 0 0", fontSize: "13px" }}>{summary.hinge_question}</p>
              </div>
            )}
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "13px" }}>
            {summary.gates_passed ? (
              <>
                <CheckCircle2 size={16} color="#56624b" />
                <span>Gates Kill Critic: OK para avanzar</span>
              </>
            ) : (
              <>
                <AlertTriangle size={16} color="#c9a227" />
                <span>Gates con advertencias — revisar antes de propuesta comercial</span>
              </>
            )}
          </div>

          {(summary.recommended_documents?.length ?? 0) > 0 && (
            <div>
              <p style={{ margin: "0 0 8px", fontSize: "10px", fontFamily: "IBM Plex Mono, monospace", color: "#9b6d4d" }}>
                DOCUMENTOS RECOMENDADOS
              </p>
              <ul style={{ margin: 0, paddingLeft: "18px", fontSize: "13px", lineHeight: 1.6 }}>
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
            <p style={{ margin: 0, fontSize: "12px", fontFamily: "IBM Plex Mono, monospace", color: "rgba(245,240,232,0.9)" }}>
              → {summary.next_operational_step}
            </p>
          )}

          {caseId && (
            <div style={{ display: "flex", flexWrap: "wrap", gap: "10px", marginTop: "8px" }}>
              <button
                type="button"
                onClick={() => downloadMd(`/pro/cases/${caseId}/download/phenomenon-internal`, "fenomeno_interno.md")}
                style={{
                  display: "inline-flex", alignItems: "center", gap: "6px",
                  padding: "8px 12px", background: "rgba(255,255,255,0.12)", border: "1px solid rgba(255,255,255,0.2)",
                  borderRadius: "2px", color: "#f5f0e8", fontSize: "11px", fontFamily: "IBM Plex Mono, monospace", cursor: "pointer",
                }}
              >
                <Download size={12} /> Análisis interno (.md)
              </button>
              <button
                type="button"
                onClick={() => downloadMd(`/pro/cases/${caseId}/download/phenomenon-discovery`, "descubrimiento.md")}
                style={{
                  display: "inline-flex", alignItems: "center", gap: "6px",
                  padding: "8px 12px", background: "rgba(255,255,255,0.12)", border: "1px solid rgba(255,255,255,0.2)",
                  borderRadius: "2px", color: "#f5f0e8", fontSize: "11px", fontFamily: "IBM Plex Mono, monospace", cursor: "pointer",
                }}
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
