#!/usr/bin/env python3
"""Regenera PDF de un caso ya aprobado con el builder denso."""
import pathlib
import sys

import httpx

API = "http://localhost:8000"
OUT = pathlib.Path(__file__).resolve().parents[2] / "exports" / "e2e_demo"


def main() -> int:
    case_id = sys.argv[1] if len(sys.argv) > 1 else ""
    if not case_id:
        print("Uso: regen_pdf.py <case_uuid>")
        return 1

    r = httpx.post(
        f"{API}/auth/login",
        data={"username": "admin@arhiax.com", "password": "arhiax-admin-2026"},
        timeout=30,
    )
    r.raise_for_status()
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}

    cr = httpx.get(f"{API}/pro/cases/{case_id}", headers=h, timeout=30)
    cr.raise_for_status()
    case_ref = cr.json().get("case_id", case_id)
    print(f"Caso: {case_ref} status={cr.json().get('case_status')}")

    if cr.json().get("case_status") not in ("approved", "published"):
        ar = httpx.post(
            f"{API}/pro/cases/{case_id}/approval",
            json={"action": "approve", "comment": "Regen PDF"},
            headers=h,
            timeout=30,
        )
        print("approve", ar.status_code)

    gr = httpx.post(f"{API}/pro/cases/{case_id}/generate-deliverables", headers=h, timeout=120)
    print("generate", gr.status_code)
    if gr.status_code != 200:
        print(gr.text[:1000])
        return 1

    pr = httpx.get(f"{API}/pro/cases/{case_id}/download/pdf", headers=h, timeout=120)
    print("pdf", pr.status_code, len(pr.content), "bytes")
    if pr.status_code != 200:
        print(pr.text[:500])
        return 1

    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{case_ref}_diagnostico_nuevo.pdf"
    path.write_bytes(pr.content)
    print(f"Guardado: {path}")

    from pypdf import PdfReader
    rd = PdfReader(str(path))
    print(f"Páginas: {len(rd.pages)}")
    for i in range(min(5, len(rd.pages))):
        t = rd.pages[i].extract_text() or ""
        print(f"\n--- Página {i + 1} ({len(t)} chars) ---")
        print(t[:900])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
