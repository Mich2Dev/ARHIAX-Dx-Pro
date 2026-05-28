"use client";

import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { CheckCircle, Circle, Loader2, XCircle, ChevronDown, ChevronUp } from "lucide-react";
import type { PipelineStage } from "@/lib/types";

// ── Agent metadata ────────────────────────────────────────────────────────────
const TOOL_META: Record<string, { label: string; description: string; phase: string }> = {
  g01_receptor:       { label: "Recepción del mandato",        phase: "Intake",        description: "Parsea el mandato del cliente, valida coherencia y clasifica el tipo de diagnóstico." },
  g02_configurador:   { label: "Configuración del dominio",    phase: "Intake",        description: "Define el marco de referencia, benchmarks del sector y los 3 roles para la encuesta." },
  g03_cienciometro:   { label: "Revisión de literatura",       phase: "Investigación", description: "Mapea evidencia académica relevante (Semantic Scholar, OpenAlex) para el subproceso." },
  academic_search:    { label: "Búsqueda académica",           phase: "Investigación", description: "Busca artículos y estudios científicos relacionados con el problema." },
  web_search:         { label: "Búsqueda web sectorial",       phase: "Investigación", description: "Obtiene benchmarks, tendencias y contexto regulatorio del sector en Latam." },
  g04_cartografo:     { label: "Mapa de procesos",             phase: "Mapeo",         description: "Mapea la praxis empresarial: casos reales, mejores prácticas y proceso estándar del sector." },
  g05_brechas:        { label: "Análisis de brechas",          phase: "Mapeo",         description: "Detecta brechas AS-IS vs benchmark y genera hipótesis diagnósticas priorizadas." },
  g06_bpmn_architect: { label: "Arquitectura BPMN (AS-IS)",    phase: "Diseño",        description: "Diseña el proceso actual con 15-20 actividades, actores, gateways y cuellos visibles." },
  g07_cuellos:        { label: "Cuantificación de cuellos",    phase: "Diseño",        description: "Cuantifica cada cuello de botella: horas perdidas/mes y costo de oportunidad en USD." },
  g08_optimizador:    { label: "Opciones de mejora (TO-BE)",   phase: "Diseño",        description: "Diseña 2-3 opciones de mejora con ROI, payback y análisis de sensibilidad." },
  bpmn_generator:     { label: "Generador de diagramas BPMN",  phase: "Diseño",        description: "Genera el XML BPMN 2.0 del proceso para renderizado en Camunda/Bizagi." },
  g09a_preguntas:     { label: "Banco de preguntas",           phase: "Encuesta",      description: "Diseña 15 preguntas Likert + 3 abiertas específicas al subproceso, mapeadas a las brechas de G05." },
  g09b_ramificacion:  { label: "Lógica de ramificación",       phase: "Encuesta",      description: "Define qué preguntas ve cada rol (Estratégico/Táctico/Operativo) y la lógica de salto." },
  g09c_validacion:    { label: "Validación de encuesta",       phase: "Encuesta",      description: "Calcula IRR estimado (α Krippendorff), valida cobertura por dimensión y emite veredicto." },
  g10a_scoring:       { label: "Matrices de scoring",          phase: "Análisis",      description: "Calcula scores en 6 capas: por pregunta, dimensión, rol, compuesto, percentil y delta_sigma." },
  g10b_psicometria:   { label: "Análisis psicométrico",        phase: "Análisis",      description: "Calcula Alpha de Cronbach por dimensión y evalúa validez convergente/discriminante." },
  g11a_bayesiano:     { label: "Análisis Bayesiano",           phase: "Análisis",      description: "Actualiza probabilidades de las hipótesis de G05 con la evidencia del scoring. Confirma/rechaza." },
  g11b_nlp:           { label: "Análisis de texto libre",      phase: "Análisis",      description: "Analiza respuestas abiertas: temas, sentimiento por rol y problemas ocultos no capturados en scoring." },
  irr_calculator:     { label: "Confiabilidad inter-evaluador",phase: "Análisis",      description: "Calcula Krippendorff Alpha entre los 3 roles. Mínimo aceptable: α = 0.70." },
  scoring_engine:     { label: "Motor de normalización",       phase: "Análisis",      description: "Normaliza y agrega scores finales para el informe ejecutivo." },
  g12_hallazgos:      { label: "Consolidación de hallazgos",   phase: "Síntesis",      description: "Consolida toda la evidencia en una FindingsMatrix priorizada por impacto × confianza bayesiana." },
  g13_redactor:       { label: "Redacción ejecutiva",          phase: "Reporte",       description: "Redacta el informe completo para C-suite: resumen, hallazgos, recomendaciones y roadmap 90/180/365." },
  g14_qa_control:     { label: "Control de calidad (QA)",      phase: "Reporte",       description: "Evalúa el informe en 5 dimensiones (0-20 c/u). Score mínimo para aprobar: 85/100." },
  docx_generator:     { label: "Generación del reporte Word",  phase: "Reporte",       description: "Estructura el contenido final para el documento Word ejecutivo descargable." },
};

// ── Extract key output snippet per tool ──────────────────────────────────────
function getOutputSnippet(toolName: string, stage: any): string | null {
  const raw = stage.output?.output ?? stage.output;
  if (!raw || typeof raw !== "object") return null;

  switch (toolName) {
    case "g01_receptor":
      return raw.mandate_confirmed === false
        ? `❌ Rechazado: ${raw.rejection_reason}`
        : `✓ ${raw.diagnostic_type ?? "proceso"} · Urgencia: ${raw.urgency ?? "—"}`;
    case "g02_configurador":
      return raw.frameworks?.length
        ? `Marcos: ${raw.frameworks.slice(0, 3).join(", ")}`
        : null;
    case "g05_brechas": {
      const h = raw.hypotheses?.length ?? 0;
      const g = raw.gaps?.length ?? 0;
      return `${g} brechas · ${h} hipótesis`;
    }
    case "g07_cuellos":
      return raw.total_opportunity_loss_usd_month
        ? `Pérdida total: USD ${raw.total_opportunity_loss_usd_month}/mes`
        : raw.bottlenecks?.length ? `${raw.bottlenecks.length} cuellos identificados` : null;
    case "g09a_preguntas": {
      const q = raw.questions?.length ?? 0;
      const dims = raw.dimensions?.length ?? 0;
      return q > 0 ? `${q} preguntas · ${dims} dimensiones` : null;
    }
    case "g09c_validacion":
      return raw.irr_alpha_estimated != null
        ? `IRR α = ${raw.irr_alpha_estimated} · ${raw.irr_status ?? "—"}`
        : null;
    case "g10a_scoring": {
      const overall = raw.scoring_summary?.overall_score;
      const delta = raw.delta_sigma?.max_gap;
      return overall != null ? `Score: ${overall}/100 · δσ = ${delta ?? "—"}` : null;
    }
    case "g11a_bayesiano": {
      const confirmed = raw.confirmed_hypotheses?.length ?? 0;
      const rejected  = raw.rejected_hypotheses?.length ?? 0;
      return `${confirmed} hipótesis confirmadas · ${rejected} rechazadas`;
    }
    case "g12_hallazgos": {
      const critical = raw.findings_matrix?.filter((f: any) => f.priority === "CRITICA").length ?? 0;
      const total    = raw.findings_matrix?.length ?? 0;
      return total > 0 ? `${total} hallazgos · ${critical} críticos` : null;
    }
    case "g14_qa_control":
      return raw.qa_score != null
        ? `QA: ${raw.qa_score}/100 · ${raw.approved_for_rendering ? "✓ Aprobado" : "✗ Requiere revisión"}`
        : null;
    default:
      return null;
  }
}

// ── Phase color ───────────────────────────────────────────────────────────────
const PHASE_COLORS: Record<string, string> = {
  "Intake":        "bg-gray-100 text-gray-500",
  "Investigación": "bg-blue-50 text-blue-500",
  "Mapeo":         "bg-indigo-50 text-indigo-500",
  "Diseño":        "bg-purple-50 text-purple-500",
  "Encuesta":      "bg-brand-50 text-brand-600",
  "Análisis":      "bg-amber-50 text-amber-600",
  "Síntesis":      "bg-orange-50 text-orange-600",
  "Reporte":       "bg-green-50 text-green-600",
};

const StatusIcon = ({ status }: { status: string }) => {
  if (status === "completed") return <CheckCircle size={15} className="text-green-500 shrink-0" />;
  if (status === "running")   return <Loader2    size={15} className="text-blue-500 shrink-0 animate-spin" />;
  if (status === "failed")    return <XCircle    size={15} className="text-red-500 shrink-0" />;
  return <Circle size={15} className="text-gray-200 shrink-0" />;
};

// ── Stage row ─────────────────────────────────────────────────────────────────
function StageRow({ stage }: { stage: any }) {
  const [open, setOpen] = useState(false);
  const meta    = TOOL_META[stage.tool_name];
  const label   = meta?.label ?? stage.tool_name;
  const desc    = meta?.description ?? "";
  const phase   = meta?.phase ?? "";
  const snippet = stage.status === "completed" ? getOutputSnippet(stage.tool_name, stage) : null;
  const isRunning = stage.status === "running";

  return (
    <div className={`rounded-lg transition-colors ${isRunning ? "bg-blue-50" : ""}`}>
      <button
        onClick={() => (desc || snippet) && setOpen(o => !o)}
        className={`w-full flex items-center gap-3 px-3 py-2 text-left ${(desc || snippet) ? "cursor-pointer" : "cursor-default"}`}
      >
        <StatusIcon status={stage.status} />

        <span className={`flex-1 text-sm ${
          isRunning                    ? "font-semibold text-blue-800" :
          stage.status === "completed" ? "text-gray-700" :
          stage.status === "failed"    ? "text-red-600" :
                                         "text-gray-400"
        }`}>
          {label}
        </span>

        {/* Phase badge */}
        {phase && stage.status !== "pending" && (
          <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full shrink-0 ${PHASE_COLORS[phase] ?? "bg-gray-100 text-gray-400"}`}>
            {phase}
          </span>
        )}

        {/* Metrics */}
        <div className="flex items-center gap-2 text-xs text-gray-400 shrink-0">
          {stage.tokens_used  && <span>{stage.tokens_used.toLocaleString()} tok</span>}
          {stage.latency_ms   && <span>{(stage.latency_ms / 1000).toFixed(1)}s</span>}
        </div>

        {/* Expand icon */}
        {(desc || snippet) && stage.status !== "pending" && (
          open
            ? <ChevronUp size={13} className="text-gray-300 shrink-0" />
            : <ChevronDown size={13} className="text-gray-300 shrink-0" />
        )}
      </button>

      {/* Expanded detail */}
      {open && (
        <div className="px-10 pb-3 space-y-1.5">
          {desc && (
            <p className="text-xs text-gray-500 leading-relaxed">{desc}</p>
          )}
          {snippet && (
            <p className={`text-xs font-semibold ${
              snippet.startsWith("❌") ? "text-red-600" : "text-brand-600"
            }`}>
              {snippet}
            </p>
          )}
          {stage.model_used && (
            <p className="text-[10px] text-gray-400">Modelo: {stage.model_used}</p>
          )}
        </div>
      )}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
export function PipelineProgress({
  stages,
  diagnosticId,
  status,
}: {
  stages: PipelineStage[];
  diagnosticId: string;
  status: string;
}) {
  const qc    = useQueryClient();
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (status !== "running" && status !== "pending") return;
    const wsUrl = `${process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000"}/v2/diagnostics/${diagnosticId}/stream`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;
    ws.onmessage = () => qc.invalidateQueries({ queryKey: ["diagnostic", diagnosticId] });
    return () => ws.close();
  }, [diagnosticId, status, qc]);

  const completed = stages.filter(s => s.status === "completed").length;
  const pct       = stages.length ? Math.round((completed / stages.length) * 100) : 0;
  const running   = stages.find(s => s.status === "running");

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-gray-800">Ejecución del pipeline</h3>
        <span className="text-sm font-bold text-gray-500">{completed}/{stages.length} módulos</span>
      </div>

      {/* Progress bar */}
      <div className="w-full bg-gray-100 rounded-full h-2">
        <div
          className="bg-brand-500 h-2 rounded-full transition-all duration-700"
          style={{ width: `${pct}%` }}
        />
      </div>

      {/* Current step callout */}
      {running && (
        <div className="bg-blue-50 rounded-xl px-4 py-2.5 flex items-center gap-2 text-sm">
          <Loader2 size={14} className="text-blue-500 animate-spin shrink-0" />
          <div className="flex-1 min-w-0">
            <span className="text-blue-700 font-medium">
              {TOOL_META[running.tool_name]?.label ?? running.tool_name}
            </span>
            {TOOL_META[running.tool_name]?.description && (
              <p className="text-xs text-blue-500 mt-0.5 truncate">
                {TOOL_META[running.tool_name].description}
              </p>
            )}
          </div>
          {running.model_used && (
            <span className="text-xs text-blue-400 shrink-0">{running.model_used}</span>
          )}
        </div>
      )}

      {/* Stage list */}
      <div
        className="space-y-0.5 max-h-80 overflow-y-auto pr-1"
        style={{ scrollbarWidth: "thin", scrollbarColor: "#e5e7eb transparent" }}
      >
        {stages.map((stage) => (
          <StageRow key={stage.id} stage={stage} />
        ))}
      </div>

      <p className="text-[10px] text-gray-400 text-center">
        Haz clic en un módulo completado para ver qué produjo
      </p>
    </div>
  );
}
