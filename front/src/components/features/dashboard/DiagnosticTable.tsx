"use client";

// Imports from Next.js and UI components
import Link from "next/link";
import { useTranslations } from "next-intl";
import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";
import { Loader2 } from "lucide-react";

// Imports from lib utilities and types
import { formatDate, decisionVariant, statusVariant, statusLabel } from "@/lib/utils";
import type { DiagnosticSummary } from "@/lib/types";

// Imports from config constants
import { STATUS_LABELS, DECISION_LABELS } from "@/config/constants";

export function DiagnosticTable({
  diagnostics,
  isLoading,
}: {
  diagnostics: DiagnosticSummary[];
  isLoading: boolean;
}) {
  if (isLoading) {
    return <div className="flex justify-center py-12"><Spinner /></div>;
  }

  if (!diagnostics.length) {
    return (
      <div className="text-center py-16 space-y-2">
        <p className="text-gray-400 text-sm">No hay diagnósticos aún</p>
        <Link href="/dashboard/diagnostics/new"
          className="inline-block text-sm text-brand-500 hover:text-brand-600 font-medium">
          Crear el primero →
        </Link>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-gray-400 border-b border-gray-100">
            <th className="px-6 py-3 font-semibold">Empresa</th>
            <th className="px-6 py-3 font-semibold">Área</th>
            <th className="px-6 py-3 font-semibold">Estado</th>
            <th className="px-6 py-3 font-semibold">Decisión</th>
            <th className="px-6 py-3 font-semibold">Creado</th>
            <th className="px-6 py-3"></th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-50">
          {diagnostics.map((d) => (
            <tr key={d.id} className="hover:bg-gray-50 transition-colors group">
              <td className="px-6 py-3.5">
                <div className="flex items-center gap-2">
                  {(d.status === "running" || d.status === "pending") && (
                    <Loader2 size={12} className="text-blue-400 animate-spin shrink-0" />
                  )}
                  <span className="font-semibold text-gray-900">{d.organization_name}</span>
                </div>
              </td>
              <td className="px-6 py-3.5 text-gray-500">{d.domain}</td>
              <td className="px-6 py-3.5">
                <Badge variant={statusVariant(d.status)}>
                  {STATUS_LABELS[d.status] ?? d.status}
                </Badge>
              </td>
              <td className="px-6 py-3.5">
                {d.decision && (
                  <Badge variant={decisionVariant(d.decision)}>
                    {DECISION_LABELS[d.decision] ?? d.decision}
                  </Badge>
                )}
              </td>
              <td className="px-6 py-3.5 text-gray-400 text-xs">{formatDate(d.created_at)}</td>
              <td className="px-6 py-3.5">
                <Link
                  href={`/dashboard/diagnostics/${d.id}`}
                  className="text-brand-500 hover:text-brand-600 font-medium opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  Ver →
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
