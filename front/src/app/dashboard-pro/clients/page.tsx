"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { apiPro } from "@/lib/api-pro";
import { formatDate } from "@/lib/utils";
import { Loader2, Plus, Building2, ChevronRight } from "lucide-react";

const S_COLOR: Record<string, string> = {
  draft: "#706f69", running: "#243c4f", review_ready: "#9b6d4d",
  approved: "#56624b", published: "#56624b", rejected: "#8b3a3a",
};
const S_LABEL: Record<string, string> = {
  draft: "Borrador", running: "Ejecutando", review_ready: "En revisión",
  approved: "Aprobado", published: "Publicado", rejected: "Rechazado",
};

export default function ProClientsPage() {
  const router = useRouter();
  const [selected, setSelected] = useState<string | null>(null);

  // Obtener todos los casos y agrupar por cliente
  const { data, isLoading } = useQuery({
    queryKey: ["pro-cases-all"],
    queryFn: () => apiPro.get("/pro/cases?limit=200").then(r => r.data),
  });

  const all: any[] = data?.items ?? [];

  // Agrupar por client_name
  const clientMap = new Map<string, any[]>();
  for (const c of all) {
    const key = c.client_name;
    if (!clientMap.has(key)) clientMap.set(key, []);
    clientMap.get(key)!.push(c);
  }
  const clients = Array.from(clientMap.entries()).map(([name, cases]) => ({
    name,
    total: cases.length,
    last: cases[0]?.created_at,
    cases,
  })).sort((a, b) => new Date(b.last).getTime() - new Date(a.last).getTime());

  const selectedCases = selected ? (clientMap.get(selected) ?? []) : [];

  return (
    <div>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "24px", paddingBottom: "24px", borderBottom: "1px solid rgba(23,23,23,0.12)" }}>
        <div>
          <p style={{ margin: 0, fontSize: "11px", fontFamily: "IBM Plex Mono, monospace", color: "#56624b", letterSpacing: "0.06em" }}>§ 03 · clientes</p>
          <h1 style={{ margin: "6px 0 0", fontFamily: "Cormorant Garamond, Georgia, serif", fontWeight: 500, fontSize: "56px", lineHeight: 0.92, color: "#171717" }}>
            Clientes
          </h1>
          <p style={{ margin: "10px 0 0", fontSize: "13px", color: "#706f69" }}>Historial de casos por organización</p>
        </div>
        <Link href="/dashboard-pro/new" style={{
          display: "flex", alignItems: "center", gap: "7px", height: "38px",
          padding: "0 16px", background: "#171717", color: "#f4f1ea",
          fontSize: "12px", fontFamily: "IBM Plex Mono, monospace", textDecoration: "none",
          border: "1px solid #171717", marginTop: "8px",
        }}>
          <Plus size={13} /> Nuevo caso
        </Link>
      </div>

      {/* Layout dos columnas */}
      <div style={{ display: "grid", gridTemplateColumns: "280px 1fr", gap: "1px", marginTop: "24px", background: "rgba(23,23,23,0.12)", alignItems: "start" }}>

        {/* Lista de clientes */}
        <div style={{ background: "#fff", minHeight: "400px" }}>
          <div style={{ padding: "14px 16px", borderBottom: "1px solid rgba(23,23,23,0.08)" }}>
            <p style={{ margin: 0, fontSize: "10px", fontFamily: "IBM Plex Mono, monospace", color: "#706f69", fontWeight: 500, letterSpacing: "0.06em" }}>
              ORGANIZACIONES · {clients.length}
            </p>
          </div>

          {isLoading ? (
            <div style={{ display: "flex", justifyContent: "center", padding: "48px 0" }}>
              <Loader2 size={18} style={{ color: "#706f69", animation: "spin 1s linear infinite" }} />
            </div>
          ) : clients.length === 0 ? (
            <div style={{ padding: "48px 16px", textAlign: "center" }}>
              <Building2 size={28} style={{ color: "rgba(23,23,23,0.15)", margin: "0 auto 12px" }} />
              <p style={{ margin: 0, fontSize: "12px", color: "#706f69", fontFamily: "IBM Plex Mono, monospace" }}>Sin clientes aún</p>
            </div>
          ) : (
            clients.map(client => (
              <button
                key={client.name}
                onClick={() => setSelected(client.name === selected ? null : client.name)}
                style={{
                  width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between",
                  gap: "12px", padding: "14px 16px", textAlign: "left",
                  background: selected === client.name ? "rgba(86,98,75,0.06)" : "transparent",
                  border: "none", borderBottom: "1px solid rgba(23,23,23,0.06)",
                  borderLeft: selected === client.name ? "2px solid #56624b" : "2px solid transparent",
                  cursor: "pointer",
                }}
              >
                <div style={{ minWidth: 0 }}>
                  <p style={{ margin: 0, fontSize: "13px", fontWeight: 500, color: "#171717", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {client.name}
                  </p>
                  <p style={{ margin: "3px 0 0", fontSize: "11px", color: "#706f69" }}>
                    {formatDate(client.last)}
                  </p>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "8px", flexShrink: 0 }}>
                  <span style={{ fontSize: "11px", fontFamily: "IBM Plex Mono, monospace", fontWeight: 500, color: "#56624b", background: "rgba(86,98,75,0.1)", padding: "2px 7px" }}>
                    {client.total}
                  </span>
                  <ChevronRight size={12} style={{ color: "rgba(23,23,23,0.2)" }} />
                </div>
              </button>
            ))
          )}
        </div>

        {/* Historial del cliente seleccionado */}
        <div style={{ background: "#fff", minHeight: "400px" }}>
          {!selected ? (
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "80px 24px", textAlign: "center" }}>
              <Building2 size={36} style={{ color: "rgba(23,23,23,0.1)", marginBottom: "16px" }} />
              <p style={{ margin: 0, fontSize: "13px", color: "#706f69", fontFamily: "IBM Plex Mono, monospace" }}>
                Selecciona un cliente para ver su historial
              </p>
            </div>
          ) : (
            <>
              {/* Header del cliente */}
              <div style={{ padding: "16px 20px", borderBottom: "1px solid rgba(23,23,23,0.08)", display: "flex", alignItems: "center", justifyContent: "space-between", gap: "16px" }}>
                <div>
                  <p style={{ margin: 0, fontSize: "14px", fontWeight: 500, color: "#171717" }}>{selected}</p>
                  <p style={{ margin: "3px 0 0", fontSize: "11px", color: "#706f69" }}>
                    {selectedCases.length} caso{selectedCases.length !== 1 ? "s" : ""}
                  </p>
                </div>
                <button
                  onClick={() => router.push(`/dashboard-pro/new?clone_from=${selectedCases[0].id}`)}
                  style={{
                    display: "flex", alignItems: "center", gap: "6px", height: "34px",
                    padding: "0 12px", background: "#171717", color: "#f4f1ea",
                    fontSize: "11px", fontFamily: "IBM Plex Mono, monospace",
                    border: "none", cursor: "pointer",
                  }}
                >
                  <Plus size={11} /> Nuevo diagnóstico
                </button>
              </div>

              {/* Tabla de casos */}
              <div style={{ padding: "0 20px" }}>
                {selectedCases.map((c: any) => (
                  <div key={c.id} style={{ display: "flex", alignItems: "center", gap: "16px", padding: "14px 0", borderBottom: "1px solid rgba(23,23,23,0.06)" }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <p style={{ margin: 0, fontSize: "13px", fontWeight: 500, color: "#171717", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {c.domain}
                      </p>
                      <p style={{ margin: "3px 0 0", fontSize: "11px", color: "#706f69" }}>
                        {c.case_id} · {formatDate(c.created_at)}
                      </p>
                    </div>
                    <span style={{
                      padding: "2px 8px", fontSize: "10px", fontFamily: "IBM Plex Mono, monospace", fontWeight: 500,
                      background: `${S_COLOR[c.case_status] ?? "#706f69"}14`,
                      color: S_COLOR[c.case_status] ?? "#706f69",
                      border: `1px solid ${S_COLOR[c.case_status] ?? "#706f69"}30`,
                      flexShrink: 0,
                    }}>
                      {S_LABEL[c.case_status] ?? c.case_status}
                    </span>
                    <Link href={`/dashboard-pro/cases/${c.id}`} style={{ fontSize: "11px", fontFamily: "IBM Plex Mono, monospace", color: "#56624b", fontWeight: 500, textDecoration: "none", flexShrink: 0 }}>
                      Ver →
                    </Link>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
