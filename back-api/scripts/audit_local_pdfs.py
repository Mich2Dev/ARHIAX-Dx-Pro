#!/usr/bin/env python3
"""Auditoría de PDFs locales en carpeta Sinergia."""
from __future__ import annotations

import json
import re
from pathlib import Path

DRIFT = [
    ("vacaciones_rrhh", r"(?i)(solicitud de vacaciones|analista rrhh|jefe directo|solicitante)"),
    ("onboarding", r"(?i)(onboarding|nuevo ingreso|time-to-productivity)"),
    ("credito", r"(?i)(solicitud(es)? de cr[eé]dito|aprobaci[oó]n de cr[eé]dito)"),
    ("construccion_ok", r"(?i)(cotizaci[oó]n|liquidaci[oó]n|requisici[oó]n|mantenimiento)"),
    ("ddf_ok", r"(?i)(ingeniero.*liquidaci[oó]n|demora.*d[ií]as)"),
]

SINERGIA = Path(__file__).resolve().parents[3]


def audit_file(path: Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        return {"file": str(path), "error": str(e)}
    markers = {}
    for name, pat in DRIFT:
        markers[name] = bool(re.search(pat, text))
    pages = len(re.findall(r"-- \d+ of \d+ --", text))
    return {
        "file": path.name,
        "path": str(path),
        "size_kb": round(path.stat().st_size / 1024, 1),
        "pages_approx": pages,
        "markers": markers,
        "entregable": not (
            markers.get("vacaciones_rrhh")
            or markers.get("onboarding")
            or markers.get("credito")
        ),
    }


def main() -> None:
    pdfs = list(SINERGIA.glob("**/*diagnostico*.pdf")) + list(SINERGIA.glob("**/*IVANIA*.pdf"))
    pdfs = sorted({p.resolve() for p in pdfs if p.is_file()})
    results = [audit_file(p) for p in pdfs]
    out = SINERGIA / "AUDITORIA_PDFS_LOCALES.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
