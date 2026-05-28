"use client";

import { useQuery } from "@tanstack/react-query";
import { apiPro } from "@/lib/api-pro";
import { Loader2, RefreshCw } from "lucide-react";

export default function ProCompliancePage() {
  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ["pro-compliance"],
    queryFn: () => apiPro.get("/pro/compliance/posture").then(r => r.data),
  });

  const c = data ?? {};

  return (
    <div style={{ fontFamily: "Manrope, sans-serif" }}>
      {/* Header */}
      <div style={{ minHeight: "92px", display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "24px", borderBottom: "1px solid rgba(23,23,23,0.14)", paddingBottom: "20px" }}>
        <div>
          <p style={{ margin: 0, color: "#56624b", fontSize: "12px", fontFamily: "IBM Plex Mono, monospace" }}>§ governance posture</p>
          <h1 style={{ margin: "8px 0 0", fontFamily: "Cormorant Garamond, Georgia, serif", fontWeight: 500, fontSize: "52px", lineHeight: 0.96, color: "#171717" }}>
            Compliance
          </h1>
          <p style={{ margin: "8px 0 0", fontSize: "14px", color: "#706f69" }}>Estado del runtime PMEL/ATK y cobertura de políticas</p>
        </div>
        <button
          onClick={() => refetch()}
          disabled={isFetching}
          style={{ minHeight: "42px", border: "1px solid rgba(23,23,23,0.14)", padding: "9px 12px", background: "transparent", color: "#706f69", cursor: "pointer", opacity: isFetching ? 0.5 : 1 }}
        >
          <RefreshCw size={14} style={{ animation: isFetching ? "spin 1s linear infinite" : "none" }} />
        </button>
      </div>

      {isLoading ? (
        <div style={{ display: "flex", justifyContent: "center", padding: "80px 0" }}>
          <Loader2 size={24} style={{ color: "#706f69", animation: "spin 1s linear infinite" }} />
        </div>
      ) : (
        <div style={{ display: "grid", gap: "1px", marginTop: "28px", background: "rgba(23,23,23,0.14)" }}>

          {/* Runtime */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: "1px", background: "rgba(23,23,23,0.14)" }}>
            {[
              { label: "Producto", value: c.product_identity ?? "ARHIAX-DxPro-v1" },
              { label: "Policy Engine", value: c.policy_engine_mode ?? "native-fallback" },
              { label: "Entorno", value: c.env ?? "development" },
            ].map(({ label, value }) => (
              <div key={label} style={{ minHeight: "94px", background: "rgba(244,241,234,0.96)", padding: "20px" }}>
                <dt style={{ color: "#706f69", fontSize: "11px", fontFamily: "IBM Plex Mono, monospace" }}>{label}</dt>
                <dd style={{ margin: "10px 0 0", fontSize: "16px", fontWeight: 500, color: "#171717", fontFamily: "IBM Plex Mono, monospace" }}>{value}</dd>
              </div>
            ))}
          </div>

          {/* Ledger head */}
          {c.ledger_head && (
            <div style={{ background: "rgba(244,241,234,0.96)", padding: "20px" }}>
              <dt style={{ color: "#706f69", fontSize: "11px", fontFamily: "IBM Plex Mono, monospace" }}>Ledger HEAD (HMAC)</dt>
              <dd style={{ margin: "10px 0 0", fontSize: "13px", fontFamily: "IBM Plex Mono, monospace", color: "#56624b", wordBreak: "break-all" }}>
                {c.ledger_head}
              </dd>
            </div>
          )}

          {/* Políticas PMEL */}
          <div style={{ background: "rgba(244,241,234,0.96)", padding: "24px" }}>
            <p style={{ margin: "0 0 16px", fontSize: "11px", fontFamily: "IBM Plex Mono, monospace", color: "#706f69", fontWeight: 500 }}>
              PAQUETES DE POLÍTICA PMEL · {(c.policy_coverage ?? []).length}
            </p>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: "1px", background: "rgba(23,23,23,0.14)" }}>
              {(c.policy_coverage ?? []).map((pkg: string) => (
                <div key={pkg} style={{ background: "#f4f1ea", padding: "12px 16px" }}>
                  <p style={{ margin: 0, fontSize: "12px", fontFamily: "IBM Plex Mono, monospace", color: "#56624b" }}>{pkg}</p>
                </div>
              ))}
              {(c.policy_coverage ?? []).length === 0 && (
                <div style={{ background: "#f4f1ea", padding: "12px 16px" }}>
                  <p style={{ margin: 0, fontSize: "12px", fontFamily: "IBM Plex Mono, monospace", color: "#706f69" }}>Sin datos de cobertura</p>
                </div>
              )}
            </div>
          </div>

          {/* Catálogo de herramientas */}
          {c.catalog?.tools?.length > 0 && (
            <div style={{ background: "rgba(244,241,234,0.96)", padding: "24px" }}>
              <p style={{ margin: "0 0 16px", fontSize: "11px", fontFamily: "IBM Plex Mono, monospace", color: "#706f69", fontWeight: 500 }}>
                CATÁLOGO DE HERRAMIENTAS · {c.catalog.tools.length}
              </p>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: "1px", background: "rgba(23,23,23,0.14)" }}>
                {c.catalog.tools.map((tool: any) => (
                  <div key={tool.name ?? tool} style={{ background: "#f4f1ea", padding: "12px 16px" }}>
                    <p style={{ margin: 0, fontSize: "12px", fontFamily: "IBM Plex Mono, monospace", color: "#222522" }}>
                      {tool.name ?? tool}
                    </p>
                    {tool.scope && (
                      <p style={{ margin: "4px 0 0", fontSize: "10px", color: "#706f69" }}>{tool.scope}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ATK Priority table */}
          <div style={{ background: "rgba(244,241,234,0.96)", padding: "24px" }}>
            <p style={{ margin: "0 0 16px", fontSize: "11px", fontFamily: "IBM Plex Mono, monospace", color: "#706f69", fontWeight: 500 }}>
              PRIORIDADES ATK
            </p>
            <div style={{ display: "grid", gap: "1px", background: "rgba(23,23,23,0.14)" }}>
              {[
                { p: 1, outcome: "SUSPEND", desc: "Detener el proceso inmediatamente", color: "#8b3a3a" },
                { p: 2, outcome: "DENY",    desc: "Bloquear la acción solicitada",     color: "#9b6d4d" },
                { p: 3, outcome: "ESCALATE",desc: "Requiere revisión humana",          color: "#243c4f" },
                { p: 4, outcome: "MODIFY",  desc: "Permitir solo con modificación",    color: "#706f69" },
                { p: 5, outcome: "AUDIT",   desc: "Permitir pero registrar",           color: "#56624b" },
                { p: 6, outcome: "PERMIT",  desc: "Permitir ejecución",                color: "#56624b" },
              ].map(({ p, outcome, desc, color }) => (
                <div key={outcome} style={{ display: "grid", gridTemplateColumns: "32px 100px 1fr", gap: "16px", alignItems: "center", padding: "12px 16px", background: "#f4f1ea" }}>
                  <span style={{ fontSize: "11px", fontFamily: "IBM Plex Mono, monospace", color: "#706f69" }}>{p}</span>
                  <span style={{ fontSize: "12px", fontFamily: "IBM Plex Mono, monospace", fontWeight: 500, color }}>{outcome}</span>
                  <span style={{ fontSize: "12px", color: "#706f69" }}>{desc}</span>
                </div>
              ))}
            </div>
          </div>

        </div>
      )}
    </div>
  );
}
