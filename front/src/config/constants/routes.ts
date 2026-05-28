/**
 * Application route paths
 * Rutas de la aplicación
 */

export const ROUTES = {
  // Auth
  LOGIN: "/login",
  
  // Dashboard
  DASHBOARD: "/dashboard",
  DIAGNOSTICS: "/dashboard/diagnostics",
  DIAGNOSTICS_NEW: "/dashboard/diagnostics/new",
  DIAGNOSTICS_DETAIL: (id: string) => `/dashboard/diagnostics/${id}`,
  
  // Admin
  ADMIN: "/dashboard/admin",
  CLIENTS: "/dashboard/clients",
  LEDGER: "/dashboard/ledger",
  
  // Survey
  SURVEY: (token: string) => `/survey/${token}`,
} as const;
