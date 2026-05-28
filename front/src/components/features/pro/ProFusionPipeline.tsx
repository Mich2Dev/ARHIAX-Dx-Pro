"use client";

import { useState } from "react";
import { CheckCircle, Circle, Loader2, XCircle, ChevronDown, ChevronUp, Wifi, WifiOff } from "lucide-react";

const TOOL_META: Record<string, { label: string; description: string; phase: string }> = {
  g10a_scoring:     { label: "Matrices de scoring",           phase: "Análisis",  description: "Calcula scores en 6 capas: por pregunta, dimensión, rol, compuesto, percentil y delta_sigma." },
  g10b_psicometria: { label: "Análisis psicométrico",         phase: "Análisis",  description: "Calcula Alpha de Cronbach por dimensión y evalúa validez convergente/discriminante." },
  g11a_bayesiano:   { label: "Análisis Bayesiano",            phase: "Análisis",  description: "Actualiza probabilidades de las hipótesis con la evidencia del scoring. Confirma/rechaza." },
  g11b_nlp:         { label: "Análisis de texto libre",       phase: "Análisis",  description: "Analiza respuestas abiertas: temas, sentimiento por rol y problemas ocultos." },
  irr_calculator:   { label: "Confiabilidad inter-evaluador", phase: "Análisis",  description: "Calcula Krippendorff Alpha entre los roles. Mínimo aceptable: α = 0.70." },
  scoring_engine:   { label: "Motor de normalización",        phase: "Análisis",  description: "Normaliza y agrega scores finales para el informe ejecutivo." },
  g12_hallazgos:    { label: "Consolidación de hallazgos",    phase: "Síntesis",  description: "Consolida toda la evidencia en una FindingsMatrix priorizada por impacto × confianza bayesiana." },
  g13_redactor:     { label: "Redacción ejecutiva",           phase: "Reporte",   description: "Redacta el informe completo para C-suite: resumen, hallazgos, recomendaciones y roadmap." },
  g14_qa_control:   { label: "Control de calidad (QA)",       phase: "Reporte",   description: "Evalúa el informe en 5 dimensiones. Score mínimo para aprobar: 85/100." },
};

// Orden esperado de agentes — para mostrar los pendientes aunque aún no existan en DB
const PIPELINE_ORDER = [
  "g10a_scoring","g10b_psicometria","g11a_bayesiano","g11b_nlp",
  "irr_calculator","scoring_engine","g12_hallazgos","g13_redactor","g14_qa_control",
];

const PHASE_COLORS: Record<string, { bg: string; text: string }> = {
  "Análisis": { bg: "rgba(155,109,77,0.1)", text: "#9b6d4d" },
  "Síntesis": { bg: "rgba(139,58,58,0.1)",  text: "#8b3a3a" },
  "Reporte":  { bg: "rgba(86,98,75,0.1)",   text: "#56624b" },
};

function getSnippet(toolName: string, output: any): string | null {
  if (!output || typeof output !== "object") return null;
  const raw = output.output ?? output;
  switch (toolName) {
    case "g10a_scoring": {
      const overall = raw.scoring_summary?.overall_score ?? raw.overall_score;
      const delta = raw.delta_sigma?.max_gap;
      return overall != null ? `Score: ${overall}/100${delta != null ? ` · δσ = ${delta}` : ""}` : null;
    }
    case "g10b_psicometria":
      return raw.cronbach_alpha_overall != null ? `α Cronbach = ${raw.cronbach_alpha_overall}` : null;
    case "g11a_bayesiano": {
      const c = raw.confirmed_hypotheses?.length ?? 0;
      const r = raw.rejected_hypotheses?.length ?? 0;
      return `${c} hipótesis confirmadas · ${r} rechazadas`;
    }
    case "irr_calculator":
      return raw.krippendorff_alpha != null ? `α Krippendorff = ${raw.krippendorff_alpha} · ${raw.irr_status ?? ""}` : null;
    case "g12_hallazgos": {
      const critical = raw.findings_matrix?.filter((f: any) => f.priority === "CRITICA").length ?? 0;
      const total = raw.findings_matrix?.length ?? 0;
      return total > 0 ? `${total} hallazgos · ${critical} críticos` : null;
    }
    case "g14_qa_control":
      return raw.qa_score != null ? `QA: ${raw.qa_score}/100 · ${raw.approved_for_rendering ? "Aprobado" : "Requiere revisión"}` : null;
    default:
      return null;
  }
}

function StageRow({ stage }: { stage: any }) {
  const [open, setOpen] = useState(false);
  const meta = TOOL_META[stage.tool_name] ?? { label: stage.tool_name, description: "", phase: "" };
  const snippet = stage.status === "completed" ? getSnippet(stage.tool_name, stage.output) : null;
  const isRunning = stage.status === "running";
  const isPending = stage.status === "pending" || !stage.status;
  const isFailed  = stage.status === "failed";
  const phaseStyle = PHASE_COLORS[meta.phase] ?? { bg: "rgba(23,23,23,0.06)", text: "#706f69" };

  return (
    <div style={{ background: isRunning ? "rgba(36,60,79,0.04)" : "transparent", borderLeft: isRunning ? "2px solid #243c4f" : "2px solid transparent" }}>
      <button
        onClick={() => (meta.description || snippet) && setOpen(o => !o)}
        style={{
          width: "100%", display: "flex", alignItems: "center", gap: "12px",
          padding: "10px 12px", textAlign: "left",
          cursor: (meta.description || snippet) ? "pointer" : "default",
          background: "transparent", border: "none",
        }}
      >
        {stage.status === "completed"
          ? <CheckCircle size={15} style={{ color: "#56624b", flexShrink: 0 }} />
          : isRunning
          ? <Loader2 size={15} style={{ color: "#243c4f", flexShrink: 0, animation: "spin 1s linear infinite" }} />
          : isFailed
          ? <XCircle size={15} style={{ color: "#8b3a3a", flexShrink: 0 }} />
          : <Circle size={15} style={{ color: "rgba(23,23,23,0.15)", flexShrink: 0 }} />
        }

        <span style={{
          flex: 1, fontSize: "13px",
          color: isRunning ? "#243c4f" : stage.status === "completed" ? "#171717" : isFailed ? "#8b3a3a" : "#c0bdb6",
          fontWeight: isRunning || stage.status === "completed" ? 500 : 400,
        }}>
          {meta.label}
        </span>

        {meta.phase && !isPending && (
          <span style={{
            fontSize: "10px", fontFamily: "IBM Plex Mono, monospace", fontWeight: 500,
            padding: "2px 6px", flexShrink: 0,
            background: phaseStyle.bg, color: phaseStyle.text,
          }}>
            {meta.phase}
          </span>
        )}

        <div style={{ display: "flex", gap: "8px", fontSize: "11px", color: "#c0bdb6", flexShrink: 0, fontFamily: "IBM Plex Mono, monospace" }}>
          {stage.tokens_used && <span>{stage.tokens_used.toLocaleString()} tok</span>}
          {stage.latency_ms && <span>{(stage.latency_ms / 1000).toFixed(1)}s</span>}
        </div>

        {(meta.description || snippet) && !isPending && (
          open
            ? <ChevronUp size={12} style={{ color: "rgba(23,23,23,0.3)", flexShrink: 0 }} />
            : <ChevronDown size={12} style={{ color: "rgba(23,23,23,0.3)", flexShrink: 0 }} />
        )}
      </button>

      {open && (
        <div style={{ padding: "0 12px 12px 40px", display: "grid", gap: "6px" }}>
          {meta.description && (
            <p style={{ margin: 0, fontSize: "12px", color: "#706f69", lineHeight: 1.5 }}>{meta.description}</p>
          )}
          {snippet && (
            <p style={{ margin: 0, fontSize: "12px", fontWeight: 500, color: "#56624b", fontFamily: "IBM Plex Mono, monospace" }}>{snippet}</p>
          )}
          {stage.model_used && (
            <p style={{ margin: 0, fontSize: "10px", color: "#c0bdb6", fontFamily: "IBM Plex Mono, monospace" }}>Modelo: {stage.model_used}</p>
          )}
          {stage.output && (
            <div style={{ marginTop: "8px", padding: "12px", background: "rgba(23,23,23,0.03)", border: "1px solid rgba(23,23,23,0.06)" }}>
              <p style={{ margin: "0 0 8px", fontSize: "10px", fontFamily: "IBM Plex Mono, monospace", color: "#9b6d4d", fontWeight: 600 }}>OUTPUT DATA & REASONING</p>
              <pre style={{ margin: 0, fontSize: "11px", color: "#171717", whiteSpace: "pre-wrap", overflowX: "auto", fontFamily: "IBM Plex Mono, monospace" }}>
                {JSON.stringify(stage.output, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function ProFusionPipeline({ caseData, isFetching }: { caseData: any; isFetching?: boolean }) {
  // ── Normalizar stages — el backend puede devolverlos como pipeline_stages o stages
  const rawStages: any[] = caseData.pipeline_stages || caseData.stages || [];
  const isRunning = caseData.case_status === "running";

  // Construir lista completa: stages reales + pendientes proyectados
  const stageMap = new Map(rawStages.map((s: any) => [s.tool_name, s]));
  const allStages = PIPELINE_ORDER.map(toolName => stageMap.get(toolName) ?? {
    tool_name: toolName,
    status: "pending",
    tokens_used: null,
    latency_ms: null,
    output: null,
    model_used: null,
  });

  const completed = allStages.filter(s => s.status === "completed").length;
  const pct = Math.round((completed / allStages.length) * 100);
  const currentStage = allStages.find(s => s.status === "running");
  const nextPending  = allStages.find(s => s.status === "pending");
  const activeAgent  = currentStage ?? nextPending;

  return (
    <div style={{ background: "rgba(244,241,234,0.96)", border: "1px solid rgba(23,23,23,0.14)", padding: "24px" }}>

      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px" }}>
        <h3 style={{ margin: 0, fontSize: "12px", fontFamily: "IBM Plex Mono, monospace", fontWeight: 500, color: "#222522", letterSpacing: "0.05em" }}>
          PIPELINE DIAGNÓSTICO · GEMINI
        </h3>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          {isFetching && isRunning && (
            <span style={{ fontSize: "10px", fontFamily: "IBM Plex Mono, monospace", color: "#56624b", display: "flex", alignItems: "center", gap: "4px" }}>
              <Wifi size={10} /> sincronizando
            </span>
          )}
          <span style={{ fontSize: "11px", fontFamily: "IBM Plex Mono, monospace", color: "#706f69" }}>
            {completed}/{allStages.length} módulos
          </span>
        </div>
      </div>

      {/* Barra de progreso */}
      <div style={{ width: "100%", height: "6px", background: "rgba(23,23,23,0.08)", marginBottom: "20px", position: "relative", overflow: "hidden" }}>
        <div style={{
          height: "6px", background: isRunning ? "#243c4f" : "#56624b",
          width: `${pct}%`, transition: "width 0.7s",
        }} />
        {isRunning && (
          <div style={{
            position: "absolute", top: 0, left: `${pct}%`, height: "6px", width: "40px",
            background: "linear-gradient(90deg, rgba(36,60,79,0.4), transparent)",
            animation: "pulse 1.5s ease-in-out infinite",
          }} />
        )}
      </div>

      {/* Banner agente activo */}
      {isRunning && (
        <div style={{
          display: "flex", alignItems: "flex-start", gap: "12px",
          padding: "14px 16px", marginBottom: "16px",
          background: "rgba(36,60,79,0.07)", border: "1px solid rgba(36,60,79,0.2)",
          borderLeft: "3px solid #243c4f",
        }}>
          <Loader2 size={16} style={{ color: "#243c4f", animation: "spin 1s linear infinite", flexShrink: 0, marginTop: "2px" }} />
          <div style={{ flex: 1 }}>
            <p style={{ margin: 0, fontSize: "11px", fontFamily: "IBM Plex Mono, monospace", color: "#706f69", fontWeight: 600, letterSpacing: "0.08em", marginBottom: "4px" }}>
              AGENTE EN EJECUCIÓN
            </p>
            <p style={{ margin: 0, fontSize: "14px", fontWeight: 600, color: "#243c4f" }}>
              {activeAgent ? (TOOL_META[activeAgent.tool_name]?.label ?? activeAgent.tool_name) : "Preparando siguiente etapa..."}
            </p>
            {activeAgent && TOOL_META[activeAgent.tool_name]?.description && (
              <p style={{ margin: "4px 0 0", fontSize: "12px", color: "#706f69", lineHeight: 1.4 }}>
                {TOOL_META[activeAgent.tool_name].description}
              </p>
            )}
            <p style={{ margin: "8px 0 0", fontSize: "11px", color: "#9b6d4d", fontFamily: "IBM Plex Mono, monospace" }}>
              {completed} de {allStages.length} completados · {100 - pct}% restante
            </p>
            <p style={{ margin: "4px 0 0", fontSize: "10px", color: "#c0bdb6", fontFamily: "IBM Plex Mono, monospace" }}>
              El servidor está procesando con Gemini. La pantalla se actualiza automáticamente cada 5s.
            </p>
          </div>
        </div>
      )}

      {/* Lista de agentes */}
      <div style={{ display: "grid", gap: "1px", background: "rgba(23,23,23,0.06)", maxHeight: "360px", overflowY: "auto" }}>
        {allStages.map((stage: any) => (
          <div key={stage.tool_name} style={{ background: "rgba(244,241,234,0.96)" }}>
            <StageRow stage={stage} />
          </div>
        ))}
      </div>

      <p style={{ margin: "12px 0 0", fontSize: "10px", color: "rgba(23,23,23,0.3)", textAlign: "center", fontFamily: "IBM Plex Mono, monospace" }}>
        Haz clic en un módulo completado para ver su razonamiento
      </p>
    </div>
  );
}
