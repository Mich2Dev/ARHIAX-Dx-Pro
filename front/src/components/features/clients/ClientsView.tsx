"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { Spinner } from "@/components/ui/Spinner";
import { Badge } from "@/components/ui/Badge";
import { PageHeader } from "@/components/layout/PageHeader";
import { formatDate, statusVariant, statusLabel, decisionVariant } from "@/lib/utils";
import { Building2, ChevronRight, Plus } from "lucide-react";

export function ClientsView() {
  const router = useRouter();
  const [selected, setSelected] = useState<string | null>(null);

  const { data: clients, isLoading } = useQuery({
    queryKey: ["clients"],
    queryFn: () => api.get("/v2/diagnostics/clients").then(r => r.data),
  });

  const { data: history } = useQuery({
    queryKey: ["client-history", selected],
    queryFn: () => api.get(`/v2/diagnostics?client_id=${selected}&limit=20`).then(r => r.data),
    enabled: !!selected,
  });

  const clientList = clients?.items ?? [];
  const selectedClient = clientList.find((c: any) => c.client_id === selected);

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
      <PageHeader
        title="Clientes"
        subtitle="historial de diagnósticos"
        code="§ 03"
        actions={
          <Link
            href="/dashboard/diagnostics/new"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              minHeight: '42px',
              border: '1px solid #171717',
              padding: '9px 14px',
              background: '#171717',
              color: '#f4f1ea',
              fontSize: '12px',
              fontFamily: 'IBM Plex Mono, monospace',
              textDecoration: 'none',
              cursor: 'pointer',
            }}
          >
            <Plus size={14} />
            Nuevo cliente
          </Link>
        }
      />

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '1px', background: 'rgba(23, 23, 23, 0.14)' }}>
        {/* Client list */}
        <div style={{ background: 'rgba(244, 241, 234, 0.96)', padding: '24px' }}>
          {isLoading ? (
            <div style={{ display: 'flex', justifyContent: 'center', padding: '32px 0' }}><Spinner /></div>
          ) : clientList.length === 0 ? (
            <div className="bg-white rounded-2xl border border-gray-200 p-8 text-center">
              <Building2 size={32} className="text-gray-200 mx-auto mb-2" />
              <p className="text-sm text-gray-400">Sin clientes aún</p>
            </div>
          ) : (
            clientList.map((c: any) => (
              <button
                key={c.client_id}
                onClick={() => setSelected(c.client_id)}
                className={`w-full text-left p-4 rounded-xl border transition-all ${
                  selected === c.client_id
                    ? "border-brand-400 bg-brand-50 shadow-sm"
                    : "border-gray-100 bg-white hover:border-gray-200"
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="font-semibold text-gray-900 text-sm truncate">
                      {c.organization_name}
                    </p>
                    <p className="text-xs text-gray-400 mt-0.5 truncate">{c.legal_name}</p>
                  </div>
                  <div className="flex flex-col items-end gap-1 shrink-0">
                    <span className="text-xs font-bold text-brand-600 bg-brand-100 px-1.5 py-0.5 rounded">
                      {c.total_diagnostics}
                    </span>
                    <ChevronRight size={12} className="text-gray-300" />
                  </div>
                </div>
                <p className="text-xs text-gray-400 mt-2">{formatDate(c.last_diagnostic)}</p>
              </button>
            ))
          )}
        </div>

        {/* History panel */}
        <div style={{ background: 'rgba(244, 241, 234, 0.96)', minHeight: '400px' }}>
          {!selected ? (
            <div className="bg-white rounded-2xl border border-gray-200 p-12 text-center">
              <Building2 size={40} className="text-gray-200 mx-auto mb-3" />
              <p className="text-gray-400 text-sm">Selecciona un cliente para ver su historial</p>
            </div>
          ) : (
            <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
              <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
                <div>
                  <h2 className="font-bold text-gray-900">{selectedClient?.organization_name}</h2>
                  <p className="text-xs text-gray-400 mt-0.5">
                    {selectedClient?.total_diagnostics} diagnóstico{selectedClient?.total_diagnostics !== 1 ? "s" : ""}
                  </p>
                </div>
                <button
                  onClick={() => {
                    const params = new URLSearchParams({ client: selectedClient?.client_id ?? "" });
                    router.push(`/dashboard/diagnostics/new?${params.toString()}`);
                  }}
                  className="flex items-center gap-1.5 bg-brand-500 hover:bg-brand-600 text-white text-xs font-semibold px-3 py-2 rounded-lg transition-colors"
                >
                  <Plus size={13} /> Nuevo diagnóstico
                </button>
              </div>

              {!history ? (
                <div className="flex justify-center py-8"><Spinner /></div>
              ) : (
                <div className="divide-y divide-gray-50">
                  {history.items?.map((d: any) => (
                    <div key={d.id} className="px-5 py-4 flex items-center gap-4 hover:bg-gray-50">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-800">{d.domain}</p>
                        <p className="text-xs text-gray-400 mt-0.5">{formatDate(d.created_at)}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant={statusVariant(d.status)}>
                          {statusLabel(d.status)}
                        </Badge>
                        {d.decision && (
                          <Badge variant={decisionVariant(d.decision)}>
                            {d.decision === "ALLOW" ? "Aprobado" : d.decision}
                          </Badge>
                        )}
                        <Link
                          href={`/dashboard/diagnostics/${d.id}`}
                          className="text-brand-500 hover:text-brand-600 text-xs font-medium"
                        >
                          Ver →
                        </Link>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
