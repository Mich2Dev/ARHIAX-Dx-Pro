"""Modo de encuesta: perspectiva única vs multi-rater — resolución y reglas."""
from __future__ import annotations

from typing import Any

SINGLE_RATER = "single_rater"
MULTI_RATER = "multi_rater"

DEFAULT_SINGLE_ROLE = "executive"
DEFAULT_MULTI_ROLES = ["executive", "operations", "technology"]


def resolve_survey_mode(
    survey_mode: str | None = None,
    roles: list[str] | None = None,
) -> str:
    """Deriva el modo explícito o lo infiere por cantidad de roles."""
    mode = (survey_mode or "").strip().lower()
    if mode in (SINGLE_RATER, MULTI_RATER):
        return mode
    role_list = [r for r in (roles or []) if r]
    if len(role_list) <= 1:
        return SINGLE_RATER
    return MULTI_RATER


def roles_for_mode(survey_mode: str, selected_roles: list[str] | None) -> list[str]:
    """Roles efectivos según modo — single fuerza un solo decisor."""
    if survey_mode == SINGLE_RATER:
        picked = [r for r in (selected_roles or []) if r]
        return [picked[0]] if picked else [DEFAULT_SINGLE_ROLE]
    roles = [r for r in (selected_roles or []) if r]
    return roles or list(DEFAULT_MULTI_ROLES)


def min_responses_for_mode(survey_mode: str, roles: list[str]) -> int:
    if survey_mode == SINGLE_RATER:
        return 1
    return max(len(roles), 1)


def survey_mode_label(survey_mode: str) -> str:
    if survey_mode == SINGLE_RATER:
        return "perspectiva única"
    return "multi-rater"


def survey_mode_instructions(survey_mode: str, roles: list[str]) -> str:
    if survey_mode == SINGLE_RATER:
        return (
            "MODO ENCUESTA: perspectiva única (1 respondente). "
            "No inventes brechas δσ entre roles ni IRR inter-evaluador. "
            "El informe debe declarar explícitamente que hay una sola perspectiva."
        )
    labels = ", ".join(roles) if roles else "Estratégico, Táctico, Operativo"
    return (
        f"MODO ENCUESTA: multi-rater ({len(roles)} roles: {labels}). "
        "Cada rol debe aportar respuestas distintas; δσ e IRR aplican solo si hay ≥2 roles con datos."
    )


def is_multi_rater(survey_mode: str | None) -> bool:
    return resolve_survey_mode(survey_mode) == MULTI_RATER


def from_payload(payload: dict[str, Any] | None) -> str:
    if not payload:
        return MULTI_RATER
    return resolve_survey_mode(
        payload.get("survey_mode"),
        payload.get("roles"),
    )
