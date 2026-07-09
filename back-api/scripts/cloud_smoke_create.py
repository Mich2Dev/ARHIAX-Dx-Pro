#!/usr/bin/env python3
import httpx

BASE = "https://arhiax-dx-pro-187668243215.southamerica-east1.run.app"
API = BASE + "/api/backend"

def check(label, fn):
    try:
        fn()
    except Exception as e:
        print(f"{label}: ERR {e}")

def main():
    print("=== Cloud Run connectivity ===")
    with httpx.Client(timeout=60, follow_redirects=True) as c:
        r = c.get(BASE + "/dashboard-pro")
        print("dashboard:", r.status_code)

        r = c.post(API + "/auth/login", data={"username": "admin@arhiax.com", "password": "arhiax-admin-2026"})
        print("login:", r.status_code, r.text[:150])
        if r.status_code != 200:
            return
        token = r.json()["access_token"]
        h = {"Authorization": f"Bearer {token}"}

        r = c.get(API + "/pro/cases", headers=h)
        print("list cases:", r.status_code, r.text[:150])

        r = c.post(
            API + "/pro/cases",
            headers=h,
            json={
                "consent": {"action": "ingest_to_llm", "consents": {"T1": True, "T3": True}},
                "engagement_id": "eng-smoke-test",
                "client_name": "Smoke Test",
                "domain": "Tecnologia",
                "roles": ["executive", "operations", "technology"],
                "dimensions": ["strategy", "process", "technology", "governance"],
                "hypotheses": [],
                "paquete_hipotesis": [{
                    "hipotesis_id": "H-01",
                    "enunciado": "Prueba de conexion al crear caso en Cloud Run",
                    "confianza": "MEDIA",
                    "observacion_refutadora": "obs",
                    "incidente_texto": "inc",
                    "informante_id": "INF-01",
                    "dato_duro": "MEDIO",
                }],
                "extra": {"symptom": "Prueba de sintoma para validar conexion", "expected_outcome": "Caso creado"},
            },
        )
        print("create case:", r.status_code, r.text[:400])

        r = c.get(API + "/pro/cases", headers=h)
        print("list after:", r.status_code, "total=", r.json().get("total"))

if __name__ == "__main__":
    main()
