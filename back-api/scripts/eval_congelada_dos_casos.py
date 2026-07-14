#!/usr/bin/env python3
"""Evaluación congelada: Ivania CD Global + caso finanzas limpio. Sin tocar producto."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

import httpx

API = "http://localhost:8000"
EMAIL = "admin@arhiax.com"
PASSWORD = "arhiax-admin-2026"
OUT = Path("/tmp/eval_congelada")
FRONT = "http://localhost:3001"

ALIEN = re.compile(
    r"\b(credit application|hr.?onboarding|vacation|onboarding|crédito de consumo)\b",
    re.I,
)


def log(step: str, msg: str) -> None:
    print(f"[{step}] {msg}", flush=True)


def login(c: httpx.Client) -> None:
    r = c.post(f"{API}/auth/login", data={"username": EMAIL, "password": PASSWORD})
    r.raise_for_status()
    c.headers["Authorization"] = f"Bearer {r.json()['access_token']}"


def get_case(c: httpx.Client, case_id: str) -> dict:
    r = c.get(f"{API}/pro/cases/{case_id}")
    r.raise_for_status()
    return r.json()


def poll(c: httpx.Client, case_id: str, want: set[str], timeout: int = 900) -> dict:
    t0 = time.time()
    while time.time() - t0 < timeout:
        data = get_case(c, case_id)
        st = data.get("case_status")
        survey = data.get("survey") or {}
        stages = data.get("stages") or data.get("pipeline_stages") or []
        done = sum(1 for s in stages if s.get("status") == "completed")
        phen = (data.get("phenomenon") or {}).get("summary") or {}
        log(
            "poll",
            f"status={st} survey={survey.get('status')} stages={done}/{len(stages)} "
            f"phen={phen.get('phenomenon_named') or '—'}",
        )
        if st in want:
            return data
        if st == "error" and "error" in want:
            return data
        if st == "error" and want <= {"survey_open"}:
            return data
        time.sleep(5)
    raise TimeoutError(f"Timeout {want}")


def fill_survey(c: httpx.Client, case: dict, role_answers: dict[str, int]) -> None:
    token = (case.get("survey") or {}).get("token")
    if not token:
        raise RuntimeError("sin token encuesta")
    log("campo", f"UI pública: {FRONT}/survey/pro/{token}")
    inst = c.get(f"{API}/pro/survey/{token}").json()
    questions = inst.get("questions") or []
    if isinstance(questions, dict):
        questions = questions.get("questions") or []
    log("campo", f"{len(questions)} preguntas · {inst.get('instrument_name', '')}")
    for role, base in role_answers.items():
        answers = {}
        for i, q in enumerate(questions):
            qid = q.get("id")
            if not qid:
                continue
            v = base + (i % 3) - 1
            answers[qid] = max(1, min(5, v))
        r = c.post(f"{API}/pro/survey/{token}/submit", json={"role": role, "answers": answers})
        r.raise_for_status()
        log("campo", f"rol={role} → {r.json().get('responses_count')}/{r.json().get('min_responses')}")
        time.sleep(0.5)


def analyze_phenomenon(c: httpx.Client, case_id: str, timeout: int = 600) -> dict:
    log("método", "POST /analyze (P01–P07)…")
    r = c.post(f"{API}/pro/cases/{case_id}/analyze")
    log("método", f"HTTP {r.status_code} {r.text[:200]}")
    r.raise_for_status()
    t0 = time.time()
    while time.time() - t0 < timeout:
        data = get_case(c, case_id)
        phen = data.get("phenomenon") or {}
        st = phen.get("status")
        named = (phen.get("summary") or {}).get("phenomenon_named")
        log("método", f"phen_status={st} named={named or '—'}")
        if st in ("done", "completed", "failed", "error") or named:
            return data
        # algunos builds no exponen status hasta terminar
        if named:
            return data
        time.sleep(6)
    return get_case(c, case_id)


def scan_contamination(case: dict) -> list[str]:
    hits = []
    blobs = [
        json.dumps(case.get("fusion_result") or {}, ensure_ascii=False),
        json.dumps(case.get("report_result") or {}, ensure_ascii=False),
        json.dumps(case.get("render_result") or {}, ensure_ascii=False)[:50000],
        json.dumps(case.get("stages") or case.get("pipeline_stages") or [], ensure_ascii=False)[:80000],
    ]
    for i, b in enumerate(blobs):
        m = ALIEN.findall(b)
        if m:
            hits.append(f"blob{i}:{sorted(set(m))}")
    return hits


def checklist(case: dict, label: str) -> dict:
    phen = (case.get("phenomenon") or {}).get("summary") or {}
    fusion = case.get("fusion_result") or {}
    thesis = str(fusion.get("executive_thesis") or "")
    err = case.get("pipeline_error") or fusion.get("error")
    contam = scan_contamination(case)
    return {
        "label": label,
        "case_ref": case.get("case_id"),
        "uuid": case.get("id"),
        "case_status": case.get("case_status"),
        "phenomenon_named": phen.get("phenomenon_named"),
        "resolution_motor": phen.get("resolution_motor"),
        "thesis_preview": thesis[:280],
        "score": (fusion.get("scoring") or {}).get("overall_score"),
        "responses": (case.get("survey") or {}).get("responses_count"),
        "pipeline_error": err,
        "contamination_hits": contam,
        "ui_case": f"{FRONT}/dashboard-pro/cases/{case.get('id')}",
    }


def run_ivania(c: httpx.Client) -> dict:
    payload = {
        "consent": {"action": "ingest_to_llm", "consents": {"T1": True, "T3": True}},
        "engagement_id": f"eng-ivania-{int(time.time())}",
        "client_name": "CD Global — Ivania Rua",
        "domain": "Ingeniería en climatización / HVAC retail",
        "survey_mode": "single_rater",
        "roles": ["executive"],
        "dimensions": ["strategy", "process", "technology", "people"],
        "paquete_hipotesis": [
            {
                "hipotesis_id": "H-01",
                "enunciado": (
                    "La cotización de cada tienda Dollar City se rearma casi desde cero "
                    "porque el criterio de cantidades y APU vive en la cabeza de pocos ingenieros "
                    "y no está sedimentado en el sistema"
                ),
                "confianza": "ALTA",
                "observacion_refutadora": (
                    "Ivania evalúa contratar otra ingeniera para compras; la nota interna dice "
                    "que en seis meses habrá una persona más y el mismo problema"
                ),
                "incidente_texto": (
                    "Más de 20 tiendas ejecutadas: la tienda 21 se cotiza como si fuera la primera; "
                    "cantidades preliminares del cliente suelen venir mal y el ingeniero las corrige "
                    "sin dejar el juicio escrito"
                ),
                "informante_id": "INF-IVANIA",
                "dato_duro": "ALTO",
            },
            {
                "hipotesis_id": "H-02",
                "enunciado": (
                    "Las requisiciones llegan incompletas y tarde porque la lista de materiales "
                    "no sale automática del APU aprobado y se rearma a mano"
                ),
                "confianza": "ALTA",
                "observacion_refutadora": "Existe Excel informal, pero no gobierna la compra",
                "incidente_texto": (
                    "Faltantes y sobrecompra en cierre de obra; seguimiento por WhatsApp entre "
                    "Jensi, Kenny, Gloria, contratistas e Ivania"
                ),
                "informante_id": "INF-OPS",
                "dato_duro": "ALTO",
            },
            {
                "hipotesis_id": "H-03",
                "enunciado": (
                    "El saber de campo (decisiones distintas al diseño) se pierde al cerrar cada obra; "
                    "mantenimiento reactivo arranca sin hoja de vida del equipo"
                ),
                "confianza": "MEDIA",
                "observacion_refutadora": "Hay tickets, pero sin historial por equipo instalado",
                "incidente_texto": "Mantenimiento reactivo por tickets; sin QR/historial por equipo",
                "informante_id": "INF-MANT",
                "dato_duro": "MEDIO",
            },
        ],
        "grey_sources": [
            "Nota interna Ivania — problema no es falta de personal",
            "Formulario descubrimiento CD Global Governex",
        ],
        "extra": {
            "legal_name": "CD Global",
            "sector": "Ingeniería climatización · VRF · ductería · drenajes",
            "city": "Barranquilla / obras Dollar City",
            "country": "Colombia",
            "size_org": "11-50",
            "contact_name": "Ivania Rua",
            "contact_role": "Gerencia",
            "symptom": (
                "Los ingenieros tardan demasiado en entender y armar cotizaciones; requisiciones "
                "incompletas; material tarde; seguimiento por WhatsApp; información dispersa. "
                "Ivania formula 'falta de personal' pero el problema es que los procesos dependen "
                "de personas y no del sistema — saber operativo no sedimentado tras 20+ tiendas."
            ),
            "problem_since": "Estructural; empeora con crecimiento retail",
            "areas_count": "4",
            "previous_attempts": "Evaluar contratación de ingeniera mecánica para compras",
            "expected_outcome": (
                "Fenómeno nombrado, contradicción TRIZ, motor 80/20 para cotización/requisición, "
                "y formulario de descubrimiento alineado a la operación real"
            ),
            "deadline": "10 semanas fase 1",
            "confidentiality": "Restringido",
        },
    }
    log("1", "Crear caso Ivania / CD Global…")
    r = c.post(f"{API}/pro/cases", json=payload, timeout=60)
    r.raise_for_status()
    case = r.json()
    cid = case["id"]
    log("1", f"uuid={cid} ref={case.get('case_id')} UI={FRONT}/dashboard-pro/cases/{cid}")

    log("2", "Esperar survey_open (arquitectura G01–G09)…")
    case = poll(c, cid, {"survey_open", "error"}, timeout=900)
    if case.get("case_status") == "error":
        return checklist(case, "ivania_error_pre_survey")

    case = analyze_phenomenon(c, cid)
    fill_survey(c, case, {"Estratégico": 3})

    log("5", "Lanzar síntesis…")
    rr = c.post(f"{API}/pro/cases/{cid}/run", timeout=60)
    log("5", f"run HTTP {rr.status_code} {rr.text[:180]}")
    case = poll(c, cid, {"review_pending", "error"}, timeout=900)
    return checklist(case, "ivania")


def run_finance(c: httpx.Client) -> dict:
    payload = {
        "consent": {"action": "ingest_to_llm", "consents": {"T1": True, "T3": True}},
        "engagement_id": f"eng-fin-{int(time.time())}",
        "client_name": "Finanzas Norte S.A.S.",
        "domain": "Finanzas corporativas / control de gestión",
        "survey_mode": "single_rater",
        "roles": ["executive"],
        "dimensions": ["strategy", "process", "governance", "technology"],
        "paquete_hipotesis": [
            {
                "hipotesis_id": "H-01",
                "enunciado": (
                    "El cierre contable mensual tarda 12–15 días porque conciliación bancaria "
                    "y provisiones viven en hojas Excel distintas sin dueño único"
                ),
                "confianza": "ALTA",
                "observacion_refutadora": "ERP reporta cierre en 5 días, pero auditoria ve ajustes post-cierre",
                "incidente_texto": (
                    "Cierre feb-2026: 47 asientos de ajuste post-cierre; CFO no confía en P&L hasta día 18"
                ),
                "informante_id": "INF-CFO",
                "dato_duro": "ALTO",
            },
            {
                "hipotesis_id": "H-02",
                "enunciado": (
                    "No hay forecast de caja a 13 semanas operativo; tesorería decide con WhatsApp "
                    "y extractos del día"
                ),
                "confianza": "ALTA",
                "observacion_refutadora": "Existe presupuesto anual, pero no rolling cash",
                "incidente_texto": "Mar-2026: sobregiro evitado en 48h con venta urgente de CDT",
                "informante_id": "INF-TES",
                "dato_duro": "ALTO",
            },
        ],
        "grey_sources": ["Bitácora ajustes post-cierre Q1.pdf"],
        "extra": {
            "legal_name": "Finanzas Norte S.A.S.",
            "sector": "Servicios financieros corporativos",
            "city": "Bogotá",
            "country": "Colombia",
            "size_org": "51-200",
            "contact_name": "Laura Mendoza",
            "contact_role": "CFO",
            "symptom": (
                "Cierre contable lento, ajustes post-cierre frecuentes y ausencia de forecast de caja "
                "rolling; el área de finanzas no confía en reportes hasta casi 3 semanas después del mes"
            ),
            "problem_since": "9 meses",
            "areas_count": "1",
            "previous_attempts": "Consultoría ERP 2025 sin cambio de proceso de cierre",
            "expected_outcome": (
                "Diagnóstico del proceso de cierre y caja con cuellos cuantificados y plan 90 días"
            ),
            "deadline": "60 días",
            "confidentiality": "Confidencial",
        },
    }
    log("1b", "Crear caso Finanzas Norte (ancla limpia)…")
    r = c.post(f"{API}/pro/cases", json=payload, timeout=60)
    r.raise_for_status()
    case = r.json()
    cid = case["id"]
    log("1b", f"uuid={cid} ref={case.get('case_id')} UI={FRONT}/dashboard-pro/cases/{cid}")

    case = poll(c, cid, {"survey_open", "error"}, timeout=900)
    if case.get("case_status") == "error":
        return checklist(case, "finance_error_pre_survey")

    case = analyze_phenomenon(c, cid)
    fill_survey(c, case, {"Estratégico": 2})
    rr = c.post(f"{API}/pro/cases/{cid}/run", timeout=60)
    log("5b", f"run HTTP {rr.status_code}")
    case = poll(c, cid, {"review_pending", "error"}, timeout=900)
    return checklist(case, "finance")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=180.0) as c:
        log("0", "Login…")
        login(c)
        results = []
        try:
            results.append(run_ivania(c))
        except Exception as e:
            results.append({"label": "ivania", "fatal": str(e)})
            log("ERR", f"Ivania: {e}")
        try:
            results.append(run_finance(c))
        except Exception as e:
            results.append({"label": "finance", "fatal": str(e)})
            log("ERR", f"Finance: {e}")

        out = OUT / f"eval_{int(time.time())}.json"
        out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
        log("DONE", str(out))
        print(json.dumps(results, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
