#!/usr/bin/env python3
"""Limpia casos Pro en Cloud Run DB y ejecuta flujo E2E completo en producción."""
from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx

CLOUD = "https://arhiax-dx-pro-187668243215.southamerica-east1.run.app"
API = f"{CLOUD}/api/backend"
FRONT = CLOUD
EMAIL = "admin@arhiax.com"
PASSWORD = "arhiax-admin-2026"
OUT = Path(__file__).resolve().parent.parent / "exports" / "cloud_caso"
ROLE_ANSWERS = {"Estratégico": 5, "Operativo": 2, "Táctico": 3}


def log(step: str, msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {step}: {msg}", flush=True)


def login(client: httpx.Client) -> None:
    r = client.post(f"{API}/auth/login", data={"username": EMAIL, "password": PASSWORD})
    r.raise_for_status()
    client.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    log("LOGIN", "OK")


def list_cases(client: httpx.Client) -> list[dict]:
    r = client.get(f"{API}/pro/cases", timeout=30)
    r.raise_for_status()
    data = r.json()
    items = data.get("items") or []
    log("LIST", f"{data.get('total', len(items))} casos en Cloud Run")
    for c in items:
        log("LIST", f"  - {c.get('case_id')} | {c.get('client_name')} | {c.get('case_status')}")
    return items


def clean_db() -> bool:
    """Borra casos Pro viejos en Cloud SQL (cascade manual por tablas hijas)."""
    sql = """
DELETE FROM pro_survey_responses;
DELETE FROM pro_survey_sessions;
DELETE FROM pro_evidence;
DELETE FROM pro_cases;
"""
    log("CLEAN", "Ejecutando DELETE en Cloud SQL (pro_cases)...")
    try:
        proc = subprocess.run(
            [
                "gcloud", "sql", "connect", "arhiax-db",
                "--project=arhiax-project",
                "--user=postgres",
                "--database=postgres",
                "--quiet",
            ],
            input=sql,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if proc.returncode == 0:
            log("CLEAN", "Base de datos limpiada")
            return True
        log("CLEAN", f"gcloud sql connect falló ({proc.returncode}): {proc.stderr[:300]}")
    except Exception as e:
        log("CLEAN", f"No se pudo limpiar DB: {e}")
    return False


def create_case(client: httpx.Client) -> dict:
    payload = {
        "consent": {"action": "ingest_to_llm", "consents": {"T1": True, "T3": True}},
        "engagement_id": f"eng-cloud-{int(time.time())}",
        "client_name": "Agencia Innovación São Caetano",
        "domain": "Dirección y estrategia pública",
        "roles": ["executive", "operations", "technology"],
        "dimensions": ["strategy", "process", "technology", "governance"],
        "hypotheses": [],
        "paquete_hipotesis": [
            {
                "hipotesis_id": "H-01",
                "enunciado": (
                    "La coordinación inter-áreas para proyectos de innovación es lenta "
                    "porque no existe un tablero único de priorización ni seguimiento"
                ),
                "confianza": "ALTA",
                "observacion_refutadora": (
                    "El comité estratégico afirma que hay reuniones semanales, "
                    "pero no hay evidencia de decisiones trazables por proyecto"
                ),
                "incidente_texto": (
                    "INC-2026-0402: proyecto smart-city detenido 8 semanas por falta de "
                    "alineación entre planeación y operaciones (auditoría interna mar-2026)"
                ),
                "informante_id": "INF-DIR-01",
                "dato_duro": "ALTO",
            },
            {
                "hipotesis_id": "H-02",
                "enunciado": (
                    "Los indicadores de impacto ciudadano no se actualizan con la periodicidad "
                    "requerida para decisiones tácticas"
                ),
                "confianza": "MEDIA",
                "observacion_refutadora": (
                    "Existen reportes trimestrales, pero no se usan en comités operativos"
                ),
                "incidente_texto": (
                    "Revisión Q1-2026: 60% de KPIs de innovación con datos mayores a 45 días"
                ),
                "informante_id": "INF-OPS-02",
                "dato_duro": "MEDIO",
            },
            {
                "hipotesis_id": "H-03",
                "enunciado": (
                    "La gobernanza de datos entre secretarías genera duplicidad de captura "
                    "y retrasa la publicación de resultados"
                ),
                "confianza": "ALTA",
                "observacion_refutadora": (
                    "TI reporta integración parcial, pero usuarios finales re-digitán información"
                ),
                "incidente_texto": (
                    "Shadowing en área de innovación: equipos re-ingresan 35% de avances "
                    "porque los sistemas no sincronizan en tiempo real"
                ),
                "informante_id": "INF-TI-03",
                "dato_duro": "ALTO",
            },
        ],
        "grey_sources": ["Plan estratégico innovación 2026.pdf", "Informe KPIs Q1-2026.xlsx"],
        "extra": {
            "legal_name": "Prefeitura de São Caetano do Sul",
            "sector": "Sector público / Innovación",
            "city": "São Caetano do Sul",
            "country": "Brasil",
            "size_org": "501-1000",
            "years_operating": "12",
            "contact_name": "Ana Souza",
            "contact_role": "Secretaria de Innovación",
            "contact_email": "ana.souza@saocaetano.gov.br",
            "symptom": (
                "Retrasos en ejecución de proyectos de innovación, KPIs desactualizados "
                "y baja trazabilidad entre dirección y operación"
            ),
            "problem_since": "8 meses",
            "areas_count": "3",
            "previous_attempts": "PMO externo 2025 sin adopción sostenida",
            "expected_outcome": (
                "Diagnóstico AS-IS/TO-BE con brechas cuantificadas, instrumento multi-rater "
                "y plan priorizado a 90 días"
            ),
            "deadline": "30 días",
            "confidentiality": "Confidencial - Uso Estratégico",
        },
    }
    r = client.post(f"{API}/pro/cases", json=payload, timeout=60)
    r.raise_for_status()
    case = r.json()
    log("CREATE", f"{case.get('case_id')} (uuid={case['id']}) status={case.get('case_status')}")
    return case


def wait_survey_open(client: httpx.Client, case_id: str, timeout: int = 1200) -> dict:
    log("WAIT", "Esperando G01-G08 + encuesta G09...")
    t0 = time.time()
    while time.time() - t0 < timeout:
        r = client.get(f"{API}/pro/cases/{case_id}", timeout=30)
        r.raise_for_status()
        data = r.json()
        status = data.get("case_status")
        stages = data.get("stages") or []
        done = sum(1 for s in stages if s.get("status") == "completed")
        survey = data.get("survey") or {}
        if int(time.time()) % 12 < 5:
            log("WAIT", f"status={status} stages={done}/{len(stages)} survey={survey.get('status')}")
        if status == "survey_open" and survey.get("status") == "open":
            log("WAIT", f"OK — {survey.get('question_count', 0)} preguntas")
            return data
        if status == "error":
            raise RuntimeError(f"Caso en error: {json.dumps(data, ensure_ascii=False)[:500]}")
        time.sleep(4)
    raise TimeoutError("Timeout esperando survey_open")


def fill_survey(client: httpx.Client, case_data: dict) -> None:
    survey = case_data.get("survey") or {}
    token = survey.get("token")
    if not token:
        raise RuntimeError("Sin token de encuesta")
    sr = client.get(f"{API}/pro/survey/{token}", timeout=30)
    sr.raise_for_status()
    instrument = sr.json()
    questions = instrument.get("questions") or []
    if isinstance(questions, dict):
        questions = questions.get("questions") or []
    role_map = {"executive": "Estratégico", "operations": "Operativo", "technology": "Táctico"}
    for role_key in case_data.get("input_payload", {}).get("roles") or ["executive", "operations", "technology"]:
        role_label = role_map.get(role_key, role_key)
        default_val = ROLE_ANSWERS.get(role_label, 3)
        answers = {}
        for i, q in enumerate(questions):
            qid = q.get("id")
            if not qid:
                continue
            val = default_val
            if q.get("reverse_scored"):
                val = 6 - val
            val = max(1, min(5, val + (i % 3) - 1))
            answers[qid] = val
        sub = client.post(
            f"{API}/pro/survey/{token}/submit",
            json={"role": role_label, "answers": answers},
            timeout=30,
        )
        sub.raise_for_status()
        log("SURVEY", f"{role_label} OK — {sub.json().get('responses_count')}/3")


def run_diagnostic(client: httpx.Client, case_id: str) -> None:
    r = client.post(f"{API}/pro/cases/{case_id}/run", timeout=60)
    r.raise_for_status()
    log("RUN", r.json().get("message", "Diagnóstico iniciado"))


def wait_review(client: httpx.Client, case_id: str, timeout: int = 1200) -> dict:
    log("FUSION", "Esperando G10-G14...")
    t0 = time.time()
    while time.time() - t0 < timeout:
        r = client.get(f"{API}/pro/cases/{case_id}", timeout=30)
        r.raise_for_status()
        data = r.json()
        status = data.get("case_status")
        stages = data.get("stages") or []
        done = sum(1 for s in stages if s.get("status") == "completed")
        if int(time.time()) % 15 < 5:
            log("FUSION", f"status={status} stages={done}/{len(stages)}")
        if status == "review_pending":
            score = (data.get("fusion_result") or {}).get("scoring", {}).get("overall_score")
            log("FUSION", f"OK — madurez={score}")
            return data
        if status == "error":
            raise RuntimeError(f"Caso en error: {json.dumps(data, ensure_ascii=False)[:500]}")
        time.sleep(5)
    raise TimeoutError("Timeout esperando review_pending")


def approve(client: httpx.Client, case_id: str) -> None:
    r = client.post(
        f"{API}/pro/cases/{case_id}/approval",
        json={
            "action": "approve",
            "comment": "Caso demo Cloud Run — flujo completo verificado.",
            "reviewer_name": "Consultor ARHIAX",
        },
        timeout=30,
    )
    r.raise_for_status()
    log("APPROVE", f"status={r.json().get('case_status')}")


def generate_pdf(client: httpx.Client, case_id: str, case_ref: str) -> Path:
    gr = client.post(f"{API}/pro/cases/{case_id}/generate-deliverables", timeout=180)
    log("PDF", f"generate status={gr.status_code}")
    if gr.status_code != 200:
        raise RuntimeError(gr.text[:800])
    pr = client.get(f"{API}/pro/cases/{case_id}/download/pdf", timeout=180)
    pr.raise_for_status()
    if pr.content[:4] != b"%PDF":
        raise RuntimeError("Descarga no es PDF válido")
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{case_ref}_cloud.pdf"
    path.write_bytes(pr.content)
    log("PDF", f"OK — {len(pr.content):,} bytes -> {path}")
    return path


def main() -> int:
    print("=" * 60)
    print("CLOUD RUN — LIMPIEZA + CASO NUEVO E2E")
    print(CLOUD)
    print("=" * 60)
    with httpx.Client(timeout=180.0, follow_redirects=True) as client:
        login(client)
        list_cases(client)
        clean_db()
        time.sleep(2)
        list_cases(client)
        case = create_case(client)
        case_id = case["id"]
        case_data = wait_survey_open(client, case_id)
        fill_survey(client, case_data)
        run_diagnostic(client, case_id)
        case_final = wait_review(client, case_id)
        approve(client, case_id)
        pdf = generate_pdf(client, case_id, case_final.get("case_id", case_id))
    print("\n" + "=" * 60)
    print("LISTO")
    print(f"  UI:  {FRONT}/dashboard-pro/cases/{case_id}")
    print(f"  PDF: {pdf}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        raise SystemExit(1)
