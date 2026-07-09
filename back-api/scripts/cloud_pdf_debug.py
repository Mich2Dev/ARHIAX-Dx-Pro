"""Diagnóstico PDF en Cloud Run — lista casos aprobados e intenta descarga."""
import json
import os
import sys

import httpx

API = os.getenv("CLOUD_API", "https://arhiax-dx-pro-187668243215.southamerica-east1.run.app/api/backend")
EMAIL = os.getenv("ARHIAX_EMAIL", "admin@arhiax.com")
PASSWORD = os.getenv("ARHIAX_PASSWORD", "arhiax-admin-2026")


def main() -> int:
    case_uuid = os.environ.get("CASE_UUID", "").strip()
    with httpx.Client(timeout=180.0) as c:
        r = c.post(f"{API}/auth/login", data={"username": EMAIL, "password": PASSWORD})
        print("login", r.status_code)
        if r.status_code != 200:
            print(r.text[:500])
            return 1
        c.headers["Authorization"] = f"Bearer {r.json()['access_token']}"

        cases = c.get(f"{API}/pro/cases").json()
        items = cases if isinstance(cases, list) else cases.get("items", [])
        approved = [x for x in items if x.get("case_status") in ("approved", "published")]
        print(f"Casos aprobados: {len(approved)}")
        for x in approved:
            print(f"  {x.get('case_id')} | {x.get('client_name')} | {x.get('id')}")

        if not approved:
            return 2

        target = case_uuid or approved[-1]["id"]
        info = c.get(f"{API}/pro/cases/{target}").json()
        print(f"\nProbando: {info.get('case_id')} ({info.get('client_name')}) status={info.get('case_status')}")

        gr = c.post(f"{API}/pro/cases/{target}/generate-deliverables")
        print(f"generate-deliverables: {gr.status_code}")
        if gr.status_code != 200:
            try:
                print(json.dumps(gr.json(), indent=2, ensure_ascii=False)[:2000])
            except Exception:
                print(gr.text[:2000])

        pr = c.get(f"{API}/pro/cases/{target}/download/pdf")
        print(f"download/pdf: {pr.status_code} bytes={len(pr.content)}")
        if pr.status_code != 200:
            try:
                print(json.dumps(pr.json(), indent=2, ensure_ascii=False)[:2000])
            except Exception:
                print(pr.text[:2000])
            return 3
        if pr.content[:4] != b"%PDF":
            print("No es PDF válido:", pr.content[:200])
            return 4
        print("PDF OK")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
