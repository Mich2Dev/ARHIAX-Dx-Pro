"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Plus, Loader2, RefreshCw, Clock, CheckCircle } from "lucide-react";
import { apiPro } from "@/lib/api-pro";
import { formatDate } from "@/lib/utils";

type Filter = "all" | "running" | "review_pending" | "approved" | "rejected";

const S_COLOR: Record<string, string> = {
  draft: "#706f69", designing: "#4a5568", survey_open: "#2d6a4f",
  running: "#243c4f", review_pending: "#9b6d4d",
  approved: "#56624b", published: "#56624b", rejected: "#8b3a3a",
};
const S_LABEL: Record<string, string> = {
  draft: "Borrador", designing: "Configurando", survey_open: "Recolección",
  running: "Ejecutando", review_pending: "En revisión",
  approved: "Aprobado", published: "Publicado", rejected: "Rechazado",
};

export default function ProCasesPage() {
  const [filter, setFilter] = useState<Filter>("all");

  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ["pro-cases"],
    queryFn: () => apiPro.get("/pro/cases").then(r => r.data),
    refetchInterval: 8000,
  });

  const all: any[] = data?.items ?? [];
  const filtered = filter === "all" ? all : all.filter(c => {
    if (filter === "running")        return ["running", "survey_open", "designing"].includes(c.case_status);
    if (filter === "review_pending") return c.case_status === "review_pending";
    if (filter === "approved")       return ["approved", "published"].includes(c.case_status);
    if (filter === "rejected")       return c.case_status === "rejected";
    return true;
  });

  const runningCount  = all.filter(c => ["running", "survey_open", "designing"].includes(c.case_status)).length;
  const reviewCount   = all.filter(c => c.case_status === "review_pending").length;
  const doneCount     = all.filter(c => ["approved", "published"].includes(c.case_status)).length;

  return (
    <div>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "24px", paddingBottom: "24px", borderBottom: "1px solid rgba(23,23,23,0.12)" }}>
        <div>
          <p style={{ margin: 0, fontSize: "11px", fontFamily: "IBM Plex Mono, monospace", color: "#56624b", letterSpacing: "0.06em" }}>§ 01 · casos gobernados</p>
          <h1 style={{ margin: "6px 0 0", fontFamily: "Cormorant Garamond, Georgia, serif", fontWeight: 500, fontSize: "56px", lineHeight: 0.92, color: "#171717" }}>
            Casos Pro
          </h1>
          <p style={{ margin: "10px 0 0", fontSize: "13px", color: "#706f69" }}>Ciclo diagnóstico gobernado PMEL/ATK · evidence ledger HMAC</p>
        </div>
        <div style={{ display: "flex", gap: "8px", alignItems: "center", paddingTop: "8px" }}>
          <button onClick={() => refetch()} disabled={isFetching} style={{
            width: "38px", height: "38px", display: "flex", alignItems: "center", justifyContent: "center",
            border: "1px solid rgba(23,23,23,0.14)", background: "transparent", color: "#706f69",
            cursor: "pointer", opacity: isFetching ? 0.4 : 1,
          }}>
            <RefreshCw size={13} style={{ animation: isFetching ? "spin 1s linear infinite" : "none" }} />
          </button>
          <Link href="/dashboard-pro/new" style={{
            display: "flex", alignItems: "center", gap: "7px", height: "38px",
            padding: "0 16px", background: "#171717", color: "#f4f1ea",
            fontSize: "12px", fontFamily: "IBM Plex Mono, monospace", textDecoration: "none",
            border: "1px solid #171717",
          }}>
            <Plus size={13} /> Nuevo caso
          </Link>
        </div>
      </div>

      {/* Stats */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: "1px", marginTop: "24px", background: "rgba(23,23,23,0.12)" }}>
        {[
          { label: "Total",       value: all.length,    color: "#171717" },
          { label: "Ejecutando",  value: runningCount,  color: "#243c4f" },
          { label: "En revisión", value: reviewCount,   color: "#9b6d4d" },
          { label: "Completados", value: doneCount,     color: "#56624b" },
        ].map(({ label, value, color }) => (
          <div key={label} style={{ background: "rgba(244,241,234,0.96)", padding: "16px 20px" }}>
            <p style={{ margin: 0, fontSize: "10px", fontFamily: "IBM Plex Mono, monospace", color: "#706f69", letterSpacing: "0.06em" }}>{label.toUpperCase()}</p>
            <p style={{ margin: "8px 0 0", fontSize: "36px", fontWeight: 500, color, lineHeight: 1, fontFamily: "Cormorant Garamond, serif" }}>{value}</p>
          </div>
        ))}
      </div>

      {/* Banner revisiones pendientes */}
      {reviewCount > 0 && (
        <div style={{ marginTop: "20px", padding: "16px 20px", border: "1px solid rgba(155,109,77,0.3)", borderLeft: "3px solid #9b6d4d", background: "rgba(155,109,77,0.04)", display: "flex", alignItems: "center", justifyContent: "space-between", gap: "16px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <Clock size={14} style={{ color: "#9b6d4d" }} />
            <p style={{ margin: 0, fontSize: "12px", fontFamily: "IBM Plex Mono, monospace", color: "#222522", fontWeight: 500 }}>
              {reviewCount} caso{reviewCount > 1 ? "s" : ""} esperando aprobación HIL
            </p>
          </div>
          <Link href="/dashboard-pro/reviews" style={{ fontSize: "11px", fontFamily: "IBM Plex Mono, monospace", color: "#9b6d4d", fontWeight: 500, textDecoration: "none" }}>
            Ver revisiones →
          </Link>
        </div>
      )}

      {/* Banner ejecutando */}
      {runningCount > 0 && (
        <div style={{ marginTop: "12px", padding: "14px 20px", border: "1px solid rgba(36,60,79,0.25)", borderLeft: "3px solid #243c4f", background: "rgba(36,60,79,0.04)", display: "flex", alignItems: "center", gap: "10px" }}>
          <Loader2 size={13} style={{ color: "#243c4f", animation: "spin 1s linear infinite" }} />
          <p style={{ margin: 0, fontSize: "12px", fontFamily: "IBM Plex Mono, monospace", color: "#243c4f", fontWeight: 500 }}>
            {runningCount} caso{runningCount > 1 ? "s" : ""} ejecutando el ciclo de fusión — actualizando automáticamente.
          </p>
        </div>
      )}

      {/* Tabla */}
      <div style={{ marginTop: "24px", background: "rgba(244,241,234,0.96)", border: "1px solid rgba(23,23,23,0.12)" }}>
        {/* Toolbar */}
        <div style={{ padding: "16px 20px", borderBottom: "1px solid rgba(23,23,23,0.08)", display: "flex", alignItems: "center", justifyContent: "space-between", gap: "16px" }}>
          <p style={{ margin: 0, fontSize: "11px", fontFamily: "IBM Plex Mono, monospace", color: "#706f69", fontWeight: 500 }}>
            TODOS LOS CASOS
          </p>
          <div style={{ display: "flex", gap: "3px" }}>
            {([
              { key: "all",             label: "Todos" },
              { key: "running",         label: "Activos" },
              { key: "review_pending",  label: "En revisión" },
              { key: "approved",        label: "Aprobados" },
              { key: "rejected",        label: "Rechazados" },
            ] as { key: Filter; label: string }[]).map(tab => (
              <button key={tab.key} onClick={() => setFilter(tab.key)} style={{
                padding: "5px 10px", fontSize: "11px", fontFamily: "IBM Plex Mono, monospace",
                border: filter === tab.key ? "1px solid #171717" : "1px solid rgba(23,23,23,0.12)",
                background: filter === tab.key ? "#171717" : "transparent",
                color: filter === tab.key ? "#f4f1ea" : "#706f69",
                cursor: "pointer",
              }}>{tab.label}</button>
            ))}
          </div>
        </div>

        {/* Header row */}
        <div style={{ display: "grid", gridTemplateColumns: "2fr 2fr 1fr 1fr 1fr 60px", gap: "16px", padding: "10px 20px", borderBottom: "1px solid rgba(23,23,23,0.08)", fontSize: "10px", fontFamily: "IBM Plex Mono, monospace", color: "#706f69", fontWeight: 500, letterSpacing: "0.06em" }}>
          <span>CLIENTE</span><span>DOMINIO</span><span>ESTADO</span><span>APROBACIÓN</span><span>FECHA</span><span></span>
        </div>

        {isLoading ? (
          <div style={{ display: "flex", justifyContent: "center", padding: "48px 0" }}>
            <Loader2 size={18} style={{ color: "#706f69", animation: "spin 1s linear infinite" }} />
          </div>
        ) : filtered.length === 0 ? (
          <div style={{ padding: "48px 20px", textAlign: "center" }}>
            <p style={{ margin: 0, fontSize: "13px", color: "#706f69", fontFamily: "IBM Plex Mono, monospace" }}>
              {all.length === 0 ? "Sin casos aún —" : "Sin casos con este filtro."}
            </p>
            {all.length === 0 && (
              <Link href="/dashboard-pro/new" style={{ display: "inline-block", marginTop: "8px", fontSize: "12px", fontFamily: "IBM Plex Mono, monospace", color: "#56624b", textDecoration: "none" }}>
                Crear el primero →
              </Link>
            )}
          </div>
        ) : (
          filtered.map((c: any) => (
            <div key={c.id} style={{ display: "grid", gridTemplateColumns: "2fr 2fr 1fr 1fr 1fr 60px", gap: "16px", padding: "14px 20px", alignItems: "center", borderBottom: "1px solid rgba(23,23,23,0.05)", background: "rgba(244,241,234,0.6)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", minWidth: 0 }}>
                {c.case_status === "running" && <Loader2 size={11} style={{ color: "#243c4f", animation: "spin 1s linear infinite", flexShrink: 0 }} />}
                <span style={{ fontSize: "13px", fontWeight: 500, color: "#171717", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{c.client_name}</span>
              </div>
              <span style={{ fontSize: "12px", color: "#706f69", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{c.domain}</span>
              <span>
                <span style={{ display: "inline-block", padding: "2px 8px", fontSize: "10px", fontFamily: "IBM Plex Mono, monospace", fontWeight: 500, background: `${S_COLOR[c.case_status] ?? "#706f69"}14`, color: S_COLOR[c.case_status] ?? "#706f69", border: `1px solid ${S_COLOR[c.case_status] ?? "#706f69"}30` }}>
                  {S_LABEL[c.case_status] ?? c.case_status}
                </span>
              </span>
              <span style={{ fontSize: "11px", color: "#706f69", fontFamily: "IBM Plex Mono, monospace" }}>{c.approval_status ?? "draft"}</span>
              <span style={{ fontSize: "11px", color: "#706f69" }}>{formatDate(c.created_at)}</span>
              <Link href={`/dashboard-pro/cases/${c.id}`} style={{ fontSize: "11px", fontFamily: "IBM Plex Mono, monospace", color: "#56624b", fontWeight: 500, textDecoration: "none", textAlign: "right" }}>
                Ver →
              </Link>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
