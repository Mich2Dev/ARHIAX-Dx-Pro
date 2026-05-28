import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import type { DecisionStatus, DiagnosticStatus } from "@/lib/types";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(iso?: string): string {
  if (!iso) return "—";
  return new Intl.DateTimeFormat("es-CO", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "America/Bogota",
  }).format(new Date(iso));
}

export function statusVariant(status: DiagnosticStatus) {
  const map: Record<DiagnosticStatus, "blue" | "orange" | "green" | "red" | "gray" | "yellow"> = {
    pending:             "yellow",
    running:             "blue",
    awaiting_review:     "orange",
    awaiting_responses:  "blue",
    completed:           "green",
    denied:              "red",
    failed:              "gray",
  };
  return map[status] ?? "gray";
}

export function statusLabel(status: DiagnosticStatus | string): string {
  const map: Record<string, string> = {
    pending:             "Pendiente",
    running:             "Ejecutando",
    awaiting_review:     "En revisión",
    awaiting_responses:  "Esperando encuesta",
    completed:           "Completado",
    denied:              "Denegado",
    failed:              "Fallido",
  };
  return map[status] ?? status;
}

export function decisionVariant(decision: DecisionStatus) {
  const map: Record<DecisionStatus, "green" | "red" | "orange" | "blue"> = {
    ALLOW:                      "green",
    DENY:                       "red",
    ESCALATE_TO_HUMAN:          "orange",
    ALLOW_WITH_HIC_NOTIFICATION:"blue",
  };
  return map[decision] ?? "gray";
}
