/**
 * Role labels and colors for user management
 * Etiquetas y colores de roles para gestión de usuarios
 */

export const ROLE_LABELS: Record<string, string> = {
  admin:    "Administrador",
  reviewer: "Revisor",
  operator: "Consultor",
};

export const ROLE_COLORS: Record<string, "red" | "orange" | "blue"> = {
  admin:    "red",
  reviewer: "orange",
  operator: "blue",
};
