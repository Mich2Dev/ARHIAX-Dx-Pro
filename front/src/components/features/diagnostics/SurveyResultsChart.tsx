"use client";

import { useState } from "react";
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, Cell, ReferenceLine,
} from "recharts";
import { BarChart2, Target, Users, Zap } from "lucide-react";

// ── Color palette ─────────────────────────────────────────────────────────────
const ROLE_COLORS = {
  "Estratégico": { fill: "#6366f1", stroke: "#4f46e5", light: "#eef2ff" },
  "Táctico":     { fill: "#0ea5e9", stroke: "#0284c7", light: "#e0f2fe" },
  "Operativo":   { fill: "#10b981", stroke: "#059669", light: "#d1fae5" },
};

const DIM_COLORS = ["#6366f1", "#0ea5e9", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6"];

// ── Custom 3D Bar ─────────────────────────────────────────────────────────────
function Bar3D(props: any) {
  const { x, y, width, height, fill } = props;
  if (!height || height <= 0) return null;

  const depth = 8;
  const topColor = fill;
  const sideColor = `${fill}99`;
  const frontColor = fill;

  return (
    <g>
      {/* Front face */}
      <rect x={x} y={y} width={width} height={height} fill={frontColor} rx={2} />
      {/* Top face (3D effect) */}
      <polygon
        points={`${x},${y} ${x + depth},${y - depth} ${x + width + depth},${y - depth} ${x + width},${y}`}
        fill={topColor}
        opacity={0.9}
      />
      {/* Right side face */}
      <polygon
        points={`${x + width},${y} ${x + width + depth},${y - depth} ${x + width + depth},${y + height - depth} ${x + width},${y + height}`}
        fill={sideColor}
      />
      {/* Shine on top */}
      <polygon
        points={`${x + 2},${y + 2} ${x + depth + 2},${y - depth + 2} ${x + width / 2},${y - depth + 2} ${x + width / 2},${y + 2}`}
        fill="white"
        opacity={0.15}
      />
    </g>
  );
}

// ── Custom Radar dot ──────────────────────────────────────────────────────────
function GlowDot(props: any) {
  const { cx, cy, fill } = props;
  return (
    <g>
      <circle cx={cx} cy={cy} r={8} fill={fill} opacity={0.2} />
      <circle cx={cx} cy={cy} r={5} fill={fill} opacity={0.5} />
      <circle cx={cx} cy={cy} r={3} fill={fill} />
    </g>
  );
}

// ── Custom Tooltip ────────────────────────────────────────────────────────────
function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-gray-900 border border-gray-700 rounded-xl p-3 shadow-2xl">
      <p className="text-xs font-bold text-gray-300 mb-2">{label}</p>
      {payload.map((p: any) => (
        <div key={p.name} className="flex items-center gap-2 text-xs">
          <div className="w-2 h-2 rounded-full" style={{ background: p.color }} />
          <span className="text-gray-400">{p.name}:</span>
          <span className="font-bold text-white">{p.value}</span>
        </div>
      ))}
    </div>
  );
}

// ── Delta Sigma Gauge ─────────────────────────────────────────────────────────
function DeltaGauge({ value, max = 4 }: { value: number; max?: number }) {
  const pct = Math.min(value / max, 1);
  const angle = -135 + pct * 270;
  const r = 60;
  const cx = 80, cy = 80;

  // Arc path
  const startAngle = -135 * (Math.PI / 180);
  const endAngle   = (angle) * (Math.PI / 180);
  const x1 = cx + r * Math.cos(startAngle);
  const y1 = cy + r * Math.sin(startAngle);
  const x2 = cx + r * Math.cos(endAngle);
  const y2 = cy + r * Math.sin(endAngle);
  const largeArc = pct > 0.5 ? 1 : 0;

  const color = value > 2 ? "#ef4444" : value > 1 ? "#f59e0b" : "#10b981";

  return (
    <div className="flex flex-col items-center">
      <svg width={160} height={100} viewBox="0 0 160 100">
        {/* Background arc */}
        <path
          d={`M ${cx + r * Math.cos(-135 * Math.PI / 180)} ${cy + r * Math.sin(-135 * Math.PI / 180)} A ${r} ${r} 0 1 1 ${cx + r * Math.cos(135 * Math.PI / 180)} ${cy + r * Math.sin(135 * Math.PI / 180)}`}
          fill="none" stroke="#1f2937" strokeWidth={12} strokeLinecap="round"
        />
        {/* Value arc */}
        {pct > 0 && (
          <path
            d={`M ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2}`}
            fill="none" stroke={color} strokeWidth={12} strokeLinecap="round"
          />
        )}
        {/* Glow */}
        {pct > 0 && (
          <path
            d={`M ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2}`}
            fill="none" stroke={color} strokeWidth={20} strokeLinecap="round" opacity={0.2}
          />
        )}
        {/* Center value */}
        <text x={cx} y={cy + 5} textAnchor="middle" fill={color} fontSize={20} fontWeight="bold">
          {value.toFixed(1)}
        </text>
        <text x={cx} y={cy + 20} textAnchor="middle" fill="#6b7280" fontSize={9}>
          δσ
        </text>
        {/* Labels */}
        <text x={20} y={95} fill="#6b7280" fontSize={8}>0</text>
        <text x={140} y={95} fill="#6b7280" fontSize={8}>{max}</text>
        <text x={cx - 5} y={18} fill="#ef4444" fontSize={8}>2.0</text>
      </svg>
      <p className="text-xs text-gray-500 -mt-2">
        {value > 2 ? "⚠️ Brecha crítica" : value > 1 ? "⚡ Brecha moderada" : "✓ Alineado"}
      </p>
    </div>
  );
}

// ── Score Ring ────────────────────────────────────────────────────────────────
function ScoreRing({ score, label, color }: { score: number; label: string; color: string }) {
  const r = 28;
  const circ = 2 * Math.PI * r;
  const pct = score / 100;
  const dash = pct * circ;

  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative">
        <svg width={72} height={72} viewBox="0 0 72 72">
          {/* Shadow */}
          <circle cx={36} cy={38} r={r} fill="none" stroke="#00000022" strokeWidth={8} />
          {/* Track */}
          <circle cx={36} cy={36} r={r} fill="none" stroke="#1f2937" strokeWidth={8} />
          {/* Progress */}
          <circle
            cx={36} cy={36} r={r}
            fill="none"
            stroke={color}
            strokeWidth={8}
            strokeDasharray={`${dash} ${circ}`}
            strokeLinecap="round"
            transform="rotate(-90 36 36)"
            style={{ filter: `drop-shadow(0 0 6px ${color}88)` }}
          />
          {/* Glow ring */}
          <circle
            cx={36} cy={36} r={r}
            fill="none"
            stroke={color}
            strokeWidth={14}
            strokeDasharray={`${dash} ${circ}`}
            strokeLinecap="round"
            transform="rotate(-90 36 36)"
            opacity={0.15}
          />
          <text x={36} y={40} textAnchor="middle" fill="white" fontSize={14} fontWeight="bold">
            {score}
          </text>
        </svg>
      </div>
      <p className="text-xs text-gray-400 text-center leading-tight">{label}</p>
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────
export function SurveyResultsChart({ stages }: { stages: any[] }) {
  const [activeTab, setActiveTab] = useState<"radar" | "bars" | "delta" | "scores">("radar");

  // Extract data from stages
  const scoringStage   = stages.find(s => s.tool_name === "g10a_scoring");
  const bayesianoStage = stages.find(s => s.tool_name === "g11a_bayesiano");
  const irrStage       = stages.find(s => s.tool_name === "irr_calculator");
  const psicometriaStage = stages.find(s => s.tool_name === "g10b_psicometria");

  const scoring   = scoringStage?.output?.output   ?? scoringStage?.output   ?? {};
  const bayesiano = bayesianoStage?.output?.output ?? bayesianoStage?.output ?? {};
  const irr       = irrStage?.output?.output       ?? irrStage?.output       ?? {};
  const psico     = psicometriaStage?.output?.output ?? psicometriaStage?.output ?? {};

  const dimScores: any[]  = scoring.dimension_scores ?? [];
  const roleScores: any   = scoring.role_scores ?? {};
  const deltaSigma: number = scoring.delta_sigma?.max_gap ?? 0;
  const overallScore: number = scoring.scoring_summary?.overall_score ?? 0;
  const benchmarkScore: number = scoring.scoring_summary?.benchmark_score ?? 0;

  if (dimScores.length === 0 && overallScore === 0) return null;

  // ── Radar data ──────────────────────────────────────────────────────────────
  const radarData = dimScores.map((d: any) => ({
    dimension: d.name?.length > 15 ? d.name.slice(0, 15) + "…" : (d.name ?? d.dimension),
    Estratégico: roleScores["Estratégico"]?.score ?? 0,
    Táctico:     roleScores["Táctico"]?.score ?? 0,
    Operativo:   roleScores["Operativo"]?.score ?? 0,
    Benchmark:   d.benchmark ?? benchmarkScore,
    score:       d.score ?? 0,
  }));

  // ── Bar data ────────────────────────────────────────────────────────────────
  const barData = dimScores.map((d: any, i: number) => ({
    name: d.name?.length > 12 ? d.name.slice(0, 12) + "…" : (d.name ?? `DIM-${i + 1}`),
    Score:     d.score ?? 0,
    Benchmark: d.benchmark ?? benchmarkScore,
    Gap:       Math.abs(d.gap ?? 0),
  }));

  // ── Role comparison ─────────────────────────────────────────────────────────
  const roleData = Object.entries(roleScores).map(([role, data]: [string, any]) => ({
    role,
    score: data.score ?? 0,
    perception: data.perception ?? "",
  }));

  const tabs = [
    { id: "radar",  label: "Radar Multi-Rol", icon: Target },
    { id: "bars",   label: "Dimensiones",     icon: BarChart2 },
    { id: "delta",  label: "Brecha δσ",       icon: Zap },
    { id: "scores", label: "Scores",          icon: Users },
  ] as const;

  return (
    <div className="bg-gray-950 rounded-2xl border border-gray-800 shadow-2xl overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-800 flex items-center justify-between">
        <div>
          <h3 className="font-bold text-white flex items-center gap-2">
            <BarChart2 size={18} className="text-brand-400" />
            Resultados de la Encuesta Multi-Rater
          </h3>
          <p className="text-xs text-gray-500 mt-0.5">
            Análisis psicométrico · {Object.keys(roleScores).length} roles · {dimScores.length} dimensiones
          </p>
        </div>
        {/* IRR badge */}
        {irr.krippendorff_alpha && (
          <div className="text-center">
            <p className={`text-lg font-black ${irr.krippendorff_alpha >= 0.70 ? "text-green-400" : "text-red-400"}`}>
              α {irr.krippendorff_alpha.toFixed(2)}
            </p>
            <p className="text-xs text-gray-500">Krippendorff</p>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-800">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex-1 flex items-center justify-center gap-1.5 py-3 text-xs font-semibold transition-all ${
              activeTab === tab.id
                ? "text-brand-400 border-b-2 border-brand-400 bg-brand-400/5"
                : "text-gray-500 hover:text-gray-300"
            }`}
          >
            <tab.icon size={13} />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Chart area */}
      <div className="p-6">

        {/* ── RADAR ── */}
        {activeTab === "radar" && radarData.length > 0 && (
          <div>
            <ResponsiveContainer width="100%" height={340}>
              <RadarChart data={radarData} margin={{ top: 10, right: 30, bottom: 10, left: 30 }}>
                <PolarGrid stroke="#374151" strokeDasharray="3 3" />
                <PolarAngleAxis
                  dataKey="dimension"
                  tick={{ fill: "#9ca3af", fontSize: 11 }}
                />
                <PolarRadiusAxis
                  angle={90}
                  domain={[0, 100]}
                  tick={{ fill: "#6b7280", fontSize: 9 }}
                  tickCount={5}
                />
                {/* Benchmark */}
                <Radar
                  name="Benchmark"
                  dataKey="Benchmark"
                  stroke="#6b7280"
                  fill="#6b7280"
                  fillOpacity={0.1}
                  strokeDasharray="5 5"
                  dot={false}
                />
                {/* Roles */}
                {Object.entries(ROLE_COLORS).map(([role, colors]) => (
                  <Radar
                    key={role}
                    name={role}
                    dataKey={role}
                    stroke={colors.stroke}
                    fill={colors.fill}
                    fillOpacity={0.25}
                    dot={<GlowDot fill={colors.fill} />}
                    strokeWidth={2}
                  />
                ))}
                <Legend
                  wrapperStyle={{ color: "#9ca3af", fontSize: 12 }}
                />
                <Tooltip content={<CustomTooltip />} />
              </RadarChart>
            </ResponsiveContainer>

            {/* Perception note */}
            {deltaSigma > 2 && (
              <div className="mt-3 bg-red-950 border border-red-800 rounded-xl p-3 text-xs text-red-300">
                ⚠️ Brecha de percepción crítica (δσ = {deltaSigma.toFixed(1)}) — La dirección y los operarios tienen visiones significativamente distintas del proceso.
              </div>
            )}
          </div>
        )}

        {/* ── BARS ── */}
        {activeTab === "bars" && barData.length > 0 && (
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={barData} margin={{ top: 20, right: 20, bottom: 20, left: 0 }} barGap={4}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
              <XAxis dataKey="name" tick={{ fill: "#9ca3af", fontSize: 10 }} axisLine={false} tickLine={false} />
              <YAxis domain={[0, 100]} tick={{ fill: "#6b7280", fontSize: 10 }} axisLine={false} tickLine={false} />
              <Tooltip content={<CustomTooltip />} cursor={{ fill: "#ffffff08" }} />
              <Legend wrapperStyle={{ color: "#9ca3af", fontSize: 12 }} />
              <ReferenceLine y={70} stroke="#6b7280" strokeDasharray="4 4" label={{ value: "Mín. aceptable", fill: "#6b7280", fontSize: 9 }} />
              <Bar dataKey="Score" shape={<Bar3D />}>
                {barData.map((_: any, i: number) => (
                  <Cell key={i} fill={DIM_COLORS[i % DIM_COLORS.length]} />
                ))}
              </Bar>
              <Bar dataKey="Benchmark" fill="#374151" radius={[4, 4, 0, 0]} opacity={0.6} />
            </BarChart>
          </ResponsiveContainer>
        )}

        {/* ── DELTA ── */}
        {activeTab === "delta" && (
          <div className="space-y-6">
            {/* Main gauge */}
            <div className="flex justify-center">
              <div className="text-center">
                <p className="text-xs text-gray-500 mb-3 uppercase tracking-wider">
                  Brecha de Percepción Máxima
                </p>
                <DeltaGauge value={deltaSigma} />
              </div>
            </div>

            {/* Gap pairs */}
            {scoring.delta_sigma?.gap_pairs?.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs text-gray-500 uppercase tracking-wider">Pares de Brecha</p>
                {scoring.delta_sigma.gap_pairs.map((gap: any, i: number) => {
                  const pct = Math.min((gap.delta / 4) * 100, 100);
                  const color = gap.delta > 2 ? "#ef4444" : gap.delta > 1 ? "#f59e0b" : "#10b981";
                  return (
                    <div key={i} className="bg-gray-900 rounded-xl p-3">
                      <div className="flex items-center justify-between mb-2">
                        <p className="text-xs text-gray-300 font-semibold">{gap.roles}</p>
                        <span className="text-xs font-black" style={{ color }}>
                          δ = {gap.delta?.toFixed(1)}
                        </span>
                      </div>
                      <div className="w-full bg-gray-800 rounded-full h-2">
                        <div
                          className="h-2 rounded-full transition-all"
                          style={{
                            width: `${pct}%`,
                            background: color,
                            boxShadow: `0 0 8px ${color}88`,
                          }}
                        />
                      </div>
                      {gap.dimension && (
                        <p className="text-xs text-gray-500 mt-1">{gap.dimension}</p>
                      )}
                    </div>
                  );
                })}
              </div>
            )}

            {/* Bayesian confirmed */}
            {bayesiano.confirmed_hypotheses?.length > 0 && (
              <div className="bg-gray-900 rounded-xl p-4">
                <p className="text-xs text-gray-500 uppercase tracking-wider mb-3">
                  Hipótesis Confirmadas (Bayesiano)
                </p>
                <div className="flex flex-wrap gap-2">
                  {bayesiano.confirmed_hypotheses.map((h: string) => (
                    <span key={h} className="px-2 py-1 bg-brand-500/20 text-brand-400 rounded-lg text-xs font-semibold border border-brand-500/30">
                      ✓ {h}
                    </span>
                  ))}
                </div>
                {bayesiano.rejected_hypotheses?.length > 0 && (
                  <div className="flex flex-wrap gap-2 mt-2">
                    {bayesiano.rejected_hypotheses.map((h: string) => (
                      <span key={h} className="px-2 py-1 bg-gray-800 text-gray-500 rounded-lg text-xs border border-gray-700">
                        ✗ {h}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* ── SCORES ── */}
        {activeTab === "scores" && (
          <div className="space-y-6">
            {/* Overall score */}
            <div className="flex justify-center gap-8">
              <ScoreRing score={overallScore} label="Score Global" color="#6366f1" />
              <ScoreRing score={benchmarkScore} label="Benchmark Sector" color="#6b7280" />
              {psico.cronbach_alpha_overall && (
                <ScoreRing
                  score={Math.round(psico.cronbach_alpha_overall * 100)}
                  label="α Cronbach"
                  color="#10b981"
                />
              )}
              {irr.krippendorff_alpha && (
                <ScoreRing
                  score={Math.round(irr.krippendorff_alpha * 100)}
                  label="α Krippendorff"
                  color="#0ea5e9"
                />
              )}
            </div>

            {/* Role scores */}
            {roleData.length > 0 && (
              <div className="space-y-3">
                <p className="text-xs text-gray-500 uppercase tracking-wider">Score por Rol</p>
                {roleData.map((r: any) => {
                  const colors = ROLE_COLORS[r.role as keyof typeof ROLE_COLORS] ?? { fill: "#6b7280", stroke: "#6b7280" };
                  const pct = r.score;
                  return (
                    <div key={r.role} className="bg-gray-900 rounded-xl p-3">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <div className="w-2 h-2 rounded-full" style={{ background: colors.fill }} />
                          <span className="text-sm font-semibold text-gray-200">{r.role}</span>
                          {r.perception && (
                            <span className="text-xs text-gray-500 italic">{r.perception}</span>
                          )}
                        </div>
                        <span className="text-lg font-black" style={{ color: colors.fill }}>
                          {r.score}
                        </span>
                      </div>
                      <div className="w-full bg-gray-800 rounded-full h-3 overflow-hidden">
                        <div
                          className="h-3 rounded-full transition-all duration-700"
                          style={{
                            width: `${pct}%`,
                            background: `linear-gradient(90deg, ${colors.stroke}, ${colors.fill})`,
                            boxShadow: `0 0 12px ${colors.fill}66`,
                          }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Dimension scores grid */}
            {dimScores.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs text-gray-500 uppercase tracking-wider">Dimensiones</p>
                <div className="grid grid-cols-2 gap-2">
                  {dimScores.map((d: any, i: number) => {
                    const color = DIM_COLORS[i % DIM_COLORS.length];
                    const pct = d.score ?? 0;
                    const gap = d.gap ?? 0;
                    return (
                      <div key={i} className="bg-gray-900 rounded-xl p-3">
                        <p className="text-xs text-gray-400 mb-1 truncate">{d.name ?? d.dimension}</p>
                        <div className="flex items-end gap-2">
                          <span className="text-xl font-black" style={{ color }}>{pct}</span>
                          <span className={`text-xs mb-0.5 ${gap < 0 ? "text-red-400" : "text-green-400"}`}>
                            {gap < 0 ? "▼" : "▲"} {Math.abs(gap)}
                          </span>
                        </div>
                        <div className="w-full bg-gray-800 rounded-full h-1.5 mt-1">
                          <div
                            className="h-1.5 rounded-full"
                            style={{
                              width: `${pct}%`,
                              background: color,
                              boxShadow: `0 0 6px ${color}88`,
                            }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
