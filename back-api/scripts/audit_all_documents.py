#!/usr/bin/env python3
"""Auditoría de todos los documentos/entregables Pro en producción."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from api.pipeline.pro_coherence import build_case_anchors, coherence_issues, derive_subprocess
from api.pipeline.pro_report_data import build_pro_report_data, validate_report_for_deliverables
from api.pipeline.pro_survey_mode import resolve_survey_mode

API = "https://arhiax-dx-pro-187668243215.southamerica-east1.run.app/api/backend"
EMAIL = "admin@arhiax.com"
PASSWORD = "arhiax-admin-2026"

# Señales de contenido que NO debería aparecer si el intake no los menciona
DRIFT_MARKERS = [
    ("vacaciones_rrhh", r"(?i)(solicitud de vacaciones|analista rrhh|jefe directo|solicitante)"),
    ("onboarding", r"(?i)(onboarding|nuevo ingreso|time-to-productivity)"),
    ("credito", r"(?i)(solicitud(es)? de cr[eé]dito|aprobaci[oó]n de cr[eé]dito)"),
    ("clima_laboral_en", r"(?i)(internal conflict|low morale|psychological safety)"),
]

SECTION_TOOLS = {
    "cienciometria": "g03_cienciometro",
    "cartografia": "g04_cartografo",
    "bpmn_asis": "g06_bpmn_architect",
    "hallazgos": "g12_hallazgos",
    "narrativa": "g13_redactor",
}


def login(client: httpx.Client) -> dict:
    r = client.post(f"{API}/auth/login", data={"username": EMAIL, "password": PASSWORD}, timeout=60)
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def case_from_api(data: dict) -> SimpleNamespace:
    payload = dict(data.get("input_payload") or {})
    symptom = payload.get("symptom") or ""
    if symptom and not payload.get("subprocess"):
        payload["subprocess"] = derive_subprocess(
            symptom, data.get("domain") or "", payload.get("expected_outcome") or ""
        )
    if not payload.get("survey_mode"):
        payload["survey_mode"] = resolve_survey_mode(None, payload.get("roles"))
    ns = SimpleNamespace(**{k: v for k, v in data.items() if k != "stages"})
    ns.input_payload = payload
    ns.pipeline_stages = data.get("stages") or []
    ns.survey_sessions = []
    ns.evidence_entries = []
    return ns


def scan_text(text: str) -> list[dict]:
    hits = []
    for label, pat in DRIFT_MARKERS:
        if re.search(pat, text):
            hits.append({"marker": label, "pattern": pat})
    return hits


def audit_case(case_json: dict) -> dict:
    case = case_from_api(case_json)
    report_data = build_pro_report_data(case)
    gaps = validate_report_for_deliverables(report_data, case)

    payload = case.input_payload or {}
    ctx = {
        "objective": payload.get("symptom") or "",
        "sector": payload.get("sector") or "",
        "domain": case.domain or "",
        "diagnostic_area": case.domain or "",
        "subprocess": payload.get("subprocess") or "",
        "paquete_hipotesis": payload.get("paquete_hipotesis") or [],
    }
    ctx["case_anchors"] = build_case_anchors(ctx)

    outputs = report_data.get("pipeline_outputs") or {}
    section_issues: dict[str, list[str]] = {}
    for sec, tool in SECTION_TOOLS.items():
        raw = outputs.get(tool) or outputs.get("bpmn_generator" if tool == "g06_bpmn_architect" else "")
        issues = coherence_issues(tool, raw, ctx) if raw else ["sin output del agente"]
        if issues:
            section_issues[sec] = issues

    # Triangulación: cuántas hipótesis vs intake
    intake_n = len(payload.get("paquete_hipotesis") or [])
    tri_rows = len((report_data.get("triangulation") or {}).get("rows") or [])

    symptom = payload.get("symptom") or ""
    anchor_hits = scan_text(symptom)

    executive = (report_data.get("executive") or {}).get("thesis") or ""
    exec_drift = scan_text(str(executive))

    verdict = "OK_ENTREGABLE"
    if gaps or section_issues:
        verdict = "NO_ENTREGAR"
    elif case_json.get("case_status") not in ("approved", "published"):
        verdict = "INCOMPLETO"

    return {
        "case_ref": case_json.get("case_id"),
        "uuid": case_json.get("id"),
        "client_name": case_json.get("client_name"),
        "case_status": case_json.get("case_status"),
        "survey_mode": payload.get("survey_mode"),
        "symptom_preview": (symptom[:120] + "…") if len(symptom) > 120 else symptom,
        "subprocess": payload.get("subprocess"),
        "intake_hypotheses": intake_n,
        "triangulation_rows": tri_rows,
        "validation_gaps": gaps,
        "section_coherence_issues": section_issues,
        "executive_drift_markers": exec_drift,
        "verdict": verdict,
        "deliverables": case_json.get("deliverables") or [],
    }


def main() -> int:
    report: list[dict] = []
    pdf_results: list[dict] = []

    with httpx.Client(timeout=120) as client:
        h = login(client)
        listing = client.get(f"{API}/pro/cases", headers=h, params={"limit": 100}).json()
        items = listing.get("items") or []

        for item in sorted(items, key=lambda x: x.get("created_at") or ""):
            cid = item["id"]
            detail = client.get(f"{API}/pro/cases/{cid}", headers=h).json()
            entry = audit_case(detail)
            report.append(entry)

            if detail.get("case_status") in ("approved", "published"):
                pr = client.get(f"{API}/pro/cases/{cid}/download/pdf", headers=h)
                pdf_results.append({
                    "case_ref": detail.get("case_id"),
                    "client_name": detail.get("client_name"),
                    "http_status": pr.status_code,
                    "bytes": len(pr.content) if pr.status_code == 200 else 0,
                    "blocked": pr.status_code == 409,
                    "error": pr.json() if pr.status_code == 409 else None,
                })

    out_dir = ROOT.parent
    audit_path = out_dir / "AUDITORIA_DOCUMENTOS_PRO.json"
    audit_path.write_text(
        json.dumps({"cases": report, "pdf_downloads": pdf_results}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Resumen legible
    lines = ["# Auditoría documentos Pro — producción\n"]
    for c in report:
        icon = "❌" if c["verdict"] == "NO_ENTREGAR" else ("⏳" if c["verdict"] == "INCOMPLETO" else "✅")
        lines.append(f"## {icon} {c['client_name']} (`{c['case_ref']}`)")
        lines.append(f"- Estado: **{c['case_status']}** | Veredicto: **{c['verdict']}**")
        lines.append(f"- Síntoma: {c['symptom_preview']}")
        if c["validation_gaps"]:
            lines.append("- **Bloqueos validación:**")
            for g in c["validation_gaps"]:
                lines.append(f"  - {g}")
        if c["section_coherence_issues"]:
            lines.append("- **Secciones con contenido ajeno al caso:**")
            for sec, issues in c["section_coherence_issues"].items():
                lines.append(f"  - `{sec}`: {'; '.join(issues[:2])}")
        lines.append("")

    lines.append("## Descarga PDF en producción (código actual desplegado)\n")
    for p in pdf_results:
        st = "✅ OK" if p["http_status"] == 200 else f"❌ {p['http_status']}"
        lines.append(f"- {p['client_name']} (`{p['case_ref']}`): {st}, {p['bytes']} bytes")
        if p.get("error"):
            missing = (p["error"].get("detail") or {}).get("missing_sections") or p["error"]
            lines.append(f"  - {missing}")

    md_path = out_dir / "AUDITORIA_DOCUMENTOS_PRO.md"
    md_path.write_text("\n".join(lines), encoding="utf-8")

    print(md_path.read_text(encoding="utf-8"))
    print(f"\nJSON: {audit_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
