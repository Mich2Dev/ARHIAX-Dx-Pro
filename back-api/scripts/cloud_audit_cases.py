#!/usr/bin/env python3
"""Auditoría read-only de casos Pro en Cloud Run — no modifica nada."""
from __future__ import annotations

import json
from datetime import datetime

import httpx

API = "https://arhiax-dx-pro-187668243215.southamerica-east1.run.app/api/backend"
EMAIL = "admin@arhiax.com"
PASSWORD = "arhiax-admin-2026"


def login(client: httpx.Client) -> dict:
    r = client.post(f"{API}/auth/login", data={"username": EMAIL, "password": PASSWORD}, timeout=40)
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def stage_summary(stages: list) -> dict:
    if not stages:
        return {"total": 0, "completed": 0, "failed": 0, "pending": 0, "failed_tools": []}
    completed = [s for s in stages if s.get("status") == "completed"]
    failed = [s for s in stages if s.get("status") == "failed" or (isinstance(s.get("output"), dict) and s["output"].get("error"))]
    pending = [s for s in stages if s.get("status") not in ("completed", "failed")]
    failed_tools = []
    for s in failed:
        out = s.get("output") or {}
        err = out.get("error") if isinstance(out, dict) else str(out)
        failed_tools.append({"tool": s.get("tool_name"), "error": (err or "falló")[:300]})
    return {
        "total": len(stages),
        "completed": len(completed),
        "failed": len(failed),
        "pending": len(pending),
        "failed_tools": failed_tools,
        "last_completed": completed[-1].get("tool_name") if completed else None,
    }


def infer_failure(stages: list, survey: dict, evidence: list) -> str:
    ss = stage_summary(stages)
    if ss["failed_tools"]:
        ft = ss["failed_tools"][0]
        return f"Pipeline falló en {ft['tool']}: {ft['error']}"

    for e in reversed(evidence or []):
        if e.get("event_type") == "pipeline_failed":
            return f"Pipeline bloqueado (evidencia pipeline_failed, agente {e.get('agent', '?')})"
        if e.get("event_type") == "diagnostic_error":
            return "Error en fase de diagnóstico/fusión (G10-G14)"

    status = (survey or {}).get("status")
    qcount = (survey or {}).get("question_count", 0)
    responses = (survey or {}).get("responses_count", 0)

    if status == "error" or qcount == 0:
        if ss["completed"] == 0 and ss["total"] > 0:
            return (
                "Falló durante arquitectura G01-G08 (fail-closed). "
                "Las etapas quedaron en pending porque el rollback no persiste el progreso parcial."
            )
        return "Encuesta no generada o en error antes de abrir recolección."

    if status == "open" and responses < (survey or {}).get("min_responses", 3):
        return f"Encuesta abierta pero incompleta: {responses}/{(survey or {}).get('min_responses', 3)} respuestas."

    return "Sin error obvio en metadatos; revisar entregables."


def main() -> None:
    report = []
    with httpx.Client(timeout=90) as client:
        h = login(client)
        listing = client.get(f"{API}/pro/cases", headers=h, params={"limit": 100}).json()
        items = listing.get("items") or []

        for item in sorted(items, key=lambda x: x.get("created_at") or ""):
            cid = item["id"]
            detail = client.get(f"{API}/pro/cases/{cid}", headers=h).json()
            stages = detail.get("stages") or []
            survey = detail.get("survey") or {}
            evidence = detail.get("evidence") or []
            extra = (detail.get("input_payload") or {})
            ss = stage_summary(stages)

            deliverables = detail.get("deliverables") or []
            if not deliverables and detail.get("export_result"):
                deliverables = (detail.get("export_result") or {}).get("files") or []

            entry = {
                "case_ref": detail.get("case_id"),
                "uuid": cid,
                "client_name": detail.get("client_name"),
                "domain": detail.get("domain"),
                "case_status": detail.get("case_status"),
                "approval_status": detail.get("approval_status"),
                "created_at": detail.get("created_at"),
                "symptom_chars": len(str(extra.get("symptom") or "")),
                "hypotheses_count": len(extra.get("paquete_hipotesis") or []),
                "survey_status": survey.get("status"),
                "survey_questions": survey.get("question_count", 0),
                "survey_responses": survey.get("responses_count", 0),
                "pipeline": ss,
                "maturity_score": (detail.get("fusion_result") or {}).get("scoring", {}).get("overall_score"),
                "deliverables_count": len(deliverables) if isinstance(deliverables, list) else 0,
                "evidence_events": [e.get("event_type") for e in evidence],
                "diagnosis": infer_failure(stages, survey, evidence),
            }
            report.append(entry)

    out_path = __file__.replace("cloud_audit_cases.py", "cloud_audit_report.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\n--- {len(report)} casos auditados (read-only) ---")


if __name__ == "__main__":
    main()
