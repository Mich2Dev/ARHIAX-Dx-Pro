/**
 * Traza auditable del caso — el mapa que un consultor/cliente puede inspeccionar.
 *
 * Capas (esfera): Encargo → Método → Campo → Síntesis → Informe → Sello
 * Núcleo: fenómeno nombrado (si existe) — «el fenómeno precede al agente».
 *
 * Cada nodo carga dato real del caso (payload, phenomenon_analysis, survey,
 * pipeline_stages, fusion_result, evidence, deliverables) con peso e id de fuente.
 */

export type NodeKind =
  | "material"
  | "hypothesis"
  | "epoche"
  | "lens"
  | "phenomenon"
  | "triz"
  | "motor"
  | "localize"
  | "kill"
  | "field"
  | "stage"
  | "finding"
  | "document"
  | "gate"
  | "seal"
  | "evidence";

export type NodeStatus = "idle" | "pending" | "running" | "done" | "failed";
export type Activation = "past" | "current" | "future" | "blocked";

export type NetNode = {
  id: string;
  kind: NodeKind;
  label: string;
  short: string;
  status: NodeStatus;
  activation: Activation;
  layerIndex: number;
  layerName: string;
  detail: string;
  signal: string;
  /** 0–1: confianza / impacto / peso auditable */
  weight: number;
  /** ruta de dato (para transparencia) */
  source: string;
  bornAt: number;
  visible: boolean;
  meta: Record<string, string | number | boolean | null>;
  position: [number, number, number];
};

export type Synapse = {
  id: string;
  from: string;
  to: string;
  weight: number;
  live: boolean;
  visible: boolean;
};

export type NeuralCaseGraph = {
  nodes: NetNode[];
  synapses: Synapse[];
  layerLabels: {
    index: number;
    name: string;
    azimuth: number;
    centroid: [number, number, number];
  }[];
  cursorId: string | null;
  progress: number;
  phaseLabel: string;
  methodCoverage: number;
  stats: {
    units: number;
    visible: number;
    live: number;
    gates: number;
    clientName: string;
    caseStatus: string;
  };
};

const LAYER_NAMES = ["Encargo", "Método", "Campo", "Síntesis", "Informe", "Sello"];
const SPHERE_R = 5.5;

const SEVEN_LENSES = [
  { id: "ver", tradition: "Husserl–Heidegger", verb: "Ver" },
  { id: "interpretar", tradition: "Gadamer", verb: "Interpretar" },
  { id: "ampliar", tradition: "B. de Sousa Santos", verb: "Ampliar" },
  { id: "localizar", tradition: "Luhmann", verb: "Localizar" },
  { id: "proteger", tradition: "Benjamin", verb: "Proteger" },
  { id: "resolver", tradition: "TRIZ–Salamatov", verb: "Resolver" },
  { id: "transformar", tradition: "Dewey", verb: "Transformar" },
] as const;

const STAGE_LABELS: Record<string, string> = {
  g10a_scoring: "Scoring",
  g10b_psicometria: "Psicometría",
  g11a_bayesiano: "Bayes",
  g11b_nlp: "Texto libre",
  irr_calculator: "IRR",
  scoring_engine: "Normalización",
  g12_hallazgos: "Hallazgos",
  g13_redactor: "Redacción",
  g14_qa_control: "QA",
};

/** Fuente legible para el consultor (nunca rutas/tablas/códigos de agente). */
export function humanSourceLabel(source: string): string {
  const s = (source || "").trim();
  if (!s || s === "—") return "Registro del caso";
  const map: Record<string, string> = {
    "pro_cases.client_name + input_payload": "Ficha del encargo",
    "input_payload.symptom": "Síntoma del intake",
    "input_payload.paquete_hipotesis": "Hipótesis del intake",
    "input_payload.phenomenon_analysis.p02_epoche": "Análisis · epojé",
    "phenomenon_analysis.p03_convergence": "Análisis · siete puntas",
    "phenomenon_analysis.summary.phenomenon_named": "Fenómeno nombrado",
    "phenomenon_analysis.p04_contradiction.technical_contradiction": "Contradicción técnica (TRIZ)",
    "phenomenon_analysis.p04_contradiction.physical_contradiction": "Contradicción física (TRIZ)",
    "phenomenon_analysis.summary.resolution_motor": "Motor de resolución",
    "phenomenon_analysis.p06_kill_critic": "Kill critic",
    "pro_survey_sessions": "Instrumento de campo",
    "pro_survey_responses": "Respuestas de encuesta",
    fusion_result: "Síntesis consolidada",
    "pipeline_error / fusion_result.error": "Error de ejecución",
    "download/phenomenon-*": "Documento de método",
    "deliverables / render_result": "Informe ejecutivo",
    "pro_cases.approval_status / case_status": "Sello humano",
    "pro_cases.pmel_outcome + trace_id": "Gobernanza del ciclo",
    "pro_evidence": "Registro de evidencia",
  };
  if (map[s]) return map[s];
  if (s.startsWith("pipeline_stages.")) {
    const tool = s.replace("pipeline_stages.", "");
    return `Etapa de síntesis · ${STAGE_LABELS[tool] || "análisis"}`;
  }
  if (/^[a-z0-9_.]+$/i.test(s) && (s.includes("_") || s.includes("."))) {
    return "Registro interno del caso";
  }
  return s;
}

function clip(s: unknown, n: number) {
  const t = String(s ?? "").trim();
  if (!t) return "—";
  return t.length <= n ? t : `${t.slice(0, n - 1)}…`;
}

function confWeight(c: unknown): number {
  const s = String(c ?? "").toUpperCase();
  if (s.includes("ALTA") || s === "HIGH") return 0.92;
  if (s.includes("BAJA") || s === "LOW") return 0.38;
  return 0.62;
}

function spherePos(
  layer: number,
  i: number,
  n: number,
  opts?: { core?: boolean; rScale?: number }
): [number, number, number] {
  if (opts?.core) return [0, 0.08, 0];
  const lon = -Math.PI * 0.9 + (layer / Math.max(LAYER_NAMES.length - 1, 1)) * Math.PI * 1.8;
  const latSpan = Math.min(Math.PI * 0.7, 0.22 + n * 0.1);
  const lat = n <= 1 ? 0 : -latSpan / 2 + (i / Math.max(n - 1, 1)) * latSpan;
  const r = SPHERE_R * (opts?.rScale ?? 1);
  return [
    r * Math.cos(lat) * Math.sin(lon),
    r * Math.sin(lat),
    r * Math.cos(lat) * Math.cos(lon),
  ];
}

function layerAzimuth(layer: number): number {
  return -Math.PI * 0.9 + (layer / Math.max(LAYER_NAMES.length - 1, 1)) * Math.PI * 1.8;
}

function layerCentroid(layer: number): [number, number, number] {
  return spherePos(layer, 0, 1);
}

function stPhen(p: any): NodeStatus {
  const s = p?.status;
  if (s === "running") return "running";
  if (s === "failed" || s === "error") return "failed";
  if (s === "completed" || s === "completed_with_warnings") return "done";
  return p?.summary?.phenomenon_named ? "done" : "idle";
}

function phaseDone(full: any, key: string): boolean {
  if (!full) return false;
  const block = full[key];
  return Boolean(block && (typeof block !== "object" || Object.keys(block).length > 0));
}

function activationOf(status: NodeStatus, isCursor: boolean): Activation {
  if (status === "failed") return "blocked";
  if (isCursor || status === "running") return "current";
  if (status === "done") return "past";
  return "future";
}

export function activationColor(a: Activation): string {
  switch (a) {
    case "past":
      return "#3d8f62";
    case "current":
      return "#d97706";
    case "blocked":
      return "#dc5a4a";
    default:
      return "#9aa3ad";
  }
}

export function statusLabelEs(s: NodeStatus): string {
  switch (s) {
    case "running":
      return "En curso";
    case "done":
      return "Registrado";
    case "failed":
      return "Bloqueado";
    case "pending":
      return "Pendiente";
    default:
      return "Sin dato aún";
  }
}

function lensFindings(full: any): Map<string, string> {
  const map = new Map<string, string>();
  const conv = full?.p03_convergence || {};
  const lenses: any[] = conv.lenses_used || conv.lenses || conv.findings_by_lens || [];
  lenses.forEach((L: any, i: number) => {
    const id = String(L.id || L.lens_id || SEVEN_LENSES[i]?.id || "").toLowerCase();
    const finding = L.finding || L.hallazgo || L.result || L.summary || "";
    if (finding && id) map.set(id, String(finding));
    const trad = String(L.tradition || L.name || "").toLowerCase();
    SEVEN_LENSES.forEach((S) => {
      if (trad.includes(S.id) || trad.includes(S.verb.toLowerCase())) {
        if (finding) map.set(S.id, String(finding));
      }
    });
  });
  return map;
}

function stageSnippet(tool: string, output: any): string {
  if (!output || typeof output !== "object") return "Etapa del pipeline";
  const raw = output.output ?? output;
  switch (tool) {
    case "g10a_scoring": {
      const overall = raw.scoring_summary?.overall_score ?? raw.overall_score;
      return overall != null ? `Score global ${overall}/100` : "Matrices de scoring";
    }
    case "g11a_bayesiano": {
      const c = raw.confirmed_hypotheses?.length ?? 0;
      const r = raw.rejected_hypotheses?.length ?? 0;
      return `${c} hipótesis confirmadas · ${r} rechazadas`;
    }
    case "g12_hallazgos": {
      const total = raw.findings_matrix?.length ?? 0;
      return total ? `${total} hallazgos priorizados` : "Consolidación de hallazgos";
    }
    case "g14_qa_control":
      return raw.qa_score != null ? `QA ${raw.qa_score}/100` : "Control de calidad";
    case "g13_redactor":
      return "Informe ejecutivo redactado";
    default:
      return STAGE_LABELS[tool] || tool;
  }
}

export function caseProgress(caseData: any): { progress: number; phaseLabel: string } {
  const st = caseData?.case_status ?? "draft";
  const phen = caseData?.input_payload?.phenomenon_analysis || caseData?.phenomenon;
  if (st === "approved" || st === "published") return { progress: 1, phaseLabel: "Ciclo sellado · auditable" };
  if (st === "review_pending") return { progress: 0.88, phaseLabel: "Informe listo · espera sello HIL" };
  if (st === "running") return { progress: 0.72, phaseLabel: "Síntesis en ejecución" };
  if (st === "error") return { progress: 0.55, phaseLabel: "Ciclo interrumpido · revisable" };
  if ((caseData?.survey?.responses_count ?? 0) > 0) return { progress: 0.55, phaseLabel: "Campo con respuestas" };
  if (caseData?.survey?.status === "open") return { progress: 0.42, phaseLabel: "Campo abierto" };
  if (stPhen(phen) === "running") return { progress: 0.32, phaseLabel: "Método en curso" };
  if (phen?.summary?.phenomenon_named || caseData?.phenomenon?.summary?.phenomenon_named) {
    return { progress: 0.38, phaseLabel: "Fenómeno nombrado" };
  }
  if (st === "designing") return { progress: 0.18, phaseLabel: "Diseñando instrumento" };
  return { progress: 0.1, phaseLabel: "Encargo recibido" };
}

export function buildNeuralCaseGraph(caseData: any): NeuralCaseGraph {
  const nodes: NetNode[] = [];
  const synapses: Synapse[] = [];
  const { progress, phaseLabel } = caseProgress(caseData);

  const push = (n: Omit<NetNode, "visible" | "activation" | "position"> & { position?: [number, number, number] }) => {
    nodes.push({
      ...n,
      position: n.position || [0, 0, 0],
      activation: "future",
      visible: progress >= n.bornAt - 0.03 || n.status === "running" || n.status === "done" || n.status === "failed",
    });
  };

  const client = caseData?.client_name ?? "Cliente";
  const caseStatus = caseData?.case_status ?? "draft";
  const payload = caseData?.input_payload ?? {};
  const flat = { ...(payload.extra || {}), ...payload };
  const symptom = String(flat.symptom || "");
  const phenSlim = caseData?.phenomenon || {};
  const phenFull = payload.phenomenon_analysis || phenSlim?.result || {};
  const summary = phenSlim.summary || phenFull.summary || {};
  const hasPhen = Boolean(summary.phenomenon_named);
  const p02 = phenFull.p02_epoche;
  const p04 = phenFull.p04_contradiction;
  const p05 = phenFull.p05_localization;
  const p06 = phenFull.p06_kill_critic;
  const findingsByLens = lensFindings(phenFull);
  const survey = caseData?.survey;
  const stages: any[] = caseData?.stages || caseData?.pipeline_stages || [];
  const fusion = caseData?.fusion_result || {};
  const evidence: any[] = caseData?.evidence || [];
  const err = String(caseData?.pipeline_error || fusion.error || "");

  // ── L0 Encargo ───────────────────────────────────────────────────────────
  push({
    id: "mat:client",
    kind: "material",
    label: client,
    short: "CASO",
    status: "done",
    layerIndex: 0,
    layerName: LAYER_NAMES[0],
    detail: [flat.legal_name, flat.city, flat.sector, caseData?.domain].filter(Boolean).join(" · ") || "Encargo",
    signal: "Identidad del encargo consultivo.",
    weight: 1,
    source: "pro_cases.client_name + input_payload",
    bornAt: 0,
    meta: { dominio: caseData?.domain ?? null },
  });
  push({
    id: "mat:symptom",
    kind: "material",
    label: "Síntoma / queja",
    short: "SÍNTOMA",
    status: symptom ? "done" : "idle",
    layerIndex: 0,
    layerName: LAYER_NAMES[0],
    detail: clip(symptom || "Sin síntoma en intake", 280),
    signal: "Material bruto del cliente — punto de partida del diagnóstico.",
    weight: symptom ? 0.95 : 0.2,
    source: "input_payload.symptom",
    bornAt: 0.02,
    meta: {},
  });

  const hyps: any[] = payload.paquete_hipotesis || payload.hypothesis_pack || [];
  hyps.slice(0, 6).forEach((h, i) => {
    const w = confWeight(h.confianza || h.confidence);
    push({
      id: `hyp:${i}`,
      kind: "hypothesis",
      label: clip(h.enunciado || h.statement || h.text || `Hipótesis ${i + 1}`, 48),
      short: `H${i + 1}`,
      status: "done",
      layerIndex: 0,
      layerName: LAYER_NAMES[0],
      detail: clip(
        [h.incidente_texto || h.incident, h.observacion_refutadora ? `Refuta: ${h.observacion_refutadora}` : ""]
          .filter(Boolean)
          .join(" · ") || "Hipótesis del intake",
        260
      ),
      signal: `Peso ${Math.round(w * 100)}% · confianza ${h.confianza || "MEDIA"}.`,
      weight: w,
      source: "input_payload.paquete_hipotesis",
      bornAt: 0.04 + i * 0.01,
      meta: { confianza: h.confianza || null, informante: h.informante_id || null },
    });
  });

  // ── L1 Método ────────────────────────────────────────────────────────────
  const phenStatus = stPhen(phenSlim.status ? phenSlim : phenFull);
  push({
    id: "epoche",
    kind: "epoche",
    label: "Epojé",
    short: "P02",
    status: phaseDone(phenFull, "p02_epoche") ? "done" : phenStatus === "running" ? "running" : "idle",
    layerIndex: 1,
    layerName: LAYER_NAMES[1],
    detail: phaseDone(phenFull, "p02_epoche")
      ? clip(p02?.summary || p02?.epoche_note || "Juicios del cliente suspendidos", 220)
      : "Pendiente: suspender el diagnóstico declarado antes de nombrar.",
    signal: "Operación metodológica · precede al agente.",
    weight: phaseDone(phenFull, "p02_epoche") ? 0.9 : 0.25,
    source: "input_payload.phenomenon_analysis.p02_epoche",
    bornAt: 0.12,
    meta: { fase: "p02_epoche" },
  });

  SEVEN_LENSES.forEach((L, i) => {
    const finding = findingsByLens.get(L.id);
    const done = Boolean(finding) || phaseDone(phenFull, "p03_convergence");
    push({
      id: `lens:${L.id}`,
      kind: "lens",
      label: `${L.verb} · ${L.tradition}`,
      short: `P${i + 1}`,
      status: done ? "done" : phenStatus === "running" ? "running" : "idle",
      layerIndex: 1,
      layerName: LAYER_NAMES[1],
      detail: finding ? clip(finding, 260) : `Lente ${L.tradition} — sin hallazgo registrado aún.`,
      signal: finding ? "Hallazgo triangulado en convergencia." : "Espera análisis de fenómeno.",
      weight: finding ? 0.85 : 0.3,
      source: "phenomenon_analysis.p03_convergence",
      bornAt: 0.16 + i * 0.01,
      meta: { tradición: L.tradition, verbo: L.verb, con_hallazgo: Boolean(finding) },
    });
  });

  // ── Núcleo Φ (sin capa; layerIndex 1.5 visual via core flag on layout) ───
  // Usamos layer 1 for method periphery; phenomenon is core of sphere
  push({
    id: "phenomenon",
    kind: "phenomenon",
    label: hasPhen ? clip(summary.phenomenon_named, 52) : "Fenómeno (sin nombrar)",
    short: "Φ",
    status: hasPhen ? "done" : phenStatus,
    layerIndex: 1,
    layerName: LAYER_NAMES[1],
    detail: hasPhen
      ? clip(summary.convergence_summary || summary.phenomenon_named, 280)
      : "Sin fenómeno nombrado no hay traza metodológica cerrada.",
    signal: "Núcleo del caso · auditable.",
    weight: hasPhen ? 1 : 0.2,
    source: "phenomenon_analysis.summary.phenomenon_named",
    bornAt: 0.28,
    meta: { nombrado: hasPhen, gates: summary.gates_passed ?? null },
  });

  const tech = p04?.technical_contradiction;
  const phys = p04?.physical_contradiction;
  push({
    id: "triz:tech",
    kind: "triz",
    label: "TRIZ · Contradicción técnica",
    short: "TRIZ-T",
    status: tech ? "done" : "idle",
    layerIndex: 1,
    layerName: LAYER_NAMES[1],
    detail: tech
      ? clip(
          typeof tech === "string"
            ? tech
            : `${tech.improving || ""} vs ${tech.worsening || tech.degrading || ""} · ${tech.statement || ""}`,
          240
        )
      : "Aparece tras P04 (contradicción).",
    signal: "Método · TRIZ–Salamatov · lo que el informe nombra como tensión.",
    weight: tech ? 0.88 : 0.2,
    source: "phenomenon_analysis.p04_contradiction.technical_contradiction",
    bornAt: 0.3,
    meta: { en_informe: Boolean(tech) },
  });
  push({
    id: "triz:phys",
    kind: "triz",
    label: "TRIZ · Contradicción física",
    short: "TRIZ-F",
    status: phys ? "done" : "idle",
    layerIndex: 1,
    layerName: LAYER_NAMES[1],
    detail: phys
      ? clip(
          typeof phys === "string"
            ? phys
            : `${phys.statement || phys.parameter || ""} · ${phys.requirement_a || ""} / ${phys.requirement_b || ""}`,
          240
        )
      : "Aparece tras P04 si el caso exige polaridades incompatibles.",
    signal: "Método · TRIZ físico · auditable en el PDF interno/final.",
    weight: phys ? 0.86 : 0.18,
    source: "phenomenon_analysis.p04_contradiction.physical_contradiction",
    bornAt: 0.305,
    meta: { en_informe: Boolean(phys) },
  });
  push({
    id: "motor",
    kind: "motor",
    label: "Motor de resolución",
    short: "MOTOR",
    status: summary.resolution_motor ? "done" : "idle",
    layerIndex: 1,
    layerName: LAYER_NAMES[1],
    detail: summary.resolution_motor
      ? clip(`${summary.resolution_motor} · ${summary.resolution_rule || ""}`, 240)
      : "Pendiente de nombramiento / P04–P05.",
    signal: "Cómo se disuelve la contradicción · sale en el informe.",
    weight: summary.resolution_motor ? 0.9 : 0.2,
    source: "phenomenon_analysis.summary.resolution_motor",
    bornAt: 0.32,
    meta: { regla: summary.resolution_rule ?? null, en_informe: Boolean(summary.resolution_motor) },
  });
  const gates = summary.gates_passed ?? p06?.gates_passed;
  push({
    id: "kill",
    kind: "kill",
    label: "Kill Critic",
    short: "P06",
    status: gates === false ? "failed" : gates === true ? "done" : "idle",
    layerIndex: 1,
    layerName: LAYER_NAMES[1],
    detail:
      gates === false
        ? clip((summary.blocking_reasons || []).join(" · ") || "Gates no pasaron", 240)
        : gates === true
          ? "Gates OK — propuesta comercial solo después de esto."
          : "Compuerta pre-comercial pendiente.",
    signal: "Compuerta antes de propuesta comercial.",
    weight: gates === true ? 0.95 : gates === false ? 0.7 : 0.25,
    source: "phenomenon_analysis.p06_kill_critic",
    bornAt: 0.34,
    meta: { gates_passed: gates ?? null },
  });

  // ── L2 Campo ─────────────────────────────────────────────────────────────
  push({
    id: "field:instrument",
    kind: "field",
    label: "Instrumento de campo",
    short: "Campo",
    status:
      survey?.status === "open"
        ? "done"
        : survey?.status === "designing"
          ? "running"
          : survey
            ? "pending"
            : "idle",
    layerIndex: 2,
    layerName: LAYER_NAMES[2],
    detail: survey
      ? `${survey.question_count ?? "—"} preguntas · ${survey.responses_count ?? 0}/${survey.min_responses ?? "—"} respuestas`
      : "Sin sesión de encuesta.",
    signal: "Instrumento de encuesta del caso.",
    weight: survey?.status === "open" || (survey?.responses_count ?? 0) > 0 ? 0.85 : 0.3,
    source: "pro_survey_sessions",
    bornAt: 0.4,
    meta: {
      respuestas: survey?.responses_count ?? 0,
      minimo: survey?.min_responses ?? null,
      preguntas: survey?.question_count ?? null,
    },
  });
  push({
    id: "field:responses",
    kind: "field",
    label: "Respuestas capturadas",
    short: "RSPS",
    status: (survey?.responses_count ?? 0) > 0 ? "done" : survey?.status === "open" ? "pending" : "idle",
    layerIndex: 2,
    layerName: LAYER_NAMES[2],
    detail:
      (survey?.responses_count ?? 0) > 0
        ? `${survey.responses_count} respuesta(s) capturada(s). Revisá el detalle en Campo o Síntesis.`
        : "Aún sin respuestas. La evidencia de campo queda incompleta.",
    signal: "Evidencia de campo del diagnóstico.",
    weight: Math.min(1, (survey?.responses_count ?? 0) / Math.max(1, survey?.min_responses ?? 1)),
    source: "pro_survey_responses",
    bornAt: 0.44,
    meta: { count: survey?.responses_count ?? 0 },
  });

  // ── L3 Síntesis ──────────────────────────────────────────────────────────
  const orderedTools = [
    "g10a_scoring",
    "g10b_psicometria",
    "g11a_bayesiano",
    "g11b_nlp",
    "irr_calculator",
    "scoring_engine",
    "g12_hallazgos",
    "g13_redactor",
    "g14_qa_control",
  ];
  const stageMap = new Map(stages.map((s: any) => [s.tool_name, s]));
  orderedTools.forEach((tool, i) => {
    const st = stageMap.get(tool);
    const status: NodeStatus =
      st?.status === "completed"
        ? "done"
        : st?.status === "running"
          ? "running"
          : st?.status === "failed"
            ? "failed"
            : caseStatus === "running"
              ? "pending"
              : "idle";
    push({
      id: `stage:${tool}`,
      kind: "stage",
      label: STAGE_LABELS[tool] || tool,
      short: STAGE_LABELS[tool] || tool,
      status,
      layerIndex: 3,
      layerName: LAYER_NAMES[3],
      detail: st ? stageSnippet(tool, st.output) : "Etapa aún no ejecutada en este caso.",
      signal:
        status === "done"
          ? `Completada${st?.latency_ms ? ` · ${Math.round(st.latency_ms / 1000)} s` : ""}`
          : status === "running"
            ? "Ejecutando ahora"
            : "Espera síntesis",
      weight: status === "done" ? 0.8 : status === "running" ? 0.7 : 0.2,
      source: `pipeline_stages.${tool}`,
      bornAt: 0.55 + i * 0.015,
      meta: {
        model: st?.model_used ?? null,
        tokens: st?.tokens_used ?? null,
        latency_ms: st?.latency_ms ?? null,
      },
    });
  });

  if (fusion.executive_thesis || fusion.scoring?.overall_score != null) {
    push({
      id: "find:thesis",
      kind: "finding",
      label: "Tesis ejecutiva",
      short: "TESIS",
      status: "done",
      layerIndex: 3,
      layerName: LAYER_NAMES[3],
      detail: clip(
        fusion.executive_thesis ||
          `Score ${fusion.scoring?.overall_score}/100 · ${fusion.outcome || ""}`,
        280
      ),
      signal: "Salida consolidada para el cliente.",
      weight: 0.92,
      source: "fusion_result",
      bornAt: 0.7,
      meta: {
        score: fusion.scoring?.overall_score ?? null,
        outcome: fusion.outcome ?? null,
      },
    });
  }

  if (err) {
    push({
      id: "gate:error",
      kind: "gate",
      label: "Error / coherencia",
      short: "ERR",
      status: "failed",
      layerIndex: 3,
      layerName: LAYER_NAMES[3],
      detail: clip(err, 280),
      signal: "Bloqueo runtime — parte de la traza auditable.",
      weight: 0.85,
      source: "pipeline_error / fusion_result.error",
      bornAt: 0.71,
      meta: {},
    });
  }

  // ── L4 Informe ───────────────────────────────────────────────────────────
  const docs = [
    { id: "discovery", label: "Formulario descubrimiento", type: "discovery_form", download: true, short: "DSC" },
    { id: "internal", label: "Análisis interno (7 puntas + TRIZ)", type: "internal_phenomenon", download: true, short: "7P" },
    { id: "report", label: "Informe / PDF diagnóstico", type: "executive_report", download: false, short: "PDF" },
  ];
  const recommended: any[] = summary.recommended_documents || [];
  const recTypes = new Set(recommended.map((d: any) => d.type || d.id));
  docs.forEach((d, i) => {
    const ready =
      (d.id === "discovery" || d.id === "internal") && hasPhen
        ? true
        : recTypes.has(d.type) ||
          (d.id === "report" && ["review_pending", "approved", "published"].includes(caseStatus));
    push({
      id: `doc:${d.id}`,
      kind: "document",
      label: d.label,
      short: d.short,
      status: ready ? "done" : hasPhen ? "pending" : "idle",
      layerIndex: 4,
      layerName: LAYER_NAMES[4],
      detail: ready
        ? d.download
          ? "Descargable desde Método. Contiene epojé, siete puntas, TRIZ y kill critic del análisis interno."
          : "Entregable final al cliente (PDF) tras sello — tesis, scores, hallazgos de síntesis."
        : "Aún no generado para este caso.",
      signal: d.id === "report" ? "Lo que el cliente recibe." : "Documento del análisis de fenómeno.",
      weight: ready ? 0.88 : 0.25,
      source: d.download ? `download/phenomenon-*` : "deliverables / render_result",
      bornAt: 0.75 + i * 0.02,
      meta: { type: d.type, ready, en_pdf: d.id === "report" || d.id === "internal" },
    });
  });

  // ── L5 Sello ─────────────────────────────────────────────────────────────
  push({
    id: "seal:hil",
    kind: "seal",
    label: "Validación humana",
    short: "Sello",
    status: ["approved", "published"].includes(caseStatus)
      ? "done"
      : caseStatus === "rejected"
        ? "failed"
        : caseStatus === "review_pending"
          ? "pending"
          : "idle",
    layerIndex: 5,
    layerName: LAYER_NAMES[5],
    detail:
      caseStatus === "approved" || caseStatus === "published"
        ? "Sello humano aplicado · descarga habilitada."
        : caseStatus === "review_pending"
          ? "El informe espera decisión del consultor senior."
          : "Sin ciclo de revisión aún.",
    signal: "Validación humana antes de entregar.",
    weight: ["approved", "published"].includes(caseStatus) ? 1 : 0.35,
    source: "pro_cases.approval_status / case_status",
    bornAt: 0.85,
    meta: { approval: caseData?.approval_status ?? null },
  });
  push({
    id: "seal:pmel",
    kind: "seal",
    label: "Gobernanza del ciclo",
    short: "CTRL",
    status: caseData?.pmel_outcome && caseData.pmel_outcome !== "PENDING" ? "done" : "pending",
    layerIndex: 5,
    layerName: LAYER_NAMES[5],
    detail:
      caseData?.pmel_outcome && caseData.pmel_outcome !== "PENDING"
        ? `Estado de controles: ${
            caseData.pmel_outcome === "PERMIT"
              ? "autorizado"
              : caseData.pmel_outcome === "DENY"
                ? "bloqueado"
                : String(caseData.pmel_outcome).toLowerCase()
          }.`
        : "Controles del ciclo aún pendientes.",
    signal: "Decisión de gobernanza del ciclo.",
    weight: 0.7,
    source: "pro_cases.pmel_outcome + trace_id",
    bornAt: 0.87,
    meta: { outcome: caseData?.pmel_outcome ?? null },
  });

  evidence.slice(0, 8).forEach((e, i) => {
    const outcomeLabel =
      e.outcome === "PERMIT"
        ? "autorizado"
        : e.outcome === "DENY"
          ? "bloqueado"
          : e.outcome || "registrado";
    push({
      id: `ev:${i}`,
      kind: "evidence",
      label: String(e.event_type || `Evento ${i + 1}`)
        .replace(/_/g, " ")
        .replace(/\b\w/g, (ch: string) => ch.toUpperCase()),
      short: "EV",
      status: e.outcome === "DENY" ? "failed" : "done",
      layerIndex: 5,
      layerName: LAYER_NAMES[5],
      detail: clip(`${outcomeLabel}.`, 200),
      signal: "Registro de evidencia del ciclo.",
      weight: 0.55,
      source: "pro_evidence",
      bornAt: 0.88 + i * 0.005,
      meta: { outcome: e.outcome ?? null },
    });
  });

  // Layout esférico
  for (let L = 0; L < LAYER_NAMES.length; L++) {
    const group = nodes.filter((n) => n.layerIndex === L && n.id !== "phenomenon");
    group.forEach((n, i) => {
      n.position = spherePos(L, i, group.length, {
        rScale: n.kind === "evidence" ? 1.08 : n.kind === "stage" ? 0.95 : 1,
      });
    });
  }
  const phenNode = nodes.find((n) => n.id === "phenomenon");
  if (phenNode) phenNode.position = spherePos(1, 0, 1, { core: true });

  // Coverage metodológica + operativa
  const methodChecks = [
    phaseDone(phenFull, "p02_epoche"),
    phaseDone(phenFull, "p03_convergence") || hasPhen,
    hasPhen,
    Boolean(tech || phys || summary.resolution_motor),
    gates === true,
    (survey?.responses_count ?? 0) > 0,
    stages.some((s: any) => s.status === "completed"),
    ["approved", "published", "review_pending"].includes(caseStatus),
  ];
  const methodCoverage = methodChecks.filter(Boolean).length / methodChecks.length;

  let cursorId: string | null = null;
  if (caseStatus === "running") {
    cursorId = nodes.find((n) => n.status === "running")?.id ?? "stage:g10a_scoring";
  } else if (phenStatus === "running") cursorId = "epoche";
  else if (err) cursorId = "gate:error";
  else if (caseStatus === "review_pending") cursorId = "seal:hil";
  else if (!hasPhen) cursorId = "mat:symptom";
  else if ((survey?.responses_count ?? 0) === 0 && survey?.status === "open") cursorId = "field:instrument";
  else if (hasPhen && !stages.length) cursorId = "field:responses";
  else cursorId = "phenomenon";

  nodes.forEach((n) => {
    n.activation = activationOf(n.status, n.id === cursorId);
  });

  const link = (from: string, to: string, weight: number) => {
    const a = nodes.find((n) => n.id === from);
    const b = nodes.find((n) => n.id === to);
    if (!a || !b) return;
    synapses.push({
      id: `${from}→${to}`,
      from,
      to,
      weight,
      live: a.activation === "current" || b.activation === "current",
      visible: a.visible && b.visible,
    });
  };

  link("mat:client", "mat:symptom", 0.7);
  link("mat:symptom", "epoche", 0.9);
  hyps.slice(0, 6).forEach((_, i) => link(`hyp:${i}`, "epoche", 0.55 + confWeight(hyps[i]?.confianza) * 0.2));
  SEVEN_LENSES.forEach((L) => {
    link("epoche", `lens:${L.id}`, 0.55);
    link(`lens:${L.id}`, "phenomenon", 0.9);
  });
  link("phenomenon", "triz:tech", 0.85);
  link("phenomenon", "triz:phys", 0.7);
  link("triz:tech", "motor", 0.88);
  link("triz:phys", "motor", 0.75);
  link("motor", "kill", 0.9);
  link("kill", "field:instrument", 0.55);
  link("field:instrument", "field:responses", 0.8);
  link("field:responses", "stage:g10a_scoring", 0.75);
  for (let i = 0; i < orderedTools.length - 1; i++) {
    link(`stage:${orderedTools[i]}`, `stage:${orderedTools[i + 1]}`, 0.7);
  }
  link("stage:g14_qa_control", "doc:report", 0.65);
  link("phenomenon", "doc:discovery", 0.7);
  link("phenomenon", "doc:internal", 0.75);
  link("doc:report", "seal:hil", 0.85);
  link("seal:hil", "seal:pmel", 0.6);
  evidence.slice(0, 4).forEach((_, i) => link("seal:pmel", `ev:${i}`, 0.4));
  if (nodes.some((n) => n.id === "find:thesis")) {
    link("stage:g13_redactor", "find:thesis", 0.85);
    link("find:thesis", "doc:report", 0.8);
  }
  if (nodes.some((n) => n.id === "gate:error")) link("stage:g12_hallazgos", "gate:error", 0.5);

  return {
    nodes,
    synapses,
    layerLabels: LAYER_NAMES.map((name, index) => ({
      index,
      name,
      azimuth: layerAzimuth(index),
      centroid: layerCentroid(index),
    })),
    cursorId,
    progress,
    phaseLabel,
    methodCoverage,
    stats: {
      units: nodes.length,
      visible: nodes.filter((n) => n.visible).length,
      live: synapses.filter((s) => s.live).length,
      gates: nodes.filter((n) => n.kind === "kill" || n.kind === "gate").length,
      clientName: client,
      caseStatus,
    },
  };
}

/** Familias para filtrar el mapa (método fenomenológico vs informe / pipeline). */
export type GraphFilterId =
  | "all"
  | "metodo"
  | "triz"
  | "field"
  | "pipeline"
  | "report"
  | "seal";

export const GRAPH_FILTERS: {
  id: GraphFilterId;
  label: string;
  hint: string;
  kinds?: NodeKind[];
  ids?: string[];
}[] = [
  { id: "all", label: "Todo", hint: "Ciclo completo" },
  {
    id: "metodo",
    label: "Método",
    hint: "Epojé · 7 puntas · Φ · Kill",
    kinds: ["epoche", "lens", "phenomenon", "triz", "motor", "kill"],
  },
  {
    id: "triz",
    label: "TRIZ",
    hint: "Contradicciones + motor",
    kinds: ["triz", "motor"],
    ids: ["lens:resolver"],
  },
  {
    id: "field",
    label: "Campo",
    hint: "Encuesta y respuestas",
    kinds: ["field"],
  },
  {
    id: "pipeline",
    label: "Síntesis",
    hint: "G10–G14 · scores · tesis",
    kinds: ["stage", "finding", "gate"],
  },
  {
    id: "report",
    label: "Informe / PDF",
    hint: "Docs + tesis que salen al cliente",
    kinds: ["document", "finding"],
  },
  {
    id: "seal",
    label: "Sello",
    hint: "HIL · evidencia",
    kinds: ["seal", "evidence"],
  },
];

export function nodeMatchesFilter(n: NetNode, filter: GraphFilterId): boolean {
  if (filter === "all") return true;
  const def = GRAPH_FILTERS.find((f) => f.id === filter);
  if (!def) return true;
  if (def.ids?.includes(n.id)) return true;
  if (def.kinds?.includes(n.kind)) return true;
  return false;
}

export function kindHue(kind: NodeKind): string {
  switch (kind) {
    case "triz":
      return "#c47a28";
    case "motor":
      return "#d4a017";
    case "epoche":
    case "lens":
    case "phenomenon":
    case "kill":
      return "#3f6b4e";
    case "field":
      return "#9b6d4d";
    case "stage":
    case "finding":
    case "gate":
      return "#243c4f";
    case "document":
      return "#56624b";
    case "seal":
    case "evidence":
      return "#6b4f3a";
    case "material":
    case "hypothesis":
      return "#8b7355";
    default:
      return "#9aa3ad";
  }
}

export function familyLabel(kind: NodeKind): string {
  switch (kind) {
    case "epoche":
    case "lens":
    case "phenomenon":
    case "triz":
    case "motor":
    case "kill":
      return "Método";
    case "field":
      return "Campo";
    case "stage":
    case "finding":
    case "gate":
      return "Síntesis / motor";
    case "document":
      return "Informe / PDF";
    case "seal":
    case "evidence":
      return "Sello";
    case "material":
    case "hypothesis":
      return "Encargo";
    default:
      return "Otro";
  }
}
