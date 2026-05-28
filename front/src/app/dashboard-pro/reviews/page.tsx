"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { apiPro } from "@/lib/api-pro";
import { formatDate } from "@/lib/utils";
import { Loader2, CheckCircle, Clock, Info, Check, Send, X, TrendingUp, AlertTriangle } from "lucide-react";

// ── helpers ───────────────────────────────────────────────────────────────────

function ScorePill({ label, value, ok }: { label: string; value: any; ok: boolean }) {
  if (value == null) return null;
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: "4px",
      fontSize: "10px", fontFamily: "IBM Plex Mono, monospace", fontWeight: 500,
      padding: "2px 8px",
      background: ok ? "rgba(86,98,75,0.1)" : "rgba(139,58,58,0.1)",
      color: ok ? "#56624b" : "#8b3a3a",
      border: `1px solid ${ok ? "rgba(86,98,75,0.25)" : "rgba(139,58,58,0.25)"}`,
    }}>
      {label}: {value}
    </span>
  );
}

// ── Card de caso en revisión ──────────────────────────────────────────────────
function ReviewCard({ c, onAction }: { c: any; onAction: (id: string, action: string, comment?: string) => void }) {
  const [comment, setComment] = useState("");
  const [pending, setPending] = useState<string | null>(null);

  const fusion  = c.fusion_result  ?? {};
  const scoring = fusion.scoring   ?? {};
  const hyps    = fusion.hypotheses ?? [];
  const risks   = fusion.risk_signals ?? [];
  const overall = scoring.overall_score;
  const confirmed = hyps.filter((h: any) => h.supported).length;

  async function handle(action: string) {
    setPending(action);
    await onAction(c.id, action, comment);
    setPending(null);
  }

  return (
    <div style={{ background: "#fff", border: "1px solid rgba(23,23,23,0.12)" }}>
      {/* Header */}
      <div style={{ padding: "20px", borderBottom: "1px solid rgba(23,23,23,0.08)" }}>
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "16px" }}>
          <div>
            <p style={{ margin: 0, fontSize: "15px", fontWeight: 500, color: "#171717" }}>{c.client_name}</p>
            <p style={{ margin: "4px 0 0", fontSize: "12px", color: "#706f69" }}>{c.domain} · {c.case_id}</p>
            <p style={{ margin: "4px 0 0", fontSize: "11px", color: "#706f69" }}>{formatDate(c.created_at)}</p>
          </div>
          <Link href={`/dashboard-pro/cases/${c.id}`} style={{ fontSize: "11px", fontFamily: "IBM Plex Mono, monospace", color: "#56624b", fontWeight: 500, textDecoration: "none", flexShrink: 0 }}>
            Ver caso →
          </Link>
        </div>

        {/* Métricas */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginTop: "12px" }}>
          <ScorePill label="Score" value={overall != null ? `${overall}/100` : null} ok={(overall ?? 0) >= 65} />
          <ScorePill label="Hipótesis confirmadas" value={confirmed > 0 ? confirmed : null} ok={confirmed > 0} />
          <ScorePill label="Señales de riesgo" value={risks.length > 0 ? risks.length : null} ok={risks.length === 0} />
          <ScorePill label="PMEL" value={c.pmel_outcome} ok={c.pmel_outcome === "PERMIT"} />
        </div>
      </div>

      {/* Resumen del diagnóstico */}
      {fusion.executive_thesis && (
        <div style={{ padding: "16px 20px", borderBottom: "1px solid rgba(23,23,23,0.06)", background: "rgba(86,98,75,0.03)" }}>
          <p style={{ margin: "0 0 6px", fontSize: "10px", fontFamily: "IBM Plex Mono, monospace", color: "#56624b", fontWeight: 500, letterSpacing: "0.06em" }}>TESIS EJECUTIVA</p>
          <p style={{ margin: 0, fontSize: "13px", color: "#222522", lineHeight: 1.6 }}>{fusion.executive_thesis}</p>
        </div>
      )}

      {/* Señales de riesgo */}
      {risks.length > 0 && (
        <div style={{ padding: "16px 20px", borderBottom: "1px solid rgba(23,23,23,0.06)" }}>
          <p style={{ margin: "0 0 10px", fontSize: "10px", fontFamily: "IBM Plex Mono, monospace", color: "#9b6d4d", fontWeight: 500, letterSpacing: "0.06em" }}>
            SEÑALES DE RIESGO · {risks.length}
          </p>
          <div style={{ display: "grid", gap: "6px" }}>
            {risks.slice(0, 3).map((r: any, i: number) => (
              <div key={i} style={{ display: "flex", alignItems: "center", gap: "10px", padding: "8px 12px", background: r.severity === "high" ? "rgba(139,58,58,0.05)" : "rgba(155,109,77,0.05)", border: `1px solid ${r.severity === "high" ? "rgba(139,58,58,0.2)" : "rgba(155,109,77,0.2)"}` }}>
                <AlertTriangle size={12} style={{ color: r.severity === "high" ? "#8b3a3a" : "#9b6d4d", flexShrink: 0 }} />
                <span style={{ fontSize: "12px", color: "#171717" }}>{r.signal}</span>
                <span style={{ marginLeft: "auto", fontSize: "10px", fontFamily: "IBM Plex Mono, monospace", color: r.severity === "high" ? "#8b3a3a" : "#9b6d4d" }}>
                  {r.severity?.toUpperCase()}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Panel HIL */}
      <div style={{ padding: "16px 20px", background: "#fafaf9" }}>
        <p style={{ margin: "0 0 10px", fontSize: "10px", fontFamily: "IBM Plex Mono, monospace", color: "#706f69", fontWeight: 500, letterSpacing: "0.06em" }}>
          DECISIÓN HIL
        </p>
        <textarea
          value={comment}
          onChange={e => setComment(e.target.value)}
          placeholder="Comentario de revisión (opcional)..."
          rows={2}
          style={{
            width: "100%", border: "1px solid rgba(23,23,23,0.14)", padding: "8px 12px",
            background: "#fff", color: "#171717", fontFamily: "Manrope, sans-serif",
            fontSize: "12px", resize: "vertical", outline: "none", boxSizing: "border-box",
            marginBottom: "10px",
          }}
        />
        <div style={{ display: "flex", gap: "8px" }}>
          {[
            { action: "approve", label: "Aprobar",  icon: Check, bg: "#56624b" },
            { action: "publish", label: "Publicar", icon: Send,  bg: "#243c4f" },
            { action: "reject",  label: "Rechazar", icon: X,     bg: "#8b3a3a" },
          ].map(({ action, label, icon: Icon, bg }) => (
            <button
              key={action}
              onClick={() => handle(action)}
              disabled={!!pending}
              style={{
                display: "flex", alignItems: "center", gap: "6px",
                height: "34px", padding: "0 14px",
                background: bg, color: "#f4f1ea",
                fontSize: "11px", fontFamily: "IBM Plex Mono, monospace",
                border: "none", cursor: pending ? "not-allowed" : "pointer",
                opacity: pending && pending !== action ? 0.4 : 1,
              }}
            >
              {pending === action
                ? <Loader2 size={11} style={{ animation: "spin 1s linear infinite" }} />
                : <Icon size={11} />
              }
              {label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Página ────────────────────────────────────────────────────────────────────
export default function ProReviewsPage() {
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["pro-reviews"],
    queryFn: () => apiPro.get("/pro/cases?limit=200").then(r => r.data),
    refetchInterval: 15000,
  });

  const approvalMutation = useMutation({
    mutationFn: ({ id, action, comment }: { id: string; action: string; comment?: string }) =>
      apiPro.post(`/pro/cases/${id}/approval`, { action, comment }).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["pro-reviews"] });
      qc.invalidateQueries({ queryKey: ["pro-cases"] });
    },
  });

  const all: any[] = data?.items ?? [];
  const pending = all.filter(c => c.case_status === "review_ready");
  const recent  = all.filter(c => ["approved", "published", "rejected"].includes(c.case_status)).slice(0, 5);

  async function handleAction(id: string, action: string, comment?: string) {
    await approvalMutation.mutateAsync({ id, action, comment });
  }

  return (
    <div>
      {/* Header */}
      <div style={{ paddingBottom: "24px", borderBottom: "1px solid rgba(23,23,23,0.12)" }}>
        <p style={{ margin: 0, fontSize: "11px", fontFamily: "IBM Plex Mono, monospace", color: "#56624b", letterSpacing: "0.06em" }}>§ 04 · revisiones HIL</p>
        <h1 style={{ margin: "6px 0 0", fontFamily: "Cormorant Garamond, Georgia, serif", fontWeight: 500, fontSize: "56px", lineHeight: 0.92, color: "#171717" }}>
          Revisiones
        </h1>
        <p style={{ margin: "10px 0 0", fontSize: "13px", color: "#706f69" }}>Control humano en el ciclo gobernado — Human-in-the-Loop</p>
      </div>

      {/* Info banner */}
      <div style={{ marginTop: "20px", padding: "14px 18px", border: "1px solid rgba(36,60,79,0.2)", borderLeft: "3px solid #243c4f", background: "rgba(36,60,79,0.04)", display: "flex", gap: "12px" }}>
        <Info size={14} style={{ color: "#243c4f", flexShrink: 0, marginTop: "1px" }} />
        <p style={{ margin: 0, fontSize: "12px", color: "#243c4f", lineHeight: 1.6 }}>
          Los casos en revisión completaron el ciclo de fusión diagnóstica. Revisa la tesis ejecutiva, señales de riesgo e hipótesis antes de aprobar o publicar.
        </p>
      </div>

      {/* Pendientes */}
      <div style={{ marginTop: "28px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "16px" }}>
          <Clock size={14} style={{ color: "#9b6d4d" }} />
          <p style={{ margin: 0, fontSize: "12px", fontFamily: "IBM Plex Mono, monospace", fontWeight: 500, color: "#222522" }}>
            PENDIENTES DE REVISIÓN
          </p>
          {pending.length > 0 && (
            <span style={{ fontSize: "11px", fontFamily: "IBM Plex Mono, monospace", padding: "2px 8px", background: "rgba(155,109,77,0.12)", color: "#9b6d4d", border: "1px solid rgba(155,109,77,0.25)" }}>
              {pending.length}
            </span>
          )}
        </div>

        {isLoading ? (
          <div style={{ display: "flex", justifyContent: "center", padding: "48px 0" }}>
            <Loader2 size={18} style={{ color: "#706f69", animation: "spin 1s linear infinite" }} />
          </div>
        ) : pending.length === 0 ? (
          <div style={{ background: "#fff", border: "1px solid rgba(23,23,23,0.12)", padding: "48px 24px", textAlign: "center" }}>
            <CheckCircle size={28} style={{ color: "rgba(86,98,75,0.4)", margin: "0 auto 12px" }} />
            <p style={{ margin: 0, fontSize: "13px", color: "#706f69", fontFamily: "IBM Plex Mono, monospace" }}>
              Sin casos pendientes de revisión.
            </p>
            <p style={{ margin: "6px 0 0", fontSize: "12px", color: "#c0bdb6" }}>
              Todos los casos completados han sido revisados.
            </p>
          </div>
        ) : (
          <div style={{ display: "grid", gap: "16px" }}>
            {pending.map((c: any) => (
              <ReviewCard key={c.id} c={c} onAction={handleAction} />
            ))}
          </div>
        )}
      </div>

      {/* Revisados recientemente */}
      {recent.length > 0 && (
        <div style={{ marginTop: "40px" }}>
          <p style={{ margin: "0 0 16px", fontSize: "12px", fontFamily: "IBM Plex Mono, monospace", fontWeight: 500, color: "#706f69", letterSpacing: "0.06em" }}>
            REVISADOS RECIENTEMENTE
          </p>
          <div style={{ background: "#fff", border: "1px solid rgba(23,23,23,0.12)" }}>
            {recent.map((c: any, i: number) => (
              <div key={c.id} style={{ display: "flex", alignItems: "center", gap: "16px", padding: "14px 20px", borderBottom: i < recent.length - 1 ? "1px solid rgba(23,23,23,0.06)" : "none" }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <p style={{ margin: 0, fontSize: "13px", fontWeight: 500, color: "#171717" }}>{c.client_name}</p>
                  <p style={{ margin: "3px 0 0", fontSize: "11px", color: "#706f69" }}>{c.domain} · {formatDate(c.reviewed_at ?? c.updated_at)}</p>
                </div>
                <span style={{
                  fontSize: "10px", fontFamily: "IBM Plex Mono, monospace", fontWeight: 500,
                  padding: "2px 8px",
                  background: c.case_status === "approved" || c.case_status === "published" ? "rgba(86,98,75,0.1)" : "rgba(139,58,58,0.1)",
                  color: c.case_status === "approved" || c.case_status === "published" ? "#56624b" : "#8b3a3a",
                  border: `1px solid ${c.case_status === "approved" || c.case_status === "published" ? "rgba(86,98,75,0.25)" : "rgba(139,58,58,0.25)"}`,
                }}>
                  {c.case_status === "published" ? "PUBLICADO" : c.case_status === "approved" ? "APROBADO" : "RECHAZADO"}
                </span>
                <Link href={`/dashboard-pro/cases/${c.id}`} style={{ fontSize: "11px", fontFamily: "IBM Plex Mono, monospace", color: "#56624b", fontWeight: 500, textDecoration: "none" }}>
                  Ver →
                </Link>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
