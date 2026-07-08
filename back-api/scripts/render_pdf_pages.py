#!/usr/bin/env python3
"""Regenera el PDF de un caso aprobado y rasteriza páginas a PNG para inspección."""
from __future__ import annotations

import sys
from pathlib import Path

import httpx

API = "http://localhost:8000"
CASE_ID = sys.argv[1] if len(sys.argv) > 1 else "3854d391-a812-4111-a549-ddb4783dad8c"
OUT = Path("/app/exports/render")
EMAIL = "admin@arhiax.com"
PASSWORD = "arhiax-admin-2026"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=180.0) as client:
        login = client.post(f"{API}/auth/login", data={"username": EMAIL, "password": PASSWORD})
        login.raise_for_status()
        client.headers["Authorization"] = f"Bearer {login.json()['access_token']}"

        gen = client.post(f"{API}/pro/cases/{CASE_ID}/generate-deliverables")
        print("generate:", gen.status_code)
        if gen.status_code != 200:
            print(gen.text[:800])
            return 1
        pdf = client.get(f"{API}/pro/cases/{CASE_ID}/download/pdf")
        pdf.raise_for_status()
        pdf_bytes = pdf.content
        print("pdf bytes:", len(pdf_bytes))

    pdf_path = OUT / "informe.pdf"
    pdf_path.write_bytes(pdf_bytes)

    import fitz  # PyMuPDF

    doc = fitz.open(pdf_path)
    print("paginas:", doc.page_count)
    for i in range(doc.page_count):
        page = doc.load_page(i)
        pix = page.get_pixmap(dpi=110)
        pix.save(str(OUT / f"pag_{i + 1:02d}.png"))
    print("render OK ->", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
