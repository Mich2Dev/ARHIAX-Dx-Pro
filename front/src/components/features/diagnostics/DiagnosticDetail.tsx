"use client";

import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { api } from "@/lib/api";
import { Spinner } from "@/components/ui/Spinner";
import { Badge } from "@/components/ui/Badge";
import { GovernancePanel } from "./GovernancePanel";
import { PipelineProgress } from "./PipelineProgress";
import { ResultsPanel } from "./ResultsPanel";
import { SurveyProgress } from "./SurveyProgress";
import { SurveyAuditPanel } from "./SurveyAuditPanel";
import { Autonometer, BBRLive } from "./NCReportPanel";
import { ExecuteProButton } from "./ExecuteProButton";
import { decisionVariant, statusVariant, formatDate } from "@/lib/utils";
import { Clock, Users, Building2, AlertCircle } from "lucide-react";

export function DiagnosticDetail({ id }: { id: string }) {
  const t = useTranslations();

  const { data, isLoading } = useQuery({
    queryKey: ["diagnostic", id],
    queryFn: () => api.get(`/v2/diagnostics/${id}`).then((r) => r.data),
    refetchInterval: (q) => {
      const s = q.state.data?.status;
      return s === "running" || s === "pending" || s === "awaiting_responses" ? 5000 : false;
    },
  });

  if (isLoading) return <div className="flex justify-center py-20"><Spinner /></div>;
  if (!data) return null;

  const isDone      = data.status === "completed";
  const isRunning   = data.status === "running" || data.status === "pending";
  const isEscalated = data.status === "awaiting_review";
  const isDenied    = data.status === "denied" || data.status === "failed";
  const isWaiting   = data.status === "awaiting_responses";

  const hasStages     = (data.stages?.length ?? 0) > 0;
  const hasGovernance = (data.rule_results?.length ?? 0) > 0;

  // Show results if completed OR if awaiting_review with g14 completed (report is ready)
  const hasCompletedReport = data.stages?.some((s: any) => s.tool_name === "g14_qa_control" && s.status === "completed");
  const showResults = isDone || (isEscalated && hasCompletedReport);

  // Always show sidebar if there's governance OR if there are stages (to show autonometer)
  const showSidebar = hasGovernance || hasStages || showResults;

  return (
    <div className="max-w-7xl mx-auto space-y-5">

      {/* ── Header card ── */}
      <div className="bg-[#f4f1ea]/90 border-b border-[#171717]/10 pb-6 mb-8">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <p className="text-xs font-mono text-[#56624b] mb-2">§ caso · {data.request_id?.slice(0, 8) ?? id}</p>
            <h1 className="text-4xl font-serif text-[#171717] leading-none mb-3">
              {data.organization_name}
            </h1>
            <div className="flex items-center gap-3 flex-wrap">
              <span className="inline-flex items-center gap-2 px-2.5 py-1 text-[11px] font-mono font-medium border border-[#171717]/20 text-[#171717] bg-[#171717]/5">
                {isRunning && <Spinner className="w-3 h-3 border-[#171717] border-t-transparent" />}
                {t(`diagnostic.status.${data.status}` as any).toUpperCase()}
              </span>
              {data.decision && (
                <span className="text-[11px] font-mono font-medium text-[#706f69]">
                  {t(`diagnostic.decision.${data.decision}` as any).toUpperCase()}
                </span>
              )}
              <span className="text-xs text-[#706f69]">{data.domain} · {data.subprocess}</span>
            </div>
            {data.objective && (
              <p className="text-sm text-[#222522] mt-4 leading-relaxed max-w-3xl">
                {data.objective}
              </p>
            )}
          </div>
        </div>

        {/* Meta row */}
        <div className="flex flex-wrap gap-4 mt-6 pt-4 border-t border-[#171717]/10 text-[11px] font-mono text-[#706f69]">
          <span className="flex items-center gap-2">
            <Clock size={12} /> Creado: {formatDate(data.created_at)}
          </span>
          {data.completed_at && (
            <span className="flex items-center gap-2">
              <Clock size={12} /> Completado: {formatDate(data.completed_at)}
            </span>
          )}
          {data.size_org && (
            <span className="flex items-center gap-2">
              <Users size={12} /> {data.size_org} empleados
            </span>
          )}
        </div>
      </div>

      {/* ── Execute with Pro button ── */}
      {isWaiting && data.survey && (
        <div className="bg-[#171717] p-5 flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-[#f4f1ea]">¿Ejecutar con motor Pro?</p>
            <p className="text-xs text-white/50 mt-1 font-mono">
              Usa el fusion cycle avanzado con gobernanza PMEL/ATK y evidence ledger HMAC
            </p>
          </div>
          <ExecuteProButton diagnosticId={id} />
        </div>
      )}

      {/* ── Status banners ── */}
      {isRunning && (
        <div className="bg-[#243c4f]/5 border border-[#243c4f]/30 border-l-[3px] border-l-[#243c4f] p-4 flex items-center gap-3">
          <Spinner className="w-5 h-5 border-[#243c4f] border-t-transparent shrink-0" />
          <div>
            <p className="text-[13px] font-medium text-[#243c4f]">Diagnóstico en ejecución</p>
            <p className="text-xs text-[#706f69] mt-1">
              El agente está procesando los módulos. Esta pantalla se actualiza automáticamente.
            </p>
          </div>
        </div>
      )}

      {isDenied && (
        <div className="bg-[#8b3a3a]/5 border border-[#8b3a3a]/30 border-l-[3px] border-l-[#8b3a3a] p-4">
          <div className="flex items-center gap-2 mb-2">
            <AlertCircle size={16} className="text-[#8b3a3a] shrink-0" />
            <p className="text-[13px] font-medium text-[#8b3a3a]">Diagnóstico denegado</p>
          </div>
          {data.rule_results?.filter((r: any) => r.outcome === "FAIL").map((r: any) => (
            <p key={r.rule_id} className="text-xs text-[#8b3a3a] mt-1 ml-6">· {r.message}</p>
          ))}
        </div>
      )}

      {isEscalated && (
        <div className="bg-[#9b6d4d]/5 border border-[#9b6d4d]/30 border-l-[3px] border-l-[#9b6d4d] p-4 flex items-start justify-between gap-4">
          <div>
            <p className="text-[13px] font-medium text-[#9b6d4d]">Esperando aprobación humana</p>
            <p className="text-xs text-[#706f69] mt-1">
              El diagnóstico completó su análisis y está en cola de revisión.
              Un revisor debe aprobar el reporte antes de entregarlo al cliente.
            </p>
          </div>
          <Link
            href="/dashboard/reviews"
            className="shrink-0 text-[11px] font-mono text-[#9b6d4d] border border-[#9b6d4d]/30 px-3 py-2 hover:bg-[#9b6d4d]/10 transition-colors whitespace-nowrap"
          >
            Ir a revisiones →
          </Link>
        </div>
      )}

      {isWaiting && (
        <div className="bg-[#56624b]/5 border border-[#56624b]/30 border-l-[3px] border-l-[#56624b] p-4 flex items-center gap-3">
          <div className="w-2 h-2 rounded-full bg-[#56624b] animate-pulse shrink-0" />
          <div>
            <p className="text-[13px] font-medium text-[#56624b]">Encuesta en curso</p>
            <p className="text-xs text-[#706f69] mt-1">
              Los empleados están respondiendo. Las gráficas se actualizan en tiempo real.
            </p>
          </div>
        </div>
      )}

      {/* ── Main layout ── */}
      <div className="flex flex-col lg:flex-row gap-5 items-start w-full">

        {/* ── LEFT SIDEBAR ── */}
        {showSidebar && (
          <div className="w-full lg:w-72 shrink-0 lg:sticky lg:top-4 space-y-4">
            {hasGovernance && (
              <GovernancePanel rules={data.rule_results} decision={data.decision} />
            )}
            <Autonometer level={data.autonomy_level ?? "A1"} />
            {/* BBR solo cuando está corriendo — en completed ya aparece en ResultsPanel */}
            {hasStages && isRunning && (
              <BBRLive stages={data.stages} />
            )}
          </div>
        )}

        {/* ── RIGHT MAIN CONTENT ── */}
        <div className="flex-1 w-full min-w-0 space-y-5">

          {/* Pipeline progress */}
          {hasStages && (
            <PipelineProgress
              stages={data.stages}
              diagnosticId={id}
              status={data.status}
            />
          )}

          {/* Survey progress */}
          {isWaiting && data.survey && (
            <SurveyProgress diagnosticId={id} />
          )}

          {/* Results */}
          {showResults && <ResultsPanel diagnostic={{...data, status: "completed"}} />}

          {/* Survey audit */}
          {showResults && data.survey?.token && (
            <SurveyAuditPanel surveyToken={data.survey.token} />
          )}

          {/* Escalated without report */}
          {isEscalated && !hasCompletedReport && hasStages && (
            <EscalatedPreview stages={data.stages} />
          )}

          {/* Empty state */}
          {!hasStages && !showResults && !isRunning && (
            <div className="bg-white rounded-2xl border border-gray-200 p-10 text-center">
              <p className="text-gray-400 text-sm">
                {isEscalated
                  ? "Este diagnóstico fue escalado a revisión humana antes de ejecutar el pipeline."
                  : isDenied
                  ? "El diagnóstico fue denegado por las reglas de gobernanza."
                  : "No hay módulos ejecutados aún."}
              </p>
            </div>
          )}

          {!showSidebar && <Autonometer level={data.autonomy_level ?? "A1"} />}
        </div>
      </div>
    </div>
  );
}

// ── Preview of key outputs when escalated ────────────────────────────────────
function EscalatedPreview({ stages }: { stages: any[] }) {
  const completed = stages.filter(s => s.status === "completed");
  if (completed.length === 0) return null;

  // Extract key outputs
  const g13 = completed.find(s => s.tool_name === "g13_redactor");
  const g12 = completed.find(s => s.tool_name === "g12_hallazgos");
  const g14 = completed.find(s => s.tool_name === "g14_qa_control");

  const summary   = g13?.output?.output?.executive_summary ?? g13?.output?.executive_summary;
  const findings  = g12?.output?.output?.findings_matrix   ?? g12?.output?.findings_matrix ?? [];
  const qaScore   = g14?.output?.output?.qa_score          ?? g14?.output?.qa_score;

  if (!summary && findings.length === 0) return null;

  return (
    <div className="space-y-4">
      {qaScore != null && (
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-4 flex items-center gap-4">
          <div className={`text-3xl font-black ${qaScore >= 85 ? "text-green-600" : "text-orange-500"}`}>
            {qaScore}<span className="text-base font-normal text-gray-400">/100</span>
          </div>
          <div>
            <p className="text-sm font-semibold text-gray-800">Control de Calidad (QA)</p>
            <p className="text-xs text-gray-500">
              {qaScore >= 85 ? "✓ Aprobado — listo para revisión humana" : "⚠ Por debajo del umbral mínimo (85)"}
            </p>
          </div>
        </div>
      )}

      {summary && (
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5">
          <p className="text-sm font-semibold text-gray-800 mb-2">Resumen Ejecutivo</p>
          <p className="text-sm text-gray-600 leading-relaxed">{summary}</p>
        </div>
      )}

      {findings.length > 0 && (
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5">
          <p className="text-sm font-semibold text-gray-800 mb-3">
            Hallazgos principales ({findings.length})
          </p>
          <div className="space-y-2">
            {findings.slice(0, 4).map((f: any, i: number) => (
              <div key={i} className={`rounded-xl p-3 border text-sm ${
                f.priority === "CRITICA" ? "border-red-200 bg-red-50" :
                f.priority === "ALTA"    ? "border-orange-200 bg-orange-50" :
                                           "border-gray-100 bg-gray-50"
              }`}>
                <span className={`text-xs font-bold mr-2 ${
                  f.priority === "CRITICA" ? "text-red-600" :
                  f.priority === "ALTA"    ? "text-orange-600" : "text-gray-500"
                }`}>{f.priority}</span>
                {f.finding}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
