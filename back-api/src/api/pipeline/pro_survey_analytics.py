"""Cálculo de scores, delta_sigma y brechas desde respuestas reales de encuesta Pro."""
from __future__ import annotations

from typing import Any

_ROLE_LABELS = {
    "executive": "Estratégico",
    "operations": "Operativo",
    "technology": "Tecnológico",
    "tactical": "Táctico",
    "tactico": "Táctico",
    "estrategico": "Estratégico",
    "operativo": "Operativo",
}


def _role_label(role: str) -> str:
    return _ROLE_LABELS.get(role.lower(), role.replace("_", " ").title())


def compute_live_scoring(case: Any) -> dict[str, Any]:
    """Scores por rol/dimensión y delta_sigma desde respuestas almacenadas."""
    sessions = getattr(case, "__dict__", {}).get("survey_sessions")
    if sessions is None:
        # Evitar lazy-load en contexto sync (PDF/markdown)
        return {}
    if not sessions:
        return {}

    responses: list = []
    questions_data: dict = {}
    for s in sessions:
        responses.extend(getattr(s, "responses", None) or [])
        if getattr(s, "questions", None):
            questions_data = s.questions or {}

    if not responses:
        return {}

    q_list = questions_data.get("questions", [])
    q_reverse = {q["id"]: q.get("reverse_scored", False) for q in q_list}
    q_to_dim = {q["id"]: q.get("dimension", q.get("dimension_id", "general")) for q in q_list}
    dim_names = {
        q.get("dimension", q.get("dimension_id", "general")): q.get("dimension", "general")
        for q in q_list
    }

    role_dim_scores: dict[str, dict[str, list[float]]] = {}
    for resp in responses:
        role = resp.role
        if role not in role_dim_scores:
            role_dim_scores[role] = {}
        for qid, val in (resp.answers or {}).items():
            if not isinstance(val, (int, float)):
                continue
            corrected = (6 - int(val)) if q_reverse.get(qid, False) else int(val)
            dim = q_to_dim.get(qid, "general")
            role_dim_scores[role].setdefault(dim, []).append((corrected - 1) / 4 * 100)

    if not role_dim_scores:
        return {}

    role_scores: dict[str, dict] = {}
    role_dim_avgs: dict[str, dict[str, float]] = {}
    role_n: dict[str, int] = {}

    for role, dims in role_dim_scores.items():
        dim_avgs: dict[str, float] = {}
        all_vals: list[float] = []
        for dim, vals in dims.items():
            dim_avgs[dim] = round(sum(vals) / len(vals), 1)
            all_vals.extend(vals)
        role_dim_avgs[role] = dim_avgs
        avg = round(sum(all_vals) / len(all_vals), 1) if all_vals else 0
        role_scores[_role_label(role)] = {
            "score": avg,
            "n_responses": sum(1 for r in responses if r.role == role),
            "dimension_breakdown": dim_avgs,
            "role_key": role,
        }
        role_n[role] = role_scores[_role_label(role)]["n_responses"]

    all_dims = sorted({d for dims in role_dim_avgs.values() for d in dims})
    dimension_scores = []
    for dim in all_dims:
        vals = [role_dim_avgs[r][dim] for r in role_dim_avgs if dim in role_dim_avgs[r]]
        avg = round(sum(vals) / len(vals), 1) if vals else 0
        dimension_scores.append({
            "dimension": dim_names.get(dim, dim),
            "name": dim_names.get(dim, dim),
            "score": avg,
            "benchmark": 75,
            "gap": round(avg - 75, 1),
        })

    gap_pairs = []
    delta_sigma = 0.0
    labels = list(role_scores.keys())
    for i in range(len(labels)):
        for j in range(i + 1, len(labels)):
            r1, r2 = labels[i], labels[j]
            d1 = role_scores[r1]["score"]
            d2 = role_scores[r2]["score"]
            delta = abs(d1 - d2) / 20
            delta_sigma = max(delta_sigma, delta)
            for dim in all_dims:
                if dim in role_dim_avgs.get(role_scores[r1].get("role_key", ""), {}) and dim in role_dim_avgs.get(role_scores[r2].get("role_key", ""), {}):
                    rk1 = role_scores[r1]["role_key"]
                    rk2 = role_scores[r2]["role_key"]
                    dd = abs(role_dim_avgs[rk1][dim] - role_dim_avgs[rk2][dim]) / 20
                    gap_pairs.append({
                        "roles": f"{r1} vs {r2}",
                        "dimension": dim_names.get(dim, dim),
                        "delta": round(dd, 2),
                        "critical": dd > 2.0,
                        "interpretation": (
                            f"Brecha de percepción en {dim_names.get(dim, dim)}: "
                            f"{r1} {role_dim_avgs[rk1][dim]:.0f} vs {r2} {role_dim_avgs[rk2][dim]:.0f}"
                        ),
                    })

    if not gap_pairs and len(labels) >= 2:
        r1, r2 = labels[0], labels[-1]
        gap_pairs.append({
            "roles": f"{r1} vs {r2}",
            "dimension": "Global",
            "delta": round(delta_sigma, 2),
            "critical": delta_sigma > 2.0,
            "interpretation": f"Diferencia global de madurez percibida entre {r1} y {r2}.",
        })

    overall = round(sum(v["score"] for v in role_scores.values()) / len(role_scores), 1)

    return {
        "overall_score": overall,
        "role_scores": role_scores,
        "dimension_scores": dimension_scores,
        "delta_sigma": {"max_gap": round(delta_sigma, 2), "gap_pairs": gap_pairs[:12]},
        "total_responses": len(responses),
        "source": "live_survey",
    }
