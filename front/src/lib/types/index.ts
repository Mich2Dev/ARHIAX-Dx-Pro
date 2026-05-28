export type DiagnosticStatus =
  | "pending" | "running" | "awaiting_review" | "awaiting_responses"
  | "completed" | "denied" | "failed";

export type DecisionStatus =
  | "ALLOW" | "DENY" | "ESCALATE_TO_HUMAN" | "ALLOW_WITH_HIC_NOTIFICATION";

export interface DiagnosticSummary {
  id: string;
  request_id: string;
  organization_name: string;
  domain: string;
  status: DiagnosticStatus;
  decision?: DecisionStatus;
  created_at: string;
}

export interface PipelineStage {
  id: string;
  tool_name: string;
  phase: string;
  status: "pending" | "running" | "completed" | "failed";
  model_used?: string;
  tokens_used?: number;
  latency_ms?: number;
}

export interface RuleResult {
  rule_id: string;
  description: string;
  outcome: "PASS" | "FAIL" | "ESCALATE" | "LOG_ONLY";
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  message: string;
}

export interface HumanReview {
  id: string;
  diagnostic_id: string;
  organization_name: string;
  domain: string;
  review_type: "publication" | "irr_followup" | "critical_gap" | "autonomy_promotion";
  status: "pending" | "approved" | "rejected";
  created_at: string;
}

export interface ProcessingProfile {
  store_raw_respondent_data: boolean;
  publish_report: boolean;
  issue_certificate: boolean;
  retention_days: number;
}

// ── Paso 1: datos completos del cliente ──────────────────────────────────────
export interface ClientData {
  // Identidad
  organization_name: string;
  legal_name: string;
  nit: string;
  sector: string;
  city: string;
  country: string;
  size_org: string;           // número de empleados
  years_operating: string;
  // Contacto
  contact_name: string;
  contact_role: string;
  contact_email: string;
  contact_phone: string;
  // El problema
  area: string;               // área a diagnosticar
  symptom: string;            // síntoma principal (texto libre)
  problem_since: string;      // hace cuánto
  previous_attempts: string;  // qué intentaron antes
  expected_outcome: string;   // qué esperan obtener
  // Alcance
  areas_count: string;        // cuántas áreas/sedes
  survey_participants: string;// cuántas personas en encuesta
  deadline: string;           // fecha límite (opcional)
  confidentiality: string;
}

// ── Paso 2: profundidad del diagnóstico ──────────────────────────────────────
export type DiagnosticDepth = "basic" | "standard" | "complete";

export interface DiagnosticFormData {
  // Paso 1
  client: ClientData;
  // Paso 2
  depth: DiagnosticDepth;
  publish_report: boolean;
  issue_certificate: boolean;
  // Derivados (calculados automáticamente)
  client_id: string;
  requested_tools: string[];
  requested_operations: string[];
  requested_data_scopes: string[];
  requested_autonomy_level: string;
  processing_profile: ProcessingProfile;
}
