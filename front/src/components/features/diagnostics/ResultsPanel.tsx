"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Spinner } from "@/components/ui/Spinner";
import { Badge } from "@/components/ui/Badge";
import {
  Download, Shield, ChevronDown, ChevronUp,
  TrendingDown, Lightbulb, CheckCircle, AlertTriangle, Clock
} from "lucide-react";
import { NCReport, CryptoPanel } from "./NCReportPanel";
import { SurveyResultsChart } from "./SurveyResultsChart";

// Extrae el output real de Gemini de la estructura del stage
function extractOutput(stage: any): any {
  if (!stage?.output) return null;
  // Estructura: stage.output = { tool, model_used, tokens_used, output: {...} }
  if (stage.output.output && typeof stage.output.output === "object") {
    return stage.output.output;
  }
  // Fallback: el output directo
  return stage.output;
}

export function ResultsPanel({ diagnostic }: { diagnostic: any }) {
  const [showCert, setShowCert]   = useState(false);
  const [downloading, setDownloading] = useState(false);

  const { data: detail, isLoading } = useQuery({
    queryKey: ["diagnostic-detail-full", diagnostic.id],
    queryFn: () => api.get(`/v2/diagnostics/${diagnostic.id}`).then(r => r.data),
    enabled: diagnostic.status === "completed",
  });

  async function handleDownload() {
    setDownloading(true);
    try {
      const response = await api.get(
        `/v2/diagnostics/${diagnostic.id}/download-pdf`,
        { responseType: "blob" }
      );
      const url  = window.URL.createObjectURL(new Blob([response.data], { type: "application/pdf" }));
      const link = document.createElement("a");
      link.href  = url;
      link.setAttribute("download", `diagnostico_${diagnostic.organization_name}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      console.error("Download failed", e);
    } finally {
      setDownloading(false);
    }
  }

  if (isLoading) return <div className="flex justify-center py-8"><Spinner /></div>;

  const stages   = detail?.stages ?? [];
  const redactor  = extractOutput(stages.find((s: any) => s.tool_name === "g13_redactor"));
  const hallazgos = extractOutput(stages.find((s: any) => s.tool_name === "g12_hallazgos"));
  const qa        = extractOutput(stages.find((s: any) => s.tool_name === "g14_qa_control"));
  const cuellos   = extractOutput(stages.find((s: any) => s.tool_name === "g07_cuellos"));
  const brechas   = extractOutput(stages.find((s: any) => s.tool_name === "g05_brechas"));
  const cert      = diagnostic.certificate;

  // Tokens totales usados
  const totalTokens = stages.reduce((acc: number, s: any) => acc + (s.tokens_used ?? 0), 0);

  return (
    <div className="space-y-4">

      {/* ── Download + stats bar ── */}
      <div className="bg-gradient-to-r from-brand-500 to-brand-600 rounded-2xl p-5 flex items-center justify-between text-white">
        <div>
          <p className="font-bold text-lg">Diagnóstico completado</p>
          <p className="text-brand-100 text-sm mt-0.5">
            {stages.filter((s: any) => s.status === "completed").length} módulos ejecutados
            {totalTokens > 0 && ` · ${totalTokens.toLocaleString()} tokens Gemini`}
          </p>
        </div>
        <button
          onClick={handleDownload}
          disabled={downloading}
          className="flex items-center gap-2 bg-white text-brand-600 hover:bg-brand-50 px-5 py-2.5 rounded-xl text-sm font-bold transition-colors disabled:opacity-60 shrink-0"
        >
          {downloading ? <Spinner className="w-4 h-4 border-brand-500 border-t-brand-200" /> : <Download size={16} />}
          {downloading ? "Generando..." : "Descargar PDF"}
        </button>
      </div>

      {/* ── QA Score ── */}
      {qa && (
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-gray-800 flex items-center gap-2">
              <CheckCircle size={16} className="text-green-500" />
              Control de Calidad
            </h3>
            <div className={`text-3xl font-black ${
              (qa.qa_score ?? 0) >= 85 ? "text-green-600" : "text-orange-500"
            }`}>
              {qa.qa_score ?? "—"}<span className="text-base font-normal text-gray-400">/100</span>
            </div>
          </div>
          {qa.qa_notes && (
            <p className="text-sm text-gray-500 mt-2">{qa.qa_notes}</p>
          )}
          {qa.quality_dimensions && (
            <div className="grid grid-cols-5 gap-2 mt-3">
              {Object.entries(qa.quality_dimensions).map(([key, val]: [string, any]) => (
                <div key={key} className="text-center">
                  <div className={`text-lg font-bold ${
                    (val.score / val.max) >= 0.85 ? "text-green-600" : "text-orange-500"
                  }`}>{val.score}</div>
                  <div className="text-[10px] text-gray-400 leading-tight mt-0.5">
                    {key.replace(/_/g, " ")}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Resumen Ejecutivo ── */}
      {redactor?.executive_summary && (
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5">
          <h3 className="font-semibold text-gray-800 mb-3">Resumen Ejecutivo</h3>
          <p className="text-sm text-gray-700 leading-relaxed">{redactor.executive_summary}</p>
        </div>
      )}

      {/* ── Hallazgos ── */}
      {(hallazgos?.confirmed_findings?.length > 0 || hallazgos?.findings_matrix?.length > 0) && (
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5 space-y-4">
          <h3 className="font-semibold text-gray-800 flex items-center gap-2">
            <AlertTriangle size={16} className="text-orange-500" />
            Hallazgos Confirmados
          </h3>

          {/* findings_matrix */}
          {hallazgos.findings_matrix?.map((f: any, i: number) => (
            <div key={i} className={`rounded-xl p-3 border ${
              f.priority === "CRITICA" ? "border-red-200 bg-red-50" :
              f.priority === "ALTA"    ? "border-orange-200 bg-orange-50" :
                                         "border-gray-100 bg-gray-50"
            }`}>
              <div className="flex items-start gap-2">
                <Badge variant={
                  f.priority === "CRITICA" ? "red" :
                  f.priority === "ALTA"    ? "orange" : "gray"
                }>
                  {f.priority ?? "MEDIA"}
                </Badge>
                <p className="text-sm font-medium text-gray-800 flex-1">{f.finding}</p>
              </div>
              {f.evidence?.length > 0 && (
                <p className="text-xs text-gray-500 mt-1 ml-1">
                  Evidencia: {f.evidence.join(" · ")}
                </p>
              )}
            </div>
          ))}

          {/* confirmed_findings simple list */}
          {!hallazgos.findings_matrix && hallazgos.confirmed_findings?.map((f: string, i: number) => (
            <div key={i} className="flex gap-2 text-sm text-gray-700">
              <span className="text-brand-500 font-bold shrink-0">{i + 1}.</span>{f}
            </div>
          ))}
        </div>
      )}

      {/* ── Cuellos de Botella ── */}
      {cuellos?.bottlenecks?.length > 0 && (
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5">
          <h3 className="font-semibold text-gray-800 flex items-center gap-2 mb-3">
            <TrendingDown size={16} className="text-red-500" />
            Cuellos de Botella
            {cuellos.total_opportunity_loss_usd_month && (
              <span className="ml-auto text-sm font-normal text-red-600">
                Pérdida estimada: USD {cuellos.total_opportunity_loss_usd_month}/mes
              </span>
            )}
          </h3>
          <div className="space-y-2">
            {cuellos.bottlenecks.slice(0, 5).map((b: any, i: number) => (
              <div key={i} className="flex items-center gap-3 p-2 rounded-lg bg-gray-50">
                <Badge variant={
                  b.severity === "CRITICO" ? "red" :
                  b.severity === "ALTO"    ? "orange" : "gray"
                }>{b.severity}</Badge>
                <span className="text-sm font-medium text-gray-800 flex-1">{b.name}</span>
                {b.estimated_cost_usd_month && (
                  <span className="text-xs text-red-600 font-semibold">
                    USD {b.estimated_cost_usd_month}/mes
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Recomendaciones ── */}
      {(hallazgos?.strategic_recommendations?.length > 0 || redactor?.strategic_recommendations?.length > 0) && (
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5">
          <h3 className="font-semibold text-gray-800 flex items-center gap-2 mb-3">
            <Lightbulb size={16} className="text-yellow-500" />
            Recomendaciones Estratégicas
          </h3>
          <div className="space-y-3">
            {(hallazgos?.strategic_recommendations ?? redactor?.strategic_recommendations ?? [])
              .slice(0, 5)
              .map((r: any, i: number) => (
              <div key={i} className="flex gap-3 p-3 rounded-xl bg-gray-50">
                <span className="w-6 h-6 rounded-full bg-brand-500 text-white text-xs font-bold flex items-center justify-center shrink-0">
                  {i + 1}
                </span>
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-800">
                    {r.recommendation ?? r}
                  </p>
                  {r.timeframe && (
                    <p className="text-xs text-gray-400 mt-0.5">
                      Plazo: {r.timeframe?.replace(/_/g, " ")}
                      {r.expected_impact && ` · ${r.expected_impact}`}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Roadmap ── */}
      {redactor?.roadmap && (
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5">
          <h3 className="font-semibold text-gray-800 flex items-center gap-2 mb-4">
            <Clock size={16} className="text-brand-500" />
            Roadmap de Implementación
          </h3>
          <div className="grid grid-cols-3 gap-3">
            {[
              { key: "days_90",  label: "90 días",  color: "bg-blue-50 border-blue-200" },
              { key: "days_180", label: "180 días", color: "bg-brand-50 border-brand-200" },
              { key: "days_365", label: "365 días", color: "bg-purple-50 border-purple-200" },
            ].map(({ key, label, color }) => {
              const period = redactor.roadmap[key];
              if (!period) return null;
              return (
                <div key={key} className={`rounded-xl border p-3 ${color}`}>
                  <p className="text-xs font-bold text-gray-600 mb-2">{label}</p>
                  {typeof period === "object" && period.theme && (
                    <p className="text-xs font-semibold text-gray-700 mb-1">{period.theme}</p>
                  )}
                  <ul className="space-y-1">
                    {(Array.isArray(period) ? period : period.actions ?? []).slice(0, 3).map((a: string, i: number) => (
                      <li key={i} className="text-xs text-gray-600 flex gap-1">
                        <span className="text-brand-500 shrink-0">·</span>{a}
                      </li>
                    ))}
                  </ul>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── Próximos pasos ── */}
      {redactor?.next_steps?.length > 0 && (
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5">
          <h3 className="font-semibold text-gray-800 mb-3">Próximos Pasos Inmediatos</h3>
          <div className="space-y-2">
            {redactor.next_steps.slice(0, 5).map((step: string, i: number) => (
              <div key={i} className="flex gap-2 text-sm text-gray-700 p-2 rounded-lg hover:bg-gray-50">
                <span className="text-brand-500 font-bold shrink-0">→</span>{step}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── NC Report ── */}
      <NCReport stages={stages} />

      {/* ── Survey Results Chart ── */}
      <SurveyResultsChart stages={stages} />

      {/* ── Certificado criptográfico ── */}
      <CryptoPanel certificate={cert} />
    </div>
  );
}
