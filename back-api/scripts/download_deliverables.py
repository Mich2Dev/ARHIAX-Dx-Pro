#!/usr/bin/env python3
"""Descarga PDF y MD de un caso aprobado."""
import pathlib
import sys

import httpx

API = "http://localhost:8000"
OUT = pathlib.Path(__file__).resolve().parents[2] / "exports" / "caso_completo"


def main() -> int:
    case_id = sys.argv[1] if len(sys.argv) > 1 else ""
    if not case_id:
        print("Uso: download_deliverables.py <case_uuid>")
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
    meta = cr.json()
    case_ref = meta.get("case_id", case_id)
    client = meta.get("client_name", "caso").replace(" ", "_").replace(".", "")[:40]

    httpx.post(f"{API}/pro/cases/{case_id}/generate-deliverables", headers=h, timeout=120)

    pr = httpx.get(f"{API}/pro/cases/{case_id}/download/pdf", headers=h, timeout=120)
    mr = httpx.get(f"{API}/pro/cases/{case_id}/download/markdown", headers=h, timeout=60)
    pr.raise_for_status()
    mr.raise_for_status()

    OUT.mkdir(parents=True, exist_ok=True)
    pdf_path = OUT / f"{case_ref}_{client}.pdf"
    md_path = OUT / f"{case_ref}_{client}.md"
    pdf_path.write_bytes(pr.content)
    md_path.write_bytes(mr.content)
    print(f"PDF: {pdf_path} ({len(pr.content)} bytes)")
    print(f"MD:  {md_path} ({len(mr.content)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
