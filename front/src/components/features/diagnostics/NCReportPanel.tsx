-"use client";

import { useState } from "react";
import { AlertOctagon, ShieldCheck, Activity, Hash, ChevronDown, ChevronUp, TrendingUp } from "lucide-react";
import { Badge } from "@/components/ui/Badge";

// ── Autonomómetro ─────────────────────────────────────────────────────────────
const AUTONOMY_LEVELS = [
  { level: "A0", label: "Observación", color: "bg-gray-200", textColor: "text-gray-500" },
  { level: "A1", label: "Asistido",    color: "bg-blue-400",  textColor: "text-blue-700" },
  { level: "A2", label: "Autónomo",    color: "bg-brand-500", textColor: "text-brand-700" },
  { level: "A3", label: "Avanzado",    color: "bg-purple-500",textColor: "text-purple-700" },
  { level: "A4", label: "Máximo",      color: "bg-red-500",   textColor: "text-red-700" },
];

function Autonometer({ level }: { level: string }) {
  const idx = AUTONOMY_LEVELS.findIndex(a => a.level === level);
  const current = AUTONOMY_LEVELS[idx] ?? AUTONOMY_LEVELS[1];

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5">
      <div className="flex items-center gap-2 mb-4">
        <Activity size={18} className="text-brand-500" />
        <h3 className="font-semibold text-gray-800">Autonomómetro</h3>
        <Badge variant="blue">{current.level} — {current.label}</Badge>
      </div>

      {/* Progress bar */}
      <div className="flex gap-1 mb-3">
        {AUTONOMY_LEVELS.map((a, i) => (
          <div
            key={a.level}
            className={`flex-1 h-3 rounded-full transition-all ${
              i <= idx ? a.color : "bg-gray-100"
            }`}
          />
        ))}
      </div>

      <div className="flex justify-between text-xs text-gray-400 mb-4">
        {AUTONOMY_LEVELS.map(a => (
          <span key={a.level} className={a.level === level ? "font-bold text-gray-700" : ""}>
            {a.level}
          </span>
        ))}
      </div>

      {/* Criteria for next level */}
      {level === "A1" && (
        <div className="bg-blue-50 rounded-xl p-3">
          <p className="text-xs font-semibold text-blue-800 mb-2">
            Criterios para promover a A2:
          </p>
          <ul className="space-y-1">
            {[
              "BBR 30 días limpio (ratio escalado ≤ 0.12)",
              "QA score promedio ≥ 87/100 en últimos 5 informes",
              "IRR ≥ 0.75 (α Krippendorff) en últimos 3 diagnósticos",
              "Aprobación explícita de director-sinergia-001",
            ].map((c, i) => (
              <li key={i} className="text-xs text-blue-700 flex gap-1.5">
                <span className="shrink-0">·</span>{c}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// ── Hash Criptográfico ────────────────────────────────────────────────────────
function CryptoPanel({ certificate }: { certificate: any }) {
  const [show, setShow] = useState(false);

  if (!certificate) return null;

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5">
      <button
        onClick={() => setShow(!show)}
        className="w-full flex items-center justify-between"
      >
        <div className="flex items-center gap-2">
          <Hash size={18} className="text-brand-500" />
          <h3 className="font-semibold text-gray-800">Certificado Criptográfico</h3>
          <Badge variant="green">Ed25519 ✓</Badge>
        </div>
        {show ? <ChevronUp size={16} className="text-gray-400" /> : <ChevronDown size={16} className="text-gray-400" />}
      </button>

      {show && (
        <div className="mt-4 space-y-3">
          {/* Hash visual */}
          <div className="bg-gray-900 rounded-xl p-4 font-mono text-xs text-green-400 space-y-2">
            <div className="flex gap-2">
              <span className="text-gray-500 shrink-0">CERT ID</span>
              <span className="break-all">{certificate.certificate_id}</span>
            </div>
            <div className="flex gap-2">
              <span className="text-gray-500 shrink-0">DECISIÓN</span>
              <span className={certificate.decision === "ALLOW" ? "text-green-400" : "text-orange-400"}>
                {certificate.decision}
              </span>
            </div>
            <div className="flex gap-2">
              <span className="text-gray-500 shrink-0">EMITIDO</span>
              <span>{certificate.issued_at}</span>
            </div>
            <div className="flex gap-2">
              <span className="text-gray-500 shrink-0">CLAVE</span>
              <span>{certificate.public_key_id}</span>
            </div>
            <div className="border-t border-gray-700 pt-2">
              <p className="text-gray-500 mb-1">HASH SHA-256</p>
              <p className="break-all text-yellow-400">{certificate.evidence_hash}</p>
            </div>
            <div>
              <p className="text-gray-500 mb-1">FIRMA Ed25519</p>
              <p className="break-all text-cyan-400">{certificate.signature}</p>
            </div>
          </div>

          <div className="flex items-center gap-2 text-xs text-green-700 bg-green-50 rounded-lg p-2">
            <ShieldCheck size={14} />
            <span>Certificado firmado digitalmente. Verificable con clave pública {certificate.public_key_id}</span>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Reportes NC (No Conformidades) ────────────────────────────────────────────
const NC_SEVERITY: Record<string, { label: string; color: string; badge: "red" | "orange" | "gray" }> = {
  CRITICA:  { label: "NC Crítica",  color: "border-red-200 bg-red-50",    badge: "red" },
  ALTA:     { label: "NC Alta",     color: "border-orange-200 bg-orange-50", badge: "orange" },
  MEDIA:    { label: "NC Media",    color: "border-yellow-200 bg-yellow-50", badge: "gray" },
  BAJA:     { label: "NC Baja",     color: "border-gray-200 bg-gray-50",   badge: "gray" },
};

// ── Data Source Badge ─────────────────────────────────────────────────────────
function DataSourceBadge({ dataSource, nRespondents }: { dataSource?: string; nRespondents?: number }) {
  if (!dataSource) return null;
  const isReal = dataSource === "real_responses";
  return (
    <div className={`flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-semibold border ${
      isReal
        ? "bg-green-50 border-green-200 text-green-800"
        : "bg-amber-50 border-amber-200 text-amber-800"
    }`}>
      <span>{isReal ? "✓" : "⚠"}</span>
      <span>
        {isReal
          ? `Análisis basado en ${nRespondents ?? 0} respuestas reales`
          : "Análisis basado en datos simulados coherentes (sin respuestas de encuesta)"}
      </span>
    </div>
  );
}

function NCReport({ stages }: { stages: any[] }) {
  const [expanded, setExpanded] = useState<string | null>(null);

  // Extract findings from g12_hallazgos
  const hallazgosStage = stages.find(s => s.tool_name === "g12_hallazgos");
  const bayesianoStage = stages.find(s => s.tool_name === "g11a_bayesiano");
  const scoringStage   = stages.find(s => s.tool_name === "g10a_scoring");

  const hallazgos = hallazgosStage?.output?.output ?? hallazgosStage?.output ?? {};
  const bayesiano = bayesianoStage?.output?.output ?? bayesianoStage?.output ?? {};
  const scoring   = scoringStage?.output?.output   ?? scoringStage?.output   ?? {};

  const findings: any[] = hallazgos.findings_matrix ?? [];
  const perceptionGaps: any[] = bayesiano.critical_perception_gaps ?? [];
  const deltaSigma = scoring.delta_sigma?.max_gap ?? 0;

  if (findings.length === 0 && perceptionGaps.length === 0) return null;

  const criticalCount = findings.filter(f => f.priority === "CRITICA").length;
  const highCount     = findings.filter(f => f.priority === "ALTA").length;

  // Data source info for auditability
  const dataSource    = scoring.scoring_summary?.data_source;
  const nRespondents  = scoring.scoring_summary?.n_respondents;

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <AlertOctagon size={18} className="text-red-500" />
          <h3 className="font-semibold text-gray-800">Reporte de No Conformidades</h3>
        </div>
        <div className="flex gap-2">
          {criticalCount > 0 && (
            <Badge variant="red">{criticalCount} Crítica{criticalCount > 1 ? "s" : ""}</Badge>
          )}
          {highCount > 0 && (
            <Badge variant="orange">{highCount} Alta{highCount > 1 ? "s" : ""}</Badge>
          )}
        </div>
      </div>

      {/* Data source badge — auditability */}
      <DataSourceBadge dataSource={dataSource} nRespondents={nRespondents} />

      {/* Delta Sigma alert */}
      {deltaSigma > 2.0 && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-3 flex items-start gap-2">
          <AlertOctagon size={16} className="text-red-500 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-red-800">
              Brecha de percepción crítica detectada (δσ = {deltaSigma.toFixed(1)})
            </p>
            <p className="text-xs text-red-600 mt-0.5">
              Diferencia significativa entre niveles jerárquicos. Escalado a revisión humana.
            </p>
          </div>
        </div>
      )}

      {/* Perception gaps */}
      {perceptionGaps.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
            Brechas de Percepción
          </p>
          {perceptionGaps.map((gap: any, i: number) => (
            <div key={i} className="flex items-center gap-3 p-3 rounded-xl bg-orange-50 border border-orange-200">
              <div className="text-center shrink-0">
                <p className="text-lg font-black text-orange-600">{gap.delta_sigma?.toFixed(1) ?? "—"}</p>
                <p className="text-xs text-orange-500">δσ</p>
              </div>
              <div className="flex-1">
                <p className="text-sm font-semibold text-gray-800">{gap.dimension}</p>
                <p className="text-xs text-gray-500">{gap.roles}</p>
                {gap.interpretation && (
                  <p className="text-xs text-orange-700 mt-0.5">{gap.interpretation}</p>
                )}
              </div>
              {gap.escalate && <Badge variant="red">HIC</Badge>}
            </div>
          ))}
        </div>
      )}

      {/* NC findings */}
      {findings.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
            Hallazgos Clasificados
          </p>
          {findings.map((f: any) => {
            const sev = NC_SEVERITY[f.priority] ?? NC_SEVERITY.BAJA;
            const isOpen = expanded === f.id;
            return (
              <div key={f.id} className={`rounded-xl border p-3 ${sev.color}`}>
                <button
                  onClick={() => setExpanded(isOpen ? null : f.id)}
                  className="w-full flex items-start gap-2 text-left"
                >
                  <Badge variant={sev.badge}>{sev.label}</Badge>
                  <p className="text-sm font-medium text-gray-800 flex-1">{f.finding}</p>
                  <div className="flex items-center gap-2 shrink-0">
                    {f.bayesian_confidence && (
                      <span className="text-xs text-gray-500">
                        P={f.bayesian_confidence.toFixed(2)}
                      </span>
                    )}
                    {isOpen
                      ? <ChevronUp size={14} className="text-gray-400" />
                      : <ChevronDown size={14} className="text-gray-400" />
                    }
                  </div>
                </button>

                {isOpen && (
                  <div className="mt-3 pt-3 border-t border-gray-200 space-y-2">
                    {f.evidence?.length > 0 && (
                      <div>
                        <p className="text-xs font-semibold text-gray-600 mb-1">Evidencia:</p>
                        <ul className="space-y-0.5">
                          {f.evidence.map((e: string, i: number) => (
                            <li key={i} className="text-xs text-gray-600 flex gap-1.5">
                              <span className="shrink-0">·</span>{e}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {f.delta_sigma > 0 && (
                      <p className="text-xs text-gray-500">
                        Delta sigma: <span className="font-semibold">{f.delta_sigma}</span>
                        {f.delta_sigma > 2 && " ⚠️ Crítico"}
                      </p>
                    )}
                    {f.requires_escalation && (
                      <div className="flex items-center gap-1 text-xs text-red-600">
                        <AlertOctagon size={12} />
                        Requiere escalado a revisión humana
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Problem statements */}
      {hallazgos.problem_statements?.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
            Declaraciones del Problema
          </p>
          {hallazgos.problem_statements.slice(0, 3).map((ps: any, i: number) => (
            <div key={i} className="p-3 rounded-xl bg-gray-50 border border-gray-200">
              <p className="text-sm text-gray-700 leading-relaxed">
                {typeof ps === "string" ? ps : ps.statement}
              </p>
              {ps.urgency && (
                <p className="text-xs text-gray-400 mt-1">
                  Urgencia: {ps.urgency.replace(/_/g, " ")}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── BBR Live ──────────────────────────────────────────────────────────────────
function BBRLive({ stages }: { stages: any[] }) {
  const completed = stages.filter(s => s.status === "completed");
  const failed    = stages.filter(s => s.status === "failed" || (s.model_used ?? "").includes("error"));
  const totalTokens = stages.reduce((a, s) => a + (s.tokens_used ?? 0), 0);
  const avgLatency  = completed.length > 0
    ? Math.round(stages.reduce((a, s) => a + (s.latency_ms ?? 0), 0) / completed.length)
    : 0;

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5">
      <div className="flex items-center gap-2 mb-4">
        <TrendingUp size={18} className="text-brand-500" />
        <h3 className="font-semibold text-gray-800">Métricas de Ejecución</h3>
      </div>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <Metric label="Módulos OK"    value={`${completed.length}/${stages.length}`} color="text-green-600" />
        <Metric label="Fallidos"      value={failed.length}    color={failed.length > 0 ? "text-red-600" : "text-gray-400"} />
        <Metric label="Tokens Gemini" value={totalTokens.toLocaleString()} color="text-blue-600" />
        <Metric label="Latencia avg"  value={`${(avgLatency/1000).toFixed(1)}s`} color="text-gray-600" />
      </div>
    </div>
  );
}

function Metric({ label, value, color }: { label: string; value: any; color: string }) {
  return (
    <div className="text-center">
      <p className={`text-xl font-black ${color}`}>{value}</p>
      <p className="text-xs text-gray-400 mt-0.5">{label}</p>
    </div>
  );
}

// ── Export ────────────────────────────────────────────────────────────────────
export { NCReport, CryptoPanel, Autonometer, BBRLive, DataSourceBadge };
