"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Plus, Download, Loader2, CheckCircle, FileText } from "lucide-react";
import { DiagnosticTable } from "@/components/features/dashboard/DiagnosticTable";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { useDownloadDiagnostic } from "@/hooks/useDownload";

type Filter = "all" | "completed" | "running" | "denied";

export default function DashboardPage() {
  const [filter, setFilter] = useState<Filter>("all");

  const { data: stats } = useQuery({
    queryKey: ["stats"],
    queryFn: () => api.get("/v2/diagnostics/stats").then((r) => r.data),
    refetchInterval: 10000,
  });

  const { data: diagnostics, isLoading } = useQuery({
    queryKey: ["diagnostics"],
    queryFn: () => api.get("/v2/diagnostics").then((r) => r.data),
    refetchInterval: 5000,
  });

  const all: any[] = diagnostics?.items ?? [];

  const filtered = filter === "all"
    ? all
    : all.filter(d => {
        if (filter === "completed") return d.status === "completed" || d.status === "awaiting_review";
        if (filter === "running")   return d.status === "running" || d.status === "pending" || d.status === "awaiting_responses";
        if (filter === "denied")    return d.status === "denied" || d.status === "failed";
        return true;
      });

  const completedCount = all.filter(d => d.status === "completed").length;
  const runningCount   = all.filter(d => ["running","pending","awaiting_responses"].includes(d.status)).length;

  return (
    <div style={{ fontFamily: 'Manrope, sans-serif' }}>
      {/* Header */}
      <div style={{
        minHeight: '92px',
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'space-between',
        gap: '24px',
        borderBottom: '1px solid rgba(23, 23, 23, 0.14)',
        paddingBottom: '20px',
      }}>
        <div>
          <p style={{ margin: 0, color: '#9b6d4d', fontSize: '12px', fontFamily: 'IBM Plex Mono, monospace' }}>
            § 01 · panel principal
          </p>
          <h1 style={{
            margin: '8px 0 0',
            fontFamily: 'Cormorant Garamond, Georgia, serif',
            fontWeight: 500,
            fontSize: '52px',
            lineHeight: 0.96,
            color: '#171717',
          }}>Diagnósticos</h1>
          <p style={{ margin: '8px 0 0', fontSize: '14px', color: '#706f69' }}>
            Diagnósticos organizacionales gobernados
          </p>
        </div>
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
          Nuevo Diagnóstico
        </Link>
      </div>

      {/* Stats */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: '1px',
        marginTop: '28px',
        background: 'rgba(23, 23, 23, 0.14)',
      }}>
        {[
          { label: 'Activos', value: stats?.running ?? 0, color: '#243c4f' },
          { label: 'En encuesta', value: stats?.awaiting_review ?? 0, color: '#9b6d4d' },
          { label: 'Completados', value: stats?.completed ?? 0, color: '#56624b' },
          { label: 'Denegados', value: stats?.denied ?? 0, color: '#706f69' },
        ].map(({ label, value, color }) => (
          <div key={label} style={{
            minHeight: '94px',
            background: 'rgba(244, 241, 234, 0.96)',
            padding: '14px',
          }}>
            <dt style={{ color: '#706f69', fontSize: '11px', fontFamily: 'IBM Plex Mono, monospace' }}>{label}</dt>
            <dd style={{ margin: '12px 0 0', fontSize: '32px', fontWeight: 500, color }}>{value}</dd>
          </div>
        ))}
      </div>

      {/* Completed — quick access */}
      {completedCount > 0 && (
        <div style={{
          marginTop: '28px',
          border: '1px solid rgba(86, 98, 75, 0.3)',
          borderLeft: '3px solid #56624b',
          padding: '20px',
          background: 'rgba(86, 98, 75, 0.05)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <CheckCircle size={16} style={{ color: '#56624b' }} />
              <h2 style={{
                margin: 0,
                fontFamily: 'IBM Plex Mono, monospace',
                fontSize: '12px',
                fontWeight: 500,
                color: '#222522',
              }}>
                {completedCount} diagnóstico{completedCount > 1 ? "s" : ""} listo{completedCount > 1 ? "s" : ""} para descargar
              </h2>
            </div>
            <button
              onClick={() => setFilter(filter === "completed" ? "all" : "completed")}
              style={{
                fontSize: '11px',
                fontFamily: 'IBM Plex Mono, monospace',
                color: '#56624b',
                fontWeight: 500,
                background: 'transparent',
                border: 'none',
                cursor: 'pointer',
                textDecoration: 'underline',
              }}
            >
              {filter === "completed" ? "Ver todos" : "Ver solo completados →"}
            </button>
          </div>
          <div style={{ display: 'grid', gap: '1px', background: 'rgba(23, 23, 23, 0.14)' }}>
            {all
              .filter(d => d.status === "completed")
              .slice(0, 3)
              .map(d => (
                <div key={d.id} style={{
                  background: '#f4f1ea',
                  padding: '14px 16px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: '16px',
                }}>
                  <div style={{ minWidth: 0 }}>
                    <p style={{
                      margin: 0,
                      fontFamily: 'IBM Plex Mono, monospace',
                      fontSize: '13px',
                      fontWeight: 500,
                      color: '#171717',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}>{d.organization_name}</p>
                    <p style={{
                      margin: '4px 0 0',
                      fontSize: '11px',
                      color: '#706f69',
                    }}>{d.domain} · {formatDate(d.created_at)}</p>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
                    <Link
                      href={`/dashboard/diagnostics/${d.id}`}
                      style={{
                        fontSize: '11px',
                        fontFamily: 'IBM Plex Mono, monospace',
                        color: '#9b6d4d',
                        fontWeight: 500,
                        textDecoration: 'none',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px',
                      }}
                    >
                      <FileText size={12} /> Ver resultados
                    </Link>
                    <DownloadButton diagnosticId={d.id} orgName={d.organization_name} />
                  </div>
                </div>
              ))}
            {completedCount > 3 && (
              <button
                onClick={() => setFilter("completed")}
                style={{
                  width: '100%',
                  fontSize: '11px',
                  fontFamily: 'IBM Plex Mono, monospace',
                  color: '#56624b',
                  fontWeight: 500,
                  padding: '8px',
                  background: 'transparent',
                  border: 'none',
                  cursor: 'pointer',
                  textDecoration: 'underline',
                }}
              >
                Ver {completedCount - 3} más →
              </button>
            )}
          </div>
        </div>
      )}

      {/* Running — if any */}
      {runningCount > 0 && (
        <div style={{
          marginTop: '28px',
          border: '1px solid rgba(36, 60, 79, 0.3)',
          borderLeft: '3px solid #243c4f',
          padding: '16px 20px',
          background: 'rgba(36, 60, 79, 0.05)',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
        }}>
          <Loader2 size={14} style={{ color: '#243c4f', animation: 'spin 1s linear infinite' }} />
          <p style={{
            margin: 0,
            fontSize: '12px',
            fontFamily: 'IBM Plex Mono, monospace',
            color: '#222522',
            fontWeight: 500,
          }}>
            {runningCount} diagnóstico{runningCount > 1 ? "s" : ""} en ejecución — esta pantalla se actualiza automáticamente.
          </p>
        </div>
      )}

      {/* Filter tabs + table */}
      <div style={{
        marginTop: '28px',
        background: 'rgba(244, 241, 234, 0.96)',
        border: '1px solid rgba(23, 23, 23, 0.14)',
      }}>
        <div style={{
          padding: '20px 24px',
          borderBottom: '1px solid rgba(23, 23, 23, 0.14)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '16px',
        }}>
          <h2 style={{
            margin: 0,
            fontFamily: 'IBM Plex Mono, monospace',
            fontSize: '12px',
            fontWeight: 500,
            color: '#222522',
          }}>Todos los diagnósticos</h2>
          <div style={{ display: 'flex', gap: '4px' }}>
            {([
              { key: "all",       label: "Todos" },
              { key: "running",   label: "En curso" },
              { key: "completed", label: "Completados" },
              { key: "denied",    label: "Denegados" },
            ] as { key: Filter; label: string }[]).map(tab => (
              <button
                key={tab.key}
                onClick={() => setFilter(tab.key)}
                style={{
                  padding: '6px 12px',
                  fontSize: '11px',
                  fontFamily: 'IBM Plex Mono, monospace',
                  fontWeight: 500,
                  border: filter === tab.key ? '1px solid #171717' : '1px solid rgba(23, 23, 23, 0.14)',
                  background: filter === tab.key ? '#171717' : 'transparent',
                  color: filter === tab.key ? '#f4f1ea' : '#706f69',
                  cursor: 'pointer',
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
        <DiagnosticTable diagnostics={filtered} isLoading={isLoading} />
      </div>
    </div>
  );
}

// ── Download button usando hook reutilizable ──────────────────────────────────
function DownloadButton({ diagnosticId, orgName }: { diagnosticId: string; orgName: string }) {
  const { download, loading } = useDownloadDiagnostic();

  return (
    <button
      onClick={() => download(diagnosticId, orgName)}
      disabled={loading}
      style={{
        display: 'flex', alignItems: 'center', gap: '4px',
        fontSize: '11px', fontFamily: 'IBM Plex Mono, monospace',
        minHeight: '32px', border: '1px solid #56624b', padding: '6px 10px',
        background: loading ? 'rgba(86,98,75,0.1)' : '#56624b',
        color: loading ? '#706f69' : '#f4f1ea',
        fontWeight: 500, cursor: loading ? 'not-allowed' : 'pointer',
        opacity: loading ? 0.5 : 1,
      }}
    >
      {loading ? <Loader2 size={11} style={{ animation: 'spin 1s linear infinite' }} /> : <Download size={11} />}
      PDF
    </button>
  );
}
