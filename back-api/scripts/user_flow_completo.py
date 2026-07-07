#!/usr/bin/env python3
"""
Flujo completo Pro — replica exacta de lo que hace un usuario en la UI:
  Login → Wizard (3 pasos) → Esperar G01-G08+G09 → Encuesta por rol →
  Lanzar diagnóstico → Esperar G10-G14 → Aprobar → Descargar PDF
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx

API = "http://localhost:8000"
FRONT = "http://localhost:3001"
OUT = Path(__file__).resolve().parents[2] / "exports" / "caso_completo"
EMAIL = "admin@arhiax.com"
PASSWORD = "arhiax-admin-2026"

# Respuestas por rol — crean delta_sigma real (como haría un usuario distinto por rol)
ROLE_ANSWERS = {
    "Estratégico": 5,   # executive — optimista
    "Operativo": 2,     # operations — crítico
    "Táctico": 3,       # technology — moderado
}


def log(step: str, msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    safe = msg.encode("ascii", "replace").decode("ascii")
    print(f"[{ts}] PASO {step}: {safe}", flush=True)


def login(client: httpx.Client) -> None:
    log("1", "Login en /auth/login (igual que pantalla login)")
    r = client.post(f"{API}/auth/login", data={"username": EMAIL, "password": PASSWORD})
    r.raise_for_status()
    client.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    log("1", f"OK — autenticado como {EMAIL}")


def create_case(client: httpx.Client) -> dict:
    log("2", "Wizard Pro — crear caso (POST /pro/cases con payload completo del wizard)")
    payload = {
        "consent": {"action": "ingest_to_llm", "consents": {"T1": True, "T3": True}},
        "engagement_id": f"eng-{int(time.time())}",
        "client_name": "Manufactura del Pacífico S.A.S.",
        "domain": "Manufactura y planificación de producción",
        "roles": ["executive", "operations", "technology"],
        "dimensions": ["strategy", "process", "technology", "governance"],
        "hypotheses": [],
        "paquete_hipotesis": [
            {
                "hipotesis_id": "H-01",
                "enunciado": (
                    "El OEE de la línea de empaque es inferior al 62% "
                    "porque los paros no programados no se registran con causa raíz en el MES"
                ),
                "confianza": "ALTA",
                "observacion_refutadora": (
                    "El tablero de planta reporta OEE 78%, pero mantenimiento registra "
                    "paros mayores a 45 min sin clasificación en el 34% de los eventos"
                ),
                "incidente_texto": (
                    "INC-2026-0518: línea L3 detenida 14 horas por falla de sensor sin registro "
                    "de causa en MES; turnos A y B usan códigos de paro distintos (auditoría mar-2026)"
                ),
                "informante_id": "INF-OPS-01",
                "dato_duro": "ALTO",
            },
            {
                "hipotesis_id": "H-02",
                "enunciado": (
                    "No existe trazabilidad de scrap por lote en la línea de inyección, "
                    "lo que impide priorizar acciones correctivas de calidad"
                ),
                "confianza": "MEDIA",
                "observacion_refutadora": (
                    "Existe bitácora en Excel compartida, pero no se usa en comités de gestión ni en decisiones"
                ),
                "incidente_texto": (
                    "Auditoría Q1-2026: 52% de rechazos de calidad sin lote trazable; "
                    "muestra de 95 unidades en línea de inyección Cali"
                ),
                "informante_id": "INF-QA-02",
                "dato_duro": "MEDIO",
            },
            {
                "hipotesis_id": "H-03",
                "enunciado": (
                    "La integración ERP-MES genera duplicidad de captura que incrementa "
                    "el tiempo de cierre de orden de producción en 35%"
                ),
                "confianza": "ALTA",
                "observacion_refutadora": (
                    "TI indica que la integración está activa desde 2024, pero no hay métricas de adopción por bodega"
                ),
                "incidente_texto": (
                    "Shadowing en planta Cali: supervisores re-ingresan 40% de avances manualmente "
                    "porque el MES no sincroniza consumos con el ERP en tiempo real"
                ),
                "informante_id": "INF-TI-03",
                "dato_duro": "ALTO",
            },
        ],
        "grey_sources": [
            "Informe auditoría OEE Q1-2026.pdf",
            "Bitácora scrap por lote.xlsx",
        ],
        "extra": {
            "legal_name": "Manufactura del Pacífico S.A.S.",
            "nit": "901.456.789-0",
            "sector": "Manufactura",
            "city": "Cali",
            "country": "Colombia",
            "size_org": "201-500",
            "years_operating": "18",
            "contact_name": "Carlos Ríos",
            "contact_role": "Gerente de Planta",
            "contact_email": "c.rios@manupacifico.com",
            "contact_phone": "+57 300 123 4567",
            "symptom": (
                "Caída de OEE en línea de empaque, scrap sin trazabilidad por lote "
                "y variabilidad en registro de paros entre turnos y plantas"
            ),
            "problem_since": "6 meses (escaló post-implementación MES parcial)",
            "areas_count": "2",
            "previous_attempts": "Lean workshop 2025 sin sostenibilidad",
            "expected_outcome": (
                "Mapa AS-IS/TO-BE con cuellos cuantificados, instrumento multi-rater validado "
                "y plan de acción priorizado con ROI en 90 días"
            ),
            "deadline": "45 días",
            "confidentiality": "Confidencial - Uso Estratégico",
        },
    }
    r = client.post(f"{API}/pro/cases", json=payload, timeout=60)
    r.raise_for_status()
    case = r.json()
    log("2", f"Caso creado -> {case.get('case_id')} (uuid={case['id']})")
    log("2", f"Estado inicial: {case.get('case_status')} — pipeline G01-G08 + G09 en background")
    return case


def wait_survey_open(client: httpx.Client, case_id: str, timeout: int = 900) -> dict:
    log("3", "Esperando fin de arquitectura (G01-G08 + encuesta G09) → survey_open")
    t0 = time.time()
    while time.time() - t0 < timeout:
        r = client.get(f"{API}/pro/cases/{case_id}", timeout=30)
        r.raise_for_status()
        data = r.json()
        status = data.get("case_status")
        stages = data.get("stages") or []
        done = sum(1 for s in stages if s.get("status") == "completed")
        survey = data.get("survey") or {}
        log("3", f"  status={status} stages={done}/{len(stages)} survey={survey.get('status')} preguntas={survey.get('question_count', 0)}")
        if status == "survey_open" and survey.get("status") == "open":
            log("3", "OK — Hub de recolección listo (como botón COPIAR enlace en UI)")
            return data
        if status == "error":
            raise RuntimeError(f"Caso en error: {data}")
        time.sleep(4)
    raise TimeoutError("Timeout esperando survey_open")


def fill_survey(client: httpx.Client, case_data: dict) -> None:
    survey = case_data.get("survey") or {}
    token = survey.get("token")
    if not token:
        raise RuntimeError("No hay token de encuesta")

    survey_url = f"{FRONT}/survey/pro/{token}"
    log("4", f"Abriendo encuesta pública: {survey_url}")

    sr = client.get(f"{API}/pro/survey/{token}", timeout=30)
    sr.raise_for_status()
    instrument = sr.json()
    questions = instrument.get("questions") or []
    if isinstance(questions, dict):
        questions = questions.get("questions") or []
    log("4", f"Instrumento cargado: {len(questions)} preguntas · {instrument.get('instrument_name', '')}")

    roles_config = case_data.get("input_payload", {}).get("roles") or ["executive", "operations", "technology"]
    role_map = {"executive": "Estratégico", "operations": "Operativo", "technology": "Táctico"}

    for role_key in roles_config:
        role_label = role_map.get(role_key, role_key)
        default_val = ROLE_ANSWERS.get(role_label, 3)
        answers = {}
        for i, q in enumerate(questions):
            qid = q.get("id")
            if not qid:
                continue
            # Variación leve por pregunta (como usuario real)
            val = default_val
            if q.get("reverse_scored"):
                val = 6 - val  # usuario responde intuitivo; backend corrige igual
            val = max(1, min(5, val + (i % 3) - 1))
            answers[qid] = val

        log("4", f"  Enviando encuesta como rol «{role_label}» ({len(answers)} respuestas, perfil={'optimista' if default_val >= 4 else 'crítico' if default_val <= 2 else 'moderado'})")
        sub = client.post(
            f"{API}/pro/survey/{token}/submit",
            json={"role": role_label, "answers": answers},
            timeout=30,
        )
        sub.raise_for_status()
        res = sub.json()
        log("4", f"  ✓ Respuesta guardada — total acumulado: {res.get('responses_count')}/{res.get('min_responses')}")
        time.sleep(1)


def run_diagnostic(client: httpx.Client, case_id: str) -> None:
    log("5", "Click «LANZAR SÍNTESIS DE DIAGNÓSTICO» → POST /pro/cases/{id}/run")
    r = client.post(f"{API}/pro/cases/{case_id}/run", timeout=60)
    r.raise_for_status()
    log("5", f"OK — {r.json().get('message', 'Diagnóstico iniciado')}")


def wait_review(client: httpx.Client, case_id: str, timeout: int = 900) -> dict:
    log("6", "Esperando ciclo de fusión G10-G14 → review_pending")
    t0 = time.time()
    while time.time() - t0 < timeout:
        r = client.get(f"{API}/pro/cases/{case_id}", timeout=30)
        r.raise_for_status()
        data = r.json()
        status = data.get("case_status")
        stages = data.get("stages") or []
        done = sum(1 for s in stages if s.get("status") == "completed")
        log("6", f"  status={status} stages={done}/{len(stages)}")
        if status == "review_pending":
            score = (data.get("fusion_result") or {}).get("scoring", {}).get("overall_score")
            log("6", f"OK — Diagnóstico listo para HIL · madurez={score}")
            return data
        if status == "error":
            raise RuntimeError(f"Caso en error: {data}")
        time.sleep(5)
    raise TimeoutError("Timeout esperando review_pending")


def approve(client: httpx.Client, case_id: str) -> None:
    log("7", "Click «APROBAR» en panel HIL → POST /pro/cases/{id}/approval")
    r = client.post(
        f"{API}/pro/cases/{case_id}/approval",
        json={
            "action": "approve",
            "comment": "Caso completo E2E — evidencia DDF + multi-rater + triangulación verificada.",
            "reviewer_name": "Consultor Senior ARHIAX",
        },
        timeout=30,
    )
    r.raise_for_status()
    log("7", f"OK — Estado: {r.json().get('case_status')} · sello criptográfico generado")


def generate_and_download(client: httpx.Client, case_id: str, case_ref: str, client_name: str) -> Path:
    log("8", "Generar entregables → POST /pro/cases/{id}/generate-deliverables")
    gr = client.post(f"{API}/pro/cases/{case_id}/generate-deliverables", timeout=120)
    log("8", f"  generate status={gr.status_code}")
    if gr.status_code != 200:
        print(gr.text[:800])
        gr.raise_for_status()

    log("9", "Descargar PDF (botón PDF en panel de resultados)")
    pr = client.get(f"{API}/pro/cases/{case_id}/download/pdf", timeout=120)
    pr.raise_for_status()
    if pr.content[:4] != b"%PDF":
        raise RuntimeError("La descarga no es un PDF válido")

    OUT.mkdir(parents=True, exist_ok=True)
    safe = client_name.replace(" ", "_").replace(".", "")[:40]
    pdf_path = OUT / f"{case_ref}_{safe}.pdf"
    md_path = OUT / f"{case_ref}_{safe}.md"

    pdf_path.write_bytes(pr.content)
    log("9", f"PDF guardado: {pdf_path} ({len(pr.content):,} bytes)")

    mr = client.get(f"{API}/pro/cases/{case_id}/download/markdown", timeout=60)
    if mr.status_code == 200:
        md_path.write_bytes(mr.content)
        log("9", f"MD guardado: {md_path}")

    summary = {
        "case_id": case_id,
        "case_ref": case_ref,
        "client_name": client_name,
        "pdf": str(pdf_path),
        "survey_url": f"{FRONT}/survey/pro/",
        "ui_url": f"{FRONT}/dashboard-pro/cases/{case_id}",
        "generated_at": datetime.now().isoformat(),
    }
    (OUT / "ultimo_caso.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return pdf_path


def main() -> int:
    import os
    resume_id = os.environ.get("CASE_ID", "").strip()
    print("=" * 60)
    print("FLUJO COMPLETO USUARIO - ARHIAX Dx Pro")
    print("=" * 60)
    with httpx.Client(timeout=120.0) as client:
        login(client)
        if resume_id:
            log("R", f"Reanudando caso existente {resume_id}")
            r = client.get(f"{API}/pro/cases/{resume_id}", timeout=30)
            r.raise_for_status()
            case = r.json()
            case_id = case["id"]
            case_data = case if case.get("case_status") == "survey_open" else wait_survey_open(client, case_id)
        else:
            case = create_case(client)
            case_id = case["id"]
            case_data = wait_survey_open(client, case_id)
        fill_survey(client, case_data)
        run_diagnostic(client, case_id)
        case_final = wait_review(client, case_id)
        approve(client, case_id)
        pdf = generate_and_download(
            client, case_id, case_final.get("case_id", case_id), case.get("client_name", "caso")
        )

    print("\n" + "=" * 60)
    print("FLUJO COMPLETADO")
    print(f"  UI caso: {FRONT}/dashboard-pro/cases/{case_id}")
    print(f"  PDF:     {pdf}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        raise SystemExit(1)
