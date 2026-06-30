#!/usr/bin/env python3
"""Flujo E2E Pro: auth → caso → encuesta → run → aprobación → grammar → PDF."""

from __future__ import annotations

import json
import sys
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = "http://localhost:8000"
WEB = "http://localhost:3001"
OUT_DIR = Path(__file__).resolve().parent.parent / "demo_pdfs"


def request_json(
    method: str,
    path: str,
    *,
    token: str | None = None,
    json_body: dict | None = None,
    form_body: dict | None = None,
):
    url = f"{BASE}{path}"
    headers: dict[str, str] = {}
    data = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if json_body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(json_body).encode("utf-8")
    elif form_body is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        data = urlencode(form_body).encode("utf-8")
    req = Request(url, data=data, method=method, headers=headers)
    try:
        with urlopen(req, timeout=300) as resp:
            raw = resp.read()
            if not raw:
                return {}
            return json.loads(raw.decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {path} -> {exc.code}: {body}") from exc


def download_bytes(path: str, token: str) -> bytes:
    req = Request(f"{BASE}{path}", headers={"Authorization": f"Bearer {token}"})
    with urlopen(req, timeout=120) as resp:
        return resp.read()


def _default_answers(questions: list[dict]) -> dict[str, int | str]:
    answers: dict[str, int | str] = {}
    for q in questions:
        qid = q.get("id")
        if not qid:
            continue
        qtype = q.get("type", "likert_5")
        if qtype == "likert_5":
            answers[qid] = 4
        elif qtype == "open_text":
            answers[qid] = "Respuesta de prueba con evidencia operativa verificable."
    return answers


def main() -> int:
    email = f"e2e.{uuid.uuid4().hex[:8]}@sinergia.co"
    password = "test1234"

    reg = request_json(
        "POST",
        "/auth/register",
        json_body={"email": email, "name": "E2E Runner", "password": password, "role": "admin"},
    )
    print(f"REGISTERED {reg.get('user_id')} {email}")

    login = request_json(
        "POST",
        "/auth/login",
        form_body={"username": email, "password": password},
    )
    token = login["access_token"]
    print(f"AUTH_OK role={login.get('role')}")
    print(f"WEB_LOGIN {WEB}/login  user={email}  pass={password}")

    created = request_json(
        "POST",
        "/pro/cases",
        token=token,
        json_body={
            "consent": {
                "consents": {"T1": True, "T2": True},
                "accepted_by": "E2E",
                "accepted_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
            "client_name": "Cliente Integración Demo",
            "domain": "Operaciones y Estrategia",
            "roles": ["Estratégico", "Táctico", "Operativo"],
            "dimensions": ["strategy", "process", "technology"],
            "hypotheses": ["Desalineación operativa", "Brechas de gobernanza"],
            "grey_sources": ["entrevistas", "KPIs"],
        },
    )
    case_id = created["id"]
    survey = created.get("survey") or {}
    survey_token = survey.get("token")
    if not survey_token:
        raise RuntimeError(f"survey token missing in create response: {list(created.keys())}")

    print(f"CASE_CREATED id={case_id} survey={survey_token}")
    print(f"WEB_CASE {WEB}/dashboard-pro/cases/{case_id}")
    print(f"WEB_SURVEY {WEB}/survey/pro/{survey_token}")

    survey_data = None
    for attempt in range(60):
        survey_data = request_json("GET", f"/pro/survey/{survey_token}")
        status = survey_data.get("status")
        qcount = len(survey_data.get("questions") or [])
        print(f"SURVEY_WAIT {attempt} status={status} questions={qcount}")
        if status == "open" and qcount > 0:
            break
        time.sleep(3)
    else:
        raise RuntimeError("Timeout esperando encuesta lista (status=open)")

    roles_raw = survey_data.get("roles") or ["Estratégico", "Táctico", "Operativo"]
    roles: list[str] = []
    for r in roles_raw:
        if isinstance(r, dict):
            roles.append(str(r.get("id") or r.get("label") or r))
        else:
            roles.append(str(r))
    answers_template = _default_answers(survey_data.get("questions") or [])

    for role in roles[:3]:
        request_json(
            "POST",
            f"/pro/survey/{survey_token}/submit",
            json_body={"role": role, "answers": answers_template},
        )
        print(f"SURVEY_SUBMITTED role={role}")

    request_json("POST", f"/pro/cases/{case_id}/run", token=token, json_body={})
    print("RUN_STARTED")

    for attempt in range(90):
        detail = request_json("GET", f"/pro/cases/{case_id}", token=token)
        status = detail.get("case_status")
        print(f"POLL {attempt} status={status}")
        if status in ("review_pending", "completed", "failed"):
            break
        time.sleep(4)
    else:
        raise RuntimeError("Timeout esperando pipeline Pro")

    approval = request_json(
        "POST",
        f"/pro/cases/{case_id}/approval",
        token=token,
        json_body={
            "action": "approve",
            "comment": "Aprobado E2E",
            "reviewer_name": "Consultor E2E",
            "reviewer_role": "lead",
            "grammar_confirmed": True,
        },
    )
    print(f"APPROVED approval_status={approval.get('approval_status')}")

    grammar = request_json("GET", f"/pro/cases/{case_id}/grammar", token=token)
    print(
        f"GRAMMAR score={grammar.get('grammar', {}).get('score')} "
        f"status={grammar.get('report_status')}"
    )

    try:
        deliver = request_json(
            "POST",
            f"/pro/cases/{case_id}/generate-deliverables",
            token=token,
            json_body={},
        )
        print(f"DELIVERABLES report_status={deliver.get('report_status')}")
    except RuntimeError as exc:
        if "grammar" in str(exc).lower():
            print(f"DELIVERABLES_BLOCKED (grammar): {exc}")
        else:
            raise

    out = OUT_DIR / f"e2e_{case_id}"
    out.mkdir(parents=True, exist_ok=True)

    pdf = download_bytes(f"/pro/cases/{case_id}/download/pdf", token)
    pdf_path = out / "diagnostico.pdf"
    pdf_path.write_bytes(pdf)
    print(f"PDF_SAVED {pdf_path} bytes={len(pdf)}")

    md = download_bytes(f"/pro/cases/{case_id}/download/markdown", token)
    (out / "diagnostico.md").write_bytes(md)
    print(f"MD_SAVED bytes={len(md)}")

    print("E2E_OK")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"E2E_FAIL {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
