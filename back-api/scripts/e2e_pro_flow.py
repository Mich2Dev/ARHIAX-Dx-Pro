#!/usr/bin/env python3
"""Flujo E2E Pro como usuario: caso → encuesta → diagnóstico → aprobación → PDF."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import httpx

API = "http://localhost:8000"
OUT_DIR = Path(__file__).resolve().parents[2] / "exports" / "e2e_demo"
EMAIL = "admin@arhiax.com"
PASSWORD = "arhiax-admin-2026"


def login(client: httpx.Client) -> str:
    r = client.post(f"{API}/auth/login", data={"username": EMAIL, "password": PASSWORD})
    r.raise_for_status()
    return r.json()["access_token"]


def poll_case(client: httpx.Client, case_id: str, want: str, timeout: int = 600) -> dict:
    headers = client.headers
    t0 = time.time()
    while time.time() - t0 < timeout:
        r = client.get(f"{API}/pro/cases/{case_id}", headers=headers)
        r.raise_for_status()
        data = r.json()
        status = data.get("case_status")
        stages = data.get("stages") or data.get("pipeline_stages") or []
        done = sum(1 for s in stages if s.get("status") == "completed")
        print(f"  status={status} stages_completed={done}/{len(stages)}", flush=True)
        if status == want:
            return data
        if status == "error":
            raise RuntimeError(f"Caso en error: {data}")
        time.sleep(3)
    raise TimeoutError(f"Timeout esperando {want}")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    client = httpx.Client(timeout=180.0)

    print("1. Login...")
    token = login(client)
    client.headers["Authorization"] = f"Bearer {token}"

    payload = {
        "consent": {"consents": {"T1": True}},
        "client_name": "Acme Logística S.A.",
        "domain": "logistica_distribucion",
        "roles": ["executive", "operations", "technology"],
        "dimensions": ["strategy", "process", "technology"],
        "paquete_hipotesis": [
            {
                "hipotesis_id": "H-01",
                "enunciado": "El SLA de despacho se cumple en menos del 70% por validación manual heterogénea",
                "confianza": "ALTA",
                "observacion_refutadora": "El dashboard muestra 92% de cumplimiento pero operaciones reporta devoluciones masivas",
                "incidente_texto": "Incidente INC-2024-881: 340 pedidos retenidos 72h por criterio distinto entre turnos",
                "informante_id": "INF-OPS-01",
                "dato_duro": "ALTO",
            },
            {
                "hipotesis_id": "H-02",
                "enunciado": "No existe trazabilidad de causa raíz en devoluciones de última milla",
                "confianza": "MEDIA",
                "observacion_refutadora": "Hay bitácora en Excel pero no se usa en decisiones",
                "incidente_texto": "Auditoría interna Q3: 61% devoluciones sin código de causa",
                "informante_id": "INF-QA-02",
                "dato_duro": "MEDIO",
            },
        ],
        "grey_sources": ["informe_auditoria_Q3.pdf"],
        "extra": {
            "symptom": "Retrasos recurrentes en despacho y devoluciones sin causa raíz",
            "size_org": "201-500",
            "subprocess": "despacho_ultima_milla",
        },
    }

    print("2. Crear caso Pro (G01-G08 + encuesta)...")
    r = client.post(f"{API}/pro/cases", json=payload)
    r.raise_for_status()
    case = r.json()
    case_id = case["id"]
    print(f"   case_id={case_id} trace={case.get('case_id')}")

    print("3. Esperar survey_open...")
    case = poll_case(client, case_id, "survey_open", timeout=900)
    survey_meta = case.get("survey") or {}
    token_survey = survey_meta.get("token")
    print(f"   survey_token={token_survey} preguntas={survey_meta.get('question_count')}")

    srvey = client.get(f"{API}/pro/survey/{token_survey}")
    srvey.raise_for_status()
    survey_data = srvey.json()
    questions = survey_data.get("questions") or []
    if isinstance(questions, dict):
        questions = questions.get("questions") or []
    print(f"   preguntas cargadas={len(questions)}")

    print("4. Enviar respuestas multi-rater...")
    roles = payload["roles"]
    for i, role in enumerate(roles):
        answers = {}
        for q in questions:
            qid = q.get("id")
            if qid:
                answers[qid] = 2 + (i % 3)  # variación por rol
        if not answers and questions:
            answers = {questions[0]["id"]: 3}
        elif not answers:
            answers = {"Q-STR-01": 3, "Q-PROC-01": 2, "Q-TEC-01": 4}
        sr = client.post(
            f"{API}/pro/survey/{token_survey}/submit",
            json={"role": role, "answers": answers},
        )
        sr.raise_for_status()
        print(f"   role={role} ok")

    print("5. Lanzar diagnóstico...")
    rr = client.post(f"{API}/pro/cases/{case_id}/run")
    rr.raise_for_status()

    print("6. Esperar review_pending...")
    case = poll_case(client, case_id, "review_pending", timeout=900)

    print("7. Aprobar caso...")
    ar = client.post(
        f"{API}/pro/cases/{case_id}/approval",
        json={"action": "approve", "comment": "E2E demo", "reviewer_name": "Consultor Demo"},
    )
    ar.raise_for_status()

    print("8. Generar entregables...")
    gr = client.post(f"{API}/pro/cases/{case_id}/generate-deliverables")
    gr.raise_for_status()

    print("9. Descargar PDF...")
    pr = client.get(f"{API}/pro/cases/{case_id}/download/pdf")
    pr.raise_for_status()
    pdf_path = OUT_DIR / f"{case.get('case_id', case_id)}_diagnostico.pdf"
    pdf_path.write_bytes(pr.content)
    print(f"   PDF guardado: {pdf_path} ({len(pr.content)} bytes)")

    mr = client.get(f"{API}/pro/cases/{case_id}/download/markdown")
    if mr.status_code == 200:
        md_path = OUT_DIR / f"{case.get('case_id', case_id)}_diagnostico.md"
        md_path.write_bytes(mr.content)
        print(f"   MD guardado: {md_path}")

    summary = {
        "case_id": case_id,
        "case_ref": case.get("case_id"),
        "pdf": str(pdf_path),
        "stages": case.get("stages") or [],
        "fusion_score": (case.get("fusion_result") or {}).get("scoring"),
    }
    (OUT_DIR / "last_run.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print("DONE")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        raise SystemExit(1)
