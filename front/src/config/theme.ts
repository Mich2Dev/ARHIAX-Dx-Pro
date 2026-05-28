/**
 * Design tokens — paleta industrial ARHIAX
 * Usar estas constantes en vez de hardcodear colores/fonts.
 */

export const C = {
  ink:     "#171717",
  char:    "#222522",
  gray:    "#706f69",
  paper:   "#f4f1ea",
  moss:    "#56624b",
  clay:    "#9b6d4d",
  navy:    "#243c4f",
  red:     "#8b3a3a",
  border:  "rgba(23,23,23,0.14)",
  borderSm:"rgba(23,23,23,0.08)",
  cardBg:  "rgba(244,241,234,0.96)",
  glassBg: "rgba(255,255,255,0.72)",
} as const;

export const F = {
  mono:  "IBM Plex Mono, monospace",
  serif: "Cormorant Garamond, Georgia, serif",
  sans:  "Manrope, sans-serif",
} as const;

export const S = {
  xs:  "10px",
  sm:  "11px",
  md:  "13px",
  lg:  "16px",
} as const;

/** Badge de estado para casos Pro */
export const PRO_STATUS_COLOR: Record<string, string> = {
  draft:        C.gray,
  running:      C.navy,
  review_ready: C.clay,
  approved:     C.moss,
  published:    C.moss,
  rejected:     C.red,
};

export const PRO_STATUS_LABEL: Record<string, string> = {
  draft:        "Borrador",
  running:      "Ejecutando",
  review_ready: "En revisión",
  approved:     "Aprobado",
  published:    "Publicado",
  rejected:     "Rechazado",
};
