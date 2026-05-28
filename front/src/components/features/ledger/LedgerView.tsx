"use client";

import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api";
import { Spinner } from "@/components/ui/Spinner";
import { Badge } from "@/components/ui/Badge";
import { decisionVariant, formatDate } from "@/lib/utils";

export function LedgerView() {
  const t = useTranslations();

  const { data, isLoading } = useQuery({
    queryKey: ["ledger"],
    queryFn: () => api.get("/v2/ledger").then((r) => r.data),
  });

  const entries = data?.items ?? [];

  return (
    <div className="max-w-4xl mx-auto space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Ledger de Evidencia</h1>
        <span className="text-sm text-gray-400">{data?.total ?? 0} entradas</span>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="flex justify-center py-12"><Spinner /></div>
        ) : entries.length === 0 ? (
          <p className="text-center text-gray-400 py-12 text-sm">Sin entradas</p>
        ) : (
          <div className="divide-y divide-gray-50">
            {entries.map((entry: any) => (
              <div key={entry.entry_hash} className="px-5 py-4 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-800">{entry.organization_name ?? entry.client_id}</span>
                  <div className="flex items-center gap-2">
                    <Badge variant={decisionVariant(entry.decision)}>{entry.decision}</Badge>
                    <span className="text-xs text-gray-400">{formatDate(entry.timestamp)}</span>
                  </div>
                </div>
                <div className="font-mono text-xs text-gray-400 space-y-0.5">
                  <p>hash: {entry.entry_hash?.slice(0, 48)}…</p>
                  <p>prev: {entry.previous_hash?.slice(0, 48)}{entry.previous_hash?.length > 48 ? "…" : ""}</p>
                </div>
                {entry.reasons?.length > 0 && (
                  <ul className="text-xs text-red-600 space-y-0.5">
                    {entry.reasons.map((r: string, i: number) => <li key={i}>· {r}</li>)}
                  </ul>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
