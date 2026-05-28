/**
 * Status labels and variants for diagnostics
 * Etiquetas y variantes de estado para diagnósticos
 */

export const STATUS_LABELS: Record<string, string> = {
  pending:             "Pendiente",
  running:             "Ejecutando",
  awaiting_review:     "En revisión",
  awaiting_responses:  "Esperando encuesta",
  completed:           "Completado",
  denied:              "Denegado",
  failed:              "Fallido",
};

export const DECISION_LABELS: Record<string, string> = {
  ALLOW:                       "Aprobado",
  DENY:                        "Denegado",
  ESCALATE_TO_HUMAN:           "Escalado",
  ALLOW_WITH_HIC_NOTIFICATION: "Aprobado c/notif.",
};
