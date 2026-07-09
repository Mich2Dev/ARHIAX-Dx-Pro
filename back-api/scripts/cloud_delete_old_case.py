#!/usr/bin/env python3
"""Borra SOLO el caso viejo en Cloud Run, preservando el nuevo."""
import httpx

API = "https://arhiax-dx-pro-187668243215.southamerica-east1.run.app/api/backend"
OLD_CASE_REF = "case-943b1ea60a"   # el que hay que borrar
KEEP_CASE_REF = "case-ffbf1ae77b"  # el nuevo que se conserva

r = httpx.post(f"{API}/auth/login",
               data={"username": "admin@arhiax.com", "password": "arhiax-admin-2026"},
               timeout=40)
r.raise_for_status()
h = {"Authorization": "Bearer " + r.json()["access_token"]}

data = httpx.get(f"{API}/pro/cases", headers=h, timeout=40).json()
target = None
for c in data.get("items", []):
    if c.get("case_id") == OLD_CASE_REF:
        target = c
if not target:
    print(f"No se encontro el caso viejo {OLD_CASE_REF}; nada que borrar.")
    raise SystemExit(0)

if target.get("case_id") == KEEP_CASE_REF:
    print("Salvaguarda: el objetivo coincide con el caso a conservar. Abortando.")
    raise SystemExit(1)

uuid = target["id"]
print(f"Borrando {OLD_CASE_REF} (uuid={uuid})...")
d = httpx.request("DELETE", f"{API}/pro/cases/{uuid}", headers=h, timeout=60)
print("delete status:", d.status_code, d.text[:200])

after = httpx.get(f"{API}/pro/cases", headers=h, timeout=40).json()
print("total restante:", after.get("total"))
for c in after.get("items", []):
    print("  -", c.get("case_id"), "|", c.get("client_name"), "|", c.get("case_status"))
