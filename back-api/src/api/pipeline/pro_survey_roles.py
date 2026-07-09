"""Etiquetas y normalización de roles para encuesta multi-rater Pro."""
from __future__ import annotations

# Roles estándar del instrumento (3 perspectivas jerárquicas)
STANDARD_SURVEY_ROLE_IDS = ("executive", "operations", "technology")

# IDs de dimensiones — no son roles de encuesta (legacy: a veces se guardaron por error)
DIMENSION_IDS = frozenset({
    "strategy", "process", "technology", "people", "finance", "governance",
})

ROLE_CATALOG: dict[str, dict[str, str]] = {
    "executive": {
        "label": "Estratégico",
        "description": "Alta dirección y gobernanza",
    },
    "operations": {
        "label": "Operativo",
        "description": "Ejecución y procesos en planta",
    },
    "technology": {
        "label": "Táctico",
        "description": "Gestión, coordinación y sistemas",
    },
    # Roles funcionales extra (casos legacy — etiqueta clara, no duplicar “estratégico”)
    "strategy": {
        "label": "Planeación",
        "description": "Área de estrategia y planeación (rol funcional)",
    },
    "finance": {
        "label": "Finanzas",
        "description": "Perspectiva del área financiera",
    },
    "hr": {
        "label": "Recursos humanos",
        "description": "Perspectiva de talento y cultura",
    },
}

DEFAULT_ROLE_OPTIONS = [
    {"id": rid, **ROLE_CATALOG[rid]} for rid in STANDARD_SURVEY_ROLE_IDS
]


def role_label(role_id: str) -> str:
    key = str(role_id or "").strip().lower()
    if key in ROLE_CATALOG:
        return ROLE_CATALOG[key]["label"]
    # Ya en español (respuesta guardada)
    if role_id in {v["label"] for v in ROLE_CATALOG.values()}:
        return role_id
    return str(role_id).replace("_", " ").title()


def role_description(role_id: str) -> str:
    key = str(role_id or "").strip().lower()
    if key in ROLE_CATALOG:
        return ROLE_CATALOG[key]["description"]
    return "Perspectiva definida para este diagnóstico"


def normalize_role_options(raw_roles: list | None) -> list[dict]:
    """Convierte IDs internos a opciones legibles para la UI pública."""
    if not raw_roles:
        return list(DEFAULT_ROLE_OPTIONS)

    options: list[dict] = []
    seen_labels: set[str] = set()
    for raw in raw_roles:
        if not raw:
            continue
        rid = str(raw).strip()
        key = rid.lower()
        # Dimensiones mezcladas como roles (bug legacy) — omitir salvo que estén en catálogo explícito
        if key in DIMENSION_IDS and key not in ROLE_CATALOG:
            continue
        if rid in ROLE_CATALOG:
            opt = {"id": rid, **ROLE_CATALOG[rid]}
        elif key in ROLE_CATALOG:
            opt = {"id": key, **ROLE_CATALOG[key]}
        elif rid in {v["label"] for v in ROLE_CATALOG.values()}:
            opt = {"id": rid, "label": rid, "description": role_description(rid)}
        else:
            opt = {"id": rid, "label": role_label(rid), "description": role_description(rid)}
        if opt["label"] in seen_labels:
            continue
        seen_labels.add(opt["label"])
        options.append(opt)

    return options or list(DEFAULT_ROLE_OPTIONS)


def available_role_labels(raw_roles: list | None) -> list[str]:
    return [o["label"] for o in normalize_role_options(raw_roles)]
