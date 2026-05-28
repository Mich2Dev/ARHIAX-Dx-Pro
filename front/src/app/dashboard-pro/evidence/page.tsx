"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiPro } from "@/lib/api-pro";
import { formatDate } from "@/lib/utils";
import { Loader2, RefreshCw, ShieldCheck } from "lucide-react";

const EVENT_COLOR: Record<string, string> = {
  policy_decision:       '#9b6d4d',
  pmel_step_aggregate:   '#243c4f',
  diagnostic_evaluation: '#56624b',
  agent_artifact:        '#56624b',
  approval_action:       '#706f69',
};

export default function ProEvidencePage() {
  const [traceFilter, setTraceFilter] = useState("");

  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ["pro-evidence", traceFilter],
    queryFn: () => apiPro.get(`/pro/evidence${traceFilter ? `?trace_id=${traceFilter}` : ""}`).then(r => r.data),
  });

  const { data: verifyData, refetch: verify, isFetching: verifying } = useQuery({
    queryKey: ["pro-evidence-verify"],
    queryFn: () => apiPro.get("/pro/evidence/verify").then(r => r.data),
    enabled: false,
  });

  const entries: any[] = data?.entries ?? [];

  return (
    <div style={{ fontFamily: "Manrope, sans-serif" }}>
      {/* Header */}
      <div style={{ minHeight: "92px", display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "24px", borderBottom: "1px solid rgba(23,23,23,0.14)", paddingBottom: "20px" }}>
        <div>
          <p style={{ margin: 0, color: "#56624b", fontSize: "12px", fontFamily: "IBM Plex Mono, monospace" }}>§ evidence ledger</p>
          <h1 style={{ margin: "8px 0 0", fontFamily: "Cormorant Garamond, Georgia, serif", fontWeight: 500, fontSize: "52px", lineHeight: 0.96, color: "#171717" }}>
            Evidencia
          </h1>
          <p style={{ margin: "8px 0 0", fontSize: "14px", color: "#706f69" }}>Registro append-only gobernado PMEL/ATK</p>
        </div>
        <div style={{ display: "flex", gap: "10px" }}>
          <button
            onClick={() => verify()}
            disabled={verifying}
            style={{ display: "flex", alignItems: "center", gap: "6px", minHeight: "42px", border: "1px solid rgba(23,23,23,0.14)", padding: "9px 14px", background: "transparent", color: "#706f69", fontSize: "12px", fontFamily: "IBM Plex Mono, monospace", cursor: "pointer", opacity: verifying ? 0.5 : 1 }}
          >
            <ShieldCheck size={14} /> Verificar HMAC
          </button>
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            style={{ minHeight: "42px", border: "1px solid rgba(23,23,23,0.14)", padding: "9px 12px", background: "transparent", color: "#706f69", cursor: "pointer", opacity: isFetching ? 0.5 : 1 }}
          >
            <RefreshCw size={14} style={{ animation: isFetching ? "spin 1s linear infinite" : "none" }} />
          </button>
        </div>
      </div>

      {/* Verificación HMAC */}
      {verifyData && (
        <div style={{
          marginTop: "20px", padding: "16px 20px",
          border: `1px solid ${verifyData.valid ? "rgba(86,98,75,0.3)" : "rgba(139,58,58,0.3)"}`,
          borderLeft: `3px solid ${verifyData.valid ? "#56624b" : "#8b3a3a"}`,
          background: verifyData.valid ? "rgba(86,98,75,0.05)" : "rgba(139,58,58,0.05)",
        }}>
          <p style={{ margin: 0, fontSize: "12px", fontFamily: "IBM Plex Mono, monospace", color: verifyData.valid ? "#56624b" : "#8b3a3a", fontWeight: 500 }}>
            {verifyData.valid ? "✓ Cadena HMAC íntegra" : "✗ Cadena HMAC comprometida"}
            {verifyData.entries_checked != null && ` · ${verifyData.entries_checked} entradas verificadas`}
          </p>
        </div>
      )}

      {/* Filtro por trace */}
      <div style={{ marginTop: "24px", display: "flex", gap: "10px", alignItems: "center" }}>
        <input
          value={traceFilter}
          onChange={e => setTraceFilter(e.target.value)}
          placeholder="Filtrar por trace ID..."
          style={{ flex: 1, maxWidth: "400px", minHeight: "42px", border: "1px solid rgba(23,23,23,0.14)", padding: "9px 14px", background: "transparent", color: "#171717", fontFamily: "IBM Plex Mono, monospace", fontSize: "12px", outline: "none" }}
        />
        {traceFilter && (
          <button onClick={() => setTraceFilter("")} style={{ fontSize: "12px", fontFamily: "IBM Plex Mono, monospace", color: "#706f69", background: "transparent", border: "none", cursor: "pointer" }}>
            Limpiar
          </button>
        )}
      </div>

      {/* Tabla */}
      <div style={{ marginTop: "20px", background: "rgba(244,241,234,0.96)", border: "1px solid rgba(23,23,23,0.14)" }}>
        <div style={{ padding: "16px 24px", borderBottom: "1px solid rgba(23,23,23,0.14)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <p style={{ margin: 0, fontSize: "11px", fontFamily: "IBM Plex Mono, monospace", color: "#706f69", fontWeight: 500 }}>
            ENTRADAS · {entries.length}
          </p>
        </div>

        {isLoading ? (
          <div style={{ display: "flex", justifyContent: "center", padding: "48px 0" }}>
            <Loader2 size={20} style={{ color: "#706f69", animation: "spin 1s linear infinite" }} />
          </div>
        ) : entries.length === 0 ? (
          <p style={{ padding: "32px 24px", color: "#706f69", fontSize: "13px", fontFamily: "IBM Plex Mono, monospace" }}>
            Sin entradas de evidencia.
          </p>
        ) : (
          <>
            <div style={{ display: "grid", gridTemplateColumns: "160px 1fr 120px 100px", gap: "16px", padding: "10px 24px", borderBottom: "1px solid rgba(23,23,23,0.14)", fontSize: "10px", fontFamily: "IBM Plex Mono, monospace", color: "#706f69", fontWeight: 500 }}>
              <span>TIPO</span><span>TRACE ID</span><span>OUTCOME</span><span>FECHA</span>
            </div>
            {entries.map((e: any, i: number) => (
              <div key={i} style={{ display: "grid", gridTemplateColumns: "160px 1fr 120px 100px", gap: "16px", padding: "14px 24px", alignItems: "center", borderBottom: "1px solid rgba(23,23,23,0.07)" }}>
                <span style={{
                  fontSize: "10px", fontFamily: "IBM Plex Mono, monospace", fontWeight: 500,
                  color: EVENT_COLOR[e.event_type] ?? "#706f69",
                }}>
                  {e.event_type}
                </span>
                <span style={{ fontSize: "11px", fontFamily: "IBM Plex Mono, monospace", color: "#706f69", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {e.trace_id ?? "—"}
                </span>
                <span style={{
                  fontSize: "10px", fontFamily: "IBM Plex Mono, monospace",
                  color: e.outcome === "PERMIT" ? "#56624b" : e.outcome ? "#9b6d4d" : "#706f69",
                }}>
                  {e.outcome ?? "—"}
                </span>
                <span style={{ fontSize: "11px", color: "#706f69" }}>{formatDate(e.created_at)}</span>
              </div>
            ))}
          </>
        )}
      </div>
    </div>
  );
}
