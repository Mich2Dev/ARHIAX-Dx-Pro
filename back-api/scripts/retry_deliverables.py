"""Reintenta generate-deliverables + descarga PDF sobre un caso ya aprobado."""

import os
import sys
from pathlib import Path

import httpx

API = "http://localhost:8000"
EMAIL = "admin@arhiax.com"
PASSWORD = "arhiax-admin-2026"
OUT = Path(__file__).resolve().parent.parent / "out_e2e"


def main() -> int:
    case_ref = os.environ.get("CASE_ID", "").strip()
    with httpx.Client(timeout=180.0) as c:
        r = c.post(f"{API}/auth/login", data={"username": EMAIL, "password": PASSWORD})
        r.raise_for_status()
        c.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
        print("login OK")

        if not case_ref:
            lst = c.get(f"{API}/pro/cases", timeout=30).json()
            items = lst if isinstance(lst, list) else lst.get("items", [])
            cand = [
                x for x in items
                if x.get("case_status") in ("approved", "review_pending")
            ]
            if not cand:
                print("No hay casos approved/review_pending. Todos:")
                for x in items:
                    print(" -", x.get("id"), x.get("case_id"), x.get("case_status"))
                return 2
            case_ref = cand[0]["id"]
            print(f"Caso elegido: {case_ref} ({cand[0].get('case_status')})")

        info = c.get(f"{API}/pro/cases/{case_ref}", timeout=30).json()
        case_id = info["id"]
        client_name = info.get("client_name", "caso")
        print(f"Caso {case_id} status={info.get('case_status')} cliente={client_name}")

        gr = c.post(f"{API}/pro/cases/{case_id}/generate-deliverables", timeout=180)
        print(f"generate-deliverables status={gr.status_code}")
        if gr.status_code != 200:
            print(gr.text[:1200])
            return 3

        pr = c.get(f"{API}/pro/cases/{case_id}/download/pdf", timeout=180)
        pr.raise_for_status()
        if pr.content[:4] != b"%PDF":
            print("La descarga no es PDF valido")
            return 4

        OUT.mkdir(parents=True, exist_ok=True)
        safe = client_name.replace(" ", "_").replace(".", "")[:40]
        pdf_path = OUT / f"{info.get('case_id', case_id)}_{safe}.pdf"
        pdf_path.write_bytes(pr.content)
        print(f"PDF guardado: {pdf_path} ({len(pr.content):,} bytes)")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
