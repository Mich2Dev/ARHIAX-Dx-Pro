#!/usr/bin/env python3
"""Regenera entregables y descarga PDF para un caso ya aprobado."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

API = "http://localhost:8000"
CASE_ID = sys.argv[1] if len(sys.argv) > 1 else "3854d391-a812-4111-a549-ddb4783dad8c"
OUT = Path("/app/exports/caso_completo")
EMAIL = "admin@arhiax.com"
PASSWORD = "arhiax-admin-2026"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=180.0) as client:
        login = client.post(f"{API}/auth/login", data={"username": EMAIL, "password": PASSWORD})
        login.raise_for_status()
        token = login.json()["access_token"]
        client.headers["Authorization"] = f"Bearer {token}"

        case = client.get(f"{API}/pro/cases/{CASE_ID}").json()
        ref = case.get("case_id", CASE_ID)
        name = case.get("client_name", "caso")
        print(f"Caso: {ref} | {name} | status={case.get('case_status')}")

        gen = client.post(f"{API}/pro/cases/{CASE_ID}/generate-deliverables")
        print(f"generate-deliverables: {gen.status_code}")
        if gen.status_code != 200:
            print(gen.text[:1000])
            gen.raise_for_status()

        pdf = client.get(f"{API}/pro/cases/{CASE_ID}/download/pdf")
        print(f"download/pdf: {pdf.status_code} bytes={len(pdf.content)}")
        pdf.raise_for_status()
        if pdf.content[:4] != b"%PDF":
            raise RuntimeError("Respuesta no es PDF")

        safe = name.replace(" ", "_").replace(".", "")[:40]
        path = OUT / f"{ref}_{safe}.pdf"
        path.write_bytes(pdf.content)
        print(f"PDF_GUARDADO: {path} ({len(pdf.content):,} bytes)")

        md = client.get(f"{API}/pro/cases/{CASE_ID}/download/markdown")
        if md.status_code == 200:
            md_path = OUT / f"{ref}_{safe}.md"
            md_path.write_bytes(md.content)
            print(f"MD_GUARDADO: {md_path}")

        summary = {
            "case_id": CASE_ID,
            "case_ref": ref,
            "client_name": name,
            "pdf": str(path),
            "status": case.get("case_status"),
        }
        (OUT / "ultimo_caso.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
