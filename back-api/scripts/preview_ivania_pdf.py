"""Vista previa local del PDF Ivania con datos actuales de producción."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from api.pipeline.pro_coherence import derive_subprocess
from api.pipeline.pro_pdf_report import build_pro_pdf_dense
from api.pipeline.pro_report_data import build_pro_report_data, validate_report_for_deliverables
from api.pipeline.pro_survey_mode import resolve_survey_mode

API = "https://arhiax-dx-pro-187668243215.southamerica-east1.run.app/api/backend"
EMAIL = "admin@arhiax.com"
PASSWORD = "arhiax-admin-2026"
IVANIA_UUID = "d1356675-4dc3-49ac-b33f-4c3ab1c3a4b0"
OUT_PREVIEW = Path(__file__).resolve().parents[2] / "CD_GLOBAL_IVANIA_RUA__preview_nuevo.pdf"
OUT_GAPS = Path(__file__).resolve().parents[2] / "CD_GLOBAL_IVANIA_RUA__validacion.json"


def _case_from_api(data: dict) -> SimpleNamespace:
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


def main() -> int:
    with httpx.Client(timeout=180.0) as c:
        r = c.post(f"{API}/auth/login", data={"username": EMAIL, "password": PASSWORD})
        r.raise_for_status()
        c.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
        case_json = c.get(f"{API}/pro/cases/{IVANIA_UUID}").json()

    case = _case_from_api(case_json)
    report_data = build_pro_report_data(case)
    gaps = validate_report_for_deliverables(report_data, case)

    meta = {
        "case_id": case_json.get("case_id"),
        "client_name": case_json.get("client_name"),
        "survey_mode": case.input_payload.get("survey_mode"),
        "subprocess": case.input_payload.get("subprocess"),
        "validation_gaps": gaps,
        "production_would_block_pdf": bool(gaps),
        "triangulation_rows": len((report_data.get("triangulation") or {}).get("rows") or []),
        "instrument_config": (report_data.get("methodology") or {}).get("instrument_config"),
    }
    OUT_GAPS.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False, indent=2))

    pdf = build_pro_pdf_dense(case, allow_incomplete=True)
    OUT_PREVIEW.write_bytes(pdf)
    print(f"\nPDF preview ({len(pdf)} bytes): {OUT_PREVIEW}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
