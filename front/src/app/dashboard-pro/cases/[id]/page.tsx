"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { apiPro } from "@/lib/api-pro";
import { formatDate } from "@/lib/utils";
import { Loader2, ChevronLeft, Check, X, Send, Cpu, RefreshCw, ShieldCheck, CheckCircle } from "lucide-react";
import { ProFusionPipeline } from "@/components/features/pro/ProFusionPipeline";
import { ProResultsPanel, ProGovernancePanel, ProAutonometer, ProExecutionMetrics } from "@/components/features/pro/ProResultsPanel";
import { SurveyAuditPanel } from "@/components/features/diagnostics/SurveyAuditPanel";

// ── helpers ───────────────────────────────────────────────────────────────────
const STATUS_COLOR: Record<string, string> = {
  draft: '#706f69', designing: '#243c4f', survey_open: '#9b6d4d',
  running: '#243c4f', review_pending: '#9b6d4d', approved: '#56624b',
  published: '#56624b', rejected: '#8b3a3a', error: '#8b3a3a',
};
const STATUS_LABEL: Record<string, string> = {
  draft: 'Borrador', designing: 'Diseñando', survey_open: 'Encuesta abierta',
  running: 'Ejecutando', review_pending: 'En revisión', approved: 'Aprobado',
  published: 'Publicado', rejected: 'Rechazado', error: 'Error',
};

// ── page ──────────────────────────────────────────────────────────────────────
export default function ProCaseDetailPage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const [reviewComment, setReviewComment] = useState("");

  const { data: caseData, isLoading, isError: isQueryError, isFetching } = useQuery({
    queryKey: ["pro-case", id],
    queryFn: () => apiPro.get(`/pro/cases/${id}`).then(r => r.data),
    refetchInterval: (q: any) => {
      const data = q.state.data;
      const status = data?.case_status;
      // Always poll aggressively when running or designing
      if (status === "running") return 5000;
      if (status === "survey_open" || data?.survey?.status === "designing") return 4000;
      // If no data yet (first load failed), keep trying
      if (!data) return 6000;
      return false;
    },
    retry: 5,
    retryDelay: (attempt) => Math.min(2000 * (attempt + 1), 10000),
    // Don't discard stale data on error — keep showing last known state
    staleTime: 0,
  });

  const approvalMutation = useMutation({
    mutationFn: ({ action, comment }: { action: string; comment?: string }) =>
      apiPro.post(`/pro/cases/${id}/approval`, { action, comment }).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["pro-case", id] });
      qc.invalidateQueries({ queryKey: ["pro-cases"] });
      setReviewComment("");
    },
  });

  const runMutation = useMutation({
    mutationFn: () => apiPro.post(`/pro/cases/${id}/run`).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["pro-case", id] });
      qc.invalidateQueries({ queryKey: ["pro-cases"] });
    },
    onError: (err: any) => {
      alert(err.response?.data?.detail || "Error al iniciar el diagnóstico.");
    }
  });

  if (isLoading) return (
    <div style={{ display: "flex", justifyContent: "center", padding: "80px 0" }}>
      <Loader2 size={24} style={{ color: "#706f69", animation: "spin 1s linear infinite" }} />
    </div>
  );

  if (!caseData && isQueryError) return (
    <div style={{ padding: "48px 0", textAlign: "center", color: "#706f69", fontFamily: "IBM Plex Mono, monospace", fontSize: "13px" }}>
      No se pudo cargar el caso. Reintente en unos segundos.
    </div>
  );

  if (!caseData) return (
    <div style={{ padding: "48px 0", textAlign: "center", color: "#706f69", fontFamily: "IBM Plex Mono, monospace", fontSize: "13px" }}>
      Caso no encontrado.
    </div>
  );

  const c = caseData;
  const statusColor = STATUS_COLOR[c.case_status] ?? "#706f69";
  const isRunning   = c.case_status === "running";
  const isCaseError = c.case_status === "error";
  const canApprove  = c.case_status === "review_pending";
  const isDone      = ["review_pending", "approved", "published"].includes(c.case_status);
  const surveyOpen  = c.survey?.status === "open";
  const surveyError = c.survey?.status === "error";

  const lifecycleSteps = [
    {
      id: "design", label: "Arquitectura",
      failed: surveyError,
      active: c.case_status === "designing" && !surveyOpen && !surveyError,
      done: surveyOpen || (["survey_open", "running", "review_pending", "approved", "published", "rejected"].includes(c.case_status) && !surveyError),
    },
    {
      id: "collection", label: "Recolección",
      failed: false,
      active: c.case_status === "survey_open" && surveyOpen,
      done: ["running", "review_pending", "approved", "published", "rejected"].includes(c.case_status)
        || (isCaseError && (c.survey?.responses_count ?? 0) > 0),
    },
    {
      id: "fusion", label: "Fusión IA",
      failed: isCaseError && !surveyError,
      active: isRunning,
      done: ["review_pending", "approved", "published", "rejected"].includes(c.case_status),
    },
    {
      id: "review", label: "Validación HIL",
      failed: c.case_status === "rejected",
      active: c.case_status === "review_pending",
      done: ["approved", "published"].includes(c.case_status),
    },
  ];

  return (
    <div style={{ fontFamily: "Manrope, sans-serif" }}>

      {/* Header */}
      <div style={{
        minHeight: "92px", display: "flex", alignItems: "flex-start",
        justifyContent: "space-between", gap: "24px",
        borderBottom: "1px solid rgba(23,23,23,0.14)", paddingBottom: "20px",
      }}>
        <div>
          <p style={{ margin: 0, color: "#56624b", fontSize: "12px", fontFamily: "IBM Plex Mono, monospace" }}>
            § caso · {c.case_id ?? id}
          </p>
          <h1 style={{ margin: "8px 0 0", fontFamily: "Cormorant Garamond, Georgia, serif", fontWeight: 500, fontSize: "48px", lineHeight: 0.96, color: "#171717" }}>
            {c.client_name}
          </h1>
          <div style={{ display: "flex", alignItems: "center", gap: "12px", marginTop: "10px", flexWrap: "wrap" }}>
            <span style={{
              display: "inline-flex", alignItems: "center", gap: "6px",
              padding: "3px 10px", fontSize: "11px",
              fontFamily: "IBM Plex Mono, monospace", fontWeight: 500,
              background: `${statusColor}18`, color: statusColor,
              border: `1px solid ${statusColor}40`,
            }}>
              {isRunning && <Loader2 size={10} style={{ animation: "spin 1s linear infinite" }} />}
              {STATUS_LABEL[c.case_status] ?? c.case_status}
            </span>
            <span style={{ fontSize: "12px", color: "#706f69" }}>{c.domain}</span>
            <span style={{ fontSize: "12px", color: "#706f69" }}>{formatDate(c.created_at)}</span>
          </div>
          {c.input_payload?.symptom && (
            <p style={{ margin: "16px 0 0", fontSize: "14px", color: "#222522", lineHeight: 1.6, maxWidth: "800px" }}>
              {c.input_payload.symptom}
            </p>
          )}
        </div>
        <Link href="/dashboard-pro" style={{
          display: "flex", alignItems: "center", gap: "6px", minHeight: "42px",
          border: "1px solid rgba(23,23,23,0.14)", padding: "9px 14px",
          background: "transparent", color: "#706f69",
          fontSize: "12px", fontFamily: "IBM Plex Mono, monospace", textDecoration: "none",
        }}>
          <ChevronLeft size={14} /> Casos
        </Link>
      </div>

      {/* Próximo paso — siempre visible */}
      {c.next_step && (
        <div style={{
          marginTop: "20px", padding: "14px 18px",
          border: "1px solid rgba(23,23,23,0.12)", borderLeft: "3px solid #56624b",
          background: "rgba(86,98,75,0.06)",
        }}>
          <p style={{ margin: 0, fontSize: "11px", fontFamily: "IBM Plex Mono, monospace", color: "#56624b", fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase" }}>
            Próximo paso
          </p>
          <p style={{ margin: "6px 0 0", fontSize: "13px", color: "#171717", lineHeight: 1.5 }}>
            {c.next_step}
          </p>
        </div>
      )}

      {/* Error de pipeline — transparente */}
      {isCaseError && c.pipeline_error && (
        <div style={{
          marginTop: "12px", padding: "16px 18px",
          border: "1px solid rgba(139,58,58,0.35)", borderLeft: "3px solid #8b3a3a",
          background: "rgba(139,58,58,0.06)",
        }}>
          <p style={{ margin: 0, fontSize: "13px", fontWeight: 600, color: "#8b3a3a" }}>
            Error del pipeline
          </p>
          <p style={{ margin: "8px 0 0", fontSize: "12px", color: "#706f69", lineHeight: 1.55, fontFamily: "IBM Plex Mono, monospace", whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
            {c.pipeline_error}
          </p>
        </div>
      )}

      {/* Lifecycle Stepper */}
      <div style={{ 
        marginTop: "32px", display: "flex", alignItems: "center", gap: "0", 
        background: "#fff", border: "1px solid rgba(23,23,23,0.1)", padding: "20px" 
      }}>
        {lifecycleSteps.map((step, i, arr) => (
          <div key={step.id} style={{ flex: 1, display: "flex", alignItems: "center", gap: "12px" }}>
            <div style={{ 
              width: "28px", height: "28px", border: "1px solid #171717", 
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: "11px", fontFamily: "IBM Plex Mono, monospace", fontWeight: 500,
              background: step.failed ? "#8b3a3a" : step.done ? "#56624b" : step.active ? "#171717" : "transparent",
              color: (step.done || step.active || step.failed) ? "#f4f1ea" : "#171717",
              borderColor: step.failed ? "#8b3a3a" : step.done ? "#56624b" : "#171717",
            }}>
              {step.failed ? <X size={14} /> : step.done ? <Check size={14} /> : i + 1}
            </div>
            <div style={{ flex: 1 }}>
              <p style={{ 
                margin: 0, fontSize: "12px", fontWeight: step.active ? 700 : 500, 
                color: step.active ? "#171717" : "#706f69",
                fontFamily: "IBM Plex Mono, monospace", textTransform: "uppercase", letterSpacing: "0.05em"
              }}>
                {step.label}
              </p>
            </div>
            {i < arr.length - 1 && (
              <div style={{ width: "40px", height: "1px", background: "rgba(23,23,23,0.12)", marginRight: "12px" }} />
            )}
          </div>
        ))}
      </div>

      {/* Banners de estado */}
      {isRunning && (
        <div style={{
          marginTop: "20px", display: "flex", alignItems: "center", gap: "12px",
          padding: "16px 20px", border: "1px solid rgba(36,60,79,0.3)",
          borderLeft: "3px solid #243c4f", background: "rgba(36,60,79,0.05)",
        }}>
          <Loader2 size={16} style={{ color: "#243c4f", animation: "spin 1s linear infinite", flexShrink: 0 }} />
          <div>
            <p style={{ margin: 0, fontSize: "13px", fontWeight: 500, color: "#243c4f" }}>
              Ciclo de fusión en ejecución
            </p>
            <p style={{ margin: "4px 0 0", fontSize: "12px", color: "#706f69" }}>
              El agente está procesando las etapas gobernadas. Esta pantalla se actualiza automáticamente.
            </p>
          </div>
        </div>
      )}

      {canApprove && (
        <div style={{
          marginTop: "20px", padding: "16px 20px",
          border: "1px solid rgba(155,109,77,0.3)", borderLeft: "3px solid #9b6d4d",
          background: "rgba(155,109,77,0.05)", display: "flex", alignItems: "center", justifyContent: "space-between", gap: "16px",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <div style={{ width: "32px", height: "32px", background: "#9b6d4d", display: "flex", alignItems: "center", justifyContent: "center", color: "#f4f1ea" }}>
              <ShieldCheck size={18} />
            </div>
            <div>
              <p style={{ margin: 0, fontSize: "13px", fontWeight: 500, color: "#9b6d4d" }}>
                Esperando aprobación HIL
              </p>
              <p style={{ margin: "4px 0 0", fontSize: "12px", color: "#706f69" }}>
                El diagnóstico completó el ciclo de fusión y está listo para revisión humana.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Layout principal: sidebar + contenido */}
      <div style={{ display: "flex", gap: "1px", marginTop: "28px", background: "rgba(23,23,23,0.14)", alignItems: "start" }}>

        {/* Sidebar izquierdo */}
        <div style={{ width: "280px", flexShrink: 0, display: "flex", flexDirection: "column", gap: "1px" }}>
          <ProGovernancePanel caseData={c} />
          <ProAutonometer />
          <ProExecutionMetrics caseData={c} />

          {/* HIL — Validación */}
          <div style={{ background: "#222522", padding: "20px" }}>
            <p style={{ margin: "0 0 4px", fontSize: "11px", fontFamily: "IBM Plex Mono, monospace", color: "rgba(244,241,234,0.5)", fontWeight: 500, letterSpacing: "0.06em" }}>
              VALIDACIÓN HUMANA · HIL
            </p>
            <p style={{ margin: "0 0 16px", fontSize: "11px", color: "rgba(244,241,234,0.25)", lineHeight: 1.4 }}>
              La aprobación genera el sello criptográfico e habilita la descarga del informe.
            </p>

            {!canApprove ? (
              <div style={{ padding: "12px", background: "rgba(244,241,234,0.04)", border: "1px solid rgba(244,241,234,0.08)" }}>
                <p style={{ margin: 0, color: "rgba(244,241,234,0.4)", fontSize: "12px", fontFamily: "IBM Plex Mono, monospace" }}>
                  {isRunning
                    ? "Disponible cuando termine el ciclo."
                    : c.case_status === "approved" || c.case_status === "published"
                    ? "Diagnostico aprobado y sellado."
                    : c.case_status === "rejected"
                    ? "Diagnostico rechazado."
                    : "El caso debe estar en revision."}
                </p>
              </div>
            ) : (
              <div style={{ display: "grid", gap: "10px" }}>
                <textarea
                  value={reviewComment}
                  onChange={e => setReviewComment(e.target.value)}
                  placeholder="Observaciones (opcional)..."
                  rows={3}
                  style={{
                    width: "100%", border: "1px solid rgba(244,241,234,0.16)", padding: "10px 12px",
                    background: "rgba(244,241,234,0.06)", color: "#f4f1ea",
                    fontFamily: "Manrope, sans-serif", fontSize: "12px", resize: "vertical",
                    outline: "none", boxSizing: "border-box",
                  }}
                />

                {/* APROBAR — genera sello SHA-256 */}
                <button
                  onClick={() => approvalMutation.mutate({ action: "approve", comment: reviewComment })}
                  disabled={approvalMutation.isPending}
                  style={{
                    display: "flex", alignItems: "center", justifyContent: "center", gap: "8px",
                    minHeight: "44px", border: "1px solid rgba(86,98,75,0.6)", padding: "10px 16px",
                    background: "rgba(86,98,75,0.3)", color: "#f4f1ea",
                    fontSize: "12px", fontFamily: "IBM Plex Mono, monospace", fontWeight: 700,
                    cursor: approvalMutation.isPending ? "not-allowed" : "pointer",
                    opacity: approvalMutation.isPending ? 0.5 : 1,
                    width: "100%", letterSpacing: "0.08em",
                  }}
                >
                  <CheckCircle size={14} />
                  {approvalMutation.isPending ? "Procesando..." : "APROBAR"}
                </button>

                {/* RECHAZAR */}
                <button
                  onClick={() => approvalMutation.mutate({ action: "reject", comment: reviewComment })}
                  disabled={approvalMutation.isPending}
                  style={{
                    display: "flex", alignItems: "center", justifyContent: "center", gap: "8px",
                    minHeight: "36px", border: "1px solid rgba(139,58,58,0.35)", padding: "8px 16px",
                    background: "transparent", color: "rgba(244,241,234,0.45)",
                    fontSize: "11px", fontFamily: "IBM Plex Mono, monospace",
                    cursor: approvalMutation.isPending ? "not-allowed" : "pointer",
                    opacity: approvalMutation.isPending ? 0.5 : 1,
                    width: "100%",
                  }}
                >
                  <X size={12} /> Rechazar diagnóstico
                </button>

                {approvalMutation.isError && (
                  <p style={{ margin: 0, color: "#f4a0a0", fontSize: "11px", fontFamily: "IBM Plex Mono, monospace" }}>
                    Error al procesar la acción.
                  </p>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Contenido principal */}
        <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", gap: "1px" }}>

          {/* Visualización de la etapa de Diseño */}
          {(c.case_status === "designing" || c.survey?.status === "designing") && (
            <div style={{ background: "#fff", border: "1px solid rgba(23,23,23,0.1)", padding: "48px 32px", textAlign: "center" }}>
              <div style={{ maxWidth: "600px", margin: "0 auto" }}>
                <div style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", width: "64px", height: "64px", background: "#f4f1ea", borderRadius: "16px", marginBottom: "24px" }}>
                  <Cpu size={32} style={{ color: "#171717" }} />
                </div>
                
                <h2 style={{ margin: "0 0 12px", fontSize: "28px", fontFamily: "Cormorant Garamond, serif", fontWeight: 500, color: "#171717" }}>
                  Arquitectura del Diagnóstico Adaptativo
                </h2>
                <p style={{ margin: "0 0 40px", fontSize: "15px", color: "#706f69", lineHeight: "1.6" }}>
                  Nuestros agentes de IA están procesando el dominio <b>{c.domain}</b> para construir un instrumento de recolección único para <b>{c.client_name}</b>.
                </p>

                <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: "16px", textAlign: "left" }}>
                  {[
                    { id: "G09a", label: "Arquitectura de preguntas", desc: "Diseñando ítems dinámicos basados en tus hipótesis." },
                    { id: "G09b", label: "Lógica de ramificación", desc: "Configurando rutas inteligentes según el perfil del respondiente." },
                    { id: "G09c", label: "Validación de integridad", desc: "Asegurando que el instrumento cumple con los estándares de ARHIAX." }
                  ].map((agent, i) => {
                    const ev = (c.evidence ?? []).find((e: any) => e.agent === agent.id || (agent.id === "G09a" && e.event_type === "survey_questions_generated"));
                    const isDone = !!ev;
                    const isNext = !isDone && (i === 0 || (c.evidence ?? []).some((e: any) => e.agent === (i === 1 ? "G09a" : "G09b")));

                    return (
                      <div key={agent.id} style={{ 
                        display: "flex", alignItems: "center", gap: "20px", padding: "20px", 
                        background: isDone ? "rgba(86,98,75,0.03)" : "transparent",
                        border: "1px solid",
                        borderColor: isDone ? "rgba(86,98,75,0.2)" : isNext ? "rgba(23,23,23,0.1)" : "rgba(23,23,23,0.05)",
                        borderRadius: "12px",
                        opacity: isDone || isNext ? 1 : 0.4
                      }}>
                        <div style={{ flexShrink: 0 }}>
                          {isDone ? (
                            <div style={{ width: "32px", height: "32px", borderRadius: "50%", background: "#56624b", display: "flex", alignItems: "center", justifyContent: "center" }}>
                              <Check size={18} style={{ color: "#f4f1ea" }} />
                            </div>
                          ) : isNext ? (
                            <Loader2 size={24} style={{ color: "#243c4f", animation: "spin 1.5s linear infinite" }} />
                          ) : (
                            <div style={{ width: "32px", height: "32px", borderRadius: "50%", border: "2px solid rgba(23,23,23,0.1)" }} />
                          )}
                        </div>
                        <div>
                          <p style={{ margin: "0 0 2px", fontSize: "14px", fontWeight: 600, color: isDone ? "#56624b" : "#171717" }}>
                            {agent.label}
                          </p>
                          <p style={{ margin: 0, fontSize: "12px", color: "#706f69" }}>
                            {isDone ? "Completado con éxito." : agent.desc}
                          </p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {/* Pipeline de fusión — siempre visible cuando running o hay stages */}
          <ProFusionPipeline caseData={c} isFetching={isFetching} />

          {/* Resultados — solo cuando hay datos */}
          {isDone && (c.fusion_result || c.report_result) && (
            <div className="flex flex-col gap-4 mt-6">
              <ProResultsPanel caseData={c} caseId={id} />
              
              {c.survey?.token && (
                <SurveyAuditPanel surveyToken={c.survey.token} isPro={true} />
              )}
            </div>
          )}

          {/* Evidencia del caso */}
          {(c.evidence ?? []).length > 0 && (
            <div style={{ background: "rgba(244,241,234,0.96)", padding: "24px" }}>
              <p style={{ margin: "0 0 16px", fontSize: "11px", fontFamily: "IBM Plex Mono, monospace", color: "#706f69", fontWeight: 500 }}>
                EVIDENCIA GOBERNADA · {c.evidence.length} entradas
              </p>
              <div style={{ display: "grid", gap: "1px", background: "rgba(23,23,23,0.14)" }}>
                {c.evidence.map((e: any, i: number) => (
                  <div key={i} style={{ background: "#f4f1ea", padding: "12px 16px", display: "grid", gridTemplateColumns: "160px 1fr 100px 100px", gap: "12px", alignItems: "center" }}>
                    <span style={{ fontSize: "10px", fontFamily: "IBM Plex Mono, monospace", color: "#9b6d4d", fontWeight: 500 }}>
                      {e.event_type}
                    </span>
                    <span style={{ fontSize: "11px", fontFamily: "IBM Plex Mono, monospace", color: "#706f69", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {e.trace_id ?? "—"}
                    </span>
                    <span style={{ fontSize: "11px", fontFamily: "IBM Plex Mono, monospace", color: e.outcome === "PERMIT" ? "#56624b" : "#9b6d4d" }}>
                      {e.outcome ?? "—"}
                    </span>
                    <span style={{ fontSize: "11px", color: "#706f69" }}>{formatDate(e.created_at)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Estado vacío o Hub de Recolección */}
          {!isRunning && !isDone && (
            <div style={{ background: "#fff", border: "1px solid rgba(23,23,23,0.1)", padding: "48px 32px" }}>
              {c.case_status === "survey_open" && c.survey ? (
                <div style={{ maxWidth: "600px", margin: "0 auto" }}>
                  <div style={{ textAlign: "center", marginBottom: "40px" }}>
                    <div style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", width: "56px", height: "56px", background: "rgba(155,109,77,0.1)", color: "#9b6d4d", borderRadius: "50%", marginBottom: "20px" }}>
                      <Send size={28} />
                    </div>
                    <h2 style={{ fontFamily: "Cormorant Garamond, serif", fontSize: "36px", color: "#171717", margin: "0 0 12px" }}>
                      Hub de Recolección Multi-Rater
                    </h2>
                    <p style={{ color: "#706f69", fontSize: "15px", lineHeight: 1.5 }}>
                      El instrumento está listo. Distribuya el enlace seguro a los participantes para iniciar la captura de evidencia.
                    </p>
                  </div>

                  {c.survey?.status === "open" ? (
                    <>
                      <div style={{ background: "#f4f1ea", padding: "24px", border: "1px solid rgba(23,23,23,0.06)", marginBottom: "32px" }}>
                        <p style={{ margin: "0 0 12px", fontSize: "11px", fontFamily: "IBM Plex Mono, monospace", color: "#706f69", fontWeight: 600, letterSpacing: "0.1em" }}>
                          ENLACE SEGURO DE ACCESO
                        </p>
                        <div style={{ display: "flex", gap: "12px" }}>
                          <input 
                            readOnly 
                            value={`${window.location.origin}/survey/pro/${c.survey?.token || ""}`}
                            style={{ flex: 1, padding: "12px 16px", background: "#fff", border: "1px solid rgba(23,23,23,0.1)", fontSize: "13px", fontFamily: "IBM Plex Mono, monospace", color: "#171717", outline: "none" }}
                          />
                          <button 
                            onClick={() => {
                              navigator.clipboard.writeText(`${window.location.origin}/survey/pro/${c.survey?.token || ""}`);
                              alert("Copiado al portapapeles");
                            }}
                            style={{ padding: "0 24px", background: "#171717", color: "#f4f1ea", border: "none", fontSize: "12px", fontFamily: "IBM Plex Mono, monospace", fontWeight: 600, cursor: "pointer" }}
                          >
                            COPIAR
                          </button>
                        </div>
                      </div>

                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "24px", marginBottom: "24px" }}>
                        <div style={{ background: "#fff", border: "1px solid rgba(23,23,23,0.1)", padding: "24px", textAlign: "center" }}>
                          <p style={{ margin: 0, fontSize: "42px", fontFamily: "Cormorant Garamond, serif", fontWeight: 500, color: "#243c4f", lineHeight: 1 }}>{c.survey.responses_count}</p>
                          <p style={{ margin: "10px 0 0", fontSize: "11px", fontFamily: "IBM Plex Mono, monospace", color: "#706f69", fontWeight: 600, textTransform: "uppercase" }}>Respuestas</p>
                        </div>
                        <div style={{ background: "#fff", border: "1px solid rgba(23,23,23,0.1)", padding: "24px", textAlign: "center" }}>
                          <p style={{ margin: 0, fontSize: "42px", fontFamily: "Cormorant Garamond, serif", fontWeight: 500, color: "#56624b", lineHeight: 1 }}>{c.survey.min_responses}</p>
                          <p style={{ margin: "10px 0 0", fontSize: "11px", fontFamily: "IBM Plex Mono, monospace", color: "#706f69", fontWeight: 600, textTransform: "uppercase" }}>Mín. Requerido</p>
                        </div>
                      </div>

                      {(c.survey.role_labels?.length ?? 0) > 0 && (
                        <div style={{ marginBottom: "32px", padding: "16px 20px", background: "#f4f1ea", border: "1px solid rgba(23,23,23,0.06)" }}>
                          <p style={{ margin: "0 0 10px", fontSize: "11px", fontFamily: "IBM Plex Mono, monospace", color: "#706f69", fontWeight: 600, letterSpacing: "0.08em" }}>
                            PARTICIPANTES ESPERADOS (1 respuesta por rol)
                          </p>
                          <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                            {(c.survey.role_labels as string[]).map((label: string) => (
                              <span key={label} style={{ padding: "4px 10px", fontSize: "11px", fontFamily: "IBM Plex Mono, monospace", background: "#fff", border: "1px solid rgba(23,23,23,0.12)", color: "#171717" }}>
                                {label}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      <button
                        onClick={() => runMutation.mutate()}
                        disabled={runMutation.isPending || c.survey?.responses_count === 0}
                        style={{
                          width: "100%", height: "56px", background: runMutation.isPending || c.survey?.responses_count === 0 ? "rgba(23,23,23,0.1)" : "#171717",
                          color: runMutation.isPending || c.survey?.responses_count === 0 ? "#706f69" : "#f4f1ea", border: "none", fontSize: "14px", fontFamily: "IBM Plex Mono, monospace", fontWeight: 600, letterSpacing: "0.1em",
                          cursor: runMutation.isPending || c.survey?.responses_count === 0 ? "not-allowed" : "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: "12px", transition: "all 0.2s"
                        }}
                      >
                        {runMutation.isPending ? <Loader2 size={18} style={{ animation: "spin 2s linear infinite" }} /> : <Cpu size={18} />}
                        {runMutation.isPending ? "INICIANDO CICLO..." : "LANZAR SÍNTESIS DE DIAGNÓSTICO"}
                      </button>
                      
                      {c.survey?.responses_count < c.survey?.min_responses && (
                        <p style={{ margin: "16px 0 0", fontSize: "12px", textAlign: "center", color: "#9b6d4d", fontStyle: "italic" }}>
                          Faltan {c.survey.min_responses - c.survey.responses_count} respuesta(s) para alcanzar el mínimo ({c.survey.responses_count}/{c.survey.min_responses}).
                        </p>
                      )}
                      {c.survey?.responses_count === 0 && (
                        <p style={{ margin: "16px 0 0", fontSize: "12px", textAlign: "center", color: "#8b3a3a", fontStyle: "italic" }}>
                          Se requiere al menos una respuesta para activar los agentes de fusión.
                        </p>
                      )}
                    </>
                  ) : (
                    <div style={{ textAlign: "center", padding: "40px 0" }}>
                      <Loader2 size={32} style={{ color: "#171717", animation: "spin 2s linear infinite", margin: "0 auto 24px" }} />
                      <p style={{ fontSize: "14px", color: "#706f69", fontFamily: "IBM Plex Mono, monospace" }}>
                        FINALIZANDO ARQUITECTURA...
                      </p>
                    </div>
                  )}
                </div>
              ) : isCaseError ? (
                <div style={{ maxWidth: "640px", margin: "0 auto", textAlign: "center" }}>
                  <div style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", width: "56px", height: "56px", background: "rgba(139,58,58,0.1)", color: "#8b3a3a", borderRadius: "50%", marginBottom: "20px" }}>
                    <X size={28} />
                  </div>
                  <h2 style={{ fontFamily: "Cormorant Garamond, serif", fontSize: "32px", color: "#171717", margin: "0 0 12px" }}>
                    Caso en error
                  </h2>
                  <p style={{ color: "#706f69", fontSize: "14px", lineHeight: 1.6, margin: "0 0 24px" }}>
                    {c.pipeline_error
                      ? "El pipeline no pudo completarse. Revise el detalle arriba. Los casos con síntoma muy extenso pueden fallar por límite de tokens — acorte el texto o cree un caso nuevo."
                      : "Ocurrió un error en el procesamiento. Revise la evidencia gobernada."}
                  </p>
                  {c.survey?.responses_count > 0 && (
                    <p style={{ fontSize: "12px", color: "#706f69", fontFamily: "IBM Plex Mono, monospace" }}>
                      Encuesta: {c.survey.responses_count}/{c.survey.min_responses} respuestas recibidas antes del fallo.
                    </p>
                  )}
                </div>
              ) : (
                <p style={{ color: "#706f69", fontSize: "13px", fontFamily: "IBM Plex Mono, monospace", textAlign: "center" }}>
                  {c.case_status === "rejected"
                    ? "Diagnóstico rechazado. Revise las observaciones del consultor senior."
                    : "Esperando inicialización del ciclo."}
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
