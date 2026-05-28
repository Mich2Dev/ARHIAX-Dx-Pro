"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Spinner } from "@/components/ui/Spinner";
import { Copy, CheckCircle, Users, Eye, X } from "lucide-react";
import { useState } from "react";
import { SurveyResultsChart } from "./SurveyResultsChart";

// ── Modal wrapper ─────────────────────────────────────────────────────────────
function ChartModal({ onClose, liveStages }: { onClose: () => void; liveStages: any[] }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="w-full max-w-3xl max-h-[90vh] overflow-y-auto rounded-2xl shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 bg-gray-900 rounded-t-2xl border-b border-gray-800">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            <p className="text-sm font-semibold text-white">Análisis en vivo</p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors"
          >
            <X size={20} />
          </button>
        </div>
        {/* Chart */}
        <SurveyResultsChart stages={liveStages} />
      </div>
    </div>
  );
}

export function SurveyProgress({ diagnosticId }: { diagnosticId: string }) {
  const queryClient = useQueryClient();
  const [copied, setCopied] = useState(false);
  const [showChart, setShowChart] = useState(false);

  // Fetch diagnostic to get survey token
  const { data: diagnostic } = useQuery({
    queryKey: ["diagnostic", diagnosticId],
    queryFn: () => api.get(`/v2/diagnostics/${diagnosticId}`).then(r => r.data),
    refetchInterval: 5000,
  });

  // Fetch live survey status + partial scores
  const { data: surveyStatus } = useQuery({
    queryKey: ["survey-live", diagnostic?.survey?.token],
    queryFn: () =>
      api.get(`/survey/${diagnostic.survey.token}/status`).then(r => r.data),
    enabled: !!diagnostic?.survey?.token,
    refetchInterval: 5000,
  });

  const closeMutation = useMutation({
    mutationFn: () =>
      api.post(`/v2/diagnostics/${diagnosticId}/survey/close`).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["diagnostic", diagnosticId] });
    },
  });

  const survey = diagnostic?.survey;
  if (!survey) return null;

  const surveyUrl = `${process.env.NEXT_PUBLIC_APP_URL ?? (typeof window !== "undefined" ? window.location.origin : "http://localhost:3000")}/survey/${survey.token}`;
  const responses = surveyStatus?.responses_count ?? survey.responses_count ?? 0;
  const target    = survey.target_responses ?? 20;
  const minimum   = survey.min_responses ?? 5;
  const progress  = (responses / target) * 100;
  const canClose  = responses >= minimum;
  const byRole    = surveyStatus?.by_role ?? {};
  const liveScores = surveyStatus?.live_scores;

  const handleCopy = () => {
    navigator.clipboard.writeText(surveyUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Build fake stages from live scores for the chart
  const liveStages = liveScores ? [
    {
      tool_name: "g10a_scoring",
      status: "partial",
      output: {
        output: {
          scoring_summary: {
            overall_score: liveScores.overall_score,
            benchmark_score: 75,
          },
          dimension_scores: liveScores.dimension_scores,
          role_scores: liveScores.role_scores,
          delta_sigma: liveScores.delta_sigma,
        }
      }
    }
  ] : [];

  return (
    <div className="space-y-4">
      {/* ── Survey control card ── */}
      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
        <div className="flex items-center gap-2 mb-4">
          <Users size={20} className="text-brand-500" />
          <h3 className="font-semibold text-gray-800">Encuesta Multi-Rater</h3>
          {responses > 0 && (
            <span className="ml-auto text-xs bg-brand-100 text-brand-700 px-2 py-0.5 rounded-full font-semibold">
              En vivo
            </span>
          )}
        </div>

        {/* URL */}
        <div className="bg-gray-50 rounded-xl p-4 mb-4">
          <p className="text-xs font-semibold text-gray-600 mb-2">URL de la encuesta:</p>
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={surveyUrl}
              readOnly
              className="flex-1 text-sm font-mono bg-white border border-gray-200 rounded-lg px-3 py-2"
            />
            <button
              onClick={handleCopy}
              className="px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white rounded-lg text-sm font-semibold transition-colors flex items-center gap-2"
            >
              {copied ? <><CheckCircle size={16} />Copiado</> : <><Copy size={16} />Copiar</>}
            </button>
          </div>
          <p className="text-xs text-gray-500 mt-2">
            Comparte esta URL con los empleados de la organización
          </p>
        </div>

        {/* Progress */}
        <div className="space-y-3 mb-4">
          <div className="flex items-center justify-between">
            <p className="text-sm font-semibold text-gray-700">Progreso</p>
            <p className="text-sm text-gray-500">
              <span className="font-bold text-gray-900">{responses}</span> / {target} respuestas
            </p>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2.5 overflow-hidden">
            <div
              className="bg-brand-500 h-2.5 rounded-full transition-all duration-500"
              style={{ width: `${Math.min(progress, 100)}%` }}
            />
          </div>

          {/* By role */}
          {Object.keys(byRole).length > 0 && (
            <div className="grid grid-cols-3 gap-2 text-xs">
              {["Estratégico", "Táctico", "Operativo"].map(role => (
                <div key={role} className="bg-gray-50 rounded-lg p-2 text-center">
                  <p className="text-gray-500 truncate">{role}</p>
                  <p className="font-bold text-gray-900 text-base">{byRole[role] ?? 0}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Min reached */}
        {canClose && (
          <div className="bg-green-50 border border-green-200 rounded-xl p-3 mb-4">
            <p className="text-sm font-semibold text-green-800">
              ✓ Mínimo de respuestas alcanzado ({minimum})
            </p>
            <p className="text-xs text-green-600 mt-0.5">
              Ya puedes cerrar la encuesta y continuar con el análisis
            </p>
          </div>
        )}

        {/* Close button */}
        <button
          onClick={() => closeMutation.mutate()}
          disabled={closeMutation.isPending || !canClose}
          className="w-full bg-brand-500 hover:bg-brand-600 disabled:bg-gray-300 text-white font-semibold py-2.5 rounded-xl text-sm transition-colors flex items-center justify-center gap-2"
        >
          {closeMutation.isPending ? (
            <><Spinner className="w-4 h-4 border-white border-t-brand-200" />Cerrando...</>
          ) : (
            "Cerrar Encuesta y Continuar Análisis →"
          )}
        </button>
        <p className="text-xs text-gray-400 mt-2 text-center">
          Mínimo requerido: {minimum} respuestas
        </p>
      </div>

      {/* ── Live charts — shown as soon as there are responses ── */}
      {liveScores && liveScores.total_responses > 0 && (
        <div className="space-y-2">
          <div className="flex items-center gap-2 px-1">
            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            <p className="text-xs font-semibold text-gray-600">
              Análisis parcial en vivo — {liveScores.total_responses} respuesta{liveScores.total_responses !== 1 ? "s" : ""}
            </p>
          </div>
          <SurveyResultsChart stages={liveStages} />
        </div>
      )}
    </div>
  );
}
