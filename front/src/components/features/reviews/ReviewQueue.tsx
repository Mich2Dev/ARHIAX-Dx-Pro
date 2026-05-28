"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api";
import { Spinner } from "@/components/ui/Spinner";
import { formatDate } from "@/lib/utils";
import {
  CheckCircle, AlertTriangle, TrendingUp,
  ExternalLink, Bell, Info,
} from "lucide-react";

// ── Alert type metadata ───────────────────────────────────────────────────────
const ALERT_META: Record<string, {
  label: string;
  explanation: string;
  recommendation: string;
  color: string;
  bg: string;
  icon: React.ElementType;
}> = {
  "IRR-LOW": {
    label: "Confiabilidad baja entre evaluadores",
    explanation: "El Alpha de Krippendorff entre los 3 niveles jerárquicos está por debajo de 0.70. Esto significa que Estratégico, Táctico y Operativo respondieron de forma inconsistente entre sí.",
    recommendation: "Considera repetir la encuesta con instrucciones más claras, o tomar los resultados con cautela al presentarlos al cliente.",
    color: "text-orange-600",
    bg: "bg-orange-50 border-orange-200",
    icon: AlertTriangle,
  },
  "DELTA-SIGMA-CRITICAL": {
    label: "Brecha de percepción crítica detectada",
    explanation: "La diferencia de percepción entre niveles jerárquicos supera δσ = 2.0. La dirección y los operarios tienen visiones radicalmente distintas del proceso.",
    recommendation: "Este hallazgo es valioso — indica un problema cultural o de comunicación. Asegúrate de destacarlo en la presentación al cliente como un hallazgo crítico.",
    color: "text-red-600",
    bg: "bg-red-50 border-red-200",
    icon: TrendingUp,
  },
  "QA-LOW": {
    label: "Score de calidad del informe bajo",
    explanation: "El control de calidad automático (G14) dio un score menor a 85/100. El informe puede tener secciones incompletas o poco coherentes.",
    recommendation: "Revisa el informe antes de entregarlo al cliente. Presta atención a las secciones de hallazgos y recomendaciones.",
    color: "text-amber-600",
    bg: "bg-amber-50 border-amber-200",
    icon: AlertTriangle,
  },
  "G01-MANDATE-COHERENCE": {
    label: "Mandato rechazado por datos incoherentes",
    explanation: "El agente G01 detectó que los datos del mandato no eran coherentes para ejecutar un diagnóstico real.",
    recommendation: "Crea un nuevo diagnóstico con datos reales del cliente.",
    color: "text-red-600",
    bg: "bg-red-50 border-red-200",
    icon: AlertTriangle,
  },
};

function getAlertMeta(ruleId: string) {
  return ALERT_META[ruleId] ?? {
    label: ruleId,
    explanation: "Alerta del sistema.",
    recommendation: "Revisa el diagnóstico para más detalles.",
    color: "text-gray-600",
    bg: "bg-gray-50 border-gray-200",
    icon: Info,
  };
}

// ── Metric pill ───────────────────────────────────────────────────────────────
function MetricPill({ label, value, ok }: { label: string; value: any; ok: boolean }) {
  if (value == null) return null;
  return (
    <span className={`inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full ${
      ok ? "bg-green-100 text-green-700" : "bg-red-100 text-red-600"
    }`}>
      {label}: {value}
    </span>
  );
}

// ── Alert card ────────────────────────────────────────────────────────────────
function AlertCard({ item }: { item: any }) {
  const { alerts, metrics } = item;

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-gray-100">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="font-bold text-gray-900">{item.organization_name}</p>
            <p className="text-sm text-gray-500 mt-0.5">{item.domain} · {item.subprocess}</p>
            {item.objective && (
              <p className="text-xs text-gray-400 mt-1 italic">"{item.objective}"</p>
            )}
          </div>
          <div className="flex flex-col items-end gap-1 shrink-0">
            <span className="text-xs text-gray-400">{formatDate(item.completed_at)}</span>
            <Link
              href={`/dashboard/diagnostics/${item.diagnostic_id}`}
              className="text-xs text-brand-500 hover:text-brand-600 flex items-center gap-1"
            >
              Ver diagnóstico <ExternalLink size={10} />
            </Link>
          </div>
        </div>

        {/* Metrics row */}
        {metrics && (
          <div className="flex flex-wrap gap-2 mt-3">
            <MetricPill label="QA" value={metrics.qa_score != null ? `${metrics.qa_score}/100` : null} ok={(metrics.qa_score ?? 0) >= 85} />
            <MetricPill label="Score" value={metrics.overall_score != null ? `${metrics.overall_score}/100` : null} ok={(metrics.overall_score ?? 0) >= 60} />
            <MetricPill label="δσ" value={metrics.delta_sigma != null ? metrics.delta_sigma.toFixed(1) : null} ok={(metrics.delta_sigma ?? 0) <= 2.0} />
            <MetricPill label="IRR α" value={metrics.irr_alpha != null ? metrics.irr_alpha.toFixed(2) : null} ok={(metrics.irr_alpha ?? 0) >= 0.70} />
            {metrics.critical_findings > 0 && (
              <span className="inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full bg-red-100 text-red-600">
                {metrics.critical_findings} hallazgo{metrics.critical_findings > 1 ? "s" : ""} crítico{metrics.critical_findings > 1 ? "s" : ""}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Alerts */}
      <div className="px-5 py-4 space-y-3">
        {alerts.map((alert: any, i: number) => {
          const meta = getAlertMeta(alert.rule_id);
          const Icon = meta.icon;
          return (
            <div key={i} className={`rounded-xl border p-4 ${meta.bg}`}>
              <div className="flex items-start gap-3">
                <Icon size={16} className={`${meta.color} shrink-0 mt-0.5`} />
                <div className="space-y-1.5">
                  <p className={`text-sm font-semibold ${meta.color}`}>{meta.label}</p>
                  <p className="text-xs text-gray-600 leading-relaxed">{meta.explanation}</p>
                  <div className="bg-white/70 rounded-lg px-3 py-2">
                    <p className="text-xs font-semibold text-gray-500 mb-0.5">Recomendación:</p>
                    <p className="text-xs text-gray-600">{meta.recommendation}</p>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
export function ReviewQueue() {
  const { data, isLoading } = useQuery({
    queryKey: ["reviews"],
    queryFn: () => api.get("/v2/reviews/pending").then((r) => r.data),
    refetchInterval: 30000,
  });

  const items = data?.items ?? [];

  return (
    <div className="max-w-3xl mx-auto space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Alertas de calidad</h1>
          <p className="text-sm text-gray-500 mt-1">
            Diagnósticos completados con observaciones del sistema.
          </p>
        </div>
        {items.length > 0 && (
          <span className="bg-amber-100 text-amber-700 text-sm font-bold px-3 py-1 rounded-full">
            {items.length} con alertas
          </span>
        )}
      </div>

      {/* Info banner */}
      <div className="bg-blue-50 border border-blue-200 rounded-2xl p-4 flex gap-3">
        <Info size={16} className="text-blue-500 shrink-0 mt-0.5" />
        <p className="text-xs text-blue-700 leading-relaxed">
          Estos diagnósticos están <strong>completados</strong> y el reporte está disponible para descargar.
          Las alertas son observaciones informativas del sistema — no bloquean la entrega al cliente.
          Úsalas para decidir si necesitas mencionar algo al cliente o repetir algún paso.
        </p>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12"><Spinner /></div>
      ) : items.length === 0 ? (
        <div className="bg-white rounded-2xl border border-gray-200 p-16 text-center space-y-2">
          <CheckCircle size={32} className="text-green-400 mx-auto" />
          <p className="text-gray-500 text-sm font-medium">Sin alertas</p>
          <p className="text-gray-400 text-xs">Todos los diagnósticos completados pasaron los controles de calidad.</p>
        </div>
      ) : (
        items.map((item: any) => (
          <AlertCard key={item.id} item={item} />
        ))
      )}
    </div>
  );
}
