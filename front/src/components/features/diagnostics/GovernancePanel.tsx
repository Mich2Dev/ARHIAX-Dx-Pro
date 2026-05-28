"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { CheckCircle, XCircle, AlertTriangle, Info, ChevronDown, ChevronUp, ShieldCheck } from "lucide-react";
import type { RuleResult } from "@/lib/types";

const OUTCOME_CONFIG = {
  PASS:     { icon: CheckCircle,   color: "text-green-500",  bg: "bg-green-50",  border: "border-green-100" },
  FAIL:     { icon: XCircle,       color: "text-red-500",    bg: "bg-red-50",    border: "border-red-100" },
  ESCALATE: { icon: AlertTriangle, color: "text-orange-500", bg: "bg-orange-50", border: "border-orange-100" },
  LOG_ONLY: { icon: Info,          color: "text-blue-500",   bg: "bg-blue-50",   border: "border-blue-100" },
};

export function GovernancePanel({
  rules,
  decision,
}: {
  rules: RuleResult[];
  decision?: string;
}) {
  const t = useTranslations("governance");
  const [expanded, setExpanded] = useState(false);

  const preflight = rules.slice(0, 13);
  const execution = rules.slice(13);

  const passCount = rules.filter(r => r.outcome === "PASS").length;
  const failCount = rules.filter(r => r.outcome === "FAIL").length;
  const escalateCount = rules.filter(r => r.outcome === "ESCALATE").length;

  const decisionColor =
    decision === "ALLOW" ? "bg-green-500" :
    decision === "DENY"  ? "bg-red-500" :
    "bg-orange-500";

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-gray-100">
        <div className="flex items-center gap-2 mb-3">
          <ShieldCheck size={16} className="text-brand-500" />
          <h3 className="font-semibold text-gray-800 text-sm">{t("title")}</h3>
        </div>

        {/* Decision badge */}
        {decision && (
          <div className={`flex items-center gap-2 px-3 py-2 rounded-xl text-white text-xs font-bold ${decisionColor}`}>
            <div className="w-2 h-2 rounded-full bg-white/50" />
            {t("decision")}: {decision}
          </div>
        )}

        {/* Summary counts */}
        <div className="grid grid-cols-3 gap-2 mt-3">
          <div className="text-center bg-green-50 rounded-lg py-1.5">
            <p className="text-lg font-black text-green-600">{passCount}</p>
            <p className="text-xs text-green-500">OK</p>
          </div>
          <div className="text-center bg-red-50 rounded-lg py-1.5">
            <p className="text-lg font-black text-red-600">{failCount}</p>
            <p className="text-xs text-red-500">Fallo</p>
          </div>
          <div className="text-center bg-orange-50 rounded-lg py-1.5">
            <p className="text-lg font-black text-orange-600">{escalateCount}</p>
            <p className="text-xs text-orange-500">Escala</p>
          </div>
        </div>
      </div>

      {/* Toggle button */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-2.5 text-xs font-semibold text-gray-500 hover:bg-gray-50 transition-colors"
      >
        <span>{expanded ? "Ocultar reglas" : `Ver ${rules.length} reglas`}</span>
        {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
      </button>

      {/* Rules list — collapsible */}
      {expanded && (
        <div className="px-4 pb-4 space-y-3 max-h-96 overflow-y-auto">
          <RuleGroup title={t("preflight")} rules={preflight} />
          {execution.length > 0 && <RuleGroup title={t("execution")} rules={execution} />}
        </div>
      )}
    </div>
  );
}

function RuleGroup({ title, rules }: { title: string; rules: RuleResult[] }) {
  return (
    <div>
      <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-1.5 mt-2">{title}</p>
      <div className="space-y-1">
        {rules.map((rule) => {
          const cfg = OUTCOME_CONFIG[rule.outcome as keyof typeof OUTCOME_CONFIG] ?? OUTCOME_CONFIG.LOG_ONLY;
          const Icon = cfg.icon;
          return (
            <div
              key={rule.rule_id}
              className={`flex items-start gap-2 text-xs py-1.5 px-2 rounded-lg border ${cfg.bg} ${cfg.border}`}
            >
              <Icon size={12} className={`${cfg.color} shrink-0 mt-0.5`} />
              <div className="flex-1 min-w-0">
                <span className="font-mono text-gray-400 mr-1 text-[10px]">{rule.rule_id}</span>
                <span className="text-gray-600 leading-tight">{rule.message}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
