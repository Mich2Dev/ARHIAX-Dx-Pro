/**
 * Application route paths
 * Rutas de la aplicación
 */

export const ROUTES = {
  // Auth
  LOGIN: "/login",

  // App principal (unificada)
  DASHBOARD: "/dashboard-pro",
  CASES_NEW: "/dashboard-pro/new",
  CASE_DETAIL: (id: string) => `/dashboard-pro/cases/${id}`,
  CLIENTS: "/dashboard-pro/clients",
  REVIEWS: "/dashboard-pro/reviews",
  EVIDENCE: "/dashboard-pro/evidence",
  COMPLIANCE: "/dashboard-pro/compliance",

  // Rutas legacy — el middleware redirige a dashboard-pro
  LEGACY_DASHBOARD: "/dashboard",
  LEGACY_DIAGNOSTICS_NEW: "/dashboard/diagnostics/new",
  LEGACY_DIAGNOSTICS_DETAIL: (id: string) => `/dashboard/diagnostics/${id}`,

  // Survey
  SURVEY: (token: string) => `/survey/${token}`,
  SURVEY_PRO: (token: string) => `/survey/pro/${token}`,
} as const;
