"use client";

/**
 * CaseWorkspace — estudio del caso (vistas, no cola hacia un PDF).
 *
 * Trabajo: Encargo · Método · Campo · Síntesis · Sello
 * Explorar: Mapa · Documentos (paquete de artefactos cuando existen)
 *
 * El sello habilita el informe ejecutivo; no es “el fin” del producto.
 * Cada vista demuestra una cara del sistema.
 */

import { useEffect, useMemo, useState, type CSSProperties } from "react";
import Link from "next/link";
import {
  Check,
  ChevronLeft,
  Copy,
  Cpu,
  Loader2,
  Send,
  ShieldCheck,
  CheckCircle,
  X,
  Map,
  AlertTriangle,
  FileText,
} from "lucide-react";
import { formatDate } from "@/lib/utils";
import { ProPhenomenonPanel } from "@/components/features/pro/ProPhenomenonPanel";
import { CaseDecisionBrainLazy } from "@/components/features/pro/CaseDecisionBrainLazy";
import { ProFusionPipeline } from "@/components/features/pro/ProFusionPipeline";
import {
  ProResultsPanel,
  ProGovernancePanel,
  ProExecutionMetrics,
} from "@/components/features/pro/ProResultsPanel";
import { SurveyAuditPanel } from "@/components/features/diagnostics/SurveyAuditPanel";

export type WorkspaceSection =
  | "encargo"
  | "metodo"
  | "campo"
  | "sintesis"
  | "sello"
  | "docs"
  | "mapa";

const STATUS_COLOR: Record<string, string> = {
  draft: "#706f69",
  designing: "#243c4f",
  survey_open: "#9b6d4d",
  running: "#243c4f",
  review_pending: "#9b6d4d",
  approved: "#56624b",
  published: "#56624b",
  rejected: "#8b3a3a",
  error: "#8b3a3a",
};

const STATUS_LABEL: Record<string, string> = {
  draft: "Borrador",
  designing: "Diseñando instrumento",
  survey_open: "Campo abierto",
  running: "Síntesis en curso",
  review_pending: "Listo para sellar",
  approved: "Sellado",
  published: "Publicado",
  rejected: "Rechazado",
  error: "Error",
};

type SectionDef = {
  id: WorkspaceSection;
  n: string;
  label: string;
  hint: string;
};

/** Vistas de trabajo — importantes entre sí, no una fila hacia el PDF. */
const WORK_VIEWS: SectionDef[] = [
  { id: "encargo", n: "01", label: "Encargo", hint: "Dolor / material" },
  { id: "metodo", n: "02", label: "Método", hint: "Fenómeno · TRIZ · 7P" },
  { id: "campo", n: "03", label: "Campo", hint: "Evidencia viva" },
  { id: "sintesis", n: "04", label: "Síntesis", hint: "Hallazgos" },
  { id: "sello", n: "05", label: "Sello", hint: "Firma humana" },
];

/** Vistas de exploración — demuestran el sistema, no “cierran” el caso. */
const EXPLORE_VIEWS: SectionDef[] = [
  { id: "mapa", n: "◉", label: "Mapa 3D", hint: "Globo del caso" },
  { id: "docs", n: "◇", label: "Documentos", hint: "Paquete del caso" },
];

type Props = {
  caseId: string;
  caseData: any;
  isFetching?: boolean;
  reviewComment: string;
  onReviewComment: (v: string) => void;
  onAnalyze: () => void;
  analyzing: boolean;
  onRun: () => void;
  runningDiag: boolean;
  onApprove: (action: "approve" | "reject") => void;
  approving: boolean;
  approveError?: boolean;
  onRefresh: () => void;
};

function inferSection(c: any): WorkspaceSection {
  const st = c.case_status;
  if (st === "review_pending" || st === "rejected") return "sello";
  if (st === "running" || st === "error") return "sintesis";
  if (st === "survey_open" || c.survey?.status === "open") return "campo";
  if (st === "designing" || c.survey?.status === "designing") return "campo";
  if (c.phenomenon?.summary?.phenomenon_named) return "metodo";
  return "encargo";
}

function sectionDone(id: WorkspaceSection, c: any): boolean {
  const st = c.case_status;
  switch (id) {
    case "encargo":
      return Boolean(c.client_name);
    case "metodo":
      return Boolean(c.phenomenon?.summary?.phenomenon_named);
    case "campo":
      return ["running", "review_pending", "approved", "published", "rejected"].includes(st)
        || (c.survey?.responses_count ?? 0) > 0;
    case "sintesis":
      return ["review_pending", "approved", "published"].includes(st);
    case "sello":
      return ["approved", "published"].includes(st);
    case "docs":
      return Boolean(c.phenomenon?.summary?.phenomenon_named)
        || ["review_pending", "approved", "published"].includes(st);
    case "mapa":
      return Boolean(c.phenomenon?.summary?.phenomenon_named) || (c.survey?.responses_count ?? 0) > 0;
    default:
      return false;
  }
}

function hypList(c: any): any[] {
  const p = c.input_payload || {};
  return (
    p.paquete_hipotesis ||
    p.hypothesis_pack ||
    p.scope?.hypothesis_pack ||
    []
  ).slice(0, 8);
}

function PrimaryCta({
  c,
  analyzing,
  runningDiag,
  approving,
  onAnalyze,
  onRun,
  onGo,
}: {
  c: any;
  analyzing: boolean;
  runningDiag: boolean;
  approving: boolean;
  onAnalyze: () => void;
  onRun: () => void;
  onGo: (s: WorkspaceSection) => void;
}) {
  const st = c.case_status;
  const phenOk = Boolean(c.phenomenon?.summary?.phenomenon_named);
  const phenRunning = c.phenomenon?.status === "running" || analyzing;
  const surveyOpen = c.survey?.status === "open";
  const busy = analyzing || runningDiag || approving || st === "running" || phenRunning;

  if (st === "review_pending") {
    return (
      <button type="button" onClick={() => onGo("sello")} style={ctaPrimary}>
        <ShieldCheck size={14} /> Abrir sello
      </button>
    );
  }
  if (st === "running") {
    return (
      <button type="button" onClick={() => onGo("sintesis")} style={ctaGhost} disabled>
        <Loader2 size={14} style={{ animation: "spin 1s linear infinite" }} /> Sintetizando…
      </button>
    );
  }
  if (st === "survey_open" && surveyOpen) {
    const canRun = (c.survey?.responses_count ?? 0) > 0;
    return (
      <button
        type="button"
        onClick={() => (canRun ? onRun() : onGo("campo"))}
        disabled={busy || !canRun}
        style={canRun ? ctaPrimary : ctaGhost}
      >
        {runningDiag ? <Loader2 size={14} style={{ animation: "spin 1s linear infinite" }} /> : <Cpu size={14} />}
        {canRun ? "Lanzar síntesis" : "Esperando respuestas"}
      </button>
    );
  }
  if (st === "designing" || c.survey?.status === "designing") {
    return (
      <button type="button" onClick={() => onGo("campo")} style={ctaGhost} disabled>
        <Loader2 size={14} style={{ animation: "spin 1s linear infinite" }} /> Diseñando instrumento…
      </button>
    );
  }
  if (!phenOk) {
    return (
      <button type="button" onClick={onAnalyze} disabled={busy} style={ctaPrimary}>
        {phenRunning ? <Loader2 size={14} style={{ animation: "spin 1s linear infinite" }} /> : null}
        {phenRunning ? "Nombrando fenómeno…" : "Analizar fenómeno"}
      </button>
    );
  }
  if (["approved", "published"].includes(st)) {
    return (
      <button type="button" onClick={() => onGo("mapa")} style={ctaPrimary}>
        <Map size={14} /> Explorar mapa
      </button>
    );
  }
  if (st === "error") {
    return (
      <button
        type="button"
        onClick={() => ((c.survey?.responses_count ?? 0) > 0 ? onRun() : onGo("sintesis"))}
        disabled={busy}
        style={ctaPrimary}
      >
        {runningDiag ? <Loader2 size={14} style={{ animation: "spin 1s linear infinite" }} /> : <Cpu size={14} />}
        Reintentar
      </button>
    );
  }
  return (
    <button type="button" onClick={() => onGo("campo")} style={ctaPrimary}>
      Abrir campo
    </button>
  );
}

const ctaPrimary: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: 8,
  minHeight: 42,
  padding: "0 18px",
  background: "#171717",
  color: "#f4f1ea",
  border: "none",
  fontSize: 12,
  fontFamily: "IBM Plex Mono, monospace",
  fontWeight: 600,
  letterSpacing: "0.06em",
  cursor: "pointer",
};

const ctaGhost: CSSProperties = {
  ...ctaPrimary,
  background: "transparent",
  color: "#706f69",
  border: "1px solid rgba(23,23,23,0.14)",
  cursor: "default",
};

export function CaseWorkspace(props: Props) {
  const {
    caseId,
    caseData: c,
    isFetching,
    reviewComment,
    onReviewComment,
    onAnalyze,
    analyzing,
    onRun,
    runningDiag,
    onApprove,
    approving,
    approveError,
    onRefresh,
  } = props;

  const [section, setSection] = useState<WorkspaceSection>(() => inferSection(c));
  const [copied, setCopied] = useState(false);

  // Auto-jump when status moves the work forward (don't fight manual browse)
  useEffect(() => {
    const next = inferSection(c);
    setSection((prev) => {
      // If user is already ahead on sello/sintesis reviewing, don't yank them back
      if (prev === "sello" && ["review_pending", "approved", "published", "rejected"].includes(c.case_status)) {
        return prev;
      }
      return next;
    });
  }, [c.case_status, c.phenomenon?.status, c.survey?.status, c.survey?.responses_count]);

  const statusColor = STATUS_COLOR[c.case_status] ?? "#706f69";
  const hyps = useMemo(() => hypList(c), [c]);
  const payload = c.input_payload || {};
  // Al crear el caso, `extra` se aplana en el root de input_payload (no queda anidado).
  const extra = { ...(payload.extra || {}), ...payload };
  const symptom = payload.symptom || extra.symptom || "";
  const isDone = ["review_pending", "approved", "published"].includes(c.case_status);
  const canApprove = c.case_status === "review_pending";
  const surveyUrl =
    typeof window !== "undefined" && c.survey?.token
      ? `${window.location.origin}/survey/pro/${c.survey.token}`
      : c.survey?.token
        ? `/survey/pro/${c.survey.token}`
        : "";

  async function copySurvey() {
    if (!surveyUrl) return;
    try {
      await navigator.clipboard.writeText(surveyUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      window.alert(surveyUrl);
    }
  }

  return (
    <div style={{ fontFamily: "Manrope, sans-serif", paddingBottom: 48 }}>
      <style>{`
        .cw-rail {
          position: sticky; top: 0; z-index: 20;
          background: rgba(244,241,234,0.94);
          backdrop-filter: blur(10px);
          border-bottom: 1px solid rgba(23,23,23,0.1);
          margin: 0 -4px; padding: 0 4px;
        }
        .cw-sections {
          display: flex; gap: 4px; overflow-x: auto;
          padding: 10px 0 12px;
          scrollbar-width: none;
        }
        .cw-sections::-webkit-scrollbar { display: none; }
        .cw-stage {
          margin-top: 28px;
          display: grid;
          grid-template-columns: minmax(0, 1.05fr) minmax(320px, 0.95fr);
          gap: 20px;
          align-items: start;
        }
        .cw-stage.is-mapa {
          grid-template-columns: 1fr;
        }
        .cw-panel {
          min-width: 0;
          animation: cwIn 0.28s ease;
        }
        .cw-brain-dock {
          position: sticky;
          top: 64px;
          min-width: 0;
          animation: cwBrainIn 0.55s ease;
        }
        .cw-stage.is-mapa .cw-brain-dock {
          position: relative;
          top: auto;
        }
        @keyframes cwIn {
          from { opacity: 0; transform: translateY(6px); }
          to { opacity: 1; transform: none; }
        }
        @keyframes cwBrainIn {
          from { opacity: 0; transform: translateX(10px) scale(0.985); }
          to { opacity: 1; transform: none; }
        }
        @media (max-width: 1100px) {
          .cw-stage {
            grid-template-columns: 1fr;
          }
          .cw-brain-dock {
            position: relative;
            top: auto;
            order: -1;
          }
          .cw-stage.is-mapa .cw-brain-dock { order: 0; }
        }
        @media (max-width: 860px) {
          .cw-head { flex-direction: column; align-items: stretch !important; }
          .cw-head-actions { justify-content: flex-start !important; }
          .cw-encargo-grid { grid-template-columns: 1fr !important; }
          .cw-campo-stats { grid-template-columns: 1fr 1fr 1fr !important; }
          .cw-sello-grid { grid-template-columns: 1fr !important; }
          .cw-evidence-row { grid-template-columns: 1fr 1fr !important; }
        }
      `}</style>

      {/* ── Header del caso ─────────────────────────────────────────────── */}
      <div
        className="cw-head"
        style={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          gap: 20,
          paddingBottom: 18,
          borderBottom: "1px solid rgba(23,23,23,0.1)",
        }}
      >
        <div style={{ minWidth: 0, flex: 1 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
            <Link
              href="/dashboard-pro"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 4,
                color: "#706f69",
                fontSize: 11,
                fontFamily: "IBM Plex Mono, monospace",
                textDecoration: "none",
              }}
            >
              <ChevronLeft size={12} /> Casos
            </Link>
            <span style={{ color: "rgba(23,23,23,0.2)" }}>·</span>
            <span style={{ fontSize: 11, fontFamily: "IBM Plex Mono, monospace", color: "#56624b" }}>
              {c.case_id ?? caseId}
            </span>
          </div>
          <h1
            style={{
              margin: "10px 0 0",
              fontFamily: "Cormorant Garamond, Georgia, serif",
              fontWeight: 500,
              fontSize: "clamp(32px, 5vw, 48px)",
              lineHeight: 0.95,
              color: "#171717",
            }}
          >
            {c.client_name}
          </h1>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 12, flexWrap: "wrap" }}>
            <span
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
                padding: "4px 10px",
                fontSize: 11,
                fontFamily: "IBM Plex Mono, monospace",
                background: `${statusColor}14`,
                color: statusColor,
                border: `1px solid ${statusColor}35`,
              }}
            >
              {(c.case_status === "running" || c.phenomenon?.status === "running") && (
                <Loader2 size={10} style={{ animation: "spin 1s linear infinite" }} />
              )}
              {STATUS_LABEL[c.case_status] ?? c.case_status}
            </span>
            <span style={{ fontSize: 12, color: "#706f69" }}>{c.domain}</span>
            <span style={{ fontSize: 12, color: "#9ca3af" }}>{formatDate(c.created_at)}</span>
          </div>
          {c.next_step && (
            <p
              style={{
                margin: "14px 0 0",
                fontSize: 13,
                color: "#3f4a3a",
                lineHeight: 1.5,
                maxWidth: 640,
                borderLeft: "2px solid #56624b",
                paddingLeft: 12,
              }}
            >
              <span
                style={{
                  display: "block",
                  fontSize: 10,
                  fontFamily: "IBM Plex Mono, monospace",
                  color: "#56624b",
                  letterSpacing: "0.08em",
                  marginBottom: 4,
                }}
              >
                AHORA
              </span>
              {c.next_step}
            </p>
          )}
        </div>

        <div className="cw-head-actions" style={{ display: "flex", gap: 8, flexShrink: 0, flexWrap: "wrap", justifyContent: "flex-end" }}>
          <PrimaryCta
            c={c}
            analyzing={analyzing}
            runningDiag={runningDiag}
            approving={approving}
            onAnalyze={onAnalyze}
            onRun={onRun}
            onGo={setSection}
          />
        </div>
      </div>

      {c.case_status === "error" && c.pipeline_error && (
        <div
          style={{
            marginTop: 16,
            padding: "14px 16px",
            borderLeft: "3px solid #8b3a3a",
            background: "rgba(139,58,58,0.06)",
            border: "1px solid rgba(139,58,58,0.25)",
          }}
        >
          <p style={{ margin: 0, fontSize: 12, fontWeight: 600, color: "#8b3a3a", display: "flex", gap: 8, alignItems: "center" }}>
            <AlertTriangle size={14} /> Error del pipeline
          </p>
          <p
            style={{
              margin: "8px 0 0",
              fontSize: 12,
              color: "#706f69",
              fontFamily: "IBM Plex Mono, monospace",
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
            }}
          >
            {c.pipeline_error}
          </p>
        </div>
      )}

      {/* ── Rail: trabajo + explorar (pares, no cola) ─────────────────────── */}
      <div className="cw-rail">
        <div className="cw-rail-inner" style={{ display: "flex", gap: 16, alignItems: "stretch", padding: "10px 0 12px", overflowX: "auto" }}>
          <nav aria-label="Trabajo del caso" style={{ display: "flex", gap: 4, flex: "0 0 auto" }}>
            <span
              style={{
                alignSelf: "center",
                fontSize: 9,
                fontFamily: "IBM Plex Mono, monospace",
                color: "#706f69",
                letterSpacing: "0.1em",
                marginRight: 6,
                writingMode: "horizontal-tb",
              }}
            >
              TRABAJO
            </span>
            {WORK_VIEWS.map((s) => (
              <ViewTab key={s.id} s={s} active={section === s.id} done={sectionDone(s.id, c)} onClick={() => setSection(s.id)} />
            ))}
          </nav>
          <div style={{ width: 1, alignSelf: "stretch", background: "rgba(23,23,23,0.12)", flex: "0 0 1px" }} />
          <nav aria-label="Explorar el sistema" style={{ display: "flex", gap: 4, flex: "0 0 auto" }}>
            <span
              style={{
                alignSelf: "center",
                fontSize: 9,
                fontFamily: "IBM Plex Mono, monospace",
                color: "#706f69",
                letterSpacing: "0.1em",
                marginRight: 6,
              }}
            >
              EXPLORAR
            </span>
            {EXPLORE_VIEWS.map((s) => (
              <ViewTab key={s.id} s={s} active={section === s.id} done={sectionDone(s.id, c)} onClick={() => setSection(s.id)} />
            ))}
          </nav>
        </div>
      </div>

      {/* ── Contenido + mapa 3D persistente (Canvas no se desmonta al cambiar vista) ── */}
      <div className={`cw-stage${section === "mapa" ? " is-mapa" : ""}`}>
        <div className="cw-panel" key={section}>
          {section === "encargo" && (
            <EncargoSection c={c} symptom={symptom} hyps={hyps} extra={extra} onGoMetodo={() => setSection("metodo")} />
          )}

          {section === "metodo" && (
            <div>
              <SectionIntro
                kicker="Cómo se piensa el caso"
                title="Método"
                body="Epojé, siete puntas, fenómeno, TRIZ y kill critic. El globo a la derecha sigue la capa Método en vivo."
              />
              <ProPhenomenonPanel
                phenomenon={c.phenomenon}
                caseId={caseId}
                analyzing={analyzing}
                onAnalyze={onAnalyze}
              />

              <div style={{ marginTop: 16, display: "flex", justifyContent: "flex-start", gap: 12, flexWrap: "wrap" }}>
                <button
                  type="button"
                  onClick={() => setSection("mapa")}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 8,
                    padding: "10px 14px",
                    background: "#fff",
                    color: "#171717",
                    border: "1px solid rgba(23,23,23,0.14)",
                    fontSize: 12,
                    fontFamily: "IBM Plex Mono, monospace",
                    cursor: "pointer",
                  }}
                >
                  <Map size={14} /> Ampliar mapa 3D
                </button>
                <button
                  type="button"
                  onClick={() => setSection("docs")}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 8,
                    padding: "10px 14px",
                    background: "#fff",
                    color: "#171717",
                    border: "1px solid rgba(23,23,23,0.14)",
                    fontSize: 12,
                    fontFamily: "IBM Plex Mono, monospace",
                    cursor: "pointer",
                  }}
                >
                  <FileText size={14} /> Documentos del método
                </button>
                {c.phenomenon?.summary?.phenomenon_named && (
                  <button type="button" onClick={() => setSection("campo")} style={ctaGhost}>
                    Abrir campo
                  </button>
                )}
              </div>
            </div>
          )}

          {section === "campo" && (
            <CampoSection
              c={c}
              surveyUrl={surveyUrl}
              copied={copied}
              onCopy={copySurvey}
              onRun={onRun}
              runningDiag={runningDiag}
              onGoSintesis={() => setSection("sintesis")}
            />
          )}

          {section === "sintesis" && (
            <div>
              <SectionIntro
                kicker="Motor de hallazgos"
                title="Síntesis"
                body="Tesis, scores y etapas de consolidación. El mapa 3D acompaña el avance sin salirte de esta vista."
              />
              {(c.case_status === "running" || (c.stages ?? c.pipeline_stages)?.length > 0) && (
                <ProFusionPipeline caseData={c} isFetching={isFetching} />
              )}
              {isDone && (c.fusion_result || c.report_result) && (
                <div style={{ marginTop: 16 }}>
                  <ProResultsPanel caseData={c} caseId={caseId} onRefresh={onRefresh} showDownloads={false} />
                </div>
              )}
              {c.survey?.token && isDone && (
                <div style={{ marginTop: 16 }}>
                  <SurveyAuditPanel surveyToken={c.survey.token} isPro={true} />
                </div>
              )}
              {!isDone && c.case_status !== "running" && !(c.stages ?? c.pipeline_stages)?.length && (
                <EmptyHint text="Todavía no hay etapas de síntesis. Completá campo y lanzá el diagnóstico." />
              )}
              <div style={{ marginTop: 24, display: "flex", gap: 10, flexWrap: "wrap" }}>
                <button type="button" onClick={() => setSection("mapa")} style={ctaGhost}>
                  <Map size={14} /> Ampliar mapa 3D
                </button>
                {canApprove && (
                  <button type="button" onClick={() => setSection("sello")} style={ctaPrimary}>
                    <ShieldCheck size={14} /> Abrir sello
                  </button>
                )}
              </div>
            </div>
          )}

          {section === "sello" && (
            <SelloSection
              c={c}
              canApprove={canApprove}
              reviewComment={reviewComment}
              onReviewComment={onReviewComment}
              onApprove={onApprove}
              approving={approving}
              approveError={approveError}
              onGo={(id) => setSection(id)}
            />
          )}

          {section === "docs" && (
            <DocsHub
              c={c}
              caseId={caseId}
              onRefresh={onRefresh}
              onGo={(id) => setSection(id)}
            />
          )}

          {section === "mapa" && (
            <SectionIntro
              kicker="Traza viva del caso"
              title="Mapa 3D"
              body="Globo completo: método, campo, síntesis, documentos y sello. Girás, tocás fases y ves la deducción entera sin salir del caso."
            />
          )}
        </div>

        <aside className="cw-brain-dock" aria-label="Mapa 3D del caso">
          <CaseDecisionBrainLazy
            caseData={c}
            variant={section === "mapa" ? "full" : "companion"}
            section={section}
          />
        </aside>
      </div>
    </div>
  );
}

function SectionIntro({ kicker, title, body }: { kicker: string; title: string; body: string }) {
  return (
    <div style={{ marginBottom: 22, maxWidth: 640 }}>
      <p style={{ margin: 0, fontSize: 11, fontFamily: "IBM Plex Mono, monospace", color: "#56624b", letterSpacing: "0.08em" }}>
        {kicker}
      </p>
      <h2
        style={{
          margin: "6px 0 0",
          fontFamily: "Cormorant Garamond, Georgia, serif",
          fontWeight: 500,
          fontSize: 36,
          lineHeight: 1,
          color: "#171717",
        }}
      >
        {title}
      </h2>
      <p style={{ margin: "10px 0 0", fontSize: 14, color: "#706f69", lineHeight: 1.55 }}>{body}</p>
    </div>
  );
}

function ViewTab({
  s,
  active,
  done,
  onClick,
}: {
  s: SectionDef;
  active: boolean;
  done: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        flex: "0 0 auto",
        display: "flex",
        alignItems: "center",
        gap: 10,
        padding: "10px 14px",
        border: active ? "1px solid #171717" : "1px solid rgba(23,23,23,0.1)",
        background: active ? "#171717" : done ? "rgba(86,98,75,0.08)" : "#fff",
        color: active ? "#f4f1ea" : "#171717",
        cursor: "pointer",
        textAlign: "left",
        minWidth: 120,
      }}
    >
      <span
        style={{
          width: 22,
          height: 22,
          display: "grid",
          placeItems: "center",
          fontSize: 10,
          fontFamily: "IBM Plex Mono, monospace",
          border: active ? "1px solid rgba(244,241,234,0.35)" : "1px solid rgba(23,23,23,0.2)",
          background: done && !active ? "#56624b" : "transparent",
          color: done && !active ? "#f4f1ea" : "inherit",
        }}
      >
        {done && !active ? <Check size={11} /> : s.n}
      </span>
      <span>
        <span style={{ display: "block", fontSize: 12, fontWeight: 600, fontFamily: "IBM Plex Mono, monospace" }}>
          {s.label}
        </span>
        <span style={{ display: "block", fontSize: 10, opacity: active ? 0.65 : 0.55, marginTop: 2 }}>{s.hint}</span>
      </span>
    </button>
  );
}

function DocsHub({
  c,
  caseId,
  onRefresh,
  onGo,
}: {
  c: any;
  caseId: string;
  onRefresh: () => void;
  onGo: (s: WorkspaceSection) => void;
}) {
  const phenOk = Boolean(c.phenomenon?.summary?.phenomenon_named);
  const sealed = ["approved", "published"].includes(c.case_status);
  const hasSynth = Boolean(c.fusion_result || c.report_result);
  const phenName = c.phenomenon?.summary?.phenomenon_named || "—";

  const cards: {
    id: string;
    title: string;
    body: string;
    ready: boolean;
    action?: () => void;
    actionLabel?: string;
  }[] = [
    {
      id: "interno",
      title: "Análisis interno (método)",
      body: phenOk
        ? `Epojé, siete puntas, TRIZ y kill critic del fenómeno «${phenName}». Disponible en Método.`
        : "Se genera cuando el fenómeno queda nombrado.",
      ready: phenOk,
      action: () => onGo("metodo"),
      actionLabel: "Abrir Método",
    },
    {
      id: "campo",
      title: "Campo / respuestas",
      body:
        (c.survey?.responses_count ?? 0) > 0
          ? `${c.survey.responses_count} respuesta(s) auditables — variabilidad de rater.`
          : "Sin respuestas aún; el paquete de evidencia está incompleto.",
      ready: (c.survey?.responses_count ?? 0) > 0,
      action: () => onGo("campo"),
      actionLabel: "Abrir Campo",
    },
    {
      id: "sintesis",
      title: "Síntesis (hallazgos)",
      body: hasSynth
        ? "Tesis, scores y pipeline — la lectura cuantitativa del caso."
        : "Aparece cuando corre G10–G14.",
      ready: hasSynth,
      action: () => onGo("sintesis"),
      actionLabel: "Abrir Síntesis",
    },
    {
      id: "mapa",
      title: "Mapa de traza",
      body: "Grafo filtrable: Método, TRIZ, síntesis, docs. Aquí se ve la diferenciación del caso.",
      ready: phenOk || (c.survey?.responses_count ?? 0) > 0,
      action: () => onGo("mapa"),
      actionLabel: "Abrir Mapa",
    },
    {
      id: "informe",
      title: "Informe ejecutivo",
      body: sealed
        ? "PDF / DOCX / MD del diagnóstico listo para descargar."
        : "Se descarga cuando el sello humano está aplicado. Mientras, explorá Método, Síntesis y Mapa.",
      ready: sealed,
      action: sealed ? undefined : () => onGo("sello"),
      actionLabel: sealed ? undefined : "Abrir Sello",
    },
  ];

  return (
    <div>
      <SectionIntro
        kicker="Descargas del caso"
        title="Documentos"
        body="Solo archivos y accesos. Los hallazgos se leen en Síntesis; el método en Método. Acá no se repite el mismo panel."
      />

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))",
          gap: 12,
          marginBottom: 24,
        }}
      >
        {cards.map((card) => (
          <div
            key={card.id}
            style={{
              border: "1px solid rgba(23,23,23,0.12)",
              background: card.ready ? "#fff" : "rgba(244,241,234,0.45)",
              padding: 18,
              display: "flex",
              flexDirection: "column",
              gap: 10,
              minHeight: 150,
            }}
          >
            <p
              style={{
                margin: 0,
                fontSize: 10,
                fontFamily: "IBM Plex Mono, monospace",
                color: card.ready ? "#56624b" : "#9b6d4d",
                letterSpacing: "0.06em",
              }}
            >
              {card.ready ? "DISPONIBLE" : "PENDIENTE"}
            </p>
            <h3 style={{ margin: 0, fontSize: 16, fontFamily: "Cormorant Garamond, Georgia, serif", fontWeight: 500 }}>
              {card.title}
            </h3>
            <p style={{ margin: 0, fontSize: 12, color: "#54534d", lineHeight: 1.45, flex: 1 }}>{card.body}</p>
            {card.action && card.actionLabel && (
              <button type="button" onClick={card.action} style={{ ...ctaGhost, alignSelf: "flex-start" }}>
                {card.actionLabel}
              </button>
            )}
          </div>
        ))}
      </div>

      {sealed ? (
        <div>
          <p style={{ margin: "0 0 12px", fontSize: 12, fontFamily: "IBM Plex Mono, monospace", color: "#706f69" }}>
            INFORME EJECUTIVO · PDF / DOCX / MD
          </p>
          <ProResultsPanel caseData={c} caseId={caseId} onRefresh={onRefresh} showDownloads />
        </div>
      ) : (
        <EmptyHint text="El informe descargable aparece acá después del sello. Para tesis y scores, abrí Síntesis." />
      )}
    </div>
  );
}

function EmptyHint({ text }: { text: string }) {
  return (
    <div
      style={{
        padding: "28px 24px",
        border: "1px dashed rgba(23,23,23,0.16)",
        background: "rgba(244,241,234,0.5)",
        textAlign: "center",
        color: "#706f69",
        fontSize: 13,
        fontFamily: "IBM Plex Mono, monospace",
      }}
    >
      {text}
    </div>
  );
}

function EncargoSection({
  c,
  symptom,
  hyps,
  extra,
  onGoMetodo,
}: {
  c: any;
  symptom: string;
  hyps: any[];
  extra: any;
  onGoMetodo: () => void;
}) {
  const grey: string[] = c.input_payload?.grey_sources || [];
  return (
    <div>
      <SectionIntro
        kicker="Material en bruto"
        title="Encargo"
        body="Lo que el cliente trae antes de suspender juicios. Acá no se decide todavía — se lee."
      />

      <div className="cw-encargo-grid" style={{ display: "grid", gridTemplateColumns: "minmax(0, 1.4fr) minmax(0, 1fr)", gap: 20 }}>
        <div style={{ background: "#fff", border: "1px solid rgba(23,23,23,0.1)", padding: "24px 26px" }}>
          <p style={metaLabel}>Síntoma / queja</p>
          <p style={{ margin: "10px 0 0", fontSize: 16, lineHeight: 1.55, color: "#171717", fontFamily: "Cormorant Garamond, Georgia, serif" }}>
            {symptom || "Sin síntoma registrado en el intake."}
          </p>
          {extra.expected_outcome && (
            <div style={{ marginTop: 22 }}>
              <p style={metaLabel}>Resultado esperado</p>
              <p style={{ margin: "8px 0 0", fontSize: 14, color: "#3f4a3a", lineHeight: 1.5 }}>{extra.expected_outcome}</p>
            </div>
          )}
          {extra.previous_attempts && (
            <div style={{ marginTop: 18 }}>
              <p style={metaLabel}>Intentos previos</p>
              <p style={{ margin: "8px 0 0", fontSize: 13, color: "#706f69", lineHeight: 1.5 }}>{extra.previous_attempts}</p>
            </div>
          )}
        </div>

        <div style={{ display: "grid", gap: 12, alignContent: "start" }}>
          <MetaBlock label="Contacto" value={[extra.contact_name, extra.contact_role].filter(Boolean).join(" · ") || "—"} />
          <MetaBlock label="Organización" value={[extra.legal_name || c.client_name, extra.city, extra.country].filter(Boolean).join(" · ")} />
          <MetaBlock label="Desde cuándo" value={extra.problem_since || "—"} />
          <MetaBlock label="Áreas" value={extra.areas_count || "—"} />
        </div>
      </div>

      <div style={{ marginTop: 28 }}>
        <p style={metaLabel}>Hipótesis del intake</p>
        {hyps.length === 0 ? (
          <EmptyHint text="No hay paquete de hipótesis en el intake." />
        ) : (
          <div style={{ display: "grid", gap: 8, marginTop: 12 }}>
            {hyps.map((h: any, i: number) => (
              <div
                key={i}
                style={{
                  display: "grid",
                  gridTemplateColumns: "64px 1fr",
                  gap: 14,
                  padding: "14px 16px",
                  background: "#fff",
                  border: "1px solid rgba(23,23,23,0.08)",
                }}
              >
                <span style={{ fontSize: 10, fontFamily: "IBM Plex Mono, monospace", color: "#9b6d4d" }}>
                  {h.confianza || h.confidence || "MEDIA"}
                </span>
                <div>
                  <p style={{ margin: 0, fontSize: 14, color: "#171717", fontWeight: 500 }}>
                    {h.enunciado || h.statement || h.text || `Hipótesis ${i + 1}`}
                  </p>
                  {(h.incidente_texto || h.incident) && (
                    <p style={{ margin: "6px 0 0", fontSize: 12, color: "#706f69", lineHeight: 1.45 }}>
                      {h.incidente_texto || h.incident}
                    </p>
                  )}
                  {h.observacion_refutadora && (
                    <p style={{ margin: "6px 0 0", fontSize: 12, color: "#56624b", lineHeight: 1.45 }}>
                      Refuta: {h.observacion_refutadora}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {grey.length > 0 && (
        <div style={{ marginTop: 24 }}>
          <p style={metaLabel}>Fuentes grises</p>
          <ul style={{ margin: "8px 0 0", paddingLeft: 18, color: "#706f69", fontSize: 13, lineHeight: 1.6 }}>
            {grey.map((g, i) => (
              <li key={i}>{g}</li>
            ))}
          </ul>
        </div>
      )}

      <div style={{ marginTop: 28, display: "flex", justifyContent: "flex-end" }}>
        <button type="button" onClick={onGoMetodo} style={ctaPrimary}>
          Abrir método
        </button>
      </div>
    </div>
  );
}

function MetaBlock({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ background: "#fff", border: "1px solid rgba(23,23,23,0.08)", padding: "14px 16px" }}>
      <p style={metaLabel}>{label}</p>
      <p style={{ margin: "6px 0 0", fontSize: 13, color: "#171717", lineHeight: 1.4 }}>{value}</p>
    </div>
  );
}

const metaLabel: CSSProperties = {
  margin: 0,
  fontSize: 10,
  fontFamily: "IBM Plex Mono, monospace",
  color: "#9b6d4d",
  letterSpacing: "0.08em",
  textTransform: "uppercase",
};

function CampoSection({
  c,
  surveyUrl,
  copied,
  onCopy,
  onRun,
  runningDiag,
  onGoSintesis,
}: {
  c: any;
  surveyUrl: string;
  copied: boolean;
  onCopy: () => void;
  onRun: () => void;
  runningDiag: boolean;
  onGoSintesis: () => void;
}) {
  const designing = c.case_status === "designing" || c.survey?.status === "designing";
  const open = c.survey?.status === "open";
  const evidence = c.evidence ?? [];

  if (designing) {
    return (
      <div>
        <SectionIntro
          kicker="Instrumento en construcción"
          title="Campo"
          body="Los agentes están armando las preguntas del caso. Cuando termine, vas a poder compartir el enlace."
        />
        <div style={{ display: "grid", gap: 10, maxWidth: 560 }}>
          {[
            { id: "G09a", label: "Arquitectura de preguntas" },
            { id: "G09b", label: "Lógica de ramificación" },
            { id: "G09c", label: "Validación de integridad" },
          ].map((agent, i) => {
            const ev = evidence.find(
              (e: any) =>
                e.agent === agent.id ||
                (agent.id === "G09a" && e.event_type === "survey_questions_generated")
            );
            const done = !!ev;
            const active =
              !done &&
              (i === 0 ||
                evidence.some((e: any) => e.agent === (i === 1 ? "G09a" : "G09b")));
            return (
              <div
                key={agent.id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 14,
                  padding: "16px 18px",
                  background: "#fff",
                  border: "1px solid rgba(23,23,23,0.1)",
                  opacity: done || active ? 1 : 0.45,
                }}
              >
                {done ? (
                  <div style={{ width: 28, height: 28, background: "#56624b", display: "grid", placeItems: "center" }}>
                    <Check size={14} color="#f4f1ea" />
                  </div>
                ) : active ? (
                  <Loader2 size={22} style={{ color: "#243c4f", animation: "spin 1s linear infinite" }} />
                ) : (
                  <div style={{ width: 28, height: 28, border: "1px solid rgba(23,23,23,0.15)" }} />
                )}
                <div>
                  <p style={{ margin: 0, fontSize: 13, fontWeight: 600, color: "#171717" }}>{agent.label}</p>
                  <p style={{ margin: "4px 0 0", fontSize: 11, fontFamily: "IBM Plex Mono, monospace", color: "#706f69" }}>
                    {done ? "Listo" : active ? "En curso" : "En espera"}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  if (!c.survey && !open) {
    return (
      <div>
        <SectionIntro kicker="Campo" title="Campo" body="Todavía no hay sesión de encuesta en este caso." />
        <EmptyHint text="Volvé a método o esperá a que el instrumento se genere." />
      </div>
    );
  }

  const responses = c.survey?.responses_count ?? 0;
  const min = c.survey?.min_responses ?? 1;
  const canRun = responses > 0 && ["survey_open", "error"].includes(c.case_status);

  return (
    <div>
      <SectionIntro
        kicker="Recolección"
        title="Campo"
        body="Distribuí el enlace, seguí las respuestas y recién entonces lanzá la síntesis. El mapa no sustituye esto."
      />

      <div
        className="cw-campo-stats"
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
          gap: 12,
          marginBottom: 20,
        }}
      >
        <Stat value={String(responses)} label="Respuestas" />
        <Stat value={String(min)} label="Mínimo" />
        <Stat value={String(c.survey?.question_count ?? "—")} label="Preguntas" />
      </div>

      {open && surveyUrl && (
        <div style={{ background: "#fff", border: "1px solid rgba(23,23,23,0.1)", padding: 20, marginBottom: 20 }}>
          <p style={metaLabel}>Enlace seguro</p>
          <div style={{ display: "flex", gap: 10, marginTop: 10, flexWrap: "wrap" }}>
            <input
              readOnly
              value={surveyUrl}
              style={{
                flex: "1 1 220px",
                minWidth: 0,
                padding: "12px 14px",
                border: "1px solid rgba(23,23,23,0.12)",
                fontSize: 12,
                fontFamily: "IBM Plex Mono, monospace",
                background: "#f4f1ea",
                color: "#171717",
              }}
            />
            <button
              type="button"
              onClick={onCopy}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
                padding: "0 18px",
                background: "#171717",
                color: "#f4f1ea",
                border: "none",
                fontSize: 12,
                fontFamily: "IBM Plex Mono, monospace",
                cursor: "pointer",
              }}
            >
              <Copy size={13} /> {copied ? "Copiado" : "Copiar"}
            </button>
            <a
              href={surveyUrl}
              target="_blank"
              rel="noreferrer"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
                padding: "0 16px",
                border: "1px solid rgba(23,23,23,0.14)",
                color: "#171717",
                fontSize: 12,
                fontFamily: "IBM Plex Mono, monospace",
                textDecoration: "none",
                minHeight: 42,
              }}
            >
              <Send size={13} /> Abrir
            </a>
          </div>
        </div>
      )}

      {(c.survey?.role_labels?.length ?? 0) > 0 && (
        <div style={{ marginBottom: 20 }}>
          <p style={metaLabel}>Roles esperados</p>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 10 }}>
            {(c.survey.role_labels as string[]).map((label: string) => (
              <span
                key={label}
                style={{
                  padding: "5px 10px",
                  fontSize: 11,
                  fontFamily: "IBM Plex Mono, monospace",
                  background: "#fff",
                  border: "1px solid rgba(23,23,23,0.12)",
                }}
              >
                {label}
              </span>
            ))}
          </div>
        </div>
      )}

      {canRun && (
        <button
          type="button"
          onClick={onRun}
          disabled={runningDiag}
          style={{ ...ctaPrimary, width: "100%", minHeight: 52, display: "inline-flex", justifyContent: "center" }}
        >
          {runningDiag ? <Loader2 size={16} style={{ animation: "spin 1s linear infinite" }} /> : <Cpu size={16} />}
          {runningDiag ? "Iniciando síntesis…" : "Lanzar síntesis de diagnóstico"}
        </button>
      )}

      {responses > 0 && responses < min && (
        <p style={{ margin: "12px 0 0", fontSize: 12, color: "#9b6d4d", textAlign: "center" }}>
          Podés lanzar con {responses} respuesta(s); el mínimo declarado es {min}.
        </p>
      )}

      {["running", "review_pending", "approved", "published"].includes(c.case_status) && (
        <div style={{ marginTop: 20, display: "flex", justifyContent: "flex-end" }}>
          <button type="button" onClick={onGoSintesis} style={ctaPrimary}>
            Ver síntesis →
          </button>
        </div>
      )}
    </div>
  );
}

function Stat({ value, label }: { value: string; label: string }) {
  return (
    <div style={{ background: "#fff", border: "1px solid rgba(23,23,23,0.1)", padding: "18px 16px", textAlign: "center" }}>
      <p style={{ margin: 0, fontSize: 36, fontFamily: "Cormorant Garamond, Georgia, serif", color: "#171717", lineHeight: 1 }}>
        {value}
      </p>
      <p style={{ margin: "8px 0 0", fontSize: 10, fontFamily: "IBM Plex Mono, monospace", color: "#706f69", letterSpacing: "0.06em" }}>
        {label.toUpperCase()}
      </p>
    </div>
  );
}

function SelloSection({
  c,
  canApprove,
  reviewComment,
  onReviewComment,
  onApprove,
  approving,
  approveError,
  onGo,
}: {
  c: any;
  canApprove: boolean;
  reviewComment: string;
  onReviewComment: (v: string) => void;
  onApprove: (action: "approve" | "reject") => void;
  approving: boolean;
  approveError?: boolean;
  onGo?: (s: WorkspaceSection) => void;
}) {
  const [showTech, setShowTech] = useState(false);
  const fusion = c.fusion_result ?? {};
  const thesis = String(fusion.executive_thesis ?? "").trim();
  const nextStep = String(fusion.recommended_next_step ?? "").trim();
  const phenName =
    c.phenomenon?.summary?.phenomenon_named ||
    c.phenomenon?.named_phenomenon ||
    "—";
  const responses = c.survey?.responses_count ?? 0;
  const sealed = c.case_status === "approved" || c.case_status === "published";
  const rejected = c.case_status === "rejected";

  const checks = [
    { ok: Boolean(c.client_name), label: "Encargo del cliente cargado" },
    { ok: Boolean(c.phenomenon?.summary?.phenomenon_named), label: `Fenómeno nombrado: ${phenName}` },
    { ok: responses > 0, label: `${responses} respuesta(s) de campo` },
    { ok: Boolean(thesis || fusion.scoring), label: "Síntesis con hallazgos listos" },
  ];

  return (
    <div>
      <SectionIntro
        kicker="Tu firma profesional"
        title="Sello"
        body="Confirmás que la lectura del caso es defendible ante el cliente. Con tu firma queda habilitada la descarga del informe."
      />

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(0, 1.15fr) minmax(240px, 0.85fr)",
          gap: 20,
          alignItems: "start",
        }}
        className="cw-sello-grid"
      >
        <div style={{ background: "#fff", border: "1px solid rgba(23,23,23,0.12)", padding: 28 }}>
          <p style={{ margin: 0, fontSize: 11, fontFamily: "IBM Plex Mono, monospace", color: "#9b6d4d", letterSpacing: "0.08em" }}>
            ¿QUÉ ESTÁS APROBANDO?
          </p>
          <h3
            style={{
              margin: "10px 0 0",
              fontSize: 26,
              fontFamily: "Cormorant Garamond, Georgia, serif",
              fontWeight: 500,
              color: "#171717",
              lineHeight: 1.2,
            }}
          >
            {sealed
              ? "Caso sellado"
              : rejected
                ? "Caso rechazado"
                : canApprove
                  ? "Revisá y sellá el diagnóstico"
                  : "Todavía no hay nada que sellar"}
          </h3>
          <p style={{ margin: "12px 0 0", fontSize: 14, color: "#54534d", lineHeight: 1.55, maxWidth: 520 }}>
            {sealed
              ? "Ya firmaste. Podés abrir Mapa o Documentos cuando quieras."
              : rejected
                ? "Quedó marcado como rechazado. Volvé a síntesis o método y corregí."
                : canApprove
                  ? "Estás confirmando coherencia consultiva: dolor, método, campo y síntesis. No estás firmando un botón de descarga."
                  : c.case_status === "running"
                    ? "La síntesis sigue corriendo. Cuando termine, volvé acá."
                    : "Faltan piezas (método, campo o síntesis) para poder firmar."}
          </p>

          <ul style={{ margin: "22px 0 0", padding: 0, listStyle: "none", display: "grid", gap: 10 }}>
            {checks.map((ch) => (
              <li
                key={ch.label}
                style={{
                  display: "flex",
                  gap: 10,
                  alignItems: "flex-start",
                  fontSize: 13,
                  color: ch.ok ? "#2f3a2c" : "#706f69",
                  lineHeight: 1.4,
                }}
              >
                <span
                  style={{
                    width: 18,
                    height: 18,
                    borderRadius: 999,
                    flexShrink: 0,
                    marginTop: 1,
                    background: ch.ok ? "rgba(86,98,75,0.15)" : "rgba(23,23,23,0.06)",
                    color: ch.ok ? "#56624b" : "#9aa3ad",
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: 11,
                  }}
                >
                  {ch.ok ? "✓" : "·"}
                </span>
                <span>{ch.label}</span>
              </li>
            ))}
          </ul>

          {thesis && (
            <div
              style={{
                marginTop: 24,
                padding: "16px 18px",
                background: "rgba(244,241,234,0.65)",
                borderLeft: "3px solid #9b6d4d",
              }}
            >
              <p style={{ margin: 0, fontSize: 10, fontFamily: "IBM Plex Mono, monospace", color: "#9b6d4d", letterSpacing: "0.08em" }}>
                TESIS DEL CASO
              </p>
              <p style={{ margin: "10px 0 0", fontSize: 15, fontFamily: "Cormorant Garamond, Georgia, serif", lineHeight: 1.45, color: "#171717" }}>
                {thesis.length > 420 ? `${thesis.slice(0, 418)}…` : thesis}
              </p>
              {nextStep && (
                <p style={{ margin: "12px 0 0", fontSize: 12, color: "#54534d", lineHeight: 1.45 }}>
                  Próximo paso sugerido: {nextStep.length > 180 ? `${nextStep.slice(0, 178)}…` : nextStep}
                </p>
              )}
            </div>
          )}

          {canApprove && (
            <div style={{ marginTop: 22, display: "grid", gap: 10 }}>
              <label style={{ display: "grid", gap: 6 }}>
                <span style={{ fontSize: 11, fontFamily: "IBM Plex Mono, monospace", color: "#706f69" }}>
                  Nota para el registro (opcional)
                </span>
                <textarea
                  value={reviewComment}
                  onChange={(e) => onReviewComment(e.target.value)}
                  placeholder="Ej.: Lectura coherente con el campo; listo para firmar."
                  rows={3}
                  style={{
                    width: "100%",
                    boxSizing: "border-box",
                    border: "1px solid rgba(23,23,23,0.16)",
                    padding: "12px",
                    background: "#fff",
                    color: "#171717",
                    fontFamily: "Manrope, sans-serif",
                    fontSize: 13,
                    resize: "vertical",
                  }}
                />
              </label>
              <button
                type="button"
                onClick={() => onApprove("approve")}
                disabled={approving}
                style={{
                  ...ctaPrimary,
                  background: "#56624b",
                  width: "100%",
                  minHeight: 48,
                }}
              >
                <CheckCircle size={14} />
                {approving ? "Sellando…" : "Aprobar lectura del caso"}
              </button>
              <button
                type="button"
                onClick={() => onApprove("reject")}
                disabled={approving}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 8,
                  minHeight: 40,
                  background: "transparent",
                  border: "1px solid rgba(139,58,58,0.35)",
                  color: "#8b3a3a",
                  fontSize: 12,
                  fontFamily: "IBM Plex Mono, monospace",
                  cursor: "pointer",
                }}
              >
                <X size={12} /> Rechazar lectura
              </button>
              {approveError && (
                <p style={{ margin: 0, color: "#8b3a3a", fontSize: 12 }}>
                  No se pudo registrar la decisión. Reintentá.
                </p>
              )}
            </div>
          )}

          {sealed && onGo && (
            <div style={{ marginTop: 22, display: "flex", gap: 10, flexWrap: "wrap" }}>
              <button type="button" onClick={() => onGo("mapa")} style={ctaPrimary}>
                <Map size={14} /> Explorar mapa
              </button>
              <button type="button" onClick={() => onGo("docs")} style={ctaGhost}>
                <FileText size={14} /> Abrir documentos
              </button>
            </div>
          )}
        </div>

        <aside style={{ display: "grid", gap: 14 }}>
          <div style={{ background: "#222522", color: "#f4f1ea", padding: 20 }}>
            <p style={{ margin: 0, fontSize: 10, fontFamily: "IBM Plex Mono, monospace", color: "rgba(244,241,234,0.45)", letterSpacing: "0.08em" }}>
              VISTAS DEL SISTEMA
            </p>
            <ul style={{ margin: "14px 0 0", padding: "0 0 0 18px", display: "grid", gap: 10, fontSize: 13, lineHeight: 1.4 }}>
              <li>Método — fenómeno y contradicción</li>
              <li>Campo — evidencia</li>
              <li>Síntesis — hallazgos</li>
              <li style={{ fontWeight: 600 }}>Sello — tu firma</li>
              <li>Mapa / Documentos — explorar</li>
            </ul>
          </div>

          <div style={{ border: "1px solid rgba(23,23,23,0.12)", padding: 16, background: "#fff" }}>
            <p style={{ margin: 0, fontSize: 12, color: "#54534d", lineHeight: 1.5 }}>
              Si la tesis no sostiene el dolor del encargo, rechazá y corregí antes de firmar.
            </p>
          </div>
        </aside>
      </div>

      <div style={{ marginTop: 28 }}>
        <button
          type="button"
          onClick={() => setShowTech((v) => !v)}
          style={{
            background: "transparent",
            border: "none",
            padding: 0,
            fontSize: 11,
            fontFamily: "IBM Plex Mono, monospace",
            color: "#706f69",
            cursor: "pointer",
            textDecoration: "underline",
            textUnderlineOffset: 3,
          }}
        >
          {showTech ? "Ocultar detalle técnico" : "Ver detalle técnico (gobernanza / evidencia)"}
        </button>
        {showTech && (
          <div style={{ marginTop: 14, display: "grid", gap: 12 }}>
            <ProGovernancePanel caseData={c} />
            <ProExecutionMetrics caseData={c} />
            {(c.evidence ?? []).length > 0 && (
              <div>
                <p style={metaLabel}>Evidencia · {c.evidence.length}</p>
                <div style={{ marginTop: 10, display: "grid", gap: 1, background: "rgba(23,23,23,0.1)" }}>
                  {c.evidence.map((e: any, i: number) => (
                    <div
                      key={i}
                      style={{
                        background: "#fff",
                        padding: "12px 14px",
                        display: "grid",
                        gridTemplateColumns: "minmax(120px, 180px) 1fr 80px 110px",
                        gap: 10,
                        alignItems: "center",
                        fontSize: 11,
                        fontFamily: "IBM Plex Mono, monospace",
                      }}
                    >
                      <span style={{ color: "#9b6d4d" }}>{e.event_type}</span>
                      <span style={{ color: "#706f69", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {e.trace_id ?? "—"}
                      </span>
                      <span style={{ color: e.outcome === "PERMIT" ? "#56624b" : "#9b6d4d" }}>{e.outcome ?? "—"}</span>
                      <span style={{ color: "#706f69" }}>{formatDate(e.created_at)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
