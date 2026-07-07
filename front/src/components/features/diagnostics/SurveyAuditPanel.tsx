"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { apiPro } from "@/lib/api-pro";
import { Spinner } from "@/components/ui/Spinner";
import {
  ChevronDown, ChevronUp, CheckCircle, XCircle,
  AlertTriangle, BookOpen, BarChart2, MessageSquare, Shield
} from "lucide-react";

// ── Color helpers ─────────────────────────────────────────────────────────────
const ROLE_COLORS: Record<string, string> = {
  "Estratégico": "text-[#56624b] bg-[#56624b]/10 border-[#56624b]/20",
  "Táctico":     "text-[#243c4f] bg-[#243c4f]/10 border-[#243c4f]/20",
  "Operativo":   "text-[#9b6d4d] bg-[#9b6d4d]/10 border-[#9b6d4d]/20",
};
const ROLE_BAR: Record<string, string> = {
  "Estratégico": "bg-[#56624b]",
  "Táctico":     "bg-[#243c4f]",
  "Operativo":   "bg-[#9b6d4d]",
};

function scoreColor(score: number) {
  if (score >= 70) return "text-green-600";
  if (score >= 50) return "text-amber-600";
  return "text-red-600";
}

// ── Distribution bar ──────────────────────────────────────────────────────────
function DistBar({ dist, n }: { dist: Record<string, number>; n: number }) {
  const labels = ["1", "2", "3", "4", "5"];
  const colors = ["bg-red-400", "bg-orange-400", "bg-yellow-400", "bg-lime-400", "bg-green-500"];
  return (
    <div className="flex gap-0.5 h-4 rounded overflow-hidden w-full">
      {labels.map((l, i) => {
        const count = dist[l] ?? 0;
        const pct = n > 0 ? (count / n) * 100 : 0;
        return pct > 0 ? (
          <div
            key={l}
            className={`${colors[i]} flex items-center justify-center text-[9px] text-white font-bold`}
            style={{ width: `${pct}%` }}
            title={`${l}: ${count} (${pct.toFixed(0)}%)`}
          >
            {count > 0 && pct > 8 ? l : ""}
          </div>
        ) : null;
      })}
    </div>
  );
}

// ── Question card ─────────────────────────────────────────────────────────────
function QuestionCard({ q, index }: { q: any; index: number }) {
  const [open, setOpen] = useState(false);
  const isLikert = q.type === "likert_5";
  const isReverse = q.reverse_scored;
  const stats = q.response_stats ?? {};
  const hasStats = Object.keys(stats).length > 0;

  return (
    <div className={`rounded-xl border ${isReverse ? "border-amber-200 bg-amber-50/30" : "border-gray-200 bg-white"}`}>
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-start gap-3 p-4 text-left"
      >
        {/* Number */}
        <span className="shrink-0 w-7 h-7 rounded-full bg-gray-100 text-gray-500 text-xs font-bold flex items-center justify-center mt-0.5">
          {index + 1}
        </span>

        <div className="flex-1 min-w-0">
          {/* Header row */}
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span className="text-xs font-bold text-gray-400">{q.id}</span>
            <span className="text-xs px-1.5 py-0.5 rounded bg-gray-100 text-gray-500">{q.dimension}</span>
            {q.hypothesis_tested && (
              <span className="text-xs px-1.5 py-0.5 rounded bg-brand-100 text-brand-700 font-semibold">
                {q.hypothesis_tested}
              </span>
            )}
            {isReverse && (
              <span className="text-xs px-1.5 py-0.5 rounded bg-amber-100 text-amber-700 font-semibold">
                ↔ Reverse
              </span>
            )}
            {q.roles?.map((r: string) => (
              <span key={r} className={`text-xs px-1.5 py-0.5 rounded border font-medium ${ROLE_COLORS[r] ?? "bg-gray-50 text-gray-500 border-gray-200"}`}>
                {r}
              </span>
            ))}
          </div>

          {/* Question text */}
          <p className="text-sm text-gray-800 leading-relaxed">{q.text}</p>

          {/* Quick score preview */}
          {isLikert && hasStats && (
            <div className="flex gap-3 mt-2">
              {Object.entries(stats).map(([role, s]: [string, any]) => (
                <span key={role} className={`text-xs font-bold ${scoreColor(s.corrected_score)}`}>
                  {role.slice(0, 3)}: {s.corrected_score}
                </span>
              ))}
            </div>
          )}
        </div>

        {open ? <ChevronUp size={14} className="text-gray-400 shrink-0 mt-1" /> : <ChevronDown size={14} className="text-gray-400 shrink-0 mt-1" />}
      </button>

      {open && (
        <div className="px-4 pb-4 space-y-4 border-t border-gray-100 pt-3">

          {/* Rationale */}
          {q.rationale && (
            <div className="bg-blue-50 rounded-lg p-3">
              <p className="text-xs font-semibold text-blue-700 mb-1">¿Por qué esta pregunta?</p>
              <p className="text-xs text-blue-600 leading-relaxed">{q.rationale}</p>
            </div>
          )}

          {/* Expected direction */}
          {q.expected_direction?.if_hypothesis_true && (
            <div className="bg-gray-50 rounded-lg p-3">
              <p className="text-xs font-semibold text-gray-600 mb-2">Señal esperada si la hipótesis es verdadera:</p>
              <div className="space-y-1">
                {Object.entries(q.expected_direction.if_hypothesis_true).map(([role, expectation]: [string, any]) => (
                  <div key={role} className="flex gap-2 text-xs">
                    <span className={`font-semibold shrink-0 ${ROLE_COLORS[role]?.split(" ")[0] ?? "text-gray-600"}`}>{role}:</span>
                    <span className="text-gray-600">{expectation}</span>
                  </div>
                ))}
              </div>
              {q.expected_direction.signal_logic && (
                <p className="text-xs text-gray-500 mt-2 italic">
                  Lógica: {q.expected_direction.signal_logic}
                </p>
              )}
            </div>
          )}

          {/* Reverse scoring explanation */}
          {isReverse && (
            <div className="bg-amber-50 rounded-lg p-3 flex gap-2">
              <AlertTriangle size={14} className="text-amber-600 shrink-0 mt-0.5" />
              <div>
                <p className="text-xs font-semibold text-amber-700">Ítem reverse-scored</p>
                <p className="text-xs text-amber-600 mt-0.5">
                  Score corregido = 6 − respuesta original. Controla sesgo de aquiescencia (Paulhus, 1991).
                  Un score alto en la respuesta original indica problema, no acuerdo.
                </p>
              </div>
            </div>
          )}

          {/* Response stats per role */}
          {isLikert && hasStats && (
            <div className="space-y-3">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Respuestas reales</p>
              {Object.entries(stats).map(([role, s]: [string, any]) => (
                <div key={role} className="space-y-1">
                  <div className="flex items-center justify-between">
                    <span className={`text-xs font-semibold ${ROLE_COLORS[role]?.split(" ")[0] ?? "text-gray-600"}`}>
                      {role} (n={s.n})
                    </span>
                    <div className="flex gap-3 text-xs">
                      <span className="text-gray-400">Promedio raw: <span className="font-semibold text-gray-600">{s.raw_avg}</span></span>
                      <span className="text-gray-400">Corregido: <span className={`font-bold ${scoreColor(s.corrected_score)}`}>{s.corrected_score}/100</span></span>
                    </div>
                  </div>
                  <DistBar dist={s.distribution} n={s.n} />
                  <div className="flex justify-between text-[9px] text-gray-400 px-0.5">
                    <span>1 (Nunca)</span>
                    <span>3 (Neutral)</span>
                    <span>5 (Siempre)</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Dimension card ────────────────────────────────────────────────────────────
function DimensionCard({ dim }: { dim: any }) {
  const [open, setOpen] = useState(false);
  const roleScores = dim.role_scores ?? {};
  const hasScores = Object.keys(roleScores).length > 0;

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center gap-3 p-4 text-left"
      >
        <div className="flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-bold text-gray-400">{dim.id}</span>
            {dim.hypothesis_mapped && (
              <span className="text-xs px-1.5 py-0.5 rounded bg-brand-100 text-brand-700 font-semibold">
                → {dim.hypothesis_mapped}
              </span>
            )}
            <span className="text-xs text-gray-400">{dim.n_questions} preguntas · {dim.reverse_scored_count} reverse</span>
          </div>
          <p className="text-sm font-semibold text-gray-800 mt-0.5">{dim.name}</p>
          {hasScores && (
            <div className="flex gap-3 mt-1">
              {Object.entries(roleScores).map(([role, score]: [string, any]) => (
                <span key={role} className={`text-xs font-bold ${scoreColor(score)}`}>
                  {role.slice(0, 3)}: {score}
                </span>
              ))}
            </div>
          )}
        </div>
        {open ? <ChevronUp size={14} className="text-gray-400" /> : <ChevronDown size={14} className="text-gray-400" />}
      </button>

      {open && (
        <div className="px-4 pb-4 space-y-3 border-t border-gray-100 pt-3">
          {dim.hypothesis_text && (
            <div className="bg-brand-50 rounded-lg p-3">
              <p className="text-xs font-semibold text-brand-700 mb-1">Hipótesis que verifica:</p>
              <p className="text-xs text-brand-600">{dim.hypothesis_text}</p>
            </div>
          )}
          {dim.expected_pattern_if_true && (
            <div className="bg-green-50 rounded-lg p-3">
              <p className="text-xs font-semibold text-green-700 mb-1">Patrón esperado si la hipótesis es verdadera:</p>
              <p className="text-xs text-green-600">{dim.expected_pattern_if_true}</p>
            </div>
          )}
          {dim.expected_pattern_if_false && (
            <div className="bg-gray-50 rounded-lg p-3">
              <p className="text-xs font-semibold text-gray-600 mb-1">Patrón si la hipótesis es falsa:</p>
              <p className="text-xs text-gray-500">{dim.expected_pattern_if_false}</p>
            </div>
          )}
          {hasScores && (
            <div className="space-y-2">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Score corregido por rol</p>
              {Object.entries(roleScores).map(([role, score]: [string, any]) => (
                <div key={role}>
                  <div className="flex justify-between text-xs mb-1">
                    <span className={`font-semibold ${ROLE_COLORS[role]?.split(" ")[0] ?? "text-gray-600"}`}>{role}</span>
                    <span className={`font-bold ${scoreColor(score)}`}>{score}/100</span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${ROLE_BAR[role] ?? "bg-gray-400"}`}
                      style={{ width: `${score}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
export function SurveyAuditPanel({ surveyToken, isPro }: { surveyToken: string, isPro?: boolean }) {
  const [tab, setTab] = useState<"instrument" | "questions" | "responses" | "methodology">("instrument");

  const { data, isLoading, error } = useQuery({
    queryKey: ["survey-audit", surveyToken, isPro],
    queryFn: () => {
      const client = isPro ? apiPro : api;
      const path = isPro
        ? `/pro/survey/${surveyToken}/audit`
        : `/survey/${surveyToken}/audit`;
      return client.get(path).then((r) => r.data);
    },
    enabled: !!surveyToken,
  });

  if (isLoading) return <div className="flex justify-center py-12"><Spinner /></div>;
  if (error) {
    const msg = error instanceof Error ? error.message : "Error desconocido";
    return (
      <div className="p-4 bg-red-50 text-red-600 text-xs font-mono border border-red-200">
        Error loading audit: {msg}
      </div>
    );
  }
  if (!data) return null;

  const tabs = [
    { id: "instrument",  label: "Instrumento",   icon: BookOpen },
    { id: "questions",   label: "Preguntas",      icon: MessageSquare },
    { id: "responses",   label: "Respuestas",     icon: BarChart2 },
    { id: "methodology", label: "Metodología",    icon: Shield },
  ] as const;

  const likertQuestions = data.questions?.filter((q: any) => q.type === "likert_5") ?? [];
  const openQuestions   = data.questions?.filter((q: any) => q.type === "open_text") ?? [];

  return (
    <div className="bg-[#f4f1ea]/90 border border-[#171717]/10 overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-[#171717]/10">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-serif text-xl font-medium text-[#171717]">Auditoría del Instrumento Multi-Rater</h3>
            <p className="text-[11px] font-mono text-[#706f69] mt-0.5">
              {data.instrument_name} · {data.total_responses} respuestas
            </p>
          </div>
          <div className="flex gap-2">
            {Object.entries(data.responses_by_role ?? {}).map(([role, n]: [string, any]) => (
              <span key={role} className={`text-xs px-2 py-1 rounded-lg border font-semibold ${ROLE_COLORS[role] ?? "bg-gray-50 text-gray-500 border-gray-200"}`}>
                {role.slice(0, 3)}: {n}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-[#171717]/10 bg-[#171717]/5">
        {tabs.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex-1 flex items-center justify-center gap-1.5 py-3 text-[11px] font-mono transition-all ${
              tab === t.id
                ? "text-[#171717] font-semibold border-b-2 border-[#171717] bg-transparent"
                : "text-[#706f69] hover:text-[#171717] hover:bg-[#171717]/5"
            }`}
          >
            <t.icon size={13} />
            {t.label}
          </button>
        ))}
      </div>

      <div className="p-5">

        {/* ── INSTRUMENTO ── */}
        {tab === "instrument" && (
          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-3 text-center">
              <div className="bg-gray-50 rounded-xl p-3">
                <p className="text-2xl font-black text-gray-900">{data.questions?.length ?? 0}</p>
                <p className="text-xs text-gray-500 mt-0.5">Preguntas totales</p>
              </div>
              <div className="bg-gray-50 rounded-xl p-3">
                <p className="text-2xl font-black text-gray-900">{likertQuestions.length}</p>
                <p className="text-xs text-gray-500 mt-0.5">Likert 1-5</p>
              </div>
              <div className="bg-gray-50 rounded-xl p-3">
                <p className="text-2xl font-black text-gray-900">{openQuestions.length}</p>
                <p className="text-xs text-gray-500 mt-0.5">Abiertas</p>
              </div>
            </div>

            {/* Reverse scoring info */}
            {data.reverse_scored_items?.length > 0 && (
              <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
                <div className="flex items-center gap-2 mb-2">
                  <AlertTriangle size={14} className="text-amber-600" />
                  <p className="text-xs font-semibold text-amber-700">
                    {data.reverse_scored_items.length} ítems con corrección de reverse-scoring
                  </p>
                </div>
                <div className="flex flex-wrap gap-1.5 mb-2">
                  {data.reverse_scored_items.map((id: string) => (
                    <span key={id} className="text-xs px-2 py-0.5 bg-amber-100 text-amber-700 rounded font-mono font-semibold">{id}</span>
                  ))}
                </div>
                <p className="text-xs text-amber-600">
                  Fórmula aplicada: <span className="font-mono font-semibold">{data.correction_formula}</span>
                  <br />Aplicado por: pipeline_runner.py (código determinista, no LLM)
                </p>
              </div>
            )}

            {/* Dimensions */}
            <div className="space-y-2">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Dimensiones del instrumento</p>
              {data.dimensions?.map((dim: any) => (
                <DimensionCard key={dim.id} dim={dim} />
              ))}
            </div>
          </div>
        )}

        {/* ── PREGUNTAS ── */}
        {tab === "questions" && (
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-xs text-gray-500 bg-gray-50 rounded-lg p-3">
              <CheckCircle size={13} className="text-green-500" />
              Cada pregunta muestra: texto, hipótesis que verifica, señal esperada por rol, y distribución real de respuestas.
            </div>
            {data.questions?.map((q: any, i: number) => (
              <QuestionCard key={q.id} q={q} index={i} />
            ))}
          </div>
        )}

        {/* ── RESPUESTAS ── */}
        {tab === "responses" && (
          <div className="space-y-5">
            {/* Open answers by role */}
            {Object.entries(data.open_answers_by_role ?? {}).map(([role, answers]: [string, any]) => {
              if (!answers?.length) return null;
              return (
                <div key={role}>
                  <p className={`text-xs font-semibold mb-2 ${ROLE_COLORS[role]?.split(" ")[0] ?? "text-gray-600"}`}>
                    {role} — Respuestas abiertas ({answers.length})
                  </p>
                  <div className="space-y-2">
                    {answers.map((a: any, i: number) => {
                      const q = data.questions?.find((q: any) => q.id === a.question_id);
                      return (
                        <div key={i} className="bg-gray-50 rounded-xl p-3">
                          {q && <p className="text-xs text-gray-400 mb-1">{q.text}</p>}
                          <p className="text-sm text-gray-700 leading-relaxed">"{a.text}"</p>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}

            {/* Per-question score heatmap */}
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                Score corregido por pregunta y rol
              </p>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-gray-100">
                      <th className="text-left py-2 pr-3 text-gray-400 font-medium w-16">ID</th>
                      <th className="text-left py-2 pr-3 text-gray-400 font-medium">Pregunta</th>
                      <th className="text-center py-2 px-2 text-indigo-500 font-semibold">Est.</th>
                      <th className="text-center py-2 px-2 text-sky-500 font-semibold">Tác.</th>
                      <th className="text-center py-2 px-2 text-emerald-500 font-semibold">Op.</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.questions?.filter((q: any) => q.type === "likert_5").map((q: any) => {
                      const stats = q.response_stats ?? {};
                      return (
                        <tr key={q.id} className="border-b border-gray-50 hover:bg-gray-50">
                          <td className="py-2 pr-3 font-mono text-gray-400">{q.id}</td>
                          <td className="py-2 pr-3 text-gray-600 max-w-xs">
                            <span className="line-clamp-1">{q.text}</span>
                            {q.reverse_scored && <span className="ml-1 text-amber-500 text-[10px]">↔</span>}
                          </td>
                          {["Estratégico", "Táctico", "Operativo"].map(role => {
                            const s = stats[role];
                            const score = s?.corrected_score;
                            const bg = score == null ? "text-gray-300" : score >= 70 ? "text-green-600 font-bold" : score >= 50 ? "text-amber-600 font-bold" : "text-red-600 font-bold";
                            return (
                              <td key={role} className={`text-center py-2 px-2 ${bg}`}>
                                {score != null ? score : "—"}
                              </td>
                            );
                          })}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* ── METODOLOGÍA ── */}
        {tab === "methodology" && (
          <div className="space-y-4">
            {data.methodology && (
              <div className="space-y-3">
                <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
                  <p className="text-xs font-semibold text-blue-700 mb-1">Estándar metodológico</p>
                  <p className="text-sm text-blue-800 font-medium">{data.methodology.standard}</p>
                </div>
                {data.methodology.design_principle && (
                  <div className="bg-gray-50 rounded-xl p-4">
                    <p className="text-xs font-semibold text-gray-600 mb-1">Principio de diseño</p>
                    <p className="text-sm text-gray-700">{data.methodology.design_principle}</p>
                  </div>
                )}
                <div className="grid grid-cols-2 gap-3">
                  {[
                    { label: "IRR objetivo", value: data.methodology.irr_target },
                    { label: "Reverse scoring", value: data.methodology.reverse_scoring },
                    { label: "Diferenciación de roles", value: data.methodology.role_differentiation },
                  ].filter(i => i.value).map(item => (
                    <div key={item.label} className="bg-gray-50 rounded-xl p-3">
                      <p className="text-xs font-semibold text-gray-500 mb-1">{item.label}</p>
                      <p className="text-xs text-gray-700">{item.value}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Correction audit */}
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
              <div className="flex items-center gap-2 mb-3">
                <Shield size={14} className="text-amber-600" />
                <p className="text-xs font-semibold text-amber-700">Trazabilidad del scoring</p>
              </div>
              <div className="space-y-2 text-xs text-amber-700">
                <p>• Ítems reverse-scored: <span className="font-mono font-bold">{data.reverse_scored_items?.join(", ") || "ninguno"}</span></p>
                <p>• Corrección aplicada: <span className="font-mono font-bold">{data.correction_formula}</span></p>
                <p>• Aplicado por: <span className="font-semibold">pipeline_runner.py (código Python determinista)</span></p>
                <p>• Verificable: toma las respuestas crudas de survey_responses, aplica la fórmula, y compara con los scores de g10a_scoring</p>
              </div>
            </div>

            {/* Scale explanation */}
            <div className="bg-white border border-gray-200 rounded-xl p-4">
              <p className="text-xs font-semibold text-gray-600 mb-3">Escala Likert 1-5 → Score 0-100</p>
              <div className="space-y-1.5">
                {[
                  { val: 1, label: "Nunca / Totalmente en desacuerdo", score: 0 },
                  { val: 2, label: "Rara vez / En desacuerdo", score: 25 },
                  { val: 3, label: "A veces / Neutral", score: 50 },
                  { val: 4, label: "Frecuentemente / De acuerdo", score: 75 },
                  { val: 5, label: "Siempre / Totalmente de acuerdo", score: 100 },
                ].map(row => (
                  <div key={row.val} className="flex items-center gap-3 text-xs">
                    <span className="w-4 h-4 rounded-full bg-gray-200 flex items-center justify-center font-bold text-gray-600 shrink-0">{row.val}</span>
                    <span className="flex-1 text-gray-600">{row.label}</span>
                    <span className="font-mono font-bold text-gray-500">{row.score}/100</span>
                  </div>
                ))}
              </div>
              <p className="text-xs text-gray-400 mt-3">
                Fórmula: <span className="font-mono">(valor - 1) / 4 × 100</span>
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
